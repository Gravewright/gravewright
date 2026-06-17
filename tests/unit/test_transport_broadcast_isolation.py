"""STABILIZATION_V1 P1.5 — a dead socket must not sink the whole broadcast.

``WebSocketConnectionManager.send_to_users`` isolates failure per connection:
a ``send_json`` that raises (client dropped without a clean disconnect) is
caught, the offending connection is reaped, and every other recipient still
gets the event.
"""

from __future__ import annotations

import pytest

from app.realtime.events import TransportEvent
from app.realtime.transport import WebSocketConnectionManager


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
    dead_conn_id = await manager.connect(
        user_id="dead", room_ids=["room-1"], websocket=dead
    )

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
