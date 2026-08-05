"""Discover and load SDK packages from the configured data directory.

The universal layout groups packages by kind:
``<DATA_DIR>/packages/{kind_plural}/{id}/``. Discovery also keeps read-only
compatibility with the legacy flat layout (``<DATA_DIR>/packages/{id}/``) so
``grave doctor`` can report and guide migrations instead of silently ignoring
old package directories. Loading validates whether ``manifest.json`` exists,
which lets doctor surface broken package directories.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config import config
from app.engine.sdk.package_loader import LoadedPackage, load_package
from app.engine.sdk.package_manifest import DIRECTORY_TO_KIND, KIND_TO_DIRECTORY
from app.engine.sdk.package_paths import package_id_is_safe

PACKAGES_DIR = Path(config.data_dir) / "packages"
STORAGE_PACKAGES_DIR = Path(config.data_dir) / "storage" / "packages"

_KIND_DIRS = frozenset(DIRECTORY_TO_KIND)


def package_dir_for(kind: str, package_id: str) -> Path | None:
    """The grouped package directory for a validated ``(kind, id)``.

    ``None`` when the kind is unknown or the id is unsafe — callers must derive
    package/storage paths only from a validated kind and id, never from
    attacker-controlled input.
    """
    kind_dir = KIND_TO_DIRECTORY.get(kind)
    if kind_dir is None or not package_id_is_safe(package_id):
        return None
    return PACKAGES_DIR / kind_dir / package_id


def storage_dir_for(kind: str, package_id: str) -> Path | None:
    """The managed storage root for a validated ``(kind, id)`` (Phase 7)."""
    kind_dir = KIND_TO_DIRECTORY.get(kind)
    if kind_dir is None or not package_id_is_safe(package_id):
        return None
    return STORAGE_PACKAGES_DIR / kind_dir / package_id


@dataclass(frozen=True)
class PackageLocation:
    package_dir: Path
    package_id: str
    kind_dir: str | None  # the kind_plural root the package was discovered under


def _base_dir(packages_dir: Path | None) -> Path:
    return packages_dir if packages_dir is not None else PACKAGES_DIR


def _locations(base: Path) -> list[PackageLocation]:
    """All discoverable package locations under ``base``."""
    if not base.is_dir():
        return []
    found: list[PackageLocation] = []
    seen: set[Path] = set()

    # Universal grouped layout: data/packages/{kind_plural}/{id}.
    # Do not require manifest.json during discovery: a directory under a known
    # kind root is an operator intent to install/use a package. If the manifest
    # is missing, load_package() returns sdk.validation.manifest_missing and
    # doctor surfaces the broken package instead of hiding it.
    for kind_dir in sorted(_KIND_DIRS):
        kind_root = base / kind_dir
        if not kind_root.is_dir():
            continue
        for child in sorted(kind_root.iterdir()):
            if not child.is_dir() or not package_id_is_safe(child.name):
                continue
            found.append(PackageLocation(child, child.name, kind_dir))
            seen.add(child.resolve())

    # Legacy flat layout: data/packages/{id}. Keep discovery read-compatible so
    # operators get an explicit doctor finding instead of a missing package.
    for child in sorted(base.iterdir()):
        if child.name in _KIND_DIRS:
            continue
        if not child.is_dir() or not package_id_is_safe(child.name):
            continue
        try:
            resolved = child.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        found.append(PackageLocation(child, child.name, None))

    return found


def discover_package_dirs(packages_dir: Path | None = None) -> list[Path]:
    return [loc.package_dir for loc in _locations(_base_dir(packages_dir))]


def load_all(packages_dir: Path | None = None) -> list[LoadedPackage]:
    return [
        load_package(loc.package_dir, expected_id=loc.package_id, expected_kind_root=loc.kind_dir)
        for loc in _locations(_base_dir(packages_dir))
    ]


def load_by_package_id(
    package_id: str, packages_dir: Path | None = None
) -> LoadedPackage | None:
    if not package_id_is_safe(package_id):
        return None
    base = _base_dir(packages_dir)

    # As with load_all(), return a LoadedPackage for existing directories even
    # when manifest.json is missing so package-specific doctor/validate flows can
    # report the error.
    for kind_dir in sorted(_KIND_DIRS):
        candidate = base / kind_dir / package_id
        if candidate.is_dir():
            return load_package(
                candidate, expected_id=package_id, expected_kind_root=kind_dir
            )
    candidate = base / package_id
    if candidate.is_dir():
        return load_package(candidate, expected_id=package_id, expected_kind_root=None)
    return None
