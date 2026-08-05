"""Resolve a drag *source* into the canonical ``DropEntry`` (Canonical Drop Entry API).

Every drag onto an actor sheet — a read-only Content Pack Entry or a campaign
Item Document — is normalised by the backend to the *same* shape so the sheet's
``onDrop`` action only ever consumes ``@drop.entry.*`` and never has to know the
concrete origin. The client sends only ``source``; the backend resolves it here.

Item Documents are *projected* (not linked): the resulting instance on the actor
is an editable snapshot. ``source`` is kept for traceability, not as a strong link.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.engine.items.item_permissions import can_view_item
from app.engine.content.content_pack_service import ContentPackService
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.persistence.repositories.item_repository import ItemRepository


@dataclass(frozen=True)
class DropEntry:
    id: str
    drop_type: str
    type: str
    name: str
    img: str
    source: dict
    data: dict

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "dropType": self.drop_type,
            "type": self.type,
            "name": self.name,
            "img": self.img,
            "source": self.source,
            "data": self.data,
        }


class DropEntryResolver:
    def __init__(self) -> None:
        self.content = ContentPackService()
        self.items = ItemRepository()
        self.storage = ScopedJsonStorage()

    def resolve(
        self,
        *,
        system_id: str,
        campaign_id: str,
        campaign: dict,
        user_id: str,
        source: dict,
    ) -> tuple[DropEntry | None, str | None]:
        kind = str(source.get("kind", ""))
        if kind == "content_pack_entry":
            return self._from_content_pack(system_id, source)
        if kind == "item":
            return self._from_item(system_id, campaign_id, campaign, user_id, source)
        return None, "game.drop.errors.unsupported_source"

                                                                              

    def _from_content_pack(
        self, system_id: str, source: dict
    ) -> tuple[DropEntry | None, str | None]:
        pack_id = str(source.get("pack_id", ""))
        entry_id = str(source.get("entry_id", ""))
        entry = self.content.get_entry(system_id, pack_id, entry_id)
        if entry is None:
            return None, "game.drop.errors.entry_not_found"
        data = entry.get("data") if isinstance(entry.get("data"), dict) else {}
        entry_type = str(entry.get("type") or data.get("type") or "")
        category = str(data.get("category") or entry.get("category") or "")
        drop_type = f"effect.{category}" if entry_type == "effect" and category else f"item.{entry_type}"
        if entry_type == "effect" and not category:
            drop_type = "effect"
        return (
            DropEntry(
                id=str(entry.get("id", entry_id)),
                drop_type=drop_type,
                type=entry_type,
                name=str(entry.get("name") or entry.get("label") or ""),
                img=str(entry.get("img", "")),
                source={
                    "kind": "content_pack_entry",
                    "systemId": system_id,
                    "packId": pack_id,
                    "entryId": entry_id,
                },
                data=data,
            ),
            None,
        )

                                                                              

    def _from_item(
        self, system_id: str, campaign_id: str, campaign: dict, user_id: str, source: dict
    ) -> tuple[DropEntry | None, str | None]:
        item_id = str(source.get("item_id", ""))
        item = self.items.get(item_id)
        if item is None or item["status"] != "active" or item["campaign_id"] != campaign_id:
            return None, "game.drop.errors.item_not_found"
                                                                              
        if item["system_id"] != system_id:
            return None, "game.drop.errors.system_mismatch"
        if not can_view_item(item=item, campaign=campaign, user_id=user_id):
            return None, "game.drop.errors.item_not_found"

        envelope = self.storage.read_item(
            system_id=item["system_id"], campaign_id=campaign_id, item_id=item_id
        )
        data = (
            envelope.get("data")
            if isinstance(envelope, dict) and isinstance(envelope.get("data"), dict)
            else {}
        )
        item_type = str(item.get("type", ""))
        return (
            DropEntry(
                id=item_id,
                drop_type=f"item.{item_type}",
                type=item_type,
                name=str(item.get("name", "")),
                img=str(item.get("portrait_asset_id") or ""),
                source={"kind": "item", "itemId": item_id},
                data=data,
            ),
            None,
        )
