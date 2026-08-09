from __future__ import annotations

import time

from sqlalchemy import select

from app.persistence.database import engine_begin, engine_connect
from app.persistence.engine import upsert_statement
from app.persistence.tables import campaign_lobby_states


class LobbyRepository:
    def set_state(self, *, campaign_id: str, user_id: str, is_ready: bool,
                  selected_actor_id: str | None, assets_state: str) -> dict:
        now = int(time.time())
        values = {
            "campaign_id": campaign_id, "user_id": user_id,
            "is_ready": int(is_ready), "selected_actor_id": selected_actor_id,
            "assets_state": assets_state, "updated_at": now,
        }
        with engine_begin() as connection:
            connection.execute(upsert_statement(
                dialect_name=connection.dialect.name, table=campaign_lobby_states,
                values=values,
                index_elements=[campaign_lobby_states.c.campaign_id, campaign_lobby_states.c.user_id],
                set_={key: value for key, value in values.items() if key not in {"campaign_id", "user_id"}},
            ))
        return values

    def get(self, *, campaign_id: str, user_id: str) -> dict | None:
        with engine_connect() as connection:
            row = connection.execute(select(campaign_lobby_states).where(
                campaign_lobby_states.c.campaign_id == campaign_id,
                campaign_lobby_states.c.user_id == user_id,
            )).mappings().first()
        return dict(row) if row else None

    def list_campaign(self, campaign_id: str) -> list[dict]:
        with engine_connect() as connection:
            return [dict(row) for row in connection.execute(
                select(campaign_lobby_states).where(
                    campaign_lobby_states.c.campaign_id == campaign_id
                )
            ).mappings()]
