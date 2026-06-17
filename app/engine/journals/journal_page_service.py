from __future__ import annotations

from dataclasses import dataclass

from app.engine.journals.journal_service import JournalService
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.journal_folder_repository import JournalFolderRepository
from app.persistence.repositories.journal_repository import JournalRepository


@dataclass(frozen=True)
class JournalModalPage:
    journal: dict
    view: dict
    campaign: dict
    is_gm: bool
    can_edit: bool
    journal_folders: list[dict]
    room_members: list[dict]
    board_quest_options: list[dict]


@dataclass(frozen=True)
class JournalCreatePage:
    campaign: dict
    is_gm: bool
    journal_folders: list[dict]
    room_members: list[dict]


class JournalPageService:
    def __init__(
        self,
        *,
        journals: JournalRepository | None = None,
        campaigns: CampaignRepository | None = None,
        folders: JournalFolderRepository | None = None,
        journal_service: JournalService | None = None,
    ) -> None:
        self.journals = journals or JournalRepository()
        self.campaigns = campaigns or CampaignRepository()
        self.folders = folders or JournalFolderRepository()
        self.journal_service = journal_service or JournalService()

    def build_modal(self, *, journal_id: str, user_id: str) -> JournalModalPage | None:
        journal = self.journals.get_by_id(journal_id)
        if journal is None or journal["status"] != "active":
            return None

        campaign = self.campaigns.get_for_user(
            campaign_id=journal["campaign_id"],
            user_id=user_id,
        )
        if campaign is None:
            return None

        campaign_dict = dict(campaign)
        journal_dict = dict(journal)
        if not self.journal_service.can_view_journal(
            journal=journal_dict,
            campaign=campaign_dict,
            user_id=user_id,
        ):
            return None

        owners = self.journals.list_owners_for_journal(journal_id=journal_id)
        journal_dict["owners"] = owners
        journal_dict["owner_ids"] = {owner["id"] for owner in owners}
        journal_dict["owner_name"] = (
            ", ".join(owner["name"] for owner in owners) if owners else None
        )
        journal_dict["type_label_key"] = f"game.journal.types.{journal_dict['type']}"

        is_gm = campaign_dict.get("member_role") == "gm"
        can_edit = self.journal_service.can_edit_journal(
            journal=journal_dict,
            campaign=campaign_dict,
            user_id=user_id,
        )
        view = self.journal_service.build_view(
            journal=journal_dict,
            campaign=campaign_dict,
            user_id=user_id,
        )

        board_quest_options: list[dict] = []
        if journal_dict["type"] == "quest_board" and is_gm:
            on_board = {entry["quest_id"] for entry in view.get("board_entries", [])}
            for candidate in self.journals.list_active_for_campaign(
                campaign_id=journal["campaign_id"]
            ):
                if candidate["type"] == "quest" and candidate["id"] not in on_board:
                    board_quest_options.append(
                        {"id": candidate["id"], "title": candidate["title"]}
                    )

        return JournalModalPage(
            journal=journal_dict,
            view=view,
            campaign=campaign_dict,
            is_gm=is_gm,
            can_edit=can_edit,
            journal_folders=[
                dict(folder)
                for folder in self.folders.list_for_campaign(campaign_id=journal["campaign_id"])
            ],
            room_members=[
                dict(member)
                for member in self.campaigns.list_members(campaign_id=journal["campaign_id"])
            ],
            board_quest_options=board_quest_options,
        )

    def build_create_modal(self, *, campaign_id: str, user_id: str) -> JournalCreatePage | None:
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return None

        campaign_dict = dict(campaign)
        return JournalCreatePage(
            campaign=campaign_dict,
            is_gm=campaign_dict.get("member_role") == "gm",
            journal_folders=[
                dict(folder)
                for folder in self.folders.list_for_campaign(campaign_id=campaign_id)
            ],
            room_members=[
                dict(member)
                for member in self.campaigns.list_members(campaign_id=campaign_id)
            ],
        )

    def list_owners(self, *, journal_id: str) -> list[dict]:
        return self.journals.list_owners_for_journal(journal_id=journal_id)
