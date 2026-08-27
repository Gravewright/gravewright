from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_sparse_tile_descriptors_invalidate_cached_pixi_plan() -> None:
    streaming = (ROOT / "static/js/map/streaming/map-streaming.js").read_text(encoding="utf-8")
    renderer = (ROOT / "static/js/board/pixi/pixi-tile-layer.js").read_text(encoding="utf-8")

    assert "runtime.tileDescriptorRevision += 1" in streaming
    assert "tiles.tileDescriptorRevision || 0" in renderer


def test_pixi_tile_plan_is_reused_while_visible_tile_range_is_unchanged() -> None:
    renderer = (ROOT / "static/js/board/pixi/pixi-tile-layer.js").read_text(encoding="utf-8")
    cache_key = renderer.split("const key = [", 1)[1].split("] .join", 1)[0] if "] .join" in renderer else renderer.split("const key = [", 1)[1].split("].join", 1)[0]

    assert "view.tx0" in cache_key
    assert "view.ty1" in cache_key
    assert "view.centerTx" not in cache_key
    assert "view.centerTy" not in cache_key


def test_pan_defers_camera_persistence_until_after_drag_finishes() -> None:
    pan = (ROOT / "static/js/map/camera/map-pan.js").read_text(encoding="utf-8")
    update_body = pan.split("function update(event)", 1)[1].split("function stop(event)", 1)[0]

    assert "scheduleCameraSave" not in update_body
    assert "saveCameraNow" not in pan
    assert "scheduleCameraSave(activePan.canvas)" in pan


def test_viewport_updates_keep_one_trailing_timer_during_pan() -> None:
    streaming = (ROOT / "static/js/map/streaming/map-streaming.js").read_text(encoding="utf-8")
    scheduler = streaming.split("function scheduleViewportUpdate", 1)[1].split(
        "function sendViewportUpdate", 1
    )[0]

    assert "if (!immediate && runtime.pendingTimer) return;" in scheduler
    assert "if (immediate && runtime.pendingTimer)" in scheduler


def test_tile_scheduler_prioritizes_visible_current_generation_work() -> None:
    renderer = (ROOT / "static/js/board/pixi/pixi-board-renderer.js").read_text(encoding="utf-8")
    tiles = (ROOT / "static/js/board/pixi/pixi-tile-layer.js").read_text(encoding="utf-8")

    assert "this.maxTextureLoads" in renderer
    assert "b.generation - a.generation" in renderer
    assert "request.visible ? 0 : 1_000_000" in renderer
    assert "_dropObsoleteQueuedTextures" in renderer
    assert 'job.lifecycle.cancelled = "obsolete_generation_while_queued"' in renderer
    assert "generation: this.tiles?.generation || 0" in tiles
    assert "visibleTx0" in tiles


def test_directional_prefetch_is_bounded_and_affects_priority() -> None:
    tiles = (ROOT / "static/js/board/pixi/pixi-tile-layer.js").read_text(encoding="utf-8")

    assert "const TILE_FORWARD_MARGIN = 6" in tiles
    assert "const MAX_LEAD = TILE_FORWARD_MARGIN" in tiles
    assert "directionalProgress" in tiles
    assert "directionalPenalty" in tiles
    assert "Number(b.visible) - Number(a.visible)" in tiles


def test_texture_materialization_has_a_per_frame_budget() -> None:
    renderer = (ROOT / "static/js/board/pixi/pixi-board-renderer.js").read_text(encoding="utf-8")
    tiles = (ROOT / "static/js/board/pixi/pixi-tile-layer.js").read_text(encoding="utf-8")

    assert "this.maxTextureMaterializationsPerFrame" in renderer
    assert "board.textureMaterializationsThisFrame = 0" in renderer
    assert "board.deferredTextureMaterializations > 0" in renderer
    assert "board.textureMaterializationsThisFrame >= this.maxTextureMaterializationsPerFrame" in tiles
    assert "_enforceTextureBudget()" in renderer
    assert "this.textureCacheEvictions" in renderer
    assert "MAX_BYTES" in renderer
    assert "evictedBytes" in renderer
    assert "createImageBitmap(source.blob)" in renderer
    assert '"image_decode"' in renderer
    assert '"texture_create"' in renderer
    assert "_updateAdaptiveTextureBudget" in renderer
    assert "adaptive_prefetch_pause" in renderer
    assert 'this.textureGovernorState = "idle"' in renderer
    assert "board.deferredVisibleTextureMaterializations > 0" in renderer
    assert "textureMaterializationCostEmaMs" in renderer
    assert '"texture_materialization"' in renderer
    assert "deferredVisibleTextureMaterializations" in tiles


def test_texture_decoder_concurrency_adapts_to_real_decode_cost() -> None:
    renderer = (ROOT / "static/js/board/pixi/pixi-board-renderer.js").read_text(encoding="utf-8")
    debug = (ROOT / "static/js/board/pixi/pixi-debug.js").read_text(encoding="utf-8")
    quality = (ROOT / "static/js/game/graphics-quality.js").read_text(encoding="utf-8")

    assert "this.textureConcurrencyCeiling" in renderer
    assert "_updateAdaptiveTextureConcurrency(decodeDuration)" in renderer
    assert "duration >= 180 || this.textureDecodeCostEmaMs >= 120" in renderer
    assert "Math.ceil(this.maxTextureLoads / 2)" in renderer
    assert "this.textureDecodeHeadroomSamples < 8" in renderer
    assert "performance.now() + 500" in renderer
    assert "textureConcurrency: 2" in quality
    assert "textureConcurrency: 3" in quality
    assert "textureConcurrency: 5" in quality
    assert "textureDecodeGovernor" in debug
    assert "active: this.maxTextureLoads" in debug
    assert "costEmaMs: this.textureDecodeCostEmaMs" in debug


def test_persistent_tile_cache_is_named_as_encoded_indexeddb_blob() -> None:
    renderer = (ROOT / "static/js/board/pixi/pixi-board-renderer.js").read_text(encoding="utf-8")

    assert 'lifecycle.cache = "indexeddb_blob_hit"' in renderer
    assert "decoded_blob_cache_hit" not in renderer


def test_scene_switch_releases_previous_scene_sprites_and_textures() -> None:
    renderer = (ROOT / "static/js/board/pixi/pixi-board-renderer.js").read_text(encoding="utf-8")
    set_scene = renderer.split("setScene(scene)", 1)[1].split("setCamera(camera)", 1)[0]

    assert "previousSceneId !== nextSceneId" in set_scene
    assert "this._releaseSceneTiles()" in set_scene
    assert "board.tileSprites?.clear()" in set_scene
    assert "urls.forEach((url) => this._forgetTexture(url))" in set_scene
