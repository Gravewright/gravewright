from __future__ import annotations

import pytest

from app.domain.roles import PlayerRole
from app.domain.scenes import SceneAssetKind
from app.domain.scenes import SceneChunkEncoding
from app.domain.scenes import SceneVisibility
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
                    "grid_offset_x": 0.0,
                    "grid_offset_y": 0.0,
                    "darkness": 0.0,
                    "darkness_config": 0.0,
                    "lighting_mode": "none",
                    "lights_out": True,
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


def test_virtual_raster_manifest_keeps_tile_metadata_out_of_bootstrap(db):
    gm_id = seed_user(name="GM", email="gm-virtual-manifest@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = SceneRepository().create(
        campaign_id=campaign_id,
        name="Continent",
        width=500_000,
        height=500_000,
        tile_size=512,
        grid_size=70,
        chunk_size=8,
        scene_format_version=2,
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
    tiles = SceneTileRepository()
    for tile_ref, tx in enumerate(range(32), start=1):
        asset = assets.create(
            scene_id=scene["id"], kind=SceneAssetKind.RASTER_TILE,
            storage_path=f"tiles/{tx}_0.png", hash=f"hash-{tx}", byte_size=10,
            width=512, height=512, content_type="image/png",
        )
        tiles.create(
            scene_id=scene["id"], layer_id=layer["id"], tile_ref=tile_ref,
            asset_id=asset["id"], tx=tx, ty=0, width=512, height=512,
            hash=f"hash-{tx}", byte_size=10,
        )

    result = SceneService().get_scene_manifest(scene_id=scene["id"], user_id=gm_id)

    assert result.success
    assert result.manifest["version"] == 2
    assert result.manifest["grid_size"] == 70
    assert result.manifest["raster_tile_size"] == 512
    assert result.manifest["capabilities"] == ["virtual_raster", "sparse_tile_index", "lod"]
    assert result.manifest["assets"] == []
    assert result.manifest["layers"][0]["tiles"] == []
    assert result.manifest["layers"][0]["tile_index_url"].endswith("/tile-index")


def test_virtual_raster_tile_index_is_sparse_bounded_and_paginated(db):
    gm_id = seed_user(name="GM", email="gm-tile-index@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = SceneRepository().create(
        campaign_id=campaign_id, name="Continent", width=500_000,
        height=500_000, tile_size=512, grid_size=70, chunk_size=8,
        scene_format_version=2,
    )
    layer = SceneLayerRepository().create(
        scene_id=scene["id"], name="Ground",
        kind=SceneLayerKind.RASTER_TILE_REFS,
        visibility=SceneLayerVisibility.VISIBLE, display_order=0,
        encoding=SceneChunkEncoding.UINT32_TILE_REFS_V1,
    )
    assets = SceneAssetRepository()
    tiles = SceneTileRepository()
    for tile_ref, tx in enumerate((1, 2, 999), start=1):
        asset = assets.create(
            scene_id=scene["id"], kind=SceneAssetKind.RASTER_TILE,
            storage_path=f"tiles/{tx}_0.png", hash=f"hash-{tx}", byte_size=10,
            width=512, height=512, content_type="image/png",
        )
        tiles.create(
            scene_id=scene["id"], layer_id=layer["id"], tile_ref=tile_ref,
            asset_id=asset["id"], tx=tx, ty=0, width=512, height=512,
            hash=f"hash-{tx}", byte_size=10,
        )

    page = SceneService().get_scene_tile_index(
        scene_id=scene["id"], layer_id=layer["id"], user_id=gm_id,
        lod=0, tx0=0, ty0=0, tx1=10, ty1=10, limit=1, after_ref=0,
    )

    assert page.success
    assert [tile["tx"] for tile in page.manifest["tiles"]] == [1]
    assert page.manifest["next_after_ref"] == 1


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


def test_grid_appearance_update_keeps_the_same_scene_instance(db):
    gm_id = seed_user(name="GM", email="gm-scene-grid-update@test.com")
    campaign_id = seed_campaign(gm_id)
    repository = SceneRepository()
    scene = repository.create(
        campaign_id=campaign_id,
        name="Cellar",
        width=700,
        height=700,
        tile_size=70,
        chunk_size=16,
    )

    SceneService().update_scene_metadata(
        scene_id=scene["id"],
        name=scene["name"],
        group_id=scene["group_id"],
        visibility=SceneVisibility(scene["visibility"]),
        grid_visible=False,
        grid_color="#ff3366",
        grid_opacity=0.75,
        darkness=None,
        tile_size=scene["tile_size"],
        grid_size=scene["grid_size"],
        image_scale=scene["image_scale"],
        tile_table_version=scene["tile_table_version"],
    )

    scenes = repository.list_by_campaign(campaign_id)
    assert len(scenes) == 1
    assert scenes[0]["id"] == scene["id"]
    assert scenes[0]["scene_epoch"] == scene["scene_epoch"]
    assert scenes[0]["grid_visible"] == 0
    assert scenes[0]["grid_color"] == "#ff3366"
    assert scenes[0]["grid_opacity"] == 0.75


def test_grid_calibration_persists_offsets_and_changes_stream_generation(db):
    gm_id = seed_user(name="GM", email="gm-grid-calibration@test.com")
    campaign_id = seed_campaign(gm_id)
    repository = SceneRepository()
    scene = repository.create(
        campaign_id=campaign_id, name="Printed grid", width=700, height=700,
        tile_size=70, chunk_size=16,
    )

    SceneService().update_scene_metadata(
        scene_id=scene["id"], name=scene["name"], group_id=None,
        visibility=SceneVisibility(scene["visibility"]), grid_visible=True,
        grid_color=scene["grid_color"], grid_opacity=scene["grid_opacity"],
        darkness=None, tile_size=scene["tile_size"], grid_size=69.72,
        image_scale=scene["image_scale"], tile_table_version=scene["tile_table_version"],
        grid_offset_x=11.5, grid_offset_y=17.25,
    )

    updated = repository.get_by_id(scene["id"])
    assert updated["grid_offset_x"] == 11.5
    assert updated["grid_offset_y"] == 17.25
    assert updated["grid_size"] == 69.72
    assert updated["scene_epoch"] == scene["scene_epoch"] + 1


async def test_metadata_update_reaches_the_room(db):
    """Sem este evento, escuridão e grade só chegavam a quem editou: o modal
    atualiza o próprio canvas pela resposta e o resto da sala ficava com a cena
    antiga até recarregar a página."""
    gm_id = seed_user(name="GM", email="gm-scene-update@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = SceneRepository().create(
        campaign_id=campaign_id, name="Cellar", width=700, height=700,
        tile_size=70, chunk_size=16,
    )
    service = SceneService()
    await service.activate_scene(scene_id=scene["id"], user_id=gm_id)

    service.update_scene_metadata(
        scene_id=scene["id"],
        name="Cellar",
        group_id=None,
        visibility=SceneVisibility.PLAYERS,
        grid_visible=True,
        grid_color="#6fddb4",
        grid_opacity=0.55,
        darkness=None,
        tile_size=70,
        image_scale=1.0,
        tile_table_version=1,
    )

    transport = FakeTransport()
    assert await service.broadcast_scene_update(scene_id=scene["id"], transport=transport)

    assert len(transport.room_events) == 1
    event = transport.room_events[0]
    assert event["room_id"] == campaign_id
    assert event["event"] == TransportEvent.SCENE_UPDATED
    assert event["payload"]["scene_id"] == scene["id"]
    assert event["payload"]["scene"]["grid_opacity"] == 0.55

    # A escuridao e do regime de luz, nao dos metadados: o broadcast anuncia a
    # EFETIVA, e ela so vale com a cena em iluminacao dinamica e a luz apagada.
    service.update_scene_lighting(
        scene_id=scene["id"], mode="dynamic", darkness=0.85, lights_out=True
    )
    transport = FakeTransport()
    assert await service.broadcast_scene_update(scene_id=scene["id"], transport=transport)
    announced = transport.room_events[0]["payload"]["scene"]
    assert announced["darkness"] == 0.85
    assert announced["darkness_config"] == 0.85
    assert announced["lighting_mode"] == "dynamic"

    # Acender a luz abre o mapa sem perder a intensidade ajustada.
    service.update_scene_lighting(scene_id=scene["id"], mode="dynamic", lights_out=False)
    transport = FakeTransport()
    assert await service.broadcast_scene_update(scene_id=scene["id"], transport=transport)
    lit = transport.room_events[0]["payload"]["scene"]
    assert lit["darkness"] == 0.0, "luz acesa nao escurece nada"
    assert lit["darkness_config"] == 0.85, "mas o slider guarda o valor"


async def test_only_the_active_scene_is_announced(db):
    """Editar uma cena guardada não interessa a ninguém na mesa, e espalhar o
    nome e as dimensões dela para a sala seria vazamento à toa."""
    gm_id = seed_user(name="GM", email="gm-scene-inactive@test.com")
    campaign_id = seed_campaign(gm_id)
    live = SceneRepository().create(
        campaign_id=campaign_id, name="Live", width=700, height=700,
        tile_size=70, chunk_size=16,
    )
    stored = SceneRepository().create(
        campaign_id=campaign_id, name="Segredo do GM", width=700, height=700,
        tile_size=70, chunk_size=16,
    )
    service = SceneService()
    await service.activate_scene(scene_id=live["id"], user_id=gm_id)

    transport = FakeTransport()
    assert not await service.broadcast_scene_update(scene_id=stored["id"], transport=transport)
    assert transport.room_events == []

    assert await service.broadcast_scene_update(scene_id=live["id"], transport=transport)
    assert len(transport.room_events) == 1
