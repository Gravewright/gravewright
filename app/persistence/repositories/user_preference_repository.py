from __future__ import annotations

import time

from sqlalchemy import select

from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.engine import upsert_statement
from app.persistence.tables import user_preferences


class UserPreferenceRepository:
    def _read(self, column, user_id: str) -> str | None:
        with engine_connect() as connection:
            value = connection.execute(
                select(column).where(user_preferences.c.user_id == user_id).limit(1)
            ).scalar_one_or_none()
        return str(value) if value is not None else None



    def _write(self, field: str, *, user_id: str, value: str) -> None:
        now = int(time.time())
        with engine_begin() as connection:
            statement = upsert_statement(
                dialect_name=connection.dialect.name,
                table=user_preferences,
                values={"user_id": user_id, field: value, "updated_at": now},
                index_elements=["user_id"],
                set_={field: value, "updated_at": now},
            )
            connection.execute(statement)

    def get_game_layout_mode(self, user_id: str) -> str | None:
        return self._read(user_preferences.c.game_layout_mode, user_id)

    def set_game_layout_mode(self, *, user_id: str, layout_mode: str) -> None:
        self._write("game_layout_mode", user_id=user_id, value=layout_mode)

    def get_vision_mode(self, user_id: str) -> str | None:
        return self._read(user_preferences.c.vision_mode, user_id)

    def set_vision_mode(self, *, user_id: str, vision_mode: str) -> None:
        self._write("vision_mode", user_id=user_id, value=vision_mode)

    def get_ping_color(self, user_id: str) -> str | None:
        return self._read(user_preferences.c.ping_color, user_id)

    def set_ping_color(self, *, user_id: str, ping_color: str) -> None:
        self._write("ping_color", user_id=user_id, value=ping_color)
