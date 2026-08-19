(() => {
    function wrappedMarkerText(text) {
        const lines = [];
        String(text || "").split("\n").forEach((rawLine) => {
            const words = rawLine.trim().split(/\s+/).filter(Boolean);
            let line = "";
            words.forEach((word) => {
                const next = line ? `${line} ${word}` : word;
                if (next.length > 24 && line) {
                    lines.push(line);
                    line = word;
                } else {
                    line = next;
                }
            });
            if (line) lines.push(line);
        });
        return lines.slice(0, 4).join("\n");
    }

    function createMeasureRenderer(deps) {
        const {
            activeCanvas,
            boardRenderer,
            effectiveIsGm,
            flashStoreFor,
            geometry,
            getActiveFreehand,
            getActiveMeasure,
            measureStoreFor,
            onRenderStart,
            sceneDataFor,
            selectedMeasureIdFor,
            textFontSizeFor,
        } = deps;

        function presentationItem(measure, scene, preview = false) {
            const item = {
                id: measure.id || "preview",
                kind: measure.kind || "shape",
                shape: measure.shape,
                style: measure.style || null,
                preview,
                selected: !preview && selectedMeasureIdFor(activeCanvas()) === measure.id,
                gmLayer: measure.layer === "gm",
            };
            if (measure.kind === "freehand") {
                item.points = measure.points || [];
                return item;
            }
            if (measure.kind === "text") {
                item.position = measure.position;
                item.text = measure.text || "";
                item.fontSize = measure.fontSize || textFontSizeFor(scene);
                return item;
            }
            item.start = measure.start;
            item.end = measure.end;
            item.rotation = geometry.normalizedRotation(measure);
            item.label = geometry.measureLabelFor(measure, scene);
            if (measure.shape === "line" || measure.shape === "square") {
                item.cells = geometry.gridCellsForMeasure(measure, scene);
            }
            const markerText = wrappedMarkerText(measure.text);
            if (markerText) {
                item.markerText = markerText;
                item.markerTextAnchor = geometry.areaMarkerTextAnchor(measure);
            }
            return item;
        }

        function renderOverlay(canvas = activeCanvas()) {
            if (!canvas) return;
            const scene = sceneDataFor(canvas);
            const workspaceActive = canvas.closest(".room-workspace")?.classList.contains("is-active");
            if (!scene || !workspaceActive) {
                boardRenderer.setMeasurements(canvas, { items: [] });
                return;
            }
            onRenderStart?.(canvas);
            const showGmLayer = effectiveIsGm(canvas);
            const roomId = canvas.dataset.roomId || "";
            const visible = (measure) => (showGmLayer || measure.layer !== "gm")
                && window.GravewrightTools?.isLayerVisible?.(
                    measure.layer === "gm" ? "gm" : "game",
                    roomId,
                ) !== false;
            const items = [
                ...measureStoreFor(canvas).filter(visible).map((measure) => presentationItem(measure, scene)),
                ...flashStoreFor(canvas).filter(visible).map((measure) => presentationItem(measure, scene)),
            ];
            const activeFreehand = getActiveFreehand?.();
            const activeMeasure = getActiveMeasure?.();
            if (activeFreehand?.canvas === canvas) items.push(presentationItem(activeFreehand, scene, true));
            if (activeMeasure?.canvas === canvas) items.push(presentationItem(activeMeasure, scene, true));
            boardRenderer.setMeasurements(canvas, { items });
        }

        return { renderOverlay, wrappedMarkerText };
    }

    window.GravewrightMapMeasureRenderer = { createMeasureRenderer };
})();
