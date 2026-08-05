from __future__ import annotations

import time

from sqlalchemy import select
from sqlalchemy import update

from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.engine import upsert_statement
from app.persistence.tables import campaign_presence
from app.persistence.tables import user_presence


class PresenceRepository:
    def touch(self, user_id: str) -> None:
        now = int(time.time())
        values = {"user_id": user_id, "last_seen_at": now, "updated_at": now}

        with engine_begin() as connection:
            connection.execute(
                upsert_statement(
                    dialect_name=connection.dialect.name,
                    table=user_presence,
                    values=values,
                    index_elements=[user_presence.c.user_id],
                    set_={"last_seen_at": now, "updated_at": now},
                )
            )

    def list_online_user_ids(
        self,
        *,
        user_ids: list[str],
        threshold_seconds: int,
    ) -> set[str]:
        if not user_ids:
            return set()

        now = int(time.time())
        cutoff = now - threshold_seconds

        with engine_connect() as connection:
            rows = (
                connection.execute(
                    select(user_presence.c.user_id)
                    .where(user_presence.c.user_id.in_(user_ids))
                    .where(user_presence.c.last_seen_at >= cutoff)
                )
                .mappings()
                .all()
            )

        return {row["user_id"] for row in rows}

    def touch_user_rooms(
        self,
        *,
        user_id: str,
        room_ids: list[str],
        threshold_seconds: int,
    ) -> list[str]:
        if not room_ids:
            return []

        now = int(time.time())
        cutoff = now - threshold_seconds

        with engine_begin() as connection:
            existing_rows = (
                connection.execute(
                    select(
                        campaign_presence.c.campaign_id,
                        campaign_presence.c.is_online,
                        campaign_presence.c.last_seen_at,
                    )
                    .where(campaign_presence.c.user_id == user_id)
                    .where(campaign_presence.c.campaign_id.in_(room_ids))
                )
                .mappings()
                .all()
            )

            existing = {row["campaign_id"]: row for row in existing_rows}
            changed_room_ids: list[str] = []

            for room_id in room_ids:
                row = existing.get(room_id)
                if row is None:
                    changed_room_ids.append(room_id)
                elif int(row["is_online"]) != 1:
                    changed_room_ids.append(room_id)
                elif int(row["last_seen_at"]) < cutoff:
                    changed_room_ids.append(room_id)

                values = {
                    "campaign_id": room_id,
                    "user_id": user_id,
                    "is_online": 1,
                    "last_seen_at": now,
                    "updated_at": now,
                }
                connection.execute(
                    upsert_statement(
                        dialect_name=connection.dialect.name,
                        table=campaign_presence,
                        values=values,
                        index_elements=[campaign_presence.c.campaign_id, campaign_presence.c.user_id],
                        set_={
                            "is_online": 1,
                            "last_seen_at": now,
                            "updated_at": now,
                        },
                    )
                )

            return changed_room_ids

    def leave_user_rooms(
        self,
        *,
        user_id: str,
        room_ids: list[str],
    ) -> list[str]:
        if not room_ids:
            return []

        now = int(time.time())

        with engine_begin() as connection:
            rows = (
                connection.execute(
                    select(campaign_presence.c.campaign_id)
                    .where(campaign_presence.c.user_id == user_id)
                    .where(campaign_presence.c.campaign_id.in_(room_ids))
                    .where(campaign_presence.c.is_online == 1)
                )
                .mappings()
                .all()
            )
            changed_room_ids = [row["campaign_id"] for row in rows]

            connection.execute(
                update(campaign_presence)
                .where(campaign_presence.c.user_id == user_id)
                .where(campaign_presence.c.campaign_id.in_(room_ids))
                .values(is_online=0, updated_at=now)
            )

            return changed_room_ids

    def mark_stale_room_presence_offline(
        self,
        *,
        threshold_seconds: int,
    ) -> None:
        now = int(time.time())
        cutoff = now - threshold_seconds

        with engine_begin() as connection:
            connection.execute(
                update(campaign_presence)
                .where(campaign_presence.c.is_online == 1)
                .where(campaign_presence.c.last_seen_at < cutoff)
                .values(is_online=0, updated_at=now)
            )

    def list_online_user_ids_by_room(
        self,
        *,
        room_ids: list[str],
        threshold_seconds: int,
    ) -> dict[str, set[str]]:
        if not room_ids:
            return {}

        now = int(time.time())
        cutoff = now - threshold_seconds

        with engine_connect() as connection:
            rows = (
                connection.execute(
                    select(campaign_presence.c.campaign_id, campaign_presence.c.user_id)
                    .where(campaign_presence.c.campaign_id.in_(room_ids))
                    .where(campaign_presence.c.is_online == 1)
                    .where(campaign_presence.c.last_seen_at >= cutoff)
                )
                .mappings()
                .all()
            )

        online_by_room: dict[str, set[str]] = {room_id: set() for room_id in room_ids}
        for row in rows:
            online_by_room.setdefault(row["campaign_id"], set()).add(row["user_id"])
        return online_by_room
