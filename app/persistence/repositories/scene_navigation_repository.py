"""Persistence for per-user scene navigation state."""

from __future__ import annotations

import time
from sqlalchemy import insert, select, update

from app.persistence.database import engine_begin
from app.persistence.tables import user_scene_navigation


class NavigationRepository:
    def get(self, campaign_id: str, user_id: str) -> dict | None:
        with engine_begin() as conn: row=conn.execute(select(user_scene_navigation).where(user_scene_navigation.c.campaign_id==campaign_id,user_scene_navigation.c.user_id==user_id)).mappings().first()
        return dict(row) if row else None
    def set(self, campaign_id: str, user_id: str, scene_id: str, reason: str, key: str | None) -> dict:
        now=int(time.time()); current=self.get(campaign_id,user_id)
        if current and key and current.get("idempotency_key")==key:return current
        with engine_begin() as conn:
            if current: conn.execute(update(user_scene_navigation).where(user_scene_navigation.c.campaign_id==campaign_id,user_scene_navigation.c.user_id==user_id).values(scene_id=scene_id,reason=reason,idempotency_key=key,version=user_scene_navigation.c.version+1,updated_at=now))
            else: conn.execute(insert(user_scene_navigation).values(campaign_id=campaign_id,user_id=user_id,scene_id=scene_id,reason=reason,idempotency_key=key,version=1,created_at=now,updated_at=now))
        return self.get(campaign_id,user_id)
