from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]


def test_gm_hint_warms_indexeddb_without_materializing_a_texture() -> None:
    """Exercise the browser pipeline, not just source-code contracts.

    The page receives one authorized GM hint with an already-known chunk and
    descriptor. Chromium must fetch the tile once, persist its Blob in
    IndexedDB, and never invoke createImageBitmap (the GPU/decode boundary).
    """

    tile_url = "http://gravewright.test/game/scenes/scene/tiles/layer/0/0"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.route(
            "http://gravewright.test/",
            lambda route: route.fulfill(
                status=200,
                content_type="text/html",
                body='<body data-gm-guided-prefetch="true"><canvas data-map-canvas data-scene-id="scene"></canvas></body>',
            ),
        )
        page.route(
            "**/game/scenes/scene/tiles/**",
            lambda route: route.fulfill(status=200, content_type="image/png", body=b"encoded-tile"),
        )
        page.goto("http://gravewright.test/")
        page.add_script_tag(path=str(ROOT / "static/js/board/pixi/pixi-board-renderer.js"))
        page.add_script_tag(path=str(ROOT / "static/js/map/streaming/map-streaming.js"))

        result = page.evaluate(
            """
            async (tileUrl) => {
                let bitmapCalls = 0;
                window.createImageBitmap = async () => { bitmapCalls += 1; throw new Error("must not decode"); };
                const canvas = document.querySelector("[data-map-canvas]");
                const scene = {
                    id: "scene", baseWidth: 256, baseHeight: 256,
                    tileSize: 256, rasterTileSize: 256,
                    scaledTileSize: 256, scaledRasterTileSize: 256,
                };
                const streaming = window.GravewrightMapStreaming.createSceneStreaming({
                    api: { loadSceneTileIndex: async () => ({ tiles: [] }) },
                    applyCameraToState() {}, applyMeasureSnapshot() {},
                    chunkHeaderBytes: 0, chunkMagic: 0, defaultChunkSize: 1,
                    initialCameraFor() {}, loadTokensForScene() {}, markDirty() {},
                    maxRetries: 0, pullMs: 10, retryMs: 10,
                    sceneDataFor: () => scene, selection: {},
                    stateFor: () => ({ offsetX: 0, offsetY: 0, zoom: 1 }),
                    tokens: {}, tokenStoreFor: () => new Map(),
                    viewportSizeFor: () => ({ width: 256, height: 256 }),
                    viewportUpdateMs: 50, viewChunkMargin: 1,
                });
                const runtime = streaming.runtimeFor(canvas);
                runtime.manifest = {
                    scene_id: "scene", scene_format_version: 1, chunk_size: 1,
                    layers: [{ layer_id: "layer", tiles: [{ tile_ref: 7, url: tileUrl }] }],
                };
                runtime.tileTables = streaming.buildTileTables(runtime.manifest);
                runtime.chunks.set("layer:0:0", { layerId: "layer", cx: 0, cy: 0, refs: [7] });

                await streaming.handleGmPrefetchHint({
                    scene_id: "scene", cx0: 0, cy0: 0, cx1: 0, cy1: 0,
                    layer_ids: ["layer"], expires_at_ms: Date.now() + 60_000,
                });
                const deadline = Date.now() + 5_000;
                while (runtime.gmPrefetchActive && Date.now() < deadline) {
                    await new Promise((resolve) => setTimeout(resolve, 10));
                }
                const cached = await window.GravewrightTileBlobCache.get(tileUrl);
                return { bitmapCalls, cachedSize: cached?.size || 0, metrics: runtime.metrics };
            }
            """,
            tile_url,
        )
        browser.close()

    assert result["cachedSize"] == len(b"encoded-tile")
    assert result["bitmapCalls"] == 0
    assert result["metrics"]["gm_hint_prefetch_requested"] == 1
    assert result["metrics"]["gm_hint_prefetch_completed"] == 1
    assert result["metrics"]["gm_hint_bytes_downloaded"] == len(b"encoded-tile")
