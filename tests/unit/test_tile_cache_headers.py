from __future__ import annotations

from app.actions.game.serve_scene_tile import _TILE_CACHE_HEADERS


def test_scene_tiles_use_private_cache_header() -> None:
    assert _TILE_CACHE_HEADERS["Cache-Control"] == "private, max-age=31536000, immutable"
