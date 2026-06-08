"""Resolves (and confines) paths inside the system-scoped storage tree (§16.2).

    storage/system-data/{system_id}/campaigns/{campaign_id}/{actors|items}/{entity_id}.json

The system never picks a path: the core derives it from ids it controls. Every
id segment is validated, and the resolved path is confined to the storage root
so a crafted id can never escape it. The root is derived from the active
``DATABASE_PATH`` so tests (which point the DB at a tmp dir) stay isolated.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.persistence import database

_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")

                                                           
_KIND_DIRS = {"actor": "actors", "item": "items"}


def system_data_root() -> Path:
    return database.database_storage_root() / "system-data"


def _safe(segment: str) -> bool:
    return bool(segment) and segment not in {".", ".."} and bool(_SAFE_SEGMENT.match(segment))


def entity_data_path(
    *, kind: str, system_id: str, campaign_id: str, entity_id: str
) -> Path | None:
    sub = _KIND_DIRS.get(kind)
    if sub is None:
        return None
    if not (_safe(system_id) and _safe(campaign_id) and _safe(entity_id)):
        return None
    root = system_data_root()
    candidate = (
        root / system_id / "campaigns" / campaign_id / sub / f"{entity_id}.json"
    ).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def actor_data_path(*, system_id: str, campaign_id: str, actor_id: str) -> Path | None:
    return entity_data_path(
        kind="actor", system_id=system_id, campaign_id=campaign_id, entity_id=actor_id
    )
