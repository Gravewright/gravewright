"""Sheet Data plane for items (mirrors SheetDataService, scoped to items_core).

The only sanctioned way to read/patch an item's scoped-json-v1 data: enforces
item permissions, bumps the version, and reports changed paths for realtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.engine.items.item_permissions import can_edit_item, can_view_item
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.item_repository import ItemRepository


@dataclass(frozen=True)
class ItemSheetDataResult:
    success: bool
    item_id: str | None = None
    campaign_id: str | None = None
    system_id: str | None = None
    version: int | None = None
    data: dict | None = None
    changed_paths: list[str] = field(default_factory=list)
    error_key: str | None = None


def _set_path(data: dict, dotted_path: str, value: Any) -> None:
    segments = [segment for segment in dotted_path.split(".") if segment]
    if not segments:
        return
    cursor = data
    for segment in segments[:-1]:
        nxt = cursor.get(segment)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[segment] = nxt
        cursor = nxt
    cursor[segments[-1]] = value


class ItemSheetDataService:
    def __init__(self) -> None:
        self.items = ItemRepository()
        self.campaigns = CampaignRepository()
        self.storage = ScopedJsonStorage()

    def get_data(self, *, item_id: str, user_id: str) -> ItemSheetDataResult:
        item, error = self._load(item_id, user_id, require_edit=False)
        if error is not None:
            return error
        envelope = self._read(item)
        return ItemSheetDataResult(
            success=True,
            item_id=item_id,
            campaign_id=item["campaign_id"],
            system_id=item["system_id"],
            version=int(envelope.get("version", 1)),
            data=envelope.get("data", {}),
        )

    def patch_data(
        self, *, item_id: str, user_id: str, patch: dict[str, Any]
    ) -> ItemSheetDataResult:
        item, error = self._load(item_id, user_id, require_edit=True)
        if error is not None:
            return error
        if not isinstance(patch, dict) or not patch:
            return ItemSheetDataResult(success=False, error_key="game.sheet_data.errors.empty_patch")

        envelope = self._read(item)
        data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
        for path, value in patch.items():
            _set_path(data, str(path), value)

        version = int(envelope.get("version", 1)) + 1
        self.storage.write_item(
            system_id=item["system_id"],
            campaign_id=item["campaign_id"],
            item_id=item_id,
            version=version,
            data=data,
        )
        return ItemSheetDataResult(
            success=True,
            item_id=item_id,
            campaign_id=item["campaign_id"],
            system_id=item["system_id"],
            version=version,
            data=data,
            changed_paths=sorted(str(path) for path in patch),
        )

    def set_data(self, *, item_id: str, user_id: str, data: dict) -> ItemSheetDataResult:
        item, error = self._load(item_id, user_id, require_edit=True)
        if error is not None:
            return error
        if not isinstance(data, dict):
            return ItemSheetDataResult(success=False, error_key="game.sheet_data.errors.invalid_data")

        envelope = self._read(item)
        version = int(envelope.get("version", 1)) + 1
        self.storage.write_item(
            system_id=item["system_id"],
            campaign_id=item["campaign_id"],
            item_id=item_id,
            version=version,
            data=data,
        )
        return ItemSheetDataResult(
            success=True,
            item_id=item_id,
            campaign_id=item["campaign_id"],
            system_id=item["system_id"],
            version=version,
            data=data,
            changed_paths=["*"],
        )

                                                                              

    def _read(self, item: dict) -> dict:
        envelope = self.storage.read_item(
            system_id=item["system_id"],
            campaign_id=item["campaign_id"],
            item_id=item["id"],
        )
        if envelope is None:
            return {"version": 1, "data": {}}
        return envelope

    def _load(
        self, item_id: str, user_id: str, *, require_edit: bool
    ) -> tuple[dict | None, ItemSheetDataResult | None]:
        item = self.items.get(item_id)
        if item is None or item["status"] != "active":
            return None, ItemSheetDataResult(success=False, error_key="game.items.errors.not_found")
        campaign = self.campaigns.get_for_user(campaign_id=item["campaign_id"], user_id=user_id)
        if campaign is None:
            return None, ItemSheetDataResult(success=False, error_key="game.items.errors.not_found")
        campaign_dict = dict(campaign)
        allowed = (
            can_edit_item(item=item, campaign=campaign_dict, user_id=user_id)
            if require_edit
            else can_view_item(item=item, campaign=campaign_dict, user_id=user_id)
        )
        if not allowed:
            return None, ItemSheetDataResult(success=False, error_key="game.items.errors.forbidden")
        return item, None
