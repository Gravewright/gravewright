(() => {
    function createLayerModeController(deps) {
        const {
            activeCanvas,
            getMeasureController,
            history,
            isGmForCanvas,
            renderMeasureOverlay,
            requestDrawAll,
            sceneDataFor,
            selectedSet,
        } = deps;

        let playerVisionActive = false;
        let activeDrawLayer = "game";
        let gmLayerBannerEl = null;
        let playerVisionBannerEl = null;

        function streamerLocalMode() {
            return document.body?.dataset?.streamerMode === "true";
        }

        function effectiveIsGm(canvas) {
            return isGmForCanvas(canvas) && !playerVisionActive;
        }

        function syncModeBannerStack() {
            const gmVisible = activeDrawLayer === "gm";
            if (playerVisionBannerEl) {
                playerVisionBannerEl.classList.toggle("is-stacked", gmVisible && playerVisionActive);
            }
        }

        function updatePlayerVisionIndicator() {
            if (playerVisionActive && !playerVisionBannerEl) {
                playerVisionBannerEl = document.createElement("div");
                playerVisionBannerEl.className = "gm-layer-banner gm-layer-banner--player-view";
                const icon = document.createElement("i");
                icon.className = "ph ph-eye-slash";
                icon.setAttribute("aria-hidden", "true");
                const label = document.createElement("span");
                label.textContent = document.querySelector("[data-vision-toggle]")
                    ?.dataset.playerViewBanner || "Player view";
                playerVisionBannerEl.append(icon, label);
                document.body.appendChild(playerVisionBannerEl);
            }
            if (playerVisionBannerEl) playerVisionBannerEl.classList.toggle("is-visible", playerVisionActive);
            syncModeBannerStack();
        }

        function updateGmLayerIndicator() {
            const active = activeDrawLayer === "gm";
            if (active && !gmLayerBannerEl) {
                gmLayerBannerEl = document.createElement("div");
                gmLayerBannerEl.className = "gm-layer-banner";
                const icon = document.createElement("i");
                icon.className = "ph ph-eye-slash";
                icon.setAttribute("aria-hidden", "true");
                const label = document.createElement("span");
                label.textContent = document.querySelector('[data-tool-sub-panel="layers"]')
                    ?.dataset.gmLayerBanner || "GM layer";
                gmLayerBannerEl.append(icon, label);
                document.body.appendChild(gmLayerBannerEl);
            }
            if (gmLayerBannerEl) gmLayerBannerEl.classList.toggle("is-visible", active);
            syncModeBannerStack();
        }

        function setPlayerVision(active) {
            const next = Boolean(active);
            if (next === playerVisionActive) return;
            playerVisionActive = next;
            document.dispatchEvent(new CustomEvent("vision:changed", {
                detail: { playerVision: playerVisionActive },
            }));
            updatePlayerVisionIndicator();
            requestDrawAll();
            renderMeasureOverlay(activeCanvas());
        }

        function setActiveLayer(layer) {
            activeDrawLayer = (layer === "gm" || layer === "composition") ? layer : "game";
            updateGmLayerIndicator();
        }

        function moveSelectionToLayer(layer, canvas = activeCanvas()) {
            if (!canvas || !isGmForCanvas(canvas)) return;
            const wantGm = layer === "gm";

            getMeasureController()?.moveSelectedMeasureToLayer(canvas, wantGm);

            const tokenIds = [...selectedSet(canvas)];
            if (tokenIds.length) {
                const scene = sceneDataFor(canvas);
                const roomId = canvas.dataset.roomId || "";
                const store = window.GravewrightMap?.tokenStoreFor?.(canvas);
                const changes = tokenIds
                    .map((id) => store?.get(id))
                    .filter((token) => token && token.hidden !== wantGm)
                    .map((token) => ({ token_id: token.token_id, from: !!token.hidden, to: wantGm }));
                tokenIds.forEach((id) => {
                    const token = store?.get(id);
                    if (streamerLocalMode()) {
                        if (token) store.set(id, { ...token, hidden: wantGm });
                        return;
                    }
                    window.GravewrightRealtime?.sendCommand?.(
                        wantGm ? "token.hide" : "token.reveal",
                        { scene_id: scene?.id, token_id: id },
                        { sceneId: scene?.id, roomId },
                    );
                });
                if (changes.length) {
                    history?.push?.({
                        undo() {
                            changes.forEach((change) => {
                                const token = store?.get(change.token_id);
                                if (streamerLocalMode()) {
                                    if (token) store.set(change.token_id, { ...token, hidden: change.from });
                                    requestDrawAll();
                                    return;
                                }
                                window.GravewrightRealtime?.sendCommand?.(
                                    change.from ? "token.hide" : "token.reveal",
                                    { scene_id: scene?.id, token_id: change.token_id },
                                    { sceneId: scene?.id, roomId },
                                );
                            });
                        },
                        redo() {
                            changes.forEach((change) => {
                                const token = store?.get(change.token_id);
                                if (streamerLocalMode()) {
                                    if (token) store.set(change.token_id, { ...token, hidden: change.to });
                                    requestDrawAll();
                                    return;
                                }
                                window.GravewrightRealtime?.sendCommand?.(
                                    change.to ? "token.hide" : "token.reveal",
                                    { scene_id: scene?.id, token_id: change.token_id },
                                    { sceneId: scene?.id, roomId },
                                );
                            });
                        },
                    });
                }
            }

            requestDrawAll();
        }

        function bindEvents() {
            document.addEventListener("tool:vision-toggle", () => {
                setPlayerVision(!playerVisionActive);
            });

            document.addEventListener("tool:active-layer", (event) => {
                setActiveLayer(event.detail?.layer);
            });

            document.addEventListener("tool:move-layer", (event) => {
                moveSelectionToLayer(event.detail?.layer);
            });
        }

        return {
            activeLayer: () => activeDrawLayer,
            bindEvents,
            effectiveIsGm,
            isPlayerView: () => playerVisionActive,
            setPlayerVision,
        };
    }

    window.GravewrightMapLayerMode = { createLayerModeController };
})();
