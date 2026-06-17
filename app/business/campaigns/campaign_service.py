from __future__ import annotations

from dataclasses import dataclass
from app.persistence.rows import Row

from app.domain.roles import PlayerRole
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.infrastructure.storage.local_actor_asset_storage import LocalActorAssetStorage
from app.infrastructure.storage.local_journal_asset_storage import LocalJournalAssetStorage
from app.infrastructure.storage.local_scene_asset_storage import LocalSceneAssetStorage
from app.helpers.codes import generate_removal_code
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_repository import SceneRepository


DELETE_CODE_TTL_SECONDS = 10 * 60


@dataclass(frozen=True)
class CampaignResult:
    success: bool
    campaign: Row | None = None
    removal_code: str | None = None
    member: Row | None = None
    room_user_ids: list[str] | None = None
    error_key: str | None = None


class CampaignService:
    def __init__(
        self,
        *,
        campaigns: CampaignRepository | None = None,
        scenes: SceneRepository | None = None,
        scene_asset_storage: LocalSceneAssetStorage | None = None,
        actor_asset_storage: LocalActorAssetStorage | None = None,
        journal_asset_storage: LocalJournalAssetStorage | None = None,
        system_storage: ScopedJsonStorage | None = None,
    ) -> None:
        self.campaigns = campaigns or CampaignRepository()
        self.scenes = scenes or SceneRepository()
        self.scene_asset_storage = scene_asset_storage or LocalSceneAssetStorage()
        self.actor_asset_storage = actor_asset_storage or LocalActorAssetStorage()
        self.journal_asset_storage = journal_asset_storage or LocalJournalAssetStorage()
        self.system_storage = system_storage or ScopedJsonStorage()

    def list_for_user(self, user_id: str) -> list[Row]:
        return self.campaigns.list_for_user(user_id)

    def list_members_for_user_campaigns(self, user_id: str) -> list[Row]:
        return self.campaigns.list_members_for_user_campaigns(user_id)

    def update_measure_flash_seconds(self, *, campaign_id: str, seconds: int) -> CampaignResult:
        updated = self.campaigns.update_measure_flash_seconds(
            campaign_id=campaign_id,
            seconds=seconds,
        )
        if not updated:
            return CampaignResult(
                success=False,
                error_key="inside.campaigns.errors.not_found",
            )
        return CampaignResult(success=True)

    def create_campaign(
        self,
        *,
        owner_user_id: str,
        title: str,
        description: str,
    ) -> CampaignResult:
        normalized_title = " ".join(title.strip().split())
        normalized_description = description.strip()

        if len(normalized_title) < 2:
            return CampaignResult(
                success=False,
                error_key="inside.campaigns.errors.invalid_title",
            )

        if len(normalized_title) > 120:
            return CampaignResult(
                success=False,
                error_key="inside.campaigns.errors.title_too_long",
            )

        if len(normalized_description) > 2000:
            return CampaignResult(
                success=False,
                error_key="inside.campaigns.errors.description_too_long",
            )

        campaign = self.campaigns.create(
            owner_user_id=owner_user_id,
            title=normalized_title,
            description=normalized_description,
        )

        return CampaignResult(
            success=True,
            campaign=campaign,
        )

    def update_campaign(
        self,
        *,
        campaign_id: str,
        user_id: str,
        title: str,
        description: str,
    ) -> CampaignResult:
        campaign = self.campaigns.get_for_user(
            campaign_id=campaign_id,
            user_id=user_id,
        )

        if campaign is None:
            return CampaignResult(
                success=False,
                error_key="inside.campaigns.errors.not_found",
            )

        if campaign["member_role"] != PlayerRole.GM.value:
            return CampaignResult(
                success=False,
                error_key="inside.campaigns.errors.gm_required",
            )

        normalized_title = " ".join(title.strip().split())
        normalized_description = description.strip()

        if len(normalized_title) < 2:
            return CampaignResult(
                success=False,
                error_key="inside.campaigns.errors.invalid_title",
            )

        if len(normalized_title) > 120:
            return CampaignResult(
                success=False,
                error_key="inside.campaigns.errors.title_too_long",
            )

        if len(normalized_description) > 2000:
            return CampaignResult(
                success=False,
                error_key="inside.campaigns.errors.description_too_long",
            )

        self.campaigns.update_details(
            campaign_id=campaign_id,
            title=normalized_title,
            description=normalized_description,
        )

        return CampaignResult(success=True)

    def generate_delete_code(
        self,
        *,
        campaign_id: str,
        user_id: str,
    ) -> CampaignResult:
        campaign = self.campaigns.get_for_user(
            campaign_id=campaign_id,
            user_id=user_id,
        )

        if campaign is None:
            return CampaignResult(
                success=False,
                error_key="inside.campaigns.errors.not_found",
            )

        if campaign["member_role"] != PlayerRole.GM.value:
            return CampaignResult(
                success=False,
                error_key="inside.campaigns.errors.gm_required",
            )

        code = generate_removal_code()

        self.campaigns.create_delete_code(
            campaign_id=campaign_id,
            requested_by_user_id=user_id,
            code=code,
            ttl_seconds=DELETE_CODE_TTL_SECONDS,
        )

        return CampaignResult(
            success=True,
            removal_code=code,
        )

    def delete_campaign(
        self,
        *,
        campaign_id: str,
        user_id: str,
        removal_code: str,
    ) -> CampaignResult:
        campaign = self.campaigns.get_for_user(
            campaign_id=campaign_id,
            user_id=user_id,
        )

        if campaign is None:
            return CampaignResult(
                success=False,
                error_key="inside.campaigns.errors.not_found",
            )

        if campaign["member_role"] != PlayerRole.GM.value:
            return CampaignResult(
                success=False,
                error_key="inside.campaigns.errors.gm_required",
            )

        if not self.campaigns.has_valid_delete_code(
            campaign_id=campaign_id,
            requested_by_user_id=user_id,
            code=removal_code,
        ):
            return CampaignResult(
                success=False,
                error_key="inside.campaigns.errors.invalid_removal_code",
            )

        try:
            self._delete_campaign_storage(campaign_id=campaign_id)
        except (OSError, ValueError):
            return CampaignResult(
                success=False,
                error_key="inside.campaigns.errors.delete_failed",
            )

        self.campaigns.delete(campaign_id=campaign_id)

        return CampaignResult(success=True)

    def _delete_campaign_storage(self, *, campaign_id: str) -> None:
        scenes = self.scenes.list_by_campaign(campaign_id)
        for scene in scenes:
            self.scene_asset_storage.delete_scene(scene_id=scene["id"])
        self.actor_asset_storage.delete_campaign(campaign_id=campaign_id)
        self.journal_asset_storage.delete_campaign(campaign_id=campaign_id)
        self.system_storage.delete_campaign(campaign_id=campaign_id)

    def ban_member(
        self,
        *,
        campaign_id: str,
        requester_user_id: str,
        target_user_id: str,
    ) -> CampaignResult:
        campaign = self.campaigns.get_for_user(
            campaign_id=campaign_id,
            user_id=requester_user_id,
        )

        if campaign is None:
            return CampaignResult(
                success=False,
                error_key="inside.campaigns.errors.not_found",
            )

        if campaign["member_role"] != PlayerRole.GM.value:
            return CampaignResult(
                success=False,
                error_key="inside.campaigns.errors.gm_required",
            )

        if requester_user_id == target_user_id:
            return CampaignResult(
                success=False,
                error_key="game.players.errors.cannot_ban_self",
            )

        member = self.campaigns.get_member(
            campaign_id=campaign_id,
            user_id=target_user_id,
        )

        if member is None:
            return CampaignResult(
                success=False,
                error_key="game.players.errors.not_found",
            )

        if member["role"] == PlayerRole.GM.value:
            return CampaignResult(
                success=False,
                error_key="game.players.errors.cannot_ban_gm",
            )

        room_user_ids = self.campaigns.list_member_user_ids(campaign_id=campaign_id)
        self.campaigns.remove_member(campaign_id=campaign_id, user_id=target_user_id)

        return CampaignResult(
            success=True,
            member=member,
            room_user_ids=room_user_ids,
        )
