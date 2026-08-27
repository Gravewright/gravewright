from __future__ import annotations

import pytest

from app.engine.tokens.token_service import TokenService
from app.realtime.events import TransportEvent


class _Transport:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def to_token_audience(self, **values) -> None:
        self.events.append(values)


@pytest.mark.asyncio
async def test_created_tokens_reach_players_immediately_but_hidden_tokens_do_not():
    transport = _Transport()

    await TokenService.__new__(TokenService)._emit_tokens_created(
        campaign_id="room-1",
        scene_id="scene-1",
        token_views=[
            {"token_id": "visible", "hidden": False},
            {"token_id": "hidden", "hidden": True},
        ],
        transport=transport,
    )

    assert transport.events == [
        {
            "room_id": "room-1",
            "event": TransportEvent.TOKENS_CREATED,
            "payload": {
                "room_id": "room-1",
                "scene_id": "scene-1",
                "tokens": [{"token_id": "visible", "hidden": False}],
            },
            "include_players": True,
        },
        {
            "room_id": "room-1",
            "event": TransportEvent.TOKENS_CREATED,
            "payload": {
                "room_id": "room-1",
                "scene_id": "scene-1",
                "tokens": [{"token_id": "hidden", "hidden": True}],
            },
            "include_players": False,
        },
    ]
