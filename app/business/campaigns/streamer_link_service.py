from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

from app.business.permissions import PermissionService
from app.domain.permissions.permissions import TablePermission
from app.persistence.repositories.streamer_link_repository import StreamerLinkRepository


                                                                                
                                                                 
STREAMER_LINK_TTL_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class StreamerLinkResult:
    success: bool
    token: str | None = None
    expires_at: int | None = None
    error_key: str | None = None


class StreamerLinkService:
    def __init__(self) -> None:
        self.links = StreamerLinkRepository()
        self.permissions = PermissionService()

    def _can_manage(self, *, campaign_id: str, user_id: str) -> bool:
        return self.permissions.can(
            user_id=user_id,
            campaign_id=campaign_id,
            permission=TablePermission.CAMPAIGN_INVITE_MEMBERS,
        )

    def generate(self, *, campaign_id: str, user_id: str) -> StreamerLinkResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return StreamerLinkResult(success=False, error_key="game.streamer.errors.gm_required")

        token = secrets.token_urlsafe(32)
        expires_at = int(time.time()) + STREAMER_LINK_TTL_SECONDS
        link = self.links.create_active(
            campaign_id=campaign_id,
            token=token,
            created_by_user_id=user_id,
            expires_at=expires_at,
        )
        return StreamerLinkResult(
            success=True,
            token=link["token"],
            expires_at=link["expires_at"],
        )

    def get_active(self, *, campaign_id: str, user_id: str) -> StreamerLinkResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return StreamerLinkResult(success=False, error_key="game.streamer.errors.gm_required")

        link = self.links.get_active_for_campaign(campaign_id=campaign_id)
        if link is None:
            return StreamerLinkResult(success=True, token=None, expires_at=None)
        return StreamerLinkResult(success=True, token=link["token"], expires_at=link["expires_at"])

    def revoke(self, *, campaign_id: str, user_id: str) -> StreamerLinkResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return StreamerLinkResult(success=False, error_key="game.streamer.errors.gm_required")

        self.links.revoke_active_for_campaign(campaign_id=campaign_id)
        return StreamerLinkResult(success=True)

    def consume(self, *, token: str) -> dict | None:
        """Resolve a bearer token to ``{"campaign_id", "guest_user_id"}`` or None."""
        normalized = (token or "").strip()
        if not normalized:
            return None
        return self.links.consume_token(token=normalized)
