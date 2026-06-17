(() => {
    function createTokenDragController(deps) {
        const {
            canControlToken,
            clampGridPosition,
            history,
            isSelected,
            markDirty,
            sceneDataFor,
            screenToWorldXY,
            selectToken,
            selectedSet,
            snapDragToGrid,
            stateFor,
            tokenStoreFor,
        } = deps;

        let activeDrag = null;

        function streamerLocalMode() {
            return document.body?.dataset?.streamerMode === "true";
        }

        function start(canvas, event, hit, { additive = false } = {}) {
            if (additive) {
                selectToken(canvas, hit.token_id, { additive: true });
                return true;
            }

            if (!isSelected(canvas, hit.token_id)) {
                selectToken(canvas, hit.token_id);
            }

            const scene = sceneDataFor(canvas);
            if (!scene || !canControlToken(hit, canvas)) return true;

            const store = tokenStoreFor(canvas);
            const group = [...selectedSet(canvas)]
                .map((id) => store.get(id))
                .filter((token) => token && canControlToken(token, canvas))
                .map((token) => ({
                    tokenId: token.token_id,
                    startGridX: token.grid_x,
                    startGridY: token.grid_y,
                }));

            if (!group.some((token) => token.tokenId === hit.token_id)) {
                group.push({
                    tokenId: hit.token_id,
                    startGridX: hit.grid_x,
                    startGridY: hit.grid_y,
                });
            }

            const state = stateFor(canvas);
            const pointerWorld = screenToWorldXY(event.clientX, event.clientY, state);
            const tokenWorldX = hit.grid_x * scene.scaledTileSize;
            const tokenWorldY = hit.grid_y * scene.scaledTileSize;

            activeDrag = {
                canvas,
                pointerId: event.pointerId,
                tokenId: hit.token_id,
                startGridX: hit.grid_x,
                startGridY: hit.grid_y,
                currentGridX: hit.grid_x,
                currentGridY: hit.grid_y,
                currentWorldX: tokenWorldX,
                currentWorldY: tokenWorldY,
                grabOffsetWorldX: pointerWorld.worldX - tokenWorldX,
                grabOffsetWorldY: pointerWorld.worldY - tokenWorldY,
                hasMoved: false,
                group,
            };
            canvas.setPointerCapture(event.pointerId);
            return true;
        }

        function update(event) {
            if (!activeDrag || activeDrag.pointerId !== event.pointerId) return false;

            const scene = sceneDataFor(activeDrag.canvas);
            if (!scene) return true;

            const state = stateFor(activeDrag.canvas);
            const token = tokenStoreFor(activeDrag.canvas).get(activeDrag.tokenId);
            const pointerWorld = screenToWorldXY(event.clientX, event.clientY, state);
            const tokenW = (token?.width_cells || 1) * scene.scaledTileSize;
            const tokenH = (token?.height_cells || 1) * scene.scaledTileSize;
            const maxWorldX = Math.max(0, scene.width - tokenW);
            const maxWorldY = Math.max(0, scene.height - tokenH);

            activeDrag.currentWorldX = Math.max(
                0,
                Math.min(maxWorldX, pointerWorld.worldX - activeDrag.grabOffsetWorldX),
            );
            activeDrag.currentWorldY = Math.max(
                0,
                Math.min(maxWorldY, pointerWorld.worldY - activeDrag.grabOffsetWorldY),
            );

            const { grid_x, grid_y } = snapDragToGrid(
                activeDrag.currentWorldX,
                activeDrag.currentWorldY,
                scene,
                token,
            );
            activeDrag.currentGridX = grid_x;
            activeDrag.currentGridY = grid_y;
            activeDrag.hasMoved = true;

            if (activeDrag.group && activeDrag.group.length > 1) {
                const dx = grid_x - activeDrag.startGridX;
                const dy = grid_y - activeDrag.startGridY;
                const tile = scene.scaledTileSize;
                const store = tokenStoreFor(activeDrag.canvas);
                const positions = {};

                activeDrag.group.forEach((groupToken) => {
                    const tokenInGroup = store.get(groupToken.tokenId);
                    const clamped = clampGridPosition(
                        groupToken.startGridX + dx,
                        groupToken.startGridY + dy,
                        scene,
                        tokenInGroup,
                    );
                    positions[groupToken.tokenId] = {
                        worldX: clamped.grid_x * tile,
                        worldY: clamped.grid_y * tile,
                        gridX: clamped.grid_x,
                        gridY: clamped.grid_y,
                    };
                });
                activeDrag.positions = positions;
            }

            markDirty(activeDrag.canvas);
            return true;
        }

        function stop(event) {
            if (!activeDrag || activeDrag.pointerId !== event.pointerId) return false;

            const drag = activeDrag;
            const { canvas, tokenId, currentGridX, currentGridY, hasMoved, startGridX, startGridY } = drag;
            activeDrag = null;

            try {
                canvas.releasePointerCapture(event.pointerId);
            } catch {
                
            }

            if (hasMoved) {
                const scene = sceneDataFor(canvas);
                if (scene) {
                    const store = tokenStoreFor(canvas);
                    const roomId = canvas.dataset.roomId || "";
                    const moves = [];
                    const applyLocalMove = (id, position) => {
                        const token = store.get(id);
                        if (token) store.set(id, { ...token, ...position });
                        markDirty(canvas);
                    };
                    const sendMove = (id, gx, gy) => {
                        const token = store.get(id);
                        if (token && (token.grid_x !== gx || token.grid_y !== gy)) {
                            moves.push({
                                token_id: id,
                                from: { grid_x: token.grid_x, grid_y: token.grid_y },
                                to: { grid_x: gx, grid_y: gy },
                            });
                        }
                        if (token) store.set(id, { ...token, grid_x: gx, grid_y: gy });
                        if (streamerLocalMode()) return;
                        window.GravewrightRealtime?.sendCommand(
                            "token.move",
                            { scene_id: scene.id, token_id: id, grid_x: gx, grid_y: gy },
                            { sceneId: scene.id, roomId },
                        );
                    };

                    if (drag.group && drag.group.length > 1 && drag.positions) {
                        drag.group.forEach((groupToken) => {
                            const pos = drag.positions[groupToken.tokenId];
                            if (
                                pos
                                && (pos.gridX !== groupToken.startGridX || pos.gridY !== groupToken.startGridY)
                            ) {
                                sendMove(groupToken.tokenId, pos.gridX, pos.gridY);
                            }
                        });
                    } else if (currentGridX !== startGridX || currentGridY !== startGridY) {
                        sendMove(tokenId, currentGridX, currentGridY);
                    }
                    if (moves.length) {
                        history?.push?.({
                            undo() {
                                moves.forEach((move) => {
                                    if (streamerLocalMode()) {
                                        applyLocalMove(move.token_id, move.from);
                                        return;
                                    }
                                    window.GravewrightRealtime?.sendCommand?.(
                                        "token.move",
                                        { scene_id: scene.id, token_id: move.token_id, ...move.from },
                                        { sceneId: scene.id, roomId },
                                    );
                                });
                            },
                            redo() {
                                moves.forEach((move) => {
                                    if (streamerLocalMode()) {
                                        applyLocalMove(move.token_id, move.to);
                                        return;
                                    }
                                    window.GravewrightRealtime?.sendCommand?.(
                                        "token.move",
                                        { scene_id: scene.id, token_id: move.token_id, ...move.to },
                                        { sceneId: scene.id, roomId },
                                    );
                                });
                            },
                        });
                    }
                }
            }

            markDirty(canvas);
            return true;
        }

        return {
            active: () => activeDrag,
            start,
            stop,
            update,
        };
    }

    window.GravewrightMapTokenDrag = { createTokenDragController };
})();
