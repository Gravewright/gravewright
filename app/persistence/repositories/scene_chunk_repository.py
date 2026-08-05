from __future__ import annotations

import time
import uuid

from sqlalchemy import and_
from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import update

from app.domain.scenes import SceneChunkEncoding
from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import scene_chunks as scene_chunks_table


class SceneChunkRepository:
    def create_metadata(
        self,
        *,
        scene_id: str,
        layer_id: str,
        cx: int,
        cy: int,
        hash: str,
        byte_size: int,
        encoding: SceneChunkEncoding,
        version: int = 1,
    ) -> dict:
        now = int(time.time())
        chunk_id = uuid.uuid4().hex
        with engine_begin() as conn:
            conn.execute(
                insert(scene_chunks_table).values(
                    id=chunk_id,
                    scene_id=scene_id,
                    layer_id=layer_id,
                    cx=cx,
                    cy=cy,
                    version=version,
                    hash=hash,
                    byte_size=byte_size,
                    encoding=encoding.value,
                    created_at=now,
                    updated_at=now,
                )
            )
            row = self._get_metadata(conn, layer_id=layer_id, cx=cx, cy=cy)
        if row is None:
            raise RuntimeError("Created scene chunk could not be read back.")
        return row

    def get_metadata(self, *, layer_id: str, cx: int, cy: int) -> dict | None:
        with engine_connect() as conn:
            return self._get_metadata(conn, layer_id=layer_id, cx=cx, cy=cy)

    def list_by_scene_layer(self, *, scene_id: str, layer_id: str) -> list[dict]:
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(scene_chunks_table)
                    .where(scene_chunks_table.c.scene_id == scene_id)
                    .where(scene_chunks_table.c.layer_id == layer_id)
                    .order_by(scene_chunks_table.c.cy.asc(), scene_chunks_table.c.cx.asc())
                )
            )

    def list_by_viewport_chunk_range(
        self,
        *,
        scene_id: str,
        layer_id: str,
        cx0: int,
        cy0: int,
        cx1: int,
        cy1: int,
    ) -> list[dict]:
        min_cx = min(cx0, cx1)
        max_cx = max(cx0, cx1)
        min_cy = min(cy0, cy1)
        max_cy = max(cy0, cy1)
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(scene_chunks_table)
                    .where(scene_chunks_table.c.scene_id == scene_id)
                    .where(scene_chunks_table.c.layer_id == layer_id)
                    .where(scene_chunks_table.c.cx.between(min_cx, max_cx))
                    .where(scene_chunks_table.c.cy.between(min_cy, max_cy))
                    .order_by(scene_chunks_table.c.cy.asc(), scene_chunks_table.c.cx.asc())
                )
            )

    def delete_by_layer(self, layer_id: str) -> None:
        with engine_begin() as conn:
            conn.execute(delete(scene_chunks_table).where(scene_chunks_table.c.layer_id == layer_id))

    def record_write(
        self,
        *,
        scene_id: str,
        layer_id: str,
        cx: int,
        cy: int,
        hash: str,
        byte_size: int,
        encoding: SceneChunkEncoding,
        expected_version: int | None = None,
    ) -> dict | None:
        """Upsert chunk metadata, bumping ``version``.

        Optimistic concurrency is opt-in via ``expected_version`` (mirrors the
        token CAS, STABILIZATION_V1 P0.2). When provided on an update, the bump
        only applies if the row still carries that version, otherwise ``None`` is
        returned (``version_conflict``). Current callers omit it on purpose:
        chunk writes are GM-authored (low concurrency), so last-write-wins is an
        accepted, documented trade-off (STABILIZATION_V1 P1.1).
        """
        now = int(time.time())
        with engine_begin() as conn:
            existing = self._get_metadata(conn, layer_id=layer_id, cx=cx, cy=cy)
            if existing is None:
                conn.execute(
                    insert(scene_chunks_table).values(
                        id=uuid.uuid4().hex,
                        scene_id=scene_id,
                        layer_id=layer_id,
                        cx=cx,
                        cy=cy,
                        version=1,
                        hash=hash,
                        byte_size=byte_size,
                        encoding=encoding.value,
                        created_at=now,
                        updated_at=now,
                    )
                )
            else:
                stmt = update(scene_chunks_table).where(
                    scene_chunks_table.c.id == existing["id"]
                )
                if expected_version is not None:
                    stmt = stmt.where(scene_chunks_table.c.version == expected_version)
                result = conn.execute(
                    stmt.values(
                        version=scene_chunks_table.c.version + 1,
                        hash=hash,
                        byte_size=byte_size,
                        encoding=encoding.value,
                        updated_at=now,
                    )
                )
                if result.rowcount != 1:
                    return None
            row = self._get_metadata(conn, layer_id=layer_id, cx=cx, cy=cy)
        if row is None:
            raise RuntimeError("Written scene chunk could not be read back.")
        return row

    def list_by_coordinates(
        self,
        *,
        scene_id: str,
        layer_id: str,
        coords: tuple[tuple[int, int], ...],
    ) -> list[dict]:
        if not coords:
            return []
        coord_filter = or_(
            *(and_(scene_chunks_table.c.cx == cx, scene_chunks_table.c.cy == cy) for cx, cy in coords)
        )
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(scene_chunks_table)
                    .where(scene_chunks_table.c.scene_id == scene_id)
                    .where(scene_chunks_table.c.layer_id == layer_id)
                    .where(coord_filter)
                    .order_by(scene_chunks_table.c.cy.asc(), scene_chunks_table.c.cx.asc())
                )
            )

    def _get_metadata(self, conn, *, layer_id: str, cx: int, cy: int) -> dict | None:
        return one_or_none(
            conn.execute(
                select(scene_chunks_table)
                .where(scene_chunks_table.c.layer_id == layer_id)
                .where(scene_chunks_table.c.cx == cx)
                .where(scene_chunks_table.c.cy == cy)
                .limit(1)
            )
        )
