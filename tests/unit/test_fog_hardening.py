from __future__ import annotations

from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from app.domain.fog import FogCircleGeom
from app.domain.fog import FogInitialState
from app.domain.fog import FogMode
from app.domain.fog import FogOp
from app.domain.fog import FogShape
from app.engine.scenes import fog_service as fog_service_module
from app.engine.scenes.fog_service import FogService
from app.realtime.command_dispatcher import ClientCommandContext
from app.realtime.commands import ClientCommand
from app.realtime.fog_command_handler import FogCommandHandler
from app.realtime.fog_command_handler import _MAX_OPS_PER_COMMAND
from app.realtime.fog_command_handler import _MAX_POLYGON_POINTS
from tests.conftest import seed_campaign
from tests.conftest import seed_scene
from tests.conftest import seed_user


def _cmd(command: str, room_id: str, payload: dict) -> dict:
    return {
        "type": "command",
        "id": "fog-cmd",
        "command": command,
        "room_id": room_id,
        "payload": payload,
    }


def _transport():
    transport = MagicMock()
    transport.to_room = AsyncMock()
    return transport


def _circle_op() -> dict:
    return {
        "mode": "reveal",
        "shape": "circle",
        "geom": {"center_x_cells": 1.0, "center_y_cells": 1.0, "radius_cells": 1.0},
    }


async def _enabled_scene():
    gm_id = seed_user(email="fog-hardening-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)
    FogService().enable(scene_id=scene["id"], user_id=gm_id, initial=FogInitialState.HIDE_ALL)
    return gm_id, campaign_id, scene


async def test_paint_requires_expected_version(db):
    gm_id, campaign_id, scene = await _enabled_scene()

    result = await FogCommandHandler().handle(
        _cmd(
            ClientCommand.FOG_PAINT.value,
            campaign_id,
            {"scene_id": scene["id"], "ops": [_circle_op()]},                       
        ),
        context=ClientCommandContext(user_id=gm_id, room_ids=(campaign_id,)),
        transport=_transport(),
    )

    assert result.response["type"] == "error"
    assert result.response["code"] == "invalid_payload"


async def test_paint_rejects_too_many_ops(db):
    gm_id, campaign_id, scene = await _enabled_scene()

    result = await FogCommandHandler().handle(
        _cmd(
            ClientCommand.FOG_PAINT.value,
            campaign_id,
            {
                "scene_id": scene["id"],
                "expected_version": 1,
                "ops": [_circle_op()] * (_MAX_OPS_PER_COMMAND + 1),
            },
        ),
        context=ClientCommandContext(user_id=gm_id, room_ids=(campaign_id,)),
        transport=_transport(),
    )

    assert result.response["type"] == "error"
    assert result.response["code"] == "invalid_payload"


async def test_paint_rejects_oversized_polygon(db):
    gm_id, campaign_id, scene = await _enabled_scene()
    polygon = {
        "mode": "reveal",
        "shape": "polygon",
        "geom": {"points_cells": [[float(i), 0.0] for i in range(_MAX_POLYGON_POINTS + 1)]},
    }

    result = await FogCommandHandler().handle(
        _cmd(
            ClientCommand.FOG_PAINT.value,
            campaign_id,
            {"scene_id": scene["id"], "expected_version": 1, "ops": [polygon]},
        ),
        context=ClientCommandContext(user_id=gm_id, room_ids=(campaign_id,)),
        transport=_transport(),
    )

    assert result.response["type"] == "error"
    assert result.response["code"] == "invalid_payload"


def test_service_caps_total_ops(db, monkeypatch):
    gm_id = seed_user(email="fog-cap-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)
    service = FogService()
    service.enable(scene_id=scene["id"], user_id=gm_id, initial=FogInitialState.HIDE_ALL)

                                                                  
    monkeypatch.setattr(fog_service_module, "MAX_FOG_TOTAL_OPS", 1)

    ops = [
        FogOp(FogMode.REVEAL, FogShape.CIRCLE, FogCircleGeom(1.0, 1.0, 1.0)),
        FogOp(FogMode.REVEAL, FogShape.CIRCLE, FogCircleGeom(2.0, 2.0, 1.0)),
    ]
    result = service.paint(scene_id=scene["id"], user_id=gm_id, ops=ops, expected_version=1)

    assert not result.success
    assert result.error_key == "game.fog.errors.too_many_ops"
