from __future__ import annotations

import json
import zipfile

from app.cli import backup as backup_mod
from app.cli import main
from app.engine.sdk.package_install_service import PackageInstallService
from tests.conftest import install_system, seed_user


def _reset_engine() -> None:
    # Simulate the "restart the server" step so the next query reads the restored file.
    from app.persistence import engine as engine_module

    engine_module.reset_engine()


def test_lock_writes_snapshot(db, tmp_path, capsys):
    install_system(seed_user(email="lock@test.com"), package_id="dnd5e")
    out = tmp_path / "grave.lock.json"

    assert main(["lock", "-o", str(out)]) == 0
    payload = json.loads(out.read_text())
    pkg = {p["id"]: p for p in payload["packages"]}["dnd5e"]
    assert pkg["status"] == "enabled"
    assert pkg["checksum"] and len(pkg["checksum"]) == 64
    assert payload["core_version"]


def test_backup_creates_verifiable_zip(db, tmp_path, capsys):
    install_system(seed_user(email="bk@test.com"), package_id="dnd5e")
    out = tmp_path / "bk.zip"

    assert main(["backup", "-o", str(out), "--verify"]) == 0
    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
    assert {"backup.json", "database.sqlite3", "grave.lock.json"}.issubset(names)


def test_backup_include_assets(db, tmp_path, monkeypatch, capsys):
    assets = tmp_path / "storage"
    (assets / "uploads").mkdir(parents=True)
    (assets / "uploads" / "map.png").write_bytes(b"PNGDATA")
    monkeypatch.setattr(backup_mod, "_storage_root", lambda: assets)
    install_system(seed_user(email="bk-assets@test.com"), package_id="dnd5e")
    out = tmp_path / "bk.zip"

    assert main(["backup", "-o", str(out), "--include-assets"]) == 0
    with zipfile.ZipFile(out) as zf:
        assert "storage/uploads/map.png" in zf.namelist()


def test_restore_roundtrip_restores_removed_package(db, tmp_path, capsys):
    install_system(seed_user(email="rt@test.com"), package_id="dnd5e")
    out = tmp_path / "bk.zip"
    assert main(["backup", "-o", str(out)]) == 0

    assert main(["package", "remove", "dnd5e", "--force"]) == 0
    assert PackageInstallService().get("dnd5e") is None

    assert main(["restore", str(out), "--yes"]) == 0
    _reset_engine()
    assert PackageInstallService().get("dnd5e")["status"] == "enabled"


def test_restore_refuses_without_yes(db, tmp_path, capsys):
    install_system(seed_user(email="ry@test.com"), package_id="dnd5e")
    out = tmp_path / "bk.zip"
    assert main(["backup", "-o", str(out)]) == 0
    main(["package", "remove", "dnd5e", "--force"])

    assert main(["restore", str(out)]) == 3  # EXIT_UNSAFE
    _reset_engine()
    assert PackageInstallService().get("dnd5e") is None  # unchanged


def test_restore_dry_run_changes_nothing(db, tmp_path, capsys):
    install_system(seed_user(email="rd@test.com"), package_id="dnd5e")
    out = tmp_path / "bk.zip"
    assert main(["backup", "-o", str(out)]) == 0
    main(["package", "remove", "dnd5e", "--force"])

    assert main(["restore", str(out), "--dry-run"]) == 0
    assert "Dry run" in capsys.readouterr().out
    _reset_engine()
    assert PackageInstallService().get("dnd5e") is None


def test_restore_rejects_invalid_file(db, tmp_path, capsys):
    bogus = tmp_path / "nope.zip"
    bogus.write_bytes(b"not a zip")
    assert main(["restore", str(bogus), "--yes"]) == 1
    assert "not a valid Gravewright backup" in capsys.readouterr().out
