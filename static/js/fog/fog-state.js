




(() => {
    const FI = (window.GravewrightFogInternals = window.GravewrightFogInternals || {});

    const OPACITY_STORAGE = "gravewright.fog.gm_opacity";
    const SIZE_MIN = 1;
    const SIZE_MAX = 80;

    
    const fogStates = new Map();
    
    const panelStates = new Map();

    

    function loadGmOpacity() {
        try {
            const v = parseFloat(localStorage.getItem(OPACITY_STORAGE));
            return Number.isFinite(v) ? Math.max(0.1, Math.min(1, v)) : 0.5;
        } catch { return 0.5; }
    }

    function saveGmOpacity(v) {
        try { localStorage.setItem(OPACITY_STORAGE, String(v)); } catch {  }
    }

    

    function panelStateFor(roomId) {
        let s = panelStates.get(roomId);
        if (!s) {
            s = {
                open: false,
                mode: "reveal",
                shape: "circle",
                size: 3,
                gmOpacity: loadGmOpacity(),
                polygonCellPoints: [],
            };
            panelStates.set(roomId, s);
        }
        return s;
    }

    function activeRoomWorkspace() {
        return document.querySelector(".room-workspace.is-active");
    }

    function activeRoomId() {
        return activeRoomWorkspace()?.dataset?.roomId || null;
    }

    function activePanelState() {
        const id = activeRoomId();
        return id ? panelStateFor(id) : null;
    }

    function activeFogPanel() {
        const id = activeRoomId();
        if (!id) return null;
        return document.querySelector(`[data-fog-panel][data-room-id="${CSS.escape(id)}"]`);
    }

    function activeSceneIdFromCanvas() {
        return window.GravewrightMap?.activeCanvas?.()?.dataset?.sceneId || null;
    }

    function isPanelVisible(panel) {
        return panel && !panel.hidden && panel.offsetParent !== null;
    }

    function isGmForRoom(roomId) {
        if (!roomId) return false;
        const el = document.querySelector(`[data-fog-panel][data-room-id="${CSS.escape(roomId)}"]`);
        return !!el;
    }

    

    function isActive() {
        const panel = activeFogPanel();
        if (!isPanelVisible(panel)) return false;
        const state = activePanelState();
        if (!state) return false;
        const fog = fogStates.get(activeSceneIdFromCanvas() || "");
        return !!(fog && fog.enabled);
    }

    function applyFog(sceneId, fog) {
        if (!sceneId || !fog) return;
        const existing = fogStates.get(sceneId);
        
        
        
        
        
        const isSnapshot = Array.isArray(fog.ops);
        if (existing && fog.version != null) {
            if (isSnapshot ? existing.version > fog.version : existing.version >= fog.version) return;
        }

        let ops;
        if (Array.isArray(fog.new_ops) && existing && existing.enabled) {
            ops = existing.ops.concat(fog.new_ops);
        } else if (Array.isArray(fog.ops)) {
            ops = fog.ops.slice();
        } else if (existing) {
            ops = existing.ops;
        } else {
            ops = [];
        }

        fogStates.set(sceneId, {
            enabled: !!fog.enabled,
            version: fog.version ?? 0,
            baseline: fog.baseline || "hide_all",
            ops,
        });
        const canvas = window.GravewrightMap?.activeCanvas?.();
        if (canvas?.dataset?.sceneId === sceneId) {
            window.GravewrightMap?.redraw?.();
        }
        FI.refreshPanelForActiveScene();
    }

    function appendLocalOp(sceneId, op) {
        const fog = fogStates.get(sceneId);
        if (!fog || !fog.enabled) return;
        fog.ops.push(op);
        window.GravewrightMap?.redraw?.();
    }

    

    
    
    
    
    function fogViewFor(canvas, scene) {
        if (!canvas || !scene) return null;

        const fog = fogStates.get(scene.id);
        if (!fog || !fog.enabled) return null;

        const roomId = canvas.dataset.roomId || "";
        
        const isGm = window.GravewrightMap?.viewerIsGm
            ? window.GravewrightMap.viewerIsGm(canvas)
            : isGmForRoom(roomId);
        const panel = panelStates.get(roomId);
        const alpha = isGm ? (panel?.gmOpacity ?? loadGmOpacity()) : 1.0;

        let inProgress = null;
        if (isGm && panel?.shape === "polygon" && panel.polygonCellPoints.length >= 1) {
            inProgress = { mode: panel.mode, points: panel.polygonCellPoints };
        }

        return {
            enabled: true,
            baseline: fog.baseline || "hide_all",
            ops: fog.ops,
            opsVersion: fog.ops.length,
            alpha,
            inProgress,
        };
    }

    

    FI.SIZE_MIN = SIZE_MIN;
    FI.SIZE_MAX = SIZE_MAX;
    FI.fogStates = fogStates;
    FI.panelStates = panelStates;
    FI.loadGmOpacity = loadGmOpacity;
    FI.saveGmOpacity = saveGmOpacity;
    FI.panelStateFor = panelStateFor;
    FI.activeRoomWorkspace = activeRoomWorkspace;
    FI.activeRoomId = activeRoomId;
    FI.activePanelState = activePanelState;
    FI.activeFogPanel = activeFogPanel;
    FI.activeSceneIdFromCanvas = activeSceneIdFromCanvas;
    FI.isPanelVisible = isPanelVisible;
    FI.isGmForRoom = isGmForRoom;
    FI.isActive = isActive;
    FI.applyFog = applyFog;
    FI.appendLocalOp = appendLocalOp;
    FI.fogViewFor = fogViewFor;
})();
