from __future__ import annotations

import pytest

from app.domain.roles import PlayerRole
from app.engine.tokens.token_service import TokenResult
from app.engine.tokens.token_service import TokenService
from app.realtime.command_dispatcher import ClientCommandContext
from app.realtime.commands import ClientCommand
from app.realtime.token_command_handler import _MAX_CONDITION_LABEL_LEN
from app.realtime.token_command_handler import _MAX_OVERRIDE_BYTES
from app.realtime.token_command_handler import _MAX_TOKENS_PER_CREATE
from app.realtime.token_command_handler import TokenCommandHandler
from tests.conftest import (
    grant_actor_access,
    seed_actor,
    seed_campaign,
    seed_member,
    seed_scene,
    seed_system,
    seed_user,
)


                                                                              

async def _gm_token_for_actor(db):
    gm_id = seed_user(email="tok-split-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)
    seed_system(campaign_id, gm_id)
    actor_id = seed_actor(campaign_id, gm_id, name="Goblin")
    result = await TokenService().create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=[actor_id],
        origin_x=0,
        origin_y=0,
        user_id=gm_id,
    )
    token_id = result.tokens[0]["token_id"]
    return gm_id, campaign_id, scene, actor_id, token_id


async def test_controlling_player_can_add_condition_without_manage_permission(db):
    _gm_id, campaign_id, _scene, actor_id, token_id = await _gm_token_for_actor(db)
    player_id = seed_user(email="tok-split-owner@test.com")
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    grant_actor_access(actor_id, player_id, edit=True)

    result = await TokenService().add_condition(
        campaign_id=campaign_id,
        token_id=token_id,
        condition_id="poisoned",
        label="Poisoned",
        user_id=player_id,
    )

    assert result.success is True


async def test_non_controlling_player_cannot_add_condition(db):
    _gm_id, campaign_id, _scene, _actor_id, token_id = await _gm_token_for_actor(db)
    player_id = seed_user(email="tok-split-bystander@test.com")
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    result = await TokenService().add_condition(
        campaign_id=campaign_id,
        token_id=token_id,
        condition_id="poisoned",
        label="Poisoned",
        user_id=player_id,
    )

    assert result.success is False
    assert result.error_key == "tokens.errors.permission_denied"


async def test_non_controlling_player_cannot_hide_token(db):
    _gm_id, campaign_id, scene, _actor_id, token_id = await _gm_token_for_actor(db)
    player_id = seed_user(email="tok-split-hide@test.com")
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    result = await TokenService().set_hidden(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token_id,
        hidden=True,
        user_id=player_id,
    )

    assert result.success is False
    assert result.error_key == "tokens.errors.permission_denied"


                                                                               

class _SpyService:
    def __init__(self) -> None:
        self.called = False

    async def create_many_from_actors(self, **_kw):
        self.called = True
        return TokenResult(success=True, tokens=[])

    async def update_override(self, **_kw):
        self.called = True
        return TokenResult(success=True, token={"version": 1})

    async def add_condition(self, **_kw):
        self.called = True
        return TokenResult(success=True)


def _ctx() -> ClientCommandContext:
    return ClientCommandContext(user_id="user-1", room_ids=("room-1",))


def _cmd(command: str, payload: dict) -> dict:
    return {"type": "command", "id": "c1", "command": command, "room_id": "room-1", "payload": payload}


@pytest.mark.asyncio
async def test_create_many_batch_limit_rejected_before_service():
    spy = _SpyService()
    handler = TokenCommandHandler(service=spy)

    result = await handler.handle(
        _cmd(
            ClientCommand.TOKEN_CREATE_MANY_FROM_ACTORS.value,
            {
                "scene_id": "scene-1",
                "actor_ids": [f"a{i}" for i in range(_MAX_TOKENS_PER_CREATE + 1)],
                "origin": {"grid_x": 0, "grid_y": 0},
            },
        ),
        context=_ctx(),
    )

    assert result.response["code"] == "invalid_payload"
    assert spy.called is False


@pytest.mark.asyncio
async def test_oversized_overrides_rejected_before_service():
    spy = _SpyService()
    handler = TokenCommandHandler(service=spy)
    big = {"blob": "x" * (_MAX_OVERRIDE_BYTES + 10)}

    result = await handler.handle(
        _cmd(
            ClientCommand.TOKEN_UPDATE_OVERRIDE.value,
            {"scene_id": "scene-1", "token_id": "t1", "overrides": big},
        ),
        context=_ctx(),
    )

    assert result.response["code"] == "invalid_payload"
    assert spy.called is False


@pytest.mark.asyncio
async def test_condition_label_and_visibility_validated():
    spy = _SpyService()
    handler = TokenCommandHandler(service=spy)

    too_long = await handler.handle(
        _cmd(
            ClientCommand.TOKEN_CONDITION_ADD.value,
            {"token_id": "t1", "condition_id": "c", "label": "L" * (_MAX_CONDITION_LABEL_LEN + 1)},
        ),
        context=_ctx(),
    )
    assert too_long.response["code"] == "invalid_payload"

    bad_visibility = await handler.handle(
        _cmd(
            ClientCommand.TOKEN_CONDITION_ADD.value,
            {"token_id": "t1", "condition_id": "c", "label": "ok", "visible_to": "world"},
        ),
        context=_ctx(),
    )
    assert bad_visibility.response["code"] == "invalid_payload"
    assert spy.called is False
