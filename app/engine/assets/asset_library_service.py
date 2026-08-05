from __future__ import annotations

import hashlib
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any

from app.infrastructure.images.image_decoder import ImageDecoder
from app.infrastructure.storage.local_asset_storage import LocalAssetStorage
from app.persistence.repositories.asset_repository import AssetFolderRepository
from app.persistence.repositories.asset_repository import AssetRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.security.asset_permissions import can_manage_assets
from app.security.asset_permissions import can_view_assets

MAX_ASSET_BYTES = 10 * 1024 * 1024
MAX_ASSET_DIMENSION = 8_000
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def asset_src(asset_id: str) -> str:
    return f"/game/assets/file/{asset_id}"


@dataclass(frozen=True)
class AssetResult:
    success: bool
    payload: dict[str, Any] = field(default_factory=dict)
    error_key: str | None = None


class AssetLibraryService:
    """Manages the dedicated asset library: folders and reusable images."""

    def __init__(
        self,
        *,
        assets: AssetRepository | None = None,
        folders: AssetFolderRepository | None = None,
        campaigns: CampaignRepository | None = None,
        storage: LocalAssetStorage | None = None,
        image_decoder: ImageDecoder | None = None,
    ) -> None:
        self.assets = assets or AssetRepository()
        self.folders = folders or AssetFolderRepository()
        self.campaigns = campaigns or CampaignRepository()
        self.storage = storage or LocalAssetStorage()
        self.image_decoder = image_decoder or ImageDecoder(max_dimension=MAX_ASSET_DIMENSION)

    def get_state(self, *, campaign_id: str, user_id: str) -> AssetResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        if not can_view_assets(actor_role=role):
            return AssetResult(success=False, error_key="game.assets.errors.not_found")
        assets = [self._present_asset(asset) for asset in self.assets.list_for_campaign(campaign_id=campaign_id)]
        folders = self.folders.list_for_campaign(campaign_id=campaign_id)
        return AssetResult(success=True, payload={"campaign_id": campaign_id, "folders": folders, "assets": assets})

    def create_folder(self, *, campaign_id: str, user_id: str, name: str, parent_id: str | None = None) -> AssetResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        if not can_manage_assets(actor_role=role):
            return AssetResult(success=False, error_key="permissions.errors.denied")
        if parent_id:
            parent = self.folders.get(parent_id)
            if parent is None or parent.get("campaign_id") != campaign_id:
                return AssetResult(success=False, error_key="game.assets.errors.folder_not_found")
        folder = self.folders.create(campaign_id=campaign_id, parent_id=parent_id, name=name)
        return AssetResult(success=True, payload={"folder": folder})

    def move_asset(self, *, campaign_id: str, user_id: str, asset_id: str, folder_id: str | None) -> AssetResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        if not can_manage_assets(actor_role=role):
            return AssetResult(success=False, error_key="permissions.errors.denied")
        asset = self.assets.get_by_id(asset_id)
        if asset is None or asset.get("campaign_id") != campaign_id:
            return AssetResult(success=False, error_key="game.assets.errors.asset_not_found")
        if folder_id:
            folder = self.folders.get(folder_id)
            if folder is None or folder.get("campaign_id") != campaign_id:
                return AssetResult(success=False, error_key="game.assets.errors.folder_not_found")
        updated = self.assets.update_folder(asset_id=asset_id, folder_id=folder_id)
        if updated is None:
            return AssetResult(success=False, error_key="game.assets.errors.asset_not_found")
        return AssetResult(success=True, payload={"asset": self._present_asset(updated)})

    def delete_asset(self, *, campaign_id: str, user_id: str, asset_id: str) -> AssetResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        if not can_manage_assets(actor_role=role):
            return AssetResult(success=False, error_key="permissions.errors.denied")
        asset = self.assets.get_by_id(asset_id)
        if asset is None or asset.get("campaign_id") != campaign_id:
            return AssetResult(success=False, error_key="game.assets.errors.asset_not_found")
        storage_path = asset.get("storage_path")
        if storage_path:
            try:
                self.storage.delete(storage_path)
            except ValueError:
                # Legacy rows may point outside the library storage root; drop the
                # database entry anyway and leave the stray file untouched.
                pass
        self.assets.delete(asset_id)
        return AssetResult(success=True, payload={"asset_id": asset_id})

    def upload_asset(
        self,
        *,
        campaign_id: str,
        user_id: str,
        filename: str,
        content_type: str,
        data: bytes,
        folder_id: str | None = None,
    ) -> AssetResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        if not can_manage_assets(actor_role=role):
            return AssetResult(success=False, error_key="permissions.errors.denied")
        if folder_id:
            folder = self.folders.get(folder_id)
            if folder is None or folder.get("campaign_id") != campaign_id:
                return AssetResult(success=False, error_key="game.assets.errors.folder_not_found")
        created = self.create_asset(
            campaign_id=campaign_id,
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            data=data,
            folder_id=folder_id,
        )
        if not created.success:
            return created
        return AssetResult(success=True, payload={"asset": self._present_asset(created.payload["asset"])})

    def create_asset(
        self,
        *,
        campaign_id: str,
        user_id: str,
        filename: str,
        content_type: str,
        data: bytes,
        folder_id: str | None = None,
    ) -> AssetResult:
        """Validate, decode and persist a library asset. Returns ``asset`` and ``decoded``."""
        error = self._validate(filename=filename, content_type=content_type, data=data)
        if error is not None:
            return AssetResult(success=False, error_key=error)
        try:
            decoded = self.image_decoder.decode(data)
        except ValueError:
            return AssetResult(success=False, error_key="game.assets.errors.invalid_image")
        if decoded.format.upper() not in ALLOWED_FORMATS:
            return AssetResult(success=False, error_key="game.assets.errors.unsupported_type")

        safe_filename = self._safe_filename(filename)
        digest = hashlib.sha256(data).hexdigest()
        asset = self.assets.create(
            campaign_id=campaign_id,
            owner_user_id=user_id,
            filename=safe_filename,
            content_type=content_type,
            byte_size=len(data),
            width=decoded.width,
            height=decoded.height,
            storage_path="",
            hash=digest,
            folder_id=folder_id,
        )
        storage_path = self.storage.write_image(
            campaign_id=campaign_id,
            asset_id=asset["id"],
            filename=safe_filename,
            data=data,
        )
        self.assets.update_storage_path(asset_id=asset["id"], storage_path=storage_path)
        asset = {**asset, "storage_path": storage_path}
        return AssetResult(success=True, payload={"asset": asset, "decoded": decoded})

    def _role(self, *, campaign_id: str, user_id: str) -> str | None:
        return self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)

    def _present_asset(self, asset: dict) -> dict:
        return {**asset, "src": asset_src(asset["id"])}

    def _validate(self, *, filename: str, content_type: str, data: bytes) -> str | None:
        if not data:
            return "game.assets.errors.empty"
        if len(data) > MAX_ASSET_BYTES:
            return "game.assets.errors.too_large"
        if content_type not in ALLOWED_CONTENT_TYPES:
            return "game.assets.errors.unsupported_type"
        if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
            return "game.assets.errors.unsupported_type"
        return None

    def _safe_filename(self, filename: str) -> str:
        name = Path(filename.replace("\\", "/")).name
        stem = Path(name).stem[:80] or "image"
        extension = Path(name).suffix.lower()
        safe_stem = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in stem)
        return f"{safe_stem}{extension}"
