"""``grave.lock.json`` — a reproducible record of what is installed.

The lockfile snapshots the core/SDK versions and every installed package (id,
kind, version, status, source, checksum, install time). It lets an operator
reproduce an install and lets `grave backup`/`restore` and (later) `grave update`
reason about drift. It is data-only — generating it never mutates the database.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from app.config import config
from app.helpers.env import PROJECT_ROOT

LOCKFILE_VERSION = 1


def default_lock_path() -> Path:
    return PROJECT_ROOT / "grave.lock.json"


def _manifest_checksum(package_dir: str) -> str | None:
    """sha256 of the package's on-disk manifest.json (integrity reference)."""
    manifest = Path(config.data_dir) / "packages" / package_dir / "manifest.json"
    if not manifest.is_file():
        return None
    return hashlib.sha256(manifest.read_bytes()).hexdigest()


def build_lock() -> dict:
    from app.persistence.repositories.installed_package_repository import (
        InstalledPackageRepository,
    )

    records = sorted(InstalledPackageRepository().list_all(), key=lambda r: r["id"])
    packages = [
        {
            "id": r["id"],
            "kind": r["kind"],
            "version": r["version"],
            "status": r["status"],
            "source": "bundled",
            "checksum": r.get("package_sha256") or _manifest_checksum(r["package_dir"]),
            "installed_at": r.get("installed_at"),
        }
        for r in records
    ]
    return {
        "lockfile_version": LOCKFILE_VERSION,
        "core_version": config.gravewright_version,
        "sdk_version": config.system_api_version,
        "generated_at": int(time.time()),
        "packages": packages,
    }


def write_lock(path: Path | None = None) -> dict:
    payload = build_lock()
    target = path or default_lock_path()
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
