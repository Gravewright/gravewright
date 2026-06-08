"""Loads a system *package* directory into a validated, typed form.

A package is a directory containing ``manifest.json`` plus the files it
references. The loader parses and validates the manifest, then confirms every
referenced path resolves *inside* the package (no traversal) and exists.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.config import config
from app.engine.systems.system_manifest import SystemManifest
from app.engine.systems.system_manifest_validator import ManifestValidation, validate_manifest

                                                                               
                                                                                    
DATA_DIR = Path(config.data_dir)
SYSTEMS_DIR = DATA_DIR / "systems"
MODULES_DIR = DATA_DIR / "modules"


@dataclass(frozen=True)
class LoadedSystem:
    package_id: str
    package_dir: Path
    manifest: SystemManifest | None
    validation: ManifestValidation
    manifest_json: str


def safe_join(base: Path, relative: str) -> Path | None:
    """Resolve ``relative`` under ``base``; return None if it escapes the base."""
    if not relative:
        return None
    base = base.resolve()
    candidate = (base / relative).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        return None
    return candidate


def load_package(package_dir: Path) -> LoadedSystem:
    package_id = package_dir.name
    manifest_path = package_dir / "manifest.json"

    if not manifest_path.is_file():
        validation = ManifestValidation(errors=["inside.systems.validation.manifest_missing"])
        return LoadedSystem(package_id, package_dir, None, validation, "")

    raw_text = manifest_path.read_text(encoding="utf-8")
    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError:
        validation = ManifestValidation(errors=["inside.systems.validation.manifest_invalid_json"])
        return LoadedSystem(package_id, package_dir, None, validation, raw_text)

    validation = validate_manifest(raw)
    manifest = SystemManifest.from_dict(raw)

                                                                        
    for relative in manifest.referenced_paths():
        resolved = safe_join(package_dir, relative)
        if resolved is None:
            validation.add("inside.systems.validation.path_unsafe")
        elif not resolved.exists():
            validation.add("inside.systems.validation.file_missing")

    return LoadedSystem(package_id, package_dir, manifest, validation, raw_text)
