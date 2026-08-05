from __future__ import annotations

import hashlib

import pytest

from app.domain.roles import PlayerRole
from app.domain.scenes import SceneChunkEncoding
from app.domain.scenes import SceneLayerKind
from app.domain.scenes import SceneLayerVisibility
from app.engine.scenes.scene_chunk_service import SceneChunkService
from app.infrastructure.storage.local_chunk_storage import LocalChunkStorage
from app.persistence.repositories.scene_layer_repository import SceneLayerRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.realtime.events import TransportEvent
from tests.conftest import seed_campaign
from tests.conftest import seed_member
from tests.conftest import seed_user


class FakeTransport:
    def __init__(self):
        self.room_events = []

    async def to_room(self, room_id, event, payload):
        self.room_events.append(
            {
                "room_id": room_id,
                "event": event,
                "payload": payload,
            }
        )


def create_scene_stack(db):
    gm_id = seed_user(name="GM", email="scene-chunk-gm@test.com")
    player_id = seed_user(name="Player", email="scene-chunk-player@test.com")
    outsider_id = seed_user(name="Outsider", email="scene-chunk-outsider@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    scene = SceneRepository().create(
        campaign_id=campaign_id,
        name="Warehouse",
        width=1400,
        height=1400,
        tile_size=70,
        chunk_size=16,
    )
    layer = SceneLayerRepository().create(
        scene_id=scene["id"],
        name="Ground",
        kind=SceneLayerKind.RASTER_TILE_REFS,
        visibility=SceneLayerVisibility.VISIBLE,
        display_order=0,
        encoding=SceneChunkEncoding.UINT32_TILE_REFS_V1,
    )

    return campaign_id, gm_id, player_id, outsider_id, scene, layer


def make_service(tmp_path):
    return SceneChunkService(
        storage=LocalChunkStorage(root=tmp_path / "scenes"),
    )


@pytest.mark.asyncio
async def test_write_chunk_stores_data_versions_metadata_and_emits_small_event(db, tmp_path):
    campaign_id, gm_id, _player_id, _outsider_id, scene, layer = create_scene_stack(db)
    transport = FakeTransport()
    service = make_service(tmp_path)
    data_v1 = b"\x00\x00\x00\x01"
    data_v2 = b"\x00\x00\x00\x02"

    first = await service.write_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        data=data_v1,
        user_id=gm_id,
        transport=transport,
    )
    second = await service.write_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        data=data_v2,
        user_id=gm_id,
        transport=transport,
    )

    assert first.success
    assert first.chunk["version"] == 1
    assert first.chunk["hash"] == hashlib.sha256(data_v1).hexdigest()
    assert second.success
    assert second.chunk["version"] == 2
    assert second.chunk["hash"] == hashlib.sha256(data_v2).hexdigest()
    assert second.chunk["byte_size"] == len(data_v2)
    assert service.read_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        user_id=gm_id,
    ).data == data_v2
    assert transport.room_events[-1] == {
        "room_id": campaign_id,
        "event": TransportEvent.SCENE_CHUNK_UPDATED,
        "payload": {
            "room_id": campaign_id,
            "scene_id": scene["id"],
            "layer_id": layer["id"],
            "cx": 0,
            "cy": 0,
            "version": 2,
            "hash": hashlib.sha256(data_v2).hexdigest(),
            "byte_size": len(data_v2),
        },
    }
    assert "data" not in transport.room_events[-1]["payload"]


@pytest.mark.asyncio
async def test_player_cannot_write_chunk_by_default(db, tmp_path):
    _campaign_id, _gm_id, player_id, _outsider_id, scene, layer = create_scene_stack(db)

    result = await make_service(tmp_path).write_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        data=b"data",
        user_id=player_id,
    )

    assert not result.success
    assert result.error_key == "permissions.errors.denied"


@pytest.mark.asyncio
async def test_player_can_read_chunk_with_scene_view_permission(db, tmp_path):
    _campaign_id, gm_id, player_id, _outsider_id, scene, layer = create_scene_stack(db)
    service = make_service(tmp_path)

    await service.write_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        data=b"data",
        user_id=gm_id,
    )

    result = service.read_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        user_id=player_id,
    )

    assert result.success
    assert result.data == b"data"


@pytest.mark.asyncio
async def test_player_can_read_chunks_in_batch_with_scene_view_permission(db, tmp_path):
    _campaign_id, gm_id, player_id, _outsider_id, scene, layer = create_scene_stack(db)
    service = make_service(tmp_path)

    await service.write_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        data=b"zero",
        user_id=gm_id,
    )
    await service.write_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=1,
        cy=0,
        data=b"one",
        user_id=gm_id,
    )

    result = service.read_chunks(
        scene_id=scene["id"],
        layer_id=layer["id"],
        coords=((0, 0), (1, 0), (2, 0)),
        user_id=player_id,
    )

    assert result.success
    assert result.data_by_coord == {
        (0, 0): b"zero",
        (1, 0): b"one",
    }


@pytest.mark.asyncio
async def test_player_cannot_read_hidden_layer_chunk(db, tmp_path):
    _campaign_id, gm_id, player_id, _outsider_id, scene, layer = create_scene_stack(db)
    service = make_service(tmp_path)

    await service.write_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        data=b"data",
        user_id=gm_id,
    )
    SceneLayerRepository().update_metadata(
        layer_id=layer["id"],
        name=layer["name"],
        visibility=SceneLayerVisibility.HIDDEN,
        display_order=layer["display_order"],
        tile_table_version=layer["tile_table_version"],
    )

    result = service.read_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        user_id=player_id,
    )

    assert not result.success
    assert result.error_key == "permissions.errors.denied"


@pytest.mark.asyncio
async def test_gm_can_read_hidden_layer_chunk(db, tmp_path):
    _campaign_id, gm_id, _player_id, _outsider_id, scene, layer = create_scene_stack(db)
    service = make_service(tmp_path)

    await service.write_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        data=b"data",
        user_id=gm_id,
    )
    SceneLayerRepository().update_metadata(
        layer_id=layer["id"],
        name=layer["name"],
        visibility=SceneLayerVisibility.HIDDEN,
        display_order=layer["display_order"],
        tile_table_version=layer["tile_table_version"],
    )

    result = service.read_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        user_id=gm_id,
    )

    assert result.success
    assert result.data == b"data"


def test_outsider_cannot_read_chunk(db, tmp_path):
    _campaign_id, _gm_id, _player_id, outsider_id, scene, layer = create_scene_stack(db)

    result = make_service(tmp_path).read_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        user_id=outsider_id,
    )

    assert not result.success
    assert result.error_key == "permissions.errors.denied"


@pytest.mark.asyncio
async def test_viewport_metadata_lists_only_requested_chunks(db, tmp_path):
    _campaign_id, gm_id, player_id, _outsider_id, scene, layer = create_scene_stack(db)
    service = make_service(tmp_path)

    for cx, cy in [(0, 0), (1, 0), (3, 3)]:
        await service.write_chunk(
            scene_id=scene["id"],
            layer_id=layer["id"],
            cx=cx,
            cy=cy,
            data=f"{cx},{cy}".encode(),
            user_id=gm_id,
        )

    result = service.list_chunk_metadata_for_viewport(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx0=0,
        cy0=0,
        cx1=1,
        cy1=1,
        user_id=player_id,
    )

    assert result.success
    assert [(chunk["cx"], chunk["cy"]) for chunk in result.chunks] == [(0, 0), (1, 0)]


@pytest.mark.asyncio
async def test_write_chunk_rejects_layer_from_other_scene(db, tmp_path):
    _campaign_id, gm_id, _player_id, _outsider_id, scene, _layer = create_scene_stack(db)
    other_scene = SceneRepository().create(
        campaign_id=scene["campaign_id"],
        name="Other",
        width=1400,
        height=1400,
        tile_size=70,
        chunk_size=16,
    )
    other_layer = SceneLayerRepository().create(
        scene_id=other_scene["id"],
        name="Other Ground",
        kind=SceneLayerKind.RASTER_TILE_REFS,
        visibility=SceneLayerVisibility.VISIBLE,
        display_order=0,
        encoding=SceneChunkEncoding.UINT32_TILE_REFS_V1,
    )

    result = await make_service(tmp_path).write_chunk(
        scene_id=scene["id"],
        layer_id=other_layer["id"],
        cx=0,
        cy=0,
        data=b"data",
        user_id=gm_id,
    )

    assert not result.success
    assert result.error_key == "game.scenes.errors.not_found"
