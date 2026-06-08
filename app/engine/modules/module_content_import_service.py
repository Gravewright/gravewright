"""Import module content pack entries into campaign-owned resources."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.roles import PlayerRole
from app.engine.actors.actor_service import ActorService
from app.engine.items.item_service import ItemService
from app.engine.journals.journal_service import JournalService
from app.engine.modules.module_content_pack_service import ModuleContentPackService
from app.engine.sheets.sheet_data_service import SheetDataService
from app.persistence.repositories.campaign_repository import CampaignRepository

_ITEM_PACK_TYPES = {"item_pack", "spell_pack"}
_JOURNAL_TYPES = {"diary", "quest", "quest_board"}


@dataclass(frozen=True)
class ModuleContentImportResult:
    success: bool
    campaign_id: str | None = None
    module_id: str | None = None
    pack_type: str | None = None
    actor_id: str | None = None
    item_id: str | None = None
    journal_id: str | None = None
    system_id: str | None = None
    error_key: str | None = None


class ModuleContentImportService:
    def __init__(self) -> None:
        self.campaigns = CampaignRepository()
        self.packs = ModuleContentPackService()
        self.actors = ActorService()
        self.items = ItemService()
        self.journals = JournalService()
        self.sheet_data = SheetDataService()

    def import_entry(
        self,
        *,
        campaign_id: str,
        user_id: str,
        module_id: str,
        pack_id: str,
        entry_id: str,
    ) -> ModuleContentImportResult:
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return ModuleContentImportResult(success=False, error_key="inside.campaigns.errors.not_found")
        if campaign.get("member_role") != PlayerRole.GM.value:
            return ModuleContentImportResult(success=False, error_key="inside.campaigns.errors.gm_required")

        pack = self.packs.get_pack(campaign_id=campaign_id, module_id=module_id, pack_id=pack_id, user_id=user_id)
        if pack is None:
            return ModuleContentImportResult(success=False, error_key="game.drop.errors.entry_not_found")
        entry = next((candidate for candidate in pack["entries"] if candidate.get("id") == entry_id), None)
        if entry is None:
            return ModuleContentImportResult(success=False, error_key="game.drop.errors.entry_not_found")

        pack_type = str(pack.get("type") or "")
        if pack_type == "actor_pack":
            return self._import_actor(campaign=dict(campaign), user_id=user_id, module_id=module_id, pack_type=pack_type, entry=entry)
        if pack_type in _ITEM_PACK_TYPES:
            return self._import_item(campaign=dict(campaign), user_id=user_id, module_id=module_id, pack_type=pack_type, entry=entry)
        if pack_type == "journal_pack":
            return self._import_journal(campaign=dict(campaign), user_id=user_id, module_id=module_id, pack_type=pack_type, entry=entry)
        return ModuleContentImportResult(success=False, error_key="game.content.errors.not_importable")

    def _entry_system_id(self, *, campaign: dict, entry: dict) -> str:
        system_id = entry.get("systemId") or entry.get("system_id") or campaign.get("active_system_id") or ""
        return str(system_id)

    def _import_actor(self, *, campaign: dict, user_id: str, module_id: str, pack_type: str, entry: dict) -> ModuleContentImportResult:
        system_id = self._entry_system_id(campaign=campaign, entry=entry)
        if not system_id:
            return ModuleContentImportResult(success=False, error_key="game.items.errors.system_not_assigned")
        created = self.actors.create_actor(
            campaign_id=str(campaign["id"]),
            user_id=user_id,
            system_id=system_id,
            actor_type=str(entry.get("type") or ""),
            name=str(entry.get("name") or entry.get("title") or "Imported"),
        )
        if not created.success or not created.actor_id:
            return ModuleContentImportResult(success=False, error_key=created.error_key)
        data = entry.get("data")
        if isinstance(data, dict) and data:
            self.sheet_data.set_data(actor_id=created.actor_id, user_id=user_id, data=data)
        return ModuleContentImportResult(
            success=True,
            campaign_id=str(campaign["id"]),
            module_id=module_id,
            pack_type=pack_type,
            actor_id=created.actor_id,
            system_id=system_id,
        )

    def _import_item(self, *, campaign: dict, user_id: str, module_id: str, pack_type: str, entry: dict) -> ModuleContentImportResult:
        system_id = self._entry_system_id(campaign=campaign, entry=entry)
        if not system_id:
            return ModuleContentImportResult(success=False, error_key="game.items.errors.system_not_assigned")
        seed = entry.get("data") if isinstance(entry.get("data"), dict) else {}
        created = self.items.create_item(
            campaign_id=str(campaign["id"]),
            user_id=user_id,
            system_id=system_id,
            item_type=str(entry.get("type") or ""),
            name=str(entry.get("name") or entry.get("title") or "Imported"),
            data=seed,
        )
        if not created.success or not created.item_id:
            return ModuleContentImportResult(success=False, error_key=created.error_key)
        return ModuleContentImportResult(
            success=True,
            campaign_id=str(campaign["id"]),
            module_id=module_id,
            pack_type=pack_type,
            item_id=created.item_id,
            system_id=system_id,
        )

    def _import_journal(self, *, campaign: dict, user_id: str, module_id: str, pack_type: str, entry: dict) -> ModuleContentImportResult:
        journal_type = str(entry.get("type") or "handout")
        if journal_type not in _JOURNAL_TYPES:
            journal_type = "handout"
        content = entry.get("content_markdown", entry.get("content", ""))
        data = entry.get("data") if isinstance(entry.get("data"), dict) else {}
        created = self.journals.create_journal(
            campaign_id=str(campaign["id"]),
            user_id=user_id,
            journal_type=journal_type,
            title=str(entry.get("title") or entry.get("name") or "Imported"),
            visibility=str(entry.get("visibility") or "private"),
            content_markdown=str(content or ""),
            data=data,
        )
        if not created.success or not created.journal_id:
            return ModuleContentImportResult(success=False, error_key=created.error_key)
        return ModuleContentImportResult(
            success=True,
            campaign_id=str(campaign["id"]),
            module_id=module_id,
            pack_type=pack_type,
            journal_id=created.journal_id,
        )
