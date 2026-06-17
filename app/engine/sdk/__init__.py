"""Gravewright SDK engine — the only supported extension model.

Everything installable is a *Gravewright package* described by a single manifest
contract (``schemas/gravewright-package-v1.schema.json``). This package contains
the manifest model, validator, path-safety helpers, loader, registry, and the
services that install, activate, and serve packages.
"""

from app.engine.sdk.package_loader import LoadedPackage, load_package
from app.engine.sdk.package_manifest import PackageKind, PackageManifest
from app.engine.sdk.package_manifest_validator import (
    PackageManifestValidation,
    validate_manifest,
)
from app.engine.sdk.package_registry import (
    PACKAGES_DIR,
    discover_package_dirs,
    load_all,
    load_by_package_id,
)

__all__ = [
    "LoadedPackage",
    "PACKAGES_DIR",
    "PackageKind",
    "PackageManifest",
    "PackageManifestValidation",
    "discover_package_dirs",
    "load_all",
    "load_by_package_id",
    "load_package",
    "validate_manifest",
]
