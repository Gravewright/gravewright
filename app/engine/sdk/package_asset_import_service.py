"""Materialize declared asset-package media in a campaign asset library."""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.engine.assets.asset_library_service import AssetLibraryService
from app.engine.sdk import package_registry
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.sdk.package_paths import safe_join
from app.persistence.repositories.campaign_package_repository import CampaignPackageRepository
from app.persistence.repositories.campaign_repository import CampaignRepository


_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


class PackageAssetImportService:
    """Copy supported ``provides.assets`` entries into the campaign library."""

    def __init__(
        self,
        *,
        install: PackageInstallService | None = None,
        library: AssetLibraryService | None = None,
        campaigns: CampaignRepository | None = None,
        campaign_packages: CampaignPackageRepository | None = None,
    ) -> None:
        self.install = install or PackageInstallService()
        self.library = library or AssetLibraryService()
        self.campaigns = campaigns or CampaignRepository()
        self.campaign_packages = campaign_packages or CampaignPackageRepository()

    def list_active_packages(self, *, campaign_id: str, user_id: str) -> list[dict]:
        if not self._is_gm(campaign_id=campaign_id, user_id=user_id):
            return []
        active_ids = {
            str(row["package_id"])
            for row in self.campaign_packages.list_for_campaign(campaign_id)
            if row.get("status") == "active" and row.get("activation_role") == "assets"
        }
        packages = []
        for package_id in active_ids:
            record = self.install.get(package_id)
            manifest = self.install.get_manifest(package_id)
            if record and record.get("status") == "enabled" and manifest and manifest.kind == "assets":
                packages.append({"id": package_id, "name": record.get("name") or manifest.name})
        return sorted(packages, key=lambda item: str(item["name"]).lower())

    def list_entries(self, *, campaign_id: str, package_id: str, user_id: str) -> list[dict]:
        pair = self._active_package(campaign_id=campaign_id, package_id=package_id, user_id=user_id)
        if pair is None:
            return []
        record, manifest = pair
        version = getattr(manifest, "version", "") or "0"
        entries = []
        for category, entry in manifest.provides.asset_entries():
            relative = str(entry.get("path") or "")
            if Path(relative).suffix.lower() not in _CONTENT_TYPES:
                continue
            entries.append(
                {
                    "id": str(entry.get("id") or ""),
                    "label": str(entry.get("label") or entry.get("id") or "Asset"),
                    "category": category,
                    "folder": str(entry.get("folder") or ""),
                    "path": relative,
                    "src": f"/sdk/packages/{package_id}/asset/{relative}?v={version}",
                }
            )
        return entries

    def import_entry(
        self,
        *,
        campaign_id: str,
        package_id: str,
        asset_id: str,
        user_id: str,
        folder_id: str | None = None,
    ) -> dict | None:
        pair = self._active_package(campaign_id=campaign_id, package_id=package_id, user_id=user_id)
        if pair is None:
            return None
        record, manifest = pair
        declared = next(
            (entry for _category, entry in manifest.provides.asset_entries() if entry.get("id") == asset_id),
            None,
        )
        if declared is None:
            return None
        relative = str(declared.get("path") or "")
        path = safe_join(package_registry.PACKAGES_DIR / record["package_dir"], relative)
        content_type = _CONTENT_TYPES.get(Path(relative).suffix.lower())
        if path is None or not path.is_file() or content_type is None:
            return None
        if folder_id:
            folder = self.library.folders.get(folder_id)
            if folder is None or folder.get("campaign_id") != campaign_id:
                return None
        folder_id = self._declared_folder(
            campaign_id=campaign_id,
            user_id=user_id,
            declared=str(declared.get("folder") or ""),
            parent_id=folder_id,
        )
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        duplicate = next(
            (
                asset for asset in self.library.assets.list_for_campaign(campaign_id=campaign_id)
                if asset.get("hash") == digest and (asset.get("folder_id") or None) == folder_id
            ),
            None,
        )
        if duplicate:
            return duplicate
        result = self.library.create_asset(
            campaign_id=campaign_id,
            user_id=user_id,
            filename=path.name,
            content_type=content_type,
            data=data,
            folder_id=folder_id,
        )
        return result.payload.get("asset") if result.success else None

    def _declared_folder(
        self,
        *,
        campaign_id: str,
        user_id: str,
        declared: str,
        parent_id: str | None,
    ) -> str | None:
        """Create a safe ``folder`` hierarchy declared by an asset entry."""
        parts = [part.strip()[:120] for part in declared.replace("\\", "/").split("/")]
        parts = [part for part in parts if part and part not in {".", ".."}]
        current = parent_id
        for name in parts[:8]:
            folders = self.library.folders.list_for_campaign(campaign_id=campaign_id)
            existing = next(
                (
                    folder for folder in folders
                    if (folder.get("parent_id") or None) == current and folder.get("name") == name
                ),
                None,
            )
            if existing:
                current = str(existing["id"])
                continue
            result = self.library.create_folder(
                campaign_id=campaign_id,
                user_id=user_id,
                name=name,
                parent_id=current,
            )
            if not result.success:
                return parent_id
            current = str(result.payload["folder"]["id"])
        return current

    def import_package(self, *, campaign_id: str, package_id: str, user_id: str) -> bool:
        record = self.install.get(package_id)
        manifest = self.install.get_manifest(package_id)
        if not record or not manifest or manifest.kind != "assets":
            return False

        folder_id = self._assets_folder(campaign_id=campaign_id, user_id=user_id)
        if not folder_id:
            return False

        existing = self.library.assets.list_for_campaign(campaign_id=campaign_id)
        known = {
            (str(asset.get("hash") or ""), str(asset.get("folder_id") or ""))
            for asset in existing
        }
        base = package_registry.PACKAGES_DIR / record["package_dir"]

        for _category, entry in manifest.provides.asset_entries():
            relative = str(entry.get("path") or "")
            path = safe_join(base, relative)
            content_type = _CONTENT_TYPES.get(Path(relative).suffix.lower())
            if path is None or not path.is_file() or content_type is None:
                continue
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if (digest, folder_id) in known:
                continue
            result = self.library.create_asset(
                campaign_id=campaign_id,
                user_id=user_id,
                filename=path.name,
                content_type=content_type,
                data=data,
                folder_id=folder_id,
            )
            if not result.success:
                return False
            known.add((digest, folder_id))
        return True

    def _is_gm(self, *, campaign_id: str, user_id: str) -> bool:
        return self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id) == "gm"

    def _active_package(self, *, campaign_id: str, package_id: str, user_id: str):
        if not self._is_gm(campaign_id=campaign_id, user_id=user_id):
            return None
        active = self.campaign_packages.get(campaign_id=campaign_id, package_id=package_id)
        if not active or active.get("status") != "active" or active.get("activation_role") != "assets":
            return None
        record = self.install.get(package_id)
        manifest = self.install.get_manifest(package_id)
        if not record or record.get("status") != "enabled" or not manifest or manifest.kind != "assets":
            return None
        return record, manifest

    def _assets_folder(self, *, campaign_id: str, user_id: str) -> str:
        folders = self.library.folders.list_for_campaign(campaign_id=campaign_id)
        existing = next(
            (
                folder
                for folder in folders
                if folder.get("parent_id") is None and folder.get("name") == "Assets"
            ),
            None,
        )
        if existing:
            return str(existing["id"])
        result = self.library.create_folder(
            campaign_id=campaign_id,
            user_id=user_id,
            name="Assets",
        )
        if not result.success:
            return ""
        return str(result.payload["folder"]["id"])
