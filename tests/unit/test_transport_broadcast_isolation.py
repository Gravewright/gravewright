"""STABILIZATION_V1 P1.5: a dead socket must not sink the whole broadcast.

``WebSocketConnectionManager.send_to_users`` isolates failure per connection:
a ``send_json`` that raises (client dropped without a clean disconnect) is
caught, the offending connection is reaped, and every other recipient still
gets the event.
"""

from __future__ import annotations

import asyncio
import time

import pytest

import app.realtime.transport as transport_module
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport, WebSocketConnectionManager


class _ClosableSocket:
    def __init__(self):
        self.closed = []

    async def close(self, *, code, reason):
        self.closed.append((code, reason))


async def test_evict_user_closes_only_connections_attached_to_banned_room():
    manager = WebSocketConnectionManager()
    banned_socket = _ClosableSocket()
    other_room_socket = _ClosableSocket()
    other_user_socket = _ClosableSocket()
    await manager.connect(user_id="player", room_ids=["banned-room"], websocket=banned_socket)
    await manager.connect(user_id="player", room_ids=["other-room"], websocket=other_room_socket)
    await manager.connect(user_id="other", room_ids=["banned-room"], websocket=other_user_socket)

    closed = await manager.evict_user_from_room(user_id="player", room_id="banned-room")

    assert closed == 1
    assert banned_socket.closed == [(4003, "Campaign membership revoked.")]
    assert other_room_socket.closed == []
    assert other_user_socket.closed == []


class _OkSocket:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def send_json(self, message: dict) -> None:
        self.messages.append(message)


class _DeadSocket:
    async def send_json(self, message: dict) -> None:
        raise ConnectionError("socket is gone")


@pytest.mark.asyncio
async def test_send_to_users_isolates_a_dead_socket():
    manager = WebSocketConnectionManager()
    ok = _OkSocket()
    dead = _DeadSocket()

    await manager.connect(user_id="alive", room_ids=["room-1"], websocket=ok)
    dead_conn_id = await manager.connect(user_id="dead", room_ids=["room-1"], websocket=dead)

    await manager.send_to_users(
        user_ids=["dead", "alive"],
        room_id="room-1",
        event=TransportEvent.SCENE_UPDATED,
        payload={"room_id": "room-1", "scene_id": "scene-1"},
    )

    assert len(ok.messages) == 1
    assert ok.messages[0]["event"] == TransportEvent.SCENE_UPDATED.value

    assert await manager.is_user_connected("dead") is False
    assert await manager.disconnect(dead_conn_id) is None
    assert await manager.is_user_connected("alive") is True


class _SlowSocket:
    def __init__(self) -> None:
        self.messages: list[dict] = []
        self.closed: list[tuple[int, str]] = []

    async def send_json(self, message: dict) -> None:
        await asyncio.sleep(10)
        self.messages.append(message)

    async def close(self, *, code: int, reason: str) -> None:
        self.closed.append((code, reason))


@pytest.mark.asyncio
async def test_send_to_users_does_not_block_on_a_slow_socket(monkeypatch):
    monkeypatch.setattr(transport_module, "WEBSOCKET_SEND_TIMEOUT_SECONDS", 0.05)
    manager = WebSocketConnectionManager()
    ok = _OkSocket()
    slow = _SlowSocket()

    await manager.connect(user_id="fast", room_ids=["room-1"], websocket=ok)
    await manager.connect(user_id="slow", room_ids=["room-1"], websocket=slow)

    started = time.monotonic()
    await manager.send_to_users(
        user_ids=["slow", "fast"],
        room_id="room-1",
        event=TransportEvent.SCENE_UPDATED,
        payload={"room_id": "room-1", "scene_id": "scene-1"},
    )
    elapsed = time.monotonic() - started

    assert elapsed < 1.0
    assert len(ok.messages) == 1
    assert await manager.is_user_connected("slow") is False
    assert slow.closed and slow.closed[0][0] == 1011


@pytest.mark.asyncio
async def test_targeted_campaign_event_keeps_room_scope_from_payload():
    manager = WebSocketConnectionManager()
    socket = _OkSocket()
    await manager.connect(user_id="player", room_ids=["room-1"], websocket=socket)

    await RealtimeTransport(manager=manager).to_players(
        player_ids=["player"],
        event=TransportEvent.ITEM_CREATED,
        payload={"room_id": "room-1", "item_id": "item-1"},
    )

    assert len(socket.messages) == 1
    assert socket.messages[0]["room_id"] == "room-1"
    assert socket.messages[0]["payload"]["item_id"] == "item-1"
