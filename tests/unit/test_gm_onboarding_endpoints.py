from __future__ import annotations

from litestar.testing import TestClient

from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_user


def test_gm_reads_and_dismisses_onboarding(db):
    from main import app

    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        initial = client.get("/game/onboarding", params={"campaign_id": campaign_id})
        dismissed = client.post("/game/onboarding/preference", json={
            "campaign_id": campaign_id, "dismissed": True,
        })
    assert initial.status_code == 200
    assert initial.json()["state"]["completed"] == 1
    assert dismissed.status_code == 200
    assert dismissed.json()["state"]["dismissed"] is True


def test_player_cannot_manage_gm_onboarding(db):
    from main import app

    gm_id = seed_user(name="GM")
    player_id = seed_user(name="Player")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, "player")
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, player_id)
        response = client.post("/game/onboarding/preference", json={
            "campaign_id": campaign_id, "dismissed": True,
        })
    assert response.status_code == 403
    assert response.json()["error_key"] == "onboarding.errors.denied"
