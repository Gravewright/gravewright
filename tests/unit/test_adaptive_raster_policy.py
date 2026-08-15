from __future__ import annotations

import pytest

from app.engine.scenes.adaptive_raster_policy import (
    ADAPTIVE_RASTER_POLICY_VERSION,
    SUPPORTED_RASTER_TILE_SIZES,
    choose_raster_granularity,
)


def test_policy_enumerates_supported_candidates_and_selects_256_for_light_5k() -> None:
    decision = choose_raster_granularity(width=5_000, height=5_000, source_bytes=3_407_325)
    assert tuple(item.tile_size for item in decision.candidates) == SUPPORTED_RASTER_TILE_SIZES
    assert decision.tile_size == 256
    assert decision.policy_version == ADAPTIVE_RASTER_POLICY_VERSION
    candidate = next(item for item in decision.candidates if item.tile_size == 256)
    assert candidate.tile_count == 400
    assert candidate.chunk_count == 4


def test_policy_handles_partial_edges_extreme_aspect_and_small_images() -> None:
    extreme = choose_raster_granularity(width=30_000, height=2_000, source_bytes=8_000_000)
    assert extreme.tile_size in SUPPORTED_RASTER_TILE_SIZES
    tiny = choose_raster_granularity(width=500, height=500, source_bytes=50_000)
    assert all(item.tile_count >= 1 for item in tiny.candidates)


@pytest.mark.parametrize("field", ["width", "height", "source_bytes", "chunk_span"])
def test_policy_rejects_invalid_inputs(field: str) -> None:
    values = {"width": 100, "height": 100, "source_bytes": 100, "chunk_span": 16}
    values[field] = 0
    with pytest.raises(ValueError):
        choose_raster_granularity(**values)
