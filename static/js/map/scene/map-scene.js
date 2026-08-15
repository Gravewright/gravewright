(() => {
    function createSceneController(options = {}) {
        const defaultGridSize = options.defaultGridSize || 56;
        const minZoom = options.minZoom || 0.35;
        const maxZoom = options.maxZoom || 3.2;

        function clampOpacity(raw, fallback) {
            const value = parseFloat(raw);
            if (!Number.isFinite(value)) return fallback;
            return Math.max(0, Math.min(1, value));
        }

        function finiteNumber(raw, fallback) {
            const value = parseFloat(raw);
            return Number.isFinite(value) ? value : fallback;
        }

        function clampZoom(raw, fallback) {
            const value = parseFloat(raw);
            if (!Number.isFinite(value)) return fallback;
            return Math.max(minZoom, Math.min(maxZoom, value));
        }

        function sceneDataFor(canvas) {
            const sceneId = canvas.dataset.sceneId;
            if (!sceneId) return null;

            const imageScale = parseFloat(canvas.dataset.sceneImageScale) || 1.0;
            const baseWidth = parseInt(canvas.dataset.sceneWidth, 10);
            const baseHeight = parseInt(canvas.dataset.sceneHeight, 10);
            const legacyTileSize = parseInt(canvas.dataset.sceneTileSize, 10) || defaultGridSize;
            const gridSize = parseInt(canvas.dataset.sceneGridSize, 10) || legacyTileSize;
            const rasterTileSize = parseInt(canvas.dataset.sceneRasterTileSize, 10) || legacyTileSize;

            return {
                id: sceneId,
                width: Math.round(baseWidth * imageScale),
                height: Math.round(baseHeight * imageScale),
                baseWidth,
                baseHeight,
                tileSize: gridSize,
                gridSize,
                rasterTileSize,
                scaledTileSize: gridSize * imageScale,
                scaledRasterTileSize: rasterTileSize * imageScale,
                imageScale,
                gridVisible: canvas.dataset.sceneGridVisible !== "false",
                gridColor: canvas.dataset.sceneGridColor || null,
                gridOpacity: clampOpacity(canvas.dataset.sceneGridOpacity, 0.4),
                darkness: clampOpacity(canvas.dataset.sceneDarkness, 0),
                startWorldX: finiteNumber(canvas.dataset.sceneStartWorldX, baseWidth / 2),
                startWorldY: finiteNumber(canvas.dataset.sceneStartWorldY, baseHeight / 2),
                startZoom: clampZoom(canvas.dataset.sceneStartZoom, 1),
                layerId: canvas.dataset.sceneLayerId || null,
                tileVersion: parseInt(canvas.dataset.sceneTileVersion, 10) || 1,
            };
        }

        function viewportSizeFor(canvas) {
            const rect = canvas.getBoundingClientRect();
            return {
                width: rect.width || canvas.clientWidth || window.innerWidth,
                height: rect.height || canvas.clientHeight || window.innerHeight,
            };
        }

        return {
            clampZoom,
            sceneDataFor,
            viewportSizeFor,
        };
    }

    window.GravewrightMapScene = { createSceneController };
})();
