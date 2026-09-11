import { text as gwText } from '../../../shared/config/i18n/text.js';
import { wallPresets, wallPayload, hitWall, hitNode, snap, enclosed } from '../model/walls.js';
// Explicit lifecycle and repainting; these holders are plain local values.
const box = (value) => ({ value });
const derive = (read) => ({ get value() { return read(); } });
export function wallController(element, options) {
    const props = { ...options.props };
    const emit = options.emit;
    const reader = { state: () => options.read() };
    const writer = { command: (_a, _b, area, action, data) => options.command(area, action, data) };
    const root = box(), selected = box([]), clipboard = box([]), choice = box('normal'), picker = box(false), editing = box(), busy = box(false), error = box(''), clearConfirm = box(false);
    const context = box(), start = box(), cursor = box({ x: 0, y: 0 }), offset = box({ x: 0, y: 0 }), marquee = box();
    const preset = derive(() => wallPresets.find(p => p.id === choice.value));
    let drag, closed = false;
    let queue = Promise.resolve();
    const scope = { container: props.containerId, block: props.blockId };
    const abort = new AbortController();
    const rendered = derive(() => props.state.walls.map(w => {
        if (drag?.type === 'node' && drag.node) {
            const n = drag.node;
            return { ...w, ...(!drag.detach || w.id === n.wall.id ? Object.fromEntries([1, 2].filter(i => (!drag?.detach || i === n.endpoint) && Math.hypot(w[`x${i}`] - n.x, w[`y${i}`] - n.y) <= 1).flatMap(i => [[`x${i}`, cursor.value.x], [`y${i}`, cursor.value.y]])) : {}) };
        }
        return selected.value.includes(w.id) ? { ...w, x1: w.x1 + offset.value.x, y1: w.y1 + offset.value.y, x2: w.x2 + offset.value.x, y2: w.y2 + offset.value.y } : w;
    }));
    async function run(area, action, data, after) {
        queue = queue.then(async () => {
            if (closed)
                return;
            busy.value = true;
            error.value = '';
            options.repaint();
            try {
                const result = await writer.command(scope.container, scope.block, area, action, data);
                if (closed)
                    return;
                const state = await reader.state(scope.container, scope.block);
                if (!closed) {
                    emit('changed', state);
                    after?.(result);
                }
            }
            catch {
                if (!closed)
                    error.value = gwText('Could not save the wall. Check the data and try again.');
            }
            finally {
                if (!closed) {
                    busy.value = false;
                    offset.value = { x: 0, y: 0 };
                    options.repaint();
                }
            }
        });
        return queue;
    }
    function point(e) { const r = root.value.getBoundingClientRect(); return { x: (e.clientX - r.left - props.viewport.x) / props.viewport.scale, y: (e.clientY - r.top - props.viewport.y) / props.viewport.scale }; }
    function target(e) {
        const p = point(e);
        if (e.ctrlKey || e.metaKey)
            return p;
        return snap(p, props.state.walls, 10 / props.viewport.scale, props.cell, e.shiftKey, drag?.type === 'node' ? drag.node : undefined);
    }
    function action(id) {
        const was = picker.value;
        cancel();
        editing.value = undefined;
        context.value = undefined;
        picker.value = id === 'wall' && !was;
        if (id === 'clear-walls')
            clearConfirm.value = true;
    }
    function choose(id) { choice.value = id; picker.value = false; emit('tool', 'wall'); }
    function stop(e) { e.preventDefault(); e.stopPropagation(); }
    function down(e) {
        if (e.button === 2 && hitWall(point(e), props.state.walls, 10 / props.viewport.scale)) {
            stop(e);
            return;
        }
        if (e.button !== 0 || props.tool === 'measure')
            return;
        stop(e);
        context.value = undefined;
        if (busy.value || picker.value || editing.value || clearConfirm.value)
            return;
        const p = point(e), node = hitNode(p, props.state.walls, 8 / props.viewport.scale), hit = hitWall(p, props.state.walls, 8 / props.viewport.scale);
        let type = 'draw';
        if (!start.value && node) {
            type = 'node';
            cursor.value = { x: node.x, y: node.y };
        }
        else if (!start.value && hit) {
            type = 'move';
            if (!selected.value.includes(hit.id))
                selected.value = e.shiftKey ? [...selected.value, hit.id] : [hit.id];
            else if (e.shiftKey) {
                selected.value = selected.value.filter(id => id !== hit.id);
                return;
            }
        }
        else if (props.tool === 'select') {
            type = 'marquee';
            marquee.value = { from: p, to: p };
        }
        else if (start.value) {
            void create(target(e), !e.altKey);
            return;
        }
        else {
            start.value = target(e);
            cursor.value = start.value;
        }
        drag = { pointer: e.pointerId, type, from: p, to: p, node, detach: e.shiftKey, original: [...selected.value], additive: e.shiftKey };
        if (type === 'marquee' && !e.shiftKey)
            selected.value = [];
        root.value?.setPointerCapture(e.pointerId);
    }
    function move(e) {
        cursor.value = target(e);
        if (!drag) {
            return;
        }
        if (drag.pointer !== e.pointerId)
            return;
        stop(e);
        drag.to = point(e);
        if (drag.type === 'move')
            offset.value = { x: drag.to.x - drag.from.x, y: drag.to.y - drag.from.y };
        if (drag.type === 'marquee') {
            marquee.value = { from: drag.from, to: drag.to };
            selected.value = [...new Set([...(drag.additive ? drag.original : []), ...props.state.walls.filter(w => enclosed(w, drag.from, drag.to)).map(w => w.id)])];
        }
    }
    function up(e) {
        if (!drag || drag.pointer !== e.pointerId)
            return;
        stop(e);
        const destination = target(e), d = drag;
        drag = undefined;
        root.value?.releasePointerCapture(e.pointerId);
        marquee.value = undefined;
        const distance = Math.hypot(d.to.x - d.from.x, d.to.y - d.from.y) * props.viewport.scale;
        if (d.type === 'draw' && distance >= 5)
            void create(target(e), !e.altKey);
        if (d.type === 'move' && distance >= 3)
            void run('wall-selection', 'move', { wall_ids: [...selected.value], dx: offset.value.x, dy: offset.value.y });
        else
            offset.value = { x: 0, y: 0 };
        if (d.type === 'node' && d.node) {
            if (distance < 3) {
                if (['wall', 'door'].includes(props.tool))
                    start.value = { x: d.node.x, y: d.node.y };
                return;
            }
            const p = destination;
            void run('walls', d.detach ? 'move-endpoint' : 'move-node', d.detach ? { wall_id: d.node.wall.id, endpoint: d.node.endpoint, to_x: p.x, to_y: p.y } : { from_x: d.node.x, from_y: d.node.y, to_x: p.x, to_y: p.y });
        }
    }
    async function create(end, chain) {
        if (!start.value || Math.hypot(end.x - start.value.x, end.y - start.value.y) < 2)
            return;
        const from = start.value, kind = props.tool === 'door' ? 'door' : 'wall';
        start.value = kind === 'wall' && chain ? end : undefined;
        const p = preset.value;
        await run('walls', 'create', { kind, x1: from.x, y1: from.y, x2: end.x, y2: end.y, ...(kind === 'wall' ? { presentation: p.presentation, behavior: p.behavior, vertical: p.vertical } : {}) }, r => {
            selected.value = [r.wall.id];
            if (kind === 'wall' && p.vertical) {
                editing.value = r.wall;
                start.value = undefined;
            }
        });
        if (error.value)
            start.value = undefined;
    }
    function cancel() {
        if (drag && root.value?.hasPointerCapture(drag.pointer))
            root.value.releasePointerCapture(drag.pointer);
        drag = undefined;
        start.value = undefined;
        marquee.value = undefined;
        offset.value = { x: 0, y: 0 };
    }
    function menu(e) {
        const p = point(e), w = hitWall(p, props.state.walls, 10 / props.viewport.scale);
        if (!w)
            return;
        stop(e);
        start.value = undefined;
        if (!selected.value.includes(w.id))
            selected.value = [w.id];
        context.value = { x: e.clientX, y: e.clientY, world: p, wall: w };
    }
    function copy() { clipboard.value = props.state.walls.filter(w => selected.value.includes(w.id)).map(w => ({ ...w })); context.value = undefined; }
    function paste(p = cursor.value) {
        if (!clipboard.value.length)
            return;
        const minX = Math.min(...clipboard.value.flatMap(w => [w.x1, w.x2])), minY = Math.min(...clipboard.value.flatMap(w => [w.y1, w.y2]));
        void run('wall-selection', 'paste', { walls: clipboard.value.map(w => ({ ...wallPayload(w), door_state: w.door_state ?? 'closed', discovered: Boolean(w.discovered), x1: w.x1 + p.x - minX, y1: w.y1 + p.y - minY, x2: w.x2 + p.x - minX, y2: w.y2 + p.y - minY })) }, r => selected.value = r.walls);
        context.value = undefined;
    }
    function remove() {
        if (!selected.value.length)
            return;
        void run('wall-selection', 'delete', { wall_ids: [...selected.value] }, () => { selected.value = []; editing.value = undefined; });
        context.value = undefined;
    }
    function split(w, p) {
        if (w.kind === 'door')
            return;
        context.value = undefined;
        cancel();
        void run('walls', 'split', { wall_id: w.id, x: p.x, y: p.y });
    }
    function operate(w, lock = false) { context.value = undefined; void run('walls', 'door', { wall_id: w.id, door_state: lock ? (w.door_state === 'locked' ? 'closed' : 'locked') : (w.door_state === 'open' ? 'closed' : 'open') }); }
    function double(e) {
        const p = point(e), w = hitWall(p, props.state.walls, 8 / props.viewport.scale);
        if (!w)
            return;
        stop(e);
        cancel();
        if (w.kind === 'door') {
            operate(w);
            return;
        }
        if (!hitNode(p, [w], 8 / props.viewport.scale))
            split(w, p);
    }
    function edit(w) { editing.value = { ...w }; context.value = undefined; cancel(); }
    function key(e) {
        if (props.tool === 'managed')
            return;
        if (e.target instanceof Element && e.target.closest('input,textarea,select,[contenteditable=true],[role=dialog],.house-menu'))
            return;
        if (e.key === 'Escape') {
            cancel();
            context.value = undefined;
            picker.value = false;
            clearConfirm.value = false;
            return;
        }
        if (busy.value)
            return;
        const mod = e.ctrlKey || e.metaKey;
        if (mod && e.key.toLowerCase() === 'c') {
            stop(e);
            copy();
        }
        if (mod && e.key.toLowerCase() === 'v') {
            stop(e);
            paste();
        }
        if (['Delete', 'Backspace'].includes(e.key) && selected.value.length) {
            stop(e);
            remove();
        }
    }
    root.value = element;
    const repaint = () => options.repaint();
    const events = { pointerdown: down, pointermove: move, pointerup: up, pointercancel: cancel, contextmenu: menu, dblclick: double };
    const listeners = Object.entries(events).map(([name, fn]) => { const handler = (e) => { fn(e); repaint(); }; element.addEventListener(name, handler); return [name, handler]; });
    const keyboard = (e) => { key(e); repaint(); };
    window.addEventListener('keydown', keyboard);
    return { get view() { return { selected: selected.value, clipboard: clipboard.value, choice: choice.value, picker: picker.value, editing: editing.value, busy: busy.value, error: error.value, clearConfirm: clearConfirm.value, context: context.value, start: start.value, cursor: cursor.value, preset: preset.value, rendered: rendered.value, marquee: marquee.value }; },
        call(name, ...args) { const methods = { action, choose, edit, copy, paste, remove, split, operate, double, cancel, run, closePicker: () => picker.value = false, closeEditor: () => editing.value = undefined, closeMenu: () => context.value = undefined, closeClear: () => clearConfirm.value = false }; const result = methods[name](...args); repaint(); return result; },
        update(next) { if (next.tool !== undefined && next.tool !== props.tool) {
            cancel();
            context.value = undefined;
        } Object.assign(props, next); repaint(); },
        destroy() { closed = true; abort.abort(); cancel(); for (const [name, fn] of listeners)
            element.removeEventListener(name, fn); window.removeEventListener('keydown', keyboard); } };
}
