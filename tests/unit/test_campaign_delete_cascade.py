from __future__ import annotations

import io
import time
import uuid
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import func
from sqlalchemy import insert
from sqlalchemy import select

from app.business.campaigns.campaign_service import CampaignService
from app.domain.scenes import SCENE_NATIVE_CHUNK_SIZE
from app.engine.actors.actor_asset_service import ActorAssetService
from app.engine.journals.journal_asset_service import JournalAssetService
from app.engine.journals.journal_service import JournalService
from app.engine.scenes.map_upload_service import MapUploadService
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.engine.system_storage.storage_path_resolver import actor_data_path
from app.infrastructure.storage.local_actor_asset_storage import LocalActorAssetStorage
from app.infrastructure.storage.local_chunk_storage import LocalChunkStorage
from app.infrastructure.storage.local_journal_asset_storage import LocalJournalAssetStorage
from app.infrastructure.storage.local_scene_asset_storage import LocalSceneAssetStorage
from app.persistence.database import engine_connect
from app.persistence.database import engine_begin
from app.persistence.tables import actors_core
from app.persistence.tables import campaign_members
from app.persistence.tables import campaigns
from app.persistence.tables import journal_assets
from app.persistence.tables import journals
from app.persistence.tables import module_settings
from app.persistence.tables import modules_installed
from app.persistence.tables import scene_assets
from app.persistence.tables import scene_chunks
from app.persistence.tables import scene_tiles
from app.persistence.tables import scenes
from tests.conftest import seed_actor
from tests.conftest import seed_campaign
from tests.conftest import seed_user


def _png_bytes(width: int = 16, height: int = 16) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (90, 120, 160)).save(buffer, format="PNG")
    return buffer.getvalue()


def _count(table, *, campaign_id: str | None = None) -> int:
    with engine_connect() as conn:
        statement = select(func.count()).select_from(table)
        if campaign_id is not None:
            statement = statement.where(table.c.campaign_id == campaign_id)
        return int(conn.execute(statement).scalar_one())


def _insert_campaign_module_setting(*, campaign_id: str, user_id: str) -> None:
    now = int(time.time())
    module_id = uuid.uuid4().hex
    with engine_begin() as conn:
        conn.execute(
            insert(modules_installed).values(
                id=module_id,
                package_id=f"cascade-test-{module_id}",
                name="Cascade Test",
                version="1.0.0",
                api_version="1",
                package_dir="data/modules/cascade-test",
                manifest_json="{}",
                status="installed",
                validation_errors_json="[]",
                package_sha256=None,
                installed_by_user_id=user_id,
                installed_at=now,
                updated_at=now,
            )
        )
        conn.execute(
            insert(module_settings).values(
                id=uuid.uuid4().hex,
                module_id=module_id,
                scope="campaign",
                subject_id=campaign_id,
                setting_key="enabled",
                value_json="true",
                updated_by_user_id=user_id,
                created_at=now,
                updated_at=now,
            )
        )


@pytest.mark.asyncio
async def test_delete_campaign_cascades_database_and_uploaded_storage(db, tmp_path):
    gm_id = seed_user(name="GM", email="campaign-delete-cascade@test.com")
    campaign_id = seed_campaign(gm_id)
    scene_root = tmp_path / "scenes"
    actor_root = tmp_path / "actor-assets"
    journal_root = tmp_path / "journal-assets"

    map_result = await MapUploadService(
        asset_storage=LocalSceneAssetStorage(root=scene_root),
        chunk_storage=LocalChunkStorage(root=scene_root),
    ).upload_raster_map(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Uploaded Map",
        filename="map.png",
        content_type="image/png",
        data=_png_bytes(140, 140),
        tile_size=70,
        chunk_size=SCENE_NATIVE_CHUNK_SIZE,
    )
    assert map_result.success
    assert (scene_root / map_result.scene["id"]).exists()

    actor_id = seed_actor(campaign_id, gm_id, name="Cascade Actor")
    actor_upload = ActorAssetService(
        storage=LocalActorAssetStorage(root=actor_root)
    ).upload_image(
        actor_id=actor_id,
        user_id=gm_id,
        kind="portrait",
        filename="portrait.png",
        content_type="image/png",
        data=_png_bytes(),
    )
    assert actor_upload.success
    assert (actor_root / campaign_id).exists()

    journal_result = JournalService().create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="diary",
        title="Cascade Journal",
        visibility="private",
    )
    assert journal_result.success
    journal_upload = JournalAssetService(
        storage=LocalJournalAssetStorage(root=journal_root)
    ).upload_image(
        journal_id=journal_result.journal_id,
        user_id=gm_id,
        filename="journal.png",
        content_type="image/png",
        data=_png_bytes(),
    )
    assert journal_upload.success
    assert (journal_root / campaign_id).exists()

    system_path = actor_data_path(system_id="dnd5e", campaign_id=campaign_id, actor_id=actor_id)
    assert system_path is not None and system_path.exists()
    _insert_campaign_module_setting(campaign_id=campaign_id, user_id=gm_id)

    service = CampaignService(
        scene_asset_storage=LocalSceneAssetStorage(root=scene_root),
        actor_asset_storage=LocalActorAssetStorage(root=actor_root),
        journal_asset_storage=LocalJournalAssetStorage(root=journal_root),
        system_storage=ScopedJsonStorage(),
    )
    code_result = service.generate_delete_code(campaign_id=campaign_id, user_id=gm_id)
    assert code_result.success and code_result.removal_code

    result = service.delete_campaign(
        campaign_id=campaign_id,
        user_id=gm_id,
        removal_code=code_result.removal_code,
    )

    assert result.success
    assert _count(campaigns) == 0
    assert _count(campaign_members) == 0
    assert _count(scenes, campaign_id=campaign_id) == 0
    assert _count(scene_assets) == 0
    assert _count(scene_tiles) == 0
    assert _count(scene_chunks) == 0
    assert _count(actors_core, campaign_id=campaign_id) == 0
    assert _count(journals, campaign_id=campaign_id) == 0
    assert _count(journal_assets, campaign_id=campaign_id) == 0
    assert _count(module_settings) == 0
    assert not (scene_root / map_result.scene["id"]).exists()
    assert not (actor_root / campaign_id).exists()
    assert not (journal_root / campaign_id).exists()
    assert not Path(system_path).exists()
