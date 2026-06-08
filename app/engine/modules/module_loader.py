"""Loads module package directories into validated, typed manifests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.config import config
from app.engine.modules.module_manifest import ModuleManifest
from app.engine.modules.module_manifest_validator import MAX_ASSET_BYTES, ManifestValidation, validate_manifest
from app.engine.systems.system_loader import safe_join

DATA_DIR = Path(config.data_dir)
MODULES_DIR = DATA_DIR / "modules"
MAX_CONTENT_PACK_BYTES = 2_000_000


@dataclass(frozen=True)
class LoadedModule:
    package_id: str
    package_dir: Path
    manifest: ModuleManifest | None
    validation: ManifestValidation
    manifest_json: str


def load_package(package_dir: Path) -> LoadedModule:
    package_id = package_dir.name
    manifest_path = package_dir / "manifest.json"

    if not manifest_path.is_file():
        validation = ManifestValidation(errors=["inside.modules.validation.manifest_missing"])
        return LoadedModule(package_id, package_dir, None, validation, "")

    raw_text = manifest_path.read_text(encoding="utf-8")
    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError:
        validation = ManifestValidation(errors=["inside.modules.validation.manifest_invalid_json"])
        return LoadedModule(package_id, package_dir, None, validation, raw_text)

    validation = validate_manifest(raw)
    manifest = ModuleManifest.from_dict(raw)

    entrypoint_paths = set(manifest.entrypoint_paths())
    content_pack_paths = {str(pack.get("path")) for pack in manifest.content_packs if isinstance(pack.get("path"), str)}
    for relative in manifest.referenced_paths():
        resolved = safe_join(package_dir, relative)
        if resolved is None:
            validation.add("inside.modules.validation.path_unsafe")
        elif not resolved.exists():
            validation.add("inside.modules.validation.file_missing")
        elif relative in entrypoint_paths and resolved.is_file() and resolved.stat().st_size > MAX_ASSET_BYTES:
            validation.add("inside.modules.validation.asset_too_large")
        elif relative in content_pack_paths and resolved.is_file() and resolved.stat().st_size > MAX_CONTENT_PACK_BYTES:
            validation.add("inside.modules.validation.content_pack_too_large")

    return LoadedModule(package_id, package_dir, manifest, validation, raw_text)
