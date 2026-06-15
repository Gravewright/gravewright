from __future__ import annotations

from app.engine.sdk.package_activation_service import PackageActivationService
from app.engine.sdk.package_doctor_service import PackageDoctorService
from app.engine.sdk.package_install_service import PackageInstallService
from app.persistence.repositories.installed_package_repository import (
    InstalledPackageRepository,
)
from app.persistence.repositories.package_setting_repository import (
    PackageSettingRepository,
)
from tests.conftest import install_system, seed_campaign, seed_system, seed_user


def _codes(findings: list[dict]) -> set[str]:
    return {f["code"] for f in findings}


def test_clean_install_has_no_findings(db):
    gm = seed_user(email="doctor-clean@test.com")
    campaign = seed_campaign(gm)
    seed_system(campaign, gm, "dnd5e")

    report = PackageDoctorService().report()

    assert report["ok"] is True
    assert report["findings"] == []


def test_detects_active_but_disabled(db):
    gm = seed_user(email="doctor-disabled@test.com")
    campaign = seed_campaign(gm)
    seed_system(campaign, gm, "dnd5e")

    # The package is active in the campaign but gets disabled out from under it.
    InstalledPackageRepository().set_status(package_id="dnd5e", status="disabled")

    report = PackageDoctorService().report()

    assert report["ok"] is False
    assert "active_but_disabled" in _codes(report["findings"])
    finding = next(f for f in report["findings"] if f["code"] == "active_but_disabled")
    assert finding["package_id"] == "dnd5e"
    assert finding["campaign_id"] == campaign


def test_detects_package_missing_on_disk(db):
    gm = seed_user(email="doctor-missing@test.com")
    install_system(gm, package_id="dnd5e")

    # Forge a DB row for a package that does not exist on disk.
    InstalledPackageRepository().upsert(
        package_id="ghost-pkg",
        kind="addon",
        name="Ghost",
        version="1.0.0",
        status="enabled",
        package_dir="ghost-pkg",
        manifest_json="{}",
        compatibility_status="compatible",
        validation_errors_json="[]",
        installed_by_user_id=gm,
    )

    report = PackageDoctorService().report()

    assert "package_missing_on_disk" in _codes(report["findings"])


def test_detects_orphan_settings(db):
    gm = seed_user(email="doctor-settings@test.com")
    install_system(gm, package_id="dice-so-nice-lite")

    settings = PackageSettingRepository()
    # Undeclared key on an installed package.
    settings.set(
        package_id="dice-so-nice-lite",
        setting_key="not.a.real.key",
        value_json='"x"',
        campaign_id=None,
        user_id=None,
    )
    # Value for a package that was never installed.
    settings.set(
        package_id="vanished-pkg",
        setting_key="whatever",
        value_json='"y"',
        campaign_id=None,
        user_id=None,
    )

    codes = _codes(PackageDoctorService().report()["findings"])

    assert "orphan_setting_undeclared" in codes
    assert "orphan_setting_uninstalled" in codes


def test_clean_removal_cascades_without_false_positive(db):
    """Removing an installed package cascades its campaign activation (FK), so the
    audit must not report stale ``active_but_*`` drift afterwards."""
    gm = seed_user(email="doctor-removal@test.com")
    campaign = seed_campaign(gm)
    seed_system(campaign, gm, "dnd5e")
    install_system(gm, package_id="dice-so-nice-lite")
    PackageActivationService().activate_package(campaign, "dice-so-nice-lite", gm)

    # A clean remove (cascade) of the addon — the ruleset stays intact.
    PackageInstallService().remove(package_id="dice-so-nice-lite", force=True)

    report = PackageDoctorService().report()

    assert report["ok"] is True
    assert "dice-so-nice-lite" not in {f["package_id"] for f in report["findings"]}
