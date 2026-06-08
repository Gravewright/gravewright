from __future__ import annotations

import time
import uuid

from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update

from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import journal_folders as folder_table


class JournalFolderRepository:
    def create(
        self,
        *,
        campaign_id: str,
        created_by_user_id: str,
        name: str,
        parent_id: str | None = None,
        color: str | None = None,
    ) -> str:
        now = int(time.time())
        folder_id = uuid.uuid4().hex
        with engine_begin() as conn:
            conn.execute(
                insert(folder_table).values(
                    id=folder_id,
                    campaign_id=campaign_id,
                    created_by_user_id=created_by_user_id,
                    name=name,
                    parent_id=parent_id,
                    color=color,
                    created_at=now,
                    updated_at=now,
                )
            )
        return folder_id

    def list_for_campaign(self, *, campaign_id: str) -> list[dict]:
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(folder_table)
                    .where(folder_table.c.campaign_id == campaign_id)
                    .order_by(folder_table.c.created_at.asc())
                )
            )

    def get(self, *, folder_id: str, campaign_id: str) -> dict | None:
        with engine_connect() as conn:
            return one_or_none(
                conn.execute(
                    select(folder_table)
                    .where(folder_table.c.id == folder_id)
                    .where(folder_table.c.campaign_id == campaign_id)
                    .limit(1)
                )
            )

    def set_parent(self, *, folder_id: str, parent_id: str | None) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(folder_table)
                .where(folder_table.c.id == folder_id)
                .values(parent_id=parent_id, updated_at=now)
            )
