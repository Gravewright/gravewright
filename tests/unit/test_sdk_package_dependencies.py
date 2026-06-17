"""Phase 8 — reverse dependencies and safe activation.

A package cannot be disabled, removed, or deactivated while another active
package depends on it (unless ``force``). ``force`` is allowed but then the
doctor reports the resulting broken state. Removing a package preserves its
managed storage by default.
"""

from __future__ import annotations

import shutil

from app.engine.sdk import package_registry
from app.engine.sdk.package_activation_service import PackageActivationService
from app.engine.sdk.package_dependency_service import (
    DependencyReport,
    PackageDependencyService,
)
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk.package_manifest import PackageManifest
from tests.conftest import install_system, seed_campaign, seed_user


def _depends_on_dnd5e(self, package_id):
    """get_manifest stand-in: dice depends on dnd5e; everything else is real."""
    if package_id == "dice-so-nice-lite":
        return PackageManifest.from_dict(
            {"id": "dice-so-nice-lite", "kind": "addon", "dependencies": [{"id": "dnd5e"}]}
        )
    loaded = package_registry.load_by_package_id(package_id)
    return loaded.manifest if loaded else None


def _install_pair(email):
    gm = seed_user(email=email)
    install_system(gm, package_id="dnd5e")
    install_system(gm, package_id="dice-so-nice-lite")
    return gm


# --- reverse dependents ------------------------------------------------------


def test_active_dependents_lists_enabled_dependent(db, monkeypatch):
    _install_pair("dep-list@test.com")
    monkeypatch.setattr(PackageInstallService, "get_manifest", _depends_on_dnd5e)
    dependents = PackageInstallService().active_dependents("dnd5e")
    assert {d["id"] for d in dependents} == {"dice-so-nice-lite"}


def test_disable_blocked_when_active_package_depends_on_it(db, monkeypatch):
    _install_pair("dep-disable@test.com")
    monkeypatch.setattr(PackageInstallService, "get_manifest", _depends_on_dnd5e)
    svc = PackageInstallService()

    result = svc.disable(package_id="dnd5e")
    assert result.success is False
    assert result.error_key == "sdk.errors.active_dependents"


def test_remove_blocked_when_active_package_depends_on_it(db, monkeypatch):
    _install_pair("dep-remove@test.com")
    monkeypatch.setattr(PackageInstallService, "get_manifest", _depends_on_dnd5e)
    svc = PackageInstallService()

    result = svc.remove(package_id="dnd5e")
    assert result.success is False
    assert result.error_key == "sdk.errors.active_dependents"


def test_active_dependents_error_includes_dependents_details(db, monkeypatch):
    _install_pair("dep-details@test.com")
    monkeypatch.setattr(PackageInstallService, "get_manifest", _depends_on_dnd5e)

    result = PackageInstallService().disable(package_id="dnd5e")
    assert [d["id"] for d in result.active_dependents] == ["dice-so-nice-lite"]


def test_force_disable_allows_but_doctor_reports_missing_dependency(db, monkeypatch):
    from app.engine.sdk.package_doctor_service import PackageDoctorService

    _install_pair("dep-force@test.com")
    monkeypatch.setattr(PackageInstallService, "get_manifest", _depends_on_dnd5e)

    forced = PackageInstallService().disable(package_id="dnd5e", force=True)
    assert forced.success is True

    # dice is still enabled but its dependency dnd5e is now disabled.
    codes = {f.code for f in PackageDoctorService().audit()}
    assert "dependency_disabled" in codes


def test_remove_package_preserves_storage_by_default(db, monkeypatch):
    gm = seed_user(email="dep-storage@test.com")
    install_system(gm, package_id="dnd5e")

    storage = package_registry.storage_dir_for("ruleset", "dnd5e")
    (storage / "global").mkdir(parents=True, exist_ok=True)
    marker = storage / "global" / "data.sqlite3"
    marker.write_text("data", encoding="utf-8")
    try:
        result = PackageInstallService().remove(package_id="dnd5e", force=True)
        assert result.success is True
        assert marker.is_file(), "managed storage must survive package removal"
    finally:
        shutil.rmtree(package_registry.STORAGE_PACKAGES_DIR, ignore_errors=True)


# --- campaign deactivation ---------------------------------------------------


def test_deactivate_blocked_when_active_package_depends_on_it(db, monkeypatch):
    gm = seed_user(email="dep-deactivate@test.com")
    campaign = seed_campaign(gm)
    monkeypatch.setattr(
        PackageDependencyService,
        "active_campaign_dependents",
        lambda self, pid, cid: [{"id": "needs-it"}],
    )
    svc = PackageActivationService()

    blocked = svc.deactivate_package(campaign, "some-addon", gm)
    assert blocked.success is False
    assert blocked.error_key == "sdk.errors.active_dependents"

    forced = svc.deactivate_package(campaign, "some-addon", gm, force=True)
    assert forced.success is True


def test_ruleset_switch_revalidates_dependencies(db, monkeypatch):
    gm = seed_user(email="dep-ruleset@test.com")
    campaign = seed_campaign(gm)
    install_system(gm, package_id="dnd5e")

    # A failing dependency report must block the ruleset switch.
    monkeypatch.setattr(
        PackageDependencyService,
        "check_campaign_activation",
        lambda self, pid, cid: DependencyReport(ok=False, missing=[{"id": "needs-it"}]),
    )
    result = PackageActivationService().set_campaign_ruleset(campaign, "dnd5e", gm)
    assert result.success is False
