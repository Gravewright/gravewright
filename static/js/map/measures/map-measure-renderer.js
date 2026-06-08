(() => {
    function appendSvg(parent, tag, attrs = {}) {
        const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
        Object.entries(attrs).forEach(([key, value]) => {
            el.setAttribute(key, String(value));
        });
        parent.appendChild(el);
        return el;
    }

    function appendMeasureLabel(parent, x, y, text) {
        const width = Math.max(44, text.length * 7 + 14);
        const height = 22;
        const group = appendSvg(parent, "g", { class: "board-measure-label" });
        appendSvg(group, "rect", {
            x: Math.round(x - width / 2),
            y: Math.round(y - height / 2),
            width,
            height,
            rx: 5,
            ry: 5,
        });
        const label = appendSvg(group, "text", {
            x: Math.round(x),
            y: Math.round(y + 4),
            "text-anchor": "middle",
        });
        label.textContent = text;
    }

    function wrappedMarkerTextLines(text) {
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
        return lines.slice(0, 4);
    }

    function createMeasureRenderer(deps) {
        let overlayEl = null;
        const {
            activeCanvas,
            effectiveIsGm,
            flashStoreFor,
            geometry,
            getActiveFreehand,
            getActiveMeasure,
            measureStoreFor,
            onRenderStart,
            sceneDataFor,
            selectedMeasureIdFor,
            stateFor,
            svgStyleFor,
            textFontSizeFor,
        } = deps;

        function ensureOverlay() {
            if (overlayEl) return overlayEl;
            overlayEl = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            overlayEl.classList.add("board-measure-overlay");
            overlayEl.setAttribute("aria-hidden", "true");
            document.body.appendChild(overlayEl);
            return overlayEl;
        }

        function appendAreaMarkerText(parent, measure, state) {
            const lines = wrappedMarkerTextLines(measure.text);
            if (!lines.length) return;
            const anchor = geometry.worldToScreenXY(geometry.areaMarkerTextAnchor(measure), state);
            const width = Math.max(90, Math.max(...lines.map((line) => line.length)) * 7.1 + 22);
            const lineHeight = 15;
            const height = lines.length * lineHeight + 14;
            const group = appendSvg(parent, "g", { class: "board-area-marker-text" });
            appendSvg(group, "rect", {
                x: Math.round(anchor.x - width / 2),
                y: Math.round(anchor.y - height / 2),
                width,
                height,
                rx: 6,
                ry: 6,
            });
            const text = appendSvg(group, "text", {
                x: Math.round(anchor.x),
                y: Math.round(anchor.y - ((lines.length - 1) * lineHeight) / 2 + 5),
                "text-anchor": "middle",
            });
            lines.forEach((line, index) => {
                const tspan = appendSvg(text, "tspan", {
                    x: Math.round(anchor.x),
                    dy: index === 0 ? 0 : lineHeight,
                });
                tspan.textContent = line;
            });
        }

        function conePathFor(start, end, state) {
            const angle = Math.atan2(end.worldY - start.worldY, end.worldX - start.worldX);
            const radius = Math.sqrt((end.worldX - start.worldX) ** 2 + (end.worldY - start.worldY) ** 2);
            const halfAngle = Math.PI / 6;
            const left = {
                worldX: start.worldX + Math.cos(angle - halfAngle) * radius,
                worldY: start.worldY + Math.sin(angle - halfAngle) * radius,
            };
            const right = {
                worldX: start.worldX + Math.cos(angle + halfAngle) * radius,
                worldY: start.worldY + Math.sin(angle + halfAngle) * radius,
            };
            const tip = geometry.worldToScreenXY(start, state);
            const l = geometry.worldToScreenXY(left, state);
            const r = geometry.worldToScreenXY(right, state);
            const screenRadius = radius * state.zoom;
            return `M ${tip.x} ${tip.y} L ${l.x} ${l.y} A ${screenRadius} ${screenRadius} 0 0 1 ${r.x} ${r.y} Z`;
        }

        function renderSingleMeasure(parent, measure, scene, state, preview = false) {
            if (measure.kind === "text") {
                const pos = geometry.worldToScreenXY(measure.position, state);
                const isSelected = !preview && selectedMeasureIdFor(activeCanvas()) === measure.id;
                const group = appendSvg(parent, "g", {
                    class: [
                        "board-measure",
                        "board-measure--text",
                        preview ? "board-measure--preview" : "",
                        isSelected ? "board-measure--selected" : "",
                        measure.layer === "gm" ? "board-measure--gm-layer" : "",
                    ].filter(Boolean).join(" "),
                });
                const fontPx = Math.max(6, (measure.fontSize || textFontSizeFor(scene)) * state.zoom);
                const fill = measure.style?.fill || "#f8fafc";
                const text = appendSvg(group, "text", {
                    x: pos.x,
                    y: pos.y,
                    "dominant-baseline": "hanging",
                    "text-anchor": "start",
                    style: `font-size:${fontPx}px;fill:${fill}`,
                });
                text.textContent = measure.text || "";
                return;
            }

            if (measure.kind === "freehand") {
                const isSelected = !preview && selectedMeasureIdFor(activeCanvas()) === measure.id;
                const group = appendSvg(parent, "g", {
                    class: [
                        "board-measure",
                        "board-measure--freehand",
                        preview ? "board-measure--preview" : "",
                        isSelected ? "board-measure--selected" : "",
                        measure.layer === "gm" ? "board-measure--gm-layer" : "",
                    ].filter(Boolean).join(" "),
                });
                appendSvg(group, "path", {
                    d: geometry.worldPathFor(measure.points, state),
                    ...svgStyleFor(measure),
                });
                return;
            }

            const start = geometry.worldToScreenXY(measure.start, state);
            const end = geometry.worldToScreenXY(measure.end, state);
            const selected = selectedMeasureIdFor(activeCanvas()) === measure.id;
            const group = appendSvg(parent, "g", {
                class: [
                    "board-measure",
                    `board-measure--${measure.shape}`,
                    preview ? "board-measure--preview" : "",
                    selected && !preview ? "board-measure--selected" : "",
                    measure.layer === "gm" ? "board-measure--gm-layer" : "",
                ].filter(Boolean).join(" "),
            });
            const label = geometry.measureLabelFor(measure, scene);
            const shapeStyle = svgStyleFor(measure);
            const hasMarkerText = Boolean(measure.text);

            if (measure.shape === "line") {
                appendSvg(group, "line", { x1: start.x, y1: start.y, x2: end.x, y2: end.y, ...shapeStyle });
                appendMeasureLabel(group, (start.x + end.x) / 2, (start.y + end.y) / 2 - 14, label);
                if (hasMarkerText) appendAreaMarkerText(group, measure, state);
                return;
            }

            if (measure.shape === "circle") {
                const radius = Math.sqrt((end.x - start.x) ** 2 + (end.y - start.y) ** 2);
                appendSvg(group, "circle", { cx: start.x, cy: start.y, r: radius, ...shapeStyle });
                appendSvg(group, "line", { class: "board-measure-guide", x1: start.x, y1: start.y, x2: end.x, y2: end.y });
                appendMeasureLabel(group, end.x, end.y - 16, label);
                if (hasMarkerText) appendAreaMarkerText(group, measure, state);
                return;
            }

            if (measure.shape === "square") {
                const x = Math.min(start.x, end.x);
                const y = Math.min(start.y, end.y);
                appendSvg(group, "rect", {
                    x,
                    y,
                    width: Math.abs(end.x - start.x),
                    height: Math.abs(end.y - start.y),
                    ...shapeStyle,
                });
                if (hasMarkerText) {
                    appendMeasureLabel(group, (start.x + end.x) / 2, Math.min(start.y, end.y) - 14, label);
                    appendAreaMarkerText(group, measure, state);
                } else {
                    appendMeasureLabel(group, (start.x + end.x) / 2, (start.y + end.y) / 2, label);
                }
                return;
            }

            if (measure.shape === "cone") {
                appendSvg(group, "path", { d: conePathFor(measure.start, measure.end, state), ...shapeStyle });
                appendSvg(group, "line", { class: "board-measure-guide", x1: start.x, y1: start.y, x2: end.x, y2: end.y });
                appendMeasureLabel(group, end.x, end.y - 16, label);
                if (hasMarkerText) appendAreaMarkerText(group, measure, state);
            }
        }

        function renderOverlay(canvas = activeCanvas()) {
            const overlay = ensureOverlay();
            overlay.setAttribute("viewBox", `0 0 ${window.innerWidth} ${window.innerHeight}`);
            overlay.setAttribute("width", String(window.innerWidth));
            overlay.setAttribute("height", String(window.innerHeight));
            while (overlay.firstChild) overlay.removeChild(overlay.firstChild);

            const scene = canvas ? sceneDataFor(canvas) : null;
            if (!canvas || !scene || !canvas.closest(".room-workspace")?.classList.contains("is-active")) {
                overlay.hidden = true;
                return;
            }

            const state = stateFor(canvas);
            onRenderStart?.(canvas);
            const showGmLayer = effectiveIsGm(canvas);
            const measures = measureStoreFor(canvas)
                .filter((measure) => showGmLayer || measure.layer !== "gm");
            const flashes = flashStoreFor(canvas);
            measures.forEach((measure) => renderSingleMeasure(overlay, measure, scene, state));
            flashes.forEach((measure) => renderSingleMeasure(overlay, measure, scene, state, false));

            const activeFreehand = getActiveFreehand?.();
            const activeMeasure = getActiveMeasure?.();
            if (activeFreehand?.canvas === canvas) {
                renderSingleMeasure(overlay, activeFreehand, scene, state, true);
            }
            if (activeMeasure?.canvas === canvas) {
                renderSingleMeasure(overlay, activeMeasure, scene, state, true);
            }
            overlay.hidden = !measures.length
                && !flashes.length
                && activeMeasure?.canvas !== canvas
                && activeFreehand?.canvas !== canvas;
        }

        return {
            appendAreaMarkerText,
            appendMeasureLabel,
            appendSvg,
            conePathFor,
            ensureOverlay,
            renderOverlay,
            renderSingleMeasure,
            wrappedMarkerTextLines,
        };
    }

    window.GravewrightMapMeasureRenderer = { createMeasureRenderer };
})();
