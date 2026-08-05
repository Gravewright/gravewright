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
from app.persistence.engine import upsert_statement
from app.persistence.tables import item_owners as item_owners_table
from app.persistence.tables import items_core as items_table
from app.persistence.tables import users as users_table


class ItemRepository:
    def create(
        self,
        *,
        campaign_id: str,
        system_id: str,
        item_type: str,
        name: str,
        created_by_user_id: str,
        folder_id: str | None = None,
        permissions_json: str = "{}",
        owner_user_ids: list[str] | None = None,
    ) -> str:
        now = int(time.time())
        item_id = uuid.uuid4().hex
        with engine_begin() as conn:
            conn.execute(
                insert(items_table).values(
                    id=item_id,
                    campaign_id=campaign_id,
                    system_id=system_id,
                    type=item_type,
                    name=name,
                    folder_id=folder_id,
                    permissions_json=permissions_json,
                    status="active",
                    version=1,
                    created_by_user_id=created_by_user_id,
                    created_at=now,
                    updated_at=now,
                )
            )
            for owner_id in owner_user_ids or []:
                conn.execute(
                    upsert_statement(
                        dialect_name=conn.dialect.name,
                        table=item_owners_table,
                        values={"item_id": item_id, "user_id": owner_id},
                        index_elements=[item_owners_table.c.item_id, item_owners_table.c.user_id],
                        set_={"user_id": owner_id},
                    )
                )
        return item_id

    def get(self, item_id: str) -> dict | None:
        with engine_connect() as conn:
            return one_or_none(conn.execute(select(items_table).where(items_table.c.id == item_id).limit(1)))

    def list_active_for_campaign(self, *, campaign_id: str) -> list[dict]:
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(items_table)
                    .where(items_table.c.campaign_id == campaign_id)
                    .where(items_table.c.status == "active")
                    .order_by(items_table.c.created_at.asc())
                )
            )

    def update_core(self, *, item_id: str, name: str, folder_id: str | None, portrait_asset_id: str | None) -> int:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(items_table)
                .where(items_table.c.id == item_id)
                .values(
                    name=name,
                    folder_id=folder_id,
                    portrait_asset_id=portrait_asset_id,
                    version=items_table.c.version + 1,
                    updated_at=now,
                )
            )
            row = one_or_none(conn.execute(select(items_table.c.version).where(items_table.c.id == item_id)))
        return int(row["version"]) if row is not None else 0

    def set_folder(self, *, item_id: str, folder_id: str | None) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(update(items_table).where(items_table.c.id == item_id).values(folder_id=folder_id, updated_at=now))

    def clear_folder(self, *, folder_id: str) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(update(items_table).where(items_table.c.folder_id == folder_id).values(folder_id=None, updated_at=now))

    def has_owner(self, *, item_id: str, user_id: str) -> bool:
        with engine_connect() as conn:
            row = one_or_none(
                conn.execute(
                    select(item_owners_table.c.item_id)
                    .where(item_owners_table.c.item_id == item_id)
                    .where(item_owners_table.c.user_id == user_id)
                    .limit(1)
                )
            )
        return row is not None

    def add_owner(self, *, item_id: str, user_id: str) -> None:
        with engine_begin() as conn:
            conn.execute(
                upsert_statement(
                    dialect_name=conn.dialect.name,
                    table=item_owners_table,
                    values={"item_id": item_id, "user_id": user_id},
                    index_elements=[item_owners_table.c.item_id, item_owners_table.c.user_id],
                    set_={"user_id": user_id},
                )
            )

    def remove_owner(self, *, item_id: str, user_id: str) -> None:
        with engine_begin() as conn:
            conn.execute(
                delete(item_owners_table)
                .where(item_owners_table.c.item_id == item_id)
                .where(item_owners_table.c.user_id == user_id)
            )

    def list_owners_for_item(self, *, item_id: str) -> list[dict]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(users_table.c.id, users_table.c.name)
                    .select_from(item_owners_table.join(users_table, users_table.c.id == item_owners_table.c.user_id))
                    .where(item_owners_table.c.item_id == item_id)
                    .order_by(users_table.c.name.asc())
                )
            )
        return rows

    def list_owners_for_campaign_items(self, *, campaign_id: str) -> dict[str, list[dict]]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(
                        item_owners_table.c.item_id,
                        users_table.c.id.label("user_id"),
                        users_table.c.name.label("user_name"),
                    )
                    .select_from(
                        item_owners_table
                        .join(users_table, users_table.c.id == item_owners_table.c.user_id)
                        .join(items_table, items_table.c.id == item_owners_table.c.item_id)
                    )
                    .where(items_table.c.campaign_id == campaign_id)
                    .order_by(users_table.c.name.asc())
                )
            )
        owners_by_item: dict[str, list[dict]] = {}
        for row in rows:
            owners_by_item.setdefault(row["item_id"], []).append(
                {"id": row["user_id"], "name": row["user_name"]}
            )
        return owners_by_item

    def soft_delete(self, *, item_id: str) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(update(items_table).where(items_table.c.id == item_id).values(status="deleted", updated_at=now))
