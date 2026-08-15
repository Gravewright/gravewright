from __future__ import annotations

import time

from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import select

from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import scene_assets as scene_assets_table
from app.persistence.tables import scene_tiles as scene_tiles_table


class SceneTileRepository:
    def create(
        self,
        *,
        scene_id: str,
        layer_id: str,
        tile_ref: int,
        asset_id: str,
        tx: int,
        ty: int,
        width: int,
        height: int,
        hash: str,
        byte_size: int,
        lod: int = 0,
    ) -> dict:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                insert(scene_tiles_table).values(
                    scene_id=scene_id,
                    layer_id=layer_id,
                    tile_ref=tile_ref,
                    lod=lod,
                    asset_id=asset_id,
                    tx=tx,
                    ty=ty,
                    width=width,
                    height=height,
                    hash=hash,
                    byte_size=byte_size,
                    created_at=now,
                )
            )
            row = one_or_none(
                conn.execute(
                    select(scene_tiles_table)
                    .where(scene_tiles_table.c.scene_id == scene_id)
                    .where(scene_tiles_table.c.layer_id == layer_id)
                    .where(scene_tiles_table.c.tile_ref == tile_ref)
                    .limit(1)
                )
            )
        if row is None:
            raise RuntimeError("Created scene tile could not be read back.")
        return row

    def get_by_ref(self, *, scene_id: str, layer_id: str, tile_ref: int) -> dict | None:
        with engine_connect() as conn:
            return one_or_none(
                conn.execute(
                    select(scene_tiles_table)
                    .where(scene_tiles_table.c.scene_id == scene_id)
                    .where(scene_tiles_table.c.layer_id == layer_id)
                    .where(scene_tiles_table.c.tile_ref == tile_ref)
                    .limit(1)
                )
            )

    def get_by_coord(
        self, *, scene_id: str, layer_id: str, lod: int, tx: int, ty: int
    ) -> dict | None:
        with engine_connect() as conn:
            return one_or_none(
                conn.execute(
                    select(
                        scene_tiles_table,
                        scene_assets_table.c.storage_path.label("storage_path"),
                        scene_assets_table.c.content_type.label("content_type"),
                    )
                    .join(scene_assets_table, scene_assets_table.c.id == scene_tiles_table.c.asset_id)
                    .where(scene_tiles_table.c.scene_id == scene_id)
                    .where(scene_tiles_table.c.layer_id == layer_id)
                    .where(scene_tiles_table.c.lod == lod)
                    .where(scene_tiles_table.c.tx == tx)
                    .where(scene_tiles_table.c.ty == ty)
                    .limit(1)
                )
            )

    def delete_by_layer(self, layer_id: str) -> None:
        with engine_begin() as conn:
            conn.execute(delete(scene_tiles_table).where(scene_tiles_table.c.layer_id == layer_id))

    def list_by_layer(self, layer_id: str, *, lod: int | None = None) -> list[dict]:
        stmt = (
            select(
                scene_tiles_table,
                scene_assets_table.c.storage_path.label("storage_path"),
            )
            .join(scene_assets_table, scene_assets_table.c.id == scene_tiles_table.c.asset_id)
            .where(scene_tiles_table.c.layer_id == layer_id)
        )
        if lod is not None:
            stmt = stmt.where(scene_tiles_table.c.lod == lod)
        with engine_connect() as conn:
            return all_dicts(conn.execute(stmt.order_by(scene_tiles_table.c.tile_ref.asc())))

    def list_by_region(
        self,
        *,
        scene_id: str,
        layer_id: str,
        lod: int,
        tx0: int,
        ty0: int,
        tx1: int,
        ty1: int,
        limit: int = 1024,
        after_ref: int = 0,
    ) -> list[dict]:
        """Sparse, bounded descriptor lookup for one viewport/index page."""
        safe_limit = max(1, min(int(limit), 4096))
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(scene_tiles_table)
                    .where(scene_tiles_table.c.scene_id == scene_id)
                    .where(scene_tiles_table.c.layer_id == layer_id)
                    .where(scene_tiles_table.c.lod == lod)
                    .where(scene_tiles_table.c.tx.between(min(tx0, tx1), max(tx0, tx1)))
                    .where(scene_tiles_table.c.ty.between(min(ty0, ty1), max(ty0, ty1)))
                    .where(scene_tiles_table.c.tile_ref > max(0, after_ref))
                    .order_by(scene_tiles_table.c.tile_ref.asc())
                    .limit(safe_limit)
                )
            )
