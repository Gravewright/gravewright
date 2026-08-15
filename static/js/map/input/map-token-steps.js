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
            const { canvas, scene, moves } = pending;
            pending = null;
            const roomId = canvas.dataset.roomId || "";
            const send = (move, cell) => window.GravewrightRealtime?.sendCommand?.(
                "token.move", { scene_id: scene.id, token_id: move.tokenId, grid_x: cell.x, grid_y: cell.y },
                { sceneId: scene.id, roomId });
            const changed = moves.filter((move) => move.from.x !== move.to.x || move.from.y !== move.to.y);
            if (!changed.length) return;
            changed.forEach((move) => send(move, move.to));


            history?.push?.({
                undo() { changed.forEach((move) => send(move, move.from)); },
                redo() { changed.forEach((move) => send(move, move.to)); },
            });
        }

        function schedule(canvas, scene, moves) {
            const key = moves.map((move) => move.tokenId).sort().join("|");
            if (pending && pending.key === key) {
                window.clearTimeout(pending.timer);
                const original = new Map(pending.moves.map((move) => [move.tokenId, move.from]));
                pending = { ...pending, moves: moves.map((move) => ({ ...move, from: original.get(move.tokenId) || move.from })) };
            } else {
                commit();
                pending = { canvas, scene, key, moves };
            }
            pending.timer = window.setTimeout(commit, SETTLE_MS);
        }



        function steppableTokens(canvas) {
            return [...selectedSet(canvas)]
                .map((id) => tokenStoreFor(canvas).get(id))
                .filter((token) => token && canControlToken(token, canvas));
        }

        function step(canvas, key) {
            const [dx, dy] = KEYS[key];
            const scene = sceneDataFor(canvas);
            if (!scene) return false;
            const tokens = steppableTokens(canvas);
            if (!tokens.length) return false;
            const store = tokenStoreFor(canvas);
            const pendingFrom = new Map((pending?.moves || []).map((move) => [move.tokenId, move.from]));
            const moves = tokens.map((token) => {
                const target = clampGridPosition(token.grid_x + dx, token.grid_y + dy, scene, token);
                return {
                    token, tokenId: token.token_id,
                    from: pendingFrom.get(token.token_id) || { x: token.grid_x, y: token.grid_y },
                    current: { x: token.grid_x, y: token.grid_y },
                    to: { x: target.grid_x, y: target.grid_y },
                };
            });
            const blocked = !effectiveIsGm?.(canvas) && moves.some((move) =>
                window.GravewrightLighting?.blocksMovement?.(
                    canvas, centreOf(move.token, move.current, scene), centreOf(move.token, move.to, scene)));
            if (blocked) return true;
            moves.forEach((move) => store.set(move.tokenId, {
                ...move.token, grid_x: move.to.x, grid_y: move.to.y,
            }));




            window.GravewrightLighting?.invalidateFor?.(canvas);
            markDirty(canvas);
            schedule(canvas, scene, moves.map(({ tokenId, from, to }) => ({ tokenId, from, to })));
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
