"""Discovers installable module packages under <data_dir>/modules."""

from __future__ import annotations

from pathlib import Path
import re

from app.engine.modules import module_loader
from app.engine.modules.module_loader import LoadedModule, load_package



_PACKAGE_ID_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

def _package_id_safe(package_id: str) -> bool:
    return bool(_PACKAGE_ID_PATTERN.match(package_id or ""))

def _modules_dir(modules_dir: Path | None) -> Path:
    return modules_dir if modules_dir is not None else module_loader.MODULES_DIR


def discover_package_dirs(modules_dir: Path | None = None) -> list[Path]:
    base = _modules_dir(modules_dir)
    if not base.is_dir():
        return []
    return [
        child
        for child in sorted(base.iterdir())
        if child.is_dir() and _package_id_safe(child.name) and (child / "manifest.json").is_file()
    ]


def load_all(modules_dir: Path | None = None) -> list[LoadedModule]:
    return [load_package(pkg_dir) for pkg_dir in discover_package_dirs(modules_dir)]


def load_by_package_id(package_id: str, modules_dir: Path | None = None) -> LoadedModule | None:
    if not _package_id_safe(package_id):
        return None
    base = _modules_dir(modules_dir)
    package_dir = base / package_id
    if not (package_dir.is_dir() and (package_dir / "manifest.json").is_file()):
        return None
    return load_package(package_dir)
