from __future__ import annotations

import time
import uuid

from sqlalchemy import insert, update

from app.business.lobby import LobbyService
from app.persistence.database import engine_begin
from app.persistence.repositories.presence_repository import PresenceRepository
from app.persistence.tables import actor_owners, actors_core, campaign_presence
from tests.conftest import seed_campaign, seed_member, seed_user


def _setup():
    gm_id = seed_user(name="GM")
    player_id = seed_user(name="Player")
    other_id = seed_user(name="Other")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, "player")
    seed_member(campaign_id, other_id, "player")
    actor_id = uuid.uuid4().hex
    now = int(time.time())
    with engine_begin() as connection:
        connection.execute(insert(actors_core).values(
            id=actor_id, campaign_id=campaign_id, system_id="core", type="character",
            name="Hero", folder_id=None, portrait_asset_id=None, token_asset_id=None,
            default_token_config_json=None, permissions_json="{}", external_data_ref=None,
            status="active", version=1, created_by_user_id=gm_id,
            created_at=now, updated_at=now,
        ))
        connection.execute(insert(actor_owners).values(actor_id=actor_id, user_id=player_id))
    return gm_id, player_id, other_id, campaign_id, actor_id


def test_ready_update_is_idempotent_and_actor_is_owner_scoped(db):
    _, player_id, other_id, campaign_id, actor_id = _setup()
    service = LobbyService()
    first = service.update(
        campaign_id=campaign_id, user_id=player_id, is_ready=True,
        selected_actor_id=actor_id, assets_state="ready",
    )
    second = service.update(
        campaign_id=campaign_id, user_id=player_id, is_ready=True,
        selected_actor_id=actor_id, assets_state="ready",
    )
    denied = service.update(
        campaign_id=campaign_id, user_id=other_id, is_ready=True,
        selected_actor_id=actor_id, assets_state="ready",
    )
    assert first.success and second.success
    assert denied.error_key == "lobby.errors.invalid_actor"
    snapshot = service.snapshot(campaign_id=campaign_id, user_id=player_id)
    player = next(row for row in snapshot.members if row["user_id"] == player_id)
    assert player["is_ready"] and player["selected_actor_name"] == "Hero"
    assert snapshot.actors == [{"id": actor_id, "name": "Hero"}]


def test_snapshot_expires_stale_presence(db):
    _, player_id, _, campaign_id, _ = _setup()
    presence = PresenceRepository()
    presence.touch_user_rooms(user_id=player_id, room_ids=[campaign_id], threshold_seconds=12)
    with engine_begin() as connection:
        connection.execute(update(campaign_presence).where(
            campaign_presence.c.campaign_id == campaign_id,
            campaign_presence.c.user_id == player_id,
        ).values(last_seen_at=int(time.time()) - 30))
    snapshot = LobbyService().snapshot(campaign_id=campaign_id, user_id=player_id)
    player = next(row for row in snapshot.members if row["user_id"] == player_id)
    assert player["is_online"] is False


def test_outsider_cannot_read_or_update_lobby(db):
    _, _, _, campaign_id, _ = _setup()
    outsider = seed_user(name="Outsider")
    service = LobbyService()
    assert service.snapshot(campaign_id=campaign_id, user_id=outsider).error_key == "lobby.errors.denied"
    assert service.update(
        campaign_id=campaign_id, user_id=outsider, is_ready=True,
        selected_actor_id=None, assets_state="ready",
    ).error_key == "lobby.errors.denied"
