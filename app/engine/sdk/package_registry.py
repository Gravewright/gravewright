"""Discover and load SDK packages from the configured data directory.

Packages live under ``<GRAVEWRIGHT_DATA_DIR>/packages/<package-id>/``. Discovery
only considers directories whose name is a safe package id and that contain a
``manifest.json``.
"""

from __future__ import annotations

from pathlib import Path

from app.config import config
from app.engine.sdk.package_loader import MANIFEST_FILENAME, LoadedPackage, load_package
from app.engine.sdk.package_paths import package_id_is_safe

PACKAGES_DIR = Path(config.data_dir) / "packages"


def _base_dir(packages_dir: Path | None) -> Path:
    return packages_dir if packages_dir is not None else PACKAGES_DIR


def discover_package_dirs(packages_dir: Path | None = None) -> list[Path]:
    base = _base_dir(packages_dir)
    if not base.is_dir():
        return []
    found: list[Path] = []
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        if not package_id_is_safe(child.name):
            continue
        if not (child / MANIFEST_FILENAME).is_file():
            continue
        found.append(child)
    return found


def load_all(packages_dir: Path | None = None) -> list[LoadedPackage]:
    return [load_package(path) for path in discover_package_dirs(packages_dir)]


def load_by_package_id(
    package_id: str, packages_dir: Path | None = None
) -> LoadedPackage | None:
    if not package_id_is_safe(package_id):
        return None
    base = _base_dir(packages_dir)
    package_dir = base / package_id
    if not (package_dir / MANIFEST_FILENAME).is_file():
        return None
    return load_package(package_dir)
