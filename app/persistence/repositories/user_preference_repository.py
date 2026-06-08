from __future__ import annotations

import time

from sqlalchemy import select

from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.engine import upsert_statement
from app.persistence.tables import user_preferences


class UserPreferenceRepository:
    def get_game_layout_mode(self, user_id: str) -> str | None:
        with engine_connect() as connection:
            value = connection.execute(
                select(user_preferences.c.game_layout_mode)
                .where(user_preferences.c.user_id == user_id)
                .limit(1)
            ).scalar_one_or_none()
        return str(value) if value is not None else None

    def set_game_layout_mode(self, *, user_id: str, layout_mode: str) -> None:
        now = int(time.time())
        with engine_begin() as connection:
            statement = upsert_statement(
                dialect_name=connection.dialect.name,
                table=user_preferences,
                values={
                    "user_id": user_id,
                    "game_layout_mode": layout_mode,
                    "updated_at": now,
                },
                index_elements=["user_id"],
                set_={"game_layout_mode": layout_mode, "updated_at": now},
            )
            connection.execute(statement)
