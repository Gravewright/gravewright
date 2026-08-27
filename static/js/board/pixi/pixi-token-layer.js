





(() => {
    const DISPOSITION_COLORS = {
        friendly: 0x4a90e2,
        neutral: 0x8c8c8c,
        hostile: 0xe24a4a,
        unknown: 0x5c5c5c,
    };
    const TOKEN_BAR_H = 4;


    const TOKEN_BAR_FALLBACK_COLORS = { bar_1: 0x4caf50, bar_2: 0x3b82f6 };
    const TOKEN_HIDDEN_OPACITY = 0.42;
    const DEFEATED_ICON_URL = "/static/icons/base/death-skull.png";
    const COMBAT_RING_COLORS = {
        current: 0x28d17c,
        next: 0xef4444,
        acted: 0x9ca3af,
    };


    function hexToInt(value, fallback) {
        const text = String(value || "").trim().replace(/^#/, "");
        const full = text.length === 3 ? text.replace(/./g, (c) => c + c) : text;
        if (!/^[0-9a-fA-F]{6}$/.test(full)) return fallback;
        return parseInt(full, 16);
    }

    const proto = window.GravewrightBoardInternals.PixiBoardRenderer.prototype;

    Object.assign(proto, {
        _renderTokens(board, cssW, cssH) {
            const spatialStartedAt = performance.now();
            const scene = this.scene;
            const layer = board.tokenWorldLayer;

            if (!scene) {
                board.tokenNodes.forEach((node) => {
                    node.container.visible = false;
                });
                board.fastTokenSprites.forEach((sprite) => { sprite.visible = false; });
                return;
            }

            const cam = this.camera;
            const zoom = Math.max(0.001, cam.zoom || 1);
            const s = scene.scaledTileSize;
            const selectedIds = new Set(this.overlays.selectedIds || []);
            const hoveredId = this.overlays.hoveredId ?? null;
            const viewerIsGm = !!this.overlays.viewerIsGm;
            const drag = this.overlays.drag || null;
            const dragPositions = (drag && drag.positions) || null;

            const wx0 = (-cam.offsetX / cam.zoom) / s;
            const wy0 = (-cam.offsetY / cam.zoom) / s;
            const wx1 = ((cssW - cam.offsetX) / cam.zoom) / s;
            const wy1 = ((cssH - cam.offsetY) / cam.zoom) / s;
            const cullX0 = Math.floor(wx0) - 1;
            const cullY0 = Math.floor(wy0) - 1;
            const cullX1 = Math.ceil(wx1) + 1;
            const cullY1 = Math.ceil(wy1) + 1;

            const live = new Set();
            const liveFast = new Set();
            const existing = new Set(this.tokens.map((token) => token.token_id));
            let spatialCandidates = 0;

            this.tokens.forEach((token) => {
                if (token.hidden && !viewerIsGm) return;

                const groupPos = dragPositions ? dragPositions[token.token_id] : null;
                const isDragging = !!groupPos || (drag && drag.tokenId === token.token_id);
                let renderWorldX = (scene.gridOffsetX || 0) + token.grid_x * s;
                let renderWorldY = (scene.gridOffsetY || 0) + token.grid_y * s;
                if (groupPos) {
                    renderWorldX = groupPos.worldX;
                    renderWorldY = groupPos.worldY;
                } else if (drag && drag.tokenId === token.token_id) {
                    renderWorldX = drag.currentWorldX;
                    renderWorldY = drag.currentWorldY;
                }
                const rgx = renderWorldX / s;
                const rgy = renderWorldY / s;
                const wCells = token.width_cells || 1;
                const hCells = token.height_cells || 1;

                if (
                    rgx + wCells <= cullX0 ||
                    rgx > cullX1 ||
                    rgy + hCells <= cullY0 ||
                    rgy > cullY1
                ) {
                    return;
                }
                spatialCandidates += 1;

                const ww = s * wCells;
                const wh = s * hCells;
                if (Math.min(ww, wh) * zoom < 4) return;

                const hasBars = Object.keys(token.bars || {}).length > 0;
                const isSelected = selectedIds.has(token.token_id);
                const isHovered = hoveredId === token.token_id;
                const fast = !!token.asset_url
                    && (token.benchmark_animated || token.asset_render_mode === "transparent")
                    && !token.name && !hasBars && !token.combat_marker
                    && !isDragging && !isSelected && !isHovered;
                if (fast) {
                    liveFast.add(token.token_id);
                    this._renderFastToken(board, token, {
                        wx: renderWorldX, wy: renderWorldY, ww, wh,
                    });
                    return;
                }
                live.add(token.token_id);
                this._renderToken(board, layer, token, {
                    wx: renderWorldX,
                    wy: renderWorldY,
                    ww,
                    wh,
                    zoom,
                    isDragging,
                    selected: isSelected,
                    hovered: isHovered,
                });
            });

            board.tokenNodes.forEach((node, id) => {
                if (!existing.has(id)) {
                    node.container.destroy({ children: true });
                    node.label.destroy();
                    node.labelBg.destroy();
                    board.tokenNodes.delete(id);
                    return;
                }
                if (!live.has(id)) {
                    node.container.visible = false;
                    node.label.visible = false;
                    if (node.labelBg.visible) {
                        node.labelBg.visible = false;
                        node.labelBg.clear();
                    }
                }
            });
            board.fastTokenSprites.forEach((sprite, id) => {
                if (!existing.has(id)) {
                    sprite.destroy();
                    board.fastTokenSprites.delete(id);
                    return;
                }
                sprite.visible = liveFast.has(id);
            });
            board.tokenSpatialMetrics = {
                total: this.tokens.length,
                candidates: spatialCandidates,
                visible: live.size + liveFast.size,
                culled: Math.max(0, this.tokens.length - live.size - liveFast.size),
                queryMs: performance.now() - spatialStartedAt,
            };
        },

        _renderFastToken(board, token, { wx, wy, ww, wh }) {
            let sprite = board.fastTokenSprites.get(token.token_id);
            if (!sprite) {
                sprite = new PIXI.Sprite(PIXI.Texture.EMPTY);
                sprite.eventMode = "none";
                board.fastTokenSprites.set(token.token_id, sprite);
                board.tokenSpriteLayer.addChild(sprite);
            }
            const staleNode = board.tokenNodes.get(token.token_id);
            if (staleNode) {
                staleNode.container.destroy({ children: true });
                staleNode.label.destroy();
                staleNode.labelBg.destroy();
                board.tokenNodes.delete(token.token_id);
            }
            const texture = this._texture(token.asset_url, {
                visible: true, priority: -1_000_000,
                generation: this.tiles?.generation || 0,
            });
            sprite.visible = !!texture;
            if (!texture) return;
            sprite.texture = texture;
            const size = Math.min(ww, wh);
            sprite.position.set(wx + (ww - size) / 2, wy + (wh - size) / 2);
            sprite.width = size;
            sprite.height = size;
            sprite.alpha = token.hidden ? TOKEN_HIDDEN_OPACITY : 1;
        },

        _renderToken(board, layer, token, ctx) {
            const { wx, wy, ww, wh, zoom, isDragging, selected, hovered } = ctx;
            const px = 1 / zoom;

            let node = board.tokenNodes.get(token.token_id);
            const staleFast = board.fastTokenSprites.get(token.token_id);
            if (staleFast) {
                staleFast.destroy();
                board.fastTokenSprites.delete(token.token_id);
            }
            if (!node) {
                node = {
                    container: new PIXI.Container(),
                    sprite: new PIXI.Sprite(PIXI.Texture.EMPTY),
                    defeatedIcon: new PIXI.Sprite(PIXI.Texture.EMPTY),
                    mask: new PIXI.Graphics(),
                    gfx: new PIXI.Graphics(),
                    label: new PIXI.Text({
                        text: "",
                        style: {
                            fontFamily: "sans-serif",
                            fontSize: 11,
                            fontWeight: "bold",
                            fill: 0xe8dfc4,
                        },
                    }),
                    labelBg: new PIXI.Graphics(),
                    visualKey: null,
                };

                node.sprite.mask = node.mask;
                node.defeatedIcon.eventMode = "none";
                node.defeatedIcon.anchor.set(0.5);
                node.label.resolution = window.devicePixelRatio || 1;
                node.label.roundPixels = true;
                node.labelBg.roundPixels = true;
                node.container.addChild(node.gfx, node.mask, node.sprite, node.defeatedIcon);
                board.tokenNodes.set(token.token_id, node);
                board.tokenAdornmentLayer.addChild(node.container);
                board.tokenLabelLayer?.addChild(node.labelBg, node.label);
            }

            node.container.visible = true;
            node.container.position.set(wx, wy);
            node.container.alpha = token.hidden ? TOKEN_HIDDEN_OPACITY : 1;
            if (isDragging) node.container.alpha *= 0.75;

            const dispColor = DISPOSITION_COLORS[token.disposition] ?? DISPOSITION_COLORS.neutral;
            const cx = ww / 2;
            const cy = wh / 2;
            const tokenSize = Math.min(ww, wh);
            const radius = tokenSize * 0.42;
            const tokenX = cx - tokenSize / 2;
            const tokenY = cy - tokenSize / 2;

            const g = node.gfx;

            const texture = token.asset_url ? this._texture(token.asset_url, {
                visible: true,
                priority: -1_000_000,
                generation: this.tiles?.generation || 0,
            }) : null;
            if (texture) {
                node.sprite.visible = true;
                node.sprite.texture = texture;
                node.sprite.position.set(tokenX, tokenY);
                node.sprite.width = tokenSize;
                node.sprite.height = tokenSize;
            } else {
                node.sprite.visible = false;
            }

            const defeated = !!token.combat_marker?.defeated;
            const defeatedTexture = defeated ? this._texture(DEFEATED_ICON_URL, {
                visible: true,
                priority: -1_000_001,
                generation: this.tiles?.generation || 0,
            }) : null;
            node.defeatedIcon.visible = !!defeatedTexture;
            if (defeatedTexture) {
                node.defeatedIcon.texture = defeatedTexture;
                node.defeatedIcon.position.set(cx, cy);
                node.defeatedIcon.width = tokenSize * 0.72;
                node.defeatedIcon.height = tokenSize * 0.72;
                node.defeatedIcon.alpha = 0.92;
            }

            const barsKey = JSON.stringify(token.bars || {});
            const markerPhase = token.combat_marker?.role && token.combat_marker.role !== "acted"
                ? Math.floor(performance.now() / 50) : 0;
            const markerKey = `${JSON.stringify(token.combat_marker || null)}:${markerPhase}`;
            const visualKey = [tokenSize, zoom, dispColor, !!texture, selected, hovered, isDragging, barsKey, markerKey].join("|");
            if (node.visualKey !== visualKey) {
                node.visualKey = visualKey;
                g.clear();
                node.mask.clear();
                if (texture) node.mask.circle(cx, cy, radius).fill({ color: 0xffffff });
                else g.circle(cx, cy, radius).fill({ color: dispColor, alpha: 0.53 });
                g.circle(cx, cy, radius).stroke({
                    width: Math.max(1.5 * px, tokenSize * 0.04), color: dispColor,
                });
                if (hovered && !selected && !isDragging) {
                    g.circle(cx, cy, radius + Math.max(2 * px, tokenSize * 0.045)).stroke({
                        width: Math.max(2 * px, tokenSize * 0.045), color: 0xe8c87e, alpha: 0.82,
                    });
                }
                if (selected || isDragging) {
                    g.circle(cx, cy, radius + Math.max(2.5 * px, tokenSize * 0.06)).stroke({
                        width: Math.max(2 * px, tokenSize * 0.055), color: 0xe8c87e,
                    });
                }
                this._renderCombatTurnRing(g, token, { cx, cy, radius, tokenSize, px });
                if (tokenSize * zoom > 20) this._renderTokenBars(g, token, { tokenX, tokenY, tokenSize, px });
            }

            if (tokenSize * zoom > 20 && token.name) {
                node.label.visible = true;
                node.labelBg.visible = true;
                node.label.alpha = node.container.alpha;
                node.labelBg.alpha = node.container.alpha;

                if (node.label.text !== token.name) node.label.text = token.name;
                if (node.label.style.fontSize !== 11) {
                    node.label.style.fontSize = 11;
                }



                const screenCx = (wx + cx) * zoom + this.camera.offsetX;
                const screenY = (wy + wh) * zoom + this.camera.offsetY + 3;
                const tw = node.label.width;
                const labelX = Math.round(screenCx - tw / 2);
                const labelY = Math.round(screenY);

                node.label.position.set(labelX, labelY);

                node.labelBg.clear();
                node.labelBg
                    .rect(labelX - 3, labelY - 1, tw + 6, 14)
                    .fill({ color: 0x000000, alpha: 0.72 });
            } else {
                node.label.visible = false;
                if (node.labelBg.visible) {
                    node.labelBg.visible = false;
                    node.labelBg.clear();
                }
            }
        },

        _renderTokenBars(g, token, { tokenX, tokenY, tokenSize, px }) {
            const barH = TOKEN_BAR_H * px;
            const barPad = 3 * px;
            const barW = tokenSize - barPad * 2;
            const barX = tokenX + barPad;
            const rows = {
                bar_1: tokenY + tokenSize - barH - barPad,
                bar_2: tokenY + barPad,
            };

            Object.entries(rows).forEach(([slot, barY]) => {
                const bar = token.bars?.[slot];
                const max = Number(bar?.max);
                if (!bar || !(max > 0)) return;
                const ratio = Math.max(0, Math.min(1, Number(bar.value) / max));

                g.rect(barX, barY, barW, barH).fill({ color: 0x000000, alpha: 0.55 });
                g.rect(barX, barY, barW * ratio, barH).fill({
                    color: hexToInt(bar.color, TOKEN_BAR_FALLBACK_COLORS[slot]),
                });
            });
        },

        _renderCombatTurnRing(g, token, ctx) {
            const marker = token.combat_marker;
            if (!marker?.role) return;

            const { cx, cy, radius, tokenSize, px } = ctx;
            const role = marker.role;
            const color = Number.isFinite(marker.color) ? marker.color : (COMBAT_RING_COLORS[role] || 0xffffff);
            const now = performance.now ? performance.now() : Date.now();
            const phase = (now % 1600) / 1600;
            const wave = 0.5 + 0.5 * Math.sin(phase * Math.PI * 2);
            const baseOffset = Math.max(4 * px, tokenSize * 0.07);
            const baseRadius = radius + baseOffset;
            const baseWidth = Math.max(2.5 * px, tokenSize * 0.052);

            if (role === "acted") {
                g.circle(cx, cy, baseRadius).stroke({
                    width: Math.max(1.8 * px, tokenSize * 0.035),
                    color,
                    alpha: 0.72,
                });
                return;
            }



            const pulseRadius = baseRadius + Math.max(2 * px, tokenSize * 0.035) * wave;
            const pulseAlpha = role === "current" ? 0.18 + 0.30 * wave : 0.14 + 0.22 * wave;

            g.circle(cx, cy, pulseRadius).stroke({
                width: Math.max(5 * px, tokenSize * 0.12),
                color,
                alpha: pulseAlpha,
            });
            g.circle(cx, cy, baseRadius).stroke({
                width: baseWidth,
                color,
                alpha: marker.alpha ?? 0.92,
            });
            g.circle(cx, cy, baseRadius + Math.max(2 * px, tokenSize * 0.032)).stroke({
                width: Math.max(1.2 * px, tokenSize * 0.018),
                color: 0xffffff,
                alpha: role === "current" ? 0.16 + 0.12 * wave : 0.10 + 0.10 * wave,
            });
        },
    });
})();
