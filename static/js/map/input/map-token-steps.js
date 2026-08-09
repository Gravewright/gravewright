(() => {








    const KEYS = {
        ArrowUp: [0, -1],
        ArrowDown: [0, 1],
        ArrowLeft: [-1, 0],
        ArrowRight: [1, 0],
    };

    const SETTLE_MS = 220;

    function createTokenSteps(deps) {
        const {
            canControlToken,
            clampGridPosition,
            effectiveIsGm,
            history,
            markDirty,
            sceneDataFor,
            selectedSet,
            tokenStoreFor,
        } = deps;

        let pending = null;

        function centreOf(token, cell, scene) {
            const size = scene.scaledTileSize;
            return {
                x: (cell.x + (token.width_cells || 1) / 2) * size,
                y: (cell.y + (token.height_cells || 1) / 2) * size,
            };
        }

        function commit() {
            if (!pending) return;
            const { canvas, scene, tokenId, from, to } = pending;
            pending = null;
            if (from.x === to.x && from.y === to.y) return;

            const roomId = canvas.dataset.roomId || "";
            const send = (cell) => window.GravewrightRealtime?.sendCommand?.(
                "token.move",
                { scene_id: scene.id, token_id: tokenId, grid_x: cell.x, grid_y: cell.y },
                { sceneId: scene.id, roomId },
            );
            send(to);


            history?.push?.({
                undo() { send(from); },
                redo() { send(to); },
            });
        }

        function schedule(canvas, scene, tokenId, from, to) {
            if (pending && pending.tokenId === tokenId) {
                window.clearTimeout(pending.timer);
                pending = { ...pending, to };
            } else {
                commit();
                pending = { canvas, scene, tokenId, from, to };
            }
            pending.timer = window.setTimeout(commit, SETTLE_MS);
        }



        function steppableToken(canvas) {
            const selected = [...selectedSet(canvas)];
            if (selected.length !== 1) return null;
            const token = tokenStoreFor(canvas).get(selected[0]);
            if (!token || !canControlToken(token, canvas)) return null;
            return token;
        }

        function step(canvas, key) {
            const [dx, dy] = KEYS[key];
            const scene = sceneDataFor(canvas);
            if (!scene) return false;
            const token = steppableToken(canvas);
            if (!token) return false;

            const target = clampGridPosition(token.grid_x + dx, token.grid_y + dy, scene, token);
            if (target.grid_x === token.grid_x && target.grid_y === token.grid_y) return true;

            const cell = { x: target.grid_x, y: target.grid_y };


            const blocked = !effectiveIsGm?.(canvas) && window.GravewrightLighting?.blocksMovement?.(
                canvas,
                centreOf(token, { x: token.grid_x, y: token.grid_y }, scene),
                centreOf(token, cell, scene),
            );
            if (blocked) return true;

            const store = tokenStoreFor(canvas);
            const from = pending && pending.tokenId === token.token_id
                ? pending.from
                : { x: token.grid_x, y: token.grid_y };
            store.set(token.token_id, { ...token, grid_x: cell.x, grid_y: cell.y });




            window.GravewrightLighting?.invalidateFor?.(canvas);
            markDirty(canvas);
            schedule(canvas, scene, token.token_id, from, cell);
            return true;
        }

        return {
            handles: (key) => Object.hasOwn(KEYS, key),
            step,
            flush: commit,
        };
    }

    window.GravewrightMapTokenSteps = { createTokenSteps };
})();
