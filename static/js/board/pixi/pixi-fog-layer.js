






(() => {
    const proto = window.GravewrightBoardInternals.PixiBoardRenderer.prototype;

    Object.assign(proto, {
        
        
        
        
        
        
        
        _renderFog(board, cssW, cssH) {
            const fog = this.fog;
            const scene = this.scene;

            if (!fog || !fog.enabled || !scene) {
                board.fogSprite.visible = false;
                board.fogUiGfx.visible = false;
                board.fogUiGfx.clear();
                board.fogKey = "";
                return;
            }

            const cam = this.camera;
            const dpr = window.devicePixelRatio || 1;
            const rt = this._ensureFogRT(board, cssW, cssH, dpr);

            
            
            const key = [
                cam.offsetX, cam.offsetY, cam.zoom,
                fog.baseline, fog.opsVersion ?? (fog.ops?.length || 0),
                cssW, cssH, dpr, scene.scaledTileSize,
            ].join(":");

            if (board.fogKey !== key) {
                board.fogKey = key;
                this._composeFog(board, fog, scene, cam, rt);
            }

            board.fogSprite.texture = rt;
            board.fogSprite.position.set(0, 0);
            board.fogSprite.width = cssW;
            board.fogSprite.height = cssH;
            board.fogSprite.alpha = fog.alpha ?? 1;
            board.fogSprite.visible = true;

            this._renderFogUi(board, fog, scene, cam);
        },

        _ensureFogRT(board, cssW, cssH, dpr) {
            if (board.fogRT && board.fogRTW === cssW && board.fogRTH === cssH && board.fogRTDpr === dpr) {
                return board.fogRT;
            }
            if (board.fogRT) board.fogRT.destroy(true);
            board.fogRT = PIXI.RenderTexture.create({
                width: Math.max(1, cssW),
                height: Math.max(1, cssH),
                resolution: dpr,
            });
            board.fogRTW = cssW;
            board.fogRTH = cssH;
            board.fogRTDpr = dpr;
            board.fogKey = ""; 
            return board.fogRT;
        },

        _composeFog(board, fog, scene, cam, rt) {
            const tileSize = scene.scaledTileSize;
            const zoom = cam.zoom;
            const sx0 = cam.offsetX;
            const sy0 = cam.offsetY;
            const cellsToPx = (cells) => cells * tileSize * zoom;
            const toScreenX = (cells) => cells * tileSize * zoom + sx0;
            const toScreenY = (cells) => cells * tileSize * zoom + sy0;

            this._resetFogPool(board);

            
            
            let run = null;
            let runMode = null;
            const ensureRun = (mode) => {
                if (run && runMode === mode) return run;
                run = this._acquireFogGfx(board);
                run.blendMode = mode === "reveal" ? "erase" : "normal";
                runMode = mode;
                return run;
            };

            if (fog.baseline === "hide_all") {
                ensureRun("hide")
                    .rect(sx0, sy0, scene.width * zoom, scene.height * zoom)
                    .fill({ color: 0x000000, alpha: 1 });
            }

            for (const op of fog.ops || []) {
                const g = ensureRun(op.mode === "reveal" ? "reveal" : "hide");
                const geom = op.geom || {};

                if (op.shape === "circle") {
                    g.circle(
                        toScreenX(geom.center_x_cells),
                        toScreenY(geom.center_y_cells),
                        Math.max(0.5, cellsToPx(geom.radius_cells)),
                    ).fill({ color: 0x000000, alpha: 1 });
                } else if (op.shape === "square") {
                    const sizePx = cellsToPx(geom.size_cells);
                    g.rect(
                        toScreenX(geom.center_x_cells - geom.size_cells / 2),
                        toScreenY(geom.center_y_cells - geom.size_cells / 2),
                        sizePx, sizePx,
                    ).fill({ color: 0x000000, alpha: 1 });
                } else if (op.shape === "polygon") {
                    const pts = geom.points_cells || [];
                    if (pts.length >= 3) {
                        const flat = [];
                        pts.forEach((p) => flat.push(toScreenX(p[0]), toScreenY(p[1])));
                        g.poly(flat).fill({ color: 0x000000, alpha: 1 });
                    }
                }
            }

            board.app.renderer.render({ container: board.fogScene, target: rt, clear: true });
        },

        _resetFogPool(board) {
            board.fogScene.removeChildren();
            board.fogPoolIndex = 0;
            board.fogGfxPool.forEach((g) => {
                g.clear();
                g.blendMode = "normal";
            });
        },

        _acquireFogGfx(board) {
            let g = board.fogGfxPool[board.fogPoolIndex];
            if (!g) {
                g = new PIXI.Graphics();
                board.fogGfxPool[board.fogPoolIndex] = g;
            }
            board.fogPoolIndex += 1;
            board.fogScene.addChild(g);
            return g;
        },

        _renderFogUi(board, fog, scene, cam) {
            const g = board.fogUiGfx;
            g.clear();

            const ip = fog.inProgress;
            if (!ip || !ip.points || ip.points.length < 1) {
                g.visible = false;
                return;
            }
            g.visible = true;

            const tileSize = scene.scaledTileSize;
            const zoom = cam.zoom;
            const sx0 = cam.offsetX;
            const sy0 = cam.offsetY;
            const sx = (p) => p.x_cells * tileSize * zoom + sx0;
            const sy = (p) => p.y_cells * tileSize * zoom + sy0;

            const accent = ip.mode === "hide" ? 0xffc8c8 : 0x78c8ff;
            const firstAccent = 0xffdc78;

            if (ip.points.length >= 2) {
                const pts = ip.points.map((p) => ({ x: sx(p), y: sy(p) }));
                this._dashedPolyline(g, pts, 4, 4);
                g.stroke({ width: 1.5, color: accent, alpha: 0.95 });
            }

            ip.points.forEach((p, i) => {
                g.circle(sx(p), sy(p), i === 0 ? 6 : 4)
                    .fill({ color: i === 0 ? firstAccent : accent, alpha: i === 0 ? 1 : 0.95 })
                    .stroke({ width: 1, color: 0x000000, alpha: 0.6 });
            });
        },

        
        _dashedPolyline(g, pts, dash, gap) {
            for (let i = 0; i < pts.length - 1; i += 1) {
                const a = pts[i];
                const b = pts[i + 1];
                const dx = b.x - a.x;
                const dy = b.y - a.y;
                const len = Math.hypot(dx, dy);
                if (len < 0.001) continue;
                const ux = dx / len;
                const uy = dy / len;
                for (let d = 0; d < len; d += dash + gap) {
                    const e = Math.min(d + dash, len);
                    g.moveTo(a.x + ux * d, a.y + uy * d)
                        .lineTo(a.x + ux * e, a.y + uy * e);
                }
            }
        },
    });
})();
