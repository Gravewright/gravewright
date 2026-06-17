from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import select

from app.persistence.database import engine_begin
from app.persistence.database import engine_connect
from app.persistence.tables import room_event_log as room_event_log_table
from app.realtime.events import TransportEvent


DEFAULT_ROOM_EVENT_LOG_TTL_SECONDS = 120
DEFAULT_ROOM_EVENT_REPLAY_LIMIT = 200

REPLAYABLE_TRANSPORT_EVENTS = frozenset(
    {
        TransportEvent.SCENE_ACTIVATED.value,
        TransportEvent.SCENE_UPDATED.value,
        TransportEvent.SCENE_LAYER_CREATED.value,
        TransportEvent.SCENE_LAYER_UPDATED.value,
        TransportEvent.SCENE_LAYER_DELETED.value,
        TransportEvent.SCENE_CHUNK_UPDATED.value,
        TransportEvent.SCENE_CHUNK_DELETED.value,
        TransportEvent.COMBAT_STARTED.value,
        TransportEvent.COMBAT_UPDATED.value,
        TransportEvent.COMBAT_ENDED.value,
    }
)


@dataclass(frozen=True)
class RoomEventReplay:
    events: tuple[dict[str, Any], ...]
    expired: bool
    latest_seq: int | None


class RoomEventLog:
    def append(
        self,
        *,
        room_id: str,
        event: TransportEvent | str,
        payload: dict[str, Any],
        ttl_seconds: int = DEFAULT_ROOM_EVENT_LOG_TTL_SECONDS,
    ) -> int | None:
        event_value = event.value if isinstance(event, TransportEvent) else event
        if event_value not in REPLAYABLE_TRANSPORT_EVENTS:
            return None

        now = int(time.time())
        event_id = uuid.uuid4().hex
        payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

        with engine_begin() as connection:
                                                                           
                                                                                   
                                                                               
                                                                            
                                                                             
                                                                                
                                                                      
            result = connection.execute(
                room_event_log_table.insert().values(
                    id=event_id,
                    room_id=room_id,
                    event=event_value,
                    payload_json=payload_json,
                    created_at=now,
                    expires_at=now + ttl_seconds,
                )
            )
            return int(result.inserted_primary_key[0])

    def replay_since(
        self,
        *,
        room_id: str,
        after_seq: int,
        limit: int = DEFAULT_ROOM_EVENT_REPLAY_LIMIT,
    ) -> RoomEventReplay:
        now = int(time.time())
        self.prune_expired(now=now)

        if after_seq <= 0:
            return RoomEventReplay(events=(), expired=False, latest_seq=self.latest_seq(room_id))

        with engine_connect() as connection:
            oldest_seq = connection.execute(
                select(func.min(room_event_log_table.c.seq))
                .where(room_event_log_table.c.room_id == room_id)
                .where(room_event_log_table.c.expires_at > now)
            ).scalar_one_or_none()
            latest_seq = connection.execute(
                select(func.max(room_event_log_table.c.seq))
                .where(room_event_log_table.c.room_id == room_id)
                .where(room_event_log_table.c.expires_at > now)
            ).scalar_one_or_none()

            rows = (
                connection.execute(
                    select(
                        room_event_log_table.c.seq,
                        room_event_log_table.c.id,
                        room_event_log_table.c.room_id,
                        room_event_log_table.c.event,
                        room_event_log_table.c.payload_json,
                        room_event_log_table.c.created_at,
                    )
                    .where(room_event_log_table.c.room_id == room_id)
                    .where(room_event_log_table.c.seq > after_seq)
                    .where(room_event_log_table.c.expires_at > now)
                    .order_by(room_event_log_table.c.seq.asc())
                    .limit(limit)
                )
                .mappings()
                .all()
            )

        expired = oldest_seq is not None and after_seq < int(oldest_seq) - 1
        events = tuple(
            {
                "type": "event",
                "id": row["id"],
                "event": row["event"],
                "room_id": row["room_id"],
                "payload": json.loads(row["payload_json"]),
                "ts": row["created_at"],
                "event_seq": row["seq"],
                "replayed": True,
            }
            for row in rows
        )
        return RoomEventReplay(
            events=events,
            expired=expired,
            latest_seq=int(latest_seq) if latest_seq is not None else None,
        )

    def latest_seq(self, room_id: str) -> int | None:
        now = int(time.time())
        with engine_connect() as connection:
            latest_seq = connection.execute(
                select(func.max(room_event_log_table.c.seq))
                .where(room_event_log_table.c.room_id == room_id)
                .where(room_event_log_table.c.expires_at > now)
            ).scalar_one_or_none()
        return int(latest_seq) if latest_seq is not None else None

    def prune_expired(self, *, now: int | None = None) -> int:
        timestamp = int(time.time()) if now is None else now
        with engine_begin() as connection:
            result = connection.execute(
                delete(room_event_log_table).where(room_event_log_table.c.expires_at <= timestamp)
            )
            return int(result.rowcount or 0)
