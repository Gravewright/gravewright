from pathlib import Path

import pytest
from litestar.testing import TestClient

from app.business.users.user_preference_service import DEFAULT_PING_COLOR, UserPreferenceService
from app.realtime.board_command_handler import BoardCommandHandler, _representation_shape_style
from app.realtime.command_dispatcher import ClientCommandContext
from app.realtime.events import TransportEvent
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_scene, seed_user


ROOT = Path(__file__).resolve().parents[2]


def test_identification_color_styles_markers_and_measurements_consistently():
    style = _representation_shape_style({"strokeDasharray": "4 2", "strokeWidth": 3}, "#22c55e")
    assert style == {
        "strokeDasharray": "4 2",
        "strokeWidth": 3,
        "stroke": "#22c55e",
        "fill": "rgba(34,197,94,0.18)",
    }


def test_ping_color_is_persisted_and_validated(db):
    user_id = seed_user(name="Player", email="ping-color@test.com")
    service = UserPreferenceService()

    assert service.get_ping_color(user_id) == DEFAULT_PING_COLOR
    assert service.set_ping_color(user_id=user_id, ping_color="#12A4ef").success
    assert service.get_ping_color(user_id) == "#12a4ef"
    assert not service.set_ping_color(user_id=user_id, ping_color="red").success
    assert service.get_ping_color(user_id) == "#12a4ef"


def test_ping_color_endpoint_updates_only_the_current_user(db):
    from main import app

    user_id = seed_user(name="Player", email="ping-endpoint@test.com")
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, user_id)
        response = client.post("/game/preferences/ping", data={"ping_color": "#22c55e"})

    assert response.status_code == 200
    assert response.json()["ping_color"] == "#22c55e"
    assert UserPreferenceService().get_ping_color(user_id) == "#22c55e"


def test_board_ping_is_rendered_only_by_pixi():
    controller = (ROOT / "static/js/map/board-ping/map-board-ping.js").read_text(encoding="utf-8")
    renderer = (ROOT / "static/js/board/pixi/pixi-board-renderer.js").read_text(encoding="utf-8")
    layers = (ROOT / "static/js/board/pixi/pixi-board-layers.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/game.css").read_text(encoding="utf-8")

    assert "boardRenderer.showPing" in controller
    assert "document.createElement" not in controller
    assert "_renderPings(board)" in renderer
    assert "new PIXI.Graphics()" in layers and "board.pingLayer" in layers
    assert ".board-ping" not in css and "@keyframes board-ping" not in css


def test_streamer_ping_stays_local_while_player_ping_uses_realtime():
    controller = (ROOT / "static/js/map/board-ping/map-board-ping.js").read_text(encoding="utf-8")

    local_guard = controller.index("if (streamerLocalMode())")
    realtime_send = controller.index('sendCommand(\n                "board.ping"')
    assert 'dataset?.streamerMode === "true"' in controller
    assert local_guard < realtime_send

    map_controller = (ROOT / "static/js/map/map-controller.js").read_text(encoding="utf-8")
    assert 'detail.event === "board.ping"' in map_controller
    assert "mapBoardPing.handle(detail.payload)" in map_controller


@pytest.mark.asyncio
async def test_player_ping_is_broadcast_to_the_room():
    class AllowedPermissions:
        def can(self, **_kwargs):
            return True

    class Preferences:
        def get_ping_color(self, _user_id):
            return "#22c55e"

    class Transport:
        calls = []

        async def to_room(self, **kwargs):
            self.calls.append(kwargs)

    transport = Transport()
    result = await BoardCommandHandler(
        permissions=AllowedPermissions(),
        preferences=Preferences(),
    ).handle(
        {
            "type": "command",
            "id": "player-ping",
            "command": "board.ping",
            "room_id": "room-1",
            "payload": {
                "scene_id": "scene-1",
                "world_x": 120,
                "world_y": 240,
                "variant": "ping",
            },
        },
        context=ClientCommandContext(user_id="player-1", room_ids=("room-1",)),
        transport=transport,
    )

    assert result.handled
    assert len(transport.calls) == 1
    assert transport.calls[0]["event"] == TransportEvent.BOARD_PING
    assert transport.calls[0]["payload"]["user_id"] == "player-1"
    assert transport.calls[0]["payload"]["color"] == "#22c55e"


def test_player_ping_reaches_gm_over_real_websockets(db):
    from main import app

    gm_id = seed_user(name="GM", email="ping-gm@test.com")
    player_id = seed_user(name="Player", email="ping-player@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, "player")
    scene = seed_scene(campaign_id)

    with (
        TestClient(app=app, session_config=TEST_SESSION_CONFIG) as gm_client,
        TestClient(app=app, session_config=TEST_SESSION_CONFIG) as player_client,
    ):
        login(gm_client, gm_id)
        login(player_client, player_id)
        with (
            gm_client.websocket_connect(
                "/game/ws", headers={"origin": "http://testserver.local"}
            ) as gm_ws,
            player_client.websocket_connect(
                "/game/ws", headers={"origin": "http://testserver.local"}
            ) as player_ws,
        ):
            player_ws.send_json({
                "type": "command",
                "id": "player-ping-ws",
                "command": "board.ping",
                "room_id": campaign_id,
                "payload": {
                    "scene_id": scene["id"],
                    "world_x": 120,
                    "world_y": 240,
                    "variant": "ping",
                },
            })

            received = [gm_ws.receive_json() for _ in range(4)]
            ping = next(
                (item for item in received if item.get("event") == "board.ping"),
                None,
            )
            assert ping is not None, [item.get("event") for item in received]
            assert ping["payload"]["user_id"] == player_id
            assert ping["payload"]["scene_id"] == scene["id"]
