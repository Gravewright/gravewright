"""Safe ZIP package installation for Module API v1.

The installer treats uploaded archives as untrusted input. It validates the ZIP
member table before extraction, normalizes a root folder if present, extracts to
a hidden staging directory, validates the manifest/package from staging, then
promotes the staged tree into ``MODULES_DIR/<manifest.id>`` only after all checks
pass.
"""

from __future__ import annotations

import hashlib
import io
import shutil
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.engine.modules import module_loader
from app.engine.modules.module_loader import load_package
from app.engine.modules.module_manifest_validator import ID_PATTERN

MAX_MODULE_PACKAGE_BYTES = 25 * 1024 * 1024
MAX_MODULE_ZIP_ENTRIES = 512
MAX_MODULE_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_MODULE_PACKAGE_FILE_BYTES = 10 * 1024 * 1024
MAX_MODULE_MANIFEST_BYTES = 1 * 1024 * 1024

_ERROR_BAD_ZIP = "inside.modules.errors.package_invalid"
_ERROR_TOO_LARGE = "inside.modules.errors.package_too_large"
_ERROR_UNSAFE = "inside.modules.errors.package_unsafe"
_ERROR_MANIFEST = "inside.modules.errors.invalid_manifest"
_ERROR_ENABLED = "inside.modules.errors.disable_before_replace"
_ERROR_CAMPAIGN_ENABLED = "inside.modules.errors.disable_campaigns_before_replace"


@dataclass(frozen=True)
class ModulePackageInstallResult:
    success: bool
    package_id: str | None = None
    module_id: str | None = None
    checksum_sha256: str | None = None
    error_key: str | None = None
    validation_errors: tuple[str, ...] = ()


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
        return None, _ERROR_BAD_ZIP
    if len(infos) > MAX_MODULE_ZIP_ENTRIES:
        return None, _ERROR_TOO_LARGE
    total_uncompressed = 0
    for info in infos:
        name = info.filename
        if not _safe_member_name(name) or _zip_member_is_symlink(info):
            return None, _ERROR_UNSAFE
        if info.file_size > MAX_MODULE_PACKAGE_FILE_BYTES:
            return None, _ERROR_TOO_LARGE
        total_uncompressed += info.file_size
        if total_uncompressed > MAX_MODULE_UNCOMPRESSED_BYTES:
            return None, _ERROR_TOO_LARGE
        if name.endswith("manifest.json") and info.file_size > MAX_MODULE_MANIFEST_BYTES:
            return None, _ERROR_TOO_LARGE
    prefix = _root_prefix(infos)
    if prefix is None:
        return None, "inside.modules.validation.manifest_missing"
    return prefix, None


def _extract_normalized(zf: zipfile.ZipFile, *, prefix: str, staging_dir: Path) -> None:
    staging_dir.mkdir(parents=True, exist_ok=False)
    for info in _normalized_infos(zf):
        name = info.filename
        if prefix:
            if not name.startswith(prefix):
                continue
            relative = name[len(prefix) :]
        else:
            relative = name
        if not relative:
            continue
        if not _safe_member_name(relative):
            raise ValueError(_ERROR_UNSAFE)
        destination = staging_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info, "r") as source, destination.open("wb") as target:
            shutil.copyfileobj(source, target)


def _remove(path: Path | None) -> None:
    if path is None or not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def install_zip_package(
    *,
    filename: str,
    data: bytes,
    user_id: str | None,
    installed_repository,
    campaign_module_repository=None,
) -> ModulePackageInstallResult:
    """Install or replace a module package from an uploaded ZIP archive.

    Replacing an already-enabled module is intentionally blocked: module JS is
    privileged same-origin code, so upgrades should happen only after disabling
    the module globally to avoid swapping code while campaigns may be loading it.
    """
    if not filename.lower().endswith(".zip") or not data:
        return ModulePackageInstallResult(success=False, error_key=_ERROR_BAD_ZIP)
    if len(data) > MAX_MODULE_PACKAGE_BYTES:
        return ModulePackageInstallResult(success=False, error_key=_ERROR_TOO_LARGE)

    checksum = hashlib.sha256(data).hexdigest()
    modules_dir = module_loader.MODULES_DIR
    modules_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = modules_dir / f".upload-{uuid.uuid4().hex}"
    backup_dir: Path | None = None
    target_dir: Path | None = None

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            prefix, error = _validate_zip_table(zf)
            if error is not None:
                return ModulePackageInstallResult(success=False, error_key=error)
            _extract_normalized(zf, prefix=prefix or "", staging_dir=staging_dir)
    except zipfile.BadZipFile:
        _remove(staging_dir)
        return ModulePackageInstallResult(success=False, error_key=_ERROR_BAD_ZIP)
    except ValueError as exc:
        _remove(staging_dir)
        return ModulePackageInstallResult(success=False, error_key=str(exc) or _ERROR_UNSAFE)
    except OSError:
        _remove(staging_dir)
        return ModulePackageInstallResult(success=False, error_key=_ERROR_BAD_ZIP)

    loaded = load_package(staging_dir)
    if loaded.manifest is None:
        _remove(staging_dir)
        return ModulePackageInstallResult(success=False, error_key=_ERROR_MANIFEST, validation_errors=tuple(loaded.validation.errors))
    blocking = [error for error in loaded.validation.errors if error != "inside.modules.validation.incompatible"]
    if blocking or loaded.validation.compatibility_status == "incompatible":
        _remove(staging_dir)
        return ModulePackageInstallResult(success=False, error_key=_ERROR_MANIFEST, validation_errors=tuple(loaded.validation.errors))

    manifest = loaded.manifest
    if not ID_PATTERN.match(manifest.id):
        _remove(staging_dir)
        return ModulePackageInstallResult(success=False, error_key=_ERROR_MANIFEST, validation_errors=("inside.modules.validation.id_invalid",))

    existing = installed_repository.get(manifest.id)
    if existing is not None:
        if existing.get("status") == "enabled":
            _remove(staging_dir)
            return ModulePackageInstallResult(success=False, error_key=_ERROR_ENABLED)
        if campaign_module_repository is not None and campaign_module_repository.has_campaigns_for_module(module_id=manifest.id):
            _remove(staging_dir)
            return ModulePackageInstallResult(success=False, error_key=_ERROR_CAMPAIGN_ENABLED)

    target_dir = modules_dir / manifest.id
    backup_dir = modules_dir / f".backup-{manifest.id}-{uuid.uuid4().hex}"
    previous_status = (existing or {}).get("status") or "installed"
    if previous_status == "enabled":
        previous_status = "installed"

    try:
        if target_dir.exists():
            shutil.move(str(target_dir), str(backup_dir))
        shutil.move(str(staging_dir), str(target_dir))
        installed_repository.upsert(
            module_id=manifest.id,
            package_id=manifest.id,
            name=manifest.name or manifest.id,
            version=manifest.version,
            api_version=manifest.api_version,
            package_dir=manifest.id,
            manifest_json=loaded.manifest_json,
            status=previous_status,
            validation_errors_json="[]",
            installed_by_user_id=user_id,
            package_sha256=checksum,
        )
    except Exception:
        if target_dir is not None and target_dir.exists():
            _remove(target_dir)
        if backup_dir is not None and backup_dir.exists():
            shutil.move(str(backup_dir), str(target_dir))
        _remove(staging_dir)
        raise

    _remove(backup_dir)
    _remove(staging_dir)
    return ModulePackageInstallResult(
        success=True,
        package_id=manifest.id,
        module_id=manifest.id,
        checksum_sha256=checksum,
    )
