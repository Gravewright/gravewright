from __future__ import annotations

from pathlib import Path

from litestar.testing import TestClient
from sqlalchemy import select

from app.business.campaigns.campaign_export_service import (
    CampaignExportOptions,
    CampaignExportService,
)
from app.business.campaigns.campaign_import_service import CampaignImportService
from app.persistence.database import engine_connect
from app.persistence.tables import campaign_members, campaigns
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_user


def test_export_can_be_imported_as_new_owned_campaign(db):
    gm_id = seed_user(name="GM")
    source_id = seed_campaign(gm_id, title="Portable Table")
    exported = CampaignExportService().export(
        campaign_id=source_id, user_id=gm_id, options=CampaignExportOptions()
    )
    assert exported.archive

    result = CampaignImportService().import_archive(
        archive=exported.archive, user_id=gm_id, title="Imported Table"
    )

    assert result.success and result.campaign_id != source_id
    with engine_connect() as connection:
        campaign = connection.execute(
            select(campaigns).where(campaigns.c.id == result.campaign_id)
        ).mappings().one()
        membership = connection.execute(
            select(campaign_members).where(
                campaign_members.c.campaign_id == result.campaign_id,
                campaign_members.c.user_id == gm_id,
            )
        ).mappings().one()
    assert campaign["title"] == "Imported Table"
    assert campaign["owner_user_id"] == gm_id
    assert membership["role"] == "gm"


def test_import_endpoint_accepts_gwcampaign(db):
    from main import app

    gm_id = seed_user(name="GM")
    source_id = seed_campaign(gm_id, title="Endpoint Export")
    exported = CampaignExportService().export(
        campaign_id=source_id, user_id=gm_id, options=CampaignExportOptions()
    )
    assert exported.archive
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        csrf = login(client, gm_id)
        response = client.post(
            "/campaigns/import",
            data={"csrf_token": csrf, "title": "Endpoint Import"},
            files={"campaign_file": ("table.gwcampaign", exported.archive, "application/zip")},
            headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
        )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["message_key"] == "campaign.import.created"
    assert response.json()["campaign_id"]


def test_import_endpoint_has_no_request_body_size_limit():
    from main import app

    route = next(
        route
        for route in app.routes
        if getattr(route, "path", None) == "/campaigns/import"
    )
    handler = next(iter(route.route_handler_map.values()))[0]

    assert handler.resolve_request_max_body_size() is None


def test_import_rejects_corrupt_archive(db):
    gm_id = seed_user(name="GM")
    result = CampaignImportService().import_archive(
        archive=b"not-a-zip", user_id=gm_id
    )
    assert not result.success
    assert result.error_key == "campaign.import.errors.invalid"


def test_inside_ajax_does_not_intercept_download_or_snapshots():
    source = Path("static/js/inside/inside-ajax.js").read_text(encoding="utf-8")
    snapshots = Path("static/js/inside/campaign-snapshots.js").read_text(encoding="utf-8")
    assert ".campaign-export-form" in source
    assert ".campaign-import-form" in source
    assert "[data-campaign-clone-form]" in source
    assert ".campaign-snapshot-create" in source
    assert 'Accept: "application/json"' in snapshots
    assert "new URLSearchParams(new FormData(form))" in snapshots
    assert 'document.addEventListener("submit"' in snapshots
    transfers = Path("static/js/inside/campaign-transfer.js").read_text(encoding="utf-8")
    clone = Path("static/js/inside/campaign-clone.js").read_text(encoding="utf-8")
    assert "URL.createObjectURL" in transfers
    assert "new URLSearchParams(new FormData(form))" in transfers
    assert 'Accept: "application/json"' in transfers
    assert 'document.addEventListener("submit"' in clone
