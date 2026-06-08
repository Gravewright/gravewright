(() => {
    function bindTokenDomEvents(deps) {
        const {
            activeCanvas,
            canControlToken,
            isGmForCanvas,
            isSelected,
            markDirty,
            sceneDataFor,
            selectToken,
            selectedSet,
            selection,
            tokenAtPoint,
            tokenStoreFor,
        } = deps;

        function hoverToken(canvas, tokenId) {
            const nextTokenId = tokenId && tokenStoreFor(canvas).has(tokenId) ? tokenId : null;
            if (selection.hoveredId(canvas) === nextTokenId) return;
            selection.setHovered(canvas, nextTokenId);
            markDirty(canvas);
        }

        function canvasForToken(tokenId) {
            const active = activeCanvas();
            if (active && tokenStoreFor(active).has(tokenId)) return active;
            return Array.from(document.querySelectorAll("[data-map-canvas]"))
                .find((canvas) => tokenStoreFor(canvas).has(tokenId)) || null;
        }

        document.addEventListener("contextmenu", (event) => {
            const canvas = event.target.closest("[data-map-canvas]");
            if (!canvas) return;
            event.preventDefault();

            const hit = tokenAtPoint(canvas, event.clientX, event.clientY);
            if (!hit) return;

            const isGm = isGmForCanvas(canvas);
            if (!isGm && !canControlToken(hit, canvas)) return;

            const scene = sceneDataFor(canvas);

            let ids;
            if (isSelected(canvas, hit.token_id) && selectedSet(canvas).size > 1) {
                ids = [...selectedSet(canvas)];
            } else {
                selectToken(canvas, hit.token_id);
                ids = [hit.token_id];
            }

            const store = tokenStoreFor(canvas);
            const tokens = ids.map((id) => store.get(id)).filter(Boolean);
            const actorIds = [...new Set(tokens.map((token) => token.actor_id).filter(Boolean))];

            document.dispatchEvent(new CustomEvent("vtt:token-contextmenu", {
                detail: {
                    token: hit,
                    tokens,
                    tokenIds: ids,
                    actorIds,
                    x: event.clientX,
                    y: event.clientY,
                    sceneId: scene?.id || "",
                    roomId: canvas.dataset.roomId || "",
                    isGm,
                },
            }));
        });

        document.addEventListener("vtt:token-select", (event) => {
            const tokenId = event.detail?.tokenId || "";
            const canvas = tokenId ? canvasForToken(tokenId) : activeCanvas();
            if (!canvas) return;
            selectToken(canvas, tokenId || null);
        });

        document.addEventListener("vtt:token-hover", (event) => {
            const tokenId = event.detail?.tokenId || "";
            const canvas = tokenId ? canvasForToken(tokenId) : activeCanvas();
            if (!canvas) return;
            hoverToken(canvas, tokenId || null);
        });

        document.addEventListener("dblclick", (event) => {
            const canvas = event.target.closest("[data-map-canvas]");
            if (!canvas) return;

            const hit = tokenAtPoint(canvas, event.clientX, event.clientY);
            if (!hit?.token_id) return;
            if (
                !isGmForCanvas(canvas)
                && !document.querySelector(`[data-actor-open="${CSS.escape(hit.actor_id)}"]`)
            ) {
                return;
            }

            document.dispatchEvent(new CustomEvent("vtt:open-token-sheet", {
                detail: { tokenId: hit.token_id },
            }));
        });
    }

    window.GravewrightMapTokenDomEvents = { bindTokenDomEvents };
})();
