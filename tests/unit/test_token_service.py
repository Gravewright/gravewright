from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from app.domain.roles import PlayerRole
from app.domain.tokens import TokenConditionKind
from app.engine.tokens.token_instance_sheet_service import INSTANCE_KEY
from app.engine.tokens.token_instance_sheet_service import TokenInstanceSheetService
from app.engine.tokens.token_service import TokenService
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.persistence.database import engine_begin
from app.persistence.repositories.token_repository import TokenRepository
from app.realtime.events import TransportEvent
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
    gm_id = seed_user(email="svc-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)
    seed_system(campaign_id, gm_id)
    actor_id = seed_actor(campaign_id, gm_id, name="Monstro Modelo", data={"hp": {"value": 10, "max": 10}})
    return gm_id, campaign_id, scene, actor_id


def make_player(campaign_id: str) -> str:
    player_id = seed_user(email=f"player-{id(campaign_id)}@test.com")
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    return player_id


def grant_edit(actor_id: str, user_id: str) -> None:
    """Give a player edit access to an actor (mirrors set_member_access read/owner)."""
    grant_actor_access(actor_id, user_id, edit=True)


def mock_transport():
    t = MagicMock()
    t.to_room = AsyncMock()
    t.to_gm = AsyncMock()
    t.to_player = AsyncMock()
    t.to_players_in_room = AsyncMock()
    t.to_streamers = AsyncMock()
    return t


                                                                             
                         
                                                                             

async def test_gm_creates_tokens_from_actors(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)

    result = await TokenService().create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=[actor_id],
        origin_x=5,
        origin_y=3,
        user_id=gm_id,
    )

    assert result.success
    assert len(result.tokens) == 1
    assert result.tokens[0]["grid_x"] == 5
    assert result.tokens[0]["grid_y"] == 3


async def test_player_cannot_create_tokens(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    player_id = make_player(campaign_id)

    result = await TokenService().create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=[actor_id],
        origin_x=0,
        origin_y=0,
        user_id=player_id,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.permission_denied"


async def test_create_tokens_from_multiple_actors_uses_formation(db):
    gm_id, campaign_id, scene, _ = make_stack(db)
    actor_ids = [seed_actor(campaign_id, gm_id, name=f"Monstro Modelo {i}") for i in range(4)]

    result = await TokenService().create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=actor_ids,
        origin_x=0,
        origin_y=0,
        user_id=gm_id,
    )

    assert result.success
    assert len(result.tokens) == 4
    positions = [(t["grid_x"], t["grid_y"]) for t in result.tokens]
                                          
    assert (0, 0) in positions
    assert (1, 0) in positions
    assert (0, 1) in positions
    assert (1, 1) in positions


async def test_create_tokens_wrong_campaign_scene(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    other_gm = seed_user(email="other-gm@test.com")
    other_campaign = seed_campaign(other_gm)
    seed_member(other_campaign, gm_id, PlayerRole.GM.value)

    result = await TokenService().create_many_from_actors(
        campaign_id=other_campaign,
        scene_id=scene["id"],                                                    
        actor_ids=[actor_id],
        origin_x=0,
        origin_y=0,
        user_id=gm_id,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.scene_not_found"


async def test_create_tokens_empty_actor_ids(db):
    gm_id, campaign_id, scene, _ = make_stack(db)

    result = await TokenService().create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=[],
        origin_x=0,
        origin_y=0,
        user_id=gm_id,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.no_actors"


async def test_create_tokens_invalid_actor(db):
    gm_id, campaign_id, scene, _ = make_stack(db)

    result = await TokenService().create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=["nonexistent-actor"],
        origin_x=0,
        origin_y=0,
        user_id=gm_id,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.actor_not_found"


async def test_create_tokens_emits_batch_event(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    transport = mock_transport()

    await TokenService().create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=[actor_id, seed_actor(campaign_id, gm_id, name="Orc")],
        origin_x=0,
        origin_y=0,
        user_id=gm_id,
        transport=transport,
    )

    transport.to_gm.assert_awaited_once()
    transport.to_player.assert_not_awaited()
    call_kwargs = transport.to_gm.call_args.kwargs
    assert call_kwargs["event"] == TransportEvent.TOKENS_CREATED
    assert call_kwargs["room_id"] == campaign_id
    assert len(call_kwargs["payload"]["tokens"]) == 2


async def test_create_tokens_emits_to_all_players(db):
                                                                          
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    make_player(campaign_id)
    transport = mock_transport()

    await TokenService().create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=[actor_id],
        origin_x=0,
        origin_y=0,
        user_id=gm_id,
        transport=transport,
    )

    transport.to_gm.assert_awaited_once()
    transport.to_players_in_room.assert_awaited_once()
    transport.to_player.assert_not_awaited()
    call_kwargs = transport.to_players_in_room.call_args.kwargs
    assert call_kwargs["event"] == TransportEvent.TOKENS_CREATED
    assert call_kwargs["payload"]["tokens"][0]["name"] == "Monstro Modelo"


async def test_create_tokens_returns_tokenviews(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)

    result = await TokenService().create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=[actor_id],
        origin_x=2,
        origin_y=4,
        user_id=gm_id,
    )

    view = result.tokens[0]
    assert "token_id" in view
    assert "bars" in view
    assert "status_summary" in view
    assert view["name"] == "Monstro Modelo"
                                                                           
    assert view["bars"]["hp"]["value"] == 10


async def test_create_tokens_snapshot_actor_per_token_without_cloning_directory_actor(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    with engine_begin() as connection:
        connection.exec_driver_sql(
            "UPDATE actors_core SET token_asset_id = 'actors/template-monster-token.webp' WHERE id = ?",
            (actor_id,),
        )

    result = await TokenService().create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=[actor_id, actor_id],
        origin_x=0,
        origin_y=0,
        user_id=gm_id,
    )

    assert result.success
    stored = TokenRepository().list_by_scene(scene["id"])
    assert len(stored) == 2
    assert [token["actor_id"] for token in stored] == [actor_id, actor_id]
    assert all(token["actor_link_mode"] == "unlinked" for token in stored)
    assert all(token["name"] == "Monstro Modelo" for token in stored)
    assert all(token["token_asset_url"].startswith(f"/game/actor/{actor_id}/image/token") for token in stored)
    assert all(token["overrides"]["hp"] == {"value": 10, "max": 10} for token in stored)
    assert all(token["overrides"][INSTANCE_KEY]["source_actor_id"] == actor_id for token in stored)
    assert all(token["overrides"][INSTANCE_KEY]["data"]["hp"] == {"value": 10, "max": 10} for token in stored)


async def test_token_sheet_patch_updates_only_that_token_instance(db):
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

    result = TokenInstanceSheetService().patch_data(
        token_id=first["id"],
        user_id=gm_id,
        patch={"hp.value": 3, "core.name": "Monstro Modelo A"},
    )

    assert result.success
    updated_first = TokenRepository().get_by_id(first["id"])
    updated_second = TokenRepository().get_by_id(second["id"])
    assert updated_first["overrides"][INSTANCE_KEY]["data"]["hp"] == {"value": 3, "max": 10}
    assert updated_first["overrides"][INSTANCE_KEY]["name"] == "Monstro Modelo A"
    assert updated_first["overrides"]["name"] == "Monstro Modelo A"
    assert updated_first["overrides"]["hp"] == {"value": 3, "max": 10}
    assert updated_second["overrides"][INSTANCE_KEY]["data"]["hp"] == {"value": 10, "max": 10}
    envelope = ScopedJsonStorage().read_actor(
        system_id="dnd5e",
        campaign_id=campaign_id,
        actor_id=actor_id,
    )
    assert envelope["data"]["hp"] == {"value": 10, "max": 10}
    assert TokenRepository().get_by_id(second["id"])["name"] == "Monstro Modelo"



async def test_first_token_for_actor_is_linked_to_directory_sheet(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)

    result = await TokenService().create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=[actor_id],
        origin_x=0,
        origin_y=0,
        user_id=gm_id,
    )

    assert result.success
    stored = TokenRepository().list_by_scene(scene["id"])
    assert len(stored) == 1
    assert stored[0]["actor_id"] == actor_id
    assert stored[0]["actor_link_mode"] == "linked"
    assert INSTANCE_KEY not in stored[0]["overrides"]


async def test_second_token_promotes_existing_linked_token_to_unlinked_snapshot(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    svc = TokenService()

    first = await svc.create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=[actor_id],
        origin_x=0,
        origin_y=0,
        user_id=gm_id,
    )
    assert first.success
    first_token_id = first.tokens[0]["token_id"]

    second = await svc.create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=[actor_id],
        origin_x=1,
        origin_y=0,
        user_id=gm_id,
    )

    assert second.success
    stored = TokenRepository().list_by_scene(scene["id"])
    assert len(stored) == 2
    by_id = {token["id"]: token for token in stored}
    assert by_id[first_token_id]["actor_link_mode"] == "unlinked"
    assert second.tokens[0]["token_id"] in by_id
    assert by_id[second.tokens[0]["token_id"]]["actor_link_mode"] == "unlinked"
    assert by_id[first_token_id]["overrides"][INSTANCE_KEY]["source_actor_id"] == actor_id
    assert by_id[first_token_id]["overrides"][INSTANCE_KEY]["data"]["hp"] == {"value": 10, "max": 10}
    assert by_id[second.tokens[0]["token_id"]]["overrides"][INSTANCE_KEY]["data"]["hp"] == {"value": 10, "max": 10}


async def test_unlinked_token_does_not_create_extra_directory_actor(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    await TokenService().create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=[actor_id, actor_id],
        origin_x=0,
        origin_y=0,
        user_id=gm_id,
    )

    with engine_begin() as connection:
        rows = connection.exec_driver_sql(
            "SELECT id, name FROM actors_core WHERE campaign_id = ? AND status = 'active'",
            (campaign_id,),
        ).mappings().all()
    assert [dict(row)["id"] for row in rows] == [actor_id]


async def test_create_tokens_uses_projected_actor_size_for_grid_footprint(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    projector = MagicMock()
    projector.project.return_value = {"size": "huge"}

    result = await TokenService(projector=projector).create_many_from_actors(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        actor_ids=[actor_id],
        origin_x=2,
        origin_y=4,
        user_id=gm_id,
    )

    assert result.success
    assert result.tokens[0]["width_cells"] == 3
    assert result.tokens[0]["height_cells"] == 3


def test_token_grid_footprint_has_one_cell_minimum(db):
    dimensions = TokenService()._resolve_token_dimensions(
        config={"width_cells": 0, "height_cells": -2},
        projection={"size": "gargantuan"},
    )

    assert dimensions == (1, 1)


                                                                             
                                                   
                                                                             

async def test_gm_moves_token(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    result = await TokenService().move(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        grid_x=7,
        grid_y=5,
        user_id=gm_id,
    )

    assert result.success
    assert result.token["grid_x"] == 7
    assert result.token["grid_y"] == 5
    assert result.token["version"] == token["version"] + 1


async def test_player_without_actor_edit_cannot_move(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    player_id = make_player(campaign_id)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0,
    )

    result = await TokenService().move(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        grid_x=3,
        grid_y=3,
        user_id=player_id,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.permission_denied"


async def test_read_only_observer_cannot_move(db):
                                                                        
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    player_id = make_player(campaign_id)
    grant_actor_access(actor_id, player_id, view=True)                              
    token = TokenRepository().create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)

    result = await TokenService().move(
        campaign_id=campaign_id, scene_id=scene["id"], token_id=token["id"],
        grid_x=3, grid_y=3, user_id=player_id,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.permission_denied"


async def test_player_with_actor_edit_can_move(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    player_id = make_player(campaign_id)
    grant_edit(actor_id, player_id)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0,
    )

    result = await TokenService().move(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        grid_x=3,
        grid_y=3,
        user_id=player_id,
    )

    assert result.success


async def test_move_unlinked_token_denied_for_player(db):
    gm_id, campaign_id, scene, _ = make_stack(db)
    player_id = make_player(campaign_id)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=None, grid_x=0, grid_y=0,
    )

    result = await TokenService().move(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        grid_x=3,
        grid_y=3,
        user_id=player_id,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.permission_denied"


async def test_outsider_cannot_move_token(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    outsider_id = seed_user(email="outsider@test.com")
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    result = await TokenService().move(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        grid_x=3,
        grid_y=3,
        user_id=outsider_id,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.permission_denied"


async def test_move_locked_token_fails(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )
    with engine_begin() as conn:
        conn.exec_driver_sql("UPDATE tokens SET locked = 1 WHERE id = ?", (token["id"],))

    result = await TokenService().move(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        grid_x=5,
        grid_y=5,
        user_id=gm_id,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.locked"


async def test_move_emits_batch_event(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    transport = mock_transport()
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    await TokenService().move(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        grid_x=3,
        grid_y=3,
        user_id=gm_id,
        transport=transport,
    )

    transport.to_gm.assert_awaited_once()
    call_kwargs = transport.to_gm.call_args.kwargs
    assert call_kwargs["event"] == TransportEvent.TOKENS_MOVED
    assert call_kwargs["payload"]["tokens"][0]["token_id"] == token["id"]


async def test_move_emits_to_all_players(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    make_player(campaign_id)
    transport = mock_transport()
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    await TokenService().move(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        grid_x=3,
        grid_y=3,
        user_id=gm_id,
        transport=transport,
    )

    transport.to_gm.assert_awaited_once()
    transport.to_players_in_room.assert_awaited_once()
    transport.to_player.assert_not_awaited()


async def test_gm_cannot_move_token_from_other_campaign_with_mismatched_scene(db):
    gm_id = seed_user(email="cross-move-gm@test.com")
    campaign_a = seed_campaign(gm_id, title="Campaign A")
    campaign_b = seed_campaign(gm_id, title="Campaign B")
    scene_b = seed_scene(campaign_b)
    seed_system(campaign_b, gm_id)
    actor_b = seed_actor(campaign_b, gm_id, name="Other Monstro Modelo")
    token_b = TokenRepository().create(scene_id=scene_b["id"], actor_id=actor_b, grid_x=0, grid_y=0)

    result = await TokenService().move(
        campaign_id=campaign_a,
        scene_id=scene_b["id"],
        token_id=token_b["id"],
        grid_x=9,
        grid_y=9,
        user_id=gm_id,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.scene_not_found"
    stored = TokenRepository().get_by_id(token_b["id"])
    assert stored["grid_x"] == 0
    assert stored["grid_y"] == 0


                                                                             
                 
                                                                             

async def test_gm_updates_override(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    result = await TokenService().update_override(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        overrides={"hp": {"value": 3, "max": 7}},
        user_id=gm_id,
    )

    assert result.success
    assert result.token["overrides"]["hp"]["value"] == 3


async def test_player_with_actor_edit_updates_override(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    player_id = make_player(campaign_id)
    grant_edit(actor_id, player_id)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    result = await TokenService().update_override(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        overrides={"hp": {"value": 5, "max": 10}},
        user_id=player_id,
    )

    assert result.success


async def test_player_without_actor_edit_cannot_update_override(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    player_id = make_player(campaign_id)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    result = await TokenService().update_override(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        overrides={"hp": {"value": 1, "max": 10}},
        user_id=player_id,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.permission_denied"


async def test_gm_cannot_update_override_for_token_from_other_campaign(db):
    gm_id = seed_user(email="cross-update-gm@test.com")
    campaign_a = seed_campaign(gm_id, title="Campaign A")
    campaign_b = seed_campaign(gm_id, title="Campaign B")
    scene_b = seed_scene(campaign_b)
    seed_system(campaign_b, gm_id)
    actor_b = seed_actor(campaign_b, gm_id, name="Other Monstro Modelo")
    token_b = TokenRepository().create(scene_id=scene_b["id"], actor_id=actor_b, grid_x=0, grid_y=0)

    result = await TokenService().update_override(
        campaign_id=campaign_a,
        scene_id=scene_b["id"],
        token_id=token_b["id"],
        overrides={"hp": {"value": 1}},
        user_id=gm_id,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.scene_not_found"
    assert TokenRepository().get_by_id(token_b["id"])["overrides"] == {}


                                                                             
            
                                                                             

async def test_gm_hides_token(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    result = await TokenService().set_hidden(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        hidden=True,
        user_id=gm_id,
    )

    assert result.success
    assert result.token["hidden"] == 1
    assert result.token["version"] == token["version"] + 1


async def test_player_cannot_hide_token(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    player_id = make_player(campaign_id)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    result = await TokenService().set_hidden(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        hidden=True,
        user_id=player_id,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.permission_denied"


async def test_set_hidden_emits_visibility_changed_event(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    transport = mock_transport()
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    await TokenService().set_hidden(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        hidden=True,
        user_id=gm_id,
        transport=transport,
    )

    transport.to_gm.assert_awaited_once()
    call_kwargs = transport.to_gm.call_args.kwargs
    assert call_kwargs["event"] == TransportEvent.TOKENS_VISIBILITY_CHANGED
    assert call_kwargs["payload"]["tokens"][0]["hidden"] is True


async def test_gm_cannot_hide_token_from_other_campaign(db):
    gm_id = seed_user(email="cross-hide-gm@test.com")
    campaign_a = seed_campaign(gm_id, title="Campaign A")
    campaign_b = seed_campaign(gm_id, title="Campaign B")
    scene_b = seed_scene(campaign_b)
    seed_system(campaign_b, gm_id)
    actor_b = seed_actor(campaign_b, gm_id, name="Other Monstro Modelo")
    token_b = TokenRepository().create(scene_id=scene_b["id"], actor_id=actor_b, grid_x=0, grid_y=0)

    result = await TokenService().set_hidden(
        campaign_id=campaign_a,
        scene_id=scene_b["id"],
        token_id=token_b["id"],
        hidden=True,
        user_id=gm_id,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.scene_not_found"
    assert TokenRepository().get_by_id(token_b["id"])["hidden"] == 0


                                                                             
                   
                                                                             

async def test_gm_removes_token(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    result = await TokenService().remove_from_scene(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        user_id=gm_id,
    )

    assert result.success
    assert TokenRepository().get_by_id(token["id"]) is None


async def test_player_cannot_remove_token(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    player_id = make_player(campaign_id)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    result = await TokenService().remove_from_scene(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        user_id=player_id,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.permission_denied"


async def test_remove_emits_deleted_event(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    transport = mock_transport()
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    await TokenService().remove_from_scene(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        user_id=gm_id,
        transport=transport,
    )

    transport.to_gm.assert_awaited_once()
    call_kwargs = transport.to_gm.call_args.kwargs
    assert call_kwargs["event"] == TransportEvent.TOKENS_DELETED
    assert token["id"] in call_kwargs["payload"]["token_ids"]


async def test_gm_cannot_remove_token_from_other_campaign(db):
    gm_id = seed_user(email="cross-remove-gm@test.com")
    campaign_a = seed_campaign(gm_id, title="Campaign A")
    campaign_b = seed_campaign(gm_id, title="Campaign B")
    scene_b = seed_scene(campaign_b)
    seed_system(campaign_b, gm_id)
    actor_b = seed_actor(campaign_b, gm_id, name="Other Monstro Modelo")
    token_b = TokenRepository().create(scene_id=scene_b["id"], actor_id=actor_b, grid_x=0, grid_y=0)

    result = await TokenService().remove_from_scene(
        campaign_id=campaign_a,
        scene_id=scene_b["id"],
        token_id=token_b["id"],
        user_id=gm_id,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.scene_not_found"
    assert TokenRepository().get_by_id(token_b["id"]) is not None


                                                                             
                                  
                                                                             

async def test_gm_adds_condition(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    result = await TokenService().add_condition(
        campaign_id=campaign_id,
        token_id=token["id"],
        condition_id="poisoned",
        label="Poisoned",
        kind=TokenConditionKind.NEGATIVE,
        user_id=gm_id,
    )

    assert result.success


async def test_player_cannot_add_condition(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    player_id = make_player(campaign_id)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    result = await TokenService().add_condition(
        campaign_id=campaign_id,
        token_id=token["id"],
        condition_id="poisoned",
        label="Poisoned",
        user_id=player_id,
    )

    assert not result.success


async def test_gm_removes_condition(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )
    svc = TokenService()
    await svc.add_condition(
        campaign_id=campaign_id,
        token_id=token["id"],
        condition_id="prone",
        label="Prone",
        user_id=gm_id,
    )

    result = await svc.remove_condition(
        campaign_id=campaign_id,
        token_id=token["id"],
        condition_id="prone",
        user_id=gm_id,
    )

    assert result.success


async def test_remove_missing_condition_fails(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    result = await TokenService().remove_condition(
        campaign_id=campaign_id,
        token_id=token["id"],
        condition_id="stun",
        user_id=gm_id,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.condition_not_found"


async def test_add_condition_emits_event(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    transport = mock_transport()
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    await TokenService().add_condition(
        campaign_id=campaign_id,
        token_id=token["id"],
        condition_id="poisoned",
        label="Poisoned",
        user_id=gm_id,
        transport=transport,
    )

    transport.to_gm.assert_awaited_once()
    call_kwargs = transport.to_gm.call_args.kwargs
    assert call_kwargs["event"] == TransportEvent.TOKENS_CONDITIONS_UPDATED
    assert call_kwargs["payload"]["token_id"] == token["id"]
    assert len(call_kwargs["payload"]["conditions"]) == 1


                                                                             
                                                    
                                                                             

async def test_refresh_actor_tokens_emits_update_per_scene(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    transport = mock_transport()
    TokenRepository().create(
        scene_id=scene["id"],
        actor_id=actor_id,
        grid_x=0,
        grid_y=0,
        actor_link_mode="linked",
    )

    await TokenService().refresh_actor_tokens(
        campaign_id=campaign_id,
        actor_id=actor_id,
        transport=transport,
    )

    transport.to_room.assert_awaited_once()
    call_kwargs = transport.to_room.call_args.kwargs
    assert call_kwargs["event"] == TransportEvent.TOKENS_UPDATED
    assert call_kwargs["payload"]["scene_id"] == scene["id"]


async def test_refresh_actor_tokens_noop_without_linked_tokens(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    transport = mock_transport()
    TokenRepository().create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)

    await TokenService().refresh_actor_tokens(
        campaign_id=campaign_id,
        actor_id=actor_id,
        transport=transport,
    )

    transport.to_room.assert_not_awaited()


                                                                             
              
                                                                             

async def test_gm_snapshot_includes_hidden_tokens(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    repo = TokenRepository()
    repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)
    hidden = repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=1, grid_y=0)
    repo.set_hidden(token_id=hidden["id"], hidden=True)

    result = TokenService().get_snapshot(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        user_id=gm_id,
    )

    assert result.success
    assert len(result.tokens) == 2


async def test_player_snapshot_excludes_hidden_tokens(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    player_id = make_player(campaign_id)
    repo = TokenRepository()
    repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)
    hidden = repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=1, grid_y=0)
    repo.set_hidden(token_id=hidden["id"], hidden=True)

    result = TokenService().get_snapshot(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        user_id=player_id,
    )

    assert result.success
    assert len(result.tokens) == 1
    assert result.tokens[0]["hidden"] is False


async def test_player_snapshot_includes_unlinked_and_linked_tokens(db):
                                                                                  
                        
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    player_id = make_player(campaign_id)
    repo = TokenRepository()
    repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)
    repo.create(scene_id=scene["id"], actor_id=None, grid_x=1, grid_y=0, name="Torch")

    result = TokenService().get_snapshot(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        user_id=player_id,
    )

    assert result.success
    assert len(result.tokens) == 2
    names = [token["name"] for token in result.tokens]
    assert "Torch" in names
    assert "Monstro Modelo" in names


async def test_snapshot_includes_conditions(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )
    svc = TokenService()
    await svc.add_condition(
        campaign_id=campaign_id,
        token_id=token["id"],
        condition_id="poisoned",
        label="Poisoned",
        kind=TokenConditionKind.NEGATIVE,
        user_id=gm_id,
    )

    result = svc.get_snapshot(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        user_id=gm_id,
    )

    assert result.success
    view = result.tokens[0]
    assert view["status_summary"]["count"] == 1
    assert view["status_summary"]["has_negative"] is True


async def test_snapshot_wrong_campaign_fails(db):
    gm_id, campaign_id, scene, _ = make_stack(db)
    other_gm = seed_user(email="snap-other@test.com")
    other_campaign = seed_campaign(other_gm)
    seed_member(other_campaign, gm_id, PlayerRole.GM.value)

    result = TokenService().get_snapshot(
        campaign_id=other_campaign,
        scene_id=scene["id"],
        user_id=gm_id,
    )

    assert not result.success
    assert result.error_key == "tokens.errors.scene_not_found"


async def test_move_with_stale_expected_version_returns_conflict(db):
    gm_id, campaign_id, scene, actor_id = make_stack(db)
    token = TokenRepository().create(
        scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0
    )

    first = await TokenService().move(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        grid_x=1,
        grid_y=1,
        user_id=gm_id,
        expected_version=token["version"],
    )
    stale = await TokenService().move(
        campaign_id=campaign_id,
        scene_id=scene["id"],
        token_id=token["id"],
        grid_x=2,
        grid_y=2,
        user_id=gm_id,
        expected_version=token["version"],
    )

    assert first.success
    assert not stale.success
    assert stale.error_key == "tokens.errors.version_conflict"
