(() => {
    function createSelectionController(deps) {
        const selectedTokenIds = new WeakMap();
        const hoveredTokenIds = new WeakMap();
        const { canControlToken, tokenStoreFor, markDirty } = deps;

        function selectedSet(canvas) {
            let set = selectedTokenIds.get(canvas);
            if (!set) {
                set = new Set();
                selectedTokenIds.set(canvas, set);
            }
            return set;
        }

        function hoveredId(canvas) {
            return hoveredTokenIds.get(canvas) || null;
        }

        function setHovered(canvas, tokenId) {
            hoveredTokenIds.set(canvas, tokenId || null);
        }

        function reset(canvas) {
            selectedTokenIds.set(canvas, new Set());
            hoveredTokenIds.set(canvas, null);
        }

        function isSelected(canvas, tokenId) {
            return selectedSet(canvas).has(tokenId);
        }

        function emitChanged(canvas) {
            const ids = [...selectedSet(canvas)];
            document.dispatchEvent(new CustomEvent("vtt:token-selection-changed", {
                detail: {
                    roomId: canvas.dataset.roomId || "",
                    sceneId: canvas.dataset.sceneId || "",
                    tokenId: ids.length ? ids[ids.length - 1] : null,
                    tokenIds: ids,
                },
            }));
        }

        function select(canvas, tokenId, { additive = false } = {}) {
            const set = selectedSet(canvas);
            const token = tokenId ? tokenStoreFor(canvas).get(tokenId) : null;
            const controllable = token && canControlToken(token, canvas);
            if (!tokenId) {
                if (additive) return;
                if (!set.size) return;
                set.clear();
            } else if (!controllable) {
                return;
            } else if (additive) {
                if (set.has(tokenId)) set.delete(tokenId);
                else set.add(tokenId);
            } else {
                set.clear();
                set.add(tokenId);
            }
            emitChanged(canvas);
            markDirty(canvas);
        }

        function setSelection(canvas, ids, { additive = false } = {}) {
            const set = selectedSet(canvas);
            if (!additive) set.clear();
            const store = tokenStoreFor(canvas);
            ids.forEach((id) => {
                const token = store.get(id);
                if (token && canControlToken(token, canvas)) set.add(id);
            });
            emitChanged(canvas);
            markDirty(canvas);
        }

        function clear(canvas) {
            const set = selectedSet(canvas);
            if (!set.size) return;
            set.clear();
            emitChanged(canvas);
            markDirty(canvas);
        }

        return {
            clear,
            hoveredId,
            isSelected,
            reset,
            select,
            selectedSet,
            setHovered,
            setSelection,
        };
    }

    window.GravewrightMapSelection = { createSelectionController };
})();
