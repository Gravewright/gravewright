



(() => {
    const FI = (window.GravewrightFogInternals = window.GravewrightFogInternals || {});
    const fogStates = FI.fogStates;
    const activePanelState = FI.activePanelState;
    const isActive = FI.isActive;

    let previewEl = null;

    function ensurePreviewEl() {
        if (previewEl) return previewEl;
        previewEl = document.createElement("div");
        previewEl.className = "fog-preview-cursor";
        document.body.appendChild(previewEl);
        return previewEl;
    }

    function updatePreview(clientX, clientY) {
        const state = activePanelState();
        if (!state || !isActive()) {
            hidePreview();
            return;
        }
        if (state.shape === "polygon") {
            hidePreview();
            return;
        }
        const canvas = window.GravewrightMap?.activeCanvas?.();
        const sceneId = canvas?.dataset?.sceneId;
        if (!canvas || !sceneId) {
            hidePreview();
            return;
        }
        const fog = fogStates.get(sceneId);
        if (!fog || !fog.enabled) {
            hidePreview();
            return;
        }
        const tileSize = parseInt(canvas.dataset.sceneTileSize, 10) || 70;
        const scale = parseFloat(canvas.dataset.sceneImageScale) || 1.0;
        const scaledTile = tileSize * scale;
        const cam = window.GravewrightMap?.activeCameraForScene?.(sceneId);
        const zoom = cam?.zoom ?? 1;
        const sizePx = state.size * scaledTile * zoom;

        const el = ensurePreviewEl();
        el.dataset.shape = state.shape;
        el.dataset.mode = state.mode;
        el.style.left = `${clientX}px`;
        el.style.top = `${clientY}px`;
        el.style.width = `${Math.max(4, sizePx)}px`;
        el.style.height = `${Math.max(4, sizePx)}px`;
        el.classList.add("fog-preview-cursor--visible");
    }

    function hidePreview() {
        if (previewEl) previewEl.classList.remove("fog-preview-cursor--visible");
    }

    FI.ensurePreviewEl = ensurePreviewEl;
    FI.updatePreview = updatePreview;
    FI.hidePreview = hidePreview;
})();
