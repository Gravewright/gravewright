"""Read-only access to a package's declared front-end assets.

The core serves only the files a manifest *declares* (entrypoint styles/scripts
and ``provides.assets`` paths) from the package directory — a whitelist — so a
package can ship its own UI without inflating the core bundle. This layer is
descriptive: it never executes anything server-side, it only serves static
files and composes the per-campaign client manifest list.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.engine.sdk import package_registry
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk.package_locale_service import PackageLocaleService
from app.engine.sdk.package_manifest import PackageManifest
from app.engine.sdk.package_paths import safe_join
from app.engine.sdk.package_settings_service import PackageSettingsService
from app.persistence.repositories.campaign_package_repository import (
    CampaignPackageRepository,
)
from app.persistence.repositories.campaign_repository import CampaignRepository

_STATUS_ENABLED = "enabled"

_CONTENT_TYPES = {
    ".css": "text/css",
    ".js": "application/javascript",
    ".mjs": "application/javascript",
    ".json": "application/json",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".gif": "image/gif",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
}


class PackageAssetService:
    def __init__(self) -> None:
        self.install = PackageInstallService()
        self.campaigns = CampaignRepository()
        self.campaign_packages = CampaignPackageRepository()
        self.settings = PackageSettingsService()
        self.locales = PackageLocaleService()

    # --- single-asset serving --------------------------------------------------

    def _enabled_record_manifest(self, package_id: str) -> tuple[dict, PackageManifest] | None:
        record = self.install.get(package_id)
        if record is None or record["status"] != _STATUS_ENABLED:
            return None
        try:
            manifest = PackageManifest.from_dict(json.loads(record["manifest_json"]))
        except (TypeError, ValueError):
            return None
        return record, manifest

    def resolve(self, package_id: str, relative_path: str) -> tuple[Path, str] | None:
        """Resolve a *declared* asset to an on-disk path + content type, or None."""
        pair = self._enabled_record_manifest(package_id)
        if pair is None:
            return None
        record, manifest = pair
        relative = relative_path.lstrip("/")
        if relative not in set(manifest.referenced_paths()):
            return None
        content_type = _CONTENT_TYPES.get(Path(relative).suffix.lower())
        if content_type is None:
            return None
        base = package_registry.PACKAGES_DIR / record["package_dir"]
        path = safe_join(base, relative)
        if path is None or not path.is_file():
            return None
        return path, content_type

    # --- per-campaign composition ---------------------------------------------

    def _ordered_active_package_ids(self, campaign_id: str) -> list[str]:
        """Active package ids in load order: ruleset, libraries, then the rest."""
        ids: list[str] = []
        campaign = self.campaigns.get(campaign_id)
        ruleset_id = campaign.get("active_system_id") if campaign else None
        if ruleset_id and self.install.get(ruleset_id):
            ids.append(ruleset_id)
        # Globally-enabled libraries are passive dependencies, loaded early.
        for record in self.install.installed.list_by_kind("library"):
            if record["status"] == _STATUS_ENABLED and record["id"] not in ids:
                ids.append(record["id"])
        for row in self.campaign_packages.list_for_campaign(campaign_id):
            if row["package_id"] not in ids:
                ids.append(row["package_id"])
        return ids

    def list_assets_for_campaign(self, campaign_id: str, entrypoint: str = "game") -> list[dict]:
        out: list[dict] = []
        for package_id in self._ordered_active_package_ids(campaign_id):
            pair = self._enabled_record_manifest(package_id)
            if pair is None:
                continue
            _, manifest = pair
            styles = manifest.entrypoint_styles(entrypoint)
            scripts = manifest.entrypoint_scripts(entrypoint)
            if not styles and not scripts:
                continue
            version = manifest.version or "0"
            out.append(
                {
                    "package_id": manifest.id,
                    "kind": manifest.kind,
                    "version": version,
                    "styles": [self._asset_url(manifest.id, p, version) for p in styles],
                    "scripts": [self._asset_url(manifest.id, p, version) for p in scripts],
                }
            )
        return out

    def list_client_manifests(
        self,
        campaign_id: str,
        user_id: str | None = None,
        entrypoint: str = "game",
        locale: str = "en",
    ) -> list[dict]:
        out: list[dict] = []
        for package_id in self._ordered_active_package_ids(campaign_id):
            pair = self._enabled_record_manifest(package_id)
            if pair is None:
                continue
            _, manifest = pair
            # Client manifests describe a package to the browser SDK runtime
            # (kind, capabilities, settings). Scripts/styles are loaded by the
            # page as <script>/<link> tags via ``list_assets_for_campaign``, so
            # they are intentionally not duplicated here.
            out.append(
                {
                    "id": manifest.id,
                    "kind": manifest.kind,
                    "version": manifest.version or "0",
                    "capabilities": list(manifest.capabilities),
                    "settingDefinitions": self.settings.definitions(manifest.id),
                    "settingValues": self.settings.effective_values(manifest.id, campaign_id, user_id),
                    "locale": self.locales.get_locale(manifest.id, locale),
                }
            )
        return out

    @staticmethod
    def _asset_url(package_id: str, relative: str, version: str) -> str:
        return f"/sdk/packages/{package_id}/asset/{relative}?v={version}"
