from __future__ import annotations

import time
import uuid

from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update

from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import journal_assets as journal_assets_table


class JournalAssetRepository:
    def create(
        self,
        *,
        campaign_id: str,
        journal_id: str | None,
        owner_user_id: str,
        purpose: str,
        filename: str,
        content_type: str,
        byte_size: int,
        storage_path: str,
        hash: str,
        width: int | None = None,
        height: int | None = None,
    ) -> dict:
        now = int(time.time())
        asset_id = uuid.uuid4().hex
        with engine_begin() as conn:
            conn.execute(
                insert(journal_assets_table).values(
                    id=asset_id,
                    campaign_id=campaign_id,
                    journal_id=journal_id,
                    owner_user_id=owner_user_id,
                    purpose=purpose,
                    filename=filename,
                    content_type=content_type,
                    byte_size=byte_size,
                    width=width,
                    height=height,
                    storage_path=storage_path,
                    hash=hash,
                    created_at=now,
                )
            )
            row = one_or_none(conn.execute(select(journal_assets_table).where(journal_assets_table.c.id == asset_id).limit(1)))
        if row is None:
            raise RuntimeError("Created journal asset could not be read back.")
        return row

    def get_by_id(self, asset_id: str) -> dict | None:
        with engine_connect() as conn:
            return one_or_none(conn.execute(select(journal_assets_table).where(journal_assets_table.c.id == asset_id).limit(1)))

    def update_storage_path(self, *, asset_id: str, storage_path: str) -> None:
        with engine_begin() as conn:
            conn.execute(
                update(journal_assets_table)
                .where(journal_assets_table.c.id == asset_id)
                .values(storage_path=storage_path)
            )
