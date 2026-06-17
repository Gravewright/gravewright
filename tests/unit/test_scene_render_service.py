from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from app.domain.roles import PlayerRole
from app.domain.scenes import SCENE_NATIVE_CHUNK_SIZE
from app.domain.scenes import SceneLayerVisibility
from app.engine.scenes.map_upload_service import MapUploadService
from app.engine.scenes.scene_chunk_service import SceneChunkService
from app.engine.scenes.scene_render_service import SceneRenderService
from app.infrastructure.storage.local_chunk_storage import LocalChunkStorage
from app.infrastructure.storage.local_scene_asset_storage import LocalSceneAssetStorage
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.scene_layer_repository import SceneLayerRepository
from tests.conftest import seed_campaign
from tests.conftest import seed_member
from tests.conftest import seed_user


def png_bytes(width: int, height: int) -> bytes:
    image = Image.new("RGBA", (width, height), (0, 255, 0, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def services(tmp_path):
    storage_root = tmp_path / "scenes"
    chunk_storage = LocalChunkStorage(root=storage_root)

    return (
        MapUploadService(
            asset_storage=LocalSceneAssetStorage(root=storage_root),
            chunk_storage=chunk_storage,
        ),
        SceneRenderService(
            chunk_service=SceneChunkService(storage=chunk_storage),
        ),
    )


async def create_active_uploaded_scene(
    db,
    tmp_path,
    *,
    width=280,
    height=140,
    chunk_size=SCENE_NATIVE_CHUNK_SIZE,
):
    gm_id = seed_user(name="GM", email="render-gm@test.com")
    player_id = seed_user(name="Player", email="render-player@test.com")
    outsider_id = seed_user(name="Outsider", email="render-outsider@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    upload_service, _render_service = services(tmp_path)

    upload = await upload_service.upload_raster_map(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Render Map",
        filename="map.png",
        content_type="image/png",
        data=png_bytes(width, height),
        tile_size=70,
        chunk_size=chunk_size,
    )
    assert upload.success
    SceneRepository().set_active_scene(
        campaign_id=campaign_id,
        scene_id=upload.scene["id"],
    )

    return campaign_id, gm_id, player_id, outsider_id, upload


@pytest.mark.asyncio
async def test_active_projection_returns_render_projection_not_scene_row(db, tmp_path):
    campaign_id, _gm_id, player_id, _outsider_id, upload = await create_active_uploaded_scene(
        db,
        tmp_path,
    )

    _upload_service, render_service = services(tmp_path)
    result = render_service.get_active_projection(
        campaign_id=campaign_id,
        user_id=player_id,
    )

    assert result.success
    assert result.projection.scene_id == upload.scene["id"]
    assert result.projection.tile_size == 70
    assert result.projection.grid_size == 70
    assert result.projection.chunk_size == SCENE_NATIVE_CHUNK_SIZE
    assert result.projection.chunk_pixel_size == 1120
    assert len(result.projection.layers) == 1
    assert [tile.tile_ref for tile in result.projection.layers[0].tiles] == [1, 2, 3, 4, 5, 6, 7, 8]


@pytest.mark.asyncio
async def test_outsider_cannot_get_active_projection(db, tmp_path):
    campaign_id, _gm_id, _player_id, outsider_id, _upload = await create_active_uploaded_scene(
        db,
        tmp_path,
    )

    _upload_service, render_service = services(tmp_path)
    result = render_service.get_active_projection(
        campaign_id=campaign_id,
        user_id=outsider_id,
    )

    assert not result.success
    assert result.error_key == "permissions.errors.denied"


@pytest.mark.asyncio
async def test_hidden_layer_is_not_rendered_for_player(db, tmp_path):
    campaign_id, _gm_id, player_id, _outsider_id, upload = await create_active_uploaded_scene(
        db,
        tmp_path,
    )
    SceneLayerRepository().update_metadata(
        layer_id=upload.layer["id"],
        name=upload.layer["name"],
        visibility=SceneLayerVisibility.HIDDEN,
        display_order=upload.layer["display_order"],
        tile_table_version=upload.layer["tile_table_version"],
    )

    _upload_service, render_service = services(tmp_path)
    result = render_service.get_active_projection(
        campaign_id=campaign_id,
        user_id=player_id,
    )

    assert result.success
    assert result.projection.layers == ()


@pytest.mark.asyncio
async def test_viewport_chunks_returns_only_intersecting_chunk_metadata(db, tmp_path):
    campaign_id, _gm_id, player_id, _outsider_id, _upload = await create_active_uploaded_scene(
        db,
        tmp_path,
        width=280,
        height=140,
    )

    _upload_service, render_service = services(tmp_path)
    result = render_service.get_viewport_chunks(
        campaign_id=campaign_id,
        user_id=player_id,
        x0=0,
        y0=0,
        x1=139,
        y1=139,
    )

    assert result.success
    assert [(chunk.cx, chunk.cy) for chunk in result.chunks] == [(0, 0)]
    assert result.chunks[0].data is None
    assert result.chunks[0].tile_refs is None


@pytest.mark.asyncio
async def test_viewport_chunks_can_include_data_and_decoded_refs(db, tmp_path):
    campaign_id, _gm_id, player_id, _outsider_id, _upload = await create_active_uploaded_scene(
        db,
        tmp_path,
        width=280,
        height=140,
    )

    _upload_service, render_service = services(tmp_path)
    result = render_service.get_viewport_chunks(
        campaign_id=campaign_id,
        user_id=player_id,
        x0=0,
        y0=0,
        x1=280,
        y1=140,
        include_data=True,
        decode_refs=True,
    )

    assert result.success
    assert [(chunk.cx, chunk.cy) for chunk in result.chunks] == [(0, 0)]
    assert result.chunks[0].tile_refs[:4] == (1, 2, 3, 4)
    assert result.chunks[0].tile_refs[
        SCENE_NATIVE_CHUNK_SIZE:SCENE_NATIVE_CHUNK_SIZE + 4
    ] == (5, 6, 7, 8)
    assert sum(1 for ref in result.chunks[0].tile_refs if ref != 0) == 8
    assert result.chunks[0].data is not None


@pytest.mark.asyncio
async def test_viewport_outside_scene_returns_empty_result(db, tmp_path):
    campaign_id, _gm_id, player_id, _outsider_id, _upload = await create_active_uploaded_scene(
        db,
        tmp_path,
    )

    _upload_service, render_service = services(tmp_path)
    result = render_service.get_viewport_chunks(
        campaign_id=campaign_id,
        user_id=player_id,
        x0=1000,
        y0=1000,
        x1=1200,
        y1=1200,
    )

    assert result.success
    assert result.chunks == ()
