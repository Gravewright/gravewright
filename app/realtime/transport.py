from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Any

from litestar.connection import WebSocket

from app.contracts.transport import Payload
from app.contracts.transport import PlayerId
from app.contracts.transport import RoomId
from app.contracts.transport import RealtimeGatewayContract
from app.helpers.async_blocking import run_blocking
from app.domain.chat import ChatVisibility
from app.domain.roles import PlayerRole
from app.persistence.repositories.realtime_recipient_repository import RealtimeRecipientRepository
from app.realtime.envelopes import event_envelope
from app.realtime.event_log import RoomEventLog
from app.realtime.events import TransportEvent


@dataclass(frozen=True)
class WebSocketConnection:
    id: str
    user_id: str
    room_ids: tuple[str, ...]
    websocket: WebSocket


class WebSocketConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, WebSocketConnection] = {}
        self._connections_by_user: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(
        self,
        *,
        user_id: str,
        room_ids: list[str],
        websocket: WebSocket,
    ) -> str:
        connection_id = uuid.uuid4().hex
        connection = WebSocketConnection(
            id=connection_id,
            user_id=user_id,
            room_ids=tuple(room_ids),
            websocket=websocket,
        )

        async with self._lock:
            self._connections[connection_id] = connection
            self._connections_by_user.setdefault(user_id, set()).add(connection_id)

        return connection_id

    async def disconnect(self, connection_id: str) -> WebSocketConnection | None:
        async with self._lock:
            connection = self._connections.pop(connection_id, None)

            if connection is None:
                return None

            user_connections = self._connections_by_user.get(connection.user_id)
            if user_connections is not None:
                user_connections.discard(connection_id)

                if not user_connections:
                    self._connections_by_user.pop(connection.user_id, None)

            return connection

    async def is_user_connected(self, user_id: str) -> bool:
        async with self._lock:
            return bool(self._connections_by_user.get(user_id))

    async def connected_user_ids(self, user_ids: list[str]) -> set[str]:
        async with self._lock:
            return {
                user_id
                for user_id in user_ids
                if self._connections_by_user.get(user_id)
            }

    async def connected_user_ids_by_room(self, room_ids: list[str]) -> dict[str, set[str]]:
        room_id_set = set(room_ids)

        async with self._lock:
            connected_by_room: dict[str, set[str]] = {
                room_id: set()
                for room_id in room_ids
            }

            for connection in self._connections.values():
                for room_id in connection.room_ids:
                    if room_id in room_id_set:
                        connected_by_room.setdefault(room_id, set()).add(connection.user_id)

            return connected_by_room

    async def send_to_users(
        self,
        *,
        user_ids: list[str],
        room_id: str | None,
        event: TransportEvent,
        payload: dict[str, Any],
        event_seq: int | None = None,
    ) -> None:
        if not user_ids:
            return

        async with self._lock:
            connections = [
                self._connections[connection_id]
                for user_id in user_ids
                for connection_id in self._connections_by_user.get(user_id, set())
                if connection_id in self._connections
            ]

        if not connections:
            return

        now = int(time.time())
        stale_connection_ids = []

        for connection in connections:
            try:
                extra = {
                    "target_user_id": connection.user_id,
                    "created_at": now,
                }
                if event_seq is not None:
                    extra["event_seq"] = event_seq

                envelope = event_envelope(
                    event=event.value,
                    room_id=room_id,
                    payload=payload,
                    ts=now,
                    extra=extra,
                )
                await connection.websocket.send_json(
                    envelope
                )
            except Exception:
                stale_connection_ids.append(connection.id)

        for connection_id in stale_connection_ids:
            await self.disconnect(connection_id)


websocket_manager = WebSocketConnectionManager()


class RealtimeTransport(RealtimeGatewayContract):
    def __init__(
        self,
        *,
        manager: WebSocketConnectionManager = websocket_manager,
        recipients: RealtimeRecipientRepository | None = None,
        event_log: RoomEventLog | None = None,
    ) -> None:
        self.manager = manager
        self.recipients = recipients or RealtimeRecipientRepository()
        self.event_log = event_log or RoomEventLog()

    async def _deliver(
        self,
        *,
        user_ids: list[str],
        room_id: str | None,
        event: TransportEvent,
        payload: Payload,
    ) -> None:
        event_seq = None
        if room_id is not None:
            event_seq = await run_blocking(self.event_log.append, room_id=room_id, event=event, payload=payload)

        unique_user_ids = list(dict.fromkeys(user_ids))

        if not unique_user_ids:
            return

        connected_user_ids = await self.manager.connected_user_ids(unique_user_ids)
        connected = [
            user_id
            for user_id in unique_user_ids
            if user_id in connected_user_ids
        ]

        await self.manager.send_to_users(
            user_ids=connected,
            room_id=room_id,
            event=event,
            payload=payload,
            event_seq=event_seq,
        )

    async def to_player(
        self,
        player_id: PlayerId,
        event: TransportEvent,
        payload: Payload,
    ) -> None:
        await self._deliver(user_ids=[player_id], room_id=None, event=event, payload=payload)

    async def to_players(
        self,
        player_ids: list[PlayerId],
        event: TransportEvent,
        payload: Payload,
    ) -> None:
        await self._deliver(user_ids=player_ids, room_id=None, event=event, payload=payload)

    async def to_room(
        self,
        room_id: RoomId,
        event: TransportEvent,
        payload: Payload,
    ) -> None:
        user_ids = await run_blocking(self.recipients.list_room_member_user_ids, room_id)
        await self._deliver(user_ids=user_ids, room_id=room_id, event=event, payload=payload)

    async def to_room_except(
        self,
        room_id: RoomId,
        excluded_player_ids: list[PlayerId],
        event: TransportEvent,
        payload: Payload,
    ) -> None:
        user_ids = await run_blocking(
            self.recipients.list_room_member_user_ids_except,
            room_id=room_id,
            excluded_player_ids=excluded_player_ids,
        )
        await self._deliver(user_ids=user_ids, room_id=room_id, event=event, payload=payload)

    async def to_role(
        self,
        room_id: RoomId,
        role: PlayerRole,
        event: TransportEvent,
        payload: Payload,
    ) -> None:
        user_ids = await run_blocking(self.recipients.list_role_member_user_ids, room_id=room_id, role=role)
        await self._deliver(user_ids=user_ids, room_id=room_id, event=event, payload=payload)

    async def to_gm(
        self,
        room_id: RoomId,
        event: TransportEvent,
        payload: Payload,
    ) -> None:
        user_ids = await run_blocking(self.recipients.list_gm_user_ids, room_id)
        await self._deliver(user_ids=user_ids, room_id=room_id, event=event, payload=payload)

    async def to_players_in_room(
        self,
        room_id: RoomId,
        event: TransportEvent,
        payload: Payload,
    ) -> None:
        user_ids = await run_blocking(self.recipients.list_players_in_room_user_ids, room_id)
        await self._deliver(user_ids=user_ids, room_id=room_id, event=event, payload=payload)

    async def to_streamers(
        self,
        room_id: RoomId,
        event: TransportEvent,
        payload: Payload,
    ) -> None:
        user_ids = await run_blocking(self.recipients.list_streamer_user_ids, room_id)
        await self._deliver(user_ids=user_ids, room_id=room_id, event=event, payload=payload)

    async def chat_to_room(
        self,
        room_id: RoomId,
        message: Payload,
    ) -> None:
        await self.to_room(
            room_id=room_id,
            event=TransportEvent.CHAT_MESSAGE_CREATED,
            payload={
                "visibility": ChatVisibility.PUBLIC,
                **message,
            },
        )

    async def chat_to_gm(
        self,
        room_id: RoomId,
        message: Payload,
    ) -> None:
        await self.to_gm(
            room_id=room_id,
            event=TransportEvent.CHAT_MESSAGE_CREATED,
            payload={
                "visibility": ChatVisibility.GM_ONLY,
                **message,
            },
        )

    async def chat_whisper(
        self,
        room_id: RoomId,
        sender_player_id: PlayerId,
        target_player_ids: list[PlayerId],
        message: Payload,
    ) -> None:
        recipients = list(dict.fromkeys([sender_player_id, *target_player_ids]))
        await self._deliver(
            user_ids=recipients,
            room_id=room_id,
            event=TransportEvent.CHAT_MESSAGE_CREATED,
            payload={
                "visibility": ChatVisibility.WHISPER,
                "sender_player_id": sender_player_id,
                "target_player_ids": target_player_ids,
                **message,
            },
        )

    async def chat_system(
        self,
        room_id: RoomId,
        message: Payload,
        target_player_ids: list[PlayerId] | None = None,
    ) -> None:
        payload = {
            "visibility": ChatVisibility.SYSTEM,
            "author": "system",
            **message,
        }

        if target_player_ids is None:
            await self.to_room(
                room_id=room_id,
                event=TransportEvent.CHAT_MESSAGE_CREATED,
                payload=payload,
            )
            return

        await self._deliver(
            user_ids=target_player_ids,
            room_id=room_id,
            event=TransportEvent.CHAT_MESSAGE_CREATED,
            payload=payload,
        )

    async def is_player_connected(
        self,
        player_id: PlayerId,
    ) -> bool:
        return await self.manager.is_user_connected(player_id)
