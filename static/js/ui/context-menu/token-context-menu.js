



(() => {
    const FI = (window.GravewrightContextMenuInternals = window.GravewrightContextMenuInternals || {});
    const label = FI.label;
    const showMenu = FI.showMenu;

    function hasActorAccess(actorId) {
        if (!actorId) return false;
        return !!document.querySelector(`[data-actor-open="${CSS.escape(actorId)}"]`);
    }

    function streamerLocalMode() {
        return document.body?.dataset?.streamerMode === "true";
    }

    function setLocalVisibility(sceneId, tokenIds, hidden) {
        const canvas = Array.from(document.querySelectorAll("[data-map-canvas]"))
            .find((candidate) => candidate.dataset.sceneId === sceneId)
            || window.GravewrightMap?.activeCanvas?.();
        const store = canvas ? window.GravewrightMap?.tokenStoreFor?.(canvas) : null;
        if (!store) return;
        tokenIds.forEach((id) => {
            const token = store.get(id);
            if (token) store.set(id, { ...token, hidden });
        });
        window.GravewrightMap?.redraw?.();
    }

    function openTokenMenu(e) {
        const { token, x, y, sceneId, roomId, isGm } = e.detail;
        
        const tokenIds = Array.isArray(e.detail.tokenIds) && e.detail.tokenIds.length
            ? e.detail.tokenIds
            : [token.token_id];
        const actorIds = Array.isArray(e.detail.actorIds)
            ? e.detail.actorIds
            : (token.actor_id ? [token.actor_id] : []);
        const count = tokenIds.length;
        const suffix = count > 1 ? ` (${count})` : "";

        const items = [];

        
        if (count === 1 && token.token_id && token.actor_id && (isGm || hasActorAccess(token.actor_id))) {
            items.push({
                text: label("ctxTokenOpenSheet"),
                action() {
                    document.dispatchEvent(new CustomEvent("vtt:open-token-sheet", {
                        detail: { tokenId: token.token_id },
                    }));
                },
            });
        }

        if (isGm) {
            if (items.length) items.push({ type: "sep" });

            if (actorIds.length) {
                items.push({
                    text: label("ctxTokenAddCombat") + suffix,
                    action() {
                        fetch("/game/combat/participants/add", {
                            method: "POST",
                            headers: { "Content-Type": "application/json", Accept: "application/json" },
                            credentials: "same-origin",
                            body: JSON.stringify({ campaign_id: roomId, actor_ids: actorIds, token_ids: tokenIds }),
                        });
                    },
                });
            }

            items.push({
                text: (token.hidden ? label("ctxTokenReveal") : label("ctxTokenHide")) + suffix,
                small: true,
                action() {
                    const cmd = token.hidden ? "token.reveal" : "token.hide";
                    if (streamerLocalMode()) {
                        setLocalVisibility(sceneId, tokenIds, !token.hidden);
                        return;
                    }
                    tokenIds.forEach((id) => {
                        window.GravewrightRealtime?.sendCommand(
                            cmd,
                            { scene_id: sceneId, token_id: id },
                            { sceneId, roomId },
                        );
                    });
                },
            });

            items.push({ type: "sep" });

            items.push({
                text: label("ctxTokenRemove") + suffix,
                danger: true,
                action() {
                    showMenu(x, y, [{
                        text: label("ctxTokenRemoveConfirm"),
                        danger: true,
                        action() {
                            
                            if (window.GravewrightMap?.deleteTokens) {
                                window.GravewrightMap.deleteTokens(tokenIds);
                            } else {
                                tokenIds.forEach((id) => {
                                    window.GravewrightRealtime?.sendCommand(
                                        "token.remove_from_scene",
                                        { scene_id: sceneId, token_id: id },
                                        { sceneId, roomId },
                                    );
                                });
                            }
                        },
                    }]);
                },
            });
        }

        if (!items.length) return;
        showMenu(x, y, items);
    }

    FI.openTokenMenu = openTokenMenu;
})();
