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
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from app.persistence.database import engine_begin
from app.persistence.tables import scene_spatial_sounds, sound_playlists, soundscapes, sounds

MAX_ASSET_BYTES = 10 * 1024 * 1024
MAX_AUDIO_BYTES = 100 * 1024 * 1024
MAX_ASSET_DIMENSION = 8_000





MAX_PDF_BYTES = 25 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "audio/ogg", "audio/opus", "audio/mpeg", "audio/mp4", "audio/wav"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".ogg", ".opus", ".mp3", ".m4a", ".wav"}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}





PDF_CONTENT_TYPE = "application/pdf"
PDF_EXTENSION = ".pdf"
PDF_MAGIC = b"%PDF-"


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
        stored_assets = self.assets.list_for_campaign(campaign_id=campaign_id)
        audio_kinds: dict[str, set[str]] = {}
        with engine_begin() as db:
            for row in db.execute(
                select(sounds.c.asset_id, sounds.c.kind).where(sounds.c.campaign_id == campaign_id)
            ).mappings():
                audio_kinds.setdefault(str(row["asset_id"]), set()).add(str(row["kind"]))
        assets = [
            self._present_asset(asset, audio_kinds=sorted(audio_kinds.get(str(asset.get("id")), set())))
            for asset in stored_assets
        ]
        folders = self.folders.list_for_campaign(campaign_id=campaign_id)
        return AssetResult(
            success=True, payload={"campaign_id": campaign_id, "folders": folders, "assets": assets}
        )

    def create_folder(
        self, *, campaign_id: str, user_id: str, name: str, parent_id: str | None = None
    ) -> AssetResult:
        role = self._role(campaign_id=campaign_id, user_id=user_id)
        if not can_manage_assets(actor_role=role):
            return AssetResult(success=False, error_key="permissions.errors.denied")
        if parent_id:
            parent = self.folders.get(parent_id)
            if parent is None or parent.get("campaign_id") != campaign_id:
                return AssetResult(success=False, error_key="game.assets.errors.folder_not_found")
        folder = self.folders.create(campaign_id=campaign_id, parent_id=parent_id, name=name)
        return AssetResult(success=True, payload={"folder": folder})

    def move_asset(
        self, *, campaign_id: str, user_id: str, asset_id: str, folder_id: str | None
    ) -> AssetResult:
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
        with engine_begin() as db:
            semantic=list(db.execute(select(sounds.c.id,sounds.c.version).where(sounds.c.campaign_id==campaign_id,sounds.c.asset_id==asset_id)).mappings())
            for sound in semantic:
                needle=f'"soundId":"{sound["id"]}"'
                dependencies=db.execute(select(func.count()).select_from(scene_spatial_sounds).where(scene_spatial_sounds.c.sound_id==sound["id"])).scalar_one()
                dependencies+=db.execute(select(func.count()).select_from(sound_playlists).where(sound_playlists.c.campaign_id==campaign_id,sound_playlists.c.entries_json.contains(needle))).scalar_one()
                dependencies+=db.execute(select(func.count()).select_from(soundscapes).where(soundscapes.c.campaign_id==campaign_id,(soundscapes.c.layers_json.contains(needle))|(soundscapes.c.random_pools_json.contains(sound["id"])))).scalar_one()
                if dependencies:return AssetResult(success=False,error_key="game.assets.errors.asset_in_use")
        if semantic:
            from app.engine.audio.sound_domain_service import SoundDomainService
            domain=SoundDomainService()
            for sound in semantic:
                removed=domain.delete_sound(campaign_id=campaign_id,user_id=user_id,sound_id=sound["id"],expected_version=sound["version"])
                if not removed.success:return AssetResult(success=False,error_key="game.assets.errors.asset_in_use")
        try:deleted=self.assets.delete(asset_id)
        except IntegrityError:return AssetResult(success=False,error_key="game.assets.errors.asset_in_use")
        if not deleted:return AssetResult(success=False,error_key="game.assets.errors.asset_in_use")
        storage_path = asset.get("storage_path")
        if storage_path:
            try:self.storage.delete(storage_path)
            except ValueError:pass
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
        return AssetResult(
            success=True, payload={"asset": self._present_asset(created.payload["asset"])}
        )

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

        decoded = None
        if not self._is_pdf(filename=filename, content_type=content_type) and not content_type.startswith("audio/"):
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


            width=decoded.width if decoded else None,
            height=decoded.height if decoded else None,
            storage_path="",
            hash=digest,
            folder_id=folder_id,
        )
        storage_path = ""
        try:
            storage_path = self.storage.write_image(
                campaign_id=campaign_id, asset_id=asset["id"], filename=safe_filename, data=data,
            )
            self.assets.update_storage_path(asset_id=asset["id"], storage_path=storage_path)
        except Exception:
            self.assets.delete(asset["id"])
            if storage_path:
                try:
                    self.storage.delete(storage_path)
                except (OSError, ValueError):
                    pass
            raise
        asset = {**asset, "storage_path": storage_path}
        return AssetResult(success=True, payload={"asset": asset, "decoded": decoded})

    def _role(self, *, campaign_id: str, user_id: str) -> str | None:
        return self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)

    def _present_asset(self, asset: dict, *, audio_kinds: list[str] | None = None) -> dict:
        kind = "pdf" if asset.get("content_type") == PDF_CONTENT_TYPE else "audio" if str(asset.get("content_type") or "").startswith("audio/") else "image"
        return {
            key: asset.get(key)
            for key in ("id", "campaign_id", "owner_user_id", "folder_id", "filename", "content_type", "byte_size", "width", "height", "created_at")
        } | {"src": asset_src(asset["id"]), "kind": kind, "audio_kinds": audio_kinds or []}

    def _is_pdf(self, *, filename: str, content_type: str) -> bool:
        return (
            content_type == PDF_CONTENT_TYPE
            and Path(filename).suffix.lower() == PDF_EXTENSION
        )

    def _validate(self, *, filename: str, content_type: str, data: bytes) -> str | None:
        if not data:
            return "game.assets.errors.empty"

        if self._is_pdf(filename=filename, content_type=content_type):
            if len(data) > MAX_PDF_BYTES:
                return "game.assets.errors.too_large"


            if not data.startswith(PDF_MAGIC):
                return "game.assets.errors.unsupported_type"
            return None

        max_bytes = MAX_AUDIO_BYTES if content_type.startswith("audio/") else MAX_ASSET_BYTES
        if len(data) > max_bytes:
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
