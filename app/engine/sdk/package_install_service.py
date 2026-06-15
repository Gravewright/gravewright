"""Global install / enable / disable / remove for SDK packages (Inside > Packages).

Disk packages (read-only, discovered by the registry) are merged with the
``installed_packages`` table to produce the state machine:
``available | installed | enabled | disabled | incompatible | error``.

Everything is keyed by **package id** (the on-disk directory name, which equals
the manifest ``id`` for valid packages). Installing or enabling requires the
package to pass validation *and* be compatible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.engine.sdk import package_registry
from app.engine.sdk.package_compatibility import COMPAT_INCOMPATIBLE
from app.engine.sdk.package_loader import LoadedPackage
from app.engine.sdk.package_manifest import PackageManifest
from app.persistence.repositories.installed_package_repository import (
    InstalledPackageRepository,
)
from app.persistence.repositories.campaign_package_repository import (
    CampaignPackageRepository,
)
from app.persistence.repositories.campaign_repository import CampaignRepository

STATUS_AVAILABLE = "available"
STATUS_INSTALLED = "installed"
STATUS_ENABLED = "enabled"
STATUS_DISABLED = "disabled"
STATUS_INCOMPATIBLE = "incompatible"
STATUS_ERROR = "error"

_PERSISTED = {STATUS_INSTALLED, STATUS_ENABLED, STATUS_DISABLED}


@dataclass(frozen=True)
class PackageActionResult:
    success: bool
    package_id: str | None = None
    error_key: str | None = None
    active_campaign_ids: tuple[str, ...] = ()


def _is_incompatible(loaded: LoadedPackage) -> bool:
    return loaded.validation.compatibility_status == COMPAT_INCOMPATIBLE


def _installable(loaded: LoadedPackage) -> bool:
    return loaded.validation.ok and not _is_incompatible(loaded)


class PackageInstallService:
    def __init__(self) -> None:
        self.installed = InstalledPackageRepository()
        self.campaign_packages = CampaignPackageRepository()
        self.campaigns = CampaignRepository()

    # --- reads -----------------------------------------------------------------

    def list_for_tab(self) -> list[dict]:
        records = {row["id"]: row for row in self.installed.list_all()}
        items: list[dict] = []
        seen: set[str] = set()

        for loaded in package_registry.load_all():
            seen.add(loaded.id)
            items.append(self._tab_item(loaded, records.get(loaded.id)))

        for package_id, record in records.items():
            if package_id not in seen:
                items.append(self._missing_item(package_id, record))

        items.sort(key=lambda i: str(i["name"]).lower())
        return items

    def list_for_kind(self, kind: str) -> list[dict]:
        return [item for item in self.list_for_tab() if item["kind"] == kind]

    def get_details(self, package_id: str) -> dict | None:
        for item in self.list_for_tab():
            if item["id"] == package_id:
                return item
        return None

    def get(self, package_id: str) -> dict | None:
        return self.installed.get(package_id)

    def get_manifest(self, package_id: str) -> PackageManifest | None:
        record = self.installed.get(package_id)
        if record is None:
            return None
        try:
            raw = json.loads(record["manifest_json"])
        except (TypeError, ValueError):
            return None
        return PackageManifest.from_dict(raw)

    def get_active_manifest(self, package_id: str) -> PackageManifest | None:
        """Manifest only if the package is installed *and* enabled globally."""
        record = self.installed.get(package_id)
        if record is None or record["status"] != STATUS_ENABLED:
            return None
        return self.get_manifest(package_id)

    # --- writes ----------------------------------------------------------------

    def install(self, *, package_id: str, user_id: str | None) -> PackageActionResult:
        loaded = package_registry.load_by_package_id(package_id)
        if loaded is None:
            return PackageActionResult(success=False, error_key="sdk.errors.not_found")
        if _is_incompatible(loaded):
            return PackageActionResult(success=False, error_key="sdk.errors.incompatible")
        if not loaded.validation.ok:
            return PackageActionResult(success=False, error_key="sdk.errors.invalid_manifest")

        manifest = loaded.manifest
        self.installed.upsert(
            package_id=manifest.id,
            kind=manifest.kind,
            name=manifest.name or manifest.id,
            version=manifest.version,
            status=STATUS_INSTALLED,
            package_dir=loaded.id,
            manifest_json=json.dumps(loaded.raw),
            compatibility_status=loaded.validation.compatibility_status,
            validation_errors_json="[]",
            installed_by_user_id=user_id,
        )
        return PackageActionResult(success=True, package_id=manifest.id)

    def enable(self, *, package_id: str) -> PackageActionResult:
        record = self.installed.get(package_id)
        if record is None:
            return PackageActionResult(success=False, error_key="sdk.errors.not_installed")
        loaded = package_registry.load_by_package_id(package_id)
        if loaded is None or not _installable(loaded):
            return PackageActionResult(success=False, error_key="sdk.errors.invalid_manifest")
        self.installed.set_status(package_id=package_id, status=STATUS_ENABLED)
        return PackageActionResult(success=True, package_id=package_id)

    def disable(self, *, package_id: str, force: bool = False) -> PackageActionResult:
        record = self.installed.get(package_id)
        if record is None:
            return PackageActionResult(success=False, error_key="sdk.errors.not_installed")
        active_campaign_ids = self._active_campaign_ids(package_id)
        if active_campaign_ids and not force:
            return PackageActionResult(
                success=False,
                package_id=package_id,
                error_key="sdk.errors.package_active_in_campaign",
                active_campaign_ids=tuple(active_campaign_ids),
            )
        self.installed.set_status(package_id=package_id, status=STATUS_DISABLED)
        return PackageActionResult(success=True, package_id=package_id)

    def remove(self, *, package_id: str, force: bool = False) -> PackageActionResult:
        record = self.installed.get(package_id)
        if record is None:
            return PackageActionResult(success=False, error_key="sdk.errors.not_installed")
        active_campaign_ids = self._active_campaign_ids(package_id)
        if active_campaign_ids and not force:
            return PackageActionResult(
                success=False,
                package_id=package_id,
                error_key="sdk.errors.package_active_in_campaign",
                active_campaign_ids=tuple(active_campaign_ids),
            )
        self.installed.delete(package_id=package_id)
        return PackageActionResult(success=True, package_id=package_id)

    # --- helpers ---------------------------------------------------------------

    def _active_campaign_ids(self, package_id: str) -> list[str]:
        ids = {
            str(row["campaign_id"])
            for row in self.campaign_packages.list_active_for_package(package_id)
        }
        ids.update(str(row["id"]) for row in self.campaigns.list_by_active_system(package_id))
        return sorted(ids)

    def _tab_item(self, loaded: LoadedPackage, record: dict | None) -> dict:
        summary = loaded.manifest.summary(package_dir=loaded.package_dir)
        compat = loaded.validation.compatibility_status
        installable = _installable(loaded)

        if not loaded.validation.ok:
            status = STATUS_ERROR
        elif _is_incompatible(loaded):
            status = STATUS_INCOMPATIBLE
        elif record is not None and record["status"] in _PERSISTED:
            status = record["status"]
        else:
            status = STATUS_AVAILABLE

        return {
            **summary,
            "id": loaded.id,
            "package_id": loaded.id,
            "kind": loaded.manifest.kind,
            "scripted": loaded.manifest.has_scripts(),
            "trusted_code_required": loaded.manifest.has_scripts(),
            "status": status,
            "compatibility_status": compat,
            "validation_errors": list(loaded.validation.errors),
            "validation_warnings": list(loaded.validation.warnings),
            "can_install": installable and record is None,
            "installed": record is not None,
            "enabled": status == STATUS_ENABLED,
        }

    @staticmethod
    def _missing_item(package_id: str, record: dict) -> dict:
        return {
            "id": package_id,
            "package_id": package_id,
            "name": record["name"] or package_id,
            "kind": record["kind"],
            "scripted": False,
            "trusted_code_required": False,
            "version": record["version"],
            "description": "",
            "author": "",
            "color": "",
            "capabilities": [],
            "actor_types": [],
            "item_types": [],
            "area_markers": [],
            "content_packs": [],
            "settings": [],
            "compatibility": {},
            "status": STATUS_ERROR,
            "compatibility_status": COMPAT_INCOMPATIBLE,
            "validation_errors": ["sdk.validation.package_missing"],
            "validation_warnings": [],
            "can_install": False,
            "installed": True,
            "enabled": False,
        }
