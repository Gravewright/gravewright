from __future__ import annotations

import io
import json
import time
import uuid
import zipfile

from sqlalchemy import insert

from app.business.campaigns.campaign_export_service import (
    CampaignExportOptions, CampaignExportService,
)
from app.persistence.database import engine_begin
from app.persistence.tables import actors_core
from tests.conftest import seed_campaign, seed_user


def test_export_is_versioned_selective_and_contains_no_account_secrets(db):
    email = "gm-secret@example.test"
    gm_id = seed_user(name="GM", email=email)
    campaign_id = seed_campaign(gm_id, title="Safe Campaign")
    actor_id = uuid.uuid4().hex
    now = int(time.time())
    with engine_begin() as connection:
        connection.execute(insert(actors_core).values(
            id=actor_id, campaign_id=campaign_id, system_id="core", type="character",
            name="Hero", folder_id=None, portrait_asset_id=None, token_asset_id=None,
            default_token_config_json=None, permissions_json="{}", external_data_ref=None,
            status="active", version=1, created_by_user_id=gm_id,
            created_at=now, updated_at=now,
        ))
    service = CampaignExportService()
    result = service.export(
        campaign_id=campaign_id, user_id=gm_id,
        options=CampaignExportOptions(
            packages=False, scenes=False, actors=True, items=False,
            journals=False, settings=False,
        ),
    )
    assert result.success and result.archive and service.validate(result.archive)
    assert result.filename.endswith(".gwcampaign")
    with zipfile.ZipFile(io.BytesIO(result.archive)) as archive:
        assert set(archive.namelist()) == {"manifest.json", "campaign.json"}
        manifest = json.loads(archive.read("manifest.json"))
        payload_bytes = archive.read("campaign.json")
        payload = json.loads(payload_bytes)
    assert manifest["version"] == 1 and manifest["selected"] == ["actors"]
    assert list(payload["content"]) == ["actor_folders", "actors_core"]
    serialized = result.archive.decode("latin1", errors="ignore")
    assert email not in serialized and gm_id not in json.dumps(payload)
    assert "created_by_user_id" not in json.dumps(payload)


def test_export_rejects_non_gm_and_tampered_archive(db):
    gm_id = seed_user(name="GM")
    outsider_id = seed_user(name="Outsider")
    campaign_id = seed_campaign(gm_id)
    service = CampaignExportService()
    denied = service.export(
        campaign_id=campaign_id, user_id=outsider_id, options=CampaignExportOptions()
    )
    assert denied.error_key == "campaign.export.errors.denied"
    valid = service.export(
        campaign_id=campaign_id, user_id=gm_id, options=CampaignExportOptions()
    )
    assert valid.archive
    with zipfile.ZipFile(io.BytesIO(valid.archive)) as source:
        manifest = source.read("manifest.json")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as changed:
        changed.writestr("manifest.json", manifest)
        changed.writestr("campaign.json", b"{}")
    assert not service.validate(output.getvalue())
