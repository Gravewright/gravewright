from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from app.domain.roles import PlayerRole
from app.domain.tokens import TokenConditionKind
from app.persistence.repositories.token_repository import TokenRepository
from app.realtime.command_dispatcher import ClientCommandContext
from app.realtime.commands import ClientCommand
from app.realtime.events import TransportEvent
from app.realtime.token_command_handler import TokenCommandHandler
from tests.conftest import seed_actor, seed_campaign, seed_member, seed_scene, seed_system, seed_user


                                                                             
         
                                                                             

def ctx(campaign_id: str, user_id: str) -> ClientCommandContext:
    return ClientCommandContext(user_id=user_id, room_ids=(campaign_id,))


def cmd(command: str, room_id: str, payload: dict, cmd_id: str = "cmd-1") -> dict:
    return {
        "type": "command",
        "id": cmd_id,
        "command": command,
        "room_id": room_id,
        "payload": payload,
    }


def mock_transport():
    t = MagicMock()
    t.to_room = AsyncMock()
    t.to_gm = AsyncMock()
    t.to_player = AsyncMock()
    t.to_players_in_room = AsyncMock()
    return t


def make_stack(db):
    gm_id = seed_user(email="ch-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)
    seed_system(campaign_id, gm_id)
    actor_id = seed_actor(campaign_id, gm_id, name="Monstro Modelo")
    return gm_id, campaign_id, scene, actor_id


                                                                             
              
                                                                             

async def test_non_token_command_not_handled():
    result = await TokenCommandHandler().handle(
        {"type": "command", "id": "x", "command": "chat.message.create", "room_id": "r1", "payload": {}},
        context=ClientCommandContext(user_id="u1", room_ids=("r1",)),
    )
    assert not result.handled


async def test_non_dict_message_not_handled():
    result = await TokenCommandHandler().handle(
        "not-a-dict",
        context=ClientCommandContext(user_id="u1", room_ids=("r1",)),
    )
    assert not result.handled


                                                                             
                    
                                                                             

async def test_missing_room_id_returns_error():
    result = await TokenCommandHandler().handle(
        {
            "type": "command",
            "id": "x",
            "command": ClientCommand.TOKEN_MOVE.value,
            "payload": {},
        },
        context=ClientCommandContext(user_id="u1", room_ids=("r1",)),
    )
    assert result.handled
    assert result.response["type"] == "error"
    assert result.response["code"] == "invalid_payload"


async def test_room_not_in_context_returns_permission_error():
    result = await TokenCommandHandler().handle(
        cmd(ClientCommand.TOKEN_MOVE.value, "other-room", {}),
        context=ClientCommandContext(user_id="u1", room_ids=("r1",)),
    )
    assert result.handled
    assert result.response["type"] == "error"
    assert result.response["code"] == "permission_denied"


                                                                             
                            
                                                                             

async def test_create_many_missing_scene_id():
    result = await TokenCommandHandler().handle(
        cmd(ClientCommand.TOKEN_CREATE_MANY_FROM_ACTORS.value, "r1", {"actor_ids": ["s1"], "origin": {"grid_x": 0, "grid_y": 0}}),
        context=ClientCommandContext(user_id="u1", room_ids=("r1",)),
    )
    assert result.handled
    assert result.response["code"] == "invalid_payload"


async def test_create_many_empty_actor_ids():
    result = await TokenCommandHandler().handle(
        cmd(ClientCommand.TOKEN_CREATE_MANY_FROM_ACTORS.value, "r1", {"scene_id": "s", "actor_ids": [], "origin": {"grid_x": 0, "grid_y": 0}}),
        context=ClientCommandContext(user_id="u1", room_ids=("r1",)),
    )
    assert result.handled
    assert result.response["code"] == "invalid_payload"


async def test_create_many_invalid_origin():
    result = await TokenCommandHandler().handle(
        cmd(ClientCommand.TOKEN_CREATE_MANY_FROM_ACTORS.value, "r1", {"scene_id": "s", "actor_ids": ["x"], "origin": {"grid_x": "bad"}}),
        context=ClientCommandContext(user_id="u1", room_ids=("r1",)),
    )
    assert result.handled
    assert result.response["code"] == "invalid_payload"


async def test_move_missing_token_id():
    result = await TokenCommandHandler().handle(
        cmd(ClientCommand.TOKEN_MOVE.value, "r1", {"scene_id": "s", "grid_x": 0, "grid_y": 0}),
        context=ClientCommandContext(user_id="u1", room_ids=("r1",)),
    )
    assert result.handled
    assert result.response["code"] == "invalid_payload"


async def test_condition_add_missing_label():
    result = await TokenCommandHandler().handle(
        cmd(ClientCommand.TOKEN_CONDITION_ADD.value, "r1", {"token_id": "t", "condition_id": "poisoned"}),
        context=ClientCommandContext(user_id="u1", room_ids=("r1",)),
    )
    assert result.handled
    assert result.response["code"] == "invalid_payload"


async def test_condition_add_invalid_kind():
    result = await TokenCommandHandler().handle(
        cmd(ClientCommand.TOKEN_CONDITION_ADD.value, "r1", {"token_id": "t", "condition_id": "x", "label": "X", "kind": "bad_kind"}),
        context=ClientCommandContext(user_id="u1", room_ids=("r1",)),
    )
    assert result.handled
    assert result.response["code"] == "invalid_payload"


                                                                             
                           
                                                                             

async def test_create_many_success(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    transport = mock_transport()

    result = await TokenCommandHandler().handle(
        cmd(
            ClientCommand.TOKEN_CREATE_MANY_FROM_ACTORS.value,
            campaign_id,
            {"scene_id": scene["id"], "actor_ids": [actor_id], "origin": {"grid_x": 3, "grid_y": 5}},
        ),
        context=ctx(campaign_id, gm_id),
        transport=transport,
    )

    assert result.handled
    assert result.response["type"] == "event"
    assert result.response["event"] == "token.command.ack"
    assert result.response["payload"]["success"] is True
    assert result.response["payload"]["token_count"] == 1
    transport.to_gm.assert_awaited_once()
    assert transport.to_gm.call_args.kwargs["event"] == TransportEvent.TOKENS_CREATED


async def test_create_one_legacy_command_success(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    transport = mock_transport()

    result = await TokenCommandHandler().handle(
        cmd(
            ClientCommand.TOKEN_CREATE.value,
            campaign_id,
            {"scene_id": scene["id"], "actor_id": actor_id, "grid_x": 3, "grid_y": 5},
        ),
        context=ctx(campaign_id, gm_id),
        transport=transport,
    )

    assert result.handled
    assert result.response["event"] == "token.command.ack"
    assert result.response["payload"]["command"] == ClientCommand.TOKEN_CREATE.value
    assert result.response["payload"]["success"] is True
    assert result.response["payload"]["token_count"] == 1
    transport.to_gm.assert_awaited_once()
    assert transport.to_gm.call_args.kwargs["event"] == TransportEvent.TOKENS_CREATED


async def test_move_success(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    result = await TokenCommandHandler().handle(
        cmd(
            ClientCommand.TOKEN_MOVE.value,
            campaign_id,
            {"scene_id": scene["id"], "token_id": token["id"], "grid_x": 5, "grid_y": 7},
        ),
        context=ctx(campaign_id, gm_id),
    )

    assert result.handled
    assert result.response["payload"]["success"] is True
    assert result.response["payload"]["token_id"] == token["id"]


async def test_update_override_success(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    result = await TokenCommandHandler().handle(
        cmd(
            ClientCommand.TOKEN_UPDATE_OVERRIDE.value,
            campaign_id,
            {"scene_id": scene["id"], "token_id": token["id"], "overrides": {"hp": {"value": 3, "max": 7}}},
        ),
        context=ctx(campaign_id, gm_id),
    )

    assert result.handled
    assert result.response["payload"]["success"] is True


async def test_hide_success(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    result = await TokenCommandHandler().handle(
        cmd(ClientCommand.TOKEN_HIDE.value, campaign_id, {"scene_id": scene["id"], "token_id": token["id"]}),
        context=ctx(campaign_id, gm_id),
    )

    assert result.handled
    assert result.response["payload"]["success"] is True
    assert TokenRepository().get_by_id(token["id"])["hidden"] == 1


async def test_reveal_success(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    repo = TokenRepository()
    token = repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)
    repo.set_hidden(token_id=token["id"], hidden=True)

    result = await TokenCommandHandler().handle(
        cmd(ClientCommand.TOKEN_REVEAL.value, campaign_id, {"scene_id": scene["id"], "token_id": token["id"]}),
        context=ctx(campaign_id, gm_id),
    )

    assert result.handled
    assert result.response["payload"]["success"] is True
    assert repo.get_by_id(token["id"])["hidden"] == 0


async def test_remove_from_scene_success(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    result = await TokenCommandHandler().handle(
        cmd(ClientCommand.TOKEN_REMOVE_FROM_SCENE.value, campaign_id, {"scene_id": scene["id"], "token_id": token["id"]}),
        context=ctx(campaign_id, gm_id),
    )

    assert result.handled
    assert result.response["payload"]["success"] is True
    assert TokenRepository().get_by_id(token["id"]) is None


async def test_condition_add_success(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    result = await TokenCommandHandler().handle(
        cmd(
            ClientCommand.TOKEN_CONDITION_ADD.value,
            campaign_id,
            {
                "token_id": token["id"],
                "condition_id": "poisoned",
                "label": "Poisoned",
                "kind": TokenConditionKind.NEGATIVE,
                "duration": 3,
            },
        ),
        context=ctx(campaign_id, gm_id),
    )

    assert result.handled
    assert result.response["payload"]["success"] is True
    assert result.response["payload"]["condition_id"] == "poisoned"


async def test_condition_remove_success(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )
    handler = TokenCommandHandler()
    await handler.handle(
        cmd(ClientCommand.TOKEN_CONDITION_ADD.value, campaign_id, {"token_id": token["id"], "condition_id": "prone", "label": "Prone"}),
        context=ctx(campaign_id, gm_id),
    )

    result = await handler.handle(
        cmd(ClientCommand.TOKEN_CONDITION_REMOVE.value, campaign_id, {"token_id": token["id"], "condition_id": "prone"}),
        context=ctx(campaign_id, gm_id),
    )

    assert result.handled
    assert result.response["payload"]["success"] is True


                                                                             
                           
                                                                             

async def test_create_many_player_permission_denied(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    player_id = seed_user(email="ch-player@test.com")
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    result = await TokenCommandHandler().handle(
        cmd(
            ClientCommand.TOKEN_CREATE_MANY_FROM_ACTORS.value,
            campaign_id,
            {"scene_id": scene["id"], "actor_ids": [actor_id], "origin": {"grid_x": 0, "grid_y": 0}},
        ),
        context=ctx(campaign_id, player_id),
    )

    assert result.handled
    assert result.response["code"] == "permission_denied"


async def test_move_nonexistent_token_returns_not_found(db):
    gm_id, campaign_id, scene, _ = make_stack(db)

    result = await TokenCommandHandler().handle(
        cmd(
            ClientCommand.TOKEN_MOVE.value,
            campaign_id,
            {"scene_id": scene["id"], "token_id": "nonexistent", "grid_x": 0, "grid_y": 0},
        ),
        context=ctx(campaign_id, gm_id),
    )

    assert result.handled
    assert result.response["code"] == "not_found"


async def test_condition_add_token_from_other_campaign(db):
    """Token from campaign B cannot be modified via campaign A's room_id."""
    gm_a = seed_user(email="gm-a@test.com")
    gm_b = seed_user(email="gm-b@test.com")
    campaign_a = seed_campaign(gm_a)
    campaign_b = seed_campaign(gm_b)
    scene_b = seed_scene(campaign_b)
    actor_b = seed_actor(campaign_b, gm_b)
    token_b = TokenRepository().create(
        scene_id=scene_b["id"], actor_id=actor_b, grid_x=0, grid_y=0
    )
                                                                                

    result = await TokenCommandHandler().handle(
        cmd(
            ClientCommand.TOKEN_CONDITION_ADD.value,
            campaign_a,
            {"token_id": token_b["id"], "condition_id": "poisoned", "label": "Poisoned"},
        ),
        context=ClientCommandContext(user_id=gm_a, room_ids=(campaign_a,)),
    )

    assert result.handled
    assert result.response["code"] in ("not_found", "permission_denied")
