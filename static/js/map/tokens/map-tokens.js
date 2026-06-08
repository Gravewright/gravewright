(() => {
    function createTokenStore(deps) {
        const stores = new WeakMap();
        const loadStates = new WeakMap();
        const { isGmForCanvas, sceneDataFor, stateFor, screenFromWorld } = deps;

        function storeFor(canvas) {
            let store = stores.get(canvas);
            if (!store) {
                store = new Map();
                stores.set(canvas, store);
            }
            return store;
        }

        function loadStateFor(canvas) {
            return loadStates.get(canvas) || null;
        }

        function setLoadState(canvas, state) {
            loadStates.set(canvas, state);
        }

        function clearLoadState(canvas) {
            loadStates.delete(canvas);
        }

        function canControl(token, canvas) {
            if (isGmForCanvas(canvas)) return true;
            if (!token.actor_id) return false;
            const card = document.querySelector(`[data-actor-card="${CSS.escape(token.actor_id)}"]`);
            return Boolean(card && card.dataset.canEdit === "true");
        }

        function atPoint(canvas, screenX, screenY) {
            const scene = sceneDataFor(canvas);
            if (!scene) return null;
            const state = stateFor(canvas);
            const store = storeFor(canvas);
            const s = scene.scaledTileSize;
            let hit = null;
            store.forEach((token) => {
                if (hit) return;
                const wCells = token.width_cells || 1;
                const hCells = token.height_cells || 1;
                const tokenSize = Math.min(wCells, hCells) * s * state.zoom;
                const cx = screenFromWorld((token.grid_x + wCells / 2) * s, state.offsetX, state.zoom);
                const cy = screenFromWorld((token.grid_y + hCells / 2) * s, state.offsetY, state.zoom);
                const dist = Math.sqrt((screenX - cx) ** 2 + (screenY - cy) ** 2);
                if (dist <= tokenSize * 0.42) hit = token;
            });
            return hit;
        }

        return {
            atPoint,
            canControl,
            clearLoadState,
            loadStateFor,
            setLoadState,
            storeFor,
        };
    }

    window.GravewrightMapTokens = { createTokenStore };
})();
