/** Editable wall nodes; the workspace owns the document, camera and undo history. */
import { clone, round, snapWallSegment } from './model.js';
import { wallNodes, moveWallNode, splitWall, extendWall, snapWallPoint } from './wall-edit.js';

const namespace = 'http://www.w3.org/2000/svg';
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
const endpointNumber = value => value === 'start' ? 1 : 2;
const endpointPoint = (wall, endpoint) => ({ x: wall[`x${endpoint}`], y: wall[`y${endpoint}`] });
const svg = (name, attrs) => {
    const element = document.createElementNS(namespace, name);
    for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, value);
    return element;
};

export function createWallControls({ getDocument, setDocument, getScale, getSnap, getSelection, enabled,
    onPreview, onCommit, onError, onArmed, onCancel, onFocus, t, maxObjects = () => 2000 }) {
    let gesture;
    const selectedWall = () => {
        const refs = getSelection();
        return refs.length === 1 && refs[0].kind === 'walls'
            ? getDocument().walls.find(wall => wall.id === refs[0].id) : null;
    };
    const options = () => ({ maxObjects: maxObjects() });
    function nodeAt(document, wall, endpoint) {
        return wallNodes(document, { layerId: wall.layerId }).find(node =>
            node.ends.some(end => end.wallId === wall.id && end.endpoint === endpoint));
    }
    function begin(action, wall, endpoint, point) {
        const before = clone(getDocument()), source = clone(before), id = crypto.randomUUID();
        let node = nodeAt(source, wall, endpoint);
        if (action === 'split') {
            const midpoint = { x: (wall.x1 + wall.x2) / 2, y: (wall.y1 + wall.y2) / 2 };
            const result = splitWall(source, wall.id, midpoint, { ...options(), makeId: () => id });
            if (!result.ok) { onError(result.error); return false; }
            if (!result.changed) return false;
            node = nodeAt(source, source.walls.find(item => item.id === wall.id), 2);
        }
        if (!node) return false;
        gesture = { action, wallId: wall.id, endpoint, layerId: wall.layerId, before, source, node,
            down: point, point: { x: node.x, y: node.y }, id, fragmentIds: new Map(), moved: false, armed: false };
        if (action === 'split') { setDocument(clone(source)); onPreview(); }
        return true;
    }
    function move(point) {
        if (!gesture) return;
        const current = gesture;
        current.moved ||= distance(point, current.down) > 4 / getScale();
        if (!current.moved && !current.armed) return;
        let next = getSnap() ? { x: Math.round(point.x), y: Math.round(point.y) } : { x: round(point.x), y: round(point.y) };
        if (current.action === 'extend') {
            const segment = snapWallSegment(current.before, current.node, point, { snap: getSnap() });
            next = { x: segment.x2, y: segment.y2 };
            if (getSnap()) {
                if (Math.abs(point.x - current.node.x) >= Math.abs(point.y - current.node.y)) next.y = current.node.y;
                else next.x = current.node.x;
            }
        }
        const snapping = snapWallPoint(current.source, next, { layerId: current.layerId,
            excludeIds: current.node.ends.map(end => end.wallId), tolerance: Math.min(.35, 10 / getScale()) });
        if (snapping.snapped) next = { x: snapping.x, y: snapping.y };
        const candidate = clone(current.source);
        const result = current.action === 'extend'
            ? extendWall(candidate, current.wallId, current.endpoint, next,
                { ...options(), id: current.id, fragmentIds: current.fragmentIds })
            : moveWallNode(candidate, current.node.key, next, { layerId: current.layerId });
        current.point = next; current.result = result;
        setDocument(result.ok ? candidate : clone(current.source));
        onPreview();
    }
    function finish() {
        if (!gesture) return false;
        const current = gesture;
        if (current.action === 'extend' && !current.moved && !current.armed) {
            current.armed = true; current.down = { ...current.point }; onArmed?.(); onPreview(); return false;
        }
        gesture = undefined;
        if (current.result && !current.result.ok) {
            setDocument(current.before); onError(current.result.error); onPreview(); return false;
        }
        const changed = JSON.stringify(getDocument().walls) !== JSON.stringify(current.before.walls);
        if (changed) onCommit(current.action === 'extend'
            ? current.result?.refs.filter(ref => ref.id === current.id).concat(current.result.refs.filter(ref => ref.id !== current.id))
            : [{ kind: 'walls', id: current.wallId }]);
        else { setDocument(current.before); onCancel?.(); onPreview(); }
        return changed;
    }
    function cancel() {
        if (!gesture) return false;
        const before = gesture.before; gesture = undefined;
        setDocument(before); onCancel?.(); onPreview(); return true;
    }
    function start(point, event) {
        if (!enabled()) return null;
        if (gesture?.armed) { move(point); return true; }
        const control = event.target.closest?.('[data-builder-wall-control]');
        if (!control) return null;
        const wall = selectedWall();
        if (!wall || wall.id !== control.dataset.wallId) return false;
        const action = control.hasAttribute('data-builder-wall-split') ? 'split'
            : control.hasAttribute('data-builder-wall-extend') ? 'extend' : 'move';
        return begin(action, wall, endpointNumber(control.dataset.wallEndpoint || control.dataset.builderWallExtend), point);
    }
    function control(container, wall, point, attributes, label, plus = false) {
        const scale = getScale(), group = svg('g', { ...attributes, 'data-builder-wall-control': '',
            'data-wall-id': wall.id, class: 'map-builder__wall-control', role: 'button', tabindex: 0,
            'aria-label': t(label), transform: `translate(${point.x} ${point.y}) scale(${1 / scale})` });
        const title = svg('title', {}); title.textContent = t(label); group.append(title);
        group.append(svg('circle', { r: plus ? 12 : 11, class: 'map-builder__wall-hit' }));
        group.append(svg('circle', { r: plus ? 8 : 5, class: plus ? 'map-builder__wall-add' : 'map-builder__wall-node' }));
        if (plus) group.append(svg('path', { d: 'M-4 0H4M0-4V4', class: 'map-builder__wall-plus' }));
        container.append(group);
    }
    function render(container) {
        if (!enabled()) return;
        const wall = selectedWall(); if (!wall) return;
        const source = getDocument(), nodes = wallNodes(source, { layerId: wall.layerId });
        const size = Math.hypot(wall.x2 - wall.x1, wall.y2 - wall.y1), scale = getScale();
        if (!size || !scale) return;
        const normal = { x: -(wall.y2 - wall.y1) / size, y: (wall.x2 - wall.x1) / size };
        for (const endpoint of [1, 2]) {
            const point = endpointPoint(wall, endpoint), name = endpoint === 1 ? 'start' : 'end';
            const node = nodes.find(value => value.ends.some(end => end.wallId === wall.id && end.endpoint === endpoint));
            if (!node) continue;
            control(container, wall, point, { 'data-builder-wall-handle': '', 'data-wall-endpoint': name },
                node.ends.length > 1 ? 'Move connected wall node' : 'Move wall endpoint');
            if (size * scale >= 48) control(container, wall,
                { x: point.x + normal.x * 26 / scale, y: point.y + normal.y * 26 / scale },
                { 'data-builder-wall-extend': name, 'data-wall-endpoint': name },
                endpoint === 1 ? 'Extend wall from start' : 'Extend wall from end', true);
        }
        if (size >= .2 && size * scale >= 64) control(container, wall,
            { x: (wall.x1 + wall.x2) / 2, y: (wall.y1 + wall.y2) / 2 }, { 'data-builder-wall-split': '' }, 'Add wall node', true);
        if (gesture?.action === 'extend') container.append(svg('circle', { cx: gesture.point.x, cy: gesture.point.y,
            r: 5 / scale, class: 'map-builder__wall-node', 'vector-effect': 'non-scaling-stroke',
            'data-builder-wall-node-preview': '' }));
    }
    function keydown(event) {
        if (!enabled()) return;
        const control = event.target.closest?.('[data-builder-wall-control]');
        if (event.key === 'Escape' && gesture) { event.preventDefault(); event.stopImmediatePropagation(); cancel(); return; }
        if (event.key === 'Enter' && gesture?.armed) { event.preventDefault(); event.stopImmediatePropagation(); finish(); return; }
        if (!control || !['Enter', ' ', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
        event.preventDefault(); event.stopImmediatePropagation();
        const wall = selectedWall(); if (!wall) return;
        const endpoint = endpointNumber(control.dataset.wallEndpoint || control.dataset.builderWallExtend);
        const point = endpointPoint(wall, endpoint);
        if (event.key === 'Enter' || event.key === ' ') {
            if (control.hasAttribute('data-builder-wall-split')) { if (begin('split', wall, 1, point)) { finish(); onFocus?.(); } }
            else if (control.hasAttribute('data-builder-wall-extend')) {
                if (begin('extend', wall, endpoint, point)) { gesture.armed = true; onArmed?.(); onPreview(); onFocus?.(); }
            }
            return;
        }
        if (!control.hasAttribute('data-builder-wall-handle')) return;
        const node = nodeAt(getDocument(), wall, endpoint), step = getSnap() ? 1 : event.shiftKey ? 1 : .1;
        const next = { x: point.x + (event.key === 'ArrowLeft' ? -step : event.key === 'ArrowRight' ? step : 0),
            y: point.y + (event.key === 'ArrowUp' ? -step : event.key === 'ArrowDown' ? step : 0) };
        const result = moveWallNode(getDocument(), node.key, next, { layerId: wall.layerId });
        if (!result.ok) onError(result.error);
        else if (result.changed) {
            const container = control.parentElement;
            onCommit([{ kind: 'walls', id: wall.id }]);
            const replacement = [...container?.querySelectorAll('[data-builder-wall-handle]') || []]
                .find(element => element.dataset.wallId === wall.id && element.dataset.wallEndpoint === control.dataset.wallEndpoint);
            replacement?.focus();
        }
    }
    return { start, move, end(point) { if (gesture) { move(point); return finish(); } return false; }, cancel, render, keydown,
        get active() { return Boolean(gesture); }, get armed() { return Boolean(gesture?.armed); } };
}
