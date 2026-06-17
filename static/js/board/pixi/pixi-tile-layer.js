





(() => {
    const DEFAULT_CHUNK_SIZE = 16;
    
    
    const VIEW_CHUNK_MARGIN = 1;
    
    
    
    const TILE_VIEW_MARGIN = 3;
    
    
    
    const EVICT_MARGIN_TILES = 64;

    const proto = window.GravewrightBoardInternals.PixiBoardRenderer.prototype;

    Object.assign(proto, {
        _renderTiles(board, cssW, cssH) {
            const tiles = this.tiles;
            const scene = this.scene;
            const cam = this.camera;
            let evictRing = null;
            board.tileRenderPass += 1;
            const pass = board.tileRenderPass;

            
            
            board.worldLayer.position.set(cam.offsetX, cam.offsetY);
            board.worldLayer.scale.set(cam.zoom, cam.zoom);

            if (scene && tiles?.manifest && tiles.manifest.tile_table_version === scene.tileVersion) {
                const chunkSize = tiles.manifest.chunk_size || DEFAULT_CHUNK_SIZE;
                const s = scene.scaledTileSize;
                const tileCols = Math.ceil(scene.baseWidth / scene.tileSize);
                const tileRows = Math.ceil(scene.baseHeight / scene.tileSize);

                const worldX0 = -cam.offsetX / cam.zoom;
                const worldY0 = -cam.offsetY / cam.zoom;
                const worldX1 = (cssW - cam.offsetX) / cam.zoom;
                const worldY1 = (cssH - cam.offsetY) / cam.zoom;

                
                
                
                
                
                
                const cwx = (worldX0 + worldX1) / 2;
                const cwy = (worldY0 + worldY1) / 2;
                const now = (typeof performance !== "undefined" ? performance.now() : Date.now());
                const prev = board.camTrack;
                if (!board.vel) board.vel = { x: 0, y: 0 };
                if (!board.lead) board.lead = { x: 0, y: 0 };
                const moved = !prev || prev.x !== cwx || prev.y !== cwy || prev.zoom !== cam.zoom;
                const zoomChanged = !!prev && prev.zoom !== cam.zoom;

                if (zoomChanged) {
                    board.vel.x = 0;
                    board.vel.y = 0;
                    board.lead.x = 0;
                    board.lead.y = 0;
                } else if (moved && prev) {
                    const dt = (now - prev.t) / 1000;
                    if (dt > 0.001 && dt < 0.4) {
                        const SMOOTH = 0.4;
                        const LOOKAHEAD_S = 0.5;
                        const MAX_LEAD = 22;
                        board.vel.x = board.vel.x * (1 - SMOOTH) + ((cwx - prev.x) / dt) * SMOOTH;
                        board.vel.y = board.vel.y * (1 - SMOOTH) + ((cwy - prev.y) / dt) * SMOOTH;
                        board.lead.x = Math.max(-MAX_LEAD, Math.min(MAX_LEAD,
                            board.vel.x * LOOKAHEAD_S / s));
                        board.lead.y = Math.max(-MAX_LEAD, Math.min(MAX_LEAD,
                            board.vel.y * LOOKAHEAD_S / s));
                    }
                }
                if (moved) board.camTrack = { x: cwx, y: cwy, zoom: cam.zoom, t: now };

                const leadTx = Math.abs(board.lead.x) < 1 ? 0 : board.lead.x;
                const leadTy = Math.abs(board.lead.y) < 1 ? 0 : board.lead.y;

                
                
                evictRing = {
                    x0: Math.floor(worldX0 / s) - EVICT_MARGIN_TILES,
                    x1: Math.floor(worldX1 / s) + EVICT_MARGIN_TILES,
                    y0: Math.floor(worldY0 / s) - EVICT_MARGIN_TILES,
                    y1: Math.floor(worldY1 / s) + EVICT_MARGIN_TILES,
                };

                const base = TILE_VIEW_MARGIN;
                const tx0 = Math.max(0,
                    Math.floor(worldX0 / s) - base + Math.floor(Math.min(0, leadTx)));
                const tx1 = Math.min(tileCols - 1,
                    Math.floor(worldX1 / s) + base + Math.ceil(Math.max(0, leadTx)));
                const ty0 = Math.max(0,
                    Math.floor(worldY0 / s) - base + Math.floor(Math.min(0, leadTy)));
                const ty1 = Math.min(tileRows - 1,
                    Math.floor(worldY1 / s) + base + Math.ceil(Math.max(0, leadTy)));

                if (tx0 <= tx1 && ty0 <= ty1) {
                    
                    
                    const centerTx = cwx / s + leadTx * 0.5;
                    const centerTy = cwy / s + leadTy * 0.5;

                    const plan = this._tilePlan(board, tiles, {
                        chunkSize,
                        tx0,
                        tx1,
                        ty0,
                        ty1,
                        centerTx,
                        centerTy,
                    });

                    for (const cell of plan) {
                        this._renderTile(
                            board,
                            pass,
                            cell.tile,
                            cell.layerId,
                            cell.tx,
                            cell.ty,
                            s,
                            scene,
                        );
                    }
                }
            }

            board.tileSprites.forEach((sprite, key) => {
                if (sprite.__lastSeenPass === pass) return;
                sprite.visible = false;

                if (!evictRing) return;
                const tx = sprite.__tileTx;
                const ty = sprite.__tileTy;
                if (
                    tx < evictRing.x0 || tx > evictRing.x1 ||
                    ty < evictRing.y0 || ty > evictRing.y1
                ) {
                    const url = sprite.__tileUrl;
                    board.tileSprites.delete(key);
                    sprite.destroy();
                    if (url) {
                        this.textures.delete(url);
                        const objectUrl = this.textureObjectUrls?.get(url);
                        if (objectUrl) {
                            URL.revokeObjectURL(objectUrl);
                            this.textureObjectUrls.delete(url);
                        }
                        PIXI.Assets?.unload?.(url)?.catch?.(() => {});
                    }
                }
            });
        },

        _tilePlan(board, tiles, view) {
            const chunks = tiles.chunks;
            const layers = tiles.manifest.layers || [];
            const ccx0 = Math.floor(view.tx0 / view.chunkSize);
            const ccx1 = Math.floor(view.tx1 / view.chunkSize);
            const ccy0 = Math.floor(view.ty0 / view.chunkSize);
            const ccy1 = Math.floor(view.ty1 / view.chunkSize);

            const key = [
                tiles.manifest.scene_id,
                tiles.manifest.tile_table_version,
                tiles.chunkRevision || 0,
                view.chunkSize,
                view.tx0,
                view.tx1,
                view.ty0,
                view.ty1,
                Math.round(view.centerTx * 100) / 100,
                Math.round(view.centerTy * 100) / 100,
            ].join(":");

            if (board.tilePlanKey === key) {
                return board.tilePlan;
            }

            const cells = [];
            layers.forEach((mLayer) => {
                const table = tiles.tileTables.get(mLayer.layer_id);
                if (!table) return;

                for (let cy = ccy0; cy <= ccy1; cy += 1) {
                    for (let cx = ccx0; cx <= ccx1; cx += 1) {
                        const chunk = chunks.get(`${mLayer.layer_id}:${cx}:${cy}`);
                        if (!chunk?.refs) continue;

                        for (let index = 0; index < chunk.refs.length; index += 1) {
                            const tileRef = chunk.refs[index];
                            if (!tileRef) continue;

                            const tx = cx * view.chunkSize + (index % view.chunkSize);
                            const ty = cy * view.chunkSize + Math.floor(index / view.chunkSize);
                            if (tx < view.tx0 || tx > view.tx1 || ty < view.ty0 || ty > view.ty1) {
                                continue;
                            }

                            const tile = table.get(tileRef);
                            if (!tile) continue;

                            const dx = tx - view.centerTx;
                            const dy = ty - view.centerTy;
                            cells.push({
                                tile,
                                layerId: mLayer.layer_id,
                                tx,
                                ty,
                                dist: dx * dx + dy * dy,
                            });
                        }
                    }
                }
            });

            
            
            cells.sort((a, b) => a.dist - b.dist);
            board.tilePlanKey = key;
            board.tilePlan = cells;
            return cells;
        },

        _renderTile(board, pass, tile, layerId, tx, ty, size, scene) {
            if (!tile?.url) return;

            const texture = this._texture(tile.url);
            if (!texture) return;

            const key = `${layerId}:${tx}:${ty}`;

            let sprite = board.tileSprites.get(key);

            if (!sprite) {
                sprite = new PIXI.Sprite(texture);
                board.tileSprites.set(key, sprite);
                board.tilesLayer.addChild(sprite);
            } else if (sprite.texture !== texture) {
                sprite.texture = texture;
            }
            
            sprite.__tileUrl = tile.url;
            sprite.__tileTx = tx;
            sprite.__tileTy = ty;
            sprite.__lastSeenPass = pass;

            sprite.x = tx * size;
            sprite.y = ty * size;
            sprite.width = tile.width * scene.imageScale;
            sprite.height = tile.height * scene.imageScale;
            sprite.visible = true;
        },

        _visibleChunkRange(scene, cam, cssW, cssH) {
            const worldX0 = -cam.offsetX / cam.zoom;
            const worldY0 = -cam.offsetY / cam.zoom;
            const worldX1 = (cssW - cam.offsetX) / cam.zoom;
            const worldY1 = (cssH - cam.offsetY) / cam.zoom;

            const s = scene.scaledTileSize;
            const tileCols = Math.ceil(scene.baseWidth / scene.tileSize);
            const tileRows = Math.ceil(scene.baseHeight / scene.tileSize);

            const tx0 = Math.max(0, Math.floor(worldX0 / s));
            const tx1 = Math.min(tileCols - 1, Math.floor(worldX1 / s));
            const ty0 = Math.max(0, Math.floor(worldY0 / s));
            const ty1 = Math.min(tileRows - 1, Math.floor(worldY1 / s));

            if (tx0 > tx1 || ty0 > ty1) return null;

            const chunkSize = this.tiles?.manifest?.chunk_size || DEFAULT_CHUNK_SIZE;
            const maxCx = Math.max(0, Math.floor((tileCols - 1) / chunkSize));
            const maxCy = Math.max(0, Math.floor((tileRows - 1) / chunkSize));

            return {
                cx0: Math.max(0, Math.floor(tx0 / chunkSize) - VIEW_CHUNK_MARGIN),
                cy0: Math.max(0, Math.floor(ty0 / chunkSize) - VIEW_CHUNK_MARGIN),
                cx1: Math.min(maxCx, Math.floor(tx1 / chunkSize) + VIEW_CHUNK_MARGIN),
                cy1: Math.min(maxCy, Math.floor(ty1 / chunkSize) + VIEW_CHUNK_MARGIN),
            };
        },
    });
})();
