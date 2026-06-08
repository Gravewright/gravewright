"""Discovers installable system packages on disk.

Packages live under ``<data_dir>/systems/<package_id>/manifest.json`` (the data
dir is configurable via ``GRAVEWRIGHT_DATA_DIR``). This module only *reads* —
installation state is persisted by
:mod:`app.engine.systems.system_install_service`.
"""

from __future__ import annotations

from pathlib import Path

from app.engine.systems import system_loader
from app.engine.systems.system_loader import LoadedSystem, load_package


def _systems_dir(systems_dir: Path | None) -> Path:
                                                                               
    return systems_dir if systems_dir is not None else system_loader.SYSTEMS_DIR


def discover_package_dirs(systems_dir: Path | None = None) -> list[Path]:
    base = _systems_dir(systems_dir)
    if not base.is_dir():
        return []
    return [
        child
        for child in sorted(base.iterdir())
        if child.is_dir() and (child / "manifest.json").is_file()
    ]


def load_all(systems_dir: Path | None = None) -> list[LoadedSystem]:
    return [load_package(pkg_dir) for pkg_dir in discover_package_dirs(systems_dir)]


def load_by_package_id(package_id: str, systems_dir: Path | None = None) -> LoadedSystem | None:
    base = _systems_dir(systems_dir)
    package_dir = base / package_id
    if not (package_dir.is_dir() and (package_dir / "manifest.json").is_file()):
        return None
    return load_package(package_dir)
