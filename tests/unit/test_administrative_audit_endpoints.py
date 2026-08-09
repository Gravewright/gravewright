from __future__ import annotations

from litestar.testing import TestClient

from app.business.audit import AuditService
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_user


def _record(campaign_id: str, gm_id: str) -> None:
    AuditService().record(
        campaign_id=campaign_id,
        actor_user_id=gm_id,
        event_type="snapshot.created",
        subject_type="snapshot",
        subject_id="snapshot-id",
        action="create",
        result="success",
        metadata={"kind": "manual", "format_version": 1},
    )


def test_gm_can_list_filter_and_export_audit(db):
    from main import app

    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    _record(campaign_id, gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        listed = client.get(
            "/campaigns/audit",
            params={"campaign_id": campaign_id, "event_type": "snapshot.created"},
            headers={"Accept": "application/json"},
        )
        exported = client.get(
            "/campaigns/audit/export",
            params={"campaign_id": campaign_id},
        )

    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 1
    assert listed.json()["events"][0]["metadata"] == {
        "format_version": 1,
        "kind": "manual",
    }
    assert exported.status_code == 200
    assert exported.headers["cache-control"] == "no-store"
    assert exported.headers["content-disposition"].startswith("attachment;")
    assert exported.json()["format"] == "gravewright.audit-export"


def test_non_gm_cannot_read_or_export_audit(db):
    from main import app

    gm_id = seed_user(name="GM")
    outsider_id = seed_user(name="Outsider")
    campaign_id = seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, outsider_id)
        listed = client.get(
            "/campaigns/audit",
            params={"campaign_id": campaign_id},
            headers={"Accept": "application/json"},
        )
        exported = client.get(
            "/campaigns/audit/export",
            params={"campaign_id": campaign_id},
            headers={"Accept": "application/json"},
        )
    assert listed.status_code == 403
    assert exported.status_code == 403


def test_inside_audit_panel_is_gm_only(db):
    from main import app

    gm_id = seed_user(name="GM")
    outsider_id = seed_user(name="Outsider")
    seed_campaign(gm_id)
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        gm_page = client.get("/inside")
        login(client, outsider_id)
        outsider_page = client.get("/inside")
    assert "data-audit-panel" in gm_page.text
    assert "data-audit-panel" not in outsider_page.text


def test_audit_javascript_uses_text_only_rendering():
    from pathlib import Path

    source = Path("static/js/inside/audit-log.js").read_text(encoding="utf-8")
    assert "textContent" in source
    assert "innerHTML" not in source
