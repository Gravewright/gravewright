from __future__ import annotations

import pytest

from app.domain.scenes import RenderPriority
from app.domain.scenes import RenderPriorityAgingPolicy
from app.domain.scenes import SceneDimensions
from app.domain.scenes import SceneTile
from app.domain.scenes import TileCoord
from app.domain.scenes import UINT32_MAX


def test_scene_dimensions_use_tile_size_as_grid_size():
    dimensions = SceneDimensions(
        width=1400,
        height=1400,
        tile_size=70,
        chunk_size=16,
    )

    assert dimensions.grid_size == 70
    assert dimensions.tile_columns == 20
    assert dimensions.tile_rows == 20
    assert dimensions.chunk_columns == 2
    assert dimensions.chunk_rows == 2
    assert dimensions.chunk_pixel_size == 1120


def test_scene_dimensions_round_partial_edge_tiles_up():
    dimensions = SceneDimensions(
        width=1401,
        height=1400,
        tile_size=70,
        chunk_size=16,
    )

    assert dimensions.tile_columns == 21
    assert dimensions.tile_rows == 20
    assert dimensions.chunk_columns == 2


def test_scene_tile_accepts_uint32_refs():
    tile = SceneTile(
        scene_id="scene-1",
        layer_id="layer-1",
        tile_ref=UINT32_MAX,
        asset_id="asset-1",
        coord=TileCoord(tx=0, ty=0),
        width=70,
        height=70,
        hash="hash",
        byte_size=1024,
    )

    assert tile.tile_ref == UINT32_MAX


def test_scene_tile_reserves_zero_ref_for_empty_tile():
    with pytest.raises(ValueError, match="tile_ref"):
        SceneTile(
            scene_id="scene-1",
            layer_id="layer-1",
            tile_ref=0,
            asset_id="asset-1",
            coord=TileCoord(tx=0, ty=0),
            width=70,
            height=70,
            hash="hash",
            byte_size=1024,
        )


def test_render_priority_has_five_levels():
    assert list(RenderPriority) == [
        RenderPriority.IMMEDIATE,
        RenderPriority.HIGH,
        RenderPriority.NORMAL,
        RenderPriority.LOW,
        RenderPriority.BACKGROUND,
    ]


def test_render_priority_aging_promotes_waiting_items_without_passing_cap():
    policy = RenderPriorityAgingPolicy(
        promote_after_ms=100,
        max_aged_priority=RenderPriority.HIGH,
    )

    assert policy.effective_priority(
        base_priority=RenderPriority.BACKGROUND,
        waited_ms=0,
    ) == RenderPriority.BACKGROUND
    assert policy.effective_priority(
        base_priority=RenderPriority.BACKGROUND,
        waited_ms=100,
    ) == RenderPriority.LOW
    assert policy.effective_priority(
        base_priority=RenderPriority.BACKGROUND,
        waited_ms=200,
    ) == RenderPriority.NORMAL
    assert policy.effective_priority(
        base_priority=RenderPriority.BACKGROUND,
        waited_ms=300,
    ) == RenderPriority.HIGH
    assert policy.effective_priority(
        base_priority=RenderPriority.BACKGROUND,
        waited_ms=1000,
    ) == RenderPriority.HIGH
