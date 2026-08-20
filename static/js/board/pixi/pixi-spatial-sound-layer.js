(() => {
    "use strict";

    const proto = window.GravewrightBoardInternals.PixiBoardRenderer.prototype;

    Object.assign(proto, {
        _renderSpatialSounds(board) {
            const gfx = board.spatialSoundGfx;
            if (!gfx) return;
            gfx.clear();

            const snapshot = this.overlays?.spatialSounds;
            const emitters = (snapshot?.authoring || snapshot?.artisticReference || snapshot?.wallReference) ? (snapshot.emitters || []) : [];
            const zoom = Number(this.camera.zoom) || 1;
            const picked = new Set(snapshot?.selectedIds || (snapshot?.selectedId ? [snapshot.selectedId] : []));
            const single = picked.size === 1;
            const accent = this._color("#c69c59");
            const muted = this._color("#776f63");

            emitters.forEach((item) => {
                const x = Number(item.x) * zoom + this.camera.offsetX;
                const y = Number(item.y) * zoom + this.camera.offsetY;
                const radius = Math.max(12, Number(item.radius || 0) * zoom);
                const selected = picked.has(item.id);
                const color = item.enabled === false ? muted : accent;
                const alpha = item.enabled === false ? 0.38 : selected ? 0.95 : snapshot?.wallReference ? 0.72 : 0.55;
                const propagation = window.GravewrightLighting?.soundPropagationFor?.(this.active, item);
                const polygon = Array.isArray(propagation) && propagation.length >= 3
                    ? propagation.flatMap((point) => [Number(point.x) * zoom + this.camera.offsetX, Number(point.y) * zoom + this.camera.offsetY])
                    : null;

                const reach = polygon ? gfx.poly(polygon) : gfx.circle(x, y, radius);
                reach.fill({ color, alpha: selected ? 0.075 : 0.035 })
                    .stroke({ color, width: selected ? 2 : 1, alpha, join: "round" });
                gfx.circle(x, y, selected ? 15 : 13)
                    .fill({ color: selected ? accent : 0x15191e, alpha: 0.96 })
                    .stroke({ color, width: 2, alpha: 1 });

                const glyph = selected ? 0x17130b : color;
                gfx.rect(x - 6, y - 4, 4, 8).fill({ color: glyph, alpha: 1 });
                gfx.poly([x - 2, y - 4, x + 4, y - 9, x + 4, y + 9, x - 2, y + 4])
                    .fill({ color: glyph, alpha: 1 });
                const arcStart = -Math.PI / 3;
                gfx.moveTo(x + 3 + 7 * Math.cos(arcStart), y + 7 * Math.sin(arcStart));
                gfx.arc(x + 3, y, 7, arcStart, Math.PI / 3)
                    .stroke({ color: glyph, width: 2, alpha: 1 });

                if (selected && single) {
                    gfx.circle(x + radius, y, 6)
                        .fill({ color: accent, alpha: 1 })
                        .stroke({ color: 0x15191e, width: 2, alpha: 1 });
                }
            });

            window.__gravewrightSpatialSoundPixi = {
                count: emitters.length,
                selectedId: snapshot?.selectedId || null,
                renderer: "pixi",
                occluded: emitters.filter((item) => item.constrained_by_walls !== false).length,
            };
        },
    });
})();
