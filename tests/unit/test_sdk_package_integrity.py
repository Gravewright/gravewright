"""Phase 6 â€” package integrity migration.

The install registry stores a manifest hash and validation status; disk is the
runtime authority; the doctor detects drift between the stored snapshot/hash and
the on-disk manifest. The Alembic migration adds the integrity columns without
losing existing rows.
"""

from __future__ import annotations

import json

from sqlalchemy import create_engine, text

from app.engine.sdk import package_registry
from app.engine.sdk.package_doctor_service import PackageDoctorService
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk.package_integrity import compute_manifest_hash
from app.persistence.repositories.installed_package_repository import (
    InstalledPackageRepository,
)
from app.persistence.tables import installed_packages
from tests.conftest import install_system, seed_user


def _disk_hash(package_id: str) -> str:
    loaded = package_registry.load_by_package_id(package_id)
    return compute_manifest_hash(loaded.raw)


# --- schema ------------------------------------------------------------------


def test_installed_packages_schema_has_manifest_integrity_fields():
    columns = set(installed_packages.c.keys())
    assert {"manifest_hash", "last_validated_at", "last_validation_status"} <= columns


# --- hashing / validation ----------------------------------------------------


def test_manifest_hash_saved_on_install(db):
    gm = seed_user(email="integrity-install@test.com")
    install_system(gm, package_id="valid-ruleset")

    record = InstalledPackageRepository().get("valid-ruleset")
    assert record["manifest_hash"] == _disk_hash("valid-ruleset")
    assert record["last_validation_status"] == "valid"
    assert record["last_validated_at"] is not None


def test_enable_revalidates_manifest_from_disk(db):
    gm = seed_user(email="integrity-enable@test.com")
    svc = PackageInstallService()
    svc.install(package_id="valid-ruleset", user_id=gm)

    # Corrupt the stored hash, then enable: re-validation rewrites it from disk.
    InstalledPackageRepository().record_validation(
        package_id="valid-ruleset", manifest_hash="stale", last_validation_status="stale"
    )
    result = svc.enable(package_id="valid-ruleset")
    assert result.success

    record = InstalledPackageRepository().get("valid-ruleset")
    assert record["manifest_hash"] == _disk_hash("valid-ruleset")
    assert record["last_validation_status"] == "valid"


def test_runtime_uses_current_validated_manifest_not_stale_snapshot(db):
    gm = seed_user(email="integrity-runtime@test.com")
    install_system(gm, package_id="valid-ruleset")

    # Tamper with the stored snapshot; the runtime must still read from disk.
    InstalledPackageRepository().upsert(
        package_id="valid-ruleset",
        kind="ruleset",
        name="TAMPERED",
        version="9.9.9",
        status="enabled",
        package_dir="rulesets/valid-ruleset",
        manifest_json=json.dumps({"id": "valid-ruleset", "kind": "ruleset", "name": "TAMPERED"}),
        compatibility_status="compatible",
        validation_errors_json="[]",
        installed_by_user_id=gm,
        manifest_hash="bogus",
    )
    manifest = PackageInstallService().get_manifest("valid-ruleset")
    assert manifest is not None
    assert manifest.name != "TAMPERED"  # came from disk, not the tampered snapshot


def test_invalid_current_manifest_blocks_enable(db, monkeypatch):
    gm = seed_user(email="integrity-invalid@test.com")
    svc = PackageInstallService()
    svc.install(package_id="valid-ruleset", user_id=gm)

    from app.engine.sdk.package_loader import LoadedPackage
    from app.engine.sdk.package_manifest import PackageManifest
    from app.engine.sdk.package_manifest_validator import PackageManifestValidation
    from pathlib import Path

    invalid = LoadedPackage(
        package_dir=Path("x"),
        manifest=PackageManifest.from_dict({"id": "valid-ruleset"}),
        validation=PackageManifestValidation(errors=["sdk.validation.kind"]),
        raw={"id": "valid-ruleset"},
        kind_dir="rulesets",
    )
    monkeypatch.setattr(package_registry, "load_by_package_id", lambda pid, *a, **k: invalid)
    result = svc.enable(package_id="valid-ruleset")
    assert result.success is False


# --- doctor ------------------------------------------------------------------


def test_doctor_reports_stale_manifest_snapshot(db):
    gm = seed_user(email="integrity-stale@test.com")
    install_system(gm, package_id="valid-ruleset")

    # Snapshot + hash are mutually consistent but differ from disk -> stale.
    modified = {"id": "valid-ruleset", "kind": "ruleset", "name": "older"}
    InstalledPackageRepository().upsert(
        package_id="valid-ruleset",
        kind="ruleset",
        name="older",
        version="1.0.0",
        status="enabled",
        package_dir="rulesets/valid-ruleset",
        manifest_json=json.dumps(modified),
        compatibility_status="compatible",
        validation_errors_json="[]",
        installed_by_user_id=gm,
        manifest_hash=compute_manifest_hash(modified),
    )
    codes = {f.code for f in PackageDoctorService().audit()}
    assert "sdk.manifest.snapshot_stale" in codes


def test_doctor_reports_manifest_hash_mismatch(db):
    gm = seed_user(email="integrity-mismatch@test.com")
    install_system(gm, package_id="valid-ruleset")

    # Snapshot differs from disk but stored hash matches disk -> the stored
    # hash/snapshot pair is internally inconsistent (mismatch, not stale).
    InstalledPackageRepository().upsert(
        package_id="valid-ruleset",
        kind="ruleset",
        name="x",
        version="1.0.0",
        status="enabled",
        package_dir="rulesets/valid-ruleset",
        manifest_json=json.dumps({"id": "valid-ruleset", "kind": "ruleset", "name": "x"}),
        compatibility_status="compatible",
        validation_errors_json="[]",
        installed_by_user_id=gm,
        manifest_hash=_disk_hash("valid-ruleset"),
    )
    codes = {f.code for f in PackageDoctorService().audit()}
    assert "sdk.persistence.manifest_hash_mismatch" in codes


def test_missing_manifest_turns_package_status_error(db):
    gm = seed_user(email="integrity-missing@test.com")
    install_system(gm, package_id="valid-ruleset")
    # Forge a row for a package that does not exist on disk.
    InstalledPackageRepository().upsert(
        package_id="ghost-pkg",
        kind="addon",
        name="Ghost",
        version="1.0.0",
        status="enabled",
        package_dir="addons/ghost-pkg",
        manifest_json="{}",
        compatibility_status="compatible",
        validation_errors_json="[]",
        installed_by_user_id=gm,
    )
    item = PackageInstallService().get_details("ghost-pkg")
    assert item is not None
    assert item["status"] == "error"


# --- migration ---------------------------------------------------------------


def _load_migration(name: str):
    """Import a single migration module by file path.

    The full Alembic chain cannot be replayed from base in this repo (a legacy
    migration imports a table symbol that 0007 later removed), so we exercise the
    target migration's ``upgrade()`` in isolation against a bound Operations
    context.
    """
    import importlib.util
    from pathlib import Path

    path = Path("migrations/versions") / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_preserves_existing_installed_packages(tmp_path):
    from alembic.operations import Operations
    from alembic.runtime.migration import MigrationContext

    db_path = tmp_path / "mig.sqlite3"
    eng = create_engine(f"sqlite:///{db_path}")

    # Build installed_packages at the pre-0008 (0007) shape and seed a row.
    with eng.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE installed_packages ("
                " id VARCHAR(64) PRIMARY KEY, kind VARCHAR(191) NOT NULL,"
                " name VARCHAR(191) NOT NULL DEFAULT '', version VARCHAR(191) NOT NULL DEFAULT '',"
                " status VARCHAR(191) NOT NULL DEFAULT 'installed', package_dir TEXT NOT NULL,"
                " manifest_json TEXT NOT NULL, compatibility_status VARCHAR(191) NOT NULL DEFAULT 'unverified',"
                " validation_errors_json TEXT NOT NULL DEFAULT '[]', package_sha256 VARCHAR(64),"
                " installed_by_user_id VARCHAR(64), installed_at INTEGER NOT NULL,"
                " updated_at INTEGER NOT NULL, enabled_at INTEGER, disabled_at INTEGER)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO installed_packages "
                "(id, kind, name, version, status, package_dir, manifest_json, installed_at, updated_at) "
                "VALUES ('keep-me','addon','Keep','1.0.0','installed','addons/keep-me','{}', 1, 1)"
            )
        )

    # Run only the 0008 migration's upgrade() against this connection.
    migration = _load_migration("0008_package_manifest_integrity.py")
    with eng.begin() as conn:
        ctx = MigrationContext.configure(conn)
        migration.op = Operations(ctx)
        migration.upgrade()

    with eng.connect() as conn:
        rows = conn.execute(
            text("SELECT id, manifest_hash, last_validation_status FROM installed_packages")
        ).mappings().all()
    eng.dispose()

    assert len(rows) == 1
    assert rows[0]["id"] == "keep-me"  # existing row preserved
    # New columns exist and default to NULL for the pre-existing row.
    assert rows[0]["manifest_hash"] is None
    assert rows[0]["last_validation_status"] is None
