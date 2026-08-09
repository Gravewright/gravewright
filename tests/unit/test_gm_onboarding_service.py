from __future__ import annotations

import time
import uuid

from sqlalchemy import insert, update

from app.business.onboarding import GmOnboardingService
from app.persistence.database import engine_begin
from app.persistence.tables import actors_core, campaign_join_codes, campaigns, scenes
from tests.conftest import seed_campaign, seed_member, seed_user


def test_progress_is_server_calculated_and_dismissal_is_persistent(db):
    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    service = GmOnboardingService()

    initial = service.get(campaign_id=campaign_id, user_id=gm_id)
    assert initial.success
    assert initial.state["steps"] == {
        "campaign": True, "system": False, "character": False, "scene": False, "code": False,
    }
    assert initial.state["completed"] == 1

    dismissed = service.set_dismissed(campaign_id=campaign_id, user_id=gm_id, dismissed=True)
    assert dismissed.success and dismissed.state["dismissed"] is True
    assert GmOnboardingService().get(
        campaign_id=campaign_id, user_id=gm_id
    ).state["dismissed"] is True


def test_progress_detects_system_actor_scene_and_usable_code(db):
    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    now = int(time.time())
    with engine_begin() as connection:
        connection.execute(update(campaigns).where(campaigns.c.id == campaign_id).values(active_system_id="core"))
        connection.execute(insert(actors_core).values(
            id=uuid.uuid4().hex, campaign_id=campaign_id, system_id="core", type="character",
            name="Hero", folder_id=None, portrait_asset_id=None, token_asset_id=None,
            default_token_config_json=None, permissions_json="{}", external_data_ref=None,
            status="active", version=1, created_by_user_id=gm_id, created_at=now, updated_at=now,
        ))
        connection.execute(insert(scenes).values(
            id=uuid.uuid4().hex, campaign_id=campaign_id, group_id=None, name="Start",
            status="draft", visibility="players", active=0, width=1000, height=1000,
            tile_size=100, chunk_size=10, grid_visible=1, grid_color="#fff", grid_opacity=.4,
            image_scale=1.0, start_world_x=0.0, start_world_y=0.0, start_zoom=1.0,
            tile_table_version=1, scene_epoch=1, fog_enabled=0, fog_mask=None,
            fog_baseline="hide_all", fog_ops_json="[]", fog_version=0,
            board_area_markers_json="[]", board_version=1, created_at=now, updated_at=now,
        ))
        connection.execute(insert(campaign_join_codes).values(
            id=uuid.uuid4().hex, campaign_id=campaign_id, code_hash=uuid.uuid4().hex,
            created_by_user_id=gm_id, role="player", max_uses=2, use_count=1,
            expires_at=now + 3600, revoked_at=None, last_used_at=None,
            created_at=now, updated_at=now,
        ))
    state = GmOnboardingService().get(campaign_id=campaign_id, user_id=gm_id).state
    assert all(state["steps"].values())
    assert state["completed"] == state["total"] == 5
    assert state["finished"] is True


def test_only_campaign_gm_can_read_or_dismiss(db):
    gm_id = seed_user(name="GM")
    player_id = seed_user(name="Player")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, "player")
    service = GmOnboardingService()
    assert service.get(campaign_id=campaign_id, user_id=player_id).error_key == "onboarding.errors.denied"
    assert service.set_dismissed(
        campaign_id=campaign_id, user_id=player_id, dismissed=True
    ).error_key == "onboarding.errors.denied"
