"""Streamer = read-only omniscient viewer (server-authoritative visibility).

These assert the backend truth: a streamer sees everything the GM sees (hidden
tokens, GM-only journal content, every sheet) but holds no write authority, and
only ever sees public chat. The client read-only/fog-toggle layer is separate.
"""

from __future__ import annotations

from app.domain.roles import has_full_view
from app.engine.actors.actor_permissions import can_edit_actor, can_view_actor
from app.engine.tokens.token_service import TokenService
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.token_repository import TokenRepository
from tests.conftest import seed_actor, seed_campaign, seed_member, seed_scene, seed_user


def test_has_full_view_helper():
    assert has_full_view("gm") is True
    assert has_full_view("streamer") is True
    assert has_full_view("player") is False
    assert has_full_view("assistant_gm") is False
    assert has_full_view(None) is False


def test_streamer_sees_hidden_tokens_in_snapshot(db):
    gm_id = seed_user(email="sv-gm@test.com")
    streamer_id = seed_user(email="sv-streamer@test.com")
    player_id = seed_user(email="sv-player@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, streamer_id, "streamer")
    seed_member(campaign_id, player_id, "player")
    scene = seed_scene(campaign_id)
    actor_id = seed_actor(campaign_id, gm_id, name="Hidden Foe")

    tokens = TokenRepository()
    token = tokens.create(scene_id=scene["id"], actor_id=actor_id, grid_x=1, grid_y=1)
    tokens.set_hidden(token_id=token["id"], hidden=True)

    service = TokenService()
    streamer_view = service.get_snapshot(
        campaign_id=campaign_id, scene_id=scene["id"], user_id=streamer_id
    )
    player_view = service.get_snapshot(
        campaign_id=campaign_id, scene_id=scene["id"], user_id=player_id
    )

    assert any(t["token_id"] == token["id"] for t in (streamer_view.tokens or []))
    assert not any(t["token_id"] == token["id"] for t in (player_view.tokens or []))


def test_streamer_can_view_but_not_edit_any_actor(db):
    gm_id = seed_user(email="sv-gm2@test.com")
    streamer_id = seed_user(email="sv-streamer2@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, streamer_id, "streamer")
    actor_id = seed_actor(campaign_id, gm_id, name="GM Secret NPC")

    actor = ActorRepository().get(actor_id)
    streamer_campaign = {"id": campaign_id, "member_role": "streamer"}

    assert can_view_actor(actor=actor, campaign=streamer_campaign, user_id=streamer_id) is True
    assert can_edit_actor(actor=actor, campaign=streamer_campaign, user_id=streamer_id) is False


def test_player_cannot_view_unowned_actor(db):
    gm_id = seed_user(email="sv-gm3@test.com")
    player_id = seed_user(email="sv-player3@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, "player")
    actor_id = seed_actor(campaign_id, gm_id, name="GM Only NPC")

    actor = ActorRepository().get(actor_id)
    player_campaign = {"id": campaign_id, "member_role": "player"}

                                                                          
    assert can_view_actor(actor=actor, campaign=player_campaign, user_id=player_id) is False
