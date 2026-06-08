(() => {
    function createTokenDeleteController(deps) {
        const {
            activeCanvas,
            clearSelection,
            history,
            sceneDataFor,
            selectedSet,
            tokenStoreFor,
        } = deps;

        const undoStack = [];

        function streamerLocalMode() {
            return document.body?.dataset?.streamerMode === "true";
        }

        function createTokens(sceneId, roomId, tokens) {
            if (streamerLocalMode()) {
                const canvas = activeCanvas();
                const store = canvas ? tokenStoreFor(canvas) : null;
                if (!canvas || canvas.dataset.sceneId !== sceneId || !store) return;
                tokens.forEach((token) => {
                    if (token?.token_id) store.set(token.token_id, token);
                });
                window.GravewrightMap?.redraw?.();
                return;
            }
            tokens.forEach((token) => {
                window.GravewrightRealtime?.sendCommand(
                    "token.create_many_from_actors",
                    {
                        scene_id: sceneId,
                        actor_ids: [token.actor_id],
                        origin: { grid_x: token.grid_x, grid_y: token.grid_y },
                    },
                    { sceneId, roomId },
                );
            });
        }

        function snapshotAndDelete(canvas, tokenIds) {
            const scene = sceneDataFor(canvas);
            if (!scene || !tokenIds.length) return false;

            const store = tokenStoreFor(canvas);
            const roomId = canvas.dataset.roomId || "";
            const snapshots = [];

            tokenIds.forEach((id) => {
                const token = store.get(id);
                if (!token) return;
                if (token.actor_id) {
                    snapshots.push(streamerLocalMode()
                        ? { ...token }
                        : {
                            actor_id: token.actor_id,
                            grid_x: token.grid_x,
                            grid_y: token.grid_y,
                        });
                }
                if (streamerLocalMode()) {
                    store.delete(id);
                    window.GravewrightMap?.redraw?.();
                    return;
                }
                window.GravewrightRealtime?.sendCommand(
                    "token.remove_from_scene",
                    { scene_id: scene.id, token_id: id },
                    { sceneId: scene.id, roomId },
                );
            });

            if (snapshots.length) {
                undoStack.push({ sceneId: scene.id, roomId, tokens: snapshots });
                history?.push?.({
                    undo() {
                        createTokens(scene.id, roomId, snapshots);
                    },
                    redo() {
                        window.GravewrightMap?.removeTokensMatching?.(scene.id, snapshots);
                    },
                });
            }
            clearSelection(canvas);
            return true;
        }

        function deleteSelected(canvas) {
            const set = selectedSet(canvas);
            if (!set.size) return false;
            return snapshotAndDelete(canvas, [...set]);
        }

        function deleteTokens(tokenIds) {
            const canvas = activeCanvas();
            if (!canvas || !Array.isArray(tokenIds) || !tokenIds.length) return false;
            return snapshotAndDelete(canvas, tokenIds);
        }

        function undoLastDelete() {
            const entry = undoStack.pop();
            if (!entry) return false;

            createTokens(entry.sceneId, entry.roomId, entry.tokens);
            return true;
        }

        return {
            deleteSelected,
            deleteTokens,
            hasUndo: () => undoStack.length > 0,
            undoLastDelete,
        };
    }

    window.GravewrightMapTokenDelete = { createTokenDeleteController };
})();
