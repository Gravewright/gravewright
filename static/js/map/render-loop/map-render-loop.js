(() => {
    function createRenderLoop(deps) {
        const pendingCanvasFrames = new WeakSet();
        let pendingDrawAllFrame = false;
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

        function drawGrid(canvas) {
            const state = stateFor(canvas);
            const scene = sceneDataFor(canvas);

            if (scene) {
                requestManifest(canvas, scene);
                viewportUpdate(canvas);
            }

            boardRenderer.attach(canvas);
            boardRenderer.setTheme(theme);
            boardRenderer.setScene(scene);
            boardRenderer.setCamera({ offsetX: state.offsetX, offsetY: state.offsetY, zoom: state.zoom });
            boardRenderer.setTiles(scene ? runtimeFor(canvas) : null);
            const allTokens = scene ? [...tokenStoreFor(canvas).values()] : [];
            const visibleTokens = effectiveIsGm(canvas) ? allTokens : allTokens.filter((t) => !t.hidden);
            const roomId = canvas.dataset.roomId || "";
            const markerForToken = window.GravewrightCombatState?.markerForToken;
            boardRenderer.setTokens(visibleTokens.map((token) => {
                const marker = markerForToken?.(roomId, token.token_id) || null;
                return marker ? { ...token, combat_marker: marker } : token;
            }));
            boardRenderer.setOverlays({
                selectedIds: scene ? selectedIdsFor(canvas) : [],
                hoveredId: hoveredIdFor(canvas),
                drag: getActiveDrag()?.canvas === canvas ? getActiveDrag() : null,
                ghosts: scene ? getGhostsForScene(scene.id) : null,
                viewerIsGm: effectiveIsGm(canvas),
            });
            boardRenderer.setFog(scene ? (window.GravewrightFog?.fogViewFor?.(canvas, scene) ?? null) : null);
            boardRenderer.render();
            measureRender(canvas);

            state.dirty = false;
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

        function markDirty(canvas) {
            if (!canvas) return;
            stateFor(canvas).dirty = true;
            if (pendingCanvasFrames.has(canvas)) return;
            pendingCanvasFrames.add(canvas);
            window.requestAnimationFrame(() => {
                pendingCanvasFrames.delete(canvas);
                if (stateFor(canvas).dirty) drawGrid(canvas);
            });
        }

        return {
            drawAll,
            drawGrid,
            markDirty,
            requestDrawAll,
        };
    }

    window.GravewrightMapRenderLoop = { createRenderLoop };
})();
