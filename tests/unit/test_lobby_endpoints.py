from __future__ import annotations

from litestar.testing import TestClient

from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_user


def test_member_updates_and_reads_lobby(db):
    from main import app

    gm_id = seed_user(name="GM")
    player_id = seed_user(name="Player")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, "player")
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, player_id)
        updated = client.post("/game/lobby/state", json={
            "campaign_id": campaign_id, "is_ready": True,
            "selected_actor_id": None, "assets_state": "ready",
        })
        snapshot = client.get("/game/lobby", params={"campaign_id": campaign_id})
    assert updated.status_code == 200, updated.text
    assert snapshot.status_code == 200
    member = next(row for row in snapshot.json()["members"] if row["user_id"] == player_id)
    assert member["is_ready"] is True and member["assets_state"] == "ready"
    assert snapshot.json()["summary"] == {"ready": 1, "total": 2}


def test_outsider_is_denied_lobby_snapshot(db):
    from main import app

    gm_id = seed_user(name="GM")
    outsider_id = seed_user(name="Outsider")
    campaign_id = seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, outsider_id)
        response = client.get("/game/lobby", params={"campaign_id": campaign_id})
    assert response.status_code == 403
    assert response.json()["error_key"] == "lobby.errors.denied"
