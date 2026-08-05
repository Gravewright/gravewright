from __future__ import annotations

import time
import uuid

from sqlalchemy import select

from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.engine import upsert_statement
from app.persistence.tables import actor_permissions


class ActorPermissionRepository:
    def get_for_user(self, *, actor_id: str, user_id: str) -> dict | None:
        with engine_connect() as connection:
            row = (
                connection.execute(
                    select(actor_permissions)
                    .where(actor_permissions.c.actor_id == actor_id)
                    .where(actor_permissions.c.user_id == user_id)
                    .limit(1)
                )
                .mappings()
                .first()
            )
        return dict(row) if row else None

    def list_for_actor(self, *, actor_id: str) -> dict[str, dict]:
        with engine_connect() as connection:
            rows = (
                connection.execute(select(actor_permissions).where(actor_permissions.c.actor_id == actor_id))
                .mappings()
                .all()
            )
        return {row["user_id"]: dict(row) for row in rows}

    def upsert_for_user(
        self,
        *,
        actor_id: str,
        user_id: str,
        can_view: bool,
        can_edit: bool,
    ) -> None:
        now = int(time.time())
        values = {
            "id": uuid.uuid4().hex,
            "actor_id": actor_id,
            "user_id": user_id,
            "can_view": 1 if can_view else 0,
            "can_edit": 1 if can_edit else 0,
            "created_at": now,
            "updated_at": now,
        }
        with engine_begin() as connection:
            connection.execute(
                upsert_statement(
                    dialect_name=connection.dialect.name,
                    table=actor_permissions,
                    values=values,
                    index_elements=[actor_permissions.c.actor_id, actor_permissions.c.user_id],
                    set_={
                        "can_view": values["can_view"],
                        "can_edit": values["can_edit"],
                        "updated_at": now,
                    },
                )
            )
