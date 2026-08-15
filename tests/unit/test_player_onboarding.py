from __future__ import annotations

from litestar.testing import TestClient

from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_user


def test_player_claims_interface_introduction_once_per_campaign(db):
    from main import app

    gm_id = seed_user(name="GM")
    player_id = seed_user(name="Player")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, "player")

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, player_id)
        first = client.post(
            "/game/player-onboarding/claim", json={"campaign_id": campaign_id}
        )
        second = client.post(
            "/game/player-onboarding/claim", json={"campaign_id": campaign_id}
        )

    assert first.status_code == 200
    assert first.json() == {"ok": True, "show": True}
    assert second.status_code == 200
    assert second.json() == {"ok": True, "show": False}


def test_gm_cannot_claim_player_interface_introduction(db):
    from main import app

    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        response = client.post(
            "/game/player-onboarding/claim", json={"campaign_id": campaign_id}
        )

    assert response.status_code == 403
    assert response.json()["error_key"] == "onboarding.errors.denied"


def test_non_member_cannot_claim_player_interface_introduction(db):
    from main import app

    gm_id = seed_user(name="GM")
    stranger_id = seed_user(name="Stranger")
    campaign_id = seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, stranger_id)
        response = client.post(
            "/game/player-onboarding/claim", json={"campaign_id": campaign_id}
        )

    assert response.status_code == 404
