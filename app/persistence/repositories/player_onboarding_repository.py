from __future__ import annotations

import time

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.persistence.database import engine_begin
from app.persistence.tables import campaign_members, campaign_player_onboarding


class PlayerOnboardingRepository:
    def claim_first_visit(self, *, campaign_id: str, user_id: str) -> str:
        """Atomically claim the one-time interface introduction for a player."""
        with engine_begin() as connection:
            role = connection.scalar(
                select(campaign_members.c.role)
                .where(campaign_members.c.campaign_id == campaign_id)
                .where(campaign_members.c.user_id == user_id)
                .limit(1)
            )
            if role is None:
                return "not_found"
            if role != "player":
                return "denied"

            dialect_insert = (
                postgresql_insert if connection.dialect.name == "postgresql" else sqlite_insert
            )
            statement = (
                dialect_insert(campaign_player_onboarding)
                .values(campaign_id=campaign_id, user_id=user_id, shown_at=int(time.time()))
                .on_conflict_do_nothing(index_elements=["campaign_id", "user_id"])
            )
            return "claimed" if connection.execute(statement).rowcount == 1 else "already_claimed"
