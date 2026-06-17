"""Upload + validation of an actor's portrait/token image (Gravewright SDK).

Mirrors :class:`JournalAssetService`, simplified: one image per actor per kind,
stored at a deterministic path (no asset table). The relative storage path is
written back to ``actors_core.{portrait,token}_asset_id``; the serve route and
the URL helpers (:mod:`actor_asset_urls`) read it from there.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.engine.actors.actor_asset_urls import actor_image_url
from app.engine.actors.actor_permissions import can_edit_actor
from app.infrastructure.images.image_decoder import ImageDecoder
from app.infrastructure.storage.local_actor_asset_storage import LocalActorAssetStorage
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_DIMENSION = 4_000
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
                                                       
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
VALID_KINDS = {"portrait", "token"}


@dataclass(frozen=True)
class ActorAssetResult:
    success: bool
    actor_id: str | None = None
    campaign_id: str | None = None
    kind: str | None = None
    url: str | None = None
    error_key: str | None = None


class ActorAssetService:
    def __init__(
        self,
        *,
        actors: ActorRepository | None = None,
        campaigns: CampaignRepository | None = None,
        storage: LocalActorAssetStorage | None = None,
        image_decoder: ImageDecoder | None = None,
    ) -> None:
        self.actors = actors or ActorRepository()
        self.campaigns = campaigns or CampaignRepository()
        self.storage = storage or LocalActorAssetStorage()
        self.image_decoder = image_decoder or ImageDecoder()

    def upload_image(
        self,
        *,
        actor_id: str,
        user_id: str,
        kind: str,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> ActorAssetResult:
        if kind not in VALID_KINDS:
            return ActorAssetResult(
                success=False, error_key="game.actors.image.errors.invalid_kind"
            )

        actor = self.actors.get(actor_id)
        if actor is None or actor["status"] != "active":
            return ActorAssetResult(success=False, error_key="game.actors.errors.not_found")
        campaign = self.campaigns.get_for_user(campaign_id=actor["campaign_id"], user_id=user_id)
        if campaign is None:
            return ActorAssetResult(success=False, error_key="game.actors.errors.not_found")
        if not can_edit_actor(actor=actor, campaign=dict(campaign), user_id=user_id):
            return ActorAssetResult(success=False, error_key="game.actors.errors.not_allowed")

        error = self._validate(filename=filename, content_type=content_type, data=data)
        if error is not None:
            return ActorAssetResult(success=False, error_key=error)

        try:
            decoded = self.image_decoder.decode(data)
        except ValueError:
            return ActorAssetResult(
                success=False, error_key="game.actors.image.errors.invalid_image"
            )
        if decoded.format.upper() not in ALLOWED_FORMATS:
            return ActorAssetResult(
                success=False, error_key="game.actors.image.errors.unsupported_type"
            )
        if decoded.width > MAX_IMAGE_DIMENSION or decoded.height > MAX_IMAGE_DIMENSION:
            return ActorAssetResult(success=False, error_key="game.actors.image.errors.too_large")

        storage_path = self.storage.write_image(
            campaign_id=actor["campaign_id"],
            actor_id=actor_id,
            kind=kind,
            filename=filename,
            data=data,
        )
        self.actors.set_asset(actor_id=actor_id, kind=kind, storage_path=storage_path)

        refreshed = self.actors.get(actor_id) or actor
        return ActorAssetResult(
            success=True,
            actor_id=actor_id,
            campaign_id=actor["campaign_id"],
            kind=kind,
            url=actor_image_url(refreshed, kind),
        )

    def _validate(self, *, filename: str, content_type: str, data: bytes) -> str | None:
        if not data:
            return "game.actors.image.errors.empty"
        if len(data) > MAX_UPLOAD_BYTES:
            return "game.actors.image.errors.too_large"
        if content_type not in ALLOWED_CONTENT_TYPES:
            return "game.actors.image.errors.unsupported_type"
        if not filename.lower().endswith(ALLOWED_EXTENSIONS):
            return "game.actors.image.errors.unsupported_type"
        return None
