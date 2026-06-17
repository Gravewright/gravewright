"""``grave backup`` / ``grave restore`` — first-class safety net.

A backup is a single ``.zip`` containing the SQLite database, a ``grave.lock.json``
snapshot, and optionally the ``storage/`` assets (``--include-assets``) and the
installed packages (``--include-packages``). With ``--include-packages`` the
archive also carries ``data/packages/`` and the managed ``data/storage/packages/``
storage, so a campaign can be restored even if a package is no longer
reinstallable from its source; without it, packages are reinstalled from
``data/packages`` / the lockfile.

Restore is destructive, so it refuses to run without ``--yes`` (and offers
``--dry-run``); it writes a ``*.pre-restore`` safety copy of the current database
before overwriting it. Always test ``grave restore`` on a copy before relying on
it for an upgrade.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import tempfile
import time
import zipfile
from pathlib import Path

from app.cli.exit_codes import EXIT_DOCTOR_ERROR, EXIT_OK, EXIT_UNSAFE
from app.config import config
from app.helpers.env import PROJECT_ROOT
from app.engine.sdk import package_registry
from app.engine.sdk.package_manifest import SDK_VERSION

MANIFEST_NAME = "backup.json"
DB_NAME = "database.sqlite3"
LOCK_NAME = "grave.lock.json"
ASSETS_PREFIX = "storage/"
PACKAGES_PREFIX = "data/packages/"
PACKAGE_STORAGE_PREFIX = "data/storage/packages/"
BACKUP_FORMAT = 1


def _storage_root() -> Path:
    return (PROJECT_ROOT / "storage").resolve()


def default_backup_name() -> str:
    return f"gravewright-backup-{time.strftime('%Y%m%d-%H%M%S')}.zip"


def _sqlite_source() -> Path | None:
    """The live SQLite file, or None for a non-SQLite / memory backend."""
    from app.persistence.database import _backend, effective_sqlite_path

    if _backend() != "sqlite":
        return None
    path = effective_sqlite_path()
    if path == ":memory:":
        return None
    return Path(path)


def _snapshot_sqlite(src: Path, dst: Path) -> None:
    """Consistent copy via SQLite's online backup API (safe during writes)."""
    src.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(str(src))
    try:
        dest = sqlite3.connect(str(dst))
        try:
            source.backup(dest)
        finally:
            dest.close()
    finally:
        source.close()


def _integrity_ok(db_path: Path) -> bool:
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        conn.close()


# --- backup -----------------------------------------------------------------


def create_backup(
    *,
    out: Path,
    include_assets: bool,
    include_packages: bool = False,
    verify: bool,
) -> tuple[int, dict]:
    src = _sqlite_source()
    if src is None:
        print("ERROR  backup currently supports the SQLite backend only.")
        return EXIT_DOCTOR_ERROR, {}
    if not src.is_file():
        print(f"ERROR  database file not found: {src}")
        print("FIX    grave run (initializes the database) first.")
        return EXIT_DOCTOR_ERROR, {}

    from app.cli.lockfile import build_lock

    manifest = {
        "backup_format": BACKUP_FORMAT,
        "created_at": int(time.time()),
        "core_version": config.gravewright_version,
        "sdk_version": SDK_VERSION,
        "include_assets": include_assets,
        "include_packages": include_packages,
    }

    with tempfile.TemporaryDirectory() as tmp:
        db_copy = Path(tmp) / DB_NAME
        _snapshot_sqlite(src, db_copy)

        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2, sort_keys=True))
            zf.writestr(LOCK_NAME, json.dumps(build_lock(), indent=2, sort_keys=True))
            zf.write(db_copy, DB_NAME)
            asset_count = 0
            if include_assets and _storage_root().is_dir():
                for path in sorted(_storage_root().rglob("*")):
                    if path.is_file():
                        zf.write(path, ASSETS_PREFIX + str(path.relative_to(_storage_root())))
                        asset_count += 1
            package_count = 0
            if include_packages:
                package_count += _write_tree(
                    zf,
                    package_registry.PACKAGES_DIR,
                    PACKAGES_PREFIX,
                )
                package_count += _write_tree(
                    zf,
                    package_registry.STORAGE_PACKAGES_DIR,
                    PACKAGE_STORAGE_PREFIX,
                )

    if verify and not _verify_backup(out):
        print(f"ERROR  backup verification failed: {out}")
        return EXIT_DOCTOR_ERROR, manifest

    print(f"OK     Backup written: {out}")
    if include_assets:
        print(f"       assets included: {asset_count} file(s)")
    if include_packages:
        print(f"       package files included: {package_count} file(s)")
    return EXIT_OK, manifest


def _write_tree(zf: zipfile.ZipFile, root: Path, prefix: str) -> int:
    if not root.is_dir():
        return 0
    count = 0
    for path in sorted(root.rglob("*")):
        if path.is_file():
            zf.write(path, prefix + str(path.relative_to(root)).replace("\\", "/"))
            count += 1
    return count


def _verify_backup(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
            if not {MANIFEST_NAME, DB_NAME, LOCK_NAME}.issubset(names):
                return False
            json.loads(zf.read(LOCK_NAME))
            with tempfile.TemporaryDirectory() as tmp:
                db = Path(tmp) / DB_NAME
                db.write_bytes(zf.read(DB_NAME))
                return _integrity_ok(db)
    except (zipfile.BadZipFile, KeyError, ValueError, sqlite3.Error):
        return False


# --- restore ----------------------------------------------------------------


def _read_manifest(path: Path) -> dict | None:
    try:
        with zipfile.ZipFile(path) as zf:
            return json.loads(zf.read(MANIFEST_NAME))
    except (zipfile.BadZipFile, KeyError, ValueError):
        return None


def restore_backup(*, path: Path, dry_run: bool, yes: bool) -> int:
    if not path.is_file():
        print(f"ERROR  backup file not found: {path}")
        return EXIT_DOCTOR_ERROR
    manifest = _read_manifest(path)
    if manifest is None or not _verify_backup(path):
        print(f"ERROR  not a valid Gravewright backup: {path}")
        return EXIT_DOCTOR_ERROR

    target = _sqlite_source()
    if target is None:
        print("ERROR  restore currently supports the SQLite backend only.")
        return EXIT_DOCTOR_ERROR

    print(f"Backup created: {time.ctime(manifest.get('created_at', 0))}")
    print(f"Core version:   {manifest.get('core_version')}")
    print(f"Includes assets: {manifest.get('include_assets')}")
    print(f"Includes packages: {manifest.get('include_packages')}")
    print(f"Target database: {target}")
    if manifest.get("include_assets"):
        print(f"Target assets:   {_storage_root()}")

    if dry_run:
        print("\nDry run — nothing was changed.")
        return EXIT_OK
    if not yes:
        print("\nRefusing to overwrite your data without confirmation.")
        print("FIX    re-run with --yes (a *.pre-restore safety copy is kept), or --dry-run.")
        return EXIT_UNSAFE

    # Close any open DB connections before overwriting the file on disk (a
    # no-op in a fresh CLI process; matters if the engine was already used).
    try:
        from app.persistence import engine as _engine

        _engine.reset_engine()
    except Exception:  # noqa: BLE001
        pass

    with zipfile.ZipFile(path) as zf:
        if target.is_file():
            safety = target.with_suffix(target.suffix + ".pre-restore")
            shutil.copy2(target, safety)
            print(f"       previous database saved to {safety}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(zf.read(DB_NAME))
        # Drop stale WAL/SHM sidecars so SQLite doesn't replay pre-restore changes
        # over the restored file on next open.
        for sidecar in (f"{target}-wal", f"{target}-shm"):
            Path(sidecar).unlink(missing_ok=True)

        if manifest.get("include_assets"):
            root = _storage_root()
            for name in zf.namelist():
                if name.startswith(ASSETS_PREFIX) and not name.endswith("/"):
                    dest = root / name[len(ASSETS_PREFIX) :]
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(zf.read(name))
        if manifest.get("include_packages"):
            _restore_tree(zf, PACKAGES_PREFIX, package_registry.PACKAGES_DIR)
            _restore_tree(zf, PACKAGE_STORAGE_PREFIX, package_registry.STORAGE_PACKAGES_DIR)

    print("OK     Restore complete. Restart the server: grave run")
    return EXIT_OK


def _restore_tree(zf: zipfile.ZipFile, prefix: str, root: Path) -> None:
    root = root.resolve()
    for name in zf.namelist():
        if not name.startswith(prefix) or name.endswith("/"):
            continue
        relative = Path(name[len(prefix) :])
        dest = (root / relative).resolve()
        if root != dest and root not in dest.parents:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(zf.read(name))
