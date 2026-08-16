"""Ruleset-declared insertion of global Items as actor-local snapshots."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.engine.rules.rules_registry import SystemRulesService
from app.engine.sheets.item_sheet_data_service import ItemSheetDataService
from app.engine.sheets.sheet_data_service import SheetDataService
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.item_repository import ItemRepository


@dataclass(frozen=True)
class ItemCopyResult:
    success: bool
    value: dict | None = None
    error_key: str | None = None


def _path_get(root: dict, dotted: str) -> Any:
    cursor: Any = root
    for segment in dotted.split("."):
        cursor = cursor.get(segment) if isinstance(cursor, dict) else None
    return cursor


class ActorItemCopyService:
    def __init__(self) -> None:
        self.actors = ActorRepository(); self.items = ItemRepository(); self.rules = SystemRulesService()

    def _slots(self, system_id: str) -> dict:
        raw = self.rules.get_item_insertion(system_id).get("slots")
        if not isinstance(raw, list):
            return {}
        out: dict[str, dict] = {}
        for slot in raw[:32]:
            if not isinstance(slot, dict): continue
            slot_id, storage = slot.get("id"), slot.get("storage")
            accepts, mapping = slot.get("accepts"), slot.get("mapping")
            if isinstance(slot_id, str) and isinstance(storage, str) and isinstance(accepts, list) and isinstance(mapping, dict):
                out[slot_id] = {"id": slot_id, "storage": storage, "accepts": [str(v) for v in accepts[:32]], "duplicatePolicy": slot.get("duplicatePolicy", "allow"), "mapping": mapping, "defaults": slot.get("defaults", {}) if isinstance(slot.get("defaults"), dict) else {}}
        return out

    def slots(self, *, actor_id: str, user_id: str) -> ItemCopyResult:
        data = SheetDataService().get_data(actor_id=actor_id, user_id=user_id)
        if not data.success: return ItemCopyResult(False, error_key=data.error_key)
        slots = self._slots(str(data.system_id))
        return ItemCopyResult(True, {"slots": [{"id": s["id"], "accepts": s["accepts"], "duplicatePolicy": s["duplicatePolicy"]} for s in slots.values()]})

    def list(self, *, actor_id: str, user_id: str, slot_id: str) -> ItemCopyResult:
        data = SheetDataService().get_data(actor_id=actor_id, user_id=user_id)
        if not data.success: return ItemCopyResult(False, error_key=data.error_key)
        slot = self._slots(str(data.system_id)).get(slot_id)
        if slot is None: return ItemCopyResult(False, error_key="sdk.actors.items.slot_invalid")
        copies = _path_get(data.data or {}, slot["storage"])
        return ItemCopyResult(True, {"copies": deepcopy(copies) if isinstance(copies, list) else []})

    def insert(self, *, campaign_id: str, actor_id: str, source_item_id: str, slot_id: str, user_id: str) -> ItemCopyResult:
        actor = self.actors.get(actor_id); source = self.items.get(source_item_id)
        if not actor or not source or actor.get("campaign_id") != campaign_id or source.get("campaign_id") != campaign_id or actor.get("system_id") != source.get("system_id"):
            return ItemCopyResult(False, error_key="sdk.runtime.not_found")
        actor_data = SheetDataService().get_data(actor_id=actor_id, user_id=user_id)
        source_data = ItemSheetDataService().get_data(item_id=source_item_id, user_id=user_id)
        if not actor_data.success or not source_data.success:
            return ItemCopyResult(False, error_key="sdk.runtime.not_found")
        slots = self._slots(str(actor["system_id"])); slot = slots.get(slot_id)
        if slot is None: return ItemCopyResult(False, error_key="sdk.actors.items.slot_invalid")
        if str(source.get("type")) not in slot["accepts"]: return ItemCopyResult(False, error_key="sdk.actors.items.type_rejected")
        existing = _path_get(actor_data.data or {}, slot["storage"]); existing = deepcopy(existing) if isinstance(existing, list) else []
        if slot["duplicatePolicy"] == "rejectSource" and any(row.get("sourceItemId") == source_item_id for row in existing if isinstance(row, dict)):
            return ItemCopyResult(False, error_key="sdk.actors.items.duplicate")
        source_view = {"core": {"name": source.get("name"), "type": source.get("type")}, "data": source_data.data or {}}
        local = {"id": uuid4().hex, "sourceItemId": source_item_id, **deepcopy(slot["defaults"])}
        for target, source_path in slot["mapping"].items():
            if isinstance(target, str) and isinstance(source_path, str): local[target] = deepcopy(_path_get(source_view, source_path))
        existing.append(local)
        result = SheetDataService().patch_data(actor_id=actor_id, user_id=user_id, patch={slot["storage"]: existing})
        if not result.success: return ItemCopyResult(False, error_key=result.error_key)
        return ItemCopyResult(True, {"copy": local, "actorId": actor_id, "slot": slot_id, "version": result.version})

    def remove(self, *, actor_id: str, local_id: str, slot_id: str, user_id: str) -> ItemCopyResult:
        data = SheetDataService().get_data(actor_id=actor_id, user_id=user_id)
        if not data.success: return ItemCopyResult(False, error_key=data.error_key)
        slot = self._slots(str(data.system_id)).get(slot_id)
        if slot is None: return ItemCopyResult(False, error_key="sdk.actors.items.slot_invalid")
        rows = _path_get(data.data or {}, slot["storage"]); rows = rows if isinstance(rows, list) else []
        filtered = [row for row in rows if not isinstance(row, dict) or row.get("id") != local_id]
        if len(filtered) == len(rows): return ItemCopyResult(False, error_key="sdk.runtime.not_found")
        result = SheetDataService().patch_data(actor_id=actor_id, user_id=user_id, patch={slot["storage"]: filtered})
        if not result.success: return ItemCopyResult(False, error_key=result.error_key)
        return ItemCopyResult(True, {"removed": True, "actorId": actor_id, "slot": slot_id, "version": result.version})
