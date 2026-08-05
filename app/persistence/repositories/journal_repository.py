from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update
import time
import uuid

from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.engine import upsert_statement
from app.persistence.tables import journal_owners as journal_owners_table
from app.persistence.tables import journals as journals_table
from app.persistence.tables import quest_board_entries as quest_board_entries_table
from app.persistence.tables import users as users_table


class JournalRepository:
    def create(
        self,
        *,
        campaign_id: str,
        created_by_user_id: str,
        journal_type: str,
        title: str,
        folder_id: str | None = None,
        visibility: str = "private",
        content_markdown: str = "",
        data_json: str = "{}",
        owner_user_ids: list[str] | None = None,
    ) -> str:
        now = int(time.time())
        journal_id = uuid.uuid4().hex
        with engine_begin() as conn:
            conn.execute(
                insert(journals_table).values(
                    id=journal_id,
                    campaign_id=campaign_id,
                    folder_id=folder_id,
                    created_by_user_id=created_by_user_id,
                    type=journal_type,
                    title=title,
                    visibility=visibility,
                    version=1,
                    data_json=data_json,
                    content_markdown=content_markdown,
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
            )
            for owner_id in owner_user_ids or []:
                conn.execute(
                    upsert_statement(
                        dialect_name=conn.dialect.name,
                        table=journal_owners_table,
                        values={"journal_id": journal_id, "user_id": owner_id},
                        index_elements=[journal_owners_table.c.journal_id, journal_owners_table.c.user_id],
                        set_={"user_id": owner_id},
                    )
                )
        return journal_id

    def get_by_id(self, journal_id: str) -> dict | None:
        with engine_connect() as conn:
            return one_or_none(conn.execute(select(journals_table).where(journals_table.c.id == journal_id).limit(1)))

    def list_active_for_campaign(self, *, campaign_id: str) -> list[dict]:
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(journals_table, users_table.c.name.label("created_by_name"))
                    .select_from(journals_table.join(users_table, users_table.c.id == journals_table.c.created_by_user_id))
                    .where(journals_table.c.campaign_id == campaign_id)
                    .where(journals_table.c.status == "active")
                    .order_by(journals_table.c.created_at.asc())
                )
            )

    def update(
        self,
        *,
        journal_id: str,
        title: str,
        folder_id: str | None,
        visibility: str,
        content_markdown: str,
        data_json: str,
    ) -> int:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(journals_table)
                .where(journals_table.c.id == journal_id)
                .values(
                    title=title,
                    folder_id=folder_id,
                    visibility=visibility,
                    content_markdown=content_markdown,
                    data_json=data_json,
                    version=journals_table.c.version + 1,
                    updated_at=now,
                )
            )
            row = one_or_none(conn.execute(select(journals_table.c.version).where(journals_table.c.id == journal_id)))
        return int(row["version"]) if row is not None else 0

    def update_data(self, *, journal_id: str, data_json: str) -> int:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(journals_table)
                .where(journals_table.c.id == journal_id)
                .values(data_json=data_json, version=journals_table.c.version + 1, updated_at=now)
            )
            row = one_or_none(conn.execute(select(journals_table.c.version).where(journals_table.c.id == journal_id)))
        return int(row["version"]) if row is not None else 0

    def clear_folder(self, *, folder_id: str) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(update(journals_table).where(journals_table.c.folder_id == folder_id).values(folder_id=None, updated_at=now))

    def has_owner(self, *, journal_id: str, user_id: str) -> bool:
        with engine_connect() as conn:
            row = one_or_none(
                conn.execute(
                    select(journal_owners_table.c.journal_id)
                    .where(journal_owners_table.c.journal_id == journal_id)
                    .where(journal_owners_table.c.user_id == user_id)
                    .limit(1)
                )
            )
        return row is not None

    def set_owners(self, *, journal_id: str, user_ids: list[str]) -> None:
        with engine_begin() as conn:
            conn.execute(delete(journal_owners_table).where(journal_owners_table.c.journal_id == journal_id))
            for user_id in user_ids:
                conn.execute(
                    upsert_statement(
                        dialect_name=conn.dialect.name,
                        table=journal_owners_table,
                        values={"journal_id": journal_id, "user_id": user_id},
                        index_elements=[journal_owners_table.c.journal_id, journal_owners_table.c.user_id],
                        set_={"user_id": user_id},
                    )
                )

    def add_owner(self, *, journal_id: str, user_id: str) -> None:
        with engine_begin() as conn:
            conn.execute(
                upsert_statement(
                    dialect_name=conn.dialect.name,
                    table=journal_owners_table,
                    values={"journal_id": journal_id, "user_id": user_id},
                    index_elements=[journal_owners_table.c.journal_id, journal_owners_table.c.user_id],
                    set_={"user_id": user_id},
                )
            )

    def remove_owner(self, *, journal_id: str, user_id: str) -> None:
        with engine_begin() as conn:
            conn.execute(
                delete(journal_owners_table)
                .where(journal_owners_table.c.journal_id == journal_id)
                .where(journal_owners_table.c.user_id == user_id)
            )

    def set_folder(self, *, journal_id: str, folder_id: str | None) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(update(journals_table).where(journals_table.c.id == journal_id).values(folder_id=folder_id, updated_at=now))

    def list_owners_for_journal(self, *, journal_id: str) -> list[dict]:
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(users_table.c.id, users_table.c.name)
                    .select_from(journal_owners_table.join(users_table, users_table.c.id == journal_owners_table.c.user_id))
                    .where(journal_owners_table.c.journal_id == journal_id)
                    .order_by(users_table.c.name.asc())
                )
            )

    def list_owners_for_campaign_journals(self, *, campaign_id: str) -> dict[str, list[dict]]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(
                    select(
                        journal_owners_table.c.journal_id,
                        users_table.c.id.label("user_id"),
                        users_table.c.name.label("user_name"),
                    )
                    .select_from(
                        journal_owners_table
                        .join(users_table, users_table.c.id == journal_owners_table.c.user_id)
                        .join(journals_table, journals_table.c.id == journal_owners_table.c.journal_id)
                    )
                    .where(journals_table.c.campaign_id == campaign_id)
                    .order_by(users_table.c.name.asc())
                )
            )
        owners_by_journal: dict[str, list[dict]] = {}
        for row in rows:
            owners_by_journal.setdefault(row["journal_id"], []).append(
                {"id": row["user_id"], "name": row["user_name"]}
            )
        return owners_by_journal

    def soft_delete(self, *, journal_id: str) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(update(journals_table).where(journals_table.c.id == journal_id).values(status="deleted", updated_at=now))

    def list_board_entries(self, *, board_id: str) -> list[dict]:
        with engine_connect() as conn:
            return all_dicts(
                conn.execute(
                    select(
                        quest_board_entries_table.c.board_id,
                        quest_board_entries_table.c.quest_id,
                        quest_board_entries_table.c.sort_order,
                        quest_board_entries_table.c.pinned,
                        quest_board_entries_table.c.visibility,
                        quest_board_entries_table.c.created_at,
                    )
                    .where(quest_board_entries_table.c.board_id == board_id)
                    .order_by(
                        quest_board_entries_table.c.pinned.desc(),
                        quest_board_entries_table.c.sort_order.asc(),
                        quest_board_entries_table.c.created_at.asc(),
                    )
                )
            )

    def list_boards_for_quest(self, *, quest_id: str) -> list[str]:
        with engine_connect() as conn:
            rows = all_dicts(
                conn.execute(select(quest_board_entries_table.c.board_id).where(quest_board_entries_table.c.quest_id == quest_id))
            )
        return [row["board_id"] for row in rows]

    def get_board_entry(self, *, board_id: str, quest_id: str) -> dict | None:
        with engine_connect() as conn:
            return one_or_none(
                conn.execute(
                    select(
                        quest_board_entries_table.c.board_id,
                        quest_board_entries_table.c.quest_id,
                        quest_board_entries_table.c.sort_order,
                        quest_board_entries_table.c.pinned,
                        quest_board_entries_table.c.visibility,
                        quest_board_entries_table.c.created_at,
                    )
                    .where(quest_board_entries_table.c.board_id == board_id)
                    .where(quest_board_entries_table.c.quest_id == quest_id)
                    .limit(1)
                )
            )

    def next_board_sort_order(self, *, board_id: str) -> int:
        with engine_connect() as conn:
            row = one_or_none(
                conn.execute(
                    select(func.coalesce(func.max(quest_board_entries_table.c.sort_order), 0).label("max_order"))
                    .where(quest_board_entries_table.c.board_id == board_id)
                )
            )
        return int(row["max_order"]) + 10 if row is not None else 10

    def add_board_entry(
        self,
        *,
        board_id: str,
        quest_id: str,
        sort_order: int,
        pinned: bool = False,
        visibility: str = "public_card",
    ) -> None:
        now = int(time.time())
        values = {
            "board_id": board_id,
            "quest_id": quest_id,
            "sort_order": sort_order,
            "pinned": 1 if pinned else 0,
            "visibility": visibility,
            "created_at": now,
        }
        with engine_begin() as conn:
            conn.execute(
                upsert_statement(
                    dialect_name=conn.dialect.name,
                    table=quest_board_entries_table,
                    values=values,
                    index_elements=[quest_board_entries_table.c.board_id, quest_board_entries_table.c.quest_id],
                    set_={"sort_order": sort_order, "pinned": values["pinned"], "visibility": visibility},
                )
            )

    def remove_board_entry(self, *, board_id: str, quest_id: str) -> None:
        with engine_begin() as conn:
            conn.execute(
                delete(quest_board_entries_table)
                .where(quest_board_entries_table.c.board_id == board_id)
                .where(quest_board_entries_table.c.quest_id == quest_id)
            )

    def set_board_entry_order(self, *, board_id: str, ordered_quest_ids: list[str]) -> None:
        with engine_begin() as conn:
            for index, quest_id in enumerate(ordered_quest_ids):
                conn.execute(
                    update(quest_board_entries_table)
                    .where(quest_board_entries_table.c.board_id == board_id)
                    .where(quest_board_entries_table.c.quest_id == quest_id)
                    .values(sort_order=(index + 1) * 10)
                )

    def set_board_entry_pinned(self, *, board_id: str, quest_id: str, pinned: bool) -> None:
        with engine_begin() as conn:
            conn.execute(
                update(quest_board_entries_table)
                .where(quest_board_entries_table.c.board_id == board_id)
                .where(quest_board_entries_table.c.quest_id == quest_id)
                .values(pinned=1 if pinned else 0)
            )
