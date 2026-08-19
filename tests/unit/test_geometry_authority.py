import asyncio
import math

import pytest
from sqlalchemy import update

from app.engine.scenes.geometry_semantics import channel_blocks, line_of_sight_blocked, movement_crosses_wall
from app.engine.scenes.scene_wall_service import SceneWallService
from app.engine.tokens.token_service import TokenService
from app.persistence.repositories.token_repository import TokenRepository
from app.persistence.database import engine_begin
from app.persistence.tables import scenes
from tests.conftest import seed_campaign, seed_member, seed_scene, seed_user


BASE = {"x1": 70.0, "y1": 0.0, "x2": 70.0, "y2": 140.0}


@pytest.mark.parametrize(
    ("presentation", "behavior"),
    [
        ("normal", {"movement": "block", "vision": "block", "light": "block"}),
        ("window", {"movement": "block", "vision": "pass", "light": "pass"}),
        ("bars", {"movement": "block", "vision": "pass", "light": "pass"}),
        ("invisible", {"movement": "block", "vision": "pass", "light": "pass"}),
    ],
)
def test_closed_profiles_have_independent_movement_vision_and_light(presentation, behavior):
    wall = {**BASE, "presentation": presentation, **{f"{key}_behavior": value for key, value in behavior.items()}}
    for channel, expected in behavior.items():
        assert channel_blocks(wall, channel) is (expected == "block")
    assert movement_crosses_wall(walls=[wall], origin=(0, 70), target=(140, 70)) is (behavior["movement"] == "block")
    assert line_of_sight_blocked(walls=[wall], origin=(0, 70, 0), target=(140, 70, 0)) is (behavior["vision"] == "block")
    assert line_of_sight_blocked(walls=[wall], origin=(0, 70, 0), target=(140, 70, 0), channel="light") is (behavior["light"] == "block")


def test_secret_projection_and_discovery_do_not_leak(db):
    gm, player = seed_user(name="GM"), seed_user(name="Player")
    campaign = seed_campaign(gm); seed_member(campaign, player, "player"); scene = seed_scene(campaign)["id"]
    service = SceneWallService()
    created = service.create(campaign_id=campaign, scene_id=scene, user_id=gm, kind="door",
                             presentation="secret", behavior=None, vertical=None, **BASE)
    wall_id = created.payload["wall"]["id"]
    gm_wall = service.state(campaign_id=campaign, scene_id=scene, user_id=gm).payload["walls"][0]
    player_wall = service.state(campaign_id=campaign, scene_id=scene, user_id=player).payload["walls"][0]
    assert gm_wall["presentation"] == "secret" and gm_wall["kind"] == "door"
    assert player_wall["presentation"] == "normal" and player_wall["kind"] == "wall"
    assert "discovered" not in player_wall and "door_state" not in player_wall
    assert service.update(campaign_id=campaign, wall_id=wall_id, user_id=gm, discovered=True).success
    revealed = service.state(campaign_id=campaign, scene_id=scene, user_id=player).payload["walls"][0]
    assert revealed["presentation"] == "secret" and revealed["kind"] == "door"


def test_vertical_bounds_and_rays_preserve_legacy_behavior():
    legacy = {**BASE, "movement_behavior": "block", "vision_behavior": "block", "light_behavior": "block"}
    low = {**legacy, "vertical_bottom": 0, "vertical_top": 1}
    elevated = {**legacy, "vertical_bottom": 3, "vertical_top": 5}
    assert movement_crosses_wall(walls=[legacy], origin=(0, 70), target=(140, 70), elevation=100)
    assert movement_crosses_wall(walls=[low], origin=(0, 70), target=(140, 70), elevation=.5)
    assert not movement_crosses_wall(walls=[low], origin=(0, 70), target=(140, 70), elevation=2)
    assert line_of_sight_blocked(walls=[elevated], origin=(0, 70, 4), target=(140, 70, 4))
    assert not line_of_sight_blocked(walls=[elevated], origin=(0, 70, 1), target=(140, 70, 1))
    assert line_of_sight_blocked(walls=[low], origin=(0, 70, 0), target=(140, 70, 2), channel="light")


@pytest.mark.parametrize("vertical", [{"bottom": 2, "top": 1}, {"bottom": None, "top": 1}, {"bottom": math.nan, "top": 2}, {"bottom": 0, "top": math.inf}])
def test_invalid_vertical_geometry_and_unauthorized_mutation_are_rejected(db, vertical):
    gm, player = seed_user(name="GM"), seed_user(name="Player")
    campaign = seed_campaign(gm); seed_member(campaign, player, "player"); scene = seed_scene(campaign)["id"]
    result = SceneWallService().create(campaign_id=campaign, scene_id=scene, user_id=gm, kind="wall", vertical=vertical, **BASE)
    assert not result.success
    denied = SceneWallService().create(campaign_id=campaign, scene_id=scene, user_id=player, kind="wall", vertical=None, **BASE)
    assert denied.error_key == "lighting.errors.denied"


def test_server_authoritative_player_move_cannot_override_collision(db, monkeypatch):
    gm = seed_user(name="GM"); player=seed_user(name="Player");campaign = seed_campaign(gm);seed_member(campaign,player,"player");scene = seed_scene(campaign)
    token = TokenRepository().create(scene_id=scene["id"], actor_id=None, grid_x=0, grid_y=0)
    wall = SceneWallService().create(campaign_id=campaign, scene_id=scene["id"], user_id=gm, kind="wall",
                                     x1=105, y1=0, x2=105, y2=140, vertical=None)
    assert wall.success
    service=TokenService();monkeypatch.setattr(service,"_can_control_token",lambda **_:True)
    moved = asyncio.run(service.move(campaign_id=campaign, scene_id=scene["id"], token_id=token["id"],
                                     grid_x=2, grid_y=0, user_id=player))
    assert moved.error_key == "tokens.errors.movement_blocked"
    persisted = TokenRepository().get_by_id(token["id"])
    assert (persisted["grid_x"], persisted["grid_y"]) == (0, 0)


def test_gm_can_reposition_a_token_through_a_wall(db):
    gm=seed_user(name="GM");campaign=seed_campaign(gm);scene=seed_scene(campaign)
    token=TokenRepository().create(scene_id=scene["id"],actor_id=None,grid_x=0,grid_y=0)
    assert SceneWallService().create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,kind="wall",
                                     x1=105,y1=0,x2=105,y2=140,vertical=None).success
    moved=asyncio.run(TokenService().move(campaign_id=campaign,scene_id=scene["id"],token_id=token["id"],
                                          grid_x=2,grid_y=0,user_id=gm))
    assert moved.success and (moved.token["grid_x"],moved.token["grid_y"])==(2,0)


def test_player_drag_route_can_go_around_a_wall_without_being_retested_as_a_straight_line(db,monkeypatch):
    gm=seed_user(name="GM");player=seed_user(name="Player");campaign=seed_campaign(gm);seed_member(campaign,player,"player");scene=seed_scene(campaign)
    token=TokenRepository().create(scene_id=scene["id"],actor_id=None,grid_x=0,grid_y=0)
    assert SceneWallService().create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,kind="wall",x1=105,y1=0,x2=105,y2=140,vertical=None).success
    service=TokenService();monkeypatch.setattr(service,"_can_control_token",lambda **_:True)
    routed=asyncio.run(service.move(campaign_id=campaign,scene_id=scene["id"],token_id=token["id"],grid_x=2,grid_y=0,user_id=player,movement_path=[{"grid_x":0,"grid_y":0},{"grid_x":0,"grid_y":2},{"grid_x":2,"grid_y":2},{"grid_x":2,"grid_y":0}]))
    assert routed.success and (routed.token["grid_x"],routed.token["grid_y"])==(2,0)


def test_player_collision_uses_the_same_scaled_grid_as_the_browser(db,monkeypatch):
    gm=seed_user(name="GM");player=seed_user(name="Player");campaign=seed_campaign(gm);seed_member(campaign,player,"player");scene=seed_scene(campaign)
    with engine_begin() as conn:conn.execute(update(scenes).where(scenes.c.id==scene["id"]).values(image_scale=2.0))
    token=TokenRepository().create(scene_id=scene["id"],actor_id=None,grid_x=0,grid_y=0)
    # At scale 2 the token travels from world x=70 to x=210. This wall is behind it;
    # testing with the unscaled 70px grid would incorrectly report a collision.
    assert SceneWallService().create(campaign_id=campaign,scene_id=scene["id"],user_id=gm,kind="wall",x1=50,y1=0,x2=50,y2=280,vertical=None).success
    service=TokenService();monkeypatch.setattr(service,"_can_control_token",lambda **_:True)
    moved=asyncio.run(service.move(campaign_id=campaign,scene_id=scene["id"],token_id=token["id"],grid_x=1,grid_y=0,user_id=player,movement_path=[{"grid_x":0,"grid_y":0},{"grid_x":1,"grid_y":0}]))
    assert moved.success
