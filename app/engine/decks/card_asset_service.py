from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from app.domain.roles import PlayerRole
from app.engine.journals.journal_asset_service import asset_src
from app.infrastructure.images.image_decoder import ImageDecoder
from app.infrastructure.storage.local_journal_asset_storage import LocalJournalAssetStorage
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.journal_asset_repository import JournalAssetRepository

MAX_CARD_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_CARD_IMAGE_DIMENSION = 8_000
ALLOWED_CARD_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_CARD_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_CARD_FORMATS = {"JPEG", "PNG", "WEBP"}
VALID_CARD_PURPOSES = {"card_front", "card_back"}


@dataclass(frozen=True)
class CardAssetResult:
    success: bool
    asset_id: str | None = None
    src: str | None = None
    width: int | None = None
    height: int | None = None
    content_type: str | None = None
    byte_size: int | None = None
    sha256: str | None = None
    error_key: str | None = None


class CardAssetService:
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
        self.storage = storage or LocalJournalAssetStorage()
        self.image_decoder = image_decoder or ImageDecoder(max_dimension=MAX_CARD_IMAGE_DIMENSION)

    def upload_image(
        self,
        *,
        campaign_id: str,
        user_id: str,
        filename: str,
        content_type: str,
        data: bytes,
        purpose: str = "card_front",
    ) -> CardAssetResult:
        role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        if role not in {PlayerRole.GM.value, PlayerRole.ASSISTANT_GM.value}:
            return CardAssetResult(success=False, error_key="permissions.errors.denied")

        error = self._validate(filename=filename, content_type=content_type, data=data)
        if error is not None:
            return CardAssetResult(success=False, error_key=error)

        try:
            decoded = self.image_decoder.decode(data)
        except ValueError:
            return CardAssetResult(success=False, error_key="game.cards.assets.errors.invalid_image")

        if decoded.format.upper() not in ALLOWED_CARD_FORMATS:
            return CardAssetResult(success=False, error_key="game.cards.assets.errors.unsupported_type")

        purpose = purpose if purpose in VALID_CARD_PURPOSES else "card_front"
        safe_filename = self._safe_filename(filename)
        digest = hashlib.sha256(data).hexdigest()
        asset = self.assets.create(
            campaign_id=campaign_id,
            journal_id=None,
            owner_user_id=user_id,
            purpose=purpose,
            filename=safe_filename,
            content_type=content_type,
            byte_size=len(data),
            width=decoded.width,
            height=decoded.height,
            storage_path="",
            hash=digest,
        )
        storage_path = self.storage.write_image(
            campaign_id=campaign_id,
            asset_id=asset["id"],
            filename=safe_filename,
            data=data,
        )
        self.assets.update_storage_path(asset_id=asset["id"], storage_path=storage_path)

        return CardAssetResult(
            success=True,
            asset_id=asset["id"],
            src=asset_src(asset["id"]),
            width=decoded.width,
            height=decoded.height,
            content_type=content_type,
            byte_size=len(data),
            sha256=digest,
        )

    def _validate(self, *, filename: str, content_type: str, data: bytes) -> str | None:
        if not data:
            return "game.cards.assets.errors.empty"
        if len(data) > MAX_CARD_UPLOAD_BYTES:
            return "game.cards.assets.errors.too_large"
        if content_type not in ALLOWED_CARD_CONTENT_TYPES:
            return "game.cards.assets.errors.unsupported_type"
        if Path(filename).suffix.lower() not in ALLOWED_CARD_EXTENSIONS:
            return "game.cards.assets.errors.unsupported_type"
        return None

    def _safe_filename(self, filename: str) -> str:
        name = Path(filename.replace("\\", "/")).name
        stem = Path(name).stem[:80] or "card"
        extension = Path(name).suffix.lower()
        safe_stem = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in stem)
        return f"{safe_stem}{extension}"
