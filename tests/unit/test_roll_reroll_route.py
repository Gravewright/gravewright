from litestar.testing import TestClient

from main import app
from tests.conftest import TEST_SESSION_CONFIG, login, seed_user


def test_reroll_route_receives_its_service_from_dependency_injection(db):
    user_id = seed_user()
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, user_id)
        response = client.post(
            "/game/roll/reroll",
            json={"campaign_id": "missing", "message_id": "missing"},
        )

    assert response.status_code == 400
    assert response.json()["error_key"] == "game.rolls.reroll.invalid"
