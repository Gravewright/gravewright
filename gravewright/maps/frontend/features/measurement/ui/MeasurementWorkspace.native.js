import { text as gwText } from '../../../shared/config/i18n/text.js';
import { dragMeasure, measurePath, summary, unitsPerPixel } from '../model/measurement.js';
const PhRuler = "PhRuler";
const PhTrash = "PhTrash";
const PhX = "PhX";
const PhPlus = "PhPlus";
import { widget } from '../../../native/widget.js';
export default widget([{ "tag": "svg", "attrs": { "ref": "root", "class": "measurement-workspace" }, "bind": { "class": "({ 'measurement-workspace--active': active })" }, "events": [{ "event": "pointerdown", "code": "down($event);", "mods": [] }, { "event": "pointermove", "code": "move;", "mods": [] }, { "event": "pointerup", "code": "up;", "mods": [] }, { "event": "pointercancel", "code": "cancel;", "mods": [] }], "children": [{ "tag": "g", "attrs": {}, "bind": { "transform": "(`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`)" }, "events": [], "children": [{ "tag": "g", "attrs": {}, "bind": { "key": "(m.id)", "transform": "(`translate(${m.origin.x} ${m.origin.y})`)" }, "events": [], "children": [{ "tag": "g", "attrs": {}, "bind": { "transform": "(`rotate(${m.direction})`)" }, "events": [], "children": [{ "tag": "path", "attrs": { "stroke-linejoin": "round" }, "bind": { "d": "(measurePath(m))", "fill": "(m.kind === 'line' ? 'none' : m.color)", "fill-opacity": "(.16)", "stroke": "(m.color)", "stroke-width": "((selected === m.id ? 2 : 1.5) / viewport.scale)" }, "events": [], "children": [] }, { "tag": "path", "attrs": {}, "bind": { "d": "(`M0 0H${m.length}`)", "stroke": "(m.color)", "stroke-width": "(1 / viewport.scale)", "stroke-dasharray": "(`${5 / viewport.scale} ${3 / viewport.scale}`)" }, "events": [], "children": [], "when": "(m.kind !== 'rect')" }] }, { "tag": "circle", "attrs": { "class": "measurement-workspace__handle", "role": "button" }, "bind": { "r": "(5 / viewport.scale)", "fill": "(m.color)", "stroke": "(selected === m.id ? 'white' : '#171d23')", "stroke-width": "(1.5 / viewport.scale)", "class": "({ 'measurement-workspace__handle--active': active })", "tabindex": "(active ? 0 : -1)", "aria-label": "(`Mover ${formats.find(f => f.id === m.kind)?.label}`)" }, "events": [{ "event": "pointerdown", "code": "down($event, m);", "mods": ["stop"] }, { "event": "wheel", "code": "wheel($event, m);", "mods": [] }, { "event": "keydown", "code": "load(m);", "mods": ["enter", "stop"] }], "children": [] }, { "tag": "text", "attrs": { "fill": "white", "stroke": "#111820", "paint-order": "stroke", "font-family": "sans-serif" }, "bind": { "x": "(8 / viewport.scale)", "y": "(-13 / viewport.scale)", "font-size": "(12 / viewport.scale)", "stroke-width": "(3 / viewport.scale)" }, "events": [], "children": [{ "value": "(summary(m, factor, measureUnit))" }] }], "each": { "names": ["m"], "value": "(visible)" } }] }] }, { "tag": "Teleport", "attrs": { "to": "body" }, "bind": {}, "events": [], "children": [{ "tag": "section", "attrs": { "class": "measure-panel" }, "bind": { "aria-label": "(gwText('Measurement tool'))" }, "events": [{ "event": "pointerdown", "code": "", "mods": ["stop"] }, { "event": "keydown", "code": "", "mods": ["stop"] }], "children": [{ "tag": "header", "attrs": { "class": "measure-panel__header" }, "bind": {}, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "PhRuler", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Measurement '))" }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(measureValue)" }, { "text": " " }, { "value": "(measureUnit)" }, { "value": "(gwText(' / cell'))" }] }] }, { "tag": "button", "attrs": {}, "bind": { "aria-label": "(gwText('Close measurement'))" }, "events": [{ "event": "click", "code": "emit('close');", "mods": [] }], "children": [{ "tag": "PhX", "attrs": {}, "bind": {}, "events": [], "children": [] }] }] }, { "tag": "div", "attrs": { "class": "measure-panel__body" }, "bind": {}, "events": [], "children": [{ "tag": "div", "attrs": { "class": "measure-panel__tools" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": { "key": "(f.id)", "aria-label": "(f.label)", "title": "(f.label)", "aria-pressed": "(kind === f.id)" }, "events": [{ "event": "click", "code": "choose(f.id);", "mods": [] }], "children": [{ "tag": "svg", "attrs": { "viewBox": "0 0 24 24", "aria-hidden": "true" }, "bind": {}, "events": [], "children": [{ "tag": "path", "attrs": { "fill": "none", "stroke": "currentColor", "stroke-width": "1.5", "stroke-linejoin": "round" }, "bind": { "d": "(f.icon)" }, "events": [], "children": [] }] }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(f.label)" }] }], "each": { "names": ["f"], "value": "(formats)" } }] }, { "tag": "div", "attrs": { "class": "measure-panel__options" }, "bind": {}, "events": [], "children": [{ "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "input", "attrs": { "type": "checkbox" }, "bind": {}, "events": [], "children": [], "model": { "path": "(snap)", "mods": [] } }, { "value": "(gwText('Snap to grid'))" }] }, { "tag": "input", "attrs": { "type": "color" }, "bind": { "aria-label": "(gwText('Measurement color'))" }, "events": [{ "event": "change", "code": "apply;", "mods": [] }], "children": [], "model": { "path": "(color)", "mods": [] } }] }, { "tag": "form", "attrs": { "class": "measure-panel__form" }, "bind": {}, "events": [{ "event": "submit", "code": "apply;", "mods": ["prevent"] }], "children": [{ "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(kind === 'circle' ? gwText('Radius') : gwText('Length'))" }, { "text": " (" }, { "value": "(measureUnit)" }, { "text": ")" }, { "tag": "input", "attrs": { "type": "number", "min": "0.001", "max": "100000", "step": "any", "required": "" }, "bind": {}, "events": [], "children": [], "model": { "path": "(lengthValue)", "mods": ["number"] } }] }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Width ('))" }, { "value": "(measureUnit)" }, { "text": ")" }, { "tag": "input", "attrs": { "type": "number", "min": "0.001", "step": "any", "required": "" }, "bind": { "max": "(kind === 'wide-cone' ? lengthValue * .98 : 100000)" }, "events": [], "children": [], "model": { "path": "(widthValue)", "mods": ["number"] } }], "when": "(['rect', 'wide-cone'].includes(kind))" }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Spread (°)'))" }, { "tag": "input", "attrs": { "type": "number", "min": "5", "max": "170", "required": "" }, "bind": {}, "events": [], "children": [], "model": { "path": "(angle)", "mods": ["number"] } }], "when": "(kind === 'cone')" }, { "tag": "label", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Direction (°)'))" }, { "tag": "input", "attrs": { "type": "number", "min": "-360", "max": "360", "step": "any", "required": "" }, "bind": {}, "events": [], "children": [], "model": { "path": "(direction)", "mods": ["number"] } }], "when": "(kind !== 'circle')" }, { "tag": "button", "attrs": { "class": "measure-panel__apply", "type": "submit" }, "bind": {}, "events": [], "children": [{ "value": "(gwText('Apply dimensions'))" }] }], "when": "(current)" }, { "tag": "label", "attrs": { "class": "measure-panel__angle" }, "bind": {}, "events": [], "children": [{ "value": "(gwText('Cover'))" }, { "text": " " }, { "value": "(angle)" }, { "text": "°" }, { "tag": "input", "attrs": { "type": "range", "min": "5", "max": "170", "step": "5" }, "bind": {}, "events": [], "children": [], "model": { "path": "(angle)", "mods": ["number"] } }], "otherwiseWhen": "(kind === 'cone')" }, { "tag": "p", "attrs": { "class": "measure-panel__hint" }, "bind": {}, "events": [], "children": [{ "value": "(current ? gwText('Drag the origin to move. Shift + wheel at the origin rotates.') : gwText('Drag on the map to measure. Shift constrains the angle or creates a square.'))" }, { "text": " " }, { "value": "(gwText('Alt ignores snapping.'))" }] }, { "tag": "div", "attrs": { "class": "measure-panel__actions" }, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": {}, "bind": {}, "events": [{ "event": "click", "code": "selected = '';", "mods": [] }], "children": [{ "tag": "PhPlus", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('New'))" }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "(!selected)" }, "events": [{ "event": "click", "code": "remove;", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Delete'))" }] }, { "tag": "button", "attrs": {}, "bind": { "disabled": "(!rows.length)" }, "events": [{ "event": "click", "code": "confirmClear ? (rows = rows.filter(r => r.canEdit===false), selected = '', confirmClear = false) : confirmClear = true;", "mods": [] }], "children": [{ "value": "(confirmClear ? gwText('Confirm clearing') : gwText('Clear'))" }] }] }, { "tag": "small", "attrs": { "class": "measure-panel__scope" }, "bind": {}, "events": [], "children": [{ "value": "(shared ? gwText('Area markers')+' · ' : gwText('Local scene measurements · '))" }, { "value": "(rows.length)" }, { "value": "('/'+(maxRows || 50))" }] }] }], "when": "(active)" }] }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
    const HttpClient = options.HttpClient;
    const BlockStateApi = class {
        command(_c, _b, a, b, p) { return options.command(a, b, p); }
        state() { return options.read(); }
    };
    const props = options.props;
    const emit = options.emit;
    const root = ref(), rows = ref([]), draft = ref(), selected = ref(''), kind = ref('line'), color = ref('#e1b466'), snap = ref(false), angle = ref(60), confirmClear = ref(false);
    const lengthValue = ref(5), widthValue = ref(5), direction = ref(0);
    const factor = computed(() => unitsPerPixel(props.cell, props.measureValue));
    const current = computed(() => draft.value ?? rows.value.find(m => m.id === selected.value));
    const visible = computed(() => draft.value ? [...rows.value.filter(r => r.id !== draft.value.id), draft.value] : rows.value);
    const formats = [{ id: 'line', get label() { return gwText('Line'); }, icon: 'M3 21L21 3M3 16V21H8M16 3H21V8' }, { id: 'circle', get label() { return gwText('Circle'); }, icon: 'M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0 -18' }, { id: 'rect', get label() { return gwText('Cube / rectangle'); }, icon: 'M3 5H21V19H3Z' }, { id: 'cone', get label() { return gwText('Triangular cone'); }, icon: 'M3 12L21 3V21Z' }, { id: 'wide-cone', get label() { return gwText('Wide cone'); }, icon: 'M2 12L15 5A7 7 0 1 1 15 19Z' }];
    let drag;
    function point(e) { const b = root.value.getBoundingClientRect(); let x = (e.clientX - b.left - props.viewport.x) / props.viewport.scale, y = (e.clientY - b.top - props.viewport.y) / props.viewport.scale; if (snap.value && !e.altKey) {
        x = Math.round(x / props.cell) * props.cell;
        y = Math.round(y / props.cell) * props.cell;
    } return { x, y }; }
    function release() { if (drag && root.value?.hasPointerCapture(drag.pointer))
        root.value.releasePointerCapture(drag.pointer); drag = undefined; draft.value = undefined; }
    function cancel() { release(); confirmClear.value = false; }
    function load(m) { selected.value = m.id; kind.value = m.kind; lengthValue.value = Number((m.length * factor.value).toFixed(3)); widthValue.value = Number((m.width * factor.value).toFixed(3)); angle.value = m.angle; direction.value = ((m.direction % 360) + 360) % 360; color.value = m.color; }
    function down(e, m) {
        if (!props.active || e.button !== 0 || m?.canEdit===false)
            return;
        e.preventDefault();
        e.stopPropagation();
        cancel();
        const p = point(e);
        if (m)
            load(m);
        else
            selected.value = '';
        const seed = m ?? { id: crypto.randomUUID(), kind: kind.value, origin: p, length: 0, width: 0, direction: 0, angle: angle.value, color: color.value };
        drag = { pointer: e.pointerId, start: p, seed, move: !!m };
        draft.value = { ...seed };
        root.value?.setPointerCapture(e.pointerId);
    }
    function move(e) { if (!drag || drag.pointer !== e.pointerId)
        return; e.stopPropagation(); const p = point(e); draft.value = drag.move ? { ...drag.seed, origin: { x: drag.seed.origin.x + p.x - drag.start.x, y: drag.seed.origin.y + p.y - drag.start.y } } : dragMeasure(drag.seed, p, e.shiftKey); }
    function up(e) { if (!drag || drag.pointer !== e.pointerId)
        return; move(e); e.stopPropagation(); const m = draft.value; release(); if (m && m.length * props.viewport.scale > 2 && (m.kind !== 'rect' || m.width * props.viewport.scale > 2)) {
        rows.value = [...rows.value.filter(r => r.id !== m.id), m].slice(-Math.max(1, props.maxRows || 50));
        load(m);
    } }
    function choose(id) { cancel(); selected.value = ''; kind.value = id; }
    function apply() {
        const m = current.value;
        if (!m || m.canEdit===false)
            return;
        const l = Number(lengthValue.value), w = Number(widthValue.value), a = Number(angle.value), d = Number(direction.value);
        if (!Number.isFinite(l) || l <= 0 || l > 100000 || (['rect', 'wide-cone'].includes(m.kind) && (!Number.isFinite(w) || w <= 0 || w > 100000)) || !Number.isFinite(a) || a < 5 || a > 170 || !Number.isFinite(d))
            return;
        const next = { ...m, length: l / factor.value, width: (m.kind === 'wide-cone' ? Math.min(w, l * .98) : w) / factor.value, angle: a, direction: d % 360, color: color.value };
        rows.value = rows.value.map(r => r.id === m.id ? next : r);
        load(next);
    }
    function wheel(e, m) { if (!props.active || !e.shiftKey || m.canEdit===false)
        return; e.preventDefault(); e.stopPropagation(); const next = { ...m, direction: (m.direction + (e.deltaY > 0 ? 15 : -15) + 360) % 360 }; rows.value = rows.value.map(r => r.id === m.id ? next : r); load(next); }
    function remove() { if(current.value?.canEdit===false)return; rows.value = rows.value.filter(r => r.id !== selected.value); selected.value = ''; }
    function key(e) { if (!props.active || e.target instanceof Element && e.target.closest('input,select,textarea,[contenteditable=true]'))
        return; if (e.key === 'Escape') {
        e.preventDefault();
        e.stopImmediatePropagation();
        if (drag)
            cancel();
        else
            emit('close');
    }
    else if (['Delete', 'Backspace'].includes(e.key) && selected.value) {
        e.preventDefault();
        e.stopImmediatePropagation();
        remove();
    } }
    watch(() => props.active, active => { if (!active)
        cancel(); });
    watch(factor, () => { if (current.value)
        load(current.value); });
    onMounted(() => { window.addEventListener('keydown', key, true); window.addEventListener('blur', cancel); });
    onBeforeUnmount(() => { cancel(); window.removeEventListener('keydown', key, true); window.removeEventListener('blur', cancel); });
    watch(() => props.rows, value => {if(props.shared && value)rows.value=value;}, {deep:true,immediate:true});
    watch(rows, value => emit('change', value), { deep: true });
    defineExpose({ replace(value) { cancel(); rows.value = value; }, editId(id) { const row = rows.value.find(r => r.id === id); if (row)
            load(row); } });
    return { gwText, PhRuler, PhTrash, PhX, PhPlus, dragMeasure, measurePath, summary, unitsPerPixel, root, rows, draft, selected, kind, color, snap, angle, confirmClear, lengthValue, widthValue, direction, factor, current, visible, formats, drag, point, release, cancel, load, down, move, up, choose, apply, wheel, remove, key, emit: options.emit };
});
