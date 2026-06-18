"""Phase 9 — strict package doctor.

The doctor speaks the canonical DoctorFinding contract, never crashes on a
broken/corrupt package, and serializes findings for the CLI/UI.
"""

from __future__ import annotations

from app.engine.sdk.diagnostics import DoctorFinding
from app.engine.sdk.package_doctor_service import PackageDoctorService
from tests.conftest import install_system, seed_campaign, seed_system, seed_user


def test_doctor_findings_use_canonical_finding_type(db):
    gm = seed_user(email="strict-shape@test.com")
    campaign = seed_campaign(gm)
    seed_system(campaign, gm, "valid-ruleset")
    from app.persistence.repositories.installed_package_repository import (
        InstalledPackageRepository,
    )

    # Introduce a broken state so there is at least one finding to inspect.
    InstalledPackageRepository().set_status(package_id="valid-ruleset", status="disabled")

    findings = PackageDoctorService().audit()
    assert findings
    for finding in findings:
        assert isinstance(finding, DoctorFinding)
        assert finding.severity in {"error", "warning", "info"}
        data = finding.to_dict()
        assert set(data) <= {
            "code",
            "severity",
            "message",
            "details",
            "package_id",
            "campaign_id",
        }
        assert data["code"]


def test_report_serializes_findings_for_cli(db):
    gm = seed_user(email="strict-report@test.com")
    campaign = seed_campaign(gm)
    seed_system(campaign, gm, "valid-ruleset")
    from app.persistence.repositories.installed_package_repository import (
        InstalledPackageRepository,
    )

    InstalledPackageRepository().set_status(package_id="valid-ruleset", status="disabled")
    report = PackageDoctorService().report()
    assert report["ok"] is False
    assert report["error_count"] >= 1
    assert all("code" in f and "severity" in f for f in report["findings"])


def test_doctor_does_not_crash_on_broken_package(db, monkeypatch):
    gm = seed_user(email="strict-crash@test.com")
    install_system(gm, package_id="valid-ruleset")

    def boom(_installed):
        raise RuntimeError("simulated corrupt package")

    doctor = PackageDoctorService()
    monkeypatch.setattr(doctor, "_audit_installed", boom)

    # The audit isolates the failure into a finding instead of raising.
    findings = doctor.audit()
    codes = {f.code for f in findings}
    assert "sdk.doctor.audit_error" in codes


def test_clean_install_has_no_findings(db):
    gm = seed_user(email="strict-clean@test.com")
    campaign = seed_campaign(gm)
    seed_system(campaign, gm, "valid-ruleset")
    assert PackageDoctorService().report()["ok"] is True
