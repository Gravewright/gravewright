"""Phase 7B — storage lifecycle: doctor orphan detection and backup/export.

Removing a package preserves its managed storage; the doctor then flags that
storage as orphaned. Export excludes managed storage by default; backup includes
it.
"""

from __future__ import annotations

from app.engine.sdk import package_registry
from app.engine.sdk.package_backup import backup_includes, export_includes
from app.engine.sdk.package_doctor_service import PackageDoctorService


def test_package_export_excludes_storage_by_default():
    includes = export_includes("addon", "my-addon")
    assert len(includes) == 1
    assert includes[0].as_posix().endswith("packages/addons/my-addon")
    assert all("storage" not in p.as_posix() for p in includes)


def test_package_backup_includes_storage():
    includes = backup_includes("addon", "my-addon")
    posix = [p.as_posix() for p in includes]
    assert any(p.endswith("packages/addons/my-addon") for p in posix)
    assert any("storage/packages/addons/my-addon" in p for p in posix)


def test_doctor_reports_orphaned_storage(db, monkeypatch, tmp_path):
    # A storage directory with no matching installed package is orphaned.
    storage_root = tmp_path / "storage" / "packages"
    monkeypatch.setattr(package_registry, "STORAGE_PACKAGES_DIR", storage_root)
    (storage_root / "addons" / "ghost-addon" / "global").mkdir(parents=True)
    (storage_root / "addons" / "ghost-addon" / "global" / "data.sqlite3").write_text("x")

    codes = {f.code for f in PackageDoctorService().audit()}
    assert "sdk.storage.orphaned_storage" in codes


def test_doctor_ignores_storage_for_installed_package(db, monkeypatch, tmp_path):
    from tests.conftest import install_system, seed_user

    storage_root = tmp_path / "storage" / "packages"
    monkeypatch.setattr(package_registry, "STORAGE_PACKAGES_DIR", storage_root)
    gm = seed_user(email="storage-lifecycle@test.com")
    install_system(gm, package_id="valid-ruleset")
    (storage_root / "rulesets" / "valid-ruleset" / "global").mkdir(parents=True)

    codes = {f.code for f in PackageDoctorService().audit()}
    assert "sdk.storage.orphaned_storage" not in codes
