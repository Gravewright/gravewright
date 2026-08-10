from app.business.game_page_service import GamePageService
from app.persistence.repositories.scene_repository import SceneRepository
from litestar.testing import TestClient
from tests.conftest import (
    TEST_SESSION_CONFIG,
    login,
    seed_campaign,
    seed_member,
    seed_scene,
    seed_user,
)


def _room(context, campaign_id):
    return next(room for room in context.rooms if room["id"] == campaign_id)


def test_gm_navigation_does_not_change_the_loaded_scene(db):
    gm_id = seed_user(name="GM", email="scene-nav-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    loaded = seed_scene(campaign_id, name="Loaded")
    browsing = seed_scene(campaign_id, name="Browsing")
    SceneRepository().set_active_scene(campaign_id=campaign_id, scene_id=loaded["id"])

    room = _room(
        GamePageService().build_context(
            user_id=gm_id, navigated_scene_id=browsing["id"]
        ),
        campaign_id,
    )

    assert room["loaded_scene"]["id"] == loaded["id"]
    assert room["active_scene"]["id"] == browsing["id"]
    assert SceneRepository().get_active_scene(campaign_id)["id"] == loaded["id"]


def test_streamer_can_navigate_but_player_stays_on_the_loaded_scene(db):
    gm_id = seed_user(name="GM", email="scene-nav-owner@test.com")
    streamer_id = seed_user(name="Streamer", email="scene-nav-streamer@test.com")
    player_id = seed_user(name="Player", email="scene-nav-player@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, streamer_id, "streamer")
    seed_member(campaign_id, player_id, "player")
    loaded = seed_scene(campaign_id, name="Loaded")
    browsing = seed_scene(campaign_id, name="Browsing")
    SceneRepository().set_active_scene(campaign_id=campaign_id, scene_id=loaded["id"])

    streamer = _room(
        GamePageService().build_context(
            user_id=streamer_id, navigated_scene_id=browsing["id"]
        ),
        campaign_id,
    )
    player = _room(
        GamePageService().build_context(
            user_id=player_id, navigated_scene_id=browsing["id"]
        ),
        campaign_id,
    )

    assert streamer["active_scene"]["id"] == browsing["id"]
    assert streamer["loaded_scene"]["id"] == loaded["id"]
    assert player["active_scene"]["id"] == loaded["id"]
    assert player["loaded_scene"]["id"] == loaded["id"]


def test_scene_manager_renders_loaded_and_navigating_as_separate_actions(db):
    from main import app

    gm_id = seed_user(name="GM", email="scene-nav-page@test.com")
    campaign_id = seed_campaign(gm_id)
    loaded = seed_scene(campaign_id, name="Loaded")
    browsing = seed_scene(campaign_id, name="Browsing")
    SceneRepository().set_active_scene(campaign_id=campaign_id, scene_id=loaded["id"])

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        response = client.get(
            "/game",
            params={"room": campaign_id, "view_scene": browsing["id"]},
        )

    assert response.status_code == 200
    body = response.text
    assert f'data-scene-id="{browsing["id"]}"' in body
    assert f'data-loaded-scene-id="{loaded["id"]}"' in body
    assert 'data-local-scene-navigation="true"' in body
    assert "Carregada" in body and "Navegando" in body
    assert f"view_scene={loaded['id']}" in body
    assert f"view_scene={browsing['id']}" in body
