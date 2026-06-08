"""Read-only access to enabled modules' declared UI assets."""

from __future__ import annotations

import json
from pathlib import Path

from app.engine.modules import module_loader
from app.engine.modules.module_manifest import ModuleManifest
from app.engine.systems.system_loader import safe_join
from app.persistence.repositories.campaign_module_repository import CampaignModuleRepository
from app.persistence.repositories.installed_module_repository import InstalledModuleRepository
from app.engine.modules.module_settings_service import ModuleSettingsService

_STATUS_ENABLED = "enabled"

_CONTENT_TYPES = {
    ".css": "text/css",
    ".js": "application/javascript",
    ".mjs": "application/javascript",
}


class ModuleAssetService:
    def __init__(self) -> None:
        self.installed = InstalledModuleRepository()
        self.campaign_modules = CampaignModuleRepository()
        self.settings = ModuleSettingsService()

    def _enabled_record_manifest(self, module_id: str) -> tuple[dict, ModuleManifest] | None:
        record = self.installed.get(module_id)
        if record is None or record["status"] != _STATUS_ENABLED:
            return None
        try:
            manifest = ModuleManifest.from_dict(json.loads(record["manifest_json"]))
        except (TypeError, ValueError):
            return None
        return record, manifest

    def _record_manifest_pairs(self, *, campaign_id: str | None) -> list[tuple[dict, ModuleManifest]]:
        records = (
            self.campaign_modules.list_enabled_records_for_campaign(campaign_id=campaign_id)
            if campaign_id
            else self.installed.list_all()
        )
        pairs: list[tuple[dict, ModuleManifest]] = []
        for record in records:
            if record["status"] != _STATUS_ENABLED:
                continue
            try:
                manifest = ModuleManifest.from_dict(json.loads(record["manifest_json"]))
            except (TypeError, ValueError):
                continue
            pairs.append((record, manifest))
        return _order_module_pairs(pairs)

    def list_enabled_assets(self, *, campaign_id: str | None = None, entrypoint: str = "game") -> list[dict]:
        out: list[dict] = []
        for _, manifest in self._record_manifest_pairs(campaign_id=campaign_id):
            styles = manifest.entrypoint_styles(entrypoint)
            scripts = manifest.entrypoint_scripts(entrypoint)
            if not styles and not scripts:
                continue
            out.append(
                {
                    "module_id": manifest.id,
                    "version": manifest.version or "0",
                    "styles": styles,
                    "scripts": scripts,
                }
            )
        return out

    def list_enabled_client_manifests(self, *, campaign_id: str, user_id: str | None = None, entrypoint: str = "game") -> list[dict]:
        """Return sanitized client manifests for modules enabled on a campaign.

        The payload intentionally exposes only declarative metadata and cache-busted
        asset URLs needed by the browser module API. It does not expose package
        directories or raw installed records.
        """
        out: list[dict] = []
        for entry in self.list_enabled_assets(campaign_id=campaign_id, entrypoint=entrypoint):
            pair = self._enabled_record_manifest(entry["module_id"])
            if pair is None:
                continue
            _, manifest = pair
            version = manifest.version or "0"
            out.append(
                {
                    "id": manifest.id,
                    "name": manifest.name or manifest.id,
                    "version": version,
                    "apiVersion": manifest.api_version or "1",
                    "capabilities": list(manifest.capabilities),
                    "hooks": list(manifest.hooks),
                    "dependencies": manifest.dependency_ids(),
                    "conflicts": manifest.conflict_ids(),
                    "loadOrder": manifest.load_order,
                                                                                       
                    "settings": list(manifest.settings),
                    "settingValues": self.settings.effective_values(
                        manifest=manifest, campaign_id=campaign_id, user_id=user_id
                    ),
                    "entrypoint": entrypoint,
                    "styles": [f"/modules/{manifest.id}/asset/{path}?v={version}" for path in entry["styles"]],
                    "scripts": [f"/modules/{manifest.id}/asset/{path}?v={version}" for path in entry["scripts"]],
                }
            )
        return out

    def resolve(self, module_id: str, relative_path: str) -> tuple[Path, str] | None:
        pair = self._enabled_record_manifest(module_id)
        if pair is None:
            return None
        record, manifest = pair
        relative = relative_path.lstrip("/")
        declared = set(manifest.entrypoint_paths())
        if relative not in declared:
            return None
        base = module_loader.MODULES_DIR / record["package_dir"]
        path = safe_join(base, relative)
        if path is None or not path.is_file():
            return None
        content_type = _CONTENT_TYPES.get(path.suffix.lower())
        if content_type is None:
            return None
        return path, content_type


def _order_module_pairs(pairs: list[tuple[dict, ModuleManifest]]) -> list[tuple[dict, ModuleManifest]]:
    """Sort modules deterministically, honoring dependencies when both are enabled."""
    by_id = {manifest.id: (record, manifest) for record, manifest in pairs}
    base_order = sorted(
        by_id,
        key=lambda module_id: (
            by_id[module_id][1].load_order,
            (by_id[module_id][1].name or module_id).lower(),
            module_id,
        ),
    )
    visited: set[str] = set()
    visiting: set[str] = set()
    ordered: list[str] = []

    def visit(module_id: str) -> None:
        if module_id in visited:
            return
        if module_id in visiting:
                                                                               
                                                                             
                                                           
            return
        visiting.add(module_id)
        manifest = by_id[module_id][1]
        for dependency_id in manifest.dependency_ids():
            if dependency_id in by_id:
                visit(dependency_id)
        visiting.remove(module_id)
        visited.add(module_id)
        ordered.append(module_id)

    for module_id in base_order:
        visit(module_id)
    return [by_id[module_id] for module_id in ordered]
