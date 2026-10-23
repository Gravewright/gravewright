/** Event-free floor gestures. The workspace owns input, rendering and history. */
import { clone, floorBrushCells, floorRectangleCells, floorCircleCells, floorPolygonCells, floodFloorCells,
    paintFloorCells, eraseFloorCells, floorFreeContours, applyFloorContours, fillFloorShape, documentEditingMode } from './model.js';
import { documentBounds } from './document-bounds.js';

const samePoint = (a, b) => a && b && Math.hypot(a.x - b.x, a.y - b.y) < 1e-7;
const keyFor = cell => `${cell.x}:${cell.y}`;
const validPoint = point => point && Number.isFinite(point.x) && Number.isFinite(point.y);
const boundedPoint = (point, document) => {
    const bounds = documentBounds(document);
    return { x: Math.max(0, Math.min(bounds.width, point.x)), y: Math.max(0, Math.min(bounds.height, point.y)) };
};

export function createFloorPainter({ getDocument, getOptions, onPreview, onCommit, onCancel, onError }) {
    let gesture;
    function metadata(current) {
        return { mode: current.options.mode, vertices: current.vertices.map(point => ({ ...point })),
            cursor: { ...current.point }, invalid: current.invalid, changed: current.changed,
            operation: current.options.operation, shape: current.options.shape, anchor: current.options.anchor,
            size: current.options.size, snap: current.options.snap !== false, editingMode: current.options.editingMode };
    }
    function preview() {
        const current = gesture;
        if (!current) return;
        const { before, options, start, point } = current;
        if (options.snap === false) {
            const candidate = clone(before);
            let result;
            if (options.mode === 'fill') result = fillFloorShape(candidate, start, { ...options, choices: current.choices });
            else {
                if (options.mode === 'brush' && !samePoint(current.path.at(-1), point)) current.path.push({ ...point });
                const points = options.mode === 'brush' ? current.path : [...current.vertices];
                if (options.mode === 'polygon' && !samePoint(points.at(-1), point)) points.push(point);
                try {
                    const contours = floorFreeContours(before, { ...options, start, end: point, points });
                    result = applyFloorContours(candidate, contours, { ...options, choices: current.choices });
                } catch (cause) {
                    if (!(cause instanceof RangeError) || cause.message !== 'The map floor shapes are too complex.') throw cause;
                    result = { ok: false, changed: false, refs: [], error: cause.message };
                }
            }
            current.candidate = candidate; current.invalid = !result.ok; current.invalidReason = result.error;
            current.changed = result.changed; current.refs = result.refs;
            onPreview?.(candidate, metadata(current)); return;
        }
        let cells;
        if (options.mode === 'brush') {
            for (const cell of floorBrushCells(before, current.last, point, options.size, options)) current.cells.set(keyFor(cell), cell);
            current.last = { ...point }; cells = [...current.cells.values()];
        } else if (options.mode === 'rectangle') cells = floorRectangleCells(before, start, point, options.size);
        else if (options.mode === 'circle') cells = floorCircleCells(before, start, point);
        else if (options.mode === 'fill') {
            current.fillCells ??= floodFloorCells(before, start, { layerId: options.layerId });
            cells = current.fillCells;
        } else {
            const points = [...current.vertices];
            if (!samePoint(points.at(-1), point)) points.push(point);
            cells = floorPolygonCells(before, points);
        }
        const candidate = clone(before);
        if (options.operation === 'erase') {
            const result = eraseFloorCells(candidate, cells, { ...options, fragmentIds: current.fragmentIds });
            current.invalid = !result.ok; current.invalidReason = result.error;
        } else {
            let error;
            current.invalid = cells.length > 0 && !paintFloorCells(candidate, cells,
                { ...options, choices: current.choices, fragmentIds: current.fragmentIds, onError: message => { error = message; } });
            current.invalidReason = current.invalid ? error || 'This map has reached the object limit.' : undefined;
        }
        current.candidate = candidate;
        current.changed = !current.invalid && JSON.stringify(candidate.floors) !== JSON.stringify(before.floors);
        current.refs = current.invalid || options.operation === 'erase' ? [] : [...new Set(cells.map(cell => current.choices.get(keyFor(cell))?.id)
            .filter(Boolean))].map(id => ({ kind: 'floors', id }));
        onPreview?.(candidate, metadata(current));
    }
    function reject(message) {
        gesture = undefined; onError?.(message); onCancel?.(); return false;
    }
    function commit() {
        if (!gesture) return false;
        if (gesture.invalid) return reject(gesture.invalidReason || 'This map has reached the object limit.');
        const completed = gesture; gesture = undefined;
        if (!completed.changed) { onCancel?.(); return false; }
        onCommit?.(completed.candidate, completed.refs); return true;
    }
    return {
        get active() { return Boolean(gesture); },
        get polygon() { return gesture?.options.mode === 'polygon'; },
        start(point) {
            if (!validPoint(point)) return false;
            point = boundedPoint(point, gesture?.before || getDocument());
            if (gesture) {
                if (gesture.options.mode !== 'polygon') return false;
                if (!samePoint(gesture.vertices.at(-1), point)) gesture.vertices.push({ ...point });
                gesture.point = { ...point }; preview(); return false;
            }
            const options = clone(getOptions());
            options.editingMode ??= documentEditingMode(getDocument());
            if (!['tiles', 'paint'].includes(options.editingMode)) { onError?.('Invalid map editing mode.'); return false; }
            if (options.editingMode === 'paint') options.snap = false;
            options.operation ||= 'paint'; options.shape ||= 'square'; options.anchor ||= options.shape === 'circle' ? 'center' : 'corner';
            if (!['brush', 'rectangle', 'circle', 'polygon', 'fill'].includes(options.mode)
                || !['paint', 'erase'].includes(options.operation) || !['square', 'circle'].includes(options.shape)
                || !['corner', 'center'].includes(options.anchor)) return false;
            const before = clone(getDocument()), layer = before.layers?.find(value => value.id === options.layerId);
            if (!layer || layer.locked || layer.visible === false) {
                onError?.('Choose a visible, unlocked layer before painting.'); return false;
            }
            gesture = { before, options, start: { ...point }, point: { ...point }, last: { ...point },
                vertices: options.mode === 'polygon' ? [{ ...point }] : [], path: [{ ...point }], cells: new Map(), choices: new Map(),
                fragmentIds: new Map(), candidate: null, refs: [], invalid: false, changed: false };
            preview(); return options.mode !== 'polygon';
        },
        move(point) {
            if (!gesture || !validPoint(point)) return;
            gesture.point = boundedPoint(point, gesture.before); preview();
        },
        end(point) {
            if (!gesture || gesture.options.mode === 'polygon') return false;
            if (validPoint(point)) { gesture.point = boundedPoint(point, gesture.before); preview(); }
            return commit();
        },
        finish() {
            if (!gesture || gesture.options.mode !== 'polygon') return false;
            if (gesture.vertices.length < 3) {
                onError?.('Add at least three points to finish the polygon.'); return false;
            }
            gesture.point = { ...gesture.vertices.at(-1) }; preview(); return commit();
        },
        cancel() {
            if (!gesture) return false;
            gesture = undefined; onCancel?.(); return true;
        },
    };
}
