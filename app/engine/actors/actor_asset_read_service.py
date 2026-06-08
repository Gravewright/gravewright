from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.business.permissions import PermissionService
from app.domain.permissions.permissions import TablePermission
from app.engine.actors.actor_permissions import can_view_actor
from app.helpers.env import PROJECT_ROOT
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.token_repository import TokenRepository


@dataclass(frozen=True)
class ActorAssetReadResult:
    success: bool
    path: Path | None = None
    media_type: str | None = None
    error_key: str | None = None


class ActorAssetReadService:
    def __init__(
        self,
        *,
        actors: ActorRepository | None = None,
        campaigns: CampaignRepository | None = None,
        tokens: TokenRepository | None = None,
        permissions: PermissionService | None = None,
    ) -> None:
        self.actors = actors or ActorRepository()
        self.campaigns = campaigns or CampaignRepository()
        self.tokens = tokens or TokenRepository()
        self.permissions = permissions or PermissionService()

    def get_image(
        self,
        *,
        actor_id: str,
        user_id: str,
        kind: str,
        project_root: Path = PROJECT_ROOT,
    ) -> ActorAssetReadResult:
        if kind not in {"portrait", "token"}:
            return ActorAssetReadResult(success=False, error_key="not_found")

        actor = self.actors.get(actor_id)
        if actor is None or actor["status"] != "active":
            return ActorAssetReadResult(success=False, error_key="not_found")

        campaign = self.campaigns.get_for_user(
            campaign_id=actor["campaign_id"],
            user_id=user_id,
        )
        if campaign is None:
            return ActorAssetReadResult(success=False, error_key="not_authorized")

        if not self._can_serve_actor_image(
            actor=dict(actor),
            campaign=dict(campaign),
            user_id=user_id,
            kind=kind,
        ):
            return ActorAssetReadResult(success=False, error_key="not_authorized")

        storage_path = actor[f"{kind}_asset_id"]
        if not storage_path:
            return ActorAssetReadResult(success=False, error_key="not_found")

        path = (project_root / storage_path).resolve()
        expected_dir = (
            project_root / "storage" / "actor-assets" / actor["campaign_id"] / actor_id
        ).resolve()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }
        media_type = media_types.get(path.suffix.lower())
        if path.parent != expected_dir or path.stem != kind or media_type is None or not path.is_file():
            return ActorAssetReadResult(success=False, error_key="not_found")

        return ActorAssetReadResult(success=True, path=path, media_type=media_type)

    def _can_serve_actor_image(
        self,
        *,
        actor: dict,
        campaign: dict,
        user_id: str,
        kind: str,
    ) -> bool:
        if can_view_actor(actor=actor, campaign=campaign, user_id=user_id):
            return True

        if not self.permissions.can(
            user_id=user_id,
            campaign_id=actor["campaign_id"],
            permission=TablePermission.SCENE_VIEW,
        ):
            return False

        return self._is_actor_asset_used_by_visible_token(actor=actor, kind=kind)

    def _is_actor_asset_used_by_visible_token(self, *, actor: dict, kind: str) -> bool:
        if kind == "token":
            if not actor.get("token_asset_id"):
                return False
        elif kind == "portrait":
            if actor.get("token_asset_id") or not actor.get("portrait_asset_id"):
                return False
        else:
            return False

        return any(
            not token.get("hidden")
            for token in self.tokens.list_by_actor(actor["id"])
        )
