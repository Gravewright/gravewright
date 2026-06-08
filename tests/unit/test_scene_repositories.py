from __future__ import annotations

from app.domain.scenes import SceneAssetKind
from app.domain.scenes import SceneChunkEncoding
from app.domain.scenes import SceneLayerKind
from app.domain.scenes import SceneLayerVisibility
from app.domain.scenes import SceneStatus
from app.domain.scenes import SceneVisibility
from app.persistence.repositories.scene_asset_repository import SceneAssetRepository
from app.persistence.repositories.scene_chunk_repository import SceneChunkRepository
from app.persistence.repositories.scene_layer_repository import SceneLayerRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.scene_tile_repository import SceneTileRepository
from tests.conftest import seed_campaign
from tests.conftest import seed_user


def create_scene_stack(db):
    gm_id = seed_user(email="scene-gm@test.com")
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

    return campaign_id, scene, layer


def test_scene_repository_creates_lists_and_activates_one_scene(db):
    gm_id = seed_user(email="scene-active@test.com")
    campaign_id = seed_campaign(gm_id)
    scenes = SceneRepository()

    first = scenes.create(
        campaign_id=campaign_id,
        name="First",
        width=1400,
        height=1400,
        tile_size=70,
        chunk_size=16,
    )
    second = scenes.create(
        campaign_id=campaign_id,
        name="Second",
        width=700,
        height=700,
        tile_size=70,
        chunk_size=16,
    )

    assert [scene["id"] for scene in scenes.list_by_campaign(campaign_id)] == [
        first["id"],
        second["id"],
    ]

    activated = scenes.set_active_scene(
        campaign_id=campaign_id,
        scene_id=first["id"],
    )
    assert activated is not None
    assert activated["active"] == 1
    assert activated["status"] == SceneStatus.ACTIVE.value
    assert activated["scene_epoch"] == first["scene_epoch"] + 1

    activated = scenes.set_active_scene(
        campaign_id=campaign_id,
        scene_id=second["id"],
    )

    assert activated is not None
    assert activated["id"] == second["id"]
    assert scenes.get_active_scene(campaign_id)["id"] == second["id"]
    assert scenes.get_by_id(first["id"])["active"] == 0
    assert activated["scene_epoch"] == second["scene_epoch"] + 1


def test_scene_metadata_structural_update_increments_scene_epoch(db):
    _campaign_id, scene, _layer = create_scene_stack(db)
    scenes = SceneRepository()

    scenes.update_metadata(
        scene_id=scene["id"],
        name=scene["name"],
        group_id=scene["group_id"],
        visibility=SceneVisibility.PLAYERS,
        grid_visible=bool(scene["grid_visible"]),
        grid_color=scene["grid_color"],
        grid_opacity=scene["grid_opacity"],
        tile_size=scene["tile_size"],
        image_scale=scene["image_scale"],
        tile_table_version=scene["tile_table_version"],
    )
    unchanged = scenes.get_by_id(scene["id"])

    scenes.update_metadata(
        scene_id=scene["id"],
        name=scene["name"],
        group_id=scene["group_id"],
        visibility=SceneVisibility.GM_ONLY,
        grid_visible=bool(scene["grid_visible"]),
        grid_color=scene["grid_color"],
        grid_opacity=scene["grid_opacity"],
        tile_size=scene["tile_size"],
        image_scale=scene["image_scale"],
        tile_table_version=scene["tile_table_version"],
    )
    changed = scenes.get_by_id(scene["id"])

    assert unchanged["scene_epoch"] == scene["scene_epoch"]
    assert changed["scene_epoch"] == unchanged["scene_epoch"] + 1


def test_scene_repository_stores_start_point(db):
    _campaign_id, scene, _layer = create_scene_stack(db)
    scenes = SceneRepository()

    assert scene["start_world_x"] == scene["width"] / 2
    assert scene["start_world_y"] == scene["height"] / 2
    assert scene["start_zoom"] == 1.0

    scenes.update_start_point(
        scene_id=scene["id"],
        start_world_x=320.5,
        start_world_y=480.25,
        start_zoom=1.35,
    )
    updated = scenes.get_by_id(scene["id"])

    assert updated["start_world_x"] == 320.5
    assert updated["start_world_y"] == 480.25
    assert updated["start_zoom"] == 1.35
    assert updated["scene_epoch"] == scene["scene_epoch"]


def test_layer_structural_update_increments_scene_epoch(db):
    _campaign_id, scene, layer = create_scene_stack(db)

    SceneLayerRepository().update_metadata(
        layer_id=layer["id"],
        name=layer["name"],
        visibility=SceneLayerVisibility.HIDDEN,
        display_order=layer["display_order"],
        tile_table_version=layer["tile_table_version"],
    )

    assert SceneRepository().get_by_id(scene["id"])["scene_epoch"] == scene["scene_epoch"] + 1


def test_scene_repository_persists_board_area_markers(db):
    _campaign_id, scene, _layer = create_scene_stack(db)
    scenes = SceneRepository()
    marker = {
        "id": "marker-1",
        "scene_id": scene["id"],
        "shape": "circle",
        "preset_id": "dnd5e-spell-sphere",
        "style": {
            "stroke": "rgba(125, 211, 252, 0.96)",
            "fill": "rgba(125, 211, 252, 0.16)",
            "strokeWidth": 2,
        },
        "start": {"worldX": 10, "worldY": 20},
        "end": {"worldX": 40, "worldY": 20},
    }

    scenes.upsert_board_area_marker(scene_id=scene["id"], marker=marker)

    assert scenes.list_board_area_markers(scene["id"]) == [
        {
            "id": "marker-1",
            "scene_id": scene["id"],
            "shape": "circle",
            "preset_id": "dnd5e-spell-sphere",
            "style": {
                "stroke": "rgba(125, 211, 252, 0.96)",
                "fill": "rgba(125, 211, 252, 0.16)",
                "strokeWidth": 2.0,
            },
            "start": {"worldX": 10.0, "worldY": 20.0},
            "end": {"worldX": 40.0, "worldY": 20.0},
        }
    ]

    scenes.upsert_board_area_marker(
        scene_id=scene["id"],
        marker={**marker, "shape": "line", "end": {"worldX": 70, "worldY": 20}},
    )

    assert scenes.list_board_area_markers(scene["id"])[0]["shape"] == "line"
    assert scenes.list_board_area_markers(scene["id"])[0]["end"]["worldX"] == 70.0

    scenes.delete_board_area_marker(scene_id=scene["id"], marker_id="marker-1")
    assert scenes.list_board_area_markers(scene["id"]) == []

    scenes.upsert_board_area_marker(scene_id=scene["id"], marker=marker)
    assert scenes.clear_board_area_markers(scene["id"]) is True
    assert scenes.list_board_area_markers(scene["id"]) == []


def test_scene_repository_clears_only_board_drawings(db):
    _campaign_id, scene, _layer = create_scene_stack(db)
    scenes = SceneRepository()
    marker = {
        "id": "marker-1",
        "scene_id": scene["id"],
        "shape": "circle",
        "start": {"worldX": 10, "worldY": 20},
        "end": {"worldX": 40, "worldY": 20},
    }
    drawing = {
        "id": "draw-1",
        "scene_id": scene["id"],
        "kind": "freehand",
        "points": [
            {"worldX": 10, "worldY": 20},
            {"worldX": 12, "worldY": 24},
        ],
        "style": {"stroke": "#facc15", "fill": "none", "strokeWidth": 4},
    }

    scenes.upsert_board_area_marker(scene_id=scene["id"], marker=marker)
    scenes.upsert_board_area_marker(scene_id=scene["id"], marker=drawing)

    assert scenes.clear_board_drawings(scene["id"]) == [
        {
            "id": "marker-1",
            "scene_id": scene["id"],
            "shape": "circle",
            "start": {"worldX": 10.0, "worldY": 20.0},
            "end": {"worldX": 40.0, "worldY": 20.0},
        }
    ]


def test_scene_repository_persists_drawing_owner_and_layer(db):
    _campaign_id, scene, _layer = create_scene_stack(db)
    scenes = SceneRepository()
    scenes.upsert_board_area_marker(
        scene_id=scene["id"],
        marker={
            "id": "draw-1",
            "scene_id": scene["id"],
            "kind": "freehand",
            "points": [{"worldX": 1, "worldY": 2}, {"worldX": 3, "worldY": 4}],
            "owner_id": "user-9",
            "layer": "gm",
        },
    )

    stored = scenes.list_board_area_markers(scene["id"])[0]
    assert stored["owner_id"] == "user-9"
    assert stored["layer"] == "gm"


def test_scene_repository_clear_board_drawings_scoped_to_owner(db):
    _campaign_id, scene, _layer = create_scene_stack(db)
    scenes = SceneRepository()
    for owner in ("user-a", "user-b"):
        scenes.upsert_board_area_marker(
            scene_id=scene["id"],
            marker={
                "id": f"draw-{owner}",
                "scene_id": scene["id"],
                "kind": "freehand",
                "points": [{"worldX": 1, "worldY": 2}, {"worldX": 3, "worldY": 4}],
                "owner_id": owner,
            },
        )

    remaining = scenes.clear_board_drawings(scene["id"], owner_id="user-a")
    ids = [m["id"] for m in remaining]
    assert ids == ["draw-user-b"]


def test_scene_repository_clear_markers_keeps_gm_layer(db):
    _campaign_id, scene, _layer = create_scene_stack(db)
    scenes = SceneRepository()
    scenes.upsert_board_area_marker(
        scene_id=scene["id"],
        marker={
            "id": "shape-game",
            "scene_id": scene["id"],
            "shape": "circle",
            "start": {"worldX": 1, "worldY": 1},
            "end": {"worldX": 2, "worldY": 2},
        },
    )
    scenes.upsert_board_area_marker(
        scene_id=scene["id"],
        marker={
            "id": "shape-gm",
            "scene_id": scene["id"],
            "shape": "circle",
            "layer": "gm",
            "start": {"worldX": 3, "worldY": 3},
            "end": {"worldX": 4, "worldY": 4},
        },
    )

    scenes.clear_board_area_markers(scene["id"], keep_gm_layer=True)
    ids = [m["id"] for m in scenes.list_board_area_markers(scene["id"])]
    assert ids == ["shape-gm"]


def test_scene_repository_persists_and_clears_text_drawing(db):
    _campaign_id, scene, _layer = create_scene_stack(db)
    scenes = SceneRepository()
    text = {
        "id": "text-1",
        "scene_id": scene["id"],
        "kind": "text",
        "position": {"worldX": 30, "worldY": 40},
        "text": "  Beware  ",
        "fontSize": 36,
        "style": {"fill": "#facc15"},
    }

    scenes.upsert_board_area_marker(scene_id=scene["id"], marker=text)

    assert scenes.list_board_area_markers(scene["id"]) == [
        {
            "id": "text-1",
            "scene_id": scene["id"],
            "kind": "text",
            "position": {"worldX": 30.0, "worldY": 40.0},
            "text": "Beware",
            "fontSize": 36.0,
            "style": {"fill": "#facc15"},
        }
    ]
    assert scenes.clear_board_drawings(scene["id"]) == []


def test_scene_asset_and_tile_table_store_uint32_tile_refs(db):
    _campaign_id, scene, layer = create_scene_stack(db)
    asset = SceneAssetRepository().create(
        scene_id=scene["id"],
        kind=SceneAssetKind.RASTER_TILE,
        storage_path="storage/scenes/scene-1/assets/tiles/0_0.webp",
        hash="tile-hash",
        byte_size=1234,
        width=70,
        height=70,
        content_type="image/webp",
    )

    tile = SceneTileRepository().create(
        scene_id=scene["id"],
        layer_id=layer["id"],
        tile_ref=(2**32) - 1,
        asset_id=asset["id"],
        tx=0,
        ty=0,
        width=70,
        height=70,
        hash="tile-hash",
        byte_size=1234,
    )

    assert tile["tile_ref"] == (2**32) - 1
    assert SceneTileRepository().list_by_layer(layer["id"])[0]["asset_id"] == asset["id"]


def test_scene_chunk_record_write_versions_metadata(db):
    _campaign_id, scene, layer = create_scene_stack(db)
    chunks = SceneChunkRepository()

    first = chunks.record_write(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        hash="hash-v1",
        byte_size=8,
        encoding=SceneChunkEncoding.UINT32_TILE_REFS_V1,
    )
    second = chunks.record_write(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        hash="hash-v2",
        byte_size=12,
        encoding=SceneChunkEncoding.UINT32_TILE_REFS_V1,
    )

    assert first["version"] == 1
    assert second["version"] == 2
    assert second["hash"] == "hash-v2"
    assert second["byte_size"] == 12


def test_scene_chunk_record_write_cas_rejects_stale_version(db):
    """STABILIZATION_V1 P1.1 — opt-in CAS on chunk writes detects a stale write."""
    _campaign_id, scene, layer = create_scene_stack(db)
    chunks = SceneChunkRepository()

    first = chunks.record_write(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        hash="hash-v1",
        byte_size=8,
        encoding=SceneChunkEncoding.UINT32_TILE_REFS_V1,
    )
    assert first["version"] == 1

    winner = chunks.record_write(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        hash="hash-v2",
        byte_size=10,
        encoding=SceneChunkEncoding.UINT32_TILE_REFS_V1,
        expected_version=1,
    )
    assert winner is not None
    assert winner["version"] == 2

                                                                        
    loser = chunks.record_write(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        hash="hash-v3",
        byte_size=14,
        encoding=SceneChunkEncoding.UINT32_TILE_REFS_V1,
        expected_version=1,
    )
    assert loser is None

    current = chunks.get_metadata(layer_id=layer["id"], cx=0, cy=0)
    assert current["version"] == 2
    assert current["hash"] == "hash-v2"


def test_scene_chunk_viewport_range_returns_only_intersecting_chunks(db):
    _campaign_id, scene, layer = create_scene_stack(db)
    chunks = SceneChunkRepository()

    for cx, cy in [(0, 0), (1, 0), (3, 3)]:
        chunks.record_write(
            scene_id=scene["id"],
            layer_id=layer["id"],
            cx=cx,
            cy=cy,
            hash=f"hash-{cx}-{cy}",
            byte_size=8,
            encoding=SceneChunkEncoding.UINT32_TILE_REFS_V1,
        )

    rows = chunks.list_by_viewport_chunk_range(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx0=0,
        cy0=0,
        cx1=1,
        cy1=1,
    )

    assert [(row["cx"], row["cy"]) for row in rows] == [(0, 0), (1, 0)]


def test_scene_repository_board_version_rejects_stale_updates(db):
    _campaign_id, scene, _layer = create_scene_stack(db)
    scenes = SceneRepository()
    marker_a = {
        "id": "marker-a",
        "scene_id": scene["id"],
        "shape": "circle",
        "start": {"worldX": 10, "worldY": 20},
        "end": {"worldX": 40, "worldY": 20},
    }
    marker_b = {
        "id": "marker-b",
        "scene_id": scene["id"],
        "shape": "line",
        "start": {"worldX": 11, "worldY": 21},
        "end": {"worldX": 41, "worldY": 21},
    }

    initial_version = scenes.get_board_version(scene["id"])
    assert initial_version == 1

    updated = scenes.upsert_board_area_marker(
        scene_id=scene["id"],
        marker=marker_a,
        expected_board_version=initial_version,
    )
    assert updated is not None
    assert scenes.get_board_version(scene["id"]) == initial_version + 1

    stale = scenes.upsert_board_area_marker(
        scene_id=scene["id"],
        marker=marker_b,
        expected_board_version=initial_version,
    )
    assert stale is None
    assert [m["id"] for m in scenes.list_board_area_markers(scene["id"])] == ["marker-a"]
