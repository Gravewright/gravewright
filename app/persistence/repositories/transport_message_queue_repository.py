from __future__ import annotations

import json
import time
import uuid
from typing import Any

from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update

from app.persistence.database import all_dicts
from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.database import one_or_none
from app.persistence.tables import transport_messages as messages_table
from app.realtime.events import TransportEvent


DEFAULT_TRANSPORT_MESSAGE_TTL_SECONDS = 5 * 60


class TransportMessageQueueRepository:
    def create_for_users(
        self,
        *,
        user_ids: list[str],
        room_id: str | None,
        event: TransportEvent,
        payload: dict[str, Any],
        ttl_seconds: int = DEFAULT_TRANSPORT_MESSAGE_TTL_SECONDS,
    ) -> None:
        if not user_ids:
            return
        now = int(time.time())
        expires_at = now + ttl_seconds
        payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        rows = [
            {
                "id": uuid.uuid4().hex,
                "target_user_id": user_id,
                "room_id": room_id,
                "event": event.value,
                "payload_json": payload_json,
                "created_at": now,
                "expires_at": expires_at,
                "consumed_at": None,
            }
            for user_id in user_ids
        ]
        with engine_begin() as conn:
            conn.execute(insert(messages_table), rows)

    def drain_for_user(self, *, user_id: str, limit: int = 200) -> list[dict[str, Any]]:
        now = int(time.time())
        with engine_begin() as conn:
            rows = all_dicts(
                conn.execute(
                    select(
                        messages_table.c.id,
                        messages_table.c.target_user_id,
                        messages_table.c.room_id,
                        messages_table.c.event,
                        messages_table.c.payload_json,
                        messages_table.c.created_at,
                    )
                    .where(messages_table.c.target_user_id == user_id)
                    .where(messages_table.c.consumed_at.is_(None))
                    .where(messages_table.c.expires_at > now)
                    .order_by(messages_table.c.created_at.asc())
                    .limit(limit)
                )
            )
            if rows:
                conn.execute(
                    update(messages_table)
                    .where(messages_table.c.id.in_([row["id"] for row in rows]))
                    .values(consumed_at=now)
                )
        return [
            {
                "id": row["id"],
                "target_user_id": row["target_user_id"],
                "room_id": row["room_id"],
                "event": row["event"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def close_player_messages(self, player_id: str) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(messages_table)
                .where(messages_table.c.target_user_id == player_id)
                .where(messages_table.c.consumed_at.is_(None))
                .values(consumed_at=now)
            )

    def close_room_messages(self, room_id: str) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(
                update(messages_table)
                .where(messages_table.c.room_id == room_id)
                .where(messages_table.c.consumed_at.is_(None))
                .values(consumed_at=now)
            )

    def has_pending_player_messages(self, player_id: str) -> bool:
        now = int(time.time())
        with engine_connect() as conn:
            row = one_or_none(
                conn.execute(
                    select(messages_table.c.id)
                    .where(messages_table.c.target_user_id == player_id)
                    .where(messages_table.c.consumed_at.is_(None))
                    .where(messages_table.c.expires_at > now)
                    .limit(1)
                )
            )
        return row is not None

    def has_pending_room_messages(self, room_id: str) -> bool:
        now = int(time.time())
        with engine_connect() as conn:
            row = one_or_none(
                conn.execute(
                    select(messages_table.c.id)
                    .where(messages_table.c.room_id == room_id)
                    .where(messages_table.c.consumed_at.is_(None))
                    .where(messages_table.c.expires_at > now)
                    .limit(1)
                )
            )
        return row is not None

    def delete_expired(self) -> None:
        now = int(time.time())
        with engine_begin() as conn:
            conn.execute(delete(messages_table).where(messages_table.c.expires_at <= now))
