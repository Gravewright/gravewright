from __future__ import annotations

from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from app.domain.fog import FogInitialState
from app.engine.scenes.fog_service import FogService
from app.engine.scenes.fog_service import FogServiceResult
from app.realtime.command_dispatcher import ClientCommandContext
from app.realtime.commands import ClientCommand
from app.realtime.fog_command_handler import FogCommandHandler
from tests.conftest import seed_campaign
from tests.conftest import seed_scene
from tests.conftest import seed_user


def cmd(command: str, room_id: str, payload: dict, cmd_id: str = "fog-cmd-1") -> dict:
    return {
        "type": "command",
        "id": cmd_id,
        "command": command,
        "room_id": room_id,
        "payload": payload,
    }


def mock_transport():
    transport = MagicMock()
    transport.to_room = AsyncMock()
    return transport


async def test_fog_command_rejects_scene_from_different_room_before_mutation(db):
    gm_id = seed_user(email="fog-cross-gm@test.com")
    campaign_a = seed_campaign(gm_id, title="Campaign A")
    campaign_b = seed_campaign(gm_id, title="Campaign B")
    scene_b = seed_scene(campaign_b)
    transport = mock_transport()

    result = await FogCommandHandler().handle(
        cmd(
            ClientCommand.FOG_ENABLE.value,
            campaign_a,
            {"scene_id": scene_b["id"], "initial": FogInitialState.HIDE_ALL.value},
        ),
        context=ClientCommandContext(user_id=gm_id, room_ids=(campaign_a, campaign_b)),
        transport=transport,
    )

    assert result.handled
    assert result.response["type"] == "error"
    assert result.response["code"] == "not_found"
    transport.to_room.assert_not_awaited()

    state = FogService().get_state(scene_b["id"])
    assert state.success
    assert state.enabled is False
    assert state.version == 0


async def test_fog_command_broadcasts_to_validated_room(db):
    gm_id = seed_user(email="fog-valid-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)
    transport = mock_transport()

    result = await FogCommandHandler().handle(
        cmd(
            ClientCommand.FOG_ENABLE.value,
            campaign_id,
            {"scene_id": scene["id"], "initial": FogInitialState.HIDE_ALL.value},
        ),
        context=ClientCommandContext(user_id=gm_id, room_ids=(campaign_id,)),
        transport=transport,
    )

    assert result.handled
    assert result.response["type"] == "event"
    transport.to_room.assert_awaited_once()
    call = transport.to_room.call_args.kwargs
    assert call["room_id"] == campaign_id
    assert call["payload"]["room_id"] == campaign_id
    assert call["payload"]["scene_id"] == scene["id"]


async def test_fog_finalize_defense_refuses_mismatched_service_result(db):
    gm_id = seed_user(email="fog-defense-gm@test.com")
    campaign_a = seed_campaign(gm_id, title="Campaign A")
    campaign_b = seed_campaign(gm_id, title="Campaign B")
    scene_a = seed_scene(campaign_a)
    transport = mock_transport()
    service = MagicMock()
    service.get_state.return_value = FogService().get_state(scene_a["id"])
    service.enable.return_value = FogServiceResult(
        success=True,
        scene_id=scene_a["id"],
        campaign_id=campaign_b,
        enabled=True,
        version=1,
        baseline=FogInitialState.HIDE_ALL.value,
        ops=[],
    )

    result = await FogCommandHandler(service=service).handle(
        cmd(
            ClientCommand.FOG_ENABLE.value,
            campaign_a,
            {"scene_id": scene_a["id"], "initial": FogInitialState.HIDE_ALL.value},
        ),
        context=ClientCommandContext(user_id=gm_id, room_ids=(campaign_a,)),
        transport=transport,
    )

    assert result.handled
    assert result.response["type"] == "error"
    assert result.response["code"] == "not_found"
    transport.to_room.assert_not_awaited()
