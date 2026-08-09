from __future__ import annotations

from importlib import import_module
from types import SimpleNamespace

from litestar.testing import TestClient

from app.persistence.repositories.actor_repository import ActorRepository
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_user


def test_search_endpoint_returns_normalized_results(db):
    from main import app

    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    actor_id = ActorRepository().create(
        campaign_id=campaign_id,
        system_id="test",
        actor_type="npc",
        name="Crimson Seer",
        created_by_user_id=gm_id,
    )
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        response = client.get(
            "/game/search",
            params={"campaign_id": campaign_id, "q": "crimson"},
            headers={"Accept": "application/json"},
        )
    assert response.status_code == 200
    assert response.json()["results"][0]["id"] == actor_id
    assert response.json()["results"][0]["target"] == {
        "action": "open_actor",
        "id": actor_id,
    }


def test_search_endpoint_denies_other_campaign(db):
    from main import app

    owner_id = seed_user(name="Owner")
    outsider_id = seed_user(name="Outsider")
    campaign_id = seed_campaign(owner_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, outsider_id)
        response = client.get(
            "/game/search",
            params={"campaign_id": campaign_id, "q": "anything"},
            headers={"Accept": "application/json"},
        )
    assert response.status_code == 403
    assert response.json()["error_key"] == "search.errors.denied"


def test_search_endpoint_is_hidden_when_flag_is_disabled(db, monkeypatch):
    from main import app

    actions = import_module("app.actions.game.global_search")
    monkeypatch.setattr(actions, "config", SimpleNamespace(command_palette_enabled=False))
    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        response = client.get("/game/search", params={"campaign_id": campaign_id, "q": "anything"})
    assert response.status_code == 404
