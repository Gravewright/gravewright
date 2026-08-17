"""Checksum-verified, doctor-gated and rollback-safe Marketplace installs."""

from __future__ import annotations

import hashlib
import hmac
import json
import shutil
import uuid
from dataclasses import dataclass

from app.engine.sdk import package_archive_installer, package_registry
from app.engine.sdk.marketplace_service import MarketplaceService, fetch_bytes
from app.engine.sdk.package_doctor_service import PackageDoctorService, SEVERITY_ERROR
from app.engine.sdk.package_integrity import VALIDATION_VALID, compute_manifest_hash
from app.engine.sdk.package_install_service import STATUS_INSTALLED
from app.engine.sdk.package_loader import load_package
from app.persistence.repositories.installed_package_repository import InstalledPackageRepository


@dataclass(frozen=True)
class MarketplaceInstallResult:
    success: bool
    package_id: str = ""
    error_key: str = ""


class MarketplaceInstaller:
    def __init__(self, *, marketplace: MarketplaceService | None = None, fetcher=fetch_bytes) -> None:
        self.marketplace = marketplace or MarketplaceService()
        self.fetcher = fetcher
        self.installed = InstalledPackageRepository()

    def install(self, *, package_id: str, user_id: str | None) -> MarketplaceInstallResult:
        entry = self.marketplace.get_valid(package_id)
        if entry is None:
            return MarketplaceInstallResult(False, package_id, "MARKETPLACE_PACKAGE_UNAVAILABLE")
        artifact = entry.get("artifact") or {}
        try:
            data = self.fetcher(str(artifact.get("url", "")), package_archive_installer.MAX_PACKAGE_BYTES)
        except Exception:
            return MarketplaceInstallResult(False, package_id, "PACKAGE_DOWNLOAD_FAILED")
        actual = hashlib.sha256(data).hexdigest()
        if not hmac.compare_digest(actual.lower(), str(artifact.get("sha256", "")).lower()):
            return MarketplaceInstallResult(False, package_id, "PACKAGE_CHECKSUM_MISMATCH")

        staged = package_archive_installer.stage_archive(filename=f"{package_id}.zip", data=data)
        if not staged.success or staged.staging_dir is None:
            return MarketplaceInstallResult(False, package_id, staged.error_key or "PACKAGE_ARCHIVE_INVALID")
        if staged.package_id != package_id or staged.kind != entry.get("kind"):
            package_archive_installer.discard(staged.staging_dir)
            return MarketplaceInstallResult(False, package_id, "MARKETPLACE_MANIFEST_MISMATCH")

        staged_raw = json.loads((staged.staging_dir / "manifest.json").read_text(encoding="utf-8"))
        expected = entry.get("manifestIdentity") or {}
        actual_identity = {key: staged_raw.get(key) for key in ("id", "kind", "version", "sdkVersion")}
        if actual_identity != expected:
            package_archive_installer.discard(staged.staging_dir)
            return MarketplaceInstallResult(False, package_id, "MARKETPLACE_ARTIFACT_MANIFEST_MISMATCH")

        loaded = load_package(staged.staging_dir)
        findings = PackageDoctorService().audit_staged(loaded)
        if any(finding.severity == SEVERITY_ERROR for finding in findings):
            package_archive_installer.discard(staged.staging_dir)
            return MarketplaceInstallResult(False, package_id, "PACKAGE_DOCTOR_REJECTED")

        target = package_registry.package_dir_for(staged.kind or "", package_id)
        if target is None:
            package_archive_installer.discard(staged.staging_dir)
            return MarketplaceInstallResult(False, package_id, "PACKAGE_ARCHIVE_INVALID")
        target.parent.mkdir(parents=True, exist_ok=True)
        backup = target.parent / f".marketplace-backup-{package_id}-{uuid.uuid4().hex}"
        previous = self.installed.get(package_id)
        try:
            if target.exists():
                shutil.move(str(target), str(backup))
            shutil.move(str(staged.staging_dir), str(target))
            installed = load_package(target, expected_id=package_id, expected_kind_root=target.parent.name)
            if not installed.validation.ok:
                raise ValueError("PACKAGE_DOCTOR_REJECTED")
            status = str(previous.get("status")) if previous else STATUS_INSTALLED
            self.installed.upsert(
                package_id=installed.manifest.id, kind=installed.manifest.kind,
                name=installed.manifest.name or installed.manifest.id, version=installed.manifest.version,
                status=status, package_dir=installed.relative_dir, manifest_json=json.dumps(installed.raw),
                compatibility_status=installed.validation.compatibility_status,
                validation_errors_json="[]", installed_by_user_id=user_id, package_sha256=actual,
                manifest_hash=compute_manifest_hash(installed.raw), last_validation_status=VALIDATION_VALID,
            )
        except Exception:
            package_archive_installer.discard(target)
            if backup.exists():
                shutil.move(str(backup), str(target))
            package_archive_installer.discard(staged.staging_dir)
            return MarketplaceInstallResult(False, package_id, "PACKAGE_INSTALL_FAILED")
        package_archive_installer.discard(backup)
        return MarketplaceInstallResult(True, package_id)
