(() => {
    function screenToWorldXY(screenX, screenY, state) {
        return {
            worldX: (screenX - state.offsetX) / state.zoom,
            worldY: (screenY - state.offsetY) / state.zoom,
        };
    }

    function screenToGridXY(screenX, screenY, state, scene) {
        const s = scene.scaledTileSize;
        const world = screenToWorldXY(screenX, screenY, state);
        return {
            grid_x: Math.floor(world.worldX / s),
            grid_y: Math.floor(world.worldY / s),
        };
    }

    function clampGridPosition(gridX, gridY, scene, token) {
        const wCells = token?.width_cells || 1;
        const hCells = token?.height_cells || 1;
        return {
            grid_x: Math.max(0, Math.min(Math.floor(scene.width / scene.scaledTileSize) - wCells, gridX)),
            grid_y: Math.max(0, Math.min(Math.floor(scene.height / scene.scaledTileSize) - hCells, gridY)),
        };
    }

    function snapDragToGrid(worldX, worldY, scene, token) {
        return clampGridPosition(
            Math.round(worldX / scene.scaledTileSize),
            Math.round(worldY / scene.scaledTileSize),
            scene,
            token,
        );
    }

    window.GravewrightMapDrag = {
        clampGridPosition,
        screenToGridXY,
        screenToWorldXY,
        snapDragToGrid,
    };
})();
