"""Safe ZIP package installation for the SDK package system.

Uploaded archives are treated as untrusted input. The installer validates the
ZIP member table before extraction (size caps, no absolute paths, no ``..``, no
symlinks), normalizes a single root folder if present, extracts into a hidden
staging directory under the packages root, validates the manifest/package from
staging, and only then promotes the staged tree into the canonical grouped
location ``<packages>/{kind_plural}/{id}``.

This module is filesystem-only: it never touches the database. The conflict and
state policy (already installed, enabled, active in a campaign) lives in
``PackageInstallService.install_uploaded_archive``.
"""

from __future__ import annotations

import io
import shutil
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from app.engine.sdk import package_registry
from app.engine.sdk.package_compatibility import COMPAT_INCOMPATIBLE
from app.engine.sdk.package_loader import load_package
from app.engine.sdk.package_manifest import KIND_TO_DIRECTORY
from app.engine.sdk.package_paths import package_id_is_safe

MAX_PACKAGE_BYTES = 25 * 1024 * 1024
MAX_ZIP_ENTRIES = 2048
MAX_UNCOMPRESSED_BYTES = 80 * 1024 * 1024
MAX_PACKAGE_FILE_BYTES = 20 * 1024 * 1024
MAX_MANIFEST_BYTES = 1 * 1024 * 1024

ERROR_BAD_ZIP = "inside.addons.errors.package_invalid"
ERROR_TOO_LARGE = "inside.addons.errors.package_too_large"
ERROR_UNSAFE = "inside.addons.errors.package_unsafe"
ERROR_MANIFEST = "sdk.errors.invalid_manifest"
ERROR_INCOMPATIBLE = "sdk.errors.incompatible"


@dataclass
class StagedPackage:
    """Result of extracting an uploaded archive into a staging directory."""

    success: bool
    staging_dir: Path | None = None
    package_id: str | None = None
    kind: str | None = None
    error_key: str | None = None
    validation_errors: tuple[str, ...] = field(default_factory=tuple)


def _zip_member_is_symlink(info: zipfile.ZipInfo) -> bool:
    return ((info.external_attr >> 16) & 0o170000) == 0o120000


def _safe_member_name(name: str) -> bool:
    if not name or "\x00" in name or "\\" in name:
        return False
    if name.startswith("/") or name.startswith("../") or name == "..":
        return False
    if ":" in name.split("/", 1)[0]:
        return False
    parts = [part for part in name.split("/") if part]
    return bool(parts) and ".." not in parts


def _normalized_infos(zf: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    infos = [info for info in zf.infolist() if not info.filename.endswith("/")]
    return [info for info in infos if not info.filename.startswith("__MACOSX/")]


def _root_prefix(infos: list[zipfile.ZipInfo]) -> str | None:
    """Return the single top-level folder prefix, or "" when manifest is at root.

    ``None`` means the archive has no discoverable ``manifest.json`` at the root
    or under a single top-level folder.
    """
    names = [info.filename for info in infos]
    if "manifest.json" in names:
        return ""
    roots = {name.split("/", 1)[0] for name in names if "/" in name}
    if len(roots) != 1:
        return None
    root = next(iter(roots))
    prefix = f"{root}/"
    return prefix if f"{prefix}manifest.json" in names else None


def _validate_zip_table(zf: zipfile.ZipFile) -> tuple[str | None, str | None]:
    infos = _normalized_infos(zf)
    if not infos:
        return None, ERROR_BAD_ZIP
    if len(infos) > MAX_ZIP_ENTRIES:
        return None, ERROR_TOO_LARGE
    total = 0
    for info in infos:
        name = info.filename
        if not _safe_member_name(name) or _zip_member_is_symlink(info):
            return None, ERROR_UNSAFE
        if info.file_size > MAX_PACKAGE_FILE_BYTES:
            return None, ERROR_TOO_LARGE
        total += info.file_size
        if total > MAX_UNCOMPRESSED_BYTES:
            return None, ERROR_TOO_LARGE
        if name.endswith("manifest.json") and info.file_size > MAX_MANIFEST_BYTES:
            return None, ERROR_TOO_LARGE
    prefix = _root_prefix(infos)
    if prefix is None:
        return None, ERROR_MANIFEST
    return prefix, None


def _extract_normalized(zf: zipfile.ZipFile, *, prefix: str, staging_dir: Path) -> None:
    staging_dir.mkdir(parents=True, exist_ok=False)
    for info in _normalized_infos(zf):
        name = info.filename
        if prefix:
            if not name.startswith(prefix):
                continue
            relative = name[len(prefix):]
        else:
            relative = name
        if not relative:
            continue
        if not _safe_member_name(relative):
            raise ValueError(ERROR_UNSAFE)
        destination = staging_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info, "r") as source, destination.open("wb") as target:
            shutil.copyfileobj(source, target)


def discard(path: Path | None) -> None:
    """Best-effort removal of a staging/backup directory."""
    if path is None or not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


def stage_archive(*, filename: str, data: bytes) -> StagedPackage:
    """Validate and extract an uploaded ZIP into a staging directory.

    The caller is responsible for promoting the staging directory with
    ``promote`` or removing it with ``discard``.
    """
    if not filename.lower().endswith(".zip") or not data:
        return StagedPackage(success=False, error_key=ERROR_BAD_ZIP)
    if len(data) > MAX_PACKAGE_BYTES:
        return StagedPackage(success=False, error_key=ERROR_TOO_LARGE)

    packages_dir = package_registry.PACKAGES_DIR
    packages_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = packages_dir / f".upload-{uuid.uuid4().hex}"

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            prefix, error = _validate_zip_table(zf)
            if error is not None:
                return StagedPackage(success=False, error_key=error)
            _extract_normalized(zf, prefix=prefix or "", staging_dir=staging_dir)
    except zipfile.BadZipFile:
        discard(staging_dir)
        return StagedPackage(success=False, error_key=ERROR_BAD_ZIP)
    except ValueError as exc:
        discard(staging_dir)
        return StagedPackage(success=False, error_key=str(exc) or ERROR_UNSAFE)
    except OSError:
        discard(staging_dir)
        return StagedPackage(success=False, error_key=ERROR_BAD_ZIP)

    loaded = load_package(staging_dir)
    if loaded.manifest is None or not loaded.validation.ok:
        discard(staging_dir)
        return StagedPackage(
            success=False,
            error_key=ERROR_MANIFEST,
            validation_errors=tuple(loaded.validation.errors),
        )
    if loaded.validation.compatibility_status == COMPAT_INCOMPATIBLE:
        discard(staging_dir)
        return StagedPackage(success=False, error_key=ERROR_INCOMPATIBLE)

    manifest = loaded.manifest
    if not package_id_is_safe(manifest.id) or manifest.kind not in KIND_TO_DIRECTORY:
        discard(staging_dir)
        return StagedPackage(success=False, error_key=ERROR_MANIFEST)

    return StagedPackage(
        success=True,
        staging_dir=staging_dir,
        package_id=manifest.id,
        kind=manifest.kind,
    )


def promote(*, staging_dir: Path, kind: str, package_id: str) -> Path:
    """Move a staged package into its canonical ``{kind_plural}/{id}`` location.

    Replaces an existing directory atomically: the old tree is moved aside first
    and restored on failure. Returns the final package directory.
    """
    target_dir = package_registry.package_dir_for(kind, package_id)
    if target_dir is None:
        raise ValueError(ERROR_MANIFEST)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    backup_dir = target_dir.parent / f".backup-{package_id}-{uuid.uuid4().hex}"

    try:
        if target_dir.exists():
            shutil.move(str(target_dir), str(backup_dir))
        shutil.move(str(staging_dir), str(target_dir))
    except Exception:
        if not target_dir.exists() and backup_dir.exists():
            shutil.move(str(backup_dir), str(target_dir))
        discard(staging_dir)
        raise

    discard(backup_dir)
    return target_dir
