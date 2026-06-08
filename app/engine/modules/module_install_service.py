"""Install / enable / disable / remove for module packages."""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.engine.modules import module_registry
from app.engine.modules.module_loader import LoadedModule
from app.engine.modules.module_manifest import ModuleManifest
from app.engine.modules.module_manifest_validator import COMPAT_INCOMPATIBLE
from app.engine.modules.module_package_installer import install_zip_package
from app.domain.roles import PlayerRole
from app.persistence.repositories.campaign_module_repository import CampaignModuleRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.installed_module_repository import InstalledModuleRepository

STATUS_AVAILABLE = "available"
STATUS_INSTALLED = "installed"
STATUS_ENABLED = "enabled"
STATUS_DISABLED = "disabled"
STATUS_INCOMPATIBLE = "incompatible"
STATUS_ERROR = "error"


@dataclass(frozen=True)
class ModuleActionResult:
    success: bool
    package_id: str | None = None
    module_id: str | None = None
    error_key: str | None = None


def _blocking_errors(loaded: LoadedModule) -> list[str]:
    return [e for e in loaded.validation.errors if e != "inside.modules.validation.incompatible"]


def _is_incompatible(loaded: LoadedModule) -> bool:
    return loaded.validation.compatibility_status == COMPAT_INCOMPATIBLE


def _installable(loaded: LoadedModule) -> bool:
    return loaded.manifest is not None and not _blocking_errors(loaded) and not _is_incompatible(loaded)


class ModuleInstallService:
    def __init__(self) -> None:
        self.installed = InstalledModuleRepository()
        self.campaigns = CampaignRepository()
        self.campaign_modules = CampaignModuleRepository()

    def list_for_tab(self) -> list[dict]:
        records = {row["package_id"]: row for row in self.installed.list_all()}
        items: list[dict] = []
        seen_packages: set[str] = set()

        for loaded in module_registry.load_all():
            seen_packages.add(loaded.package_id)
            items.append(self._tab_item(loaded, records.get(loaded.package_id)))

        for package_id, record in records.items():
            if package_id not in seen_packages:
                items.append(
                    {
                        "id": package_id,
                        "module_id": record["id"],
                        "name": record["name"] or package_id,
                        "version": record["version"],
                        "api_version": record["api_version"],
                        "description": "",
                        "author": "",
                        "color": "",
                        "capabilities": [],
                        "settings": [],
                        "hooks": [],
                        "content_packs": [],
                        "compatibility": {},
                        "status": STATUS_ERROR,
                        "compatibility_status": COMPAT_INCOMPATIBLE,
                        "validation_errors": ["inside.modules.validation.package_missing"],
                        "can_install": False,
                        "installed": True,
                        "enabled": False,
                    }
                )

        items.sort(key=lambda i: i["name"].lower())
        return items

    def get_details(self, package_id: str) -> dict | None:
        for item in self.list_for_tab():
            if item["id"] == package_id:
                return item
        return None

    def get_manifest(self, module_id: str) -> ModuleManifest | None:
        record = self.installed.get(module_id)
        if record is None:
            return None
        try:
            raw = json.loads(record["manifest_json"])
        except (TypeError, ValueError):
            return None
        return ModuleManifest.from_dict(raw)

    def get_active_manifest(self, module_id: str) -> ModuleManifest | None:
        record = self.installed.get(module_id)
        if record is None or record["status"] != STATUS_ENABLED:
            return None
        return self.get_manifest(module_id)

    def _enabled_manifest_for_record(self, record: dict | None) -> ModuleManifest | None:
        if record is None or record.get("status") != STATUS_ENABLED:
            return None
        try:
            return ModuleManifest.from_dict(json.loads(record["manifest_json"]))
        except (TypeError, ValueError):
            return None

    def enabled_campaign_ids_by_module(self, campaign_ids: list[str]) -> dict[str, set[str]]:
        return self.campaign_modules.enabled_campaign_ids_by_module(campaign_ids=campaign_ids)

    def enable_for_campaign(
        self,
        *,
        campaign_id: str,
        user_id: str,
        module_id: str,
    ) -> ModuleActionResult:
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return ModuleActionResult(success=False, error_key="inside.campaigns.errors.not_found")
        if campaign["member_role"] != PlayerRole.GM.value:
            return ModuleActionResult(success=False, error_key="inside.campaigns.errors.gm_required")

        record = self.installed.get(module_id)
        manifest = self._enabled_manifest_for_record(record)
        if manifest is None:
            return ModuleActionResult(success=False, error_key="inside.modules.errors.not_installed")

        enabled_ids = set(self.campaign_modules.list_enabled_module_ids(campaign_id=campaign_id))
        for dependency_id in manifest.dependency_ids():
            if dependency_id not in enabled_ids or self.get_active_manifest(dependency_id) is None:
                return ModuleActionResult(success=False, error_key="inside.modules.errors.dependency_missing")

        conflicts = set(manifest.conflict_ids())
        if conflicts & enabled_ids:
            return ModuleActionResult(success=False, error_key="inside.modules.errors.conflict")
        for enabled_id in enabled_ids:
            enabled_manifest = self.get_active_manifest(enabled_id)
            if enabled_manifest is not None and module_id in set(enabled_manifest.conflict_ids()):
                return ModuleActionResult(success=False, error_key="inside.modules.errors.conflict")

        self.campaign_modules.enable(
            campaign_id=campaign_id,
            module_id=module_id,
            enabled_by_user_id=user_id,
        )
        return ModuleActionResult(success=True, module_id=module_id)

    def disable_for_campaign(
        self,
        *,
        campaign_id: str,
        user_id: str,
        module_id: str,
    ) -> ModuleActionResult:
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return ModuleActionResult(success=False, error_key="inside.campaigns.errors.not_found")
        if campaign["member_role"] != PlayerRole.GM.value:
            return ModuleActionResult(success=False, error_key="inside.campaigns.errors.gm_required")

        enabled_ids = set(self.campaign_modules.list_enabled_module_ids(campaign_id=campaign_id))
        for enabled_id in enabled_ids:
            if enabled_id == module_id:
                continue
            enabled_manifest = self.get_active_manifest(enabled_id)
            if enabled_manifest is not None and module_id in set(enabled_manifest.dependency_ids()):
                return ModuleActionResult(success=False, error_key="inside.modules.errors.dependent_enabled")

        self.campaign_modules.disable(campaign_id=campaign_id, module_id=module_id)
        return ModuleActionResult(success=True, module_id=module_id)


    def install_uploaded_package(
        self,
        *,
        filename: str,
        data: bytes,
        user_id: str | None,
    ) -> ModuleActionResult:
        result = install_zip_package(
            filename=filename,
            data=data,
            user_id=user_id,
            installed_repository=self.installed,
            campaign_module_repository=self.campaign_modules,
        )
        if not result.success:
            return ModuleActionResult(success=False, error_key=result.error_key or "inside.modules.errors.package_invalid")
        return ModuleActionResult(success=True, package_id=result.package_id, module_id=result.module_id)

    def install(self, *, package_id: str, user_id: str | None) -> ModuleActionResult:
        loaded = module_registry.load_by_package_id(package_id)
        if loaded is None or loaded.manifest is None:
            return ModuleActionResult(success=False, error_key="inside.modules.errors.not_found")
        if _is_incompatible(loaded):
            return ModuleActionResult(success=False, error_key="inside.modules.errors.incompatible")
        if _blocking_errors(loaded):
            return ModuleActionResult(success=False, error_key="inside.modules.errors.invalid_manifest")

        manifest = loaded.manifest
        self.installed.upsert(
            module_id=manifest.id,
            package_id=loaded.package_id,
            name=manifest.name or manifest.id,
            version=manifest.version,
            api_version=manifest.api_version,
            package_dir=loaded.package_id,
            manifest_json=loaded.manifest_json,
            status=STATUS_INSTALLED,
            validation_errors_json="[]",
            installed_by_user_id=user_id,
        )
        return ModuleActionResult(success=True, package_id=package_id, module_id=manifest.id)

    def enable(self, *, package_id: str) -> ModuleActionResult:
        record = self.installed.get_by_package_id(package_id)
        if record is None:
            return ModuleActionResult(success=False, error_key="inside.modules.errors.not_installed")
        loaded = module_registry.load_by_package_id(package_id)
        if loaded is None or not _installable(loaded):
            return ModuleActionResult(success=False, error_key="inside.modules.errors.invalid_manifest")
        self.installed.set_status(module_id=record["id"], status=STATUS_ENABLED)
        return ModuleActionResult(success=True, package_id=package_id, module_id=record["id"])

    def disable(self, *, package_id: str) -> ModuleActionResult:
        record = self.installed.get_by_package_id(package_id)
        if record is None:
            return ModuleActionResult(success=False, error_key="inside.modules.errors.not_installed")
        self.installed.set_status(module_id=record["id"], status=STATUS_DISABLED)
        return ModuleActionResult(success=True, package_id=package_id, module_id=record["id"])

    def remove(self, *, package_id: str) -> ModuleActionResult:
        record = self.installed.get_by_package_id(package_id)
        if record is None:
            return ModuleActionResult(success=False, error_key="inside.modules.errors.not_installed")
        if record.get("status") == STATUS_ENABLED:
            return ModuleActionResult(success=False, error_key="inside.modules.errors.disable_before_remove")
        if self.campaign_modules.has_campaigns_for_module(module_id=record["id"]):
            return ModuleActionResult(success=False, error_key="inside.modules.errors.disable_campaigns_before_remove")
        self.installed.delete(module_id=record["id"])
        return ModuleActionResult(success=True, package_id=package_id, module_id=record["id"])

    def _tab_item(self, loaded: LoadedModule, record: dict | None) -> dict:
        if loaded.manifest is not None:
            summary = loaded.manifest.summary()
            module_id = loaded.manifest.id
        else:
            module_id = ""
            summary = {
                "id": loaded.package_id,
                "name": loaded.package_id,
                "version": "",
                "api_version": "",
                "description": "",
                "author": "",
                "color": "",
                "capabilities": [],
                "settings": [],
                "hooks": [],
                "content_packs": [],
                "compatibility": {},
            }

        compat = loaded.validation.compatibility_status
        blocking = _blocking_errors(loaded)
        installable = _installable(loaded)

        if record is not None and record["status"] in {STATUS_INSTALLED, STATUS_ENABLED, STATUS_DISABLED}:
            status = record["status"]
        elif blocking or loaded.manifest is None:
            status = STATUS_ERROR
        elif _is_incompatible(loaded):
            status = STATUS_INCOMPATIBLE
        else:
            status = STATUS_AVAILABLE

        return {
            **summary,
            "id": loaded.package_id,
            "module_id": module_id,
            "status": status,
            "compatibility_status": compat,
            "validation_errors": list(loaded.validation.errors),
            "can_install": installable and record is None,
            "installed": record is not None,
            "enabled": status == STATUS_ENABLED,
        }
