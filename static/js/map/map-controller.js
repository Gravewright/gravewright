(() => {
    const DEFAULT_GRID_SIZE = 56;
    const MIN_ZOOM = 0.35;
    const MAX_ZOOM = 3.2;
    const CHUNK_MAGIC = "GWCB";
    const CHUNK_HEADER_BYTES = 12;
    const DEFAULT_CHUNK_SIZE = 16;
    const VIEWPORT_UPDATE_MS = 60;
    const CHUNK_STREAM_RETRY_MS = 450;



    const CHUNK_STREAM_MAX_RETRIES = 5;


    const CHUNK_STREAM_PULL_MS = 15;




    const VIEW_CHUNK_MARGIN = 0;
    const BOARD_PING_HOLD_MS = 700;
    const BOARD_PING_MOVE_TOLERANCE = 10;
    const CAMERA_STORAGE_PREFIX = "gravewright.scene.camera.";
    const CAMERA_STORAGE_VERSION = 2;
    const CAMERA_SAVE_MS = 220;
    const TOKEN_SIZE_CELLS = {
        tiny: 1,
        small: 1,
        medium: 1,
        large: 2,
        huge: 3,
        gargantuan: 4,
    };





    const BOARD_THEME = {
        background: "#11151a",
        gridColor: "rgba(192,154,90,0.18)",
        originColor: "rgba(192,154,90,0.45)",
        sceneBorderColor: "rgba(255,255,255,0.12)",
    };



    const boardRenderer = window.GravewrightBoard.create("pixi", {
        requestRender: (flags = "all") => requestDrawAll(flags),
    });
    let boardPruneFrame = 0;
    const boardObserver = new MutationObserver(() => {
        if (boardPruneFrame) return;
        boardPruneFrame = window.requestAnimationFrame(() => {
            boardPruneFrame = 0;
            boardRenderer.pruneDisconnectedBoards?.();
        });
    });
    boardObserver.observe(document.body, { childList: true, subtree: true });
    let boardDestroyed = false;
    const destroyBoard = () => {
        if (boardDestroyed) return;
        boardDestroyed = true;
        boardObserver.disconnect();
        if (boardPruneFrame) window.cancelAnimationFrame(boardPruneFrame);
        boardPruneFrame = 0;
        boardRenderer.destroy?.();
    };
    window.addEventListener("pagehide", destroyBoard, { once: true });
    window.addEventListener("vtt:game-exit", destroyBoard, { once: true });

    const mapApi = window.GravewrightMapApi;
    const mapScene = window.GravewrightMapScene.createSceneController({
        defaultGridSize: DEFAULT_GRID_SIZE,
        maxZoom: MAX_ZOOM,
        minZoom: MIN_ZOOM,
    });
    let mapStreaming;
    let mapMeasureController;
    const mapCamera = window.GravewrightMapCamera.createCameraController({
        storagePrefix: CAMERA_STORAGE_PREFIX,
        storageVersion: CAMERA_STORAGE_VERSION,
        saveMs: CAMERA_SAVE_MS,
        sceneDataFor,
        viewportSizeFor,
        clampZoom,
        markDirty,
        scheduleViewportUpdate,
    });
    const mapPan = window.GravewrightMapPan.createPanController({
        markDirty,
        saveCameraNow,
        scheduleCameraSave,
        scheduleViewportUpdate,
        stateFor,
    });
    const mapTokens = window.GravewrightMapTokens.createTokenStore({
        isGmForCanvas,
        sceneDataFor,
        stateFor,
        screenFromWorld,
    });
    const mapTokenEvents = window.GravewrightMapTokenEvents.createTokenEvents({
        api: mapApi,
        isGmForCanvas,
        markDirty,
        sceneDataFor,
        tokenStoreFor,
        tokens: mapTokens,
    });
    const boardHistory = window.GravewrightBoardHistory.createBoardHistory();
    const mapTokenDelete = window.GravewrightMapTokenDelete.createTokenDeleteController({
        activeCanvas,
        clearSelection,
        history: boardHistory,
        sceneDataFor,
        selectedSet,
        tokenStoreFor,
    });
    const mapSelection = window.GravewrightMapSelection.createSelectionController({
        activeLayer: () => mapLayerMode?.activeLayer?.() || "game",
        canControlToken,
        tokenStoreFor,
        markDirty,
    });
    const mapTokenClipboard = window.GravewrightMapTokenClipboard.createTokenClipboard({
        activeCanvas,
        history: boardHistory,
        selectedSet,
        setSelection,
        tokenStoreFor,
    });
    const mapMarquee = window.GravewrightMapMarquee.createMarqueeController({
        clearSelection,
        sceneDataFor,
        screenToWorldXY,
        setSelection,
        stateFor,
        tokenStoreFor,
    });
    const mapTokenDrag = window.GravewrightMapTokenDrag.createTokenDragController({
        canControlToken,
        clampGridPosition,
        effectiveIsGm,
        history: boardHistory,
        isSelected,
        markDirty,
        sceneDataFor,
        screenToWorldXY,
        selectToken,
        selectedSet,
        snapDragToGrid,
        stateFor,
        tokenStoreFor,
    });
    mapStreaming = window.GravewrightMapStreaming.createSceneStreaming({
        api: mapApi,
        applyCameraToState,
        applyMeasureSnapshot,
        chunkHeaderBytes: CHUNK_HEADER_BYTES,
        chunkMagic: CHUNK_MAGIC,
        defaultChunkSize: DEFAULT_CHUNK_SIZE,
        defaultGridSize: DEFAULT_GRID_SIZE,
        initialCameraFor,
        loadTokensForScene,
        markDirty,
        maxRetries: CHUNK_STREAM_MAX_RETRIES,
        pullMs: CHUNK_STREAM_PULL_MS,
        retryMs: CHUNK_STREAM_RETRY_MS,
        sceneDataFor,
        selection: mapSelection,
        stateFor,
        tokens: mapTokens,
        tokenStoreFor,
        viewportSizeFor,
        viewportUpdateMs: VIEWPORT_UPDATE_MS,
        viewChunkMargin: VIEW_CHUNK_MARGIN,
    });
    const mapBoardPing = window.GravewrightMapBoardPing.createBoardPingController({
        holdMs: BOARD_PING_HOLD_MS,
        moveTolerance: BOARD_PING_MOVE_TOLERANCE,
        activeCanvas,
        sceneDataFor,
        stateFor,
        screenFromWorld,
        screenToWorldXY,
        focusWorldPoint,
        boardRenderer,
    });
    document.addEventListener("vtt:transport-event", (event) => {
        const detail = event.detail ?? {};
        if (detail.event === "board.ping") mapBoardPing.handle(detail.payload);
    });
    const mapAddToScene = window.GravewrightMapAddToScene.createAddToSceneController({
        activeCanvas,
        api: mapApi,
        history: boardHistory,
        markDirty,
        sceneDataFor,
        screenToGridXY,
        stateFor,
        tokenSizeCells: TOKEN_SIZE_CELLS,
    });
    const mapLayerMode = window.GravewrightMapLayerMode.createLayerModeController({
        activeCanvas,
        getMeasureController: () => mapMeasureController,
        history: boardHistory,
        isGmForCanvas,
        renderMeasureOverlay,
        requestDrawAll,
        sceneDataFor,
        selectedSet,
    });
    const mapMeasures = window.GravewrightMapMeasures.createMeasureToolkit({
        activeCanvas,
        boardRenderer,
        activeDrawColor: (canvas) => window.GravewrightTools?.activeDrawColor || canvas.dataset.activeDrawColor || "#f8fafc",
        applyActiveLayer,
        broadcastAreaMarkerUpsert,
        broadcastDrawUpsert,
        currentUserId,
        defaultGridSize: DEFAULT_GRID_SIZE,
        effectiveIsGm,
        getActiveFreehand: () => mapMeasureController?.activeFreehand() || null,
        getActiveMeasure: () => mapMeasureController?.activeMeasure() || null,
        history: boardHistory,
        isGmForCanvas,
        onRenderStart: (canvas) => {
            if (mapMeasureEditors?.activeAreaMarkerCanvas() === canvas) {
                mapMeasureEditors.positionAreaMarkerTextEditor();
            }
        },
        sceneDataFor,
        selectedMeasureIdFor,
        setSelectedMeasure,
        stateFor,
        screenFromWorld,
        screenToWorldXY,
        textFontSizeFor,
        upsertMeasureLocal,
    });
    const mapMeasureEditors = mapMeasures.editors;
    mapMeasureController = window.GravewrightMapMeasureController.createMeasureController({
        activeCanvas,
        activeDrawLayer: () => mapLayerMode.activeLayer(),
        currentUserId,
        defaultGridSize: DEFAULT_GRID_SIZE,
        history: boardHistory,
        isGmForCanvas,
        measures: mapMeasures,
        sceneDataFor,
        stateFor,
    });
    document.querySelectorAll("[data-map-canvas][data-scene-id]").forEach((canvas) => {
        try {
            const boardItems = JSON.parse(canvas.dataset.boardAreaMarkers || "[]");
            if (Array.isArray(boardItems)) {
                mapMeasureController.applyMeasureSnapshot({
                    scene_id: canvas.dataset.sceneId,
                    board_area_markers: boardItems,
                });
            }
        } catch {  }
    });
    mapLayerMode.bindEvents();
    const mapRenderLoop = window.GravewrightMapRenderLoop.createRenderLoop({
        boardRenderer,
        effectiveIsGm,
        getActiveDrag: () => mapTokenDrag.active(),
        getGhostsForScene: (sceneId) => mapAddToScene.ghostsForScene(sceneId),
        hoveredIdFor: (canvas) => mapSelection.hoveredId(canvas),
        measureRender: (canvas) => renderMeasureOverlay(canvas),
        requestManifest: ensureManifest,
        runtimeFor,
        sceneDataFor,
        selectedIdsFor: (canvas) => [...selectedSet(canvas)],
        stateFor,
        theme: BOARD_THEME,
        tokenStoreFor,
        viewportUpdate: scheduleViewportUpdate,
    });

    function sceneDataFor(canvas) {
        return mapScene.sceneDataFor(canvas);
    }

    function clampZoom(raw, fallback) {
        return mapScene.clampZoom(raw, fallback);
    }

    function viewportSizeFor(canvas) {
        return mapScene.viewportSizeFor(canvas);
    }



    function runtimeFor(canvas) {
        return mapStreaming.runtimeFor(canvas);
    }

    function visibleTileRange(scene, state, canvasW, canvasH) {
        return mapStreaming.visibleTileRange(scene, state, canvasW, canvasH);
    }

    function visibleChunkRange(canvas, scene, state) {
        return mapStreaming.visibleChunkRange(canvas, scene, state);
    }




    function viewportFocusChunk(canvas, scene, state) {
        return mapStreaming.viewportFocusChunk(canvas, scene, state);
    }

    function chunkKey(layerId, cx, cy) {
        return mapStreaming.chunkKey(layerId, cx, cy);
    }

    function buildTileTables(manifest) {
        return mapStreaming.buildTileTables(manifest);
    }

    function ensureManifest(canvas, scene) {
        return mapStreaming.ensureManifest(canvas, scene);
    }

    function layerIdsFor(canvas, scene) {
        return mapStreaming.layerIdsFor(canvas, scene);
    }

    function viewportKeyFor(scene, layerIds, range) {
        return mapStreaming.viewportKeyFor(scene, layerIds, range);
    }

    function knownChunksObject(runtime) {
        return mapStreaming.knownChunksObject(runtime);
    }

    function clearChunkStreamRetry(runtime) {
        mapStreaming.clearChunkStreamRetry(runtime);
    }

    function missingVisibleChunkKeys(runtime, layerIds, range) {
        return mapStreaming.missingVisibleChunkKeys(runtime, layerIds, range);
    }

    function scheduleChunkStreamRetry(canvas, scene, layerIds, range) {
        mapStreaming.scheduleChunkStreamRetry(canvas, scene, layerIds, range);
    }

    function scheduleViewportUpdate(canvas, immediate = false) {
        mapStreaming.scheduleViewportUpdate(canvas, immediate);
    }

    function sendViewportUpdate(canvas, force = false) {
        return mapStreaming.sendViewportUpdate(canvas, force);
    }

    function sendSessionResume(canvas) {
        return mapStreaming.sendSessionResume(canvas);
    }

    function decodeChunkRefsView(payload, start, length, encoding) {
        return mapStreaming.decodeChunkRefsView(payload, start, length, encoding);
    }

    function decodeChunkBatchFrame(buffer) {
        return mapStreaming.decodeChunkBatchFrame(buffer);
    }

    function applyChunkBatchFrame(buffer) {
        mapStreaming.applyChunkBatchFrame(buffer);
    }

    function handleChunkUpdated(payload) {
        mapStreaming.handleChunkUpdated(payload);
    }

    function handleSessionResumed(payload) {
        mapStreaming.handleSessionResumed(payload);
    }

    function handleViewportReady(payload) {
        mapStreaming.handleViewportReady(payload);
    }

    function resetSceneRuntime(canvas) {
        mapStreaming.resetSceneRuntime(canvas);
    }

    function syncCanvasScene(canvas, scenePayload) {
        mapStreaming.syncCanvasScene(canvas, scenePayload);
    }

    function handleSceneActivated(payload) {
        mapStreaming.handleSceneActivated(payload);
    }

    function handleSceneUpdated(payload) {
        mapStreaming.handleSceneUpdated(payload);
    }



    function isGmForCanvas(canvas) {



        return canvas.closest(".room-workspace")?.dataset.isGm === "true";
    }

    function effectiveIsGm(canvas) {
        return mapLayerMode.effectiveIsGm(canvas);
    }

    function currentUserId() {
        return document.body.dataset.currentUserId || "";
    }



    function canControlToken(token, canvas) {
        const layer = token?.hidden ? "gm" : "game";
        const roomId = canvas?.dataset.roomId || "";
        return !window.GravewrightTools?.isLayerLocked?.(layer, roomId)
            && mapTokens.canControl(token, canvas);
    }

    function tokenStoreFor(canvas) {
        return mapTokens.storeFor(canvas);
    }

    function tokenAtPoint(canvas, screenX, screenY) {
        return mapTokens.atPoint(canvas, screenX, screenY);
    }

    function screenToWorldXY(screenX, screenY, state) {
        return window.GravewrightMapDrag.screenToWorldXY(screenX, screenY, state);
    }

    function clampGridPosition(gridX, gridY, scene, token) {
        return window.GravewrightMapDrag.clampGridPosition(gridX, gridY, scene, token);
    }

    function snapDragToGrid(worldX, worldY, scene, token, snap = true) {
        return window.GravewrightMapDrag.snapDragToGrid(worldX, worldY, scene, token, snap);
    }

    function selectedSet(canvas) {
        return mapSelection.selectedSet(canvas);
    }

    function isSelected(canvas, tokenId) {
        return mapSelection.isSelected(canvas, tokenId);
    }



    function selectToken(canvas, tokenId, { additive = false } = {}) {
        mapSelection.select(canvas, tokenId, { additive });
    }

    function setSelection(canvas, ids, { additive = false } = {}) {
        mapSelection.setSelection(canvas, ids, { additive });
    }

    function clearSelection(canvas) {
        mapSelection.clear(canvas);
    }


    function selectedMeasureIdFor(canvas) {
        return mapMeasureController.selectedMeasureIdFor(canvas);
    }

    function setSelectedMeasure(canvas, measureId) {
        mapMeasureController.setSelectedMeasure(canvas, measureId);
    }

    function upsertMeasureLocal(canvas, measure) {
        mapMeasureController.upsertMeasureLocal(canvas, measure);
    }

    function broadcastAreaMarkerUpsert(canvas, marker) {
        mapMeasureController.broadcastAreaMarkerUpsert(canvas, marker);
    }

    function broadcastDrawUpsert(canvas, drawing) {
        mapMeasureController.broadcastDrawUpsert(canvas, drawing);
    }

    function renderMeasureOverlay(canvas = activeCanvas()) {
        mapMeasureController.renderMeasureOverlay(canvas);
    }

    function startMeasure(canvas, event) {
        return mapMeasureController.startMeasure(canvas, event);
    }

    function startDrawTool(canvas, event) {
        return mapMeasureController.startDrawTool(canvas, event);
    }

    function updateMeasure(event) {
        return mapMeasureController.updateMeasure(event);
    }

    function updateFreehand(event) {
        return mapMeasureController.updateFreehand(event);
    }

    function stopMeasure(event) {
        mapMeasureController.stopMeasure(event);
    }

    function stopFreehand(event) {
        mapMeasureController.stopFreehand(event);
    }

    function textFontSizeFor(scene) {
        return mapMeasureController.textFontSizeFor(scene);
    }

    function applyActiveLayer(saved, canvas) {
        return mapMeasureController.applyActiveLayer(saved, canvas);
    }

    function clearMeasures(canvas = activeCanvas(), options = {}) {
        mapMeasureController.clearMeasures(canvas, options);
    }

    function deleteSelectedMeasure(canvas = activeCanvas(), options = {}) {
        return mapMeasureController.deleteSelectedMeasure(canvas, options);
    }

    function measureAtPointForContext(canvas, event) {
        return mapMeasureController.measureAtPointForContext(canvas, event);
    }

    function applyRemoteAreaMarkerUpsert(payload) {
        mapMeasureController.applyRemoteAreaMarkerUpsert(payload);
    }

    function applyRemoteAreaMarkerDelete(payload) {
        mapMeasureController.applyRemoteAreaMarkerDelete(payload);
    }

    function applyRemoteAreaMarkerClear(payload) {
        mapMeasureController.applyRemoteAreaMarkerClear(payload);
    }

    function applyRemoteMeasureFlash(payload) {
        mapMeasureController.applyRemoteMeasureFlash(payload);
    }

    function applyRemoteMeasureClear(payload) {
        mapMeasureController.applyRemoteMeasureClear(payload);
    }

    function applyRemoteMeasureDelete(payload) {
        mapMeasureController.applyRemoteMeasureDelete(payload);
    }

    function applyRemoteDrawUpsert(payload) {
        mapMeasureController.applyRemoteDrawUpsert(payload);
    }

    function applyRemoteDrawClear(payload) {
        mapMeasureController.applyRemoteDrawClear(payload);
    }

    function applyMeasureSnapshot(payload) {
        mapMeasureController.applyMeasureSnapshot(payload);
    }

    function loadTokensForScene(canvas, scene, force = false) {
        mapTokenEvents.loadForScene(canvas, scene, force);
    }



    function forCanvasesWithScene(sceneId, fn) {
        mapTokenEvents.forCanvasesWithScene(sceneId, fn);
    }

    function handleTokensSnapshot(payload) {
        mapTokenEvents.handleSnapshot(payload);
    }

    function reloadTokensForRoom(roomId) {
        mapTokenEvents.reloadForRoom(roomId);
    }

    function handleTokensCreated(payload) {
        mapTokenEvents.handleCreated(payload);
    }

    function handleTokensMoved(payload) {
        mapTokenEvents.handleMoved(payload);
    }

    function handleTokensUpdated(payload) {
        mapTokenEvents.handleUpdated(payload);
    }

    function handleTokensDeleted(payload) {
        mapTokenEvents.handleDeleted(payload);
    }

    function handleTokensVisibilityChanged(payload) {
        mapTokenEvents.handleVisibilityChanged(payload);
    }

    function handleTokensConditionsUpdated(payload) {
        mapTokenEvents.handleConditionsUpdated(payload);
    }



    function screenToGridXY(screenX, screenY, state, scene) {
        return window.GravewrightMapDrag.screenToGridXY(screenX, screenY, state, scene);
    }

    function startAddToScene({ actorIds, sceneId, roomId }) {
        mapAddToScene.start({ actorIds, sceneId, roomId });
    }

    function stopAddToScene() {
        mapAddToScene.stop();
    }

    function updateAddToScenePreview(screenX, screenY) {
        mapAddToScene.updatePreview(screenX, screenY);
    }

    function confirmAddToScene() {
        mapAddToScene.confirm();
    }



    function cameraStorageKey(sceneId) {
        const userId = document.body.dataset.currentUserId || "anon";
        return `${CAMERA_STORAGE_PREFIX}${userId}.${sceneId}`;
    }

    function sceneStartCamera(scene) {
        return {
            worldX: scene.startWorldX,
            worldY: scene.startWorldY,
            zoom: scene.startZoom,
        };
    }

    function cameraIntersectsScene(canvas, scene, camera) {
        const viewport = viewportSizeFor(canvas);
        const zoom = clampZoom(camera.zoom, 1);
        const halfWorldW = viewport.width / zoom / 2;
        const halfWorldH = viewport.height / zoom / 2;
        return camera.worldX + halfWorldW > 0
            && camera.worldY + halfWorldH > 0
            && camera.worldX - halfWorldW < scene.width
            && camera.worldY - halfWorldH < scene.height;
    }

    function readStoredCamera(canvas, scene) {
        try {
            const camera = JSON.parse(window.localStorage.getItem(cameraStorageKey(scene.id)) || "null");
            if (!camera || typeof camera !== "object") return null;
            if (camera.version !== CAMERA_STORAGE_VERSION) return null;
            if (!Number.isFinite(camera.worldX) || !Number.isFinite(camera.worldY)) return null;
            const restored = {
                worldX: camera.worldX,
                worldY: camera.worldY,
                zoom: clampZoom(camera.zoom, 1),
            };
            return cameraIntersectsScene(canvas, scene, restored) ? restored : null;
        } catch {
            return null;
        }
    }

    function cameraFromState(canvas) {
        return mapCamera.cameraFromState(canvas);
    }

    function applyCameraToState(canvas, camera, state = stateFor(canvas)) {
        mapCamera.applyToState(canvas, camera, state);
    }

    function initialCameraFor(canvas) {
        return mapCamera.initialFor(canvas);
    }

    function saveCameraNow(canvas) {
        mapCamera.saveNow(canvas);
    }

    function scheduleCameraSave(canvas) {
        mapCamera.scheduleSave(canvas);
    }

    function stateFor(canvas) {
        return mapCamera.stateFor(canvas);
    }

    function activeCanvas() {
        return mapCamera.activeCanvas();
    }

    function activeCameraForScene(sceneId) {
        return mapCamera.activeForScene(sceneId);
    }

    function screenFromWorld(value, offset, zoom) {
        return value * zoom + offset;
    }

    function focusWorldPoint(canvas, worldX, worldY) {
        mapCamera.focusWorldPoint(canvas, worldX, worldY);
    }

    function renderBoardPing(canvas, worldX, worldY, variant = "ping") {
        mapBoardPing.render(canvas, worldX, worldY, variant);
    }

    function handleBoardPing(payload) {
        mapBoardPing.handle(payload);
    }

    function cancelPendingBoardPing(pointerId = null) {
        mapBoardPing.cancel(pointerId);
    }

    function sendBoardPing(ping) {
        mapBoardPing.send(ping);
    }

    function scheduleBoardPing(canvas, event) {
        mapBoardPing.schedule(canvas, event);
    }

    function updatePendingBoardPing(event) {
        mapBoardPing.update(event);
    }






    function drawGrid(canvas) {
        mapRenderLoop.drawGrid(canvas);
    }

    function drawAll() {
        mapRenderLoop.drawAll();
    }

    function requestDrawAll() {
        mapRenderLoop.requestDrawAll();
    }

    function markDirty(canvas, flags = "all") {
        mapRenderLoop.markDirty(canvas, flags);
    }



    document.addEventListener("pointerdown", (event) => {
        if (event.target.closest?.("[data-scene-object-id]")) return;
        const canvas = event.target.closest("[data-map-canvas]")
            || event.target.closest("[data-map-viewport]")?.querySelector("[data-map-canvas]");
        if (!canvas) return;

        if (window.GravewrightTools?.dispatchPackagePointer?.("down", canvas, event)) {
            event.preventDefault();
            return;
        }


        if (mapAddToScene.isActive() && event.button === 0) {
            updateAddToScenePreview(event.clientX, event.clientY);
            confirmAddToScene();
            return;
        }


        // Na camada artistica o token nao e alvo: ele nem seleciona ali, entao
        // deixar que ele engula o ponteiro so tiraria a marquee e o pan do mestre.
        const artisticLayer = () => (window.GravewrightTools?.activeLayer || "game") === "composition";

        if (event.button === 2) {
            const hit = artisticLayer() ? null : tokenAtPoint(canvas, event.clientX, event.clientY);
            if (hit) return;
            if (isGmForCanvas(canvas) && measureAtPointForContext(canvas, event)) return;
            mapPan.start(canvas, event);
            return;
        }


        if (event.button === 0) {
            if (window.GravewrightFog?.isActive?.()) return;
            const activeTool = window.GravewrightTools?.activeTool ?? "select";
            if (activeTool === "draw") {
                event.preventDefault();
                startDrawTool(canvas, event);
                return;
            }
            if (activeTool === "ruler" || activeTool === "shape") {
                event.preventDefault();
                startMeasure(canvas, event);
                return;
            }
            scheduleBoardPing(canvas, event);
            if (activeTool !== "select") return;

            const additive = event.shiftKey;
            const hit = artisticLayer() ? null : tokenAtPoint(canvas, event.clientX, event.clientY);
            if (hit) {
                mapTokenDrag.start(canvas, event, hit, { additive });
            } else if (!artisticLayer() && mapMeasureController.startShapeSelection(canvas, event)) {
                event.preventDefault();
            } else {

                mapMarquee.start(canvas, event, { additive });
            }
        }
    });

    window.GravewrightMapTokenDomEvents.bindTokenDomEvents({
        activeCanvas,
        canControlToken,
        isGmForCanvas,
        isSelected,
        markDirty,
        sceneDataFor,
        selectToken,
        selectedSet,
        selection: mapSelection,
        tokenAtPoint,
        tokenStoreFor,
    });

    document.addEventListener("contextmenu", (event) => {
        const canvas = event.target.closest("[data-map-canvas]")
            || event.target.closest("[data-map-viewport]")?.querySelector("[data-map-canvas]");
        if (!canvas) return;
        if (tokenAtPoint(canvas, event.clientX, event.clientY)) return;
        if (!isGmForCanvas(canvas)) return;

        const measure = measureAtPointForContext(canvas, event);
        const scene = sceneDataFor(canvas);
        event.preventDefault();
        if (!measure) return;
        document.dispatchEvent(new CustomEvent("vtt:measure-contextmenu", {
            detail: {
                measure,
                x: event.clientX,
                y: event.clientY,
                sceneId: scene?.id || "",
                roomId: canvas.dataset.roomId || "",
                isGm: true,
            },
        }));
    });

    const ACTOR_DROP_MIME = "application/x-gravewright-actors+json";
    const CARD_DROP_MIME = "application/x-gravewright-card+json";
    const ASSET_DROP_MIME = "application/x-gravewright-asset+json";

    function canvasFromDragEvent(event) {
        const target = event.target;
        if (!target || typeof target.closest !== "function") return null;
        return target.closest("[data-map-canvas]")
            || target.closest("[data-map-viewport]")?.querySelector("[data-map-canvas]")
            || null;
    }

    function imageFilesFrom(dataTransfer) {
        return Array.from(dataTransfer?.files || []).filter((file) => (file.type || "").startsWith("image/"));
    }



    function isImageAssetDrop(raw) {
        try {
            return (JSON.parse(raw)?.kind || "image") === "image";
        } catch {
            return false;
        }
    }

    function handleCardDrop(canvas, raw, clientX, clientY) {
        let parsed = null;
        try {
            parsed = JSON.parse(raw);
        } catch {
            return;
        }
        const cardId = parsed?.card_id;
        const sceneId = canvas.dataset.sceneId || "";
        if (!cardId || !sceneId) return;


        window.GravewrightCards?.placeCardAtScene?.(canvas, parsed, clientX, clientY);
    }

    function actorDropPayload(event) {
        try {
            const raw = event.dataTransfer?.getData(ACTOR_DROP_MIME);
            if (!raw) return window.GravewrightActorsInternals?.currentTableDropPayload?.() || null;
            const parsed = JSON.parse(raw);
            if (!Array.isArray(parsed.actorIds) || !parsed.actorIds.length) return null;
            return {
                actorIds: parsed.actorIds.filter((id) => typeof id === "string" && id),
                roomId: typeof parsed.roomId === "string" ? parsed.roomId : "",
            };
        } catch {
            return null;
        }
    }

    document.addEventListener("dragover", (event) => {
        const canvas = canvasFromDragEvent(event);
        if (!canvas) return;
        const dt = event.dataTransfer;
        const types = Array.from(dt?.types || []);


        if (types.includes(CARD_DROP_MIME)) {
            event.preventDefault();
            dt.dropEffect = "move";
            return;
        }


        if (types.includes(ASSET_DROP_MIME)) {
            event.preventDefault();
            dt.dropEffect = "copy";
            return;
        }


        if (window.GravewrightSceneImages?.hasImageFiles?.(dt)) {
            event.preventDefault();
            dt.dropEffect = "copy";
            return;
        }


        if (!isGmForCanvas(canvas)) return;
        if (!types.includes(ACTOR_DROP_MIME) && !window.GravewrightActorsInternals?.currentTableDropPayload?.()) return;
        event.preventDefault();
        dt.dropEffect = "copy";
    });

    document.addEventListener("drop", (event) => {
        const canvas = canvasFromDragEvent(event);
        if (!canvas) return;
        const dt = event.dataTransfer;


        const cardRaw = dt?.getData?.(CARD_DROP_MIME);
        if (cardRaw) {
            event.preventDefault();
            handleCardDrop(canvas, cardRaw, event.clientX, event.clientY);
            return;
        }


        // O payload proprio vem antes dos arquivos: arrastar um cartao da
        // biblioteca pela miniatura faz o navegador anexar a imagem tambem como
        // arquivo, e tratar isso como upload criaria um asset novo em vez de
        // reusar o que ja esta na biblioteca.
        const assetRaw = dt?.getData?.(ASSET_DROP_MIME);
        if (assetRaw) {
            event.preventDefault();


            if (!isImageAssetDrop(assetRaw)) return;
            window.GravewrightSceneImages?.placeLibraryAssetAt?.(canvas, assetRaw, event.clientX, event.clientY);
            return;
        }


        const imageFiles = imageFilesFrom(dt);
        if (imageFiles.length && window.GravewrightSceneImages?.uploadFilesAt && canvas.dataset.sceneId) {
            event.preventDefault();

            window.GravewrightSceneImages.uploadFilesAt(canvas, imageFiles, event.clientX, event.clientY);
            return;
        }


        if (!isGmForCanvas(canvas)) return;
        const payload = actorDropPayload(event);
        if (!payload?.actorIds.length) return;
        const scene = sceneDataFor(canvas);
        if (!scene) return;
        const roomId = payload.roomId || canvas.dataset.roomId || "";
        if (roomId && roomId !== canvas.dataset.roomId) return;
        event.preventDefault();
        mapAddToScene.placeAt(canvas, {
            actorIds: payload.actorIds,
            sceneId: scene.id,
            roomId: canvas.dataset.roomId || roomId,
            screenX: event.clientX,
            screenY: event.clientY,
        });
    });
    document.addEventListener("dragleave", (event) => {
        const canvas = canvasFromDragEvent(event);
        if (!canvas) return;
        const related = event.relatedTarget;
        if (related && typeof related.closest === "function" && related.closest("[data-map-viewport]")) return;
        window.GravewrightSceneImages?.clearPreview?.(canvas);
    });
    document.addEventListener("dragend", () => {
        window.GravewrightSceneImages?.clearPreview?.();
    });

    document.addEventListener("pointermove", (event) => {
        const packageCanvas = event.target.closest?.("[data-map-canvas]")
            || event.target.closest?.("[data-map-viewport]")?.querySelector("[data-map-canvas]")
            || window.GravewrightMap?.activeCanvas?.();
        if (window.GravewrightTools?.dispatchPackagePointer?.("move", packageCanvas, event)) return;
        updatePendingBoardPing(event);

        if (mapAddToScene.isActive()) {
            updateAddToScenePreview(event.clientX, event.clientY);
        }

        if (updateFreehand(event)) {
            return;
        }

        if (updateMeasure(event)) {
            return;
        }

        if (mapMarquee.update(event)) {
            return;
        }

        if (mapTokenDrag.update(event)) {
            return;
        }

        mapPan.update(event);
    });

    document.addEventListener("pointerup", (e) => {
        const packageCanvas = window.GravewrightMap?.activeCanvas?.();
        if (window.GravewrightTools?.dispatchPackagePointer?.("up", packageCanvas, e)) return;
        cancelPendingBoardPing(e.pointerId);
        stopFreehand(e);
        stopMeasure(e);
        mapPan.stop(e);
        mapTokenDrag.stop(e);
        mapMarquee.stop(e);
    });
    document.addEventListener("pointercancel", (e) => {
        const packageCanvas = window.GravewrightMap?.activeCanvas?.();
        if (window.GravewrightTools?.dispatchPackagePointer?.("cancel", packageCanvas, e)) return;
        cancelPendingBoardPing(e.pointerId);
        mapMeasureController.cancelPointer(e);
        mapPan.stop(e);
        mapTokenDrag.cancel(e);
        mapMarquee.cancel(e);
    });

    const mapTokenSteps = window.GravewrightMapTokenSteps.createTokenSteps({
        canControlToken,
        clampGridPosition,
        effectiveIsGm,
        history: boardHistory,
        markDirty,
        sceneDataFor,
        selectedSet,
        tokenStoreFor,
    });

    window.GravewrightMapKeyboardEvents.bindKeyboardEvents({
        activeCanvas,
        boardPing: mapBoardPing,
        tokenSteps: mapTokenSteps,
        clearMeasures,
        deleteSelectedMeasure,
        getMeasureController: () => mapMeasureController,
        history: boardHistory,
        mapAddToScene,
        selectedSet,
        stopAddToScene,
        tokenDelete: mapTokenDelete,
        tokenClipboard: mapTokenClipboard,
    });

    window.GravewrightMapZoom.bindZoomWheel({
        clampZoom,
        markDirty,
        rotateSelectedMeasureByWheel: (canvas, deltaY) => mapMeasureController.rotateSelectedMeasureByWheel(canvas, deltaY),
        scheduleCameraSave,
        scheduleViewportUpdate,
        stateFor,
    });

    document.addEventListener("change", (event) => {
        if (!event.target.matches('input[name="selected-room"]')) {
            return;
        }

        mapMeasureEditors.cancelTextEditor();
        requestDrawAll();
    });

    document.addEventListener("submit", (event) => {
        const form = event.target.closest("[data-scene-start-form]");
        if (!form) return;

        const sceneId = form.querySelector('[name="scene_id"]')?.value || "";
        const camera = activeCameraForScene(sceneId);
        if (!camera) {
            event.preventDefault();
            return;
        }

        form.querySelector('[name="start_world_x"]').value = String(camera.worldX);
        form.querySelector('[name="start_world_y"]').value = String(camera.worldY);
        form.querySelector('[name="start_zoom"]').value = String(camera.zoom);
    }, true);

    window.GravewrightMapRealtimeEvents.bindRealtimeEvents({
        activeCanvas,
        applyChunkBatchFrame,
        applyMeasureSnapshot,
        applyRemoteAreaMarkerClear,
        applyRemoteAreaMarkerDelete,
        applyRemoteAreaMarkerUpsert,
        applyRemoteDrawClear,
        applyRemoteDrawUpsert,
        applyRemoteMeasureClear,
        applyRemoteMeasureDelete,
        applyRemoteMeasureFlash,
        handleChunkUpdated,
        handleSceneActivated,
        handleSceneUpdated,
        handleSessionResumed,
        handleViewportReady,
        updateSceneInfoCache: mapStreaming.updateSceneInfoCache,
        handleGmPrefetchHint: mapStreaming.handleGmPrefetchHint,
        handleTokensConditionsUpdated,
        handleTokensCreated,
        handleTokensDeleted,
        handleTokensMoved,
        handleTokensSnapshot,
        handleTokensUpdated,
        handleTokensVisibilityChanged,
        loadTokensForScene,
        reloadTokensForRoom,
        sceneDataFor,
        scheduleViewportUpdate,
        sendSessionResume,
    });

    window.addEventListener("resize", () => {
        drawAll();
        const canvas = activeCanvas();
        if (canvas) scheduleViewportUpdate(canvas, true);
    });
    requestDrawAll();

    function centerOnToken(tokenId) {
        const canvas = activeCanvas();
        if (!canvas) return;
        const scene = sceneDataFor(canvas);
        const state = stateFor(canvas);
        if (!scene) return;
        const token = tokenStoreFor(canvas).get(tokenId);
        if (!token) return;
        const s = scene.scaledTileSize;
        const viewport = viewportSizeFor(canvas);
        state.offsetX = viewport.width / 2 - ((scene.gridOffsetX || 0) + (token.grid_x + 0.5) * s) * state.zoom;
        state.offsetY = viewport.height / 2 - ((scene.gridOffsetY || 0) + (token.grid_y + 0.5) * s) * state.zoom;
        scheduleViewportUpdate(canvas);
        saveCameraNow(canvas);
        markDirty(canvas);
    }

    function worldFromScreen(canvas, screenX, screenY) {
        if (!canvas) return null;
        const state = stateFor(canvas);
        return {
            worldX: (screenX - state.offsetX) / state.zoom,
            worldY: (screenY - state.offsetY) / state.zoom,
            zoom: state.zoom,
        };
    }

    const mapDebug = window.GravewrightMapDebug.createMapDebug({
        activeCanvas,
        sceneDataFor,
        streaming: () => mapStreaming,
        cameraFromState,
        viewportSizeFor,
        boardRenderer,
    });

    function debugSnapshot() {
        return mapDebug.snapshot();
    }

    function deleteTokens(tokenIds) {
        mapTokenDelete.deleteTokens(tokenIds);
    }

    function removeTokensMatching(sceneId, snapshots) {
        const canvas = Array.from(document.querySelectorAll("[data-map-canvas]"))
            .find((candidate) => candidate.dataset.sceneId === sceneId) || activeCanvas();
        if (!canvas || !Array.isArray(snapshots)) return false;
        const scene = sceneDataFor(canvas);
        if (!scene || scene.id !== sceneId) return false;
        const roomId = canvas.dataset.roomId || "";
        const store = tokenStoreFor(canvas);
        const used = new Set();
        snapshots.forEach((snapshot) => {
            const match = [...store.values()].find((token) => {
                if (used.has(token.token_id)) return false;
                return token.actor_id === snapshot.actor_id
                    && token.grid_x === snapshot.grid_x
                    && token.grid_y === snapshot.grid_y;
            });
            if (!match) return;
            used.add(match.token_id);
            if (document.body?.dataset?.streamerMode === "true") {
                store.delete(match.token_id);
                return;
            }
            window.GravewrightRealtime?.sendCommand?.(
                "token.remove_from_scene",
                { scene_id: sceneId, token_id: match.token_id },
                { sceneId, roomId },
            );
        });
        if (used.size > 0 && document.body?.dataset?.streamerMode === "true") {
            drawAll();
        }
        return used.size > 0;
    }

    window.GravewrightMap = {
        redraw: drawAll,
        activeCanvas,
        stateFor,
        sceneDataFor,


        activeTokenDrag: () => mapTokenDrag.active(),
        activeCameraForScene,
        worldFromScreen,
        startPan: (canvas, event) => mapPan.start(canvas, event),
        startAddToScene,
        stopAddToScene,
        centerOnToken,
        deleteTokens,
        removeTokensMatching,
        tokenStoreFor,
        selectTokensInWorldRect: (canvas, rect, opts) => mapMarquee.selectTokensInWorldRect(canvas, rect, opts),
        history: boardHistory,
        historyUndo: () => boardHistory.undo(),
        historyRedo: () => boardHistory.redo(),
        debugSnapshot,
        measurementSnapshot: () => boardRenderer.measurementSnapshot(activeCanvas()),
        benchmarkSetAnimatedTokens: (tokens, sources) => {
            const canvas = activeCanvas();
            const store = canvas ? tokenStoreFor(canvas) : null;
            if (store) {
                store.clear();
                (tokens || []).forEach((token) => store.set(token.token_id, token));
            }
            boardRenderer.benchmarkSetAnimatedTokens?.(tokens, sources);
        },
        scheduleViewportUpdate: (canvas, immediate = true) => scheduleViewportUpdate(canvas || activeCanvas(), immediate),

        viewerIsGm: (canvas) => effectiveIsGm(canvas),
        isPlayerView: () => mapLayerMode.isPlayerView(),
        setPlayerVision: (active) => mapLayerMode.setPlayerVision(active),
    };
})();
