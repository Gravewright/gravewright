from __future__ import annotations

from litestar.testing import TestClient

from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_user


def test_gm_downloads_campaign_package(db):
    from main import app

    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id, title="Export Me")
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, gm_id)
        response = client.post("/campaigns/export", data={
            "csrf_token": csrf, "campaign_id": campaign_id,
            "actors": "true", "journals": "true",
        })
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/zip")
    assert ".gwcampaign" in response.headers["content-disposition"]
    assert response.content.startswith(b"PK")


def test_non_gm_cannot_export_campaign(db):
    from main import app

    gm_id = seed_user(name="GM")
    outsider_id = seed_user(name="Outsider")
    campaign_id = seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, outsider_id)
        response = client.post("/campaigns/export", data={"campaign_id": campaign_id})
    assert response.status_code == 403
    assert response.json()["error_key"] == "campaign.export.errors.denied"
