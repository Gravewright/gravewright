from __future__ import annotations

import json
import time
import uuid

from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.engine import Connection

from app.domain.tokens import TokenActorLinkMode
from app.domain.tokens import TokenControlledByRole
from app.domain.tokens import TokenDisposition
from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import tokens as tokens_table


class TokenRepository:
    """Persistence for map tokens, implemented with SQLAlchemy Core.

    This repository is in the realtime hot path. Keeping it on Core statements
    keeps queries portable across PostgreSQL/MySQL/SQLite while preserving the
    existing public API used by services and tests.
    """

    def create(
        self,
        *,
        scene_id: str,
        actor_id: str | None,
        grid_x: int,
        grid_y: int,
        width_cells: int = 1,
        height_cells: int = 1,
        name: str | None = None,
        token_asset_url: str | None = None,
        disposition: str = TokenDisposition.NEUTRAL,
        actor_link_mode: str = TokenActorLinkMode.UNLINKED,
        controlled_by_role: str = TokenControlledByRole.GM,
        controlled_by_user_ids: list[str] | None = None,
        rotation: float = 0.0,
        visible: bool = True,
        hidden: bool = False,
        locked: bool = False,
        vision_enabled: bool = True,
        vision_range: float = 0.0,
        elevation: float = 0.0,
        overrides: dict | None = None,
    ) -> dict:
        now = int(time.time())
        token_id = uuid.uuid4().hex
        values = self._create_values(
            token_id=token_id,
            scene_id=scene_id,
            actor_id=actor_id,
            grid_x=grid_x,
            grid_y=grid_y,
            width_cells=width_cells,
            height_cells=height_cells,
            name=name,
            token_asset_url=token_asset_url,
            disposition=disposition,
            actor_link_mode=actor_link_mode,
            controlled_by_role=controlled_by_role,
            controlled_by_user_ids=controlled_by_user_ids, rotation=rotation, visible=visible,
            hidden=hidden, locked=locked, vision_enabled=vision_enabled, vision_range=vision_range,
            elevation=elevation,
            overrides=overrides,
            now=now,
        )

        with engine_begin() as conn:
            conn.execute(insert(tokens_table).values(**values))
            row = self._get_by_id(conn, token_id)

        return self._hydrate(row)

    def create_many(self, tokens: list[dict]) -> list[dict]:
        """Create multiple tokens in a single transaction.

        Each dict accepts the same keyword arguments as :meth:`create`.
        Returned tokens preserve the input order.
        """
        if not tokens:
            return []

        now = int(time.time())
        ids: list[str] = []
        values: list[dict] = []
        for spec in tokens:
            token_id = uuid.uuid4().hex
            ids.append(token_id)
            values.append(
                self._create_values(
                    token_id=token_id,
                    scene_id=spec["scene_id"],
                    actor_id=spec.get("actor_id"),
                    grid_x=spec["grid_x"],
                    grid_y=spec["grid_y"],
                    width_cells=spec.get("width_cells", 1),
                    height_cells=spec.get("height_cells", 1),
                    name=spec.get("name"),
                    token_asset_url=spec.get("token_asset_url"),
                    disposition=spec.get("disposition", TokenDisposition.NEUTRAL),
                    actor_link_mode=spec.get("actor_link_mode", TokenActorLinkMode.UNLINKED),
                    controlled_by_role=spec.get(
                        "controlled_by_role",
                        TokenControlledByRole.GM,
                    ),
                    controlled_by_user_ids=spec.get("controlled_by_user_ids"),
                    rotation=spec.get("rotation", 0.0), visible=spec.get("visible", True),
                    hidden=spec.get("hidden", False), locked=spec.get("locked", False),
                    vision_enabled=spec.get("vision_enabled", True), vision_range=spec.get("vision_range", 0.0),
                    elevation=spec.get("elevation", 0.0),
                    overrides=spec.get("overrides"),
                    now=now,
                )
            )

        with engine_begin() as conn:
            conn.execute(insert(tokens_table), values)
            rows = all_dicts(conn.execute(select(tokens_table).where(tokens_table.c.id.in_(ids))))

        by_id = {row["id"]: self._hydrate(row) for row in rows}
        return [by_id[token_id] for token_id in ids]

    def get_by_id(self, token_id: str) -> dict | None:
        with engine_connect() as conn:
            row = self._get_by_id(conn, token_id)

        return self._hydrate(row) if row else None

    def get_by_scene_and_id(self, *, scene_id: str, token_id: str) -> dict | None:
        with engine_connect() as conn:
            row = one_or_none(
                conn.execute(
                    select(tokens_table)
                    .where(tokens_table.c.id == token_id)
                    .where(tokens_table.c.scene_id == scene_id)
                    .limit(1)
                )
            )

        return self._hydrate(row) if row else None

    def list_by_scene(self, scene_id: str) -> list[dict]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(tokens_table)
                    .where(tokens_table.c.scene_id == scene_id)
                    .order_by(tokens_table.c.created_at.asc())
                )
            )

        return [self._hydrate(row) for row in rows]

    def list_by_actor(self, actor_id: str) -> list[dict]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(tokens_table)
                    .where(tokens_table.c.actor_id == actor_id)
                    .order_by(tokens_table.c.created_at.asc())
                )
            )

        return [self._hydrate(row) for row in rows]

    def move(
        self,
        *,
        token_id: str,
        grid_x: int,
        grid_y: int,
        expected_version: int | None = None,
    ) -> dict | None:
        now = int(time.time())
        with engine_begin() as conn:
            stmt = update(tokens_table).where(tokens_table.c.id == token_id)
            if expected_version is not None:
                stmt = stmt.where(tokens_table.c.version == expected_version)
            result = conn.execute(
                stmt.values(
                    grid_x=grid_x,
                    grid_y=grid_y,
                    version=tokens_table.c.version + 1,
                    updated_at=now,
                )
            )
            if result.rowcount != 1:
                return None
            row = self._get_by_id(conn, token_id)

        return self._hydrate(row) if row else None

    def update_overrides(
        self,
        *,
        token_id: str,
        overrides: dict,
        expected_version: int | None = None,
    ) -> dict | None:
        now = int(time.time())
        with engine_begin() as conn:
            stmt = update(tokens_table).where(tokens_table.c.id == token_id)
            if expected_version is not None:
                stmt = stmt.where(tokens_table.c.version == expected_version)
            result = conn.execute(
                stmt.values(
                    overrides_json=json.dumps(overrides),
                    version=tokens_table.c.version + 1,
                    updated_at=now,
                )
            )
            if result.rowcount != 1:
                return None
            row = self._get_by_id(conn, token_id)

        return self._hydrate(row) if row else None

    def update_elevation_and_overrides(self, *, token_id: str, elevation: float, overrides: dict, expected_version: int | None = None) -> dict | None:
        now=int(time.time())
        with engine_begin() as conn:
            stmt=update(tokens_table).where(tokens_table.c.id==token_id)
            if expected_version is not None: stmt=stmt.where(tokens_table.c.version==expected_version)
            result=conn.execute(stmt.values(elevation=elevation,overrides_json=json.dumps(overrides),version=tokens_table.c.version+1,updated_at=now))
            if result.rowcount!=1:return None
            row=self._get_by_id(conn,token_id)
        return self._hydrate(row) if row else None

    def update_link_mode_and_overrides(
        self,
        *,
        token_id: str,
        actor_link_mode: str,
        overrides: dict,
        name: str | None = None,
        token_asset_url: str | None = None,
        expected_version: int | None = None,
    ) -> dict | None:
        now = int(time.time())
        values = {
            "actor_link_mode": actor_link_mode,
            "overrides_json": json.dumps(overrides),
            "version": tokens_table.c.version + 1,
            "updated_at": now,
        }
        if name is not None:
            values["name"] = name
        if token_asset_url is not None:
            values["token_asset_url"] = token_asset_url

        with engine_begin() as conn:
            stmt = update(tokens_table).where(tokens_table.c.id == token_id)
            if expected_version is not None:
                stmt = stmt.where(tokens_table.c.version == expected_version)
            result = conn.execute(stmt.values(**values))
            if result.rowcount != 1:
                return None
            row = self._get_by_id(conn, token_id)

        return self._hydrate(row) if row else None

    def set_vision(
        self,
        *,
        token_id: str,
        vision_enabled: bool,
        vision_range: float,
        expected_version: int | None = None,
    ) -> dict | None:
        now = int(time.time())
        with engine_begin() as conn:
            stmt = update(tokens_table).where(tokens_table.c.id == token_id)
            if expected_version is not None:
                stmt = stmt.where(tokens_table.c.version == expected_version)
            result = conn.execute(
                stmt.values(
                    vision_enabled=1 if vision_enabled else 0,
                    vision_range=vision_range,
                    version=tokens_table.c.version + 1,
                    updated_at=now,
                )
            )
            if result.rowcount != 1:
                return None
            row = self._get_by_id(conn, token_id)
            return self._hydrate(row) if row else None

    def set_hidden(
        self,
        *,
        token_id: str,
        hidden: bool,
        expected_version: int | None = None,
    ) -> dict | None:
        now = int(time.time())
        with engine_begin() as conn:
            stmt = update(tokens_table).where(tokens_table.c.id == token_id)
            if expected_version is not None:
                stmt = stmt.where(tokens_table.c.version == expected_version)
            result = conn.execute(
                stmt.values(
                    hidden=1 if hidden else 0,
                    version=tokens_table.c.version + 1,
                    updated_at=now,
                )
            )
            if result.rowcount != 1:
                return None
            row = self._get_by_id(conn, token_id)

        return self._hydrate(row) if row else None

    def remove(self, *, token_id: str) -> bool:
        with engine_begin() as conn:
            result = conn.execute(delete(tokens_table).where(tokens_table.c.id == token_id))

        return result.rowcount > 0

    def _get_by_id(self, conn: Connection, token_id: str) -> dict | None:
        return one_or_none(
            conn.execute(select(tokens_table).where(tokens_table.c.id == token_id).limit(1))
        )

    def _create_values(
        self,
        *,
        token_id: str,
        scene_id: str,
        actor_id: str | None,
        grid_x: int,
        grid_y: int,
        width_cells: int,
        height_cells: int,
        name: str | None,
        token_asset_url: str | None,
        disposition: str,
        actor_link_mode: str,
        controlled_by_role: str,
        controlled_by_user_ids: list[str] | None,
        rotation: float,
        visible: bool,
        hidden: bool,
        locked: bool,
        vision_enabled: bool,
        vision_range: float,
        elevation: float,
        overrides: dict | None,
        now: int,
    ) -> dict:
        return {
            "id": token_id,
            "scene_id": scene_id,
            "actor_id": actor_id,
            "grid_x": grid_x,
            "grid_y": grid_y,
            "width_cells": width_cells,
            "height_cells": height_cells,
            "rotation": rotation,
            "name": name,
            "token_asset_url": token_asset_url,
            "visible": 1 if visible else 0,
            "hidden": 1 if hidden else 0,
            "locked": 1 if locked else 0,
            "disposition": disposition,
            "actor_link_mode": actor_link_mode,
            "overrides_json": json.dumps(overrides or {}),
            "controlled_by_user_ids_json": json.dumps(controlled_by_user_ids or []),
            "controlled_by_role": controlled_by_role,
            "vision_enabled": 1 if vision_enabled else 0,
            "vision_range": vision_range,
            "elevation": elevation,
            "version": 1,
            "created_at": now,
            "updated_at": now,
        }

    def _hydrate(self, row: dict) -> dict:
        row["overrides"] = json.loads(row.get("overrides_json") or "{}")
        row["controlled_by_user_ids"] = json.loads(row.get("controlled_by_user_ids_json") or "[]")
        return row
