import { text as gwText } from '../../../shared/config/i18n/text.js';
import DirectoryContextMenu from '../../../shared/ui/directory/DirectoryContextMenu.native.js';
import { bounds, hit, path, translated } from '../model/drawing.js';
const PhCursor = "PhCursor";
const PhPencilSimple = "PhPencilSimple";
const PhLineSegment = "PhLineSegment";
const PhArrowUpRight = "PhArrowUpRight";
const PhRectangle = "PhRectangle";
const PhCircle = "PhCircle";
const PhTextT = "PhTextT";
const PhEraser = "PhEraser";
const PhArrowCounterClockwise = "PhArrowCounterClockwise";
const PhArrowClockwise = "PhArrowClockwise";
const PhTrash = "PhTrash";
const PhCopy = "PhCopy";
const PhClipboard = "PhClipboard";
const PhX = "PhX";
import { widget } from '../../../native/widget.js';
export default widget([{ "tag": "svg", "attrs": { "ref": "root", "class": "drawing-workspace" }, "bind": { "class": "({ 'drawing-workspace--busy': busy })" }, "events": [{ "event": "pointerdown", "code": "down;", "mods": [] }, { "event": "pointermove", "code": "move;", "mods": [] }, { "event": "pointerup", "code": "up;", "mods": [] }, { "event": "pointercancel", "code": "cancel;", "mods": [] }, { "event": "contextmenu", "code": "menu;", "mods": [] }], "children": [{ "tag": "g", "attrs": {}, "bind": { "transform": "(`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`)" }, "events": [], "children": [{ "tag": "g", "attrs": {}, "bind": { "key": "(row.id)", "opacity": "(row.opacity)", "transform": "(`rotate(${row.rotation ?? 0} ${row.points[0].x} ${row.points[0].y})`)" }, "events": [{ "event": "dblclick", "code": "edit($event, row);", "mods": [] }], "children": [{ "tag": "text", "attrs": { "dominant-baseline": "text-before-edge", "font-family": "sans-serif", "style": "white-space:pre" }, "bind": { "x": "(row.points[0].x)", "y": "(row.points[0].y)", "fill": "(row.color)", "font-size": "(row.fontSize)" }, "events": [], "children": [{ "value": "(row.text)" }], "when": "(row.kind === 'text')" }, { "tag": "path", "attrs": { "stroke-linecap": "round", "stroke-linejoin": "round" }, "bind": { "d": "(path(row))", "stroke": "(row.color)", "stroke-width": "(row.width)", "fill": "(['rect', 'ellipse'].includes(row.kind) ? row.fill : 'none')" }, "events": [], "children": [], "otherwise": true }, { "tag": "rect", "attrs": { "fill": "none", "stroke": "#e1b466" }, "bind": { "stroke-width": "(1 / viewport.scale)", "stroke-dasharray": "(`${5 / viewport.scale} ${3 / viewport.scale}`)" }, "events": [], "children": [], "when": "(selected.includes(row.id))", "spread": "(bounds(row))" }], "each": { "names": ["row"], "value": "(visible)" } }, { "tag": "rect", "attrs": { "fill": "#e1b46622", "stroke": "#e1b466" }, "bind": { "x": "(Math.min(marquee.a.x, marquee.b.x))", "y": "(Math.min(marquee.a.y, marquee.b.y))", "width": "(Math.abs(marquee.b.x - marquee.a.x))", "height": "(Math.abs(marquee.b.y - marquee.a.y))", "stroke-width": "(1 / viewport.scale)" }, "events": [], "children": [], "when": "(marquee)" }] }] }, { "tag": "Teleport", "attrs": { "to": "body" }, "bind": {}, "events": [], "children": [{ "tag": "section", "attrs": { "class": "drawing-paint", "aria-label": "Mini Paint" }, "bind": {}, "events": [{ "event": "pointerdown", "code": "", "mods": ["stop"] }, { "event": "keydown", "code": "", "mods": ["stop"] }], "children": [{ "tag": "header", "attrs": { "class": "drawing-paint__header" }, "bind": {}, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "PhPencilSimple", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "text": "Mini Paint " }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(audience === 'gm' ? gwText('GM only') : gwText('Table'))" }] }] }, { "tag": "button", "attrs": {}, "bind": { "aria-label": "(gwText('Close drawing'))", "title": "(gwText('Close drawing'))" }, "events": [{ "event": "click", "code": "emit('close');", "mods": [] }], "children": [{ "tag": "PhX", "attrs": {}, "bind": {}, "events": [], "children": [] }] }] }, { "tag": "fieldset", "attrs": { "class": "drawing-paint__body" }, "bind": { "disabled": "(busy)" }, "events": [], "children": [{ "tag": "div", "attrs": { "class": "drawing-paint__tools" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "key": "(item.id)", "title": "(item.label)", "aria-label": "(item.label)", "aria-pressed": "(tool === item.id)" }, "events": [{ "event": "click", "code": "choose(item.id);", "mods": [] }], "children": [{ "tag": "component", "attrs": { "weight": "duotone" }, "bind": { "is": "(item.icon)" }, "events": [], "children": [] }], "each": { "names": ["item"], "value": "(tools)" } }] }, { "tag": "div", "attrs": { "class": "drawing-paint__palette" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "key": "(swatch)", "style": "({ background: swatch })", "aria-label": "(gwText('Color {0}', swatch))", "aria-pressed": "(color === swatch)" }, "events": [{ "event": "click", "code": "color = swatch;", "mods": [] }], "children": [], "each": { "names": ["swatch"], "value": "(palette)" } }, { "tag": "label", "attrs": {}, "bind": { "title": "(gwText('Custom color'))" }, "events": [], "children": [{ "tag": "input", "attrs": { "type": "color" }, "bind": { "aria-label": "(gwText('Stroke color'))" }, "events": [], "children": [], "model": { "path": "(color)", "mods": [] } }] }] }, { "tag": "div", "attrs": { "class": "drawing-paint__settings" }, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Stroke '))" }, { "tag": "input", "attrs": { "type": "range", "min": "1", "max": "64" }, "bind": {}, "events": [], "children": [], "model": { "path": "(width)", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(width)" }, { "text": " px" }] }] }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Opacity '))" }, { "tag": "input", "attrs": { "type": "range", "min": "0.05", "max": "1", "step": "0.05" }, "bind": {}, "events": [], "children": [], "model": { "path": "(opacity)", "mods": ["number"] } }, { "tag": "output", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(Math.round(opacity * 100))" }, { "text": "%" }] }] }] }, { "tag": "div", "attrs": { "class": "drawing-paint__fill" }, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "checkbox" }, "bind": {}, "events": [], "children": [], "model": { "path": "(filled)", "mods": [] } }, { "value": "(gwText('Fill shapes'))" }] }, { "tag": "input", "attrs": { "type": "color" }, "bind": { "aria-label": "(gwText('Fill color'))", "disabled": "(!filled)" }, "events": [], "children": [], "model": { "path": "(fill)", "mods": [] } }] }, { "tag": "div", "attrs": { "class": "drawing-paint__text" }, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "maxlength": "1000" }, "bind": { "placeholder": "(gwText('Type and click the map'))", "aria-label": "(gwText('Drawing text'))" }, "events": [], "children": [], "model": { "path": "(text)", "mods": [] } }, { "tag": "input", "attrs": { "type": "number", "min": "8", "max": "144" }, "bind": { "aria-label": "(gwText('Text size'))" }, "events": [], "children": [], "model": { "path": "(fontSize)", "mods": ["number"] } }], "when": "(tool === 'text' || rows.some(r => selected.includes(r.id) && r.kind === 'text'))" }, { "tag": "button", "attrs": { "class": "drawing-paint__apply" }, "bind": {}, "events": [{ "event": "click", "code": "styleSelection;", "mods": [] }], "children": [{ "value": "(gwText('Apply style to selection ('))" }, { "value": "(selected.length)" }, { "text": ")" }], "when": "(selected.length)" }, { "tag": "div", "attrs": { "class": "drawing-paint__actions" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "disabled": "(!undo.length)", "title": "(gwText('Undo (Ctrl+Z)'))", "aria-label": "(gwText('Undo'))" }, "events": [{ "event": "click", "code": "history('undo');", "mods": [] }], "children": [{ "tag": "PhArrowCounterClockwise", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "(!redo.length)", "title": "(gwText('Redo (Ctrl+Shift+Z)'))", "aria-label": "(gwText('Redo'))" }, "events": [{ "event": "click", "code": "history('redo');", "mods": [] }], "children": [{ "tag": "PhArrowClockwise", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "(!selected.length)", "title": "(gwText('Copy selection'))", "aria-label": "(gwText('Copy selection'))" }, "events": [{ "event": "click", "code": "copy;", "mods": [] }], "children": [{ "tag": "PhCopy", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": {}, "bind": { "title": "(gwText('Paste copy'))", "aria-label": "(gwText('Paste copy'))" }, "events": [{ "event": "click", "code": "paste;", "mods": [] }], "children": [{ "tag": "PhClipboard", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "(!selected.length)", "title": "(gwText('Delete selection'))", "aria-label": "(gwText('Delete selection'))" }, "events": [{ "event": "click", "code": "remove;", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }] }, { "tag": "button", "attrs": { "class": "drawing-paint__clear" }, "bind": {}, "events": [{ "event": "click", "code": "clearConfirm ? save(rows.filter(r => !editable(r))) : clearConfirm = true;", "mods": [] }], "children": [{ "value": "(clearConfirm ? gwText('Confirm clearing') : gwText('Clear layer'))" }] }] }] }, { "tag": "p", "attrs": { "class": "drawing-paint__hint" }, "bind": { "role": "(error ? 'alert' : 'status')" }, "events": [], "children": [{ "value": "(error || (busy ? gwText('Saving…') : tool === 'erase' ? gwText('Drag to erase entire strokes.') : tool === 'select' ? gwText('Drag to move or select. Shift adds to the selection.') : tool === 'text' ? gwText('Type text and click to place it.') : gwText('Drag to draw. Shift constrains shapes and angles.')))" }] }] }, { "tag": "DirectoryContextMenu", "attrs": {}, "bind": { "x": "(context.x)", "y": "(context.y)" }, "events": [{ "event": "close", "code": "context = undefined;", "mods": [] }], "children": [{ "tag": "button", "attrs": {}, "bind": {}, "events": [{ "event": "click", "code": "copy;", "mods": [] }], "children": [{ "tag": "PhCopy", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Copy'))" }] }, { "tag": "button", "attrs": {}, "bind": {}, "events": [{ "event": "click", "code": "paste;", "mods": [] }], "children": [{ "tag": "PhClipboard", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Paste'))" }] }, { "tag": "button", "attrs": {}, "bind": {}, "events": [{ "event": "click", "code": "remove;", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Delete selection'))" }] }], "when": "(context)" }] }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
    const HttpClient = options.HttpClient;
    const BlockStateApi = class {
        command(_c, _b, a, b, p) { return options.command(a, b, p); }
        state() { return options.read(); }
    };
    const props = options.props;
    const emit = options.emit;
    const abort = new AbortController(), api = new BlockStateApi(new HttpClient(undefined, () => abort.signal));
    const root = ref(), tool = ref('pen');
    const rows = ref([]), version = ref(0), selected = ref([]), draft = ref(), marquee = ref();
    const color = ref('#e1b466'), fill = ref('#e1b466'), filled = ref(false), width = ref(3), opacity = ref(1), fontSize = ref(21), text = ref('');
    const busy = ref(false), error = ref(''), clearConfirm = ref(false), context = ref();
    const undo = ref([]), redo = ref([]);
    let clipboard = [];
    let drag;
    const tools = [{ id: 'select', get label() { return gwText('Select and move'); }, icon: PhCursor }, { id: 'pen', get label() { return gwText('Brush'); }, icon: PhPencilSimple }, { id: 'line', get label() { return gwText('Line'); }, icon: PhLineSegment }, { id: 'arrow', get label() { return gwText('Arrow'); }, icon: PhArrowUpRight }, { id: 'rect', get label() { return gwText('Rectangle'); }, icon: PhRectangle }, { id: 'ellipse', get label() { return gwText('Ellipse'); }, icon: PhCircle }, { id: 'text', get label() { return gwText('Text'); }, icon: PhTextT }, { id: 'erase', get label() { return gwText('Stroke eraser'); }, icon: PhEraser }];
    const palette = ['#ffffff', '#171d23', '#e1b466', '#ef5350', '#ff9800', '#fdd835', '#66bb6a', '#26c6da', '#42a5f5', '#ab47bc'];
    const visible = computed(() => draft.value ? [...rows.value, draft.value] : rows.value);
    const editable = (r) => r.audience === props.audience;
    const copyRows = (list) => list.map(r => ({ ...r, points: r.points.map(p => ({ ...p })) }));
    function point(e) { const b = root.value.getBoundingClientRect(); return { x: (e.clientX - b.left - props.viewport.x) / props.viewport.scale, y: (e.clientY - b.top - props.viewport.y) / props.viewport.scale }; }
    function pick(p) { return [...rows.value].reverse().find(r => editable(r) && hit(r, p, 5 / props.viewport.scale)); }
    function release() { if (drag && root.value?.hasPointerCapture(drag.pointer))
        root.value.releasePointerCapture(drag.pointer); drag = undefined; draft.value = undefined; marquee.value = undefined; }
    function cancel() { if (drag)
        rows.value = drag.before; release(); }
    watch(() => props.document, doc => { if (!doc || doc.version === version.value)
        return; cancel(); rows.value = copyRows(doc.rows); version.value = doc.version; undo.value = []; redo.value = []; selected.value = []; }, { immediate: true });
    async function save(next, before = copyRows(rows.value), history = 'normal') {
        if (busy.value)
            return;
        busy.value = true;
        error.value = '';
        context.value = undefined;
        clearConfirm.value = false;
        try {
            const result = await api.command(props.containerId, props.blockId, 'drawings', 'replace', { rows: next, expected_version: version.value });
            if (abort.signal.aborted)
                return;
            rows.value = result.rows;
            version.value = result.version;
            if (history === 'normal') {
                undo.value = [...undo.value.slice(-29), before];
                redo.value = [];
            }
            else if (history === 'undo') {
                undo.value.pop();
                redo.value.push(before);
            }
            else {
                redo.value.pop();
                undo.value.push(before);
            }
            emit('refresh');
        }
        catch {
            if (!abort.signal.aborted) {
                rows.value = before;
                error.value = gwText('Could not save. The scene will refresh; try again.');
                undo.value = [];
                redo.value = [];
                emit('refresh');
            }
        }
        finally {
            if (!abort.signal.aborted)
                busy.value = false;
        }
    }
    function create(p) { return { id: crypto.randomUUID(), kind: tool.value, audience: props.audience, points: [p], color: color.value, fill: filled.value ? fill.value : 'none', width: width.value, opacity: opacity.value, fontSize: fontSize.value, text: text.value }; }
    function down(e) {
        if (e.button !== 0 || busy.value)
            return;
        e.preventDefault();
        e.stopPropagation();
        context.value = undefined;
        clearConfirm.value = false;
        const p = point(e), row = pick(p), before = copyRows(rows.value);
        if (tool.value === 'text') {
            if (!text.value.trim()) {
                error.value = gwText('Enter text in the panel before clicking the map.');
                return;
            }
            void save([...rows.value, create(p)]);
            return;
        }
        if (tool.value === 'select') {
            if (row) {
                selected.value = e.shiftKey ? (selected.value.includes(row.id) ? selected.value.filter(id => id !== row.id) : [...selected.value, row.id]) : selected.value.includes(row.id) ? selected.value : [row.id];
            }
            else {
                if (!e.shiftKey)
                    selected.value = [];
                marquee.value = { a: p, b: p };
            }
        }
        else if (tool.value === 'erase') {
            if (row)
                rows.value = rows.value.filter(r => r.id !== row.id);
        }
        else {
            selected.value = [];
            draft.value = create(p);
        }
        drag = { pointer: e.pointerId, start: p, before, mode: tool.value, ids: [...selected.value] };
        root.value?.setPointerCapture(e.pointerId);
    }
    function move(e) {
        if (!drag || drag.pointer !== e.pointerId)
            return;
        e.stopPropagation();
        let p = point(e);
        const a = drag.start;
        if (drag.mode === 'select') {
            if (marquee.value)
                marquee.value.b = p;
            else
                rows.value = drag.before.map(r => drag.ids.includes(r.id) ? translated(r, p.x - a.x, p.y - a.y) : r);
        }
        else if (drag.mode === 'erase') {
            const row = pick(p);
            if (row)
                rows.value = rows.value.filter(r => r.id !== row.id);
        }
        else if (draft.value) {
            if (draft.value.kind === 'pen') {
                const last = draft.value.points.at(-1);
                if (draft.value.points.length < 4096 && Math.hypot(p.x - last.x, p.y - last.y) >= 1 / props.viewport.scale)
                    draft.value.points.push(p);
            }
            else {
                if (e.shiftKey) {
                    const dx = p.x - a.x, dy = p.y - a.y;
                    if (['rect', 'ellipse'].includes(draft.value.kind)) {
                        const size = Math.max(Math.abs(dx), Math.abs(dy));
                        p = { x: a.x + Math.sign(dx || 1) * size, y: a.y + Math.sign(dy || 1) * size };
                    }
                    else {
                        const angle = Math.round(Math.atan2(dy, dx) / (Math.PI / 4)) * Math.PI / 4, len = Math.hypot(dx, dy);
                        p = { x: a.x + Math.cos(angle) * len, y: a.y + Math.sin(angle) * len };
                    }
                }
                draft.value.points = [a, p];
            }
        }
    }
    function up(e) {
        if (!drag || drag.pointer !== e.pointerId)
            return;
        move(e);
        e.stopPropagation();
        const before = drag.before;
        if (marquee.value) {
            const { a, b } = marquee.value;
            selected.value = [...new Set([...selected.value, ...rows.value.filter(r => { const box = bounds(r); return editable(r) && box.x >= Math.min(a.x, b.x) && box.y >= Math.min(a.y, b.y) && box.x + box.width <= Math.max(a.x, b.x) && box.y + box.height <= Math.max(a.y, b.y); }).map(r => r.id)])];
            release();
            return;
        }
        const next = draft.value ? [...rows.value, copyRows([draft.value])[0]] : copyRows(rows.value);
        release();
        if (JSON.stringify(before) !== JSON.stringify(next))
            void save(next, before);
    }
    function choose(id) { cancel(); tool.value = id; context.value = undefined; clearConfirm.value = false; error.value = ''; }
    function remove() { void save(rows.value.filter(r => !selected.value.includes(r.id))); selected.value = []; }
    function copy() { clipboard = copyRows(rows.value.filter(r => selected.value.includes(r.id))); context.value = undefined; }
    function paste() { if (!clipboard.length)
        return; const added = clipboard.map(r => ({ ...translated(r, 21, 21), id: crypto.randomUUID(), audience: props.audience })); void save([...rows.value, ...added]); selected.value = added.map(r => r.id); }
    function history(direction) { cancel(); const list = direction === 'undo' ? undo.value : redo.value; const next = list.at(-1); if (next) {
        selected.value = [];
        void save(copyRows(next), copyRows(rows.value), direction);
    } }
    function styleSelection() { void save(rows.value.map(r => selected.value.includes(r.id) ? { ...r, color: color.value, fill: filled.value ? fill.value : 'none', width: width.value, opacity: opacity.value, fontSize: fontSize.value, text: r.kind === 'text' ? text.value : r.text } : r)); }
    function edit(e, row) { if (tool.value !== 'select' || !editable(row))
        return; e.stopPropagation(); selected.value = [row.id]; tool.value = row.kind === 'text' ? 'text' : 'select'; color.value = row.color; fill.value = row.fill === 'none' ? row.color : row.fill; filled.value = row.fill !== 'none'; width.value = row.width; opacity.value = row.opacity; fontSize.value = row.fontSize; text.value = row.text; }
    function menu(e) { const row = pick(point(e)); if (!row)
        return; e.preventDefault(); e.stopPropagation(); if (!selected.value.includes(row.id))
        selected.value = [row.id]; context.value = { x: e.clientX, y: e.clientY }; }
    function key(e) {
        if (e.target instanceof Element && e.target.closest('input,textarea,select,[contenteditable=true]'))
            return;
        const mod = e.ctrlKey || e.metaKey;
        const handled = e.key === 'Escape' || (['Delete', 'Backspace'].includes(e.key) && selected.value.length) || (mod && ['z', 'y', 'c', 'v', 'a'].includes(e.key.toLowerCase()));
        if (!handled)
            return;
        e.preventDefault();
        e.stopImmediatePropagation();
        if (busy.value)
            return;
        if (e.key === 'Escape') {
            if (drag)
                cancel();
            else if (selected.value.length)
                selected.value = [];
            else
                emit('close');
        }
        else if (['Delete', 'Backspace'].includes(e.key))
            remove();
        else if (e.key.toLowerCase() === 'z')
            history(e.shiftKey ? 'redo' : 'undo');
        else if (e.key.toLowerCase() === 'y')
            history('redo');
        else if (e.key.toLowerCase() === 'c')
            copy();
        else if (e.key.toLowerCase() === 'v')
            paste();
        else
            selected.value = rows.value.filter(editable).map(r => r.id);
    }
    onMounted(() => { window.addEventListener('keydown', key, true); window.addEventListener('blur', cancel); });
    onBeforeUnmount(() => { abort.abort(); cancel(); window.removeEventListener('keydown', key, true); window.removeEventListener('blur', cancel); });
    defineExpose({ editId(id) { const row = rows.value.find(r => r.id === id); if (row) {
            choose('select');
            edit(new MouseEvent('dblclick'), row);
        } } });
    return { gwText, PhCursor, PhPencilSimple, PhLineSegment, PhArrowUpRight, PhRectangle, PhCircle, PhTextT, PhEraser, PhArrowCounterClockwise, PhArrowClockwise, PhTrash, PhCopy, PhClipboard, PhX, BlockStateApi, HttpClient, DirectoryContextMenu, bounds, hit, path, translated, root, tool, rows, version, selected, draft, marquee, color, fill, filled, width, opacity, fontSize, text, busy, error, clearConfirm, context, undo, redo, clipboard, drag, tools, palette, visible, editable, copyRows, point, pick, release, cancel, save, create, down, move, up, choose, remove, copy, paste, history, styleSelection, edit, menu, key, emit: options.emit };
});
