from __future__ import annotations

import time
import uuid

from sqlalchemy import insert
from sqlalchemy import select

from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import scene_groups as scene_groups_table


class SceneGroupRepository:
    def create(
        self,
        *,
        campaign_id: str,
        name: str,
        color: str = "#8ea8ff",
        sort_order: int = 0,
    ) -> dict:
        now = int(time.time())
        group_id = uuid.uuid4().hex
        with engine_begin() as conn:
            conn.execute(
                insert(scene_groups_table).values(
                    id=group_id,
                    campaign_id=campaign_id,
                    name=name,
                    color=color,
                    sort_order=sort_order,
                    created_at=now,
                    updated_at=now,
                )
            )
            row = one_or_none(
                conn.execute(select(scene_groups_table).where(scene_groups_table.c.id == group_id).limit(1))
            )
        if row is None:
            raise RuntimeError("Created scene group could not be read back.")
        return row

    def get_by_id(self, group_id: str) -> dict | None:
        with engine_connect() as conn:
            return one_or_none(
                conn.execute(select(scene_groups_table).where(scene_groups_table.c.id == group_id).limit(1))
            )

    def list_by_campaign(self, campaign_id: str) -> list[dict]:
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(scene_groups_table)
                    .where(scene_groups_table.c.campaign_id == campaign_id)
                    .order_by(scene_groups_table.c.sort_order.asc(), scene_groups_table.c.created_at.asc())
                )
            )
