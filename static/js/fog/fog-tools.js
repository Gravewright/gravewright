




(() => {
    const FI = (window.GravewrightFogInternals = window.GravewrightFogInternals || {});
    const SIZE_MIN = FI.SIZE_MIN;
    const SIZE_MAX = FI.SIZE_MAX;
    const POLY_CLOSE_PX = 14;
    const DRAG_THROTTLE_MS = 40;

    const activePanelState = FI.activePanelState;
    const activeRoomId = FI.activeRoomId;
    const isActive = FI.isActive;
    const sendOps = FI.sendOps;
    const updatePreview = FI.updatePreview;
    const hidePreview = FI.hidePreview;

    FI.activeBrush = null; 

    function cellToClientCoords(cellPoint) {
        const canvas = window.GravewrightMap?.activeCanvas?.();
        if (!canvas) return null;
        const tileSize = parseInt(canvas.dataset.sceneTileSize, 10) || 70;
        const scale = parseFloat(canvas.dataset.sceneImageScale) || 1.0;
        const scaledTile = tileSize * scale;
        const cam = window.GravewrightMap?.activeCameraForScene?.(canvas.dataset.sceneId);
        if (!cam) return null;
        const rect = canvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        const viewW = (canvas.width || rect.width * dpr) / dpr;
        const viewH = (canvas.height || rect.height * dpr) / dpr;
        return {
            x: (cellPoint.x_cells * scaledTile - cam.worldX) * cam.zoom + viewW / 2 + rect.left,
            y: (cellPoint.y_cells * scaledTile - cam.worldY) * cam.zoom + viewH / 2 + rect.top,
        };
    }

    function pointerToCell(clientX, clientY) {
        const canvas = window.GravewrightMap?.activeCanvas?.();
        if (!canvas) return null;
        const world = window.GravewrightMap?.worldFromScreen?.(canvas, clientX, clientY);
        if (!world) return null;
        const tileSize = parseInt(canvas.dataset.sceneTileSize, 10) || 70;
        const scale = parseFloat(canvas.dataset.sceneImageScale) || 1.0;
        const scaledTile = tileSize * scale;
        return {
            x_cells: world.worldX / scaledTile,
            y_cells: world.worldY / scaledTile,
            sceneId: canvas.dataset.sceneId,
            roomId: canvas.dataset.roomId || activeRoomId() || "",
        };
    }

    function buildOpForBrush(state, cellX, cellY) {
        if (state.shape === "circle") {
            return {
                mode: state.mode,
                shape: "circle",
                geom: {
                    center_x_cells: cellX,
                    center_y_cells: cellY,
                    radius_cells: state.size / 2,
                },
            };
        }
        if (state.shape === "square") {
            return {
                mode: state.mode,
                shape: "square",
                geom: {
                    center_x_cells: cellX,
                    center_y_cells: cellY,
                    size_cells: state.size,
                },
            };
        }
        return null;
    }

    function handleBrushPoint(clientX, clientY) {
        const state = activePanelState();
        if (!state) return;
        const pt = pointerToCell(clientX, clientY);
        if (!pt) return;
        const op = buildOpForBrush(state, pt.x_cells, pt.y_cells);
        if (!op) return;
        sendOps(pt.roomId, pt.sceneId, [op]);
    }

    function handlePolygonClick(clientX, clientY) {
        const state = activePanelState();
        if (!state || state.shape !== "polygon") return;
        const pt = pointerToCell(clientX, clientY);
        if (!pt) return;

        if (state.polygonCellPoints.length >= 3) {
            const firstScreen = cellToClientCoords(state.polygonCellPoints[0]);
            if (firstScreen) {
                const dx = firstScreen.x - clientX;
                const dy = firstScreen.y - clientY;
                if (Math.hypot(dx, dy) <= POLY_CLOSE_PX) {
                    const op = {
                        mode: state.mode,
                        shape: "polygon",
                        geom: { points_cells: state.polygonCellPoints.map((p) => [p.x_cells, p.y_cells]) },
                    };
                    sendOps(pt.roomId, pt.sceneId, [op]);
                    state.polygonCellPoints = [];
                    window.GravewrightMap?.redraw?.();
                    return;
                }
            }
        }

        state.polygonCellPoints.push({ x_cells: pt.x_cells, y_cells: pt.y_cells });
        window.GravewrightMap?.redraw?.();
    }

    function onCapturePointerDown(event) {
        if (event.button !== 0) return;
        if (!isActive()) return;
        const canvas = event.target.closest("[data-map-canvas]");
        if (!canvas) return;

        event.preventDefault();
        event.stopPropagation();

        const state = activePanelState();
        if (!state) return;

        if (state.shape === "polygon") {
            handlePolygonClick(event.clientX, event.clientY);
            return;
        }

        FI.activeBrush = {
            roomId: canvas.dataset.roomId || activeRoomId() || "",
            sceneId: canvas.dataset.sceneId || "",
            lastSentAt: 0,
        };
        canvas.setPointerCapture?.(event.pointerId);
        handleBrushPoint(event.clientX, event.clientY);
        FI.activeBrush.lastSentAt = performance.now();
    }

    function onCapturePointerMove(event) {
        updatePreview(event.clientX, event.clientY);
        if (!FI.activeBrush) return;
        const now = performance.now();
        if (now - FI.activeBrush.lastSentAt < DRAG_THROTTLE_MS) return;
        FI.activeBrush.lastSentAt = now;
        handleBrushPoint(event.clientX, event.clientY);
    }

    function onCapturePointerUp(event) {
        if (!FI.activeBrush) return;
        const canvas = window.GravewrightMap?.activeCanvas?.();
        canvas?.releasePointerCapture?.(event.pointerId);
        FI.activeBrush = null;
    }

    function onPointerLeave() {
        hidePreview();
    }

    
    function handleAltWheel(event) {
        if (!isActive()) return false;
        const state = activePanelState();
        if (!state) return false;
        const delta = event.deltaY > 0 ? -1 : 1;
        const newSize = Math.max(SIZE_MIN, Math.min(SIZE_MAX, state.size + delta));
        if (newSize === state.size) return true;
        state.size = newSize;
        FI.syncPanelInputs();
        updatePreview(event.clientX, event.clientY);
        return true;
    }

    FI.cellToClientCoords = cellToClientCoords;
    FI.pointerToCell = pointerToCell;
    FI.buildOpForBrush = buildOpForBrush;
    FI.handleBrushPoint = handleBrushPoint;
    FI.handlePolygonClick = handlePolygonClick;
    FI.onCapturePointerDown = onCapturePointerDown;
    FI.onCapturePointerMove = onCapturePointerMove;
    FI.onCapturePointerUp = onCapturePointerUp;
    FI.onPointerLeave = onPointerLeave;
    FI.handleAltWheel = handleAltWheel;
})();
