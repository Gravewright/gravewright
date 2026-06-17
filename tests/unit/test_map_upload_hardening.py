from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.domain.scenes import SCENE_NATIVE_CHUNK_SIZE
from app.engine.scenes.map_upload_service import MapUploadService
from app.infrastructure.images.image_decoder import ImageDecoder
from app.infrastructure.storage.local_chunk_storage import LocalChunkStorage
from app.infrastructure.storage.local_scene_asset_storage import LocalSceneAssetStorage
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.scene_tile_repository import SceneTileRepository
from tests.conftest import seed_campaign
from tests.conftest import seed_user


def _png(width: int, height: int) -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", (width, height), (10, 20, 30, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_image_decoder_decodes_normal_image() -> None:
    decoded = ImageDecoder(max_dimension=64).decode(_png(32, 32))
    assert decoded.width == 32
    assert decoded.height == 32


def test_image_decoder_rejects_oversized_dimensions() -> None:
    decoder = ImageDecoder(max_dimension=16)
    with pytest.raises(ValueError):
        decoder.decode(_png(64, 8))


class _FailingChunkStorage(LocalChunkStorage):
    def write_chunk(self, **kwargs):                          
        raise RuntimeError("disk exploded")


@pytest.mark.asyncio
async def test_failed_upload_discards_partial_scene(db, tmp_path):
    gm_id = seed_user(name="GM", email="map-hardening-gm@test.com")
    campaign_id = seed_campaign(gm_id)

    storage_root = tmp_path / "scenes"
    service = MapUploadService(
        asset_storage=LocalSceneAssetStorage(root=storage_root),
        chunk_storage=_FailingChunkStorage(root=storage_root),
    )

    result = await service.upload_raster_map(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Doomed Map",
        filename="map.png",
        content_type="image/png",
        data=_png(140, 140),
        tile_size=70,
        chunk_size=SCENE_NATIVE_CHUNK_SIZE,
    )

    assert result.success is False
    assert result.error_key == "game.maps.errors.processing_failed"

                                                   
    assert SceneRepository().list_by_campaign(campaign_id) == []
    assert not (storage_root).exists() or list(storage_root.iterdir()) == []


@pytest.mark.asyncio
async def test_staged_retile_generation_failure_preserves_existing_scene(db, tmp_path):
    gm_id = seed_user(name="GM", email="map-staging-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    storage_root = tmp_path / "scenes"
    service = MapUploadService(
        asset_storage=LocalSceneAssetStorage(root=storage_root),
        chunk_storage=LocalChunkStorage(root=storage_root),
    )

    upload = await service.upload_raster_map(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Keep Me",
        filename="map.png",
        content_type="image/png",
        data=_png(140, 140),
        tile_size=70,
        chunk_size=SCENE_NATIVE_CHUNK_SIZE,
    )
    assert upload.success
    layer_id = upload.layer["id"]
    before = len(SceneTileRepository().list_by_layer(layer_id))
    assert before > 0

                                                                              
                                               
    def _boom(**_kwargs):
        raise RuntimeError("render exploded")

    service._render_tiles = _boom                               

    result = await service.retile_scene(scene_id=upload.scene["id"], user_id=gm_id, new_tile_size=35)

    assert result.success is False
    assert result.error_key == "game.maps.errors.processing_failed"
    assert len(SceneTileRepository().list_by_layer(layer_id)) == before

@pytest.mark.asyncio
async def test_staged_retile_commit_failure_restores_existing_artifacts(db, tmp_path):
    gm_id = seed_user(name="GM", email="map-staging-commit-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    storage_root = tmp_path / "scenes"
    service = MapUploadService(
        asset_storage=LocalSceneAssetStorage(root=storage_root),
        chunk_storage=LocalChunkStorage(root=storage_root),
    )

    upload = await service.upload_raster_map(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Restore Me",
        filename="map.png",
        content_type="image/png",
        data=_png(140, 140),
        tile_size=70,
        chunk_size=SCENE_NATIVE_CHUNK_SIZE,
    )
    assert upload.success
    layer_id = upload.layer["id"]
    before_tiles = SceneTileRepository().list_by_layer(layer_id)
    assert before_tiles
    before_tile_path = Path(before_tiles[0]["storage_path"])
    before_tile_bytes = before_tile_path.read_bytes()
    before_chunk_path = storage_root / upload.scene["id"] / "chunks" / layer_id / "0_0.bin"
    before_chunk_bytes = before_chunk_path.read_bytes()

    def _explode_metadata(*_args, **_kwargs):
        raise RuntimeError("metadata commit exploded")

    service._replace_retile_metadata_atomic = _explode_metadata                               

    result = await service.retile_scene(scene_id=upload.scene["id"], user_id=gm_id, new_tile_size=35)

    assert result.success is False
    assert result.error_key == "game.maps.errors.processing_failed"
    assert len(SceneTileRepository().list_by_layer(layer_id)) == len(before_tiles)
    assert before_tile_path.read_bytes() == before_tile_bytes
    assert before_chunk_path.read_bytes() == before_chunk_bytes
    assert not list((storage_root / upload.scene["id"] / "assets" / "tiles" / ".staging").glob("*"))
    assert not list((storage_root / upload.scene["id"] / "chunks" / ".staging").glob("*"))
