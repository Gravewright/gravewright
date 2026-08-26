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
            grid_x: Math.floor((world.worldX - (scene.gridOffsetX || 0)) / s),
            grid_y: Math.floor((world.worldY - (scene.gridOffsetY || 0)) / s),
        };
    }

    function clampGridPosition(gridX, gridY, scene, token) {
        const wCells = token?.width_cells || 1;
        const hCells = token?.height_cells || 1;
        return {
            grid_x: Math.max(0, Math.min(Math.floor((scene.width - (scene.gridOffsetX || 0)) / scene.scaledTileSize) - wCells, gridX)),
            grid_y: Math.max(0, Math.min(Math.floor((scene.height - (scene.gridOffsetY || 0)) / scene.scaledTileSize) - hCells, gridY)),
        };
    }

    function snapDragToGrid(worldX, worldY, scene, token, snap = true) {
        const gridX = (worldX - (scene.gridOffsetX || 0)) / scene.scaledTileSize;
        const gridY = (worldY - (scene.gridOffsetY || 0)) / scene.scaledTileSize;
        return clampGridPosition(
            snap ? Math.round(gridX) : Math.round(gridX * 10000) / 10000,
            snap ? Math.round(gridY) : Math.round(gridY * 10000) / 10000,
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
