from __future__ import annotations

import time
import uuid

from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import select

from app.domain.scenes import SceneAssetKind
from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import scene_assets as scene_assets_table
from app.persistence.tables import scene_tiles as scene_tiles_table


class SceneAssetRepository:
    def create(
        self,
        *,
        scene_id: str,
        kind: SceneAssetKind,
        storage_path: str,
        hash: str,
        byte_size: int,
        width: int | None = None,
        height: int | None = None,
        content_type: str | None = None,
    ) -> dict:
        now = int(time.time())
        asset_id = uuid.uuid4().hex
        with engine_begin() as conn:
            conn.execute(
                insert(scene_assets_table).values(
                    id=asset_id,
                    scene_id=scene_id,
                    kind=kind.value,
                    storage_path=storage_path,
                    hash=hash,
                    byte_size=byte_size,
                    width=width,
                    height=height,
                    content_type=content_type,
                    created_at=now,
                )
            )
            row = one_or_none(
                conn.execute(select(scene_assets_table).where(scene_assets_table.c.id == asset_id).limit(1))
            )
        if row is None:
            raise RuntimeError("Created scene asset could not be read back.")
        return row

    def get_by_id(self, asset_id: str) -> dict | None:
        with engine_connect() as conn:
            return one_or_none(
                conn.execute(select(scene_assets_table).where(scene_assets_table.c.id == asset_id).limit(1))
            )

    def get_original_for_scene(self, scene_id: str) -> dict | None:
        with engine_connect() as conn:
            return one_or_none(
                conn.execute(
                    select(scene_assets_table)
                    .where(scene_assets_table.c.scene_id == scene_id)
                    .where(scene_assets_table.c.kind == SceneAssetKind.ORIGINAL_IMAGE.value)
                    .limit(1)
                )
            )

    def delete_tile_assets_by_layer(self, layer_id: str) -> None:
        subquery = select(scene_tiles_table.c.asset_id).where(scene_tiles_table.c.layer_id == layer_id)
        with engine_begin() as conn:
            conn.execute(delete(scene_assets_table).where(scene_assets_table.c.id.in_(subquery)))

    def list_by_scene(self, scene_id: str) -> list[dict]:
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(scene_assets_table)
                    .where(scene_assets_table.c.scene_id == scene_id)
                    .order_by(scene_assets_table.c.created_at.asc())
                )
            )
