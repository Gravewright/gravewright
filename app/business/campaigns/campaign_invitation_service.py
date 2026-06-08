from __future__ import annotations

import re
from dataclasses import dataclass, field
from app.persistence.rows import Row
from typing import Any

from app.business.permissions import PermissionService
from app.domain.permissions.permissions import TablePermission
from app.domain.roles import PlayerRole
from app.persistence.repositories.campaign_invitation_repository import CampaignInvitationRepository
from app.persistence.repositories.campaign_repository import CampaignRepository


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

INVITABLE_ROLES = {
    PlayerRole.ASSISTANT_GM.value,
    PlayerRole.PLAYER.value,
    PlayerRole.STREAMER.value,
}


@dataclass(frozen=True)
class CampaignInvitationResult:
    success: bool
    message_key: str | None = None
    error_key: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


class CampaignInvitationService:
    def __init__(self) -> None:
        self.campaigns = CampaignRepository()
        self.invitations = CampaignInvitationRepository()
        self.permissions = PermissionService()

    def list_pending_for_user(self, user_id: str) -> list[Row]:
        return self.invitations.list_pending_for_user(user_id)

    def create_invitation(
        self,
        *,
        campaign_id: str,
        invited_by_user_id: str,
        invited_email: str,
        role: str,
    ) -> CampaignInvitationResult:
        normalized_email = invited_email.strip().lower()
        normalized_role = role.strip()

        if not EMAIL_RE.match(normalized_email):
            return CampaignInvitationResult(
                success=False,
                error_key="game.invite.errors.invalid_email",
            )

        if normalized_role not in INVITABLE_ROLES:
            return CampaignInvitationResult(
                success=False,
                error_key="game.invite.errors.invalid_role",
            )

        if not self.permissions.can(
            user_id=invited_by_user_id,
            campaign_id=campaign_id,
            permission=TablePermission.CAMPAIGN_INVITE_MEMBERS,
        ):
            return CampaignInvitationResult(
                success=False,
                error_key="game.invite.errors.gm_required",
            )

        status = self.invitations.create_pending(
            campaign_id=campaign_id,
            invited_email=normalized_email,
            invited_by_user_id=invited_by_user_id,
            role=PlayerRole(normalized_role),
        )

        if status == "created":
            return CampaignInvitationResult(
                success=True,
                message_key="game.invite.success",
            )

        return CampaignInvitationResult(
            success=False,
            error_key=f"game.invite.errors.{status}",
        )

    def accept_invitation(
        self,
        *,
        invitation_id: str,
        user_id: str,
    ) -> CampaignInvitationResult:
        status = self.invitations.accept_for_user(
            invitation_id=invitation_id,
            user_id=user_id,
        )

        if status != "accepted":
            return CampaignInvitationResult(
                success=False,
                error_key=f"inside.invitations.errors.{status}",
            )

        campaign = self.invitations.get_campaign_for_user_invitation(
            invitation_id=invitation_id,
            user_id=user_id,
        )
        member = None

        if campaign is not None:
            member = self.campaigns.get_member(
                campaign_id=campaign["id"],
                user_id=user_id,
            )

        return CampaignInvitationResult(
            success=True,
            message_key="inside.invitations.accepted",
            payload={
                "campaign": dict(campaign) if campaign is not None else None,
                "member": dict(member) if member is not None else None,
            },
        )

    def decline_invitation(
        self,
        *,
        invitation_id: str,
        user_id: str,
    ) -> CampaignInvitationResult:
        status = self.invitations.decline_for_user(
            invitation_id=invitation_id,
            user_id=user_id,
        )

        if status == "declined":
            return CampaignInvitationResult(
                success=True,
                message_key="inside.invitations.declined",
            )

        return CampaignInvitationResult(
            success=False,
            error_key=f"inside.invitations.errors.{status}",
        )
