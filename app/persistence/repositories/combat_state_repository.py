from __future__ import annotations

import time

from sqlalchemy import select

from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.engine import upsert_statement
from app.persistence.tables import combat_states


class CombatStateRepository:
    def get(self, *, campaign_id: str) -> dict | None:
        with engine_connect() as connection:
            row = (
                connection.execute(
                    select(combat_states).where(combat_states.c.campaign_id == campaign_id).limit(1)
                )
                .mappings()
                .first()
            )
        return dict(row) if row is not None else None

    def upsert(self, *, campaign_id: str, is_active: bool, round_number: int) -> dict:
        now = int(time.time())
        normalized_round = max(0, int(round_number))
        values = {
            "campaign_id": campaign_id,
            "is_active": 1 if is_active else 0,
            "round_number": normalized_round,
            "created_at": now,
            "updated_at": now,
        }

        with engine_begin() as connection:
            connection.execute(
                upsert_statement(
                    dialect_name=connection.dialect.name,
                    table=combat_states,
                    values=values,
                    index_elements=[combat_states.c.campaign_id],
                    set_={
                        "is_active": values["is_active"],
                        "round_number": normalized_round,
                        "updated_at": now,
                    },
                )
            )
            row = (
                connection.execute(
                    select(combat_states).where(combat_states.c.campaign_id == campaign_id).limit(1)
                )
                .mappings()
                .first()
            )
        return dict(row) if row is not None else values

    def end(self, *, campaign_id: str) -> dict:
        current = self.get(campaign_id=campaign_id) or {"round_number": 0}
        return self.upsert(campaign_id=campaign_id, is_active=False, round_number=int(current.get("round_number") or 0))
