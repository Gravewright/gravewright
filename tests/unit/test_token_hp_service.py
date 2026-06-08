from __future__ import annotations

from app.domain.roles import PlayerRole
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.engine.tokens.token_hp_service import TokenHpService
from app.engine.tokens.token_instance_sheet_service import INSTANCE_KEY
from app.engine.tokens.token_service import TokenService
from app.persistence.repositories.token_repository import TokenRepository
from tests.conftest import (
    grant_actor_access,
    seed_actor,
    seed_campaign,
    seed_member,
    seed_scene,
    seed_system,
    seed_user,
)


def make_stack(db):
    gm_id = seed_user(email="hp-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)
    seed_system(campaign_id, gm_id)
    actor_id = seed_actor(
        campaign_id,
        gm_id,
        name="Monstro Modelo",
        data={"hp": {"value": 10, "max": 10}},
    )
    return gm_id, campaign_id, scene, actor_id


async def test_update_hp_on_single_linked_token_updates_actor_sheet(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    created = await TokenService().create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=[actor_id],
        origin_x=0,
        origin_y=0,
        user_id=gm_id,
    )
    token_id = created.tokens[0]["token_id"]

    result = TokenHpService().update_hp(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token_id,
        user_id=gm_id,
        operation="damage",
        amount=4,
    )

    assert result.success
    assert result.linked_actor is True
    assert result.value_before == 10
    assert result.value_after == 6
    assert result.token_view["bars"]["hp"] == {"value": 6, "max": 10, "visibility": "everyone"}
    envelope = ScopedJsonStorage().read_actor(
        system_id="dnd5e",
        campaign_id=campaign_id,
        actor_id=actor_id,
    )
    assert envelope["data"]["hp"]["value"] == 6


async def test_update_hp_on_unlinked_token_updates_only_that_token_instance(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    await TokenService().create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=[actor_id, actor_id],
        origin_x=0,
        origin_y=0,
        user_id=gm_id,
    )
    first, second = TokenRepository().list_by_scene(scene["id"])

    result = TokenHpService().update_hp(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=first["id"],
        user_id=gm_id,
        operation="damage",
        amount=7,
    )

    assert result.success
    assert result.linked_actor is False
    assert result.value_after == 3
    updated_first = TokenRepository().get_by_id(first["id"])
    updated_second = TokenRepository().get_by_id(second["id"])
    assert updated_first["overrides"][INSTANCE_KEY]["data"]["hp"] == {"value": 3, "max": 10}
    assert updated_first["overrides"]["hp"] == {"value": 3, "max": 10}
    assert updated_second["overrides"][INSTANCE_KEY]["data"]["hp"] == {"value": 10, "max": 10}
    envelope = ScopedJsonStorage().read_actor(
        system_id="dnd5e",
        campaign_id=campaign_id,
        actor_id=actor_id,
    )
    assert envelope["data"]["hp"] == {"value": 10, "max": 10}


async def test_update_hp_denied_for_player_without_actor_edit(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    player_id = seed_user(email="hp-player@test.com")
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    created = await TokenService().create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=[actor_id],
        origin_x=0,
        origin_y=0,
        user_id=gm_id,
    )

    result = TokenHpService().update_hp(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=created.tokens[0]["token_id"],
        user_id=player_id,
        operation="damage",
        amount=1,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.permission_denied"


async def test_update_hp_allowed_for_actor_owner(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    player_id = seed_user(email="hp-owner@test.com")
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    grant_actor_access(actor_id, player_id, edit=True)
    created = await TokenService().create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=[actor_id],
        origin_x=0,
        origin_y=0,
        user_id=gm_id,
    )

    result = TokenHpService().update_hp(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=created.tokens[0]["token_id"],
        user_id=player_id,
        operation="set",
        value=8,
    )

    assert result.success
    assert result.value_after == 8
