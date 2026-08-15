(() => {
    function createTokenClipboard(deps) {
        const { activeCanvas, history, selectedSet, setSelection, tokenStoreFor } = deps;
        let clipboard = [];
        let pending = null;

        const localMode = () => document.body?.dataset?.streamerMode === "true";
        const clone = (value) => JSON.parse(JSON.stringify(value));

        function copy(canvas) {
            const items = [...selectedSet(canvas)].map((id) => tokenStoreFor(canvas).get(id)).filter(Boolean);
            if (!items.length) return false;
            clipboard = items.map(clone);
            return true;
        }

        function remove(canvas, ids) {
            const sceneId = canvas.dataset.sceneId || "";
            const roomId = canvas.dataset.roomId || "";
            if (localMode()) {
                const store = tokenStoreFor(canvas);
                ids.forEach((id) => store.delete(id));
                window.GravewrightMap?.redraw?.();
                return;
            }
            ids.forEach((tokenId) => window.GravewrightRealtime?.sendCommand?.(
                "token.remove_from_scene", { scene_id: sceneId, token_id: tokenId }, { sceneId, roomId }));
        }

        function paste(canvas, source = clipboard, { record = true, onComplete = null } = {}) {
            if (!source.length || pending) return false;
            const sceneId = canvas.dataset.sceneId || "";
            const roomId = canvas.dataset.roomId || "";
            const tokenIds = source.map((token) => token.token_id).filter(Boolean);
            if (!tokenIds.length) return false;

            if (localMode()) {
                const store = tokenStoreFor(canvas);
                const created = source.map((token, index) => ({
                    ...clone(token), token_id: `clipboard-token-${Date.now()}-${index}-${Math.random().toString(16).slice(2)}`,
                    grid_x: Number(token.grid_x || 0) + 1, grid_y: Number(token.grid_y || 0) + 1,
                    version: 1,
                }));
                created.forEach((token) => store.set(token.token_id, token));
                setSelection(canvas, created.map((token) => token.token_id));
                window.GravewrightMap?.redraw?.();
                onComplete?.(created.map((token) => token.token_id));
                if (record) pushPasteHistory(canvas, source, created.map((token) => token.token_id));
                return true;
            }

            pending = { canvas, source: source.map(clone), remaining: tokenIds.length, ids: [], record, onComplete };
            const sent = window.GravewrightRealtime?.sendCommand?.(
                "token.duplicate_many", { scene_id: sceneId, token_ids: tokenIds, offset_x: 1, offset_y: 1 },
                { sceneId, roomId });
            if (!sent) pending = null;
            return Boolean(sent);
        }

        function pushPasteHistory(canvas, source, ids) {
            let liveIds = ids.slice();
            history?.push?.({
                undo() { remove(canvas, liveIds); },
                redo() {
                    pending = null;
                    paste(canvas, source, { record: false, onComplete: (ids) => { liveIds = ids; } });
                },
            });
        }

        document.addEventListener("vtt:transport-event", (event) => {
            if (!pending || event.detail?.event !== "tokens.created") return;
            const payload = event.detail?.payload || {};
            if (payload.scene_id !== pending.canvas.dataset.sceneId) return;
            const ids = (payload.tokens || []).map((token) => token.token_id).filter(Boolean);
            pending.ids.push(...ids);
            pending.remaining -= ids.length;
            if (pending.remaining > 0) return;
            const done = pending;
            pending = null;
            setSelection(done.canvas, done.ids);
            done.onComplete?.(done.ids);
            if (done.record) pushPasteHistory(done.canvas, done.source, done.ids);
        });

        return {
            copy: (canvas = activeCanvas()) => Boolean(canvas && copy(canvas)),
            hasData: () => clipboard.length > 0,
            paste: (canvas = activeCanvas()) => Boolean(canvas && paste(canvas)),
        };
    }

    window.GravewrightMapTokenClipboard = { createTokenClipboard };
})();
