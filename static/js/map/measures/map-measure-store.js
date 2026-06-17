(() => {
    function createMeasureStore() {
        const measureStores = new WeakMap();
        const measureFlashStores = new WeakMap();
        const measureFlashTimers = new WeakMap();
        const selectedMeasureIds = new WeakMap();
        let measureSeq = 0;

        function newMeasureId() {
            if (window.crypto?.randomUUID) return `measure-${window.crypto.randomUUID()}`;
            measureSeq += 1;
            return `measure-${Date.now().toString(36)}-${measureSeq.toString(36)}`;
        }

        function measureStoreFor(canvas) {
            let store = measureStores.get(canvas);
            if (!store) {
                store = [];
                measureStores.set(canvas, store);
            }
            return store;
        }

        function flashStoreFor(canvas) {
            let store = measureFlashStores.get(canvas);
            if (!store) {
                store = [];
                measureFlashStores.set(canvas, store);
            }
            return store;
        }

        function flashTimerStoreFor(canvas) {
            let timers = measureFlashTimers.get(canvas);
            if (!timers) {
                timers = new Map();
                measureFlashTimers.set(canvas, timers);
            }
            return timers;
        }

        function flashTtlMs(canvas) {
            const seconds = parseFloat(canvas?.dataset.measureFlashSeconds || "6");
            if (!Number.isFinite(seconds)) return 6000;
            return Math.max(1, Math.min(60, seconds)) * 1000;
        }

        function selectedIdFor(canvas) {
            return selectedMeasureIds.get(canvas) || null;
        }

        function setSelectedId(canvas, measureId) {
            if (measureId) selectedMeasureIds.set(canvas, measureId);
            else selectedMeasureIds.delete(canvas);
        }

        function clearSelectedId(canvas) {
            selectedMeasureIds.delete(canvas);
        }

        return {
            clearSelectedId,
            flashStoreFor,
            flashTimerStoreFor,
            flashTtlMs,
            measureStoreFor,
            newMeasureId,
            selectedIdFor,
            setSelectedId,
        };
    }

    function areaMarkerPresetsFor(canvas) {
        try {
            const raw = JSON.parse(canvas?.dataset.areaMarkerPresets || "[]");
            return Array.isArray(raw) ? raw.filter((item) => item && typeof item === "object") : [];
        } catch {
            return [];
        }
    }

    function areaMarkerPresetFor(canvas, shape) {
        const presetId = window.GravewrightTools?.activeMarkerPresetId || canvas?.dataset.activeMarkerPreset || "";
        const preset = areaMarkerPresetsFor(canvas).find((item) => item.id === presetId) || null;
        return preset && (!preset.shape || preset.shape === shape) ? preset : null;
    }

    function normalizedMarkerStyle(raw) {
        if (!raw || typeof raw !== "object") return null;
        const style = {};
        ["stroke", "fill", "strokeDasharray"].forEach((key) => {
            if (typeof raw[key] === "string" && raw[key]) style[key] = raw[key];
        });
        if (Number.isFinite(Number(raw.strokeWidth))) {
            style.strokeWidth = Math.max(1, Math.min(12, Number(raw.strokeWidth)));
        }
        return Object.keys(style).length ? style : null;
    }

    function normalizedAreaMarkerText(raw) {
        if (typeof raw?.text !== "string") return "";
        return raw.text.replace(/\r\n?/g, "\n").trim().slice(0, 220);
    }

    function applyOwnerLayer(next, raw) {
        if (typeof raw?.owner_id === "string" && raw.owner_id) next.owner_id = raw.owner_id;
        if (raw?.layer === "gm") next.layer = "gm";
        return next;
    }

    function normalizedTextDrawing(raw) {
        const text = typeof raw?.text === "string" ? raw.text.trim().slice(0, 200) : "";
        const pos = raw?.position;
        if (!text || !pos || !Number.isFinite(Number(pos.worldX)) || !Number.isFinite(Number(pos.worldY))) {
            return null;
        }
        const next = {
            id: raw.id,
            scene_id: raw.scene_id,
            kind: "text",
            position: { worldX: Number(pos.worldX), worldY: Number(pos.worldY) },
            text,
            fontSize: Math.max(8, Math.min(200, Number(raw.fontSize) || 28)),
        };
        const style = normalizedMarkerStyle(raw.style);
        if (style) next.style = style;
        return applyOwnerLayer(next, raw);
    }

    function svgStyleFor(measure) {
        const style = normalizedMarkerStyle(measure?.style);
        if (!style) return {};
        const parts = [];
        if (style.stroke) parts.push(`stroke:${style.stroke}`);
        if (style.fill) parts.push(`fill:${style.fill}`);
        if (style.strokeWidth) parts.push(`stroke-width:${style.strokeWidth}`);
        if (style.strokeDasharray) parts.push(`stroke-dasharray:${style.strokeDasharray}`);
        return parts.length ? { style: parts.join(";") } : {};
    }

    function activeDrawStyle(canvas) {
        const color = window.GravewrightTools?.activeDrawColor || canvas?.dataset.activeDrawColor || "#f8fafc";
        return {
            stroke: /^#[0-9a-fA-F]{6}$/.test(color) ? color.toLowerCase() : "#f8fafc",
            fill: "none",
            strokeWidth: 4,
        };
    }

    window.GravewrightMapMeasureStore = {
        activeDrawStyle,
        applyOwnerLayer,
        areaMarkerPresetFor,
        areaMarkerPresetsFor,
        createMeasureStore,
        normalizedAreaMarkerText,
        normalizedMarkerStyle,
        normalizedTextDrawing,
        svgStyleFor,
    };
})();
