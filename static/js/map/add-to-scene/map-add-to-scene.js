(() => {
    function createAddToSceneController(deps) {
        let state = null;
        const {
            activeCanvas,
            api,
            history,
            markDirty,
            sceneDataFor,
            screenToGridXY,
            stateFor,
            tokenSizeCells,
        } = deps;

        function footprintForBundle(bundle) {
            const size = String(bundle?.data?.size || "").trim().toLowerCase();
            const cells = tokenSizeCells[size] || 1;
            return { width_cells: cells, height_cells: cells };
        }

        function calcPlacementPositions(originX, originY, footprints) {
            const columns = Math.max(1, Math.ceil(Math.sqrt(footprints.length)));
            return footprints.map((footprint, i) => ({
                grid_x: originX + (i % columns),
                grid_y: originY + Math.floor(i / columns),
                width_cells: footprint.width_cells || 1,
                height_cells: footprint.height_cells || 1,
            }));
        }

        function streamerLocalMode() {
            return document.body?.dataset?.streamerMode === "true";
        }

        function actorName(actorId) {
            return document.querySelector(`[data-actor-card="${CSS.escape(actorId)}"] strong`)?.textContent?.trim()
                || document.querySelector(`[data-actor-open="${CSS.escape(actorId)}"]`)?.textContent?.trim()
                || "Token";
        }

        function placeLocalTokens({ actorIds, sceneId, positions }) {
            const canvas = activeCanvas();
            const store = canvas ? window.GravewrightMap?.tokenStoreFor?.(canvas) : null;
            if (!canvas || canvas.dataset.sceneId !== sceneId || !store) return [];
            const placed = actorIds.map((actorId, index) => {
                const pos = positions[index] || {};
                const token = {
                    token_id: `streamer-token-${Date.now()}-${Math.random().toString(16).slice(2)}`,
                    actor_id: actorId,
                    name: actorName(actorId),
                    grid_x: pos.grid_x || 0,
                    grid_y: pos.grid_y || 0,
                    width_cells: pos.width_cells || 1,
                    height_cells: pos.height_cells || 1,
                    hidden: false,
                    bars: {},
                };
                store.set(token.token_id, token);
                return token;
            });
            markDirty(canvas);
            return placed;
        }

        async function footprintsForActorIds(actorIds) {
            const footprints = await Promise.all(actorIds.map(async (actorId) => {
                try {
                    return footprintForBundle(await api.loadActorSheetBundle(actorId));
                } catch {
                    return null;
                }
            }));
            return footprints.map((footprint) => footprint || { width_cells: 1, height_cells: 1 });
        }

        function sendPlacement({ actorIds, sceneId, roomId, originX, originY, positions }) {
            let placed = actorIds.map((actorId, index) => ({
                actor_id: actorId,
                grid_x: positions[index]?.grid_x ?? originX,
                grid_y: positions[index]?.grid_y ?? originY,
            }));
            if (streamerLocalMode()) {
                placed = placeLocalTokens({ actorIds, sceneId, positions });
            } else {
                api.sendCommand(
                    "token.create_many_from_actors",
                    {
                        scene_id: sceneId,
                        actor_ids: actorIds,
                        origin: { grid_x: originX, grid_y: originY },
                    },
                    { sceneId, roomId },
                );
            }
            history?.push?.({
                undo() {
                    window.GravewrightMap?.removeTokensMatching?.(sceneId, placed);
                },
                redo() {
                    if (streamerLocalMode()) {
                        placed = placeLocalTokens({ actorIds, sceneId, positions });
                        return;
                    }
                    window.GravewrightRealtime?.sendCommand?.(
                        "token.create_many_from_actors",
                        { scene_id: sceneId, actor_ids: actorIds, origin: { grid_x: originX, grid_y: originY } },
                        { sceneId, roomId },
                    );
                },
            });
        }

        async function loadActorFootprints(target) {
            const footprints = await footprintsForActorIds(target.actorIds);

            if (state !== target) return;
            target.footprints = footprints;
            target.footprintsReady = true;
            if (Number.isInteger(target.originX) && Number.isInteger(target.originY)) {
                target.positions = calcPlacementPositions(target.originX, target.originY, target.footprints);
            }
            const canvas = activeCanvas();
            if (canvas) markDirty(canvas);
        }

        function start({ actorIds, sceneId, roomId }) {
            if (!Array.isArray(actorIds) || !actorIds.length) return;
            stop();
            state = {
                actorIds,
                sceneId,
                roomId,
                originX: null,
                originY: null,
                footprints: [],
                footprintsReady: false,
                positions: [],
            };
            loadActorFootprints(state);
            document.body.style.cursor = "crosshair";
            document.dispatchEvent(new CustomEvent("vtt:show-toast", {
                detail: {
                    id: "add-to-scene",
                    message: document.body.dataset.toastAddToScene || "Choose a location to place the token on the map",
                    duration: 0,
                },
            }));
        }

        function stop() {
            if (!state) return;
            state = null;
            document.body.style.cursor = "";
            document.dispatchEvent(new CustomEvent("vtt:dismiss-toast", {
                detail: { id: "add-to-scene" },
            }));
            const canvas = activeCanvas();
            if (canvas) markDirty(canvas);
        }

        function updatePreview(screenX, screenY) {
            if (!state) return;
            const canvas = activeCanvas();
            if (!canvas) return;
            const scene = sceneDataFor(canvas);
            if (!scene || scene.id !== state.sceneId) return;
            const viewState = stateFor(canvas);

            const { grid_x, grid_y } = screenToGridXY(screenX, screenY, viewState, scene);
            if (!state.footprintsReady) {
                state.originX = grid_x;
                state.originY = grid_y;
                state.positions = [];
                markDirty(canvas);
                return;
            }
            if (
                state.positions.length
                && state.originX === grid_x
                && state.originY === grid_y
            ) return;

            state.originX = grid_x;
            state.originY = grid_y;
            state.positions = calcPlacementPositions(grid_x, grid_y, state.footprints);
            markDirty(canvas);
        }

        function confirm() {
            if (!state) return;
            const { actorIds, sceneId, roomId, originX, originY, footprintsReady, positions } = state;
            if (!footprintsReady) return;
            if (!Number.isInteger(originX) || !Number.isInteger(originY)) return;
            sendPlacement({ actorIds, sceneId, roomId, originX, originY, positions });
            stop();
        }

        async function placeAt(canvas, { actorIds, sceneId, roomId, screenX, screenY }) {
            if (!canvas || !Array.isArray(actorIds) || !actorIds.length) return false;
            const scene = sceneDataFor(canvas);
            if (!scene || scene.id !== sceneId) return false;
            const { grid_x, grid_y } = screenToGridXY(screenX, screenY, stateFor(canvas), scene);
            const footprints = await footprintsForActorIds(actorIds);
            sendPlacement({
                actorIds,
                sceneId,
                roomId,
                originX: grid_x,
                originY: grid_y,
                positions: calcPlacementPositions(grid_x, grid_y, footprints),
            });
            return true;
        }

        function ghostsForScene(sceneId) {
            return state?.sceneId === sceneId ? state.positions : null;
        }

        return {
            calcPlacementPositions,
            confirm,
            footprintForBundle,
            ghostsForScene,
            isActive: () => Boolean(state),
            placeAt,
            start,
            stop,
            updatePreview,
        };
    }

    window.GravewrightMapAddToScene = { createAddToSceneController };
})();
