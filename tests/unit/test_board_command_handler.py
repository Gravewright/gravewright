from __future__ import annotations

from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock

from app.realtime.board_command_handler import BoardCommandHandler
from app.realtime.command_dispatcher import ClientCommandContext
from app.realtime.commands import ClientCommand
from app.realtime.events import TransportEvent


def ctx() -> ClientCommandContext:
    return ClientCommandContext(user_id="user-1", room_ids=("room-1",))


def cmd(
    payload: dict,
    room_id: str = "room-1",
    command: str = ClientCommand.BOARD_PING.value,
) -> dict:
    return {
        "type": "command",
        "id": "cmd-1",
        "command": command,
        "room_id": room_id,
        "payload": payload,
    }


def mock_transport():
    transport = MagicMock()
    transport.to_room = AsyncMock()
    transport.to_gm = AsyncMock()
    transport.to_players_in_room = AsyncMock()
    return transport


class FakeCampaignRepository:
    def __init__(self, role: str | None = None) -> None:
        self.role = role

    def get_member_role(self, *, campaign_id: str, user_id: str):
        return self.role


class FakePermissionService:
    def __init__(self, allow: bool = True) -> None:
        self.allow = allow

    def can(self, *, user_id: str, campaign_id: str, permission) -> bool:
        return self.allow


class FakeSceneRepository:
    def __init__(self, *, campaign_id: str = "room-1", markers: list | None = None) -> None:
        self.scene = {"id": "scene-1", "campaign_id": campaign_id}
        self.markers = markers or []
        self.upserted = []
        self.deleted = []
        self.cleared = []

    def get_by_id(self, scene_id: str):
        if scene_id == self.scene["id"]:
            return self.scene
        return None

    def list_board_area_markers(self, scene_id: str):
        return self.markers

    def upsert_board_area_marker(self, *, scene_id: str, marker: dict):
        self.upserted.append((scene_id, marker))
        return [marker]

    def delete_board_area_marker(self, *, scene_id: str, marker_id: str):
        self.deleted.append((scene_id, marker_id))
        return []

    def clear_board_area_markers(self, scene_id: str, *, keep_gm_layer: bool = False):
        self.cleared.append((scene_id, keep_gm_layer))
        return True

    def clear_board_drawings(self, scene_id: str, *, owner_id: str | None = None):
        self.cleared.append(("draw", scene_id, owner_id))
        return []


def board_handler(scenes: FakeSceneRepository, *, role: str | None = None) -> BoardCommandHandler:
    return BoardCommandHandler(
        scenes=scenes,
        campaigns=FakeCampaignRepository(role),
        permissions=FakePermissionService(),
    )


async def test_non_board_command_not_handled():
    result = await BoardCommandHandler().handle(
        {"type": "command", "id": "cmd-1", "command": "token.move", "room_id": "room-1"},
        context=ctx(),
    )

    assert not result.handled


async def test_board_ping_rejects_room_outside_context():
    result = await BoardCommandHandler().handle(
        cmd({"scene_id": "scene-1", "world_x": 1, "world_y": 2}, room_id="other-room"),
        context=ctx(),
    )

    assert result.handled
    assert result.response["type"] == "error"
    assert result.response["code"] == "permission_denied"


async def test_board_ping_rejects_invalid_variant():
    result = await BoardCommandHandler(permissions=FakePermissionService()).handle(
        cmd({"scene_id": "scene-1", "world_x": 1, "world_y": 2, "variant": "bad"}),
        context=ctx(),
    )

    assert result.handled
    assert result.response["type"] == "error"
    assert result.response["code"] == "invalid_payload"


async def test_board_command_denied_without_permission():
    transport = mock_transport()
    handler = BoardCommandHandler(
        scenes=FakeSceneRepository(),
        campaigns=FakeCampaignRepository("player"),
        permissions=FakePermissionService(allow=False),
    )

    result = await handler.handle(
        cmd({"scene_id": "scene-1", "world_x": 1, "world_y": 2}),
        context=ctx(),
        transport=transport,
    )

    assert result.handled
    assert result.response["type"] == "error"
    assert result.response["code"] == "permission_denied"
    transport.to_room.assert_not_awaited()


async def test_board_ping_broadcasts_to_room():
    transport = mock_transport()

    result = await BoardCommandHandler(permissions=FakePermissionService()).handle(
        cmd({"scene_id": "scene-1", "world_x": 12.5, "world_y": 34, "variant": "focus"}),
        context=ctx(),
        transport=transport,
    )

    assert result.handled
    assert result.response["type"] == "event"
    assert result.response["event"] == "board.command.ack"
    transport.to_room.assert_awaited_once_with(
        room_id="room-1",
        event=TransportEvent.BOARD_PING,
        payload={
            "room_id": "room-1",
            "scene_id": "scene-1",
            "world_x": 12.5,
            "world_y": 34.0,
            "variant": "focus",
            "user_id": "user-1",
        },
    )


async def test_board_area_marker_upsert_broadcasts_to_room():
    transport = mock_transport()
    scenes = FakeSceneRepository()

    result = await board_handler(scenes).handle(
        cmd(
            {
                "marker": {
                    "id": "marker-1",
                    "scene_id": "scene-1",
                    "shape": "line",
                    "preset_id": "dnd5e-spell-line",
                    "style": {
                        "stroke": "rgba(96, 165, 250, 0.96)",
                        "fill": "rgba(96, 165, 250, 0.16)",
                        "strokeWidth": 3,
                    },
                    "text": "Zona perigosa",
                    "start": {"worldX": 10, "worldY": 20},
                    "end": {"worldX": 30.5, "worldY": 40},
                },
            },
            command=ClientCommand.BOARD_AREA_MARKER_UPSERT.value,
        ),
        context=ctx(),
        transport=transport,
    )

    assert result.handled
    assert result.response["type"] == "event"
    assert result.response["payload"]["command"] == ClientCommand.BOARD_AREA_MARKER_UPSERT.value
    assert scenes.upserted == [
        (
            "scene-1",
            {
                "id": "marker-1",
                "scene_id": "scene-1",
                "shape": "line",
                "preset_id": "dnd5e-spell-line",
                "style": {
                    "stroke": "rgba(96, 165, 250, 0.96)",
                    "fill": "rgba(96, 165, 250, 0.16)",
                    "strokeWidth": 3.0,
                },
                "text": "Zona perigosa",
                "start": {"worldX": 10.0, "worldY": 20.0},
                "end": {"worldX": 30.5, "worldY": 40.0},
            },
        )
    ]
    transport.to_room.assert_awaited_once_with(
        room_id="room-1",
        event=TransportEvent.BOARD_AREA_MARKER_UPSERTED,
        payload={
            "room_id": "room-1",
            "scene_id": "scene-1",
            "marker": {
                "id": "marker-1",
                "scene_id": "scene-1",
                "shape": "line",
                "preset_id": "dnd5e-spell-line",
                "style": {
                    "stroke": "rgba(96, 165, 250, 0.96)",
                    "fill": "rgba(96, 165, 250, 0.16)",
                    "strokeWidth": 3.0,
                },
                "text": "Zona perigosa",
                "start": {"worldX": 10.0, "worldY": 20.0},
                "end": {"worldX": 30.5, "worldY": 40.0},
            },
            "user_id": "user-1",
        },
    )


async def test_board_area_marker_upsert_rejects_invalid_shape():
    result = await board_handler(FakeSceneRepository()).handle(
        cmd(
            {
                "marker": {
                    "id": "marker-1",
                    "scene_id": "scene-1",
                    "shape": "bad",
                    "start": {"worldX": 10, "worldY": 20},
                    "end": {"worldX": 30, "worldY": 40},
                },
            },
            command=ClientCommand.BOARD_AREA_MARKER_UPSERT.value,
        ),
        context=ctx(),
    )

    assert result.handled
    assert result.response["type"] == "error"
    assert result.response["code"] == "invalid_payload"


async def test_board_area_marker_upsert_rejects_when_scene_marker_limit_reached(monkeypatch):
    import app.realtime.board_command_handler as board_commands

    monkeypatch.setattr(
        board_commands,
        "config",
        replace(board_commands.config, board_markers_max_per_scene=1),
    )
    scenes = FakeSceneRepository(
        markers=[
            {
                "id": "marker-existing",
                "scene_id": "scene-1",
                "shape": "line",
            }
        ]
    )

    result = await board_handler(scenes).handle(
        cmd(
            {
                "marker": {
                    "id": "marker-new",
                    "scene_id": "scene-1",
                    "shape": "line",
                    "start": {"worldX": 10, "worldY": 20},
                    "end": {"worldX": 30, "worldY": 40},
                },
            },
            command=ClientCommand.BOARD_AREA_MARKER_UPSERT.value,
        ),
        context=ctx(),
    )

    assert result.handled
    assert result.response["type"] == "error"
    assert result.response["code"] == "limit_reached"
    assert scenes.upserted == []


async def test_board_area_marker_delete_broadcasts_to_room():
    transport = mock_transport()
    scenes = FakeSceneRepository()

    result = await board_handler(scenes).handle(
        cmd(
            {"scene_id": "scene-1", "marker_id": "marker-1"},
            command=ClientCommand.BOARD_AREA_MARKER_DELETE.value,
        ),
        context=ctx(),
        transport=transport,
    )

    assert result.handled
    assert scenes.deleted == [("scene-1", "marker-1")]
    transport.to_room.assert_awaited_once_with(
        room_id="room-1",
        event=TransportEvent.BOARD_AREA_MARKER_DELETED,
        payload={
            "room_id": "room-1",
            "scene_id": "scene-1",
            "marker_id": "marker-1",
            "user_id": "user-1",
        },
    )


async def test_board_area_marker_clear_broadcasts_to_room():
    transport = mock_transport()
    scenes = FakeSceneRepository()

    result = await board_handler(scenes).handle(
        cmd(
            {"scene_id": "scene-1"},
            command=ClientCommand.BOARD_AREA_MARKER_CLEAR.value,
        ),
        context=ctx(),
        transport=transport,
    )

    assert result.handled
                                            
    assert scenes.cleared == [("scene-1", True)]
    transport.to_room.assert_awaited_once_with(
        room_id="room-1",
        event=TransportEvent.BOARD_AREA_MARKER_CLEARED,
        payload={
            "room_id": "room-1",
            "scene_id": "scene-1",
            "user_id": "user-1",
            "keep_gm_layer": True,
        },
    )


async def test_board_measure_flash_broadcasts_without_persistence():
    transport = mock_transport()
    scenes = FakeSceneRepository()

    result = await board_handler(scenes).handle(
        cmd(
            {
                "measure": {
                    "id": "measure-1",
                    "scene_id": "scene-1",
                    "shape": "circle",
                    "start": {"worldX": 10, "worldY": 20},
                    "end": {"worldX": 30, "worldY": 20},
                },
                "ttl_ms": 2500,
            },
            command=ClientCommand.BOARD_MEASURE_FLASH.value,
        ),
        context=ctx(),
        transport=transport,
    )

    assert result.handled
    assert scenes.upserted == []
    transport.to_room.assert_awaited_once_with(
        room_id="room-1",
        event=TransportEvent.BOARD_MEASURE_FLASHED,
        payload={
            "room_id": "room-1",
            "scene_id": "scene-1",
            "measure": {
                "id": "measure-1",
                "scene_id": "scene-1",
                "shape": "circle",
                "start": {"worldX": 10.0, "worldY": 20.0},
                "end": {"worldX": 30.0, "worldY": 20.0},
            },
            "ttl_ms": 2500,
            "user_id": "user-1",
        },
    )


async def test_board_measure_clear_broadcasts_without_persistence():
    transport = mock_transport()
    scenes = FakeSceneRepository()

    result = await board_handler(scenes).handle(
        cmd(
            {"scene_id": "scene-1"},
            command=ClientCommand.BOARD_MEASURE_CLEAR.value,
        ),
        context=ctx(),
        transport=transport,
    )

    assert result.handled
    assert scenes.cleared == []
    transport.to_room.assert_awaited_once_with(
        room_id="room-1",
        event=TransportEvent.BOARD_MEASURE_CLEARED,
        payload={
            "room_id": "room-1",
            "scene_id": "scene-1",
            "user_id": "user-1",
        },
    )


async def test_board_measure_delete_broadcasts_without_persistence():
    transport = mock_transport()
    scenes = FakeSceneRepository()

    result = await board_handler(scenes).handle(
        cmd(
            {"scene_id": "scene-1", "measure_id": "measure-1"},
            command=ClientCommand.BOARD_MEASURE_DELETE.value,
        ),
        context=ctx(),
        transport=transport,
    )

    assert result.handled
    assert scenes.cleared == []
    transport.to_room.assert_awaited_once_with(
        room_id="room-1",
        event=TransportEvent.BOARD_MEASURE_DELETED,
        payload={
            "room_id": "room-1",
            "scene_id": "scene-1",
            "measure_id": "measure-1",
            "user_id": "user-1",
        },
    )


async def test_board_draw_upsert_broadcasts_to_room():
    transport = mock_transport()
    scenes = FakeSceneRepository()

    result = await board_handler(scenes).handle(
        cmd(
            {
                "drawing": {
                    "id": "draw-1",
                    "scene_id": "scene-1",
                    "kind": "freehand",
                    "points": [
                        {"worldX": 10, "worldY": 20},
                        {"worldX": 12.5, "worldY": 24},
                    ],
                    "style": {"stroke": "#facc15", "fill": "none", "strokeWidth": 4},
                },
            },
            command=ClientCommand.BOARD_DRAW_UPSERT.value,
        ),
        context=ctx(),
        transport=transport,
    )

    assert result.handled
    assert scenes.upserted == [
        (
            "scene-1",
            {
                "id": "draw-1",
                "scene_id": "scene-1",
                "kind": "freehand",
                "points": [
                    {"worldX": 10.0, "worldY": 20.0},
                    {"worldX": 12.5, "worldY": 24.0},
                ],
                "style": {"stroke": "#facc15", "fill": "none", "strokeWidth": 4.0},
                "owner_id": "user-1",
            },
        )
    ]
    transport.to_room.assert_awaited_once_with(
        room_id="room-1",
        event=TransportEvent.BOARD_DRAW_UPSERTED,
        payload={
            "room_id": "room-1",
            "scene_id": "scene-1",
            "drawing": {
                "id": "draw-1",
                "scene_id": "scene-1",
                "kind": "freehand",
                "points": [
                    {"worldX": 10.0, "worldY": 20.0},
                    {"worldX": 12.5, "worldY": 24.0},
                ],
                "style": {"stroke": "#facc15", "fill": "none", "strokeWidth": 4.0},
                "owner_id": "user-1",
            },
            "user_id": "user-1",
        },
    )


async def test_board_draw_upsert_persists_text_drawing():
    transport = mock_transport()
    scenes = FakeSceneRepository()

    result = await board_handler(scenes).handle(
        cmd(
            {
                "drawing": {
                    "id": "text-1",
                    "scene_id": "scene-1",
                    "kind": "text",
                    "position": {"worldX": 30, "worldY": 40},
                    "text": "  Trap ahead  ",
                    "fontSize": 36,
                    "style": {"fill": "#facc15"},
                },
            },
            command=ClientCommand.BOARD_DRAW_UPSERT.value,
        ),
        context=ctx(),
        transport=transport,
    )

    assert result.handled
    assert scenes.upserted == [
        (
            "scene-1",
            {
                "id": "text-1",
                "scene_id": "scene-1",
                "kind": "text",
                "position": {"worldX": 30.0, "worldY": 40.0},
                "text": "Trap ahead",
                "fontSize": 36.0,
                "style": {"fill": "#facc15"},
                "owner_id": "user-1",
            },
        )
    ]
    transport.to_room.assert_awaited_once_with(
        room_id="room-1",
        event=TransportEvent.BOARD_DRAW_UPSERTED,
        payload={
            "room_id": "room-1",
            "scene_id": "scene-1",
            "drawing": {
                "id": "text-1",
                "scene_id": "scene-1",
                "kind": "text",
                "position": {"worldX": 30.0, "worldY": 40.0},
                "text": "Trap ahead",
                "fontSize": 36.0,
                "style": {"fill": "#facc15"},
                "owner_id": "user-1",
            },
            "user_id": "user-1",
        },
    )


async def test_board_draw_upsert_rejects_text_without_content():
    scenes = FakeSceneRepository()

    result = await board_handler(scenes).handle(
        cmd(
            {
                "drawing": {
                    "id": "text-1",
                    "scene_id": "scene-1",
                    "kind": "text",
                    "position": {"worldX": 30, "worldY": 40},
                    "text": "   ",
                },
            },
            command=ClientCommand.BOARD_DRAW_UPSERT.value,
        ),
        context=ctx(),
        transport=mock_transport(),
    )

    assert result.handled
    assert result.response["type"] == "error"
    assert result.response["code"] == "invalid_payload"
    assert scenes.upserted == []


async def test_board_draw_upsert_rejects_when_user_drawing_limit_reached(monkeypatch):
    import app.realtime.board_command_handler as board_commands

    monkeypatch.setattr(
        board_commands,
        "config",
        replace(board_commands.config, board_measurements_max_per_user=1),
    )
    scenes = FakeSceneRepository(markers=[_draw()])

    result = await board_handler(scenes).handle(
        cmd(
            {
                "drawing": {
                    "id": "draw-2",
                    "scene_id": "scene-1",
                    "kind": "freehand",
                    "points": [
                        {"worldX": 10, "worldY": 20},
                        {"worldX": 12.5, "worldY": 24},
                    ],
                },
            },
            command=ClientCommand.BOARD_DRAW_UPSERT.value,
        ),
        context=ctx(),
    )

    assert result.handled
    assert result.response["type"] == "error"
    assert result.response["code"] == "limit_reached"
    assert scenes.upserted == []


async def test_board_draw_clear_broadcasts_to_room():
    transport = mock_transport()
    scenes = FakeSceneRepository()

    result = await board_handler(scenes).handle(
        cmd(
            {"scene_id": "scene-1"},
            command=ClientCommand.BOARD_DRAW_CLEAR.value,
        ),
        context=ctx(),
        transport=transport,
    )

    assert result.handled
                                              
    assert scenes.cleared == [("draw", "scene-1", "user-1")]
    transport.to_room.assert_awaited_once_with(
        room_id="room-1",
        event=TransportEvent.BOARD_DRAW_CLEARED,
        payload={
            "room_id": "room-1",
            "scene_id": "scene-1",
            "user_id": "user-1",
            "owner_id": "user-1",
        },
    )


async def test_board_draw_clear_gm_clears_everything():
    transport = mock_transport()
    scenes = FakeSceneRepository()

    result = await board_handler(scenes, role="gm").handle(
        cmd({"scene_id": "scene-1"}, command=ClientCommand.BOARD_DRAW_CLEAR.value),
        context=ctx(),
        transport=transport,
    )

    assert result.handled
    assert scenes.cleared == [("draw", "scene-1", None)]


def _draw(layer: str | None = None, owner: str = "user-1") -> dict:
    drawing = {
        "id": "draw-1",
        "scene_id": "scene-1",
        "kind": "freehand",
        "points": [{"worldX": 1, "worldY": 2}, {"worldX": 3, "worldY": 4}],
        "owner_id": owner,
    }
    if layer:
        drawing["layer"] = layer
    return drawing


async def test_board_draw_upsert_gm_layer_routes_to_gm_only():
    transport = mock_transport()
    scenes = FakeSceneRepository()

    result = await board_handler(scenes, role="gm").handle(
        cmd({"drawing": _draw(layer="gm")}, command=ClientCommand.BOARD_DRAW_UPSERT.value),
        context=ctx(),
        transport=transport,
    )

    assert result.handled
    assert scenes.upserted[0][1]["layer"] == "gm"
    transport.to_gm.assert_awaited_once()
    transport.to_players_in_room.assert_awaited_once()
    transport.to_room.assert_not_awaited()


async def test_board_draw_upsert_non_gm_cannot_use_gm_layer():
    transport = mock_transport()
    scenes = FakeSceneRepository()

    result = await board_handler(scenes).handle(
        cmd({"drawing": _draw(layer="gm")}, command=ClientCommand.BOARD_DRAW_UPSERT.value),
        context=ctx(),
        transport=transport,
    )

    assert result.handled
    assert "layer" not in scenes.upserted[0][1]
    transport.to_room.assert_awaited_once()


async def test_board_draw_upsert_rejects_non_owner_non_gm():
    scenes = FakeSceneRepository(markers=[_draw(owner="someone-else")])

    result = await board_handler(scenes).handle(
        cmd({"drawing": _draw(owner="user-1")}, command=ClientCommand.BOARD_DRAW_UPSERT.value),
        context=ctx(),
        transport=mock_transport(),
    )

    assert result.handled
    assert result.response["code"] == "permission_denied"
    assert scenes.upserted == []


async def test_board_draw_upsert_owner_can_move_and_owner_preserved():
    scenes = FakeSceneRepository(markers=[_draw(owner="user-1")])

    result = await board_handler(scenes).handle(
        cmd({"drawing": _draw(owner="ignored")}, command=ClientCommand.BOARD_DRAW_UPSERT.value),
        context=ctx(),
        transport=mock_transport(),
    )

    assert result.handled
    assert scenes.upserted[0][1]["owner_id"] == "user-1"


async def test_board_draw_upsert_gm_can_move_others_drawing():
    scenes = FakeSceneRepository(markers=[_draw(owner="someone-else")])

    result = await board_handler(scenes, role="gm").handle(
        cmd({"drawing": _draw(owner="user-1")}, command=ClientCommand.BOARD_DRAW_UPSERT.value),
        context=ctx(),
        transport=mock_transport(),
    )

    assert result.handled
                                                                
    assert scenes.upserted[0][1]["owner_id"] == "someone-else"


async def test_board_draw_delete_rejects_non_owner_non_gm():
    scenes = FakeSceneRepository(
        markers=[{"id": "draw-1", "scene_id": "scene-1", "kind": "text", "owner_id": "someone-else"}]
    )

    result = await board_handler(scenes).handle(
        cmd(
            {"scene_id": "scene-1", "marker_id": "draw-1"},
            command=ClientCommand.BOARD_AREA_MARKER_DELETE.value,
        ),
        context=ctx(),
        transport=mock_transport(),
    )

    assert result.handled
    assert result.response["code"] == "permission_denied"
    assert scenes.deleted == []


async def test_board_draw_delete_owner_allowed():
    scenes = FakeSceneRepository(
        markers=[{"id": "draw-1", "scene_id": "scene-1", "kind": "text", "owner_id": "user-1"}]
    )

    result = await board_handler(scenes).handle(
        cmd(
            {"scene_id": "scene-1", "marker_id": "draw-1"},
            command=ClientCommand.BOARD_AREA_MARKER_DELETE.value,
        ),
        context=ctx(),
        transport=mock_transport(),
    )

    assert result.handled
    assert scenes.deleted == [("scene-1", "draw-1")]
