from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.domain.roles import PlayerRole
from app.domain.scenes import SCENE_NATIVE_CHUNK_SIZE
from app.engine.scenes.map_upload_service import MapUploadService
from app.infrastructure.storage.local_chunk_storage import LocalChunkStorage
from app.infrastructure.storage.local_scene_asset_storage import LocalSceneAssetStorage
from app.persistence.repositories.scene_asset_repository import SceneAssetRepository
from app.persistence.repositories.scene_chunk_repository import SceneChunkRepository
from app.persistence.repositories.scene_tile_repository import SceneTileRepository
from app.realtime.events import TransportEvent
from tests.conftest import seed_campaign
from tests.conftest import seed_member
from tests.conftest import seed_user


class FakeTransport:
    def __init__(self):
        self.room_events = []
        self.player_events = []

    async def to_room(self, room_id, event, payload):
        self.room_events.append(
            {
                "room_id": room_id,
                "event": event,
                "payload": payload,
            }
        )

    async def to_player(self, player_id, event, payload):
        self.player_events.append(
            {
                "player_id": player_id,
                "event": event,
                "payload": payload,
            }
        )


def png_bytes(width: int, height: int) -> bytes:
    image = Image.new("RGBA", (width, height), (255, 0, 0, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def decode_uint32_refs(data: bytes) -> list[int]:
    return [
        int.from_bytes(data[index:index + 4], byteorder="little", signed=False)
        for index in range(0, len(data), 4)
    ]


def create_upload_context(db):
    gm_id = seed_user(name="GM", email="map-upload-gm@test.com")
    player_id = seed_user(name="Player", email="map-upload-player@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    return campaign_id, gm_id, player_id


def make_service(tmp_path):
    storage_root = tmp_path / "scenes"

    return MapUploadService(
        asset_storage=LocalSceneAssetStorage(root=storage_root),
        chunk_storage=LocalChunkStorage(root=storage_root),
    )


@pytest.mark.asyncio
async def test_upload_raster_map_creates_scene_tiles_tile_table_and_chunks(db, tmp_path):
    campaign_id, gm_id, _player_id = create_upload_context(db)
    transport = FakeTransport()
    result = await make_service(tmp_path).upload_raster_map(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Test Map",
        filename="map.png",
        content_type="image/png",
        data=png_bytes(140, 140),
        tile_size=70,
        chunk_size=SCENE_NATIVE_CHUNK_SIZE,
        transport=transport,
    )

    assert result.success
    assert result.scene is not None
    assert result.layer is not None
    assert result.tile_count == 4
    assert result.chunk_count == 1

    assets = SceneAssetRepository().list_by_scene(result.scene["id"])
    tiles = SceneTileRepository().list_by_layer(result.layer["id"])
    chunk = SceneChunkRepository().get_metadata(layer_id=result.layer["id"], cx=0, cy=0)
    chunk_data = LocalChunkStorage(root=tmp_path / "scenes").read_chunk(
        scene_id=result.scene["id"],
        layer_id=result.layer["id"],
        cx=0,
        cy=0,
    )

    assert len(assets) == 5
    assert [tile["tile_ref"] for tile in tiles] == [1, 2, 3, 4]
    assert chunk is not None
    assert chunk["version"] == 1
    assert chunk["byte_size"] == SCENE_NATIVE_CHUNK_SIZE * SCENE_NATIVE_CHUNK_SIZE * 4
    refs = decode_uint32_refs(chunk_data)
    assert refs[:2] == [1, 2]
    assert refs[SCENE_NATIVE_CHUNK_SIZE:SCENE_NATIVE_CHUNK_SIZE + 2] == [3, 4]
    assert sum(1 for ref in refs if ref != 0) == 4
    assert Path(result.original_asset["storage_path"]).exists()
    assert all(Path(tile_asset["storage_path"]).exists() for tile_asset in assets[1:])
    assert transport.room_events[0]["event"] == TransportEvent.SCENE_CREATED
    assert transport.room_events[1]["event"] == TransportEvent.SCENE_LAYER_CREATED
    assert "data" not in transport.room_events[0]["payload"]


@pytest.mark.asyncio
async def test_upload_raster_map_emits_progress_to_uploader(db, tmp_path):
    campaign_id, gm_id, _player_id = create_upload_context(db)
    transport = FakeTransport()
    result = await make_service(tmp_path).upload_raster_map(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Progress Map",
        filename="map.png",
        content_type="image/png",
        data=png_bytes(140, 140),
        tile_size=70,
        chunk_size=SCENE_NATIVE_CHUNK_SIZE,
        transport=transport,
        upload_id="upload-123",
    )

    assert result.success

    progress = [
        event
        for event in transport.player_events
        if event["event"] == TransportEvent.SCENE_UPLOAD_PROGRESS
    ]

    assert progress, "expected progress events"
    assert all(event["player_id"] == gm_id for event in progress)
    assert all(event["payload"]["upload_id"] == "upload-123" for event in progress)
    assert all(event["payload"]["scene_id"] == result.scene["id"] for event in progress)

    phases = [event["payload"]["phase"] for event in progress]
    assert phases[0] == "preparing"
    assert phases[-1] == "complete"
    assert "tiling" in phases
    assert "chunking" in phases

    percents = [event["payload"]["percent"] for event in progress]
    assert percents[0] == 0
    assert percents[-1] == 100
    assert percents == sorted(percents), "progress must be monotonic"


@pytest.mark.asyncio
async def test_upload_raster_map_does_not_emit_progress_without_upload_id(db, tmp_path):
    campaign_id, gm_id, _player_id = create_upload_context(db)
    transport = FakeTransport()
    result = await make_service(tmp_path).upload_raster_map(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Silent Map",
        filename="map.png",
        content_type="image/png",
        data=png_bytes(140, 140),
        tile_size=70,
        chunk_size=SCENE_NATIVE_CHUNK_SIZE,
        transport=transport,
    )

    assert result.success
    assert transport.player_events == []


@pytest.mark.asyncio
async def test_upload_raster_map_handles_partial_edge_tiles_and_empty_chunk_cells(db, tmp_path):
    campaign_id, gm_id, _player_id = create_upload_context(db)
    result = await make_service(tmp_path).upload_raster_map(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Odd Map",
        filename="map.png",
        content_type="image/png",
        data=png_bytes(141, 70),
        tile_size=70,
        chunk_size=SCENE_NATIVE_CHUNK_SIZE,
    )

    assert result.success
    assert result.tile_count == 3
    assert result.chunk_count == 1

    tiles = SceneTileRepository().list_by_layer(result.layer["id"])
    first_chunk_data = LocalChunkStorage(root=tmp_path / "scenes").read_chunk(
        scene_id=result.scene["id"],
        layer_id=result.layer["id"],
        cx=0,
        cy=0,
    )

    assert [tile["width"] for tile in tiles] == [70, 70, 1]
    refs = decode_uint32_refs(first_chunk_data)
    assert refs[:4] == [1, 2, 3, 0]
    assert sum(1 for ref in refs if ref != 0) == 3


@pytest.mark.asyncio
async def test_player_cannot_upload_raster_map_by_default(db, tmp_path):
    campaign_id, _gm_id, player_id = create_upload_context(db)
    result = await make_service(tmp_path).upload_raster_map(
        campaign_id=campaign_id,
        user_id=player_id,
        name="Denied Map",
        filename="map.png",
        content_type="image/png",
        data=png_bytes(70, 70),
        tile_size=70,
        chunk_size=SCENE_NATIVE_CHUNK_SIZE,
    )

    assert not result.success
    assert result.error_key == "permissions.errors.denied"


@pytest.mark.asyncio
async def test_upload_raster_map_rejects_empty_file(db, tmp_path):
    campaign_id, gm_id, _player_id = create_upload_context(db)
    result = await make_service(tmp_path).upload_raster_map(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Empty Map",
        filename="map.png",
        content_type="image/png",
        data=b"",
        tile_size=70,
        chunk_size=SCENE_NATIVE_CHUNK_SIZE,
    )

    assert not result.success
    assert result.error_key == "game.maps.errors.empty_file"


@pytest.mark.asyncio
async def test_upload_raster_map_rejects_invalid_image(db, tmp_path):
    campaign_id, gm_id, _player_id = create_upload_context(db)
    result = await make_service(tmp_path).upload_raster_map(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Broken Map",
        filename="map.png",
        content_type="image/png",
        data=b"not actually an image",
        tile_size=70,
        chunk_size=SCENE_NATIVE_CHUNK_SIZE,
    )

    assert not result.success
    assert result.error_key == "game.maps.errors.invalid_image"


@pytest.mark.asyncio
async def test_upload_raster_map_rejects_unsupported_type(db, tmp_path):
    campaign_id, gm_id, _player_id = create_upload_context(db)
    result = await make_service(tmp_path).upload_raster_map(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Svg Map",
        filename="map.svg",
        content_type="image/svg+xml",
        data=b"<svg></svg>",
        tile_size=70,
        chunk_size=SCENE_NATIVE_CHUNK_SIZE,
    )

    assert not result.success
    assert result.error_key == "game.maps.errors.unsupported_type"


@pytest.mark.asyncio
async def test_upload_raster_map_rejects_invalid_tile_size(db, tmp_path):
    campaign_id, gm_id, _player_id = create_upload_context(db)
    result = await make_service(tmp_path).upload_raster_map(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Bad Grid",
        filename="map.png",
        content_type="image/png",
        data=png_bytes(70, 70),
        tile_size=0,
        chunk_size=SCENE_NATIVE_CHUNK_SIZE,
    )

    assert not result.success
    assert result.error_key == "game.scenes.errors.invalid_dimensions"


@pytest.mark.asyncio
async def test_upload_raster_map_rejects_non_native_chunk_size(db, tmp_path):
    campaign_id, gm_id, _player_id = create_upload_context(db)
    result = await make_service(tmp_path).upload_raster_map(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Bad Chunk",
        filename="map.png",
        content_type="image/png",
        data=png_bytes(70, 70),
        tile_size=70,
        chunk_size=2,
    )

    assert not result.success
    assert result.error_key == "game.scenes.errors.invalid_dimensions"


@pytest.mark.asyncio
async def test_delete_scene_removes_rows_storage_and_emits_event(db, tmp_path):
    campaign_id, gm_id, _player_id = create_upload_context(db)
    service = make_service(tmp_path)
    upload = await service.upload_raster_map(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Doomed Map",
        filename="map.png",
        content_type="image/png",
        data=png_bytes(140, 140),
        tile_size=70,
        chunk_size=SCENE_NATIVE_CHUNK_SIZE,
    )
    assert upload.success
    scene_id = upload.scene["id"]
    layer_id = upload.layer["id"]
    scene_dir = tmp_path / "scenes" / scene_id
    assert scene_dir.exists()

    transport = FakeTransport()
    result = await service.delete_scene(scene_id=scene_id, user_id=gm_id, transport=transport)

    assert result.success
    assert service.scenes.get_by_id(scene_id) is None
    assert SceneAssetRepository().list_by_scene(scene_id) == []
    assert SceneTileRepository().list_by_layer(layer_id) == []
    assert not scene_dir.exists()

    deleted = [e for e in transport.room_events if e["event"] == TransportEvent.SCENE_DELETED]
    assert len(deleted) == 1
    assert deleted[0]["payload"]["scene_id"] == scene_id
    assert deleted[0]["payload"]["room_id"] == campaign_id


@pytest.mark.asyncio
async def test_delete_scene_denied_for_player(db, tmp_path):
    campaign_id, gm_id, player_id = create_upload_context(db)
    service = make_service(tmp_path)
    upload = await service.upload_raster_map(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="Guarded Map",
        filename="map.png",
        content_type="image/png",
        data=png_bytes(140, 140),
        tile_size=70,
        chunk_size=SCENE_NATIVE_CHUNK_SIZE,
    )
    assert upload.success
    scene_id = upload.scene["id"]

    result = await service.delete_scene(scene_id=scene_id, user_id=player_id)

    assert not result.success
    assert result.error_key == "permissions.errors.denied"
    assert service.scenes.get_by_id(scene_id) is not None
