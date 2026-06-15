from litestar.testing import TestClient

from tests.conftest import TEST_SESSION_CONFIG, login, seed_user


def test_inside_renders_modules_tab(db):
    from main import app

    user_id = seed_user(name="Owner", email="owner-render-modules@test.com")

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, user_id)
        resp = client.get("/inside", follow_redirects=False)

    assert resp.status_code == 200
    assert "Add-ons" in resp.text
    # The bundled dice addon (a non-ruleset package) is listed under Add-ons with
    # an SDK install action and a kind marker — no legacy /modules routes remain.
    assert "/sdk/packages/install" in resp.text
    assert "/modules/install" not in resp.text
    assert "package-kind-badge" in resp.text
    assert "inside-ajax.js" in resp.text
    assert "module-card-grid" in resp.text
    assert "data-inside-modal-open" in resp.text
