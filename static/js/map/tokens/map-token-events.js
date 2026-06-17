(() => {
    function createTokenEvents(deps) {
        const {
            api,
            isGmForCanvas,
            markDirty,
            sceneDataFor,
            tokenStoreFor,
            tokens,
        } = deps;

        function loadForScene(canvas, scene, force = false) {
            const existing = tokens.loadStateFor(canvas);
            if (!force && existing?.sceneId === scene.id && (existing.loading || existing.loaded)) return;

            tokens.setLoadState(canvas, { loading: true, loaded: false, sceneId: scene.id });

            api.loadSceneTokens(scene.id)
                .then((data) => {
                    const store = tokenStoreFor(canvas);
                    store.clear();
                    (data.tokens || []).forEach((tv) => store.set(tv.token_id, tv));
                    tokens.setLoadState(canvas, { loading: false, loaded: true, sceneId: scene.id });
                    document.dispatchEvent(new CustomEvent("vtt:tokens-loaded", {
                        detail: { sceneId: scene.id, roomId: canvas.dataset.roomId || "", tokens: data.tokens || [] },
                    }));
                    markDirty(canvas);
                })
                .catch(() => {
                    tokens.setLoadState(canvas, { loading: false, loaded: false, sceneId: scene.id });
                });
        }

        function forCanvasesWithScene(sceneId, fn) {
            document.querySelectorAll(`[data-map-canvas][data-scene-id="${sceneId}"]`)
                .forEach(fn);
        }

        function handleSnapshot(payload) {
            if (!payload?.scene_id) return;
            forCanvasesWithScene(payload.scene_id, (canvas) => {
                const store = tokenStoreFor(canvas);
                store.clear();
                (payload.tokens || []).forEach((tv) => store.set(tv.token_id, tv));
                tokens.setLoadState(canvas, {
                    loading: false,
                    loaded: true,
                    sceneId: payload.scene_id,
                });
                markDirty(canvas);
            });
        }

        function reloadForRoom(roomId) {
            if (!roomId) return;
            document.querySelectorAll(`[data-map-canvas][data-room-id="${CSS.escape(roomId)}"]`)
                .forEach((canvas) => {
                    const scene = sceneDataFor(canvas);
                    if (!scene) return;
                    tokens.setLoadState(canvas, {
                        loading: false,
                        loaded: false,
                        sceneId: scene.id,
                    });
                    loadForScene(canvas, scene);
                });
        }

        function handleCreated(payload) {
            if (!payload?.scene_id) return;
            forCanvasesWithScene(payload.scene_id, (canvas) => {
                const store = tokenStoreFor(canvas);
                const gm = isGmForCanvas(canvas);
                (payload.tokens || []).forEach((tv) => {
                    if (tv.hidden && !gm) return;
                    store.set(tv.token_id, tv);
                });
                markDirty(canvas);
            });
        }

        function handleMoved(payload) {
            if (!payload?.scene_id) return;
            forCanvasesWithScene(payload.scene_id, (canvas) => {
                const store = tokenStoreFor(canvas);
                (payload.tokens || []).forEach((move) => {
                    const token = store.get(move.token_id);
                    if (token) {
                        store.set(move.token_id, {
                            ...token,
                            grid_x: move.grid_x,
                            grid_y: move.grid_y,
                            version: move.version ?? token.version,
                        });
                    }
                });
                markDirty(canvas);
            });
        }

        function handleUpdated(payload) {
            if (!payload?.scene_id) return;
            forCanvasesWithScene(payload.scene_id, (canvas) => {
                const loadState = tokens.loadStateFor(canvas);
                if (loadState) loadState.loaded = false;
                const scene = sceneDataFor(canvas);
                if (scene) loadForScene(canvas, scene);
            });
        }

        function handleDeleted(payload) {
            if (!payload?.scene_id) return;
            forCanvasesWithScene(payload.scene_id, (canvas) => {
                const store = tokenStoreFor(canvas);
                (payload.token_ids || []).forEach((id) => store.delete(id));
                markDirty(canvas);
            });
        }

        function handleVisibilityChanged(payload) {
            if (!payload?.scene_id) return;
            forCanvasesWithScene(payload.scene_id, (canvas) => {
                const store = tokenStoreFor(canvas);
                const gm = isGmForCanvas(canvas);

                (payload.tokens || []).forEach((change) => {
                    if (gm) {
                        const token = store.get(change.token_id);
                        if (token) {
                            store.set(change.token_id, {
                                ...token,
                                hidden: change.hidden,
                                version: change.version ?? token.version,
                            });
                        }
                    } else if (change.hidden) {
                        store.delete(change.token_id);
                    } else {
                        const loadState = tokens.loadStateFor(canvas);
                        if (loadState) loadState.loaded = false;
                        const scene = sceneDataFor(canvas);
                        if (scene) loadForScene(canvas, scene);
                    }
                });
                markDirty(canvas);
            });
        }

        function handleConditionsUpdated(payload) {
            if (!payload?.scene_id || !payload?.token_id) return;
            forCanvasesWithScene(payload.scene_id, (canvas) => {
                const store = tokenStoreFor(canvas);
                const token = store.get(payload.token_id);
                if (token) {
                    store.set(payload.token_id, {
                        ...token,
                        conditions: payload.conditions ?? token.conditions,
                    });
                    markDirty(canvas);
                }
            });
        }

        return {
            forCanvasesWithScene,
            handleConditionsUpdated,
            handleCreated,
            handleDeleted,
            handleMoved,
            handleSnapshot,
            handleUpdated,
            handleVisibilityChanged,
            loadForScene,
            reloadForRoom,
        };
    }

    window.GravewrightMapTokenEvents = { createTokenEvents };
})();
