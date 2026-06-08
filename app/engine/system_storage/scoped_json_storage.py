"""scoped-json-v1 store for Sheet Data (§2.3/§16.2).

Each actor/item's full system data is one JSON file:

    { "<kind>_id", "system_id", "version", "data": {...}, "updated_at": <iso> }

Reads/writes go through the path resolver (confinement) and atomic writer
(durability). The store knows nothing about rules or permissions — callers
(SheetDataService) enforce those. ``*_actor`` methods are thin wrappers over the
generic ``*_entity`` methods, kept so existing actor callers stay unchanged.
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone

from app.engine.system_storage.atomic_write import atomic_write_text
from app.engine.system_storage.storage_path_resolver import entity_data_path
from app.engine.system_storage.storage_path_resolver import system_data_root


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")


def _safe_segment(segment: str) -> bool:
    return bool(segment) and segment not in {".", ".."} and bool(_SAFE_SEGMENT.match(segment))


class ScopedJsonStorage:
                                                                              

    def read_entity(
        self, *, kind: str, system_id: str, campaign_id: str, entity_id: str
    ) -> dict | None:
        path = entity_data_path(
            kind=kind, system_id=system_id, campaign_id=campaign_id, entity_id=entity_id
        )
        if path is None or not path.is_file():
            return None
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return envelope if isinstance(envelope, dict) else None

    def write_entity(
        self,
        *,
        kind: str,
        system_id: str,
        campaign_id: str,
        entity_id: str,
        version: int,
        data: dict,
    ) -> dict:
        path = entity_data_path(
            kind=kind, system_id=system_id, campaign_id=campaign_id, entity_id=entity_id
        )
        if path is None:
            raise ValueError(f"unsafe storage path for {kind} data")
        envelope = {
            f"{kind}_id": entity_id,
            "system_id": system_id,
            "version": version,
            "data": data,
            "updated_at": _now_iso(),
        }
        atomic_write_text(path, json.dumps(envelope, ensure_ascii=False, separators=(",", ":")))
        return envelope

    def delete_entity(
        self, *, kind: str, system_id: str, campaign_id: str, entity_id: str
    ) -> None:
        path = entity_data_path(
            kind=kind, system_id=system_id, campaign_id=campaign_id, entity_id=entity_id
        )
        if path is not None and path.is_file():
            try:
                path.unlink()
            except OSError:
                pass

    def delete_campaign(self, *, campaign_id: str) -> None:
        if not _safe_segment(campaign_id):
            raise ValueError("campaign_id is invalid")

        root = system_data_root().resolve()
        if not root.exists():
            return

        for system_dir in root.iterdir():
            if not system_dir.is_dir():
                continue
            path = (system_dir / "campaigns" / campaign_id).resolve()
            try:
                path.relative_to(root)
            except ValueError:
                continue
            if path.exists():
                shutil.rmtree(path)

                                                                              

    def read_actor(self, *, system_id: str, campaign_id: str, actor_id: str) -> dict | None:
        return self.read_entity(
            kind="actor", system_id=system_id, campaign_id=campaign_id, entity_id=actor_id
        )

    def write_actor(
        self, *, system_id: str, campaign_id: str, actor_id: str, version: int, data: dict
    ) -> dict:
        return self.write_entity(
            kind="actor",
            system_id=system_id,
            campaign_id=campaign_id,
            entity_id=actor_id,
            version=version,
            data=data,
        )

    def delete_actor(self, *, system_id: str, campaign_id: str, actor_id: str) -> None:
        self.delete_entity(
            kind="actor", system_id=system_id, campaign_id=campaign_id, entity_id=actor_id
        )

                                                                              

    def read_item(self, *, system_id: str, campaign_id: str, item_id: str) -> dict | None:
        return self.read_entity(
            kind="item", system_id=system_id, campaign_id=campaign_id, entity_id=item_id
        )

    def write_item(
        self, *, system_id: str, campaign_id: str, item_id: str, version: int, data: dict
    ) -> dict:
        return self.write_entity(
            kind="item",
            system_id=system_id,
            campaign_id=campaign_id,
            entity_id=item_id,
            version=version,
            data=data,
        )

    def delete_item(self, *, system_id: str, campaign_id: str, item_id: str) -> None:
        self.delete_entity(
            kind="item", system_id=system_id, campaign_id=campaign_id, entity_id=item_id
        )
