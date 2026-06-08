





(() => {
    const proto = window.GravewrightBoardInternals.PixiBoardRenderer.prototype;

    Object.assign(proto, {
        debugSnapshot() {
            const board = this.active && this.boards.get(this.active);
            const textures = { loading: 0, error: 0, ready: 0 };

            this.textures.forEach((texture) => {
                if (texture === "loading") textures.loading += 1;
                else if (texture === "error") textures.error += 1;
                else textures.ready += 1;
            });

            return {
                boardReady: !!board?.ready,
                textures,
                tileSprites: board?.tileSprites.size || 0,
                visibleTileSprites: board
                    ? [...board.tileSprites.values()].filter((sprite) => sprite.visible).length
                    : 0,
                samples: board ? this._sampleSprites(board) : null,
            };
        },

        
        
        
        _sampleSprites(board) {
            const entries = [...board.tileSprites.entries()]
                .map(([key, sprite]) => ({ key, sprite, ty: parseInt(key.split(":").pop(), 10) }))
                .filter((entry) => Number.isFinite(entry.ty));
            if (!entries.length) return null;
            entries.sort((a, b) => a.ty - b.ty);

            const pick = (entry) => {
                if (!entry) return null;
                const s = entry.sprite;
                const tex = s.texture;
                const src = tex && tex.source;
                let bounds = null;
                try {
                    const b = s.getBounds();
                    bounds = {
                        x: Math.round(b.minX ?? b.x ?? 0),
                        y: Math.round(b.minY ?? b.y ?? 0),
                        w: Math.round((b.maxX - b.minX) || b.width || 0),
                        h: Math.round((b.maxY - b.minY) || b.height || 0),
                    };
                } catch (err) {
                    bounds = String(err);
                }
                return {
                    key: entry.key,
                    ty: entry.ty,
                    x: Math.round(s.x),
                    y: Math.round(s.y),
                    w: Math.round(s.width),
                    h: Math.round(s.height),
                    visible: s.visible,
                    renderable: s.renderable,
                    alpha: s.alpha,
                    parent: !!s.parent,
                    hasTexture: !!tex,
                    texValid: !!(src && src.width > 0 && src.height > 0),
                    texW: src ? src.width : null,
                    texH: src ? src.height : null,
                    bounds,
                };
            };

            const wl = board.worldLayer;
            const tl = board.tilesLayer;
            return {
                worldLayer: wl
                    ? {
                        x: Math.round(wl.x),
                        y: Math.round(wl.y),
                        scaleX: wl.scale.x,
                        scaleY: wl.scale.y,
                        visible: wl.visible,
                        alpha: wl.alpha,
                        renderable: wl.renderable,
                    }
                    : null,
                tilesLayer: tl
                    ? {
                        children: tl.children.length,
                        visible: tl.visible,
                        alpha: tl.alpha,
                        renderable: tl.renderable,
                    }
                    : null,
                top: pick(entries[0]),
                bottom: pick(entries[entries.length - 1]),
            };
        },
    });
})();
