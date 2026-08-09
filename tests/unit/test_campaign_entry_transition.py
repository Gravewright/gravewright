from __future__ import annotations

from dataclasses import replace
from importlib import import_module
from types import SimpleNamespace

from litestar.testing import TestClient

from app.business.campaigns.campaign_invitation_service import CampaignInvitationService
from app.config import config
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_user


def test_transition_flags_default_to_primary_code_and_legacy_compatibility():
    assert config.campaign_join_code_enabled is True
    assert config.campaign_email_invitation_creation_enabled is True


def test_join_code_routes_return_not_found_when_feature_is_disabled(db, monkeypatch):
    from main import app

    join_actions = import_module("app.actions.campaign_join_codes")
    monkeypatch.setattr(join_actions, "config", SimpleNamespace(campaign_join_code_enabled=False))
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        response = client.get("/join/ABCD-EFGH-JK23", follow_redirects=False)
    assert response.status_code == 404


def test_disabling_legacy_creation_does_not_block_pending_acceptance(db, monkeypatch):
    from main import app

    gm_id = seed_user(name="GM", email="transition-gm@test.com")
    player_email = "transition-player@test.com"
    player_id = seed_user(name="Player", email=player_email)
    campaign_id = seed_campaign(gm_id)
    created = CampaignInvitationService().create_invitation(
        campaign_id=campaign_id,
        invited_by_user_id=gm_id,
        invited_email=player_email,
        role="player",
    )
    assert created.success
    invitation_id = CampaignInvitationService().list_pending_for_user(player_id)[0]["id"]

    invitation_actions = import_module("app.actions.game.invite_to_campaign")
    monkeypatch.setattr(
        invitation_actions,
        "config",
        SimpleNamespace(campaign_email_invitation_creation_enabled=False),
    )
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, gm_id)
        blocked = client.post(
            "/campaigns/invitations",
            data={
                "csrf_token": csrf,
                "campaign_id": campaign_id,
                "email": "another@test.com",
                "role": "player",
            },
            headers={"Accept": "application/json"},
        )
        assert blocked.status_code == 404

        csrf = login(client, player_id)
        accepted = client.post(
            "/campaigns/invitations/accept",
            data={"csrf_token": csrf, "invitation_id": invitation_id},
            headers={"Accept": "application/json"},
        )
    assert accepted.status_code == 200
    assert accepted.json()["membership_created"] is True


def test_disabled_join_code_flag_hides_gm_and_player_interfaces(db, monkeypatch):
    from main import app

    disabled = replace(config, campaign_join_code_enabled=False)
    monkeypatch.setattr(import_module("app.actions.game.show_game"), "config", disabled)
    monkeypatch.setattr(import_module("app.actions.inside.show_inside"), "config", disabled)
    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        game = client.get(f"/game?room={campaign_id}")
        inside = client.get("/inside")
    assert game.status_code == 200
    assert f'data-modal-id="join-code-{campaign_id}"' not in game.text
    assert "data-inside-join-code-form" not in inside.text
