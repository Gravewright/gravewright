from __future__ import annotations

from litestar.testing import TestClient

from app.config import config
from app.persistence.database import engine_begin
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_user


def test_gm_can_preview_and_clone_campaign(db):
    from main import app

    gm_id = seed_user(name="GM")
    source_id = seed_campaign(gm_id, title="Original")
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, gm_id)
        form = {
            "csrf_token": csrf,
            "source_campaign_id": source_id,
            "title": "Original Copy",
            "actors": "true",
            "journals": "true",
        }
        preview = client.post(
            "/campaigns/clone/preview", data=form, headers={"Accept": "application/json"}
        )
        cloned = client.post(
            "/campaigns/clone", data=form, headers={"Accept": "application/json"}
        )

    assert preview.status_code == 200, preview.text
    assert preview.json()["summary"]["source_campaign_id"] == source_id
    assert cloned.status_code == 200, cloned.text
    target_id = cloned.json()["campaign_id"]
    assert target_id != source_id
    with engine_begin() as connection:
        title = connection.exec_driver_sql(
            "SELECT title FROM campaigns WHERE id = ?", (target_id,)
        ).scalar_one()
    assert title == "Original Copy"


def test_non_gm_cannot_clone_campaign(db):
    from main import app

    gm_id = seed_user(name="GM")
    outsider_id = seed_user(name="Outsider")
    source_id = seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, outsider_id)
        response = client.post(
            "/campaigns/clone",
            data={"csrf_token": csrf, "source_campaign_id": source_id, "title": "Copy"},
            headers={"Accept": "application/json"},
        )
    assert response.status_code == 403
    assert response.json()["error_key"] == "campaign.clone.errors.denied"


def test_clone_routes_can_be_disabled(db):
    from main import app

    gm_id = seed_user(name="GM")
    source_id = seed_campaign(gm_id)
    object.__setattr__(config, "campaign_clone_enabled", False)
    try:
        with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
            csrf = login(client, gm_id)
            response = client.post(
                "/campaigns/clone/preview",
                data={"csrf_token": csrf, "source_campaign_id": source_id},
                headers={"Accept": "application/json"},
            )
    finally:
        object.__setattr__(config, "campaign_clone_enabled", True)
    assert response.status_code == 404


def test_inside_clone_wizard_is_gm_only(db):
    from main import app

    gm_id = seed_user(name="GM")
    outsider_id = seed_user(name="Outsider")
    seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        gm_page = client.get("/inside")
        login(client, outsider_id)
        outsider_page = client.get("/inside")

    assert 'data-campaign-clone-form' in gm_page.text
    assert 'data-campaign-clone-form' not in outsider_page.text
