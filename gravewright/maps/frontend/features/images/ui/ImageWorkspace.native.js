import { text as gwText } from '../../../shared/config/i18n/text.js';
import DirectoryContextMenu from '../../../shared/ui/directory/DirectoryContextMenu.native.js';
const PhTrash = "PhTrash";
import { widget } from '../../../native/widget.js';
export default widget([{ "tag": "svg", "attrs": { "ref": "root", "class": "image-workspace" }, "bind": {}, "events": [{ "event": "pointermove", "code": "move;", "mods": [] }, { "event": "pointerup", "code": "up;", "mods": [] }, { "event": "pointercancel", "code": "cancel;", "mods": [] }], "children": [{ "tag": "g", "attrs": {}, "bind": { "transform": "(`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`)" }, "events": [], "children": [{ "tag": "g", "attrs": {}, "bind": { "key": "(image.id)", "transform": "(`translate(${image.x} ${image.y}) rotate(${image.rotation})`)" }, "events": [], "children": [{ "tag": "rect", "attrs": { "class": "image-workspace__image", "fill": "transparent", "role": "button" }, "bind": { "class": "({ 'image-workspace__image--active': tool === 'select' })", "x": "(-image.natural_width * image.scale / 2)", "y": "(-image.natural_height * image.scale / 2)", "width": "(image.natural_width * image.scale)", "height": "(image.natural_height * image.scale)", "stroke": "(selected === image.id ? '#e9c46a' : 'none')", "stroke-width": "(2 / viewport.scale)", "tabindex": "(tool === 'select' ? 0 : -1)", "aria-label": "(gwText('Scene image'))", "aria-pressed": "(selected === image.id)" }, "events": [{ "event": "pointerdown", "code": "down($event, image);", "mods": [] }, { "event": "contextmenu", "code": "menu($event, image);", "mods": [] }, { "event": "keydown", "code": "selected = image.id;", "mods": ["enter", "stop"] }], "children": [] }], "each": { "names": ["image"], "value": "(images)" } }] }] }, { "tag": "p", "attrs": { "class": "image-workspace__status" }, "bind": { "role": "(error ? 'alert' : 'status')" }, "events": [], "children": [{ "value": "(error || gwText('Saving image…'))" }], "when": "(error || busy)" }, { "tag": "Teleport", "attrs": { "to": "body" }, "bind": {}, "events": [], "children": [{ "tag": "DirectoryContextMenu", "attrs": {}, "bind": { "x": "(context.x)", "y": "(context.y)", "label": "(gwText('Image actions'))" }, "events": [{ "event": "close", "code": "context = undefined;", "mods": [] }], "children": [{ "tag": "li", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": { "class": "is-danger" }, "bind": { "disabled": "(busy)" }, "events": [{ "event": "click", "code": "remove;", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Remove from scene'))" }] }] }], "when": "(context)" }] }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
    const HttpClient = options.HttpClient;
    const BlockStateApi = class {
        command(_c, _b, a, b, p) { return options.command(a, b, p); }
        state() { return options.read(); }
    };
    const props = options.props;
    const emit = options.emit;
    const abort = new AbortController(), api = new BlockStateApi(new HttpClient(undefined, () => abort.signal));
    const root = ref(), selected = ref(''), preview = ref(), busy = ref(false), error = ref(''), context = ref();
    const images = computed(() => [...props.images].sort((a, b) => a.z_index - b.z_index).map(image => preview.value?.id === image.id ? preview.value : image));
    let drag;
    function show(image) { preview.value = image; emit('preview', image); }
    function point(e) { const box = root.value.getBoundingClientRect(); return { x: (e.clientX - box.left - props.viewport.x) / props.viewport.scale, y: (e.clientY - box.top - props.viewport.y) / props.viewport.scale }; }
    function down(e, image) { if (e.button !== 0 || busy.value || props.tool !== 'select')
        return; e.preventDefault(); e.stopPropagation(); selected.value = image.id; context.value = undefined; error.value = ''; const p = point(e); drag = { pointer: e.pointerId, ...p, image: { ...image } }; root.value?.setPointerCapture(e.pointerId); }
    function move(e) { if (!drag || drag.pointer !== e.pointerId)
        return; e.stopPropagation(); const p = point(e); show({ ...drag.image, x: drag.image.x + p.x - drag.x, y: drag.image.y + p.y - drag.y }); }
    function release() { if (drag && root.value?.hasPointerCapture(drag.pointer))
        root.value.releasePointerCapture(drag.pointer); drag = undefined; }
    function cancel() { release(); show(); context.value = undefined; }
    async function save(image) { if (busy.value)
        return; busy.value = true; error.value = ''; show(image); try {
        await api.command(props.containerId, props.blockId, 'images', 'update', { placement_id: image.id, x: image.x, y: image.y, expected_version: image.version });
        if (!abort.signal.aborted)
            emit('refresh');
    }
    catch {
        if (!abort.signal.aborted) {
            show();
            error.value = gwText('Could not move the image. Refreshing the scene…');
            emit('refresh');
        }
    }
    finally {
        if (!abort.signal.aborted)
            busy.value = false;
    } }
    function up(e) { if (!drag || drag.pointer !== e.pointerId)
        return; e.stopPropagation(); const original = drag.image; const image = preview.value; release(); if (!image || (image.x === original.x && image.y === original.y)) {
        show();
        return;
    } const cell = props.cell; void save({ ...image, x: props.grid && !e.altKey ? Math.round(image.x / cell) * cell : image.x, y: props.grid && !e.altKey ? Math.round(image.y / cell) * cell : image.y }); }
    async function remove() { if (!selected.value || busy.value)
        return; busy.value = true; context.value = undefined; try {
        await api.command(props.containerId, props.blockId, 'images', 'delete', { placement_id: selected.value });
        if (!abort.signal.aborted) {
            selected.value = '';
            emit('refresh');
        }
    }
    catch {
        if (!abort.signal.aborted)
            error.value = gwText('Could not remove the image.');
    }
    finally {
        if (!abort.signal.aborted)
            busy.value = false;
    } }
    function menu(e, image) { if (props.tool !== 'select')
        return; e.preventDefault(); e.stopPropagation(); selected.value = image.id; context.value = { x: e.clientX, y: e.clientY }; }
    function key(e) { if (e.target instanceof Element && e.target.closest('input,textarea,select,[contenteditable=true]'))
        return; if (e.key === 'Escape') {
        cancel();
        selected.value = '';
        return;
    } if (!selected.value || busy.value || drag || props.tool !== 'select')
        return; if (['Delete', 'Backspace'].includes(e.key)) {
        e.preventDefault();
        e.stopPropagation();
        void remove();
        return;
    } const delta = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[e.key]; const image = props.images.find(i => i.id === selected.value); if (delta && image) {
        e.preventDefault();
        e.stopPropagation();
        const step = e.altKey ? 1 : props.cell;
        void save({ ...image, x: image.x + delta[0] * step, y: image.y + delta[1] * step });
    } }
    watch(() => props.images, rows => { if (drag && !rows.some(i => i.id === drag.image.id && i.version === drag.image.version))
        cancel(); if (!drag)
        show(); if (!rows.some(i => i.id === selected.value))
        selected.value = ''; });
    watch(() => props.tool, cancel);
    onMounted(() => { window.addEventListener('keydown', key); window.addEventListener('blur', cancel); });
    onBeforeUnmount(() => { abort.abort(); cancel(); window.removeEventListener('keydown', key); window.removeEventListener('blur', cancel); });
    return { gwText, PhTrash, BlockStateApi, HttpClient, DirectoryContextMenu, root, selected, preview, busy, error, context, images, drag, show, point, down, move, release, cancel, save, up, remove, menu, key, emit: options.emit };
});
