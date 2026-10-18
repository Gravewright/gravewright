/** Continuous terrain gestures; the host owns pointer capture, history and rendering. */
import { clone, applyTerrainStroke } from './model.js';
import { terrainBrushLimits } from './terrain-brush.js';

const finitePoint = point => point && Number.isFinite(point.x) && Number.isFinite(point.y);
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
const limitError = 'The map has too many terrain brush dabs.';
export function createTerrainPainter({ getDocument, getOptions, onPreview, onCommit, onCancel, onError,
    schedule = callback => globalThis.setInterval(callback, terrainBrushLimits.holdMilliseconds),
    unschedule = handle => globalThis.clearInterval(handle) }) {
    let gesture, timer, disposed = false;
    const stopTimer = () => { if (timer !== undefined) { unschedule(timer); timer = undefined; } };
    const bounded = (point, document) => ({ x: Math.max(0, Math.min(document.columns, point.x)), y: Math.max(0, Math.min(document.rows, point.y)) });
    function preview() {
        const current = gesture;
        if (!current) return;
        const candidate = clone(current.before), points = [...current.stamps];
        if (distance(points.at(-1), current.point) > 1e-9) points.push({ ...current.point });
        const result = current.overflow ? { ok: false, changed: false, refs: [], error: limitError }
            : applyTerrainStroke(candidate, points, { ...current.options, choices: current.choices });
        current.candidate = candidate; current.result = result;
        if (!result.ok) stopTimer();
        onPreview?.(candidate, { mode: 'terrain', cursor: { ...current.point }, changed: result.changed, invalid: !result.ok,
            operation: current.options.operation, size: current.options.size, hardness: current.options.hardness,
            intensity: current.options.intensity, dabs: points.length });
    }
    function move(point) {
        if (!gesture || !finitePoint(point)) return;
        const current = gesture, next = bounded(point, current.before), from = current.last;
        const size = distance(from, next);
        if (!size) return;
        if (size / current.spacing > terrainBrushLimits.dabs - current.stamps.length + 1) current.overflow = true;
        if (!current.overflow) {
            let walked = 0;
            while (walked + current.until <= size + 1e-10) {
                walked += current.until;
                const t = Math.min(1, walked / size);
                current.stamps.push({ x: from.x + (next.x - from.x) * t, y: from.y + (next.y - from.y) * t });
                current.until = current.spacing;
                if (current.stamps.length > terrainBrushLimits.dabs) { current.overflow = true; break; }
            }
            current.until -= Math.max(0, size - walked);
        }
        current.last = next; current.point = next; preview();
    }
    function cancel() {
        stopTimer();
        if (!gesture) return false;
        gesture = undefined; onCancel?.(); return true;
    }
    return {
        get active() { return Boolean(gesture); },
        start(point) {
            if (disposed || gesture || !finitePoint(point)) return false;
            const before = clone(getDocument()), options = { size: 1, hardness: .5, intensity: 1, operation: 'paint', ...clone(getOptions()) };
            const layer = before.layers?.find(item => item.id === options.layerId);
            if (!layer || layer.visible === false || layer.locked) { onError?.('Choose a visible, unlocked layer before painting.'); return false; }
            if (!Number.isFinite(options.size) || options.size < .05 || options.size > 20) { onError?.('Invalid floor brush.'); return false; }
            const first = bounded(point, before), spacing = options.size / 2 * terrainBrushLimits.spacing;
            gesture = { before, options, point: first, last: first, stamps: [first], spacing, until: spacing,
                choices: new Map(), overflow: false, candidate: null, result: null };
            preview();
            if (gesture.result.ok && options.intensity > 0) timer = schedule(() => {
                if (!gesture) return;
                gesture.stamps.push({ ...gesture.point });
                if (gesture.stamps.length > terrainBrushLimits.dabs) gesture.overflow = true;
                preview();
            });
            return true;
        },
        move,
        end(point) {
            if (!gesture) return false;
            if (finitePoint(point)) move(point);
            stopTimer();
            const completed = gesture; gesture = undefined;
            if (!completed.result.ok) { onError?.(completed.result.error); onCancel?.(); return false; }
            if (!completed.result.changed) { onCancel?.(); return false; }
            onCommit?.(completed.candidate, completed.result.refs); return true;
        },
        cancel,
        dispose() { disposed = true; cancel(); },
    };
}
