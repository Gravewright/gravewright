from __future__ import annotations

import time
import uuid

from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update

from app.domain.scenes import SceneChunkEncoding
from app.domain.scenes import SceneLayerKind
from app.domain.scenes import SceneLayerVisibility
from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import scene_layers as scene_layers_table
from app.persistence.tables import scenes as scenes_table


class SceneLayerRepository:
    def create(
        self,
        *,
        scene_id: str,
        name: str,
        kind: SceneLayerKind,
        visibility: SceneLayerVisibility,
        display_order: int,
        encoding: SceneChunkEncoding,
        tile_table_version: int = 1,
    ) -> dict:
        now = int(time.time())
        layer_id = uuid.uuid4().hex
        with engine_begin() as conn:
            conn.execute(
                insert(scene_layers_table).values(
                    id=layer_id,
                    scene_id=scene_id,
                    name=name,
                    kind=kind.value,
                    visibility=visibility.value,
                    display_order=display_order,
                    encoding=encoding.value,
                    tile_table_version=tile_table_version,
                    created_at=now,
                    updated_at=now,
                )
            )
            row = self._get_by_id(conn, layer_id)
        if row is None:
            raise RuntimeError("Created scene layer could not be read back.")
        return row

    def get_by_id(self, layer_id: str) -> dict | None:
        with engine_connect() as conn:
            return self._get_by_id(conn, layer_id)

    def list_by_scene(self, scene_id: str) -> list[dict]:
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(scene_layers_table)
                    .where(scene_layers_table.c.scene_id == scene_id)
                    .order_by(scene_layers_table.c.display_order.asc(), scene_layers_table.c.created_at.asc())
                )
            )

    def update_metadata(
        self,
        *,
        layer_id: str,
        name: str,
        visibility: SceneLayerVisibility,
        display_order: int,
        tile_table_version: int,
        bump_scene_epoch: bool = True,
    ) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            existing = one_or_none(
                conn.execute(
                    select(
                        scene_layers_table.c.scene_id,
                        scene_layers_table.c.visibility,
                        scene_layers_table.c.display_order,
                        scene_layers_table.c.tile_table_version,
                    )
                    .where(scene_layers_table.c.id == layer_id)
                    .limit(1)
                )
            )
            conn.execute(
                update(scene_layers_table)
                .where(scene_layers_table.c.id == layer_id)
                .values(
                    name=name,
                    visibility=visibility.value,
                    display_order=display_order,
                    tile_table_version=tile_table_version,
                    updated_at=now,
                )
            )
            if existing is not None and bump_scene_epoch:
                should_bump_scene_epoch = (
                    existing["visibility"] != visibility.value
                    or existing["display_order"] != display_order
                    or existing["tile_table_version"] != tile_table_version
                )
                if should_bump_scene_epoch:
                    conn.execute(
                        update(scenes_table)
                        .where(scenes_table.c.id == existing["scene_id"])
                        .values(scene_epoch=scenes_table.c.scene_epoch + 1, updated_at=now)
                    )

    def delete(self, layer_id: str) -> None:
        with engine_begin() as conn:
            conn.execute(delete(scene_layers_table).where(scene_layers_table.c.id == layer_id))

    def _get_by_id(self, conn, layer_id: str) -> dict | None:
        return one_or_none(
            conn.execute(select(scene_layers_table).where(scene_layers_table.c.id == layer_id).limit(1))
        )
