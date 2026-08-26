(() => {
    const median = (values) => {
        const sorted = [...values].sort((a, b) => a - b);
        const middle = Math.floor(sorted.length / 2);
        return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
    };

    const modulo = (value, size) => ((value % size) + size) % size;

    function calculateCalibration(samples) {
        const roughSize = median(samples.flatMap((sample) => [sample.width, sample.height]));
        const origin = samples[0];
        const end = samples[samples.length - 1];
        const longRangeSizes = [];
        samples.slice(1).forEach((sample) => {
            const columns = Math.round((sample.x - origin.x) / roughSize);
            const rows = Math.round((sample.y - origin.y) / roughSize);
            if (columns > 0) longRangeSizes.push((sample.x - origin.x) / columns);
            if (rows > 0) longRangeSizes.push((sample.y - origin.y) / rows);
        });
        const spanX = end.x + end.width - origin.x;
        const spanY = end.y + end.height - origin.y;
        const columns = Math.round(spanX / roughSize);
        const rows = Math.round(spanY / roughSize);
        let size = columns > 0 && rows > 0
            ? (spanX + spanY) / (columns + rows)
            : (longRangeSizes.length ? median(longRangeSizes) : roughSize);
        // Raster maps commonly have an exact integer cell size. Tiny drawing
        // errors must not accumulate across dozens of rows/columns.
        if (Math.abs(size - Math.round(size)) <= Math.max(0.08, size * 0.0025)) {
            size = Math.round(size);
        }
        const stabilizeOffset = (value) => {
            const canonical = modulo(value, size);
            const edgeDistance = Math.min(canonical, size - canonical);
            return edgeDistance <= Math.max(0.75, size * 0.01) ? 0 : canonical;
        };
        return {
            size,
            // Any parallel grid line can be used as the first sample. Reduce
            // that absolute coordinate to the canonical origin inside one cell;
            // otherwise sampling near the far edge would make cell 0 start there.
            offsetX: stabilizeOffset(origin.x),
            offsetY: stabilizeOffset(origin.y),
        };
    }

    function begin(button) {
        const modal = button.closest(".scene-edit-modal");
        const form = button.closest("form");
        const sceneId = form?.querySelector('[name="scene_id"]')?.value || "";
        const canvas = [...document.querySelectorAll("[data-map-canvas]")]
            .find((entry) => entry.dataset.sceneId === sceneId);
        if (!modal || !form || !canvas || !window.GravewrightMap) {
            window.alert(button.dataset.gridMapperInactive || "Activate this scene first.");
            return;
        }

        modal.hidden = true;
        const samples = [];
        let drawing = null;
        let animationFrame = 0;
        const layer = document.createElement("div");
        layer.className = "scene-grid-mapper-overlay";
        const previewCanvas = document.createElement("canvas");
        previewCanvas.className = "scene-grid-mapper-preview";
        layer.appendChild(previewCanvas);
        const toolbar = document.createElement("div");
        toolbar.className = "scene-grid-mapper-toolbar";
        toolbar.innerHTML = `<header class="scene-grid-mapper-head">
                <span class="scene-grid-mapper-icon"><i class="ph ph-grid-four"></i></span>
                <div><strong>${button.dataset.gridMapperPanelTitle}</strong><span data-grid-mapper-instruction></span></div>
                <b data-grid-mapper-count>0 / 3</b>
            </header>
            <div class="scene-grid-mapper-progress" aria-hidden="true">
                <i data-grid-step="0"></i><span></span><i data-grid-step="1"></i><span></span><i data-grid-step="2"></i>
            </div>
            <div class="scene-grid-mapper-result" data-grid-mapper-result hidden>
                <span><small>${button.dataset.gridMapperCell}</small><strong data-grid-result-size></strong></span>
                <span><small>${button.dataset.gridMapperOrigin}</small><strong data-grid-result-origin></strong></span>
                <em><i class="ph ph-eye"></i> ${button.dataset.gridMapperPreview}</em>
            </div>
            <footer class="scene-grid-mapper-actions">
                <button type="button" class="secondary-action" data-grid-mapper-undo disabled><i class="ph ph-arrow-counter-clockwise"></i>${button.dataset.gridMapperUndo}</button>
                <button type="button" class="secondary-action" data-grid-mapper-cancel>${button.dataset.gridMapperCancel}</button>
                <button type="button" class="primary-action" data-grid-mapper-apply disabled><i class="ph ph-check"></i>${button.dataset.gridMapperFinish}</button>
            </footer>`;
        document.body.append(layer, toolbar);

        const count = toolbar.querySelector("[data-grid-mapper-count]");
        const undo = toolbar.querySelector("[data-grid-mapper-undo]");
        const apply = toolbar.querySelector("[data-grid-mapper-apply]");
        const instruction = toolbar.querySelector("[data-grid-mapper-instruction]");
        const resultPanel = toolbar.querySelector("[data-grid-mapper-result]");
        const resultSize = toolbar.querySelector("[data-grid-result-size]");
        const resultOrigin = toolbar.querySelector("[data-grid-result-origin]");
        const steps = [button.dataset.gridMapperStepStart, button.dataset.gridMapperStepCenter, button.dataset.gridMapperStepEnd];
        const boxes = [];

        const renderSample = (sample) => {
            const state = window.GravewrightMap.stateFor(canvas);
            Object.assign(sample.box.style, {
                left: `${sample.x * state.zoom + state.offsetX}px`,
                top: `${sample.y * state.zoom + state.offsetY}px`,
                width: `${sample.width * state.zoom}px`,
                height: `${sample.height * state.zoom}px`,
            });
        };
        const renderPreview = () => {
            const dpr = window.devicePixelRatio || 1;
            const width = window.innerWidth;
            const height = window.innerHeight;
            if (previewCanvas.width !== Math.round(width * dpr) || previewCanvas.height !== Math.round(height * dpr)) {
                previewCanvas.width = Math.round(width * dpr);
                previewCanvas.height = Math.round(height * dpr);
                previewCanvas.style.width = `${width}px`;
                previewCanvas.style.height = `${height}px`;
            }
            const ctx = previewCanvas.getContext("2d");
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            ctx.clearRect(0, 0, width, height);
            if (samples.length !== 3) return;
            const calibration = calculateCalibration(samples);
            const state = window.GravewrightMap.stateFor(canvas);
            const scene = window.GravewrightMap.sceneDataFor(canvas);
            const size = calibration.size;
            const sceneLeft = state.offsetX;
            const sceneTop = state.offsetY;
            const sceneRight = state.offsetX + scene.width * state.zoom;
            const sceneBottom = state.offsetY + scene.height * state.zoom;
            ctx.save();
            ctx.beginPath();
            ctx.rect(sceneLeft, sceneTop, sceneRight - sceneLeft, sceneBottom - sceneTop);
            ctx.clip();
            ctx.strokeStyle = "rgba(239, 197, 111, .82)";
            ctx.lineWidth = 1;
            ctx.setLineDash([5, 4]);
            ctx.beginPath();
            for (let x = calibration.offsetX, lines = 0; x <= scene.width && lines < 500; x += size, lines += 1) {
                const sx = Math.round(x * state.zoom + state.offsetX) + .5;
                ctx.moveTo(sx, sceneTop); ctx.lineTo(sx, sceneBottom);
            }
            for (let y = calibration.offsetY, lines = 0; y <= scene.height && lines < 500; y += size, lines += 1) {
                const sy = Math.round(y * state.zoom + state.offsetY) + .5;
                ctx.moveTo(sceneLeft, sy); ctx.lineTo(sceneRight, sy);
            }
            ctx.stroke();
            ctx.restore();
        };
        const followCamera = () => {
            samples.forEach(renderSample);
            renderPreview();
            animationFrame = window.requestAnimationFrame(followCamera);
        };

        const cleanup = (reopen = true) => {
            window.cancelAnimationFrame(animationFrame);
            layer.remove();
            toolbar.remove();
            if (reopen) modal.hidden = false;
        };
        const refresh = () => {
            count.textContent = `${samples.length} / 3`;
            instruction.innerHTML = `<i class="ph ph-grid-four"></i> ${steps[Math.min(samples.length, 2)] || button.dataset.gridMapperInstruction}`;
            undo.disabled = samples.length === 0;
            apply.disabled = samples.length !== 3;
            toolbar.querySelectorAll("[data-grid-step]").forEach((step) => {
                step.classList.toggle("is-complete", Number(step.dataset.gridStep) < samples.length);
                step.classList.toggle("is-current", Number(step.dataset.gridStep) === samples.length);
            });
            resultPanel.hidden = samples.length !== 3;
            if (samples.length === 3) {
                const calibration = calculateCalibration(samples);
                const imageScale = window.GravewrightMap.sceneDataFor(canvas)?.imageScale || 1;
                resultSize.textContent = `${(calibration.size / imageScale).toFixed(4).replace(/0+$/, "").replace(/\.$/, "")} px`;
                resultOrigin.textContent = `${(calibration.offsetX / imageScale).toFixed(2)}, ${(calibration.offsetY / imageScale).toFixed(2)}`;
            }
        };
        const point = (event) => window.GravewrightMap.worldFromScreen(canvas, event.clientX, event.clientY);
        refresh();

        layer.addEventListener("pointerdown", (event) => {
            if (event.button === 1 || event.button === 2) {
                event.preventDefault();
                event.stopPropagation();
                window.GravewrightMap.startPan(canvas, event);
                return;
            }
            if (event.button !== 0) return;
            if (samples.length >= 3) return;
            const start = point(event);
            if (!start) return;
            const box = document.createElement("div");
            box.className = "scene-grid-mapper-sample is-drawing";
            layer.appendChild(box);
            drawing = { pointerId: event.pointerId, start, startX: event.clientX, startY: event.clientY, box };
            layer.setPointerCapture(event.pointerId);
        });
        layer.addEventListener("contextmenu", (event) => event.preventDefault());
        layer.addEventListener("wheel", (event) => {
            event.preventDefault();
            canvas.dispatchEvent(new WheelEvent("wheel", {
                bubbles: true,
                cancelable: true,
                clientX: event.clientX,
                clientY: event.clientY,
                deltaX: event.deltaX,
                deltaY: event.deltaY,
                deltaZ: event.deltaZ,
                deltaMode: event.deltaMode,
                ctrlKey: event.ctrlKey,
                shiftKey: event.shiftKey,
                altKey: event.altKey,
                metaKey: event.metaKey,
            }));
        }, { passive: false });
        layer.addEventListener("pointermove", (event) => {
            if (!drawing || drawing.pointerId !== event.pointerId) return;
            const left = Math.min(drawing.startX, event.clientX);
            const top = Math.min(drawing.startY, event.clientY);
            Object.assign(drawing.box.style, {
                left: `${left}px`, top: `${top}px`,
                width: `${Math.abs(event.clientX - drawing.startX)}px`,
                height: `${Math.abs(event.clientY - drawing.startY)}px`,
            });
        });
        layer.addEventListener("pointerup", (event) => {
            if (!drawing || drawing.pointerId !== event.pointerId) return;
            const end = point(event);
            const width = Math.abs(end.worldX - drawing.start.worldX);
            const height = Math.abs(end.worldY - drawing.start.worldY);
            if (width >= 8 && height >= 8) {
                drawing.box.classList.remove("is-drawing");
                const sample = {
                    x: Math.min(drawing.start.worldX, end.worldX),
                    y: Math.min(drawing.start.worldY, end.worldY),
                    width,
                    height,
                    box: drawing.box,
                };
                samples.push(sample);
                boxes.push(drawing.box);
                renderSample(sample);
            } else drawing.box.remove();
            drawing = null;
            refresh();
        });
        undo.addEventListener("click", () => {
            samples.pop();
            boxes.pop()?.remove();
            refresh();
        });
        toolbar.querySelector("[data-grid-mapper-cancel]").addEventListener("click", () => cleanup());
        apply.addEventListener("click", () => {
            const scene = window.GravewrightMap.sceneDataFor(canvas);
            const calibration = calculateCalibration(samples);
            const scaledSize = calibration.size;
            const imageScale = scene?.imageScale || 1;
            const offsetX = calibration.offsetX / imageScale;
            const offsetY = calibration.offsetY / imageScale;
            form.querySelector('[name="tile_size"]').value = (scaledSize / imageScale).toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
            form.querySelector('[name="grid_offset_x"]').value = offsetX.toFixed(3);
            form.querySelector('[name="grid_offset_y"]').value = offsetY.toFixed(3);
            form.querySelector('[name="grid_visible"]').checked = true;
            cleanup();
        });
        document.addEventListener("keydown", function escape(event) {
            if (event.key !== "Escape" || !document.body.contains(layer)) return;
            document.removeEventListener("keydown", escape);
            cleanup();
        });
        animationFrame = window.requestAnimationFrame(followCamera);
    }

    document.addEventListener("click", (event) => {
        const button = event.target.closest("[data-grid-mapper-start]");
        if (button) begin(button);
    });
    window.GravewrightGridMapper = { calculateCalibration };
})();
