from litestar.testing import TestClient

from tests.conftest import TEST_SESSION_CONFIG, login, seed_user


def test_inside_renders_systems_tab(db):
    from main import app

    user_id = seed_user(name="Owner", email="owner-render-systems@test.com")

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, user_id)
        resp = client.get("/inside", follow_redirects=False)

    assert resp.status_code == 200
    assert "dnd5e" in resp.text
    assert "system-card-grid" in resp.text
    assert "data-inside-modal-open" in resp.text
