"""Bounded public presentation projection for campaign participants."""

from __future__ import annotations

from dataclasses import dataclass

from app.business.users.user_preference_service import UserPreferenceService
from app.persistence.repositories.campaign_repository import CampaignRepository


@dataclass(frozen=True)
class UserPresentationResult:
    success: bool
    presentation: dict[str, str] | None = None
    presentations: list[dict[str, str]] | None = None
    error_key: str | None = None


class UserPresentationService:
    """Expose only presentation data for members visible in one campaign."""

    def __init__(self) -> None:
        self.campaigns = CampaignRepository()
        self.preferences = UserPreferenceService()

    def get(
        self, *, campaign_id: str, requester_user_id: str, target_user_id: str
    ) -> UserPresentationResult:
        if self.campaigns.get_member(
            campaign_id=campaign_id, user_id=requester_user_id
        ) is None:
            return UserPresentationResult(False, error_key="sdk.runtime.permission_denied")
        if self.campaigns.get_member(campaign_id=campaign_id, user_id=target_user_id) is None:
            return UserPresentationResult(False, error_key="sdk.runtime.not_found")
        return UserPresentationResult(
            True,
            presentation={
                "userId": target_user_id,
                "color": self.preferences.get_ping_color(target_user_id),
            },
        )

    def list(
        self, *, campaign_id: str, requester_user_id: str
    ) -> UserPresentationResult:
        members = self.campaigns.list_members(campaign_id=campaign_id)
        if not any(member["user_id"] == requester_user_id for member in members):
            return UserPresentationResult(False, error_key="sdk.runtime.permission_denied")
        user_ids = [str(member["user_id"]) for member in members]
        colors = self.preferences.get_ping_colors(user_ids)
        return UserPresentationResult(
            True,
            presentations=[
                {"userId": user_id, "color": colors[user_id]} for user_id in user_ids
            ],
        )
