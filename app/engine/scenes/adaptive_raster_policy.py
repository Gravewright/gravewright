from __future__ import annotations

import math
from dataclasses import dataclass


# A raster page has a fixed scheduling/decoding cost in the browser even when
# the encoded WebP is tiny. 64/128 px pages made small, screen-sized maps fan
# out into hundreds of createImageBitmap calls and could stall low-end clients.
# Keep manual legacy retile compatibility in MapUploadService, but never select
# those page sizes for a new adaptive upload.
SUPPORTED_RASTER_TILE_SIZES = (256, 512, 1024)
ADAPTIVE_RASTER_POLICY_VERSION = 2


@dataclass(frozen=True)
class RasterCandidate:
    tile_size: int
    tile_count: int
    chunk_count: int
    expected_viewport_tiles: int
    estimated_metadata_bytes: int
    estimated_overfetch_pixels: int
    estimated_cost: float


@dataclass(frozen=True)
class RasterPolicyDecision:
    tile_size: int
    chunk_span: int
    policy_version: int
    mode: str
    compression_density: float
    candidates: tuple[RasterCandidate, ...]


def choose_raster_granularity(
    *, width: int, height: int, source_bytes: int, chunk_span: int = 16,
    viewport_width: int = 1920, viewport_height: int = 1080,
) -> RasterPolicyDecision:
    if width <= 0 or height <= 0 or source_bytes <= 0 or chunk_span <= 0:
        raise ValueError("positive image dimensions, source bytes and chunk span are required")
    pixels = width * height
    density = source_bytes / pixels
    candidates: list[RasterCandidate] = []
    for size in SUPPORTED_RASTER_TILE_SIZES:
        columns, rows = math.ceil(width / size), math.ceil(height / size)
        tile_count = columns * rows
        chunk_count = math.ceil(columns / chunk_span) * math.ceil(rows / chunk_span)
        viewport_columns = math.ceil(viewport_width / size) + 2
        viewport_rows = math.ceil(viewport_height / size) + 2
        viewport_tiles = min(tile_count, viewport_columns * viewport_rows)
        covered = viewport_columns * size * viewport_rows * size
        overfetch = max(0, covered - viewport_width * viewport_height)
        metadata = tile_count * 32 + chunk_count * 96
        # Administrative work penalizes tiny pages; overfetch/prefetch risk
        # penalizes coarse pages. Density turns pixel waste into expected bytes.
        scheduler_cost = viewport_tiles * 8_192
        overfetch_cost = overfetch * density * 3.0
        metadata_cost = metadata * 3.0
        cost = metadata_cost + scheduler_cost + overfetch_cost
        candidates.append(RasterCandidate(size, tile_count, chunk_count, viewport_tiles, metadata, overfetch, cost))
    selected = min(candidates, key=lambda item: (item.estimated_cost, item.tile_size))
    return RasterPolicyDecision(
        tile_size=selected.tile_size, chunk_span=chunk_span,
        policy_version=ADAPTIVE_RASTER_POLICY_VERSION, mode="adaptive",
        compression_density=density, candidates=tuple(candidates),
    )
