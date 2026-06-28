from __future__ import annotations

import time
import uuid

from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update

from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import asset_folders
from app.persistence.tables import library_assets


class AssetRepository:
    """Persistence for the dedicated asset library (``library_assets`` table)."""

    def create(
        self,
        *,
        campaign_id: str,
        owner_user_id: str | None,
        filename: str,
        content_type: str,
        byte_size: int,
        storage_path: str,
        hash: str,
        width: int | None = None,
        height: int | None = None,
        folder_id: str | None = None,
    ) -> dict:
        now = int(time.time())
        asset_id = uuid.uuid4().hex
        with engine_begin() as conn:
            conn.execute(
                insert(library_assets).values(
                    id=asset_id,
                    campaign_id=campaign_id,
                    owner_user_id=owner_user_id,
                    folder_id=folder_id,
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
            row = one_or_none(conn.execute(select(library_assets).where(library_assets.c.id == asset_id).limit(1)))
        if row is None:
            raise RuntimeError("Created library asset could not be read back.")
        return row

    def get_by_id(self, asset_id: str) -> dict | None:
        with engine_connect() as conn:
            return one_or_none(conn.execute(select(library_assets).where(library_assets.c.id == asset_id).limit(1)))

    def list_for_campaign(self, *, campaign_id: str) -> list[dict]:
        stmt = (
            select(library_assets)
            .where(library_assets.c.campaign_id == campaign_id)
            .order_by(library_assets.c.created_at.desc())
        )
        with engine_connect() as conn:
            return all_dicts(conn.execute(stmt))

    def update_folder(self, *, asset_id: str, folder_id: str | None) -> dict | None:
        with engine_begin() as conn:
            row = one_or_none(conn.execute(select(library_assets).where(library_assets.c.id == asset_id).limit(1)))
            if row is None:
                return None
            conn.execute(
                update(library_assets)
                .where(library_assets.c.id == asset_id)
                .values(folder_id=folder_id)
            )
            return one_or_none(conn.execute(select(library_assets).where(library_assets.c.id == asset_id).limit(1)))

    def update_storage_path(self, *, asset_id: str, storage_path: str) -> None:
        with engine_begin() as conn:
            conn.execute(
                update(library_assets)
                .where(library_assets.c.id == asset_id)
                .values(storage_path=storage_path)
            )

    def delete(self, asset_id: str) -> bool:
        with engine_begin() as conn:
            result = conn.execute(delete(library_assets).where(library_assets.c.id == asset_id))
        return bool(result.rowcount)


class AssetFolderRepository:
    def list_for_campaign(self, *, campaign_id: str) -> list[dict]:
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(asset_folders)
                    .where(asset_folders.c.campaign_id == campaign_id)
                    .order_by(asset_folders.c.sort_order.asc(), asset_folders.c.name.asc())
                )
            )

    def get(self, folder_id: str) -> dict | None:
        with engine_connect() as conn:
            return one_or_none(conn.execute(select(asset_folders).where(asset_folders.c.id == folder_id).limit(1)))

    def create(self, *, campaign_id: str, parent_id: str | None, name: str) -> dict:
        now = int(time.time())
        folder_id = uuid.uuid4().hex
        normalized = " ".join(str(name or "").split())[:120] or "Nova pasta"
        with engine_begin() as conn:
            conn.execute(
                insert(asset_folders).values(
                    id=folder_id,
                    campaign_id=campaign_id,
                    parent_id=parent_id,
                    name=normalized,
                    sort_order=0,
                    created_at=now,
                    updated_at=now,
                )
            )
            row = one_or_none(conn.execute(select(asset_folders).where(asset_folders.c.id == folder_id).limit(1)))
        if row is None:
            raise RuntimeError("Created asset folder could not be read back.")
        return row

    def delete(self, *, folder_id: str) -> bool:
        with engine_begin() as conn:
            conn.execute(update(library_assets).where(library_assets.c.folder_id == folder_id).values(folder_id=None))
            result = conn.execute(delete(asset_folders).where(asset_folders.c.id == folder_id))
        return bool(result.rowcount)
