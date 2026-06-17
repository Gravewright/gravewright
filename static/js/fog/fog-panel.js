




(() => {
    const FI = (window.GravewrightFogInternals = window.GravewrightFogInternals || {});
    const SIZE_MIN = FI.SIZE_MIN;
    const SIZE_MAX = FI.SIZE_MAX;
    const fogStates = FI.fogStates;
    const activeFogPanel = FI.activeFogPanel;
    const activeSceneIdFromCanvas = FI.activeSceneIdFromCanvas;
    const activePanelState = FI.activePanelState;
    const panelStateFor = FI.panelStateFor;
    const saveGmOpacity = FI.saveGmOpacity;
    const hidePreview = FI.hidePreview;
    const sendEnable = FI.sendEnable;
    const sendDisable = FI.sendDisable;
    const sendReset = FI.sendReset;

    function notifyPanelContentUpdated(panel) {
        if (!panel || panel.hidden) return;
        document.dispatchEvent(new CustomEvent("vtt:modal-content-updated", {
            detail: { modal: panel },
        }));
    }

    function refreshPanelForActiveScene() {
        const panel = activeFogPanel();
        if (!panel) return;
        const sceneId = activeSceneIdFromCanvas();
        const fog = sceneId ? fogStates.get(sceneId) : null;
        const enabled = !!(fog && fog.enabled);

        const statusEl = panel.querySelector("[data-fog-status]");
        const enableControls = panel.querySelector("[data-fog-enable-controls]");
        const disableBtn = panel.querySelector("[data-fog-disable]");
        const toolsSection = panel.querySelector("[data-fog-tools]");

        if (statusEl) {
            statusEl.textContent = enabled
                ? (document.body.dataset.fogStatusEnabled || "Manual lighting is on.")
                : (document.body.dataset.fogStatusDisabled || "Manual lighting is off.");
        }

        if (enableControls) enableControls.hidden = enabled;
        if (disableBtn) disableBtn.hidden = !enabled;
        if (toolsSection) toolsSection.hidden = !enabled;
        notifyPanelContentUpdated(panel);
    }

    function syncPanelInputs() {
        const panel = activeFogPanel();
        const state = activePanelState();
        if (!panel || !state) return;

        panel.querySelectorAll("[data-fog-mode]").forEach((b) => {
            b.setAttribute("aria-pressed", b.dataset.fogMode === state.mode ? "true" : "false");
        });
        panel.querySelectorAll("[data-fog-shape]").forEach((b) => {
            b.setAttribute("aria-pressed", b.dataset.fogShape === state.shape ? "true" : "false");
        });

        const sizeRow = panel.querySelector("[data-fog-size-row]");
        if (sizeRow) sizeRow.hidden = state.shape === "polygon";

        const sizeInput = panel.querySelector("[data-fog-size]");
        const sizeOut = panel.querySelector("[data-fog-size-output]");
        if (sizeInput) sizeInput.value = state.size;
        if (sizeOut) sizeOut.textContent = String(state.size);

        const opacityInput = panel.querySelector("[data-fog-opacity]");
        const opacityOut = panel.querySelector("[data-fog-opacity-output]");
        if (opacityInput) opacityInput.value = Math.round(state.gmOpacity * 100);
        if (opacityOut) opacityOut.textContent = `${Math.round(state.gmOpacity * 100)}%`;
        notifyPanelContentUpdated(panel);
    }

    function clearPolygonInProgress() {
        const state = activePanelState();
        if (!state) return;
        state.polygonCellPoints = [];
        window.GravewrightMap?.redraw?.();
    }

    function bindPanel(panel) {
        const roomId = panel.dataset.roomId;
        if (!roomId) return;
        panelStateFor(roomId); 

        panel.addEventListener("click", (e) => {
            const enableBtn = e.target.closest("[data-fog-enable]");
            if (enableBtn) {
                const sceneId = activeSceneIdFromCanvas();
                if (!sceneId) return;
                sendEnable(roomId, sceneId, enableBtn.dataset.fogEnable);
                return;
            }
            const disableBtn = e.target.closest("[data-fog-disable]");
            if (disableBtn) {
                const sceneId = activeSceneIdFromCanvas();
                if (!sceneId) return;
                sendDisable(roomId, sceneId);
                clearPolygonInProgress();
                return;
            }
            const modeBtn = e.target.closest("[data-fog-mode]");
            if (modeBtn) {
                const state = panelStateFor(roomId);
                state.mode = modeBtn.dataset.fogMode;
                syncPanelInputs();
                return;
            }
            const shapeBtn = e.target.closest("[data-fog-shape]");
            if (shapeBtn) {
                const state = panelStateFor(roomId);
                state.shape = shapeBtn.dataset.fogShape;
                if (state.shape !== "polygon") clearPolygonInProgress();
                syncPanelInputs();
                return;
            }
            const resetBtn = e.target.closest("[data-fog-reset]");
            if (resetBtn) {
                const sceneId = activeSceneIdFromCanvas();
                if (!sceneId) return;
                sendReset(roomId, sceneId, resetBtn.dataset.fogReset);
                clearPolygonInProgress();
                return;
            }
        });

        panel.addEventListener("input", (e) => {
            const sizeInput = e.target.closest("[data-fog-size]");
            if (sizeInput) {
                const state = panelStateFor(roomId);
                state.size = Math.max(SIZE_MIN, Math.min(SIZE_MAX, parseInt(sizeInput.value, 10) || 1));
                syncPanelInputs();
                return;
            }
            const opacityInput = e.target.closest("[data-fog-opacity]");
            if (opacityInput) {
                const state = panelStateFor(roomId);
                state.gmOpacity = Math.max(0.1, Math.min(1, (parseInt(opacityInput.value, 10) || 50) / 100));
                saveGmOpacity(state.gmOpacity);
                syncPanelInputs();
                window.GravewrightMap?.redraw?.();
                return;
            }
        });
    }

    
    function observePanelVisibility(panel) {
        const observer = new MutationObserver(() => {
            const state = panelStateFor(panel.dataset.roomId);
            const wasOpen = state.open;
            state.open = !panel.hidden;
            if (!state.open) {
                hidePreview();
                clearPolygonInProgress();
                FI.activeBrush = null;
            }
            if (state.open && !wasOpen) {
                refreshPanelForActiveScene();
                syncPanelInputs();
            }
        });
        observer.observe(panel, { attributes: true, attributeFilter: ["hidden"] });
    }

    function initPanels() {
        document.querySelectorAll("[data-fog-panel]").forEach((panel) => {
            bindPanel(panel);
            observePanelVisibility(panel);
            const state = panelStateFor(panel.dataset.roomId);
            state.open = !panel.hidden;
            syncPanelInputs();
        });
        refreshPanelForActiveScene();
    }

    FI.refreshPanelForActiveScene = refreshPanelForActiveScene;
    FI.syncPanelInputs = syncPanelInputs;
    FI.clearPolygonInProgress = clearPolygonInProgress;
    FI.bindPanel = bindPanel;
    FI.observePanelVisibility = observePanelVisibility;
    FI.initPanels = initPanels;
})();
