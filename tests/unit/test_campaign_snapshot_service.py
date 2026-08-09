from __future__ import annotations

from sqlalchemy import select, update

from app.business.campaigns.campaign_snapshot_service import CampaignSnapshotService
from app.config import config
from app.persistence.database import engine_begin
from app.persistence.tables import campaign_snapshots, campaigns, scenes
from tests.conftest import seed_campaign, seed_scene, seed_user


def _setup():
    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id, name="Dungeon")
    return CampaignSnapshotService(), gm_id, campaign_id, scene["id"]


def test_create_snapshot_has_versioned_manifest_and_checksum(db):
    service, gm_id, campaign_id, _ = _setup()
    result = service.create(campaign_id=campaign_id, user_id=gm_id, name="Before session")

    assert result.success
    assert len(result.snapshot["checksum"]) == 64
    stored = service.repository.get(result.snapshot["id"])
    assert stored["format_version"] == 1
    assert '"gravewright.campaign-snapshot"' in stored["manifest_json"]
    assert "members" in stored["manifest_json"]


def test_restore_recovers_state_and_creates_safety_snapshot(db):
    service, gm_id, campaign_id, scene_id = _setup()
    created = service.create(campaign_id=campaign_id, user_id=gm_id, name="Known good")
    with engine_begin() as connection:
        connection.execute(
            update(campaigns)
            .where(campaigns.c.id == campaign_id)
            .values(description="changed", persistent_state_json='{"changed":true}')
        )
        connection.execute(
            update(scenes)
            .where(scenes.c.id == scene_id)
            .values(board_area_markers_json='[{"x":1}]', fog_enabled=1)
        )

    preview = service.preview(
        snapshot_id=created.snapshot["id"], campaign_id=campaign_id, user_id=gm_id
    )
    restored = service.restore(
        snapshot_id=created.snapshot["id"], campaign_id=campaign_id, user_id=gm_id
    )

    assert preview.success and preview.preview["safety_snapshot"] is True
    assert restored.success and restored.preview["scenes_restored"] == 1
    with engine_begin() as connection:
        campaign = connection.execute(
            select(campaigns).where(campaigns.c.id == campaign_id)
        ).mappings().one()
        scene = connection.execute(select(scenes).where(scenes.c.id == scene_id)).mappings().one()
        snapshots = list(
            connection.execute(
                select(campaign_snapshots).where(
                    campaign_snapshots.c.campaign_id == campaign_id
                )
            ).mappings()
        )
    assert campaign["description"] == ""
    assert scene["board_area_markers_json"] == "[]"
    assert scene["fog_enabled"] == 0
    assert {row["kind"] for row in snapshots} == {"manual", "safety"}


def test_invalid_checksum_and_non_gm_are_rejected(db):
    service, gm_id, campaign_id, _ = _setup()
    outsider_id = seed_user(name="Outsider")
    created = service.create(campaign_id=campaign_id, user_id=gm_id, name="Safe")
    with engine_begin() as connection:
        connection.execute(
            update(campaign_snapshots)
            .where(campaign_snapshots.c.id == created.snapshot["id"])
            .values(payload_json="{}")
        )

    corrupt = service.preview(
        snapshot_id=created.snapshot["id"], campaign_id=campaign_id, user_id=gm_id
    )
    denied = service.create(campaign_id=campaign_id, user_id=outsider_id, name="No access")
    assert corrupt.error_key == "campaign.snapshot.errors.checksum"
    assert denied.error_key == "campaign.snapshot.errors.denied"


def test_restore_does_not_remove_scenes_created_after_snapshot(db):
    service, gm_id, campaign_id, _ = _setup()
    created = service.create(campaign_id=campaign_id, user_id=gm_id, name="Initial")
    later = seed_scene(campaign_id, name="Later")
    result = service.restore(
        snapshot_id=created.snapshot["id"], campaign_id=campaign_id, user_id=gm_id
    )
    assert result.success
    with engine_begin() as connection:
        assert connection.execute(
            select(scenes.c.id).where(scenes.c.id == later["id"])
        ).scalar_one() == later["id"]


def test_snapshot_retention_prunes_oldest_entries(db):
    service, gm_id, campaign_id, _ = _setup()
    original = config.campaign_snapshot_retention
    object.__setattr__(config, "campaign_snapshot_retention", 2)
    try:
        for name in ("First", "Second", "Third"):
            assert service.create(
                campaign_id=campaign_id, user_id=gm_id, name=name
            ).success
    finally:
        object.__setattr__(config, "campaign_snapshot_retention", original)
    rows = service.repository.list_for_campaign(campaign_id)
    assert len(rows) == 2
    assert {row["name"] for row in rows} == {"Second", "Third"}
