from __future__ import annotations

from typing import Any, Protocol

from app.domain.roles import PlayerRole
from app.realtime.events import TransportEvent


Payload = dict[str, Any]
PlayerId = str
RoomId = str


class RealtimeGatewayContract(Protocol):
    """
    Port used by engine and realtime services to deliver events to connected players.

    The engine does not know whether the implementation is WebSocket, SSE, or anything else.
    """

    async def to_player(
        self,
        player_id: PlayerId,
        event: TransportEvent,
        payload: Payload,
    ) -> None: ...

    async def to_players(
        self,
        player_ids: list[PlayerId],
        event: TransportEvent,
        payload: Payload,
    ) -> None: ...

    async def to_room(
        self,
        room_id: RoomId,
        event: TransportEvent,
        payload: Payload,
    ) -> None: ...

    async def to_room_except(
        self,
        room_id: RoomId,
        excluded_player_ids: list[PlayerId],
        event: TransportEvent,
        payload: Payload,
    ) -> None: ...

    async def to_role(
        self,
        room_id: RoomId,
        role: PlayerRole,
        event: TransportEvent,
        payload: Payload,
    ) -> None: ...

    async def to_gm(
        self,
        room_id: RoomId,
        event: TransportEvent,
        payload: Payload,
    ) -> None: ...

    async def to_players_in_room(
        self,
        room_id: RoomId,
        event: TransportEvent,
        payload: Payload,
    ) -> None: ...

    async def to_streamers(
        self,
        room_id: RoomId,
        event: TransportEvent,
        payload: Payload,
    ) -> None: ...

    async def to_token_audience(
        self,
        room_id: RoomId,
        event: TransportEvent,
        payload: Payload,
        *,
        include_players: bool,
    ) -> None: ...

    async def chat_to_room(
        self,
        room_id: RoomId,
        message: Payload,
    ) -> None: ...

    async def chat_to_gm(
        self,
        room_id: RoomId,
        message: Payload,
    ) -> None: ...

    async def chat_whisper(
        self,
        room_id: RoomId,
        sender_player_id: PlayerId,
        target_player_ids: list[PlayerId],
        message: Payload,
    ) -> None: ...

    async def chat_system(
        self,
        room_id: RoomId,
        message: Payload,
        target_player_ids: list[PlayerId] | None = None,
    ) -> None: ...

    async def is_player_connected(
        self,
        player_id: PlayerId,
    ) -> bool: ...
