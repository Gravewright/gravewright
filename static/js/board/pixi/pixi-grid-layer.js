





(() => {
    const screenFromWorld = (value, offset, zoom) => value * zoom + offset;

    const proto = window.GravewrightBoardInternals.PixiBoardRenderer.prototype;

    Object.assign(proto, {
        _renderGrid(board, cssW, cssH) {
            const g = board.gridGfx;
            const border = board.borderGfx;

            g.clear();
            border.clear();

            const scene = this.scene;
            const cam = this.camera;

            if (!scene) return;

            const gridSize = scene.scaledTileSize;
            const scaledGrid = gridSize * cam.zoom;
            const visible = scene.gridVisible;

            if (!visible || scaledGrid <= 0) return;

            const color = this._gridColor();

            const sceneX = Math.round(screenFromWorld(0, cam.offsetX, cam.zoom));
            const sceneY = Math.round(screenFromWorld(0, cam.offsetY, cam.zoom));
            const sceneW = Math.round(scene.width * cam.zoom);
            const sceneH = Math.round(scene.height * cam.zoom);

            if (sceneW <= 0 || sceneH <= 0) return;

            
            
            const clipX = Math.max(0, sceneX);
            const clipY = Math.max(0, sceneY);
            const clipRight = Math.min(cssW, sceneX + sceneW);
            const clipBottom = Math.min(cssH, sceneY + sceneH);
            const clipW = clipRight - clipX;
            const clipH = clipBottom - clipY;

            if (clipW <= 0 || clipH <= 0) return;

            let startX = Math.floor((clipX - cam.offsetX) / scaledGrid) - 1;
            let endX = Math.ceil((clipRight - cam.offsetX) / scaledGrid) + 1;
            let startY = Math.floor((clipY - cam.offsetY) / scaledGrid) - 1;
            let endY = Math.ceil((clipBottom - cam.offsetY) / scaledGrid) + 1;

            const maxGridX = Math.floor(scene.width / gridSize);
            const maxGridY = Math.floor(scene.height / gridSize);

            startX = Math.max(0, startX);
            endX = Math.min(maxGridX, endX);
            startY = Math.max(0, startY);
            endY = Math.min(maxGridY, endY);

            
            
            if (scaledGrid >= 4) {
                for (let gx = startX; gx <= endX; gx += 1) {
                    const x = Math.round(screenFromWorld(gx * gridSize, cam.offsetX, cam.zoom));

                    if (x < clipX || x > clipRight) continue;

                    g.rect(x, clipY, 1, clipH).fill({
                        color: color.color,
                        alpha: color.alpha,
                    });
                }

                for (let gy = startY; gy <= endY; gy += 1) {
                    const y = Math.round(screenFromWorld(gy * gridSize, cam.offsetY, cam.zoom));

                    if (y < clipY || y > clipBottom) continue;

                    g.rect(clipX, y, clipW, 1).fill({
                        color: color.color,
                        alpha: color.alpha,
                    });
                }
            }

            const borderColor = this._color(this.theme.sceneBorderColor);

            
            border.rect(sceneX, sceneY, sceneW, 2).fill({
                color: borderColor,
                alpha: 1,
            });

            border.rect(sceneX, sceneY + sceneH - 2, sceneW, 2).fill({
                color: borderColor,
                alpha: 1,
            });

            border.rect(sceneX, sceneY, 2, sceneH).fill({
                color: borderColor,
                alpha: 1,
            });

            border.rect(sceneX + sceneW - 2, sceneY, 2, sceneH).fill({
                color: borderColor,
                alpha: 1,
            });
        },

        _gridColor() {
            const scene = this.scene;

            if (scene && scene.gridColor) {
                return {
                    color: this._color(scene.gridColor),
                    alpha: scene.gridOpacity,
                };
            }

            return this._colorAlpha(this.theme.gridColor);
        },
    });
})();
