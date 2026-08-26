




(() => {
    const proto = window.GravewrightBoardInternals.PixiBoardRenderer.prototype;

    Object.assign(proto, {
        _renderGhosts(board) {
            const g = board.ghostsGfx;
            g.clear();

            const positions = this.overlays.ghosts;
            const scene = this.scene;
            if (!positions?.length || !scene) return;

            const cam = this.camera;
            const zoom = Math.max(0.001, cam.zoom || 1);
            const s = scene.scaledTileSize;

            positions.forEach((pos) => {
                const wx = (scene.gridOffsetX || 0) + pos.grid_x * s;
                const wy = (scene.gridOffsetY || 0) + pos.grid_y * s;
                const ww = s * (pos.width_cells || 1);
                const wh = s * (pos.height_cells || 1);
                const cx = wx + ww / 2;
                const cy = wy + wh / 2;
                const radius = Math.min(ww, wh) * 0.42;

                g.circle(cx, cy, radius)
                    .fill({ color: 0xb9995d, alpha: 0.182 })
                    .stroke({ width: 2 / zoom, color: 0xe8c87e, alpha: 0.52 });
            });
        },
    });
})();
