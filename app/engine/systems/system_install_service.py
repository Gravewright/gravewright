"""Install / enable / disable / remove for system packages (Systems tab).

Disk packages (read-only, discovered by the registry) are merged with the
``systems_installed`` table to produce the state machine from spec §7:
``available | installed | enabled | disabled | incompatible | error``.

The tab and all actions are keyed by **package_id** (the on-disk directory
name), which is stable even for a package whose manifest is invalid. The
installed record additionally stores the manifest ``id`` as the system's real
identity (used by later slices: Actor Core, Sheet Data, etc). Installing or
enabling requires the package to pass validation *and* be compatible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.engine.systems import system_registry
from app.engine.systems.system_loader import LoadedSystem
from app.engine.systems.system_manifest import SystemManifest
from app.engine.systems.system_manifest_validator import COMPAT_INCOMPATIBLE
from app.persistence.repositories.installed_system_repository import InstalledSystemRepository

STATUS_AVAILABLE = "available"
STATUS_INSTALLED = "installed"
STATUS_ENABLED = "enabled"
STATUS_DISABLED = "disabled"
STATUS_INCOMPATIBLE = "incompatible"
STATUS_ERROR = "error"


@dataclass(frozen=True)
class SystemActionResult:
    success: bool
    package_id: str | None = None
    system_id: str | None = None
    error_key: str | None = None


def _blocking_errors(loaded: LoadedSystem) -> list[str]:
    """Validation errors that prevent install, excluding the incompatible flag."""
    return [e for e in loaded.validation.errors if e != "inside.systems.validation.incompatible"]


def _is_incompatible(loaded: LoadedSystem) -> bool:
    return loaded.validation.compatibility_status == COMPAT_INCOMPATIBLE


def _installable(loaded: LoadedSystem) -> bool:
    return loaded.manifest is not None and not _blocking_errors(loaded) and not _is_incompatible(loaded)


class SystemInstallService:
    def __init__(self) -> None:
        self.installed = InstalledSystemRepository()

                                                                              

    def list_for_tab(self) -> list[dict]:
        records = {row["package_id"]: row for row in self.installed.list_all()}
        items: list[dict] = []
        seen_packages: set[str] = set()

        for loaded in system_registry.load_all():
            seen_packages.add(loaded.package_id)
            items.append(self._tab_item(loaded, records.get(loaded.package_id)))

                                                                               
        for package_id, record in records.items():
            if package_id not in seen_packages:
                items.append(
                    {
                        "id": package_id,
                        "system_id": record["id"],
                        "name": record["name"] or package_id,
                        "version": record["version"],
                        "api_version": record["api_version"],
                        "description": "",
                        "author": "",
                        "color": "",
                        "capabilities": [],
                        "actor_types": [],
                        "item_types": [],
                        "content_packs": [],
                        "compatibility": {},
                        "status": STATUS_ERROR,
                        "compatibility_status": COMPAT_INCOMPATIBLE,
                        "validation_errors": ["inside.systems.validation.package_missing"],
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

    def get_manifest(self, system_id: str) -> SystemManifest | None:
        """Parsed manifest snapshot for an installed system (any status)."""
        record = self.installed.get(system_id)
        if record is None:
            return None
        try:
            raw = json.loads(record["manifest_json"])
        except (TypeError, ValueError):
            return None
        return SystemManifest.from_dict(raw)

    def get_active_manifest(self, system_id: str) -> SystemManifest | None:
        """Manifest only if the system is installed *and* enabled."""
        record = self.installed.get(system_id)
        if record is None or record["status"] != STATUS_ENABLED:
            return None
        return self.get_manifest(system_id)

                                                                                

    def install(self, *, package_id: str, user_id: str | None) -> SystemActionResult:
        loaded = system_registry.load_by_package_id(package_id)
        if loaded is None or loaded.manifest is None:
            return SystemActionResult(success=False, error_key="inside.systems.errors.not_found")
        if _is_incompatible(loaded):
            return SystemActionResult(success=False, error_key="inside.systems.errors.incompatible")
        if _blocking_errors(loaded):
            return SystemActionResult(success=False, error_key="inside.systems.errors.invalid_manifest")

        manifest = loaded.manifest
        self.installed.upsert(
            system_id=manifest.id,
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
        return SystemActionResult(success=True, package_id=package_id, system_id=manifest.id)

    def enable(self, *, package_id: str) -> SystemActionResult:
        record = self.installed.get_by_package_id(package_id)
        if record is None:
            return SystemActionResult(success=False, error_key="inside.systems.errors.not_installed")
        loaded = system_registry.load_by_package_id(package_id)
        if loaded is None or not _installable(loaded):
            return SystemActionResult(success=False, error_key="inside.systems.errors.invalid_manifest")
        self.installed.set_status(system_id=record["id"], status=STATUS_ENABLED)
        return SystemActionResult(success=True, package_id=package_id, system_id=record["id"])

    def disable(self, *, package_id: str) -> SystemActionResult:
        record = self.installed.get_by_package_id(package_id)
        if record is None:
            return SystemActionResult(success=False, error_key="inside.systems.errors.not_installed")
        self.installed.set_status(system_id=record["id"], status=STATUS_DISABLED)
        return SystemActionResult(success=True, package_id=package_id, system_id=record["id"])

    def remove(self, *, package_id: str) -> SystemActionResult:
        record = self.installed.get_by_package_id(package_id)
        if record is None:
            return SystemActionResult(success=False, error_key="inside.systems.errors.not_installed")
        self.installed.delete(system_id=record["id"])
        return SystemActionResult(success=True, package_id=package_id, system_id=record["id"])

                                                                                

    def _tab_item(self, loaded: LoadedSystem, record: dict | None) -> dict:
        if loaded.manifest is not None:
            summary = loaded.manifest.summary()
            system_id = loaded.manifest.id
        else:
            system_id = ""
            summary = {
                "id": loaded.package_id,
                "name": loaded.package_id,
                "version": "",
                "api_version": "",
                "description": "",
                "author": "",
                "color": "",
                "capabilities": [],
                "actor_types": [],
                "item_types": [],
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
            "system_id": system_id,
            "status": status,
            "compatibility_status": compat,
            "validation_errors": list(loaded.validation.errors),
            "can_install": installable and record is None,
            "installed": record is not None,
            "enabled": status == STATUS_ENABLED,
        }
