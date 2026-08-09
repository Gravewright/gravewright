from __future__ import annotations

import time

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.persistence.database import engine_begin, engine_connect, one_or_none
from app.persistence.tables import (
    actors_core,
    campaign_gm_onboarding,
    campaign_join_codes,
    campaign_members,
    campaigns,
    scenes,
)


class GmOnboardingRepository:
    def progress(self, *, campaign_id: str, user_id: str, now: int | None = None) -> dict | None:
        timestamp = int(time.time()) if now is None else now
        with engine_connect() as connection:
            membership = one_or_none(connection.execute(
                select(campaigns.c.active_system_id, campaign_members.c.role)
                .select_from(campaigns.join(campaign_members, campaign_members.c.campaign_id == campaigns.c.id))
                .where(campaigns.c.id == campaign_id)
                .where(campaign_members.c.user_id == user_id)
                .limit(1)
            ))
            if membership is None:
                return None
            actor_count = connection.scalar(
                select(func.count()).select_from(actors_core)
                .where(actors_core.c.campaign_id == campaign_id)
                .where(actors_core.c.status == "active")
            ) or 0
            scene_count = connection.scalar(
                select(func.count()).select_from(scenes)
                .where(scenes.c.campaign_id == campaign_id)
            ) or 0
            active_code = connection.scalar(
                select(func.count()).select_from(campaign_join_codes)
                .where(campaign_join_codes.c.campaign_id == campaign_id)
                .where(campaign_join_codes.c.revoked_at.is_(None))
                .where(campaign_join_codes.c.expires_at > timestamp)
                .where(
                    (campaign_join_codes.c.max_uses.is_(None))
                    | (campaign_join_codes.c.use_count < campaign_join_codes.c.max_uses)
                )
            ) or 0
            preference = one_or_none(connection.execute(
                select(campaign_gm_onboarding.c.dismissed_at)
                .where(campaign_gm_onboarding.c.campaign_id == campaign_id)
                .where(campaign_gm_onboarding.c.user_id == user_id)
            ))
        return {
            "role": membership["role"],
            "has_system": bool(membership["active_system_id"]),
            "has_actor": actor_count > 0,
            "has_scene": scene_count > 0,
            "has_join_code": active_code > 0,
            "dismissed": bool(preference and preference["dismissed_at"] is not None),
        }

    def set_dismissed(self, *, campaign_id: str, user_id: str, dismissed: bool) -> None:
        timestamp = int(time.time())
        values = {
            "campaign_id": campaign_id,
            "user_id": user_id,
            "dismissed_at": timestamp if dismissed else None,
            "updated_at": timestamp,
        }
        with engine_begin() as connection:
            dialect_insert = postgresql_insert if connection.dialect.name == "postgresql" else sqlite_insert
            statement = dialect_insert(campaign_gm_onboarding).values(**values)
            statement = statement.on_conflict_do_update(
                index_elements=["campaign_id", "user_id"],
                set_={"dismissed_at": values["dismissed_at"], "updated_at": timestamp},
            )
            connection.execute(statement)
