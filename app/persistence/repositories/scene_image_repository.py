from __future__ import annotations

import json
import time
import uuid
from typing import Any

from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update

from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import scene_image_placements


class SceneImageRepository:
    def list_for_campaign(self, *, campaign_id: str) -> list[dict]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(scene_image_placements)
                    .where(scene_image_placements.c.campaign_id == campaign_id)
                    .order_by(scene_image_placements.c.scene_id.asc(), scene_image_placements.c.z_index.asc())
                )
            )
        return [_decode(row) for row in rows]

    def list_for_scene(self, *, scene_id: str) -> list[dict]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(scene_image_placements)
                    .where(scene_image_placements.c.scene_id == scene_id)
                    .order_by(scene_image_placements.c.z_index.asc())
                )
            )
        return [_decode(row) for row in rows]

    def get(self, placement_id: str) -> dict | None:
        with engine_connect() as conn:
            row = self._get(conn, placement_id)
        return _decode(row) if row is not None else None

    def create(
        self,
        *,
        campaign_id: str,
        scene_id: str,
        asset_id: str,
        owner_user_id: str | None,
        x: float,
        y: float,
        natural_width: int,
        natural_height: int,
        rotation: float = 0.0,
        scale: float = 1.0,
        z_index: int | None = None,
        layer: str = "game",
        metadata: dict | None = None,
    ) -> dict:
        now = int(time.time())
        placement_id = uuid.uuid4().hex
        with engine_begin() as conn:
            if z_index is None:
                current_top = one_or_none(
                    conn.execute(
                        select(scene_image_placements.c.z_index)
                        .where(scene_image_placements.c.scene_id == scene_id)
                        .order_by(scene_image_placements.c.z_index.desc())
                        .limit(1)
                    )
                )
                z_index = int(current_top["z_index"]) + 1 if current_top is not None else 0
            conn.execute(
                insert(scene_image_placements).values(
                    id=placement_id,
                    campaign_id=campaign_id,
                    scene_id=scene_id,
                    asset_id=asset_id,
                    owner_user_id=owner_user_id,
                    x=float(x),
                    y=float(y),
                    rotation=float(rotation),
                    scale=max(0.05, min(20.0, float(scale))),
                    z_index=int(z_index),
                    natural_width=max(0, int(natural_width)),
                    natural_height=max(0, int(natural_height)),
                    locked=0,
                    gm_only=1 if layer == "gm" else 0,
                    layer=_normalize_layer(layer),
                    metadata_json=_dump(metadata or {}),
                    created_at=now,
                    updated_at=now,
                )
            )
            row = self._get(conn, placement_id)
        if row is None:
            raise RuntimeError("Created scene image placement could not be read back.")
        return _decode(row)

    def update(
        self,
        *,
        placement_id: str,
        x: float | None = None,
        y: float | None = None,
        rotation: float | None = None,
        scale: float | None = None,
        z_index: int | None = None,
        locked: bool | None = None,
        layer: str | None = None,
    ) -> dict | None:
        now = int(time.time())
        values: dict[str, Any] = {"updated_at": now}
        if x is not None:
            values["x"] = float(x)
        if y is not None:
            values["y"] = float(y)
        if rotation is not None:
            values["rotation"] = float(rotation)
        if scale is not None:
            values["scale"] = max(0.05, min(20.0, float(scale)))
        if z_index is not None:
            values["z_index"] = int(z_index)
        if locked is not None:
            values["locked"] = 1 if locked else 0
        if layer is not None:
            normalized = _normalize_layer(layer)
            values["layer"] = normalized
            values["gm_only"] = 1 if normalized == "gm" else 0
        with engine_begin() as conn:
            if self._get(conn, placement_id) is None:
                return None
            conn.execute(
                update(scene_image_placements)
                .where(scene_image_placements.c.id == placement_id)
                .values(**values)
            )
            row = self._get(conn, placement_id)
        return _decode(row) if row is not None else None

    def delete(self, placement_id: str) -> bool:
        with engine_begin() as conn:
            result = conn.execute(
                delete(scene_image_placements).where(scene_image_placements.c.id == placement_id)
            )
        return bool(result.rowcount)

    def _get(self, conn, placement_id: str) -> dict | None:
        return one_or_none(
            conn.execute(
                select(scene_image_placements)
                .where(scene_image_placements.c.id == placement_id)
                .limit(1)
            )
        )


VALID_LAYERS = {"game", "gm", "composition"}


def _normalize_layer(value: str | None) -> str:
    return value if value in VALID_LAYERS else "game"


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _decode(row: dict) -> dict:
    row["locked"] = bool(row.get("locked"))
    row["gm_only"] = bool(row.get("gm_only"))
    row["layer"] = _normalize_layer(row.get("layer"))
    raw = row.get("metadata_json")
    if raw in (None, ""):
        row["metadata"] = {}
    elif isinstance(raw, dict):
        row["metadata"] = raw
    else:
        try:
            row["metadata"] = json.loads(raw)
        except (TypeError, ValueError):
            row["metadata"] = {}
    return row
