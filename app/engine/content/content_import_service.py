"""``content.entry.import`` — copy a read-only content entry into a campaign (§2.6/§10).

``import_entry`` handles ``actor_pack`` entries: it creates an Actor Core of the
entry's type and seeds its Sheet Data with the entry's ``data`` (a campaign-owned
copy). ``import_item_entry`` does the same for ``item_pack``/``spell_pack`` entries
into an Item Core. (Plain item/spell entries can also be dropped onto actor sheets
via ``sheet.drop``.)
"""

from __future__ import annotations

from dataclasses import dataclass

from app.engine.actors.actor_service import ActorService
from app.engine.content.content_pack_service import ContentPackService
from app.engine.items.item_service import ItemService
from app.engine.sheets.sheet_data_service import SheetDataService

_ITEM_PACK_TYPES = {"item_pack", "spell_pack"}


@dataclass(frozen=True)
class ImportResult:
    success: bool
    actor_id: str | None = None
    item_id: str | None = None
    campaign_id: str | None = None
    system_id: str | None = None
    error_key: str | None = None


class ContentImportService:
    def __init__(self) -> None:
        self.content = ContentPackService()
        self.actors = ActorService()
        self.items = ItemService()
        self.sheet_data = SheetDataService()

    def import_entry(
        self,
        *,
        campaign_id: str,
        user_id: str,
        system_id: str,
        pack_id: str,
        entry_id: str,
    ) -> ImportResult:
        pack = self.content.get_pack(system_id, pack_id)
        if pack is None:
            return ImportResult(success=False, error_key="game.drop.errors.entry_not_found")
        if pack["type"] != "actor_pack":
            return ImportResult(success=False, error_key="game.content.errors.not_importable")

        entry = next((e for e in pack["entries"] if e.get("id") == entry_id), None)
        if entry is None:
            return ImportResult(success=False, error_key="game.drop.errors.entry_not_found")

        created = self.actors.create_actor(
            campaign_id=campaign_id,
            user_id=user_id,
            system_id=system_id,
            actor_type=str(entry.get("type", "")),
            name=str(entry.get("name", "")) or "Imported",
        )
        if not created.success:
            return ImportResult(success=False, error_key=created.error_key)

        data = entry.get("data")
        if isinstance(data, dict) and data:
            self.sheet_data.set_data(actor_id=created.actor_id, user_id=user_id, data=data)

        return ImportResult(
            success=True,
            actor_id=created.actor_id,
            campaign_id=campaign_id,
            system_id=system_id,
        )

    def import_item_entry(
        self,
        *,
        campaign_id: str,
        user_id: str,
        system_id: str,
        pack_id: str,
        entry_id: str,
    ) -> ImportResult:
        pack = self.content.get_pack(system_id, pack_id)
        if pack is None:
            return ImportResult(success=False, error_key="game.drop.errors.entry_not_found")
        if pack["type"] not in _ITEM_PACK_TYPES:
            return ImportResult(success=False, error_key="game.content.errors.not_importable")

        entry = next((e for e in pack["entries"] if e.get("id") == entry_id), None)
        if entry is None:
            return ImportResult(success=False, error_key="game.drop.errors.entry_not_found")

        seed = entry.get("data") if isinstance(entry.get("data"), dict) else {}
        created = self.items.create_item(
            campaign_id=campaign_id,
            user_id=user_id,
            system_id=system_id,
            item_type=str(entry.get("type", "")),
            name=str(entry.get("name", "")) or "Imported",
            data=seed,
        )
        if not created.success:
            return ImportResult(success=False, error_key=created.error_key)

        return ImportResult(
            success=True,
            item_id=created.item_id,
            campaign_id=campaign_id,
            system_id=system_id,
        )
