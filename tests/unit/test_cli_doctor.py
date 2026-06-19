from __future__ import annotations

import json
from pathlib import Path

from app.cli import main
from app.cli.doctor import Check, _audit_checks, render_check_lines, render_pretty
from app.engine.sdk.diagnostics import DoctorFinding
from app.engine.sdk.package_doctor_service import PackageDoctorService
from app.engine.sdk.package_install_service import PackageInstallService
from app.persistence.repositories.installed_package_repository import (
    InstalledPackageRepository,
)
from tests.conftest import (
    SDK_FIXTURES_ROOT,
    install_system,
    seed_campaign,
    seed_system,
    seed_user,
)


def _write_bad_package(root: Path) -> None:
    pkg = root / "bad-package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text('{"id": "Bad"}', encoding="utf-8")


def test_doctor_reports_error_and_fix_for_invalid_package(tmp_path, capsys):
    _write_bad_package(tmp_path)

    exit_code = main(["doctor", "--packages-dir", str(tmp_path), "--skip-db", "--json"])

    assert exit_code == 1  # EXIT_DOCTOR_ERROR
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    errors = [c for c in payload["checks"] if c["status"] == "error"]
    assert errors, "expected at least one error check"
    assert any(c["fix"] and "grave package validate" in c["fix"] for c in errors)


def test_doctor_text_lists_fix_lines(tmp_path, capsys):
    _write_bad_package(tmp_path)

    exit_code = main(["doctor", "--packages-dir", str(tmp_path), "--skip-db"])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "ERROR" in out
    assert "FIX " in out
    assert "Not ready" in out


def test_doctor_reports_grouped_package_dir_missing_manifest(tmp_path, capsys):
    pkg = tmp_path / "rulesets" / "sample-ruleset"
    pkg.mkdir(parents=True)

    exit_code = main(["doctor", "--packages-dir", str(tmp_path), "--skip-db", "--json"])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    errors = [c for c in payload["checks"] if c["status"] == "error"]
    assert any("sample-ruleset" in c["message"] for c in errors)
    assert any("sdk.validation.manifest_missing" in c["message"] for c in errors)


def test_doctor_db_audit_surfaces_active_but_disabled_with_fix(db, capsys):
    gm = seed_user(email="doctor-cli-disabled@test.com")
    campaign = seed_campaign(gm)
    seed_system(campaign, gm, "valid-ruleset")
    InstalledPackageRepository().set_status(package_id="valid-ruleset", status="disabled")

    exit_code = main(
        ["doctor", "--packages-dir", str(SDK_FIXTURES_ROOT), "--json"]
    )

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    audit = {c["id"]: c for c in payload["checks"]}
    assert "audit:active_but_disabled" in audit
    assert "grave package enable" in audit["audit:active_but_disabled"]["fix"]


def test_doctor_warns_enabled_addon_inactive_in_any_campaign(db, capsys):
    gm = seed_user(email="doctor-cli-inactive@test.com")
    install_system(gm, package_id="valid-addon")  # installed + enabled, never activated
    # Keep the install valid so the only finding is the inactivity hint.
    assert PackageInstallService().get("valid-addon")["status"] == "enabled"

    exit_code = main(
        ["doctor", "--packages-dir", str(SDK_FIXTURES_ROOT), "--json"]
    )

    # Inactivity is a warning, not an error.
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    warns = {c["id"]: c for c in payload["checks"] if c["status"] == "warn"}
    assert "inactive:valid-addon" in warns


def test_doctor_normalizes_audit_warning_for_text_output(monkeypatch):
    monkeypatch.setattr(
        PackageDoctorService,
        "audit",
        lambda self: [
            DoctorFinding(
                code="orphan_setting_uninstalled",
                severity="warning",
                package_id="missing-addon",
            )
        ],
    )

    checks = _audit_checks()

    assert checks[0].status == "warn"
    assert render_check_lines(checks)[0].startswith("WARN ")


def test_doctor_pretty_output_has_report_table_and_verdict():
    output = render_pretty(
        [
            Check("python", "ok", "Python detected"),
            Check("package:x", "error", "manifest invalid", fix="grave package validate x"),
        ],
        verbose=True,
    )
    assert "Gravewright Doctor" in output
    assert "Check" in output and "FIX" in output
    assert "package:x" in output
    assert "Not ready" in output
