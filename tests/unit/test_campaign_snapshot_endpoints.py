from __future__ import annotations

from litestar.testing import TestClient

from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_user


def test_gm_create_list_preview_restore_and_delete_snapshot(db):
    from main import app

    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, gm_id)
        created = client.post(
            "/campaigns/snapshots",
            data={"csrf_token": csrf, "campaign_id": campaign_id, "name": "Session zero"},
            headers={"Accept": "application/json"},
        )
        assert created.status_code == 200, created.text
        snapshot_id = created.json()["snapshot"]["id"]

        listed = client.get(
            "/campaigns/snapshots",
            params={"campaign_id": campaign_id},
            headers={"Accept": "application/json"},
        )
        preview = client.post(
            "/campaigns/snapshots/preview",
            data={"csrf_token": csrf, "campaign_id": campaign_id, "snapshot_id": snapshot_id},
            headers={"Accept": "application/json"},
        )
        restore = client.post(
            "/campaigns/snapshots/restore",
            data={"csrf_token": csrf, "campaign_id": campaign_id, "snapshot_id": snapshot_id, "confirm": "RESTORE"},
            headers={"Accept": "application/json"},
        )
        deleted = client.post(
            "/campaigns/snapshots/delete",
            data={"csrf_token": csrf, "campaign_id": campaign_id, "snapshot_id": snapshot_id, "confirm": "DELETE"},
            headers={"Accept": "application/json"},
        )

    assert listed.status_code == 200 and len(listed.json()["snapshots"]) == 1
    assert preview.status_code == 200 and preview.json()["preview"]["safety_snapshot"]
    assert restore.status_code == 200 and restore.json()["result"]["safety_snapshot_id"]
    assert deleted.status_code == 200


def test_snapshot_restore_requires_strong_confirmation(db):
    from main import app

    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, gm_id)
        response = client.post(
            "/campaigns/snapshots/restore",
            data={"csrf_token": csrf, "campaign_id": campaign_id, "snapshot_id": "x", "confirm": "yes"},
            headers={"Accept": "application/json"},
        )
    assert response.status_code == 400
    assert response.json()["error_key"] == "campaign.snapshot.errors.confirmation"


def test_non_gm_cannot_list_snapshots(db):
    from main import app

    gm_id = seed_user(name="GM")
    outsider_id = seed_user(name="Outsider")
    campaign_id = seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, outsider_id)
        response = client.get(
            "/campaigns/snapshots",
            params={"campaign_id": campaign_id},
            headers={"Accept": "application/json"},
        )
    assert response.status_code == 403


def test_inside_renders_snapshot_panel_only_for_gm(db):
    from main import app

    gm_id = seed_user(name="GM")
    outsider_id = seed_user(name="Outsider")
    seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        gm_page = client.get("/inside")
        login(client, outsider_id)
        outsider_page = client.get("/inside")
    assert 'action="/campaigns/snapshots"' in gm_page.text
    assert 'action="/campaigns/snapshots"' not in outsider_page.text
