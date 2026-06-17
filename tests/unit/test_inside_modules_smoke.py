from litestar.testing import TestClient

from tests.conftest import TEST_SESSION_CONFIG, login, seed_user


def test_inside_renders_addons_tab(db):
    from main import app

    user_id = seed_user(name="Owner", email="owner-render-modules@test.com")

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, user_id)
        resp = client.get("/inside", follow_redirects=False)

    assert resp.status_code == 200
    # The Add-ons tab renders through the SDK package surface with no bundled
    # packages installed, and no legacy /modules routes remain. Per-package card
    # markers (module-card-grid, package-kind-badge, /sdk/packages/install) only
    # appear once packages exist, so they are not asserted here.
    assert "Add-ons" in resp.text
    assert "/modules/install" not in resp.text
    assert "inside-ajax.js" in resp.text
    assert "data-inside-modal-open" in resp.text
