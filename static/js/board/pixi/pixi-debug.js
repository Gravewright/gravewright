





(() => {
    const proto = window.GravewrightBoardInternals.PixiBoardRenderer.prototype;

    Object.assign(proto, {
        debugSnapshot() {
            const board = this.active && this.boards.get(this.active);
            const textures = { queued: 0, loading: 0, error: 0, ready: 0 };

            this.textures.forEach((texture) => {
                if (texture === "queued") textures.queued += 1;
                else if (texture === "loading") textures.loading += 1;
                else if (texture === "error") textures.error += 1;
                else textures.ready += 1;
            });

            return {
                boardReady: !!board?.ready,
                textures,
                textureMaterializationBudget: this.maxTextureMaterializationsPerFrame,
                textureMaterializationBudgetRange: {
                    min: this.minTextureMaterializationsPerFrame,
                    max: this.maxAdaptiveTextureMaterializationsPerFrame,
                },
                textureFrameWorkEmaMs: this.textureFrameWorkEmaMs,
                textureMaterializationCostEmaMs: this.textureMaterializationCostEmaMs,
                textureGovernorState: this.textureGovernorState,
                textureGovernorAdjustments: {
                    increases: this.textureGovernorIncreases,
                    decreases: this.textureGovernorDecreases,
                },
                prefetchPaused: performance.now() < this.prefetchPausedUntil,
                textureMaterializationsThisFrame: board?.textureMaterializationsThisFrame || 0,
                deferredTextureMaterializations: board?.deferredTextureMaterializations || 0,
                deferredVisibleTextureMaterializations: board?.deferredVisibleTextureMaterializations || 0,
                deferredPrefetchTextureMaterializations: board?.deferredPrefetchTextureMaterializations || 0,
                textureMaterializationWorkMs: board?.textureMaterializationWorkMs || 0,
                textureCache: {
                    entries: this.textureMeta.size,
                    bytes: this.textureCacheBytes,
                    maxEntries: this.maxTextureCacheEntries,
                    maxBytes: this.maxTextureCacheBytes,
                    evictions: this.textureCacheEvictions,
                    evictedBytes: this.textureCacheEvictedBytes,
                },
                blobCache: window.GravewrightTileBlobCache?.snapshot?.() || null,
                tileSprites: board?.tileSprites.size || 0,
                visibleTileSprites: board
                    ? [...board.tileSprites.values()].filter((sprite) => sprite.visible).length
                    : 0,
                animatedEntities: (() => {
                    const animated = this.tokens.filter((token) => token.benchmark_animated);
                    const assets = new Set(animated.map((token) => token.asset_url).filter(Boolean));
                    return {
                        instances: animated.length,
                        visible: board?.tokenSpatialMetrics?.visible || 0,
                        uniqueAssets: assets.size,
                        textureSources: assets.size,
                        sharedAssetHits: Math.max(0, animated.length - assets.size),
                        tokenNodes: (board?.tokenNodes?.size || 0) + (board?.fastTokenSprites?.size || 0),
                        fastSprites: board?.fastTokenSprites?.size || 0,
                    };
                })(),
                spatialIndex: board?.tokenSpatialMetrics || {
                    total: this.tokens.length, candidates: 0, visible: 0,
                    culled: this.tokens.length, queryMs: 0,
                },
                visibleLightingSources: board?.visibleLightingSources || 0,
                samples: board ? this._sampleSprites(board) : null,
            };
        },

        benchmarkSetAnimatedTokens(tokens, sources) {
            const wanted = new Set((sources || []).map((source) => source.url));
            [...this.textures.keys()].forEach((url) => {
                if (String(url).startsWith("benchmark://") && !wanted.has(url)) this._forgetTexture(url);
            });
            (sources || []).forEach(({ url, canvas }) => {
                const existing = this.textures.get(url);
                if (existing && existing !== "queued" && existing !== "loading" && existing !== "error") return;
                const texture = PIXI.Texture.from(canvas);
                this.textures.set(url, texture);
                this.textureMeta.set(url, { bytes: canvas.width * canvas.height * 4, lastUsedAt: performance.now() });
                this.textureCacheBytes += canvas.width * canvas.height * 4;
            });
            this.setTokens(tokens);
            this.deps.requestRender?.();
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
