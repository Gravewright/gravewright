(() => {
    function createRenderLoop(deps) {
        const pendingCanvasFrames = new WeakSet();
        const dirtyFlags = new WeakMap();
        let pendingDrawAllFrame = false;
        const ALL_FLAGS = new Set(["scene", "camera", "tiles", "tokens", "overlays", "fog", "viewport"]);
        const {
            boardRenderer,
            effectiveIsGm,
            getActiveDrag,
            getGhostsForScene,
            hoveredIdFor,
            measureRender,
            requestManifest,
            runtimeFor,
            sceneDataFor,
            selectedIdsFor,
            stateFor,
            theme,
            tokenStoreFor,
            viewportUpdate,
        } = deps;

        function normalizeFlags(flags) {
            if (!flags || flags === "all") return new Set(ALL_FLAGS);
            if (typeof flags === "string") return new Set([flags]);
            if (Array.isArray(flags) || flags instanceof Set) return new Set(flags);
            return new Set(Object.keys(flags).filter((key) => flags[key]));
        }

        function mergeFlags(canvas, flags) {
            const merged = dirtyFlags.get(canvas) || new Set();
            normalizeFlags(flags).forEach((flag) => merged.add(flag));
            dirtyFlags.set(canvas, merged);
            return merged;
        }

        function drawGrid(canvas, requestedFlags = "all") {
            const flags = normalizeFlags(requestedFlags);
            const measureFrame = window.__gravewrightMeasureRender === true;
            const renderStartedAt = measureFrame ? performance.now() : 0;
            const state = stateFor(canvas);
            const scene = sceneDataFor(canvas);

            if (scene && (flags.has("scene") || flags.has("tiles") || flags.has("viewport"))) {
                requestManifest(canvas, scene);
            }
            if (scene && flags.has("viewport")) {
                viewportUpdate(canvas);
            }

            boardRenderer.attach(canvas);
            boardRenderer.setTheme(theme);
            if (flags.has("scene")) boardRenderer.setScene(scene);
            if (flags.has("camera")) boardRenderer.setCamera({ offsetX: state.offsetX, offsetY: state.offsetY, zoom: state.zoom });
            if (flags.has("tiles")) boardRenderer.setTiles(scene ? runtimeFor(canvas) : null);
            const allTokens = flags.has("tokens") && scene ? [...tokenStoreFor(canvas).values()] : [];
            const roomId = canvas.dataset.roomId || "";
            const layerVisible = (layer) => window.GravewrightTools?.isLayerVisible?.(layer, roomId) !== false;
            const visibleTokens = (effectiveIsGm(canvas) ? allTokens : allTokens.filter((t) => !t.hidden))
                .filter((token) => layerVisible(token.hidden ? "gm" : "game"));
            const markerForToken = window.GravewrightCombatState?.markerForToken;
            if (flags.has("tokens")) boardRenderer.setTokens(visibleTokens.map((token) => {
                const marker = markerForToken?.(roomId, token.token_id) || null;
                return marker ? { ...token, combat_marker: marker } : token;
            }));
            if (flags.has("overlays")) boardRenderer.setOverlays({
                selectedIds: scene ? selectedIdsFor(canvas) : [],
                hoveredId: hoveredIdFor(canvas),
                drag: getActiveDrag()?.canvas === canvas ? getActiveDrag() : null,
                ghosts: scene ? getGhostsForScene(scene.id) : null,
                viewerIsGm: effectiveIsGm(canvas),
                spatialSounds: scene
                    ? (window.GravewrightSpatialSounds?.snapshotFor?.(canvas) || null)
                    : null,
            });
            if (flags.has("fog")) boardRenderer.setFog(scene ? (window.GravewrightFog?.fogViewFor?.(canvas, scene) ?? null) : null);
            boardRenderer.render();
            const domStartedAt = measureFrame ? performance.now() : 0;
            measureRender(canvas);
            if (measureFrame) window.__gravewrightPerfRecord?.("dom_layout_style", performance.now() - domStartedAt);

            if (measureFrame) {
                const samples = window.__gravewrightRenderSamples
                    || (window.__gravewrightRenderSamples = []);
                samples.push(performance.now() - renderStartedAt);
                if (samples.length > 4000) samples.splice(0, samples.length - 4000);
            }

            state.dirty = false;
            dirtyFlags.delete(canvas);
        }

        function drawAll() {
            document.querySelectorAll("[data-map-canvas]").forEach((canvas) => {
                if (!canvas.closest(".room-workspace")?.classList.contains("is-active")) return;
                drawGrid(canvas);
            });
        }

        function requestDrawAll() {
            if (pendingDrawAllFrame) return;
            pendingDrawAllFrame = true;
            window.requestAnimationFrame(() => {
                pendingDrawAllFrame = false;
                drawAll();
            });
        }

        function markDirty(canvas, flags = "all") {
            if (!canvas) return;
            stateFor(canvas).dirty = true;
            mergeFlags(canvas, flags);
            if (pendingCanvasFrames.has(canvas)) return;
            pendingCanvasFrames.add(canvas);
            const requestedAt = window.__gravewrightMeasureRender === true ? performance.now() : 0;
            window.requestAnimationFrame(() => {
                if (requestedAt) window.__gravewrightPerfRecord?.("raf_wait", performance.now() - requestedAt);
                pendingCanvasFrames.delete(canvas);
                if (stateFor(canvas).dirty) drawGrid(canvas, dirtyFlags.get(canvas) || "all");
            });
        }

        return {
            drawAll,
            drawGrid,
            markDirty,
            invalidate: markDirty,
            flags: Object.freeze([...ALL_FLAGS]),
            requestDrawAll,
        };
    }

    window.GravewrightMapRenderLoop = { createRenderLoop };
})();
