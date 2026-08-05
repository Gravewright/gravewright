from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.infrastructure.images.image_decoder import ImageDecoder
from app.infrastructure.storage.local_journal_asset_storage import LocalJournalAssetStorage
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.journal_asset_repository import JournalAssetRepository
from app.persistence.repositories.journal_repository import JournalRepository

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_DIMENSION = 8_000
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
                                                                       
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
VALID_PURPOSES = {"journal_image", "journal_cover", "quest_image", "quest_board_image"}


def asset_src(asset_id: str) -> str:
    return f"/game/journal/asset/{asset_id}"


@dataclass(frozen=True)
class JournalAssetResult:
    success: bool
    asset_id: str | None = None
    src: str | None = None
    width: int | None = None
    height: int | None = None
    error_key: str | None = None


class JournalAssetService:
    def __init__(
        self,
        *,
        assets: JournalAssetRepository | None = None,
        campaigns: CampaignRepository | None = None,
        storage: LocalJournalAssetStorage | None = None,
        image_decoder: ImageDecoder | None = None,
    ) -> None:
        self.assets = assets or JournalAssetRepository()
        self.campaigns = campaigns or CampaignRepository()
        self.journals = JournalRepository()
        self.storage = storage or LocalJournalAssetStorage()
        self.image_decoder = image_decoder or ImageDecoder()

    def upload_image(
        self,
        *,
        journal_id: str,
        user_id: str,
        filename: str,
        content_type: str,
        data: bytes,
        purpose: str = "journal_image",
    ) -> JournalAssetResult:
        journal = self.journals.get_by_id(journal_id)
        if journal is None or journal["status"] != "active":
            return JournalAssetResult(success=False, error_key="game.journal.errors.not_found")

        campaign = self.campaigns.get_for_user(campaign_id=journal["campaign_id"], user_id=user_id)
        if campaign is None:
            return JournalAssetResult(success=False, error_key="game.journal.errors.not_found")

                                                                               
                                                                            
                                                                                 
                                                   
        from app.engine.journals.journal_service import JournalService

        if not JournalService().can_edit_journal(journal=dict(journal), campaign=dict(campaign), user_id=user_id):
            return JournalAssetResult(success=False, error_key="game.journal.errors.not_owner")

        campaign_id = journal["campaign_id"]

        error = self._validate(filename=filename, content_type=content_type, data=data)
        if error is not None:
            return JournalAssetResult(success=False, error_key=error)

        try:
            decoded = self.image_decoder.decode(data)
        except ValueError:
            return JournalAssetResult(success=False, error_key="game.journal.assets.errors.invalid_image")

        if decoded.format.upper() not in ALLOWED_FORMATS:
            return JournalAssetResult(success=False, error_key="game.journal.assets.errors.unsupported_type")
        if decoded.width > MAX_IMAGE_DIMENSION or decoded.height > MAX_IMAGE_DIMENSION:
            return JournalAssetResult(success=False, error_key="game.journal.assets.errors.too_large")

        purpose = purpose if purpose in VALID_PURPOSES else "journal_image"
        asset = self.assets.create(
            campaign_id=campaign_id,
            journal_id=journal_id,
            owner_user_id=user_id,
            purpose=purpose,
            filename=filename[:255],
            content_type=content_type,
            byte_size=len(data),
            width=decoded.width,
            height=decoded.height,
            storage_path="",                                 
            hash=hashlib.sha256(data).hexdigest(),
        )
                                                                            
        storage_path = self.storage.write_image(
            campaign_id=campaign_id,
            asset_id=asset["id"],
            filename=filename,
            data=data,
        )
        self._set_storage_path(asset_id=asset["id"], storage_path=storage_path)

        return JournalAssetResult(
            success=True,
            asset_id=asset["id"],
            src=asset_src(asset["id"]),
            width=decoded.width,
            height=decoded.height,
        )

    def _validate(self, *, filename: str, content_type: str, data: bytes) -> str | None:
        if not data:
            return "game.journal.assets.errors.empty"
        if len(data) > MAX_UPLOAD_BYTES:
            return "game.journal.assets.errors.too_large"
        if content_type not in ALLOWED_CONTENT_TYPES:
            return "game.journal.assets.errors.unsupported_type"
        if not filename.lower().endswith(ALLOWED_EXTENSIONS):
            return "game.journal.assets.errors.unsupported_type"
        return None

    def _set_storage_path(self, *, asset_id: str, storage_path: str) -> None:
        self.assets.update_storage_path(asset_id=asset_id, storage_path=storage_path)
