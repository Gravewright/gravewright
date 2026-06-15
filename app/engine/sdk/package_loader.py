"""Load a single SDK package from disk into a validated in-memory shape.

Only SDK package manifests are loaded here — never legacy System/Module API
manifests. A package directory is the unit of installation; its ``manifest.json``
is read, parsed, modelled, and validated.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.engine.sdk.package_manifest import PackageManifest
from app.engine.sdk.package_manifest_validator import (
    PackageManifestValidation,
    validate_manifest,
)
from app.engine.sdk.package_paths import safe_join

MANIFEST_FILENAME = "manifest.json"


@dataclass
class LoadedPackage:
    package_dir: Path
    manifest: PackageManifest
    validation: PackageManifestValidation
    raw: dict

    @property
    def id(self) -> str:
        return self.manifest.id or self.package_dir.name

    @property
    def ok(self) -> bool:
        return self.validation.ok


def load_package(package_dir: Path) -> LoadedPackage:
    manifest_path = package_dir / MANIFEST_FILENAME
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raw = {}
        validation = PackageManifestValidation(errors=["sdk.validation.manifest_missing"])
        return LoadedPackage(package_dir, PackageManifest.from_dict(raw), validation, {})
    except (json.JSONDecodeError, OSError):
        raw = {}
        validation = PackageManifestValidation(errors=["sdk.validation.manifest_unreadable"])
        return LoadedPackage(package_dir, PackageManifest.from_dict(raw), validation, {})

    manifest = PackageManifest.from_dict(raw)
    validation = validate_manifest(raw)

    # Every declared path must resolve inside the package and exist on disk.
    for relative in manifest.referenced_paths():
        resolved = safe_join(package_dir, relative)
        if resolved is None:
            validation.add("sdk.validation.path_unsafe")
        elif not resolved.exists():
            validation.add("sdk.validation.file_missing")

    return LoadedPackage(package_dir, manifest, validation, raw if isinstance(raw, dict) else {})
