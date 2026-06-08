





(() => {
    const DISPOSITION_COLORS = {
        friendly: 0x4a90e2,
        neutral: 0x8c8c8c,
        hostile: 0xe24a4a,
        unknown: 0x5c5c5c,
    };
    const TOKEN_HP_BAR_H = 4;
    const TOKEN_HIDDEN_OPACITY = 0.42;
    const COMBAT_RING_COLORS = {
        current: 0x28d17c,
        next: 0xef4444,
        acted: 0x9ca3af,
    };

    const proto = window.GravewrightBoardInternals.PixiBoardRenderer.prototype;

    Object.assign(proto, {
        _renderTokens(board, cssW, cssH) {
            const scene = this.scene;
            const layer = board.tokenWorldLayer;

            if (!scene) {
                board.tokenNodes.forEach((node) => {
                    node.container.visible = false;
                });
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

            this.tokens.forEach((token) => {
                if (token.hidden && !viewerIsGm) return;

                const groupPos = dragPositions ? dragPositions[token.token_id] : null;
                const isDragging = !!groupPos || (drag && drag.tokenId === token.token_id);
                let renderWorldX = token.grid_x * s;
                let renderWorldY = token.grid_y * s;
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

                const ww = s * wCells;
                const wh = s * hCells;
                if (Math.min(ww, wh) * zoom < 4) return;

                live.add(token.token_id);
                this._renderToken(board, layer, token, {
                    wx: renderWorldX,
                    wy: renderWorldY,
                    ww,
                    wh,
                    zoom,
                    isDragging,
                    selected: selectedIds.has(token.token_id),
                    hovered: hoveredId === token.token_id,
                });
            });

            board.tokenNodes.forEach((node, id) => {
                if (!live.has(id)) {
                    node.container.visible = false;
                    node.label.visible = false;
                    node.labelBg.visible = false;
                    node.labelBg.clear();
                }
            });
        },

        _renderToken(board, layer, token, ctx) {
            const { wx, wy, ww, wh, zoom, isDragging, selected, hovered } = ctx;
            const px = 1 / zoom;

            let node = board.tokenNodes.get(token.token_id);
            if (!node) {
                node = {
                    container: new PIXI.Container(),
                    sprite: new PIXI.Sprite(PIXI.Texture.EMPTY),
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
                };

                node.sprite.mask = node.mask;
                node.label.resolution = window.devicePixelRatio || 1;
                node.label.roundPixels = true;
                node.labelBg.roundPixels = true;
                node.container.addChild(node.gfx, node.mask, node.sprite);
                board.tokenNodes.set(token.token_id, node);
                layer.addChild(node.container);
                board.tokenLabelLayer?.addChild(node.labelBg, node.label);
            }

            node.container.visible = true;
            node.container.alpha = token.hidden ? TOKEN_HIDDEN_OPACITY : 1;
            if (isDragging) node.container.alpha *= 0.75;

            const dispColor = DISPOSITION_COLORS[token.disposition] ?? DISPOSITION_COLORS.neutral;
            const cx = wx + ww / 2;
            const cy = wy + wh / 2;
            const tokenSize = Math.min(ww, wh);
            const radius = tokenSize * 0.42;
            const tokenX = cx - tokenSize / 2;
            const tokenY = cy - tokenSize / 2;

            const g = node.gfx;
            g.clear();

            const texture = token.asset_url ? this._texture(token.asset_url) : null;
            if (texture) {
                node.sprite.visible = true;
                node.sprite.texture = texture;
                node.sprite.position.set(tokenX, tokenY);
                node.sprite.width = tokenSize;
                node.sprite.height = tokenSize;

                node.mask.clear();
                node.mask.circle(cx, cy, radius).fill({ color: 0xffffff });
            } else {
                node.sprite.visible = false;
                node.mask.clear();
                g.circle(cx, cy, radius).fill({ color: dispColor, alpha: 0.53 });
            }

            g.circle(cx, cy, radius).stroke({
                width: Math.max(1.5 * px, tokenSize * 0.04),
                color: dispColor,
            });

            if (hovered && !selected && !isDragging) {
                g.circle(cx, cy, radius + Math.max(2 * px, tokenSize * 0.045))
                    .stroke({
                        width: Math.max(2 * px, tokenSize * 0.045),
                        color: 0xe8c87e,
                        alpha: 0.82,
                    });
            }

            if (selected || isDragging) {
                g.circle(cx, cy, radius + Math.max(2.5 * px, tokenSize * 0.06))
                    .stroke({
                        width: Math.max(2 * px, tokenSize * 0.055),
                        color: 0xe8c87e,
                    });
            }

            this._renderCombatTurnRing(g, token, { cx, cy, radius, tokenSize, px });

            const hp = token.bars?.hp;
            if (hp && hp.max > 0 && tokenSize * zoom > 20) {
                const barH = TOKEN_HP_BAR_H * px;
                const barPad = 3 * px;
                const barW = tokenSize - barPad * 2;
                const barX = tokenX + barPad;
                const barY = tokenY + tokenSize - barH - barPad;
                const ratio = Math.max(0, Math.min(1, hp.value / hp.max));

                g.rect(barX, barY, barW, barH)
                    .fill({ color: 0x000000, alpha: 0.55 });

                g.rect(barX, barY, barW * ratio, barH)
                    .fill({ color: 0x4caf50 });
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

                
                
                const screenCx = cx * zoom + this.camera.offsetX;
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
                node.labelBg.visible = false;
                node.labelBg.clear();
            }
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
