from __future__ import annotations

import pytest

from app.realtime.command_dispatcher import ClientCommandContext
from app.realtime.command_dispatcher import CommandDispatcher


def context() -> ClientCommandContext:
    return ClientCommandContext(
        user_id="user-1",
        room_ids=("room-1",),
    )


@pytest.mark.asyncio
async def test_dispatcher_handles_legacy_ping():
    response = await CommandDispatcher().dispatch(
        {"type": "ping"},
        context=context(),
    )

    assert response["type"] == "event"
    assert response["event"] == "pong"


@pytest.mark.asyncio
async def test_dispatcher_handles_command_ping():
    response = await CommandDispatcher().dispatch(
        {
            "type": "command",
            "id": "cmd-1",
            "command": "ping",
            "room_id": "room-1",
            "payload": {},
        },
        context=context(),
    )

    assert response["type"] == "event"
    assert response["event"] == "pong"
    assert response["room_id"] == "room-1"


@pytest.mark.asyncio
async def test_dispatcher_rejects_unknown_command():
    response = await CommandDispatcher().dispatch(
        {
            "type": "command",
            "id": "cmd-1",
            "command": "scene.paint_everything",
            "room_id": "room-1",
            "payload": {},
        },
        context=context(),
    )

    assert response == {
        "type": "error",
        "command_id": "cmd-1",
        "code": "unknown_command",
        "message": "Unknown command.",
    }


@pytest.mark.asyncio
async def test_dispatcher_rejects_invalid_payload():
    response = await CommandDispatcher().dispatch(
        {
            "type": "command",
            "id": "cmd-1",
            "command": "ping",
            "payload": [],
        },
        context=context(),
    )

    assert response["type"] == "error"
    assert response["command_id"] == "cmd-1"
    assert response["code"] == "invalid_payload"


@pytest.mark.asyncio
async def test_dispatcher_rejects_room_outside_user_context():
    response = await CommandDispatcher().dispatch(
        {
            "type": "command",
            "id": "cmd-1",
            "command": "ping",
            "room_id": "other-room",
            "payload": {},
        },
        context=context(),
    )

    assert response == {
        "type": "error",
        "command_id": "cmd-1",
        "code": "permission_denied",
        "message": "You cannot perform this action.",
    }
