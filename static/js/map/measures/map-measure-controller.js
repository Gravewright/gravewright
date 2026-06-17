(() => {
    const SHAPE_SELECT_KINDS = new Set(["shape"]);
    const DRAW_SELECT_KINDS = new Set(["freehand", "text"]);

    function createMeasureController(deps) {
        let activeFreehand = null;
        let activeMeasure = null;
        let activeMeasureMove = null;

        const {
            activeCanvas,
            activeDrawLayer,
            currentUserId,
            defaultGridSize,
            history,
            isGmForCanvas,
            measures,
            sceneDataFor,
            stateFor,
        } = deps;

        const storeApi = measures.store;
        const geometry = measures.geometry;
        const renderer = measures.renderer;
        const editors = measures.editors;
        const data = measures.data;

        const {
            activeDrawStyle,
            applyOwnerLayer,
            normalizedAreaMarkerText,
            normalizedMarkerStyle,
            normalizedTextDrawing,
        } = data;

        function measureStoreFor(canvas) {
            return storeApi.measureStoreFor(canvas);
        }

        function selectedMeasureIdFor(canvas) {
            return storeApi.selectedIdFor(canvas);
        }

        function renderMeasureOverlay(canvas = activeCanvas()) {
            renderer.renderOverlay(canvas);
        }

        function setSelectedMeasure(canvas, measureId) {
            const next = measureId || null;
            if (selectedMeasureIdFor(canvas) === next) return;
            storeApi.setSelectedId(canvas, next);
            renderMeasureOverlay(canvas);
        }

        function sameMeasureScene(canvas, measure) {
            const scene = sceneDataFor(canvas);
            return scene && measure?.scene_id === scene.id;
        }

        function upsertMeasureLocal(canvas, measure) {
            if (!canvas || !sameMeasureScene(canvas, measure)) return;
            const store = measureStoreFor(canvas);
            const idx = store.findIndex((existing) => existing.id === measure.id);
            if (measure.kind === "text") {
                const next = normalizedTextDrawing(measure);
                if (!next) return;
                if (idx >= 0) store[idx] = next;
                else store.push(next);
                renderMeasureOverlay(canvas);
                return;
            }
            if (measure.kind === "freehand") {
                const next = {
                    id: measure.id,
                    scene_id: measure.scene_id,
                    kind: "freehand",
                    points: Array.isArray(measure.points)
                        ? measure.points.map((point) => ({ worldX: point.worldX, worldY: point.worldY }))
                        : [],
                };
                const style = normalizedMarkerStyle(measure.style);
                if (style) next.style = style;
                applyOwnerLayer(next, measure);
                if (idx >= 0) store[idx] = next;
                else store.push(next);
                renderMeasureOverlay(canvas);
                return;
            }
            const next = {
                id: measure.id,
                scene_id: measure.scene_id,
                shape: measure.shape,
                start: { worldX: measure.start.worldX, worldY: measure.start.worldY },
                end: { worldX: measure.end.worldX, worldY: measure.end.worldY },
            };
            const text = normalizedAreaMarkerText(measure);
            if (text) next.text = text;
            if (typeof measure.preset_id === "string" && measure.preset_id) next.preset_id = measure.preset_id;
            const style = normalizedMarkerStyle(measure.style);
            if (style) next.style = style;
            applyOwnerLayer(next, measure);
            if (idx >= 0) store[idx] = next;
            else store.push(next);
            renderMeasureOverlay(canvas);
        }

        function deleteMeasureLocal(canvas, measureId) {
            const store = measureStoreFor(canvas);
            const idx = store.findIndex((measure) => measure.id === measureId);
            if (idx >= 0) store.splice(idx, 1);
            if (selectedMeasureIdFor(canvas) === measureId) storeApi.clearSelectedId(canvas);
            renderMeasureOverlay(canvas);
        }

        function streamerLocalMode() {
            return document.body?.dataset?.streamerMode === "true";
        }

        function applyLocalMeasureCommand(canvas, command, payload) {
            if (command === "board.area_marker.upsert") {
                upsertMeasureLocal(canvas, payload.marker);
                return true;
            }
            if (command === "board.area_marker.delete") {
                deleteMeasureLocal(canvas, payload.marker_id);
                return true;
            }
            if (command === "board.area_marker.clear") {
                const store = measureStoreFor(canvas);
                for (let i = store.length - 1; i >= 0; i -= 1) {
                    const item = store[i];
                    if (item.kind !== "freehand" && item.kind !== "text") store.splice(i, 1);
                }
                storeApi.clearSelectedId(canvas);
                renderMeasureOverlay(canvas);
                return true;
            }
            if (command === "board.measure.flash") {
                flashMeasureLocal(canvas, payload.measure, payload.ttl_ms);
                return true;
            }
            if (command === "board.measure.delete") {
                deleteMeasureFlashLocal(canvas, payload.measure_id);
                return true;
            }
            if (command === "board.measure.clear") {
                clearMeasureFlashes(canvas);
                return true;
            }
            if (command === "board.draw.upsert") {
                upsertMeasureLocal(canvas, payload.drawing);
                return true;
            }
            if (command === "board.draw.clear") {
                const store = measureStoreFor(canvas);
                for (let i = store.length - 1; i >= 0; i -= 1) {
                    const item = store[i];
                    if (item.kind === "freehand" || item.kind === "text") store.splice(i, 1);
                }
                storeApi.clearSelectedId(canvas);
                renderMeasureOverlay(canvas);
                return true;
            }
            return false;
        }

        function sendMeasureCommand(canvas, command, payload) {
            const scene = sceneDataFor(canvas);
            if (!scene) return;
            if (streamerLocalMode() && applyLocalMeasureCommand(canvas, command, payload)) {
                return;
            }
            window.GravewrightRealtime?.sendCommand(
                command,
                payload,
                { sceneId: scene.id, roomId: canvas.dataset.roomId || "" },
            );
        }

        function cloneMeasure(measure) {
            return measure ? JSON.parse(JSON.stringify(measure)) : null;
        }

        function broadcastMeasureUpsert(canvas, measure) {
            if (measure?.kind === "freehand" || measure?.kind === "text") broadcastDrawUpsert(canvas, measure);
            else if (measure) broadcastAreaMarkerUpsert(canvas, measure);
        }

        function broadcastMeasureDelete(canvas, measureId) {
            broadcastAreaMarkerDelete(canvas, measureId);
        }

        function pushMeasureUpsertHistory(canvas, measure) {
            const snapshot = cloneMeasure(measure);
            if (!snapshot) return;
            history?.push?.({
                undo() {
                    broadcastMeasureDelete(canvas, snapshot.id);
                },
                redo() {
                    broadcastMeasureUpsert(canvas, snapshot);
                },
            });
        }

        function pushMeasureChangeHistory(canvas, before, after) {
            const oldSnapshot = cloneMeasure(before);
            const newSnapshot = cloneMeasure(after);
            if (!oldSnapshot || !newSnapshot) return;
            history?.push?.({
                undo() {
                    broadcastMeasureUpsert(canvas, oldSnapshot);
                },
                redo() {
                    broadcastMeasureUpsert(canvas, newSnapshot);
                },
            });
        }

        function pushMeasureDeleteHistory(canvas, measure) {
            const snapshot = cloneMeasure(measure);
            if (!snapshot) return;
            history?.push?.({
                undo() {
                    broadcastMeasureUpsert(canvas, snapshot);
                },
                redo() {
                    broadcastMeasureDelete(canvas, snapshot.id);
                },
            });
        }

        function pushMeasureFlashHistory(canvas, measure, ttlMs) {
            const snapshot = cloneMeasure(measure);
            if (!snapshot) return;
            history?.push?.({
                undo() {
                    broadcastMeasureFlashDelete(canvas, snapshot.id);
                },
                redo() {
                    broadcastMeasureFlash(canvas, snapshot, ttlMs);
                },
            });
        }

        function broadcastAreaMarkerUpsert(canvas, marker) {
            sendMeasureCommand(canvas, "board.area_marker.upsert", { marker });
        }

        function broadcastAreaMarkerDelete(canvas, markerId) {
            const scene = sceneDataFor(canvas);
            if (!scene) return;
            sendMeasureCommand(canvas, "board.area_marker.delete", {
                scene_id: scene.id,
                marker_id: markerId,
            });
        }

        function broadcastAreaMarkerClear(canvas) {
            const scene = sceneDataFor(canvas);
            if (scene) sendMeasureCommand(canvas, "board.area_marker.clear", { scene_id: scene.id });
        }

        function broadcastMeasureFlash(canvas, measure, ttlMs) {
            sendMeasureCommand(canvas, "board.measure.flash", { measure, ttl_ms: ttlMs });
        }

        function broadcastMeasureFlashDelete(canvas, measureId) {
            const scene = sceneDataFor(canvas);
            if (scene) sendMeasureCommand(canvas, "board.measure.delete", { scene_id: scene.id, measure_id: measureId });
        }

        function broadcastMeasureClear(canvas) {
            const scene = sceneDataFor(canvas);
            if (scene) sendMeasureCommand(canvas, "board.measure.clear", { scene_id: scene.id });
        }

        function broadcastDrawUpsert(canvas, drawing) {
            sendMeasureCommand(canvas, "board.draw.upsert", { drawing });
        }

        function broadcastDrawClear(canvas) {
            const scene = sceneDataFor(canvas);
            if (scene) sendMeasureCommand(canvas, "board.draw.clear", { scene_id: scene.id });
        }

        function applyActiveLayer(saved, canvas) {
            if (isGmForCanvas(canvas) && activeDrawLayer() === "gm") saved.layer = "gm";
            return saved;
        }

        function canEditDrawing(measure, canvas) {
            if (isGmForCanvas(canvas)) return true;
            if (measure?.kind !== "freehand" && measure?.kind !== "text") return true;
            return !measure.owner_id || measure.owner_id === currentUserId();
        }

        function startMeasure(canvas, event) {
            const activeTool = window.GravewrightTools?.activeTool ?? canvas.dataset.activeTool ?? "select";
            const shape = window.GravewrightTools?.activeSubTool || canvas.dataset.activeSubtool || "line";
            if (activeTool === "shape" && shape === "select") return startMeasureMove(canvas, event, SHAPE_SELECT_KINDS);
            if (activeTool !== "shape" && activeTool !== "ruler") return false;
            const start = geometry.measurePointFromEvent(canvas, event);
            if (!start) return false;
            activeMeasure = {
                canvas,
                pointerId: event.pointerId,
                sourceTool: activeTool,
                shape: ["line", "circle", "square", "cone"].includes(shape) ? shape : "line",
                start,
                end: start,
                moved: false,
            };
            canvas.setPointerCapture(event.pointerId);
            renderMeasureOverlay(canvas);
            return true;
        }

        function startFreehand(canvas, event) {
            const start = geometry.rawMeasurePointFromEvent(canvas, event);
            if (!start) return false;
            activeFreehand = {
                canvas,
                pointerId: event.pointerId,
                kind: "freehand",
                points: [start],
                style: activeDrawStyle(canvas),
                moved: false,
            };
            canvas.setPointerCapture(event.pointerId);
            renderMeasureOverlay(canvas);
            return true;
        }

        function startMeasureMove(canvas, event, allowedKinds = SHAPE_SELECT_KINDS, predicate = null) {
            const hit = geometry.measureAtPoint(canvas, event, allowedKinds, predicate);
            if (!hit) {
                setSelectedMeasure(canvas, null);
                return false;
            }
            const freeform = hit.kind === "freehand" || hit.kind === "text";
            const startPoint = freeform
                ? geometry.rawMeasurePointFromEvent(canvas, event)
                : geometry.measurePointFromEvent(canvas, event);
            if (!startPoint) return false;
            setSelectedMeasure(canvas, hit.id);
            activeMeasureMove = {
                canvas,
                pointerId: event.pointerId,
                measureId: hit.id,
                startPoint,
                original: JSON.parse(JSON.stringify(hit)),
                snap: !freeform,
                moved: false,
            };
            canvas.setPointerCapture(event.pointerId);
            return true;
        }

        function measureAtPointForContext(canvas, event) {
            const hit = geometry.measureAtPoint(canvas, event, null, (measure) => canEditDrawing(measure, canvas));
            if (!hit) return null;
            setSelectedMeasure(canvas, hit.id);
            return hit;
        }

        function startDrawTool(canvas, event) {
            const sub = window.GravewrightTools?.activeSubTool || canvas.dataset.activeSubtool || "brush";
            if (sub === "select") return startMeasureMove(canvas, event, DRAW_SELECT_KINDS, (m) => canEditDrawing(m, canvas));
            if (sub === "text") return editors.startTextPlacement(canvas, event);
            return startFreehand(canvas, event);
        }

        function updateMeasure(event) {
            if (updateMeasureMove(event)) return true;
            if (!activeMeasure || activeMeasure.pointerId !== event.pointerId) return false;
            const end = geometry.measurePointFromEvent(activeMeasure.canvas, event);
            if (!end) return true;
            activeMeasure.end = end;
            activeMeasure.moved = Math.abs(end.worldX - activeMeasure.start.worldX) > 0
                || Math.abs(end.worldY - activeMeasure.start.worldY) > 0;
            renderMeasureOverlay(activeMeasure.canvas);
            return true;
        }

        function updateFreehand(event) {
            if (!activeFreehand || activeFreehand.pointerId !== event.pointerId) return false;
            const point = geometry.rawMeasurePointFromEvent(activeFreehand.canvas, event);
            if (!point) return true;
            const last = activeFreehand.points[activeFreehand.points.length - 1];
            const dx = point.worldX - last.worldX;
            const dy = point.worldY - last.worldY;
            if (Math.sqrt(dx * dx + dy * dy) < 3 / stateFor(activeFreehand.canvas).zoom) return true;
            activeFreehand.points.push(point);
            if (activeFreehand.points.length > 512) activeFreehand.points.shift();
            activeFreehand.moved = true;
            renderMeasureOverlay(activeFreehand.canvas);
            return true;
        }

        function updateMeasureMove(event) {
            if (!activeMeasureMove || activeMeasureMove.pointerId !== event.pointerId) return false;
            const scene = sceneDataFor(activeMeasureMove.canvas);
            const point = activeMeasureMove.snap
                ? geometry.measurePointFromEvent(activeMeasureMove.canvas, event)
                : geometry.rawMeasurePointFromEvent(activeMeasureMove.canvas, event);
            if (!scene || !point) return true;
            const rawDx = point.worldX - activeMeasureMove.startPoint.worldX;
            const rawDy = point.worldY - activeMeasureMove.startPoint.worldY;
            const { dx, dy } = geometry.clampMeasureDelta(activeMeasureMove.original, rawDx, rawDy, scene);
            activeMeasureMove.moved = Math.abs(dx) > 0 || Math.abs(dy) > 0;
            upsertMeasureLocal(activeMeasureMove.canvas, geometry.translatedMeasure(activeMeasureMove.original, dx, dy));
            return true;
        }

        function stopMeasure(event) {
            if (activeMeasureMove && activeMeasureMove.pointerId === event.pointerId) {
                stopMeasureMove(event);
                return;
            }
            if (!activeMeasure || activeMeasure.pointerId !== event.pointerId) return;
            const measure = activeMeasure;
            activeMeasure = null;
            try {
                measure.canvas.releasePointerCapture(event.pointerId);
            } catch {  }
            if (measure.moved) {
                const scene = sceneDataFor(measure.canvas);
                const saved = {
                    id: storeApi.newMeasureId(),
                    scene_id: scene.id,
                    shape: measure.shape,
                    start: measure.start,
                    end: measure.end,
                };
                if (measure.sourceTool === "ruler") {
                    const ttlMs = storeApi.flashTtlMs(measure.canvas);
                    flashMeasureLocal(measure.canvas, saved, ttlMs);
                    broadcastMeasureFlash(measure.canvas, saved, ttlMs);
                    pushMeasureFlashHistory(measure.canvas, saved, ttlMs);
                } else {
                    const preset = data.areaMarkerPresetFor(measure.canvas, measure.shape);
                    const style = normalizedMarkerStyle(preset?.style);
                    if (preset?.id) saved.preset_id = preset.id;
                    if (style) saved.style = style;
                    applyActiveLayer(saved, measure.canvas);
                    upsertMeasureLocal(measure.canvas, saved);
                    setSelectedMeasure(measure.canvas, saved.id);
                    if (!editors.startAreaMarkerTextEditor(measure.canvas, saved)) {
                        broadcastAreaMarkerUpsert(measure.canvas, saved);
                    }
                    pushMeasureUpsertHistory(measure.canvas, saved);
                }
            }
            renderMeasureOverlay(measure.canvas);
        }

        function stopFreehand(event) {
            if (!activeFreehand || activeFreehand.pointerId !== event.pointerId) return;
            const drawing = activeFreehand;
            activeFreehand = null;
            try {
                drawing.canvas.releasePointerCapture(event.pointerId);
            } catch {  }
            if (drawing.moved && drawing.points.length >= 2) {
                const scene = sceneDataFor(drawing.canvas);
                const saved = {
                    id: storeApi.newMeasureId().replace("measure-", "draw-"),
                    scene_id: scene.id,
                    kind: "freehand",
                    points: drawing.points,
                    style: drawing.style,
                    owner_id: currentUserId(),
                };
                applyActiveLayer(saved, drawing.canvas);
                upsertMeasureLocal(drawing.canvas, saved);
                broadcastDrawUpsert(drawing.canvas, saved);
                pushMeasureUpsertHistory(drawing.canvas, saved);
            }
            renderMeasureOverlay(drawing.canvas);
        }

        function stopMeasureMove(event) {
            const move = activeMeasureMove;
            activeMeasureMove = null;
            try {
                move.canvas.releasePointerCapture(event.pointerId);
            } catch {  }
            if (move.moved) {
                const measure = measureStoreFor(move.canvas).find((item) => item.id === move.measureId);
                broadcastMeasureUpsert(move.canvas, measure);
                if (measure) pushMeasureChangeHistory(move.canvas, move.original, measure);
            }
            renderMeasureOverlay(move.canvas);
        }

        function cancelActiveMeasure() {
            const canvas = activeMeasure?.canvas || activeMeasureMove?.canvas || activeCanvas();
            activeMeasure = null;
            activeMeasureMove = null;
            renderMeasureOverlay(canvas);
        }

        function cancelActiveFreehand() {
            const canvas = activeFreehand?.canvas || activeCanvas();
            activeFreehand = null;
            renderMeasureOverlay(canvas);
        }

        function textFontSizeFor(scene) {
            return Math.max(12, Math.round((scene?.scaledTileSize || defaultGridSize) * 0.4));
        }

        function clearMeasures(canvas = activeCanvas(), { broadcast = true, record = true, tool = "shape" } = {}) {
            if (!canvas) return;
            const before = measureStoreFor(canvas).map(cloneMeasure).filter(Boolean);
            if (tool === "ruler") {
                clearMeasureFlashes(canvas);
            } else if (tool === "draw") {
                const gm = isGmForCanvas(canvas);
                const uid = currentUserId();
                const store = measureStoreFor(canvas);
                for (let i = store.length - 1; i >= 0; i -= 1) {
                    const item = store[i];
                    if (item.kind !== "freehand" && item.kind !== "text") continue;
                    if (gm || !item.owner_id || item.owner_id === uid) store.splice(i, 1);
                }
                if (activeFreehand?.canvas === canvas) activeFreehand = null;
                if (editors.activeTextCanvas() === canvas) editors.cancelTextEditor();
            } else {
                if (editors.activeAreaMarkerCanvas() === canvas) {
                    editors.cancelAreaMarkerTextEditor({ broadcast: false });
                }
                measureStoreFor(canvas).length = 0;
            }
            if (activeMeasure?.canvas === canvas) activeMeasure = null;
            if (activeMeasureMove?.canvas === canvas) activeMeasureMove = null;
            storeApi.clearSelectedId(canvas);
            renderMeasureOverlay(canvas);
            if (broadcast && tool === "ruler") broadcastMeasureClear(canvas);
            if (broadcast && tool === "draw") broadcastDrawClear(canvas);
            if (broadcast && tool !== "ruler" && tool !== "draw") broadcastAreaMarkerClear(canvas);
            if (record && broadcast && tool !== "ruler") {
                const removed = before.filter((measure) => {
                    if (tool === "draw") return measure.kind === "freehand" || measure.kind === "text";
                    return true;
                });
                if (removed.length) {
                    history?.push?.({
                        undo() {
                            removed.forEach((measure) => broadcastMeasureUpsert(canvas, measure));
                        },
                        redo() {
                            clearMeasures(canvas, { broadcast: true, record: false, tool });
                        },
                    });
                }
            }
        }

        function replaceMeasuresSnapshot(canvas, measuresSnapshot) {
            if (!canvas || !Array.isArray(measuresSnapshot)) return;
            const scene = sceneDataFor(canvas);
            if (!scene) return;
            const store = measureStoreFor(canvas);
            store.length = 0;
            measuresSnapshot.forEach((measure) => {
                if (measure?.scene_id === scene.id) upsertMeasureLocal(canvas, measure);
            });
            const selectedId = selectedMeasureIdFor(canvas);
            if (selectedId && !store.some((measure) => measure.id === selectedId)) storeApi.clearSelectedId(canvas);
            renderMeasureOverlay(canvas);
        }

        function deleteSelectedMeasure(canvas = activeCanvas(), { broadcast = true, record = true } = {}) {
            if (!canvas) return false;
            const measureId = selectedMeasureIdFor(canvas);
            if (!measureId) return false;
            const measure = measureStoreFor(canvas).find((item) => item.id === measureId);
            deleteMeasureLocal(canvas, measureId);
            if (broadcast) broadcastAreaMarkerDelete(canvas, measureId);
            if (record && broadcast) pushMeasureDeleteHistory(canvas, measure);
            return true;
        }

        function clearMeasureFlashes(canvas) {
            const timers = storeApi.flashTimerStoreFor(canvas);
            timers.forEach((timer) => clearTimeout(timer));
            timers.clear();
            storeApi.flashStoreFor(canvas).length = 0;
            renderMeasureOverlay(canvas);
        }

        function deleteMeasureFlashLocal(canvas, measureId) {
            const timers = storeApi.flashTimerStoreFor(canvas);
            if (timers.has(measureId)) {
                clearTimeout(timers.get(measureId));
                timers.delete(measureId);
            }
            const store = storeApi.flashStoreFor(canvas);
            const idx = store.findIndex((measure) => measure.id === measureId);
            if (idx >= 0) store.splice(idx, 1);
            renderMeasureOverlay(canvas);
        }

        function flashMeasureLocal(canvas, measure, ttlMs = storeApi.flashTtlMs(canvas)) {
            if (!canvas || !sameMeasureScene(canvas, measure)) return;
            const store = storeApi.flashStoreFor(canvas);
            const timers = storeApi.flashTimerStoreFor(canvas);
            const idx = store.findIndex((existing) => existing.id === measure.id);
            const next = {
                id: measure.id,
                scene_id: measure.scene_id,
                shape: measure.shape,
                start: { worldX: measure.start.worldX, worldY: measure.start.worldY },
                end: { worldX: measure.end.worldX, worldY: measure.end.worldY },
            };
            const style = normalizedMarkerStyle(measure.style);
            if (style) next.style = style;
            if (idx >= 0) store[idx] = next;
            else store.push(next);
            if (timers.has(next.id)) clearTimeout(timers.get(next.id));
            timers.set(next.id, window.setTimeout(() => {
                const current = store.findIndex((existing) => existing.id === next.id);
                if (current >= 0) store.splice(current, 1);
                timers.delete(next.id);
                renderMeasureOverlay(canvas);
            }, Math.max(1000, Math.min(60000, ttlMs))));
            renderMeasureOverlay(canvas);
        }

        function canvasesForScene(sceneId) {
            return Array.from(document.querySelectorAll("[data-map-canvas]"))
                .filter((canvas) => canvas.dataset.sceneId === sceneId);
        }

        function applyRemoteAreaMarkerUpsert(payload) {
            if (!payload?.scene_id || !payload.marker) return;
            canvasesForScene(payload.scene_id).forEach((canvas) => upsertMeasureLocal(canvas, payload.marker));
            renderMeasureOverlay(activeCanvas());
        }

        function applyRemoteAreaMarkerDelete(payload) {
            if (!payload?.scene_id || !payload.marker_id) return;
            canvasesForScene(payload.scene_id).forEach((canvas) => deleteMeasureLocal(canvas, payload.marker_id));
            renderMeasureOverlay(activeCanvas());
        }

        function applyRemoteAreaMarkerClear(payload) {
            if (!payload?.scene_id) return;
            const keepGm = payload.keep_gm_layer === true;
            canvasesForScene(payload.scene_id).forEach((canvas) => {
                const store = measureStoreFor(canvas);
                if (keepGm) {
                    for (let i = store.length - 1; i >= 0; i -= 1) {
                        if (store[i].layer !== "gm") store.splice(i, 1);
                    }
                } else {
                    store.length = 0;
                }
                storeApi.clearSelectedId(canvas);
                renderMeasureOverlay(canvas);
            });
            renderMeasureOverlay(activeCanvas());
        }

        function applyRemoteMeasureFlash(payload) {
            if (!payload?.scene_id || !payload.measure) return;
            canvasesForScene(payload.scene_id).forEach((canvas) => flashMeasureLocal(canvas, payload.measure, payload.ttl_ms));
            renderMeasureOverlay(activeCanvas());
        }

        function applyRemoteMeasureClear(payload) {
            if (!payload?.scene_id) return;
            canvasesForScene(payload.scene_id).forEach((canvas) => clearMeasureFlashes(canvas));
            renderMeasureOverlay(activeCanvas());
        }

        function applyRemoteMeasureDelete(payload) {
            if (!payload?.scene_id || !payload.measure_id) return;
            canvasesForScene(payload.scene_id).forEach((canvas) => deleteMeasureFlashLocal(canvas, payload.measure_id));
            renderMeasureOverlay(activeCanvas());
        }

        function applyRemoteDrawUpsert(payload) {
            if (!payload?.scene_id || !payload.drawing) return;
            canvasesForScene(payload.scene_id).forEach((canvas) => upsertMeasureLocal(canvas, payload.drawing));
            renderMeasureOverlay(activeCanvas());
        }

        function applyRemoteDrawClear(payload) {
            if (!payload?.scene_id) return;
            const owner = typeof payload.owner_id === "string" && payload.owner_id ? payload.owner_id : null;
            canvasesForScene(payload.scene_id).forEach((canvas) => {
                const store = measureStoreFor(canvas);
                for (let i = store.length - 1; i >= 0; i -= 1) {
                    const item = store[i];
                    if (item.kind !== "freehand" && item.kind !== "text") continue;
                    if (!owner || item.owner_id === owner) store.splice(i, 1);
                }
                const selectedId = selectedMeasureIdFor(canvas);
                if (selectedId && !store.some((m) => m.id === selectedId)) storeApi.clearSelectedId(canvas);
                renderMeasureOverlay(canvas);
            });
            renderMeasureOverlay(activeCanvas());
        }

        function applyMeasureSnapshot(payload) {
            if (!payload?.scene_id || !Array.isArray(payload.board_area_markers)) return;
            canvasesForScene(payload.scene_id).forEach((canvas) => {
                replaceMeasuresSnapshot(canvas, payload.board_area_markers);
            });
            renderMeasureOverlay(activeCanvas());
        }

        function moveSelectedMeasureToLayer(canvas, wantGm) {
            const measureId = selectedMeasureIdFor(canvas);
            if (!measureId) return;
            const measure = measureStoreFor(canvas).find((m) => m.id === measureId);
            if (!measure) return;
            const before = cloneMeasure(measure);
            const next = { ...measure };
            if (wantGm) next.layer = "gm";
            else delete next.layer;
            upsertMeasureLocal(canvas, next);
            broadcastMeasureUpsert(canvas, next);
            pushMeasureChangeHistory(canvas, before, next);
        }

        function handleEscape() {
            if (activeMeasure || activeMeasureMove) cancelActiveMeasure();
            if (activeFreehand) cancelActiveFreehand();
            if (editors.activeTextCanvas()) editors.cancelTextEditor();
            if (editors.activeAreaMarkerCanvas()) editors.cancelAreaMarkerTextEditor({ broadcast: true });
        }

        function handleSubtoolChanged(detail) {
            if (detail?.tool === "ruler" || detail?.tool === "shape") {
                editors.commitAreaMarkerTextEditor();
                cancelActiveMeasure();
            }
            if (detail?.tool === "draw") {
                editors.commitTextEditor();
                setSelectedMeasure(activeCanvas(), null);
            }
        }

        return {
            activeFreehand: () => activeFreehand,
            activeMeasure: () => activeMeasure,
            activeMeasureMove: () => activeMeasureMove,
            applyActiveLayer,
            applyMeasureSnapshot,
            applyRemoteAreaMarkerClear,
            applyRemoteAreaMarkerDelete,
            applyRemoteAreaMarkerUpsert,
            applyRemoteDrawClear,
            applyRemoteDrawUpsert,
            applyRemoteMeasureClear,
            applyRemoteMeasureDelete,
            applyRemoteMeasureFlash,
            broadcastAreaMarkerUpsert,
            broadcastDrawUpsert,
            clearMeasures,
            deleteSelectedMeasure,
            handleEscape,
            handleSubtoolChanged,
            measureAtPointForContext,
            moveSelectedMeasureToLayer,
            renderMeasureOverlay,
            selectedMeasureIdFor,
            setSelectedMeasure,
            startDrawTool,
            startMeasure,
            stopFreehand,
            stopMeasure,
            textFontSizeFor,
            updateFreehand,
            updateMeasure,
            upsertMeasureLocal,
        };
    }

    window.GravewrightMapMeasureController = { createMeasureController };
})();
