from __future__ import annotations

import pytest

from app.domain.roles import PlayerRole
from app.domain.scenes import SceneAssetKind
from app.domain.scenes import SceneChunkEncoding
from app.domain.scenes import SceneLayerKind
from app.domain.scenes import SceneLayerVisibility
from app.engine.scenes.scene_service import SceneService
from app.persistence.repositories.scene_asset_repository import SceneAssetRepository
from app.persistence.repositories.scene_layer_repository import SceneLayerRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.scene_tile_repository import SceneTileRepository
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


def test_create_scene_requires_scene_create_permission(db):
    gm_id = seed_user(name="GM", email="gm-scene-create@test.com")
    player_id = seed_user(name="Player", email="player-scene-create@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    result = SceneService().create_scene(
        campaign_id=campaign_id,
        user_id=player_id,
        name="Warehouse",
        width=1400,
        height=1400,
        tile_size=70,
        chunk_size=16,
    )

    assert not result.success
    assert result.error_key == "permissions.errors.denied"


def test_gm_can_create_and_list_scenes(db):
    gm_id = seed_user(name="GM", email="gm-scene-list@test.com")
    campaign_id = seed_campaign(gm_id)
    service = SceneService()

    create_result = service.create_scene(
        campaign_id=campaign_id,
        user_id=gm_id,
        name="  Warehouse   Floor ",
        width=1400,
        height=1400,
        tile_size=70,
        chunk_size=16,
    )

    assert create_result.success
    assert create_result.scene is not None
    assert create_result.scene["name"] == "Warehouse Floor"

    list_result = service.list_scenes_for_campaign(
        campaign_id=campaign_id,
        user_id=gm_id,
    )

    assert list_result.success
    assert [scene["id"] for scene in list_result.scenes] == [create_result.scene["id"]]


@pytest.mark.asyncio
async def test_activate_scene_emits_realtime_event(db):
    gm_id = seed_user(name="GM", email="gm-scene-activate@test.com")
    campaign_id = seed_campaign(gm_id)
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
    transport = FakeTransport()

    result = await SceneService().activate_scene(
        scene_id=scene["id"],
        user_id=gm_id,
        transport=transport,
    )

    assert result.success
    assert result.scene is not None
    assert result.scene["active"] == 1
    assert transport.room_events == [
        {
            "room_id": campaign_id,
            "event": TransportEvent.SCENE_ACTIVATED,
            "payload": {
                "room_id": campaign_id,
                "scene_id": scene["id"],
                "previous_scene_id": None,
                "scene_epoch": result.scene["scene_epoch"],
                "scene": {
                    "id": scene["id"],
                    "name": "Warehouse",
                    "width": 1400,
                    "height": 1400,
                    "tile_size": 70,
                    "grid_visible": True,
                    "grid_color": "#6fddb4",
                    "grid_opacity": 0.4,
                    "image_scale": 1.0,
                    "start_world_x": 700.0,
                    "start_world_y": 700.0,
                    "start_zoom": 1.0,
                    "layer_id": layer["id"],
                    "tile_table_version": 1,
                    "scene_epoch": result.scene["scene_epoch"],
                },
            },
        }
    ]


def test_manifest_contains_metadata_without_chunk_payload(db):
    gm_id = seed_user(name="GM", email="gm-scene-manifest@test.com")
    campaign_id = seed_campaign(gm_id)
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
    assets = SceneAssetRepository()
    assets.create(
        scene_id=scene["id"],
        kind=SceneAssetKind.ORIGINAL_IMAGE,
        storage_path="storage/scenes/original/map.png",
        hash="original-hash",
        byte_size=2048,
        width=1400,
        height=1400,
        content_type="image/png",
    )
    tile_asset = assets.create(
        scene_id=scene["id"],
        kind=SceneAssetKind.RASTER_TILE,
        storage_path="storage/scenes/tiles/0_0.png",
        hash="tile-hash",
        byte_size=512,
        width=70,
        height=70,
        content_type="image/png",
    )
    SceneTileRepository().create(
        scene_id=scene["id"],
        layer_id=layer["id"],
        tile_ref=1,
        asset_id=tile_asset["id"],
        tx=0,
        ty=0,
        width=70,
        height=70,
        hash="tile-hash",
        byte_size=512,
    )

    result = SceneService().get_scene_manifest(
        scene_id=scene["id"],
        user_id=gm_id,
    )

    assert result.success
    assert result.manifest is not None
    assert result.manifest["tile_size"] == 70
    assert result.manifest["grid_size"] == 70
    assert result.manifest["chunk_size"] == 16
    assert result.manifest["scene_epoch"] == scene["scene_epoch"]
    assert result.manifest["layers"][0]["layer_id"] == layer["id"]
    assert result.manifest["layers"][0]["tiles"] == [
        {
            "tile_ref": 1,
            "asset_id": tile_asset["id"],
            "tx": 0,
            "ty": 0,
            "width": 70,
            "height": 70,
            "hash": "tile-hash",
            "byte_size": 512,
            "url": f"/game/scenes/{scene['id']}/layers/{layer['id']}/tiles/0/0?v=tile-hash",
        }
    ]
    assert "chunks" not in result.manifest
    assert "data" not in result.manifest


def test_manifest_filters_hidden_layers_for_player(db):
    gm_id = seed_user(name="GM", email="gm-scene-filter@test.com")
    player_id = seed_user(name="Player", email="player-scene-filter@test.com")
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
    SceneLayerRepository().create(
        scene_id=scene["id"],
        name="Hidden",
        kind=SceneLayerKind.RASTER_TILE_REFS,
        visibility=SceneLayerVisibility.HIDDEN,
        display_order=0,
        encoding=SceneChunkEncoding.UINT32_TILE_REFS_V1,
    )

    result = SceneService().get_scene_manifest(
        scene_id=scene["id"],
        user_id=player_id,
    )

    assert result.success
    assert result.manifest["layers"] == []


def test_outsider_cannot_get_scene_manifest(db):
    gm_id = seed_user(name="GM", email="gm-scene-denied@test.com")
    outsider_id = seed_user(name="Outsider", email="outsider-scene-denied@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = SceneRepository().create(
        campaign_id=campaign_id,
        name="Warehouse",
        width=1400,
        height=1400,
        tile_size=70,
        chunk_size=16,
    )

    result = SceneService().get_scene_manifest(
        scene_id=scene["id"],
        user_id=outsider_id,
    )

    assert not result.success
    assert result.error_key == "permissions.errors.denied"
