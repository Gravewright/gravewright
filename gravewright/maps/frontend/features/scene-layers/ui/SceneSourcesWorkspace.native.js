import { text as gwText } from '../../../shared/config/i18n/text.js';
import DirectoryContextMenu from '../../../shared/ui/directory/DirectoryContextMenu.native.js';
import LightPicker from '../../lighting/ui/LightPicker.native.js';
import LightEditor from '../../lighting/ui/LightEditor.native.js';
import { lightPresets } from '../../lighting/model/light-profiles.js';
import EffectEditor from '../../effects/ui/EffectEditor.native.js';
import EffectPicker from '../../effects/ui/EffectPicker.native.js';
import { PARTICLE_DEFAULTS } from '../../effects/model/particle-profiles.js';
import { ShaderDraftValidator } from '../../effects/model/shader-validation.js';
import { shaderPresets } from '../lib/shader-presets.js';
import { effects, defaults, hitEffect, inMarquee, payload, translatedCopies } from '../../effects/model/effects.js';
const PhCopy = "PhCopy";
const PhClipboard = "PhClipboard";
const PhTrash = "PhTrash";
import { widget } from '../../../native/widget.js';
export default widget([{ "tag": "svg", "attrs": { "ref": "root", "class": "scene-sources", "role": "group" }, "bind": { "aria-label": "(`Origens de ${noun} da cena`)" }, "events": [{ "event": "pointerdown", "code": "down;", "mods": [] }, { "event": "pointermove", "code": "move;", "mods": [] }, { "event": "pointerup", "code": "up;", "mods": [] }, { "event": "pointercancel", "code": "up;", "mods": [] }, { "event": "dblclick", "code": "doubleClick;", "mods": [] }, { "event": "contextmenu", "code": "menu;", "mods": [] }, { "event": "wheel", "code": "wheel;", "mods": [] }], "children": [{ "tag": "g", "attrs": {}, "bind": { "transform": "(`translate(${viewport.x},${viewport.y}) scale(${viewport.scale})`)" }, "events": [], "children": [{ "tag": "g", "attrs": { "role": "button", "tabindex": "0", "class": "scene-sources__origin" }, "bind": { "key": "(effect.key)", "data-effect-id": "(effect.id)", "aria-label": "(gwText('{0}: {1}', effect.kind === 'light' ? 'Light' : effect.kind === 'particle' ? 'Particle' : 'Shader', effect.kind === 'light' ? effect.data.animation : effect.kind === 'particle' ? effect.data.kind : effect.data.name))", "data-effect-kind": "(effect.kind)", "class": "({ 'scene-sources__origin--selected': selection.includes(effect.key) })", "transform": "(`translate(${effect.x + (selection.includes(effect.key) ? delta.x : 0)},${effect.y + (selection.includes(effect.key) ? delta.y : 0)}) scale(${1 / viewport.scale})`)" }, "events": [], "children": [{ "tag": "title", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(effect.kind === 'light' ? effect.data.animation : effect.kind === 'shader' ? effect.data.name : effect.data.kind)" }, { "text": " " }, { "value": "(gwText('· double-click to edit'))" }] }, { "tag": "circle", "attrs": { "r": "13" }, "bind": {}, "events": [], "children": [] }, { "tag": "path", "attrs": {}, "bind": { "transform": "(`rotate(${effect.data.rotation})`)", "d": "(effect.kind === 'light' ? 'M 13 0 L 21 0 M 17 -5 L 21 0 L 17 5' : 'M 0 -21 L 0 -13 M -5 -17 L 0 -21 L 5 -17')" }, "events": [], "children": [] }, { "tag": "text", "attrs": { "text-anchor": "middle", "dominant-baseline": "central" }, "bind": {}, "events": [], "children": [{ "value": "(effect.kind === 'light' ? '☀' : effect.kind === 'particle' ? '✦' : '⌘')" }] }], "each": { "names": ["effect"], "value": "(items)" } }, { "tag": "rect", "attrs": { "class": "scene-sources__marquee" }, "bind": { "x": "(Math.min(marquee.from.x, marquee.to.x))", "y": "(Math.min(marquee.from.y, marquee.to.y))", "width": "(Math.abs(marquee.to.x - marquee.from.x))", "height": "(Math.abs(marquee.to.y - marquee.from.y))", "stroke-width": "(1 / viewport.scale)" }, "events": [], "children": [], "when": "(marquee)" }] }] }, { "tag": "Teleport", "attrs": { "to": "body" }, "bind": {}, "events": [], "children": [{ "tag": "DirectoryContextMenu", "attrs": {}, "bind": { "x": "(context.x)", "y": "(context.y)", "label": "(lights ? gwText('Lights') : gwText('Effects'))" }, "events": [{ "event": "close", "code": "context = undefined;", "mods": [] }], "children": [{ "tag": "button", "attrs": { "type": "button" }, "bind": { "disabled": "(!selected.length)" }, "events": [{ "event": "click", "code": "copy;", "mods": [] }], "children": [{ "tag": "PhCopy", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Copy'))" }] }, { "tag": "button", "attrs": { "type": "button" }, "bind": { "disabled": "(!clipboard.length)" }, "events": [{ "event": "click", "code": "paste;", "mods": [] }], "children": [{ "tag": "PhClipboard", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Paste'))" }] }, { "tag": "button", "attrs": { "type": "button" }, "bind": { "disabled": "(!selected.length || busy)" }, "events": [{ "event": "click", "code": "remove();", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Remove'))" }, { "value": "(selected.length > 1 ? ` (${selected.length})` : '')" }] }], "when": "(context)" }, { "tag": "LightPicker", "attrs": {}, "bind": { "selected": "(lightChoice)" }, "events": [{ "event": "choose", "code": "choose;", "mods": [] }, { "event": "close", "code": "closePicker;", "mods": [] }], "children": [], "when": "(picker === 'light')" }, { "tag": "EffectPicker", "attrs": {}, "bind": { "key": "(picker)", "kind": "(picker)", "particle": "(particleChoice)", "shader": "(shaderChoice)" }, "events": [{ "event": "choose", "code": "choose;", "mods": [] }, { "event": "close", "code": "closePicker;", "mods": [] }], "children": [], "when": "(picker && picker !== 'light')" }, { "tag": "LightEditor", "attrs": {}, "bind": { "busy": "(busy)", "error": "(error)" }, "events": [{ "event": "close", "code": "closeEditor;", "mods": [] }, { "event": "change", "code": "changed;", "mods": [] }, { "event": "remove", "code": "remove(items.filter(e => e.id === editing));", "mods": [] }], "children": [], "when": "(editor === 'light')", "model": { "path": "(draft)", "mods": [] } }, { "tag": "EffectEditor", "attrs": {}, "bind": { "kind": "(editor)", "existing": "(!!editing)", "busy": "(busy)", "error": "(error)" }, "events": [{ "event": "close", "code": "closeEditor;", "mods": [] }, { "event": "change", "code": "changed;", "mods": [] }, { "event": "save", "code": "save();", "mods": [] }, { "event": "remove", "code": "remove(items.filter(e => e.id === editing));", "mods": [] }], "children": [], "when": "(editor && editor !== 'light')", "model": { "path": "(draft)", "mods": [] } }, { "tag": "section", "attrs": { "class": "gw-window scene-sources__confirm", "role": "alertdialog" }, "bind": { "aria-label": "(gwText('Clear scene {0}', noun))" }, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Clear '))" }, { "value": "(lights ? gwText('all lights') : gwText('all effects'))" }, { "text": " " }, { "value": "(gwText('from this scene?'))" }] }, { "tag": "p", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(lights ? gwText('Light sources will be removed.') : gwText('Particles and shaders will be removed.'))" }] }, { "tag": "div", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "button", "attrs": { "type": "button" }, "bind": {}, "events": [{ "event": "click", "code": "clearConfirm = false;", "mods": [] }], "children": [{ "value": "(gwText('Cancel'))" }] }, { "tag": "button", "attrs": { "type": "button" }, "bind": {}, "events": [{ "event": "click", "code": "clear;", "mods": [] }], "children": [{ "tag": "PhTrash", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Clear '))" }, { "value": "(noun)" }] }] }], "when": "(clearConfirm)" }, { "tag": "p", "attrs": { "class": "scene-sources__error", "role": "alert" }, "bind": {}, "events": [], "children": [{ "value": "(error)" }], "when": "(error && !editor)" }] }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
    const HttpClient = options.HttpClient;
    const BlockStateApi = class {
        command(_c, _b, a, b, p) { return options.command(a, b, p); }
        state() { return options.read(); }
    };
    const props = options.props;
    const emit = options.emit;
    const lights = props.layer === 'lighting';
    const batchArea = lights ? 'light-selection' : 'effects';
    const lightChoice = ref('torch');
    const noun = lights ? gwText('lights') : gwText('effects');
    const area = (kind) => kind === 'light' ? 'lights' : kind === 'particle' ? 'particles' : 'shaders';
    const identityKey = (kind) => kind === 'light' ? 'light_id' : kind === 'particle' ? 'emitter_id' : 'shader_id';
    const rowKey = (kind) => kind === 'light' ? 'light' : kind === 'particle' ? 'emitter' : 'shader';
    const root = ref();
    const items = computed(() => effects(props.state, props.layer));
    const selection = ref([]), clipboard = ref([]);
    const selected = computed(() => items.value.filter(e => selection.value.includes(e.key)));
    const context = ref();
    const picker = ref(), particleChoice = ref('smoke'), shaderChoice = ref('orb-1');
    const editor = ref(), editing = ref();
    const draft = ref(defaults()), error = ref(''), busy = ref(false), clearConfirm = ref(false);
    const delta = ref({ x: 0, y: 0 });
    const marquee = ref();
    let gesture;
    let editorVisit = 0, previewFrame = 0;
    let pendingDelta = { x: 0, y: 0 };
    let lastPoint = { x: 0, y: 0 }, closed = false, queue = Promise.resolve();
    let saveTimer;
    let shaderTimer;
    const validator = new ShaderDraftValidator();
    const abort = new AbortController();
    const api = new BlockStateApi(new HttpClient(undefined, () => abort.signal));
    const writer = new BlockStateApi();
    const containerId = props.containerId, blockId = props.blockId;
    function point(event) { const r = root.value.getBoundingClientRect(); return { x: (event.clientX - r.left - props.viewport.x) / props.viewport.scale, y: (event.clientY - r.top - props.viewport.y) / props.viewport.scale }; }
    function center() { const r = root.value?.getBoundingClientRect(); return { x: ((r?.width ?? 0) / 2 - props.viewport.x) / props.viewport.scale, y: ((r?.height ?? 0) / 2 - props.viewport.y) / props.viewport.scale }; }
    function refs(list = selected.value) { return list.map(e => ({ id: e.id, kind: e.kind })); }
    function run(area, action, data, after) {
        const operation = async () => { if (closed)
            return; busy.value = true; error.value = ''; try {
            const result = await writer.command(containerId, blockId, area, action, data);
            if (closed)
                return;
            after?.(result);
            const state = await api.state(containerId, blockId);
            if (!closed) {
                emit('changed', state);
                if (area === batchArea && action === 'transform' && editing.value) {
                    const row = effects(state, props.layer).find(e => e.id === editing.value);
                    if (row)
                        draft.value = { ...draft.value, x: row.x, y: row.y, rotation: row.data.rotation };
                }
            }
        }
        catch (reason) {
            if (!closed)
                error.value = gwText('Could not save the change. Check the data and try again.');
        }
        finally {
            if (!closed) {
                busy.value = false;
                emit('preview', undefined);
            }
        } };
        queue = queue.then(operation);
        return queue;
    }
    function open(kind, effect) { closePicker(); flush(); if (shaderTimer)
        clearTimeout(shaderTimer); emit('preview', undefined); ++editorVisit; context.value = undefined; editor.value = kind; editing.value = effect.id; draft.value = { ...effect.data }; if (kind === 'shader') {
        const match = /^gravewright-preset:\/\/([^/]+)\/v1$/.exec(draft.value.source);
        if (match)
            draft.value.source = shaderPresets.find(p => p.id === match[1])?.source ?? draft.value.source;
    } }
    function closePicker() { picker.value = undefined; emit('preview', undefined); }
    function action(id) {
        const previous = picker.value;
        closePicker();
        closeEditor();
        if ((id === 'clear-effects' || id === 'clear-lights')) {
            clearConfirm.value = true;
            return;
        }
        if ((id === 'particle' || id === 'shader' || id === 'light') && previous !== id)
            picker.value = id;
    }
    function choose(id) { if (picker.value === 'light')
        lightChoice.value = id;
    else if (picker.value === 'particle')
        particleChoice.value = id;
    else
        shaderChoice.value = id; closePicker(); }
    function shaderData(id) { const preset = shaderPresets.find(p => p.id === id); return { ...defaults(), scale: 1, color: '#8fb6ff', ...preset }; }
    defineExpose({ action, doubleClick });
    function save(at) { if (!editor.value)
        return; if (saveTimer)
        clearTimeout(saveTimer); saveTimer = undefined; const kind = editor.value; if (kind === 'shader') {
        error.value = validator.validate(draft.value.source);
        if (error.value)
            return;
    } const data = payload(kind, { ...draft.value, ...at }); const identity = editing.value, visit = editorVisit; void run(area(kind), identity ? 'update' : 'create', identity ? { ...data, [identityKey(kind)]: identity } : data, result => { const row = result[rowKey(kind)]; if (row && editor.value === kind && visit === editorVisit) {
        editing.value = row.id;
        selection.value = [`${kind}:${row.id}`];
    } }); }
    function previewShader() { if (closed || editor.value !== 'shader')
        return; error.value = validator.validate(draft.value.source); if (error.value)
        return; const shader = { ...draft.value, id: editing.value ?? 'draft-shader' }; emit('preview', { ...props.state, shaders: [...props.state.shaders.filter(s => s.id !== shader.id), shader] }); }
    function changed() { if (editor.value === 'light' && draft.value.dim_radius > 0)
        draft.value.dim_radius = Math.max(draft.value.dim_radius, draft.value.bright_radius); if (editor.value === 'shader') {
        if (shaderTimer)
            clearTimeout(shaderTimer);
        shaderTimer = setTimeout(previewShader, 250);
        return;
    } if (editor.value && editing.value) {
        if (saveTimer)
            clearTimeout(saveTimer);
        saveTimer = setTimeout(() => save(), 250);
    } }
    function flush() { if (saveTimer) {
        clearTimeout(saveTimer);
        saveTimer = undefined;
        save();
    } }
    function closeEditor() { flush(); if (shaderTimer)
        clearTimeout(shaderTimer); emit('preview', undefined); validator.dispose(); ++editorVisit; editor.value = undefined; editing.value = undefined; }
    function createAt(at) {
        const kind = props.tool;
        const data = kind === 'light' ? { ...defaults(), ...lightPresets.find(p => p.id === lightChoice.value), animation: lightChoice.value, ...at } : kind === 'particle' ? { ...defaults(), ...PARTICLE_DEFAULTS[particleChoice.value], light_response: ['smoke', 'dust', 'rain', 'snow', 'leaves', 'bubbles', 'ash', 'blood'].includes(particleChoice.value) ? .8 : 0, light_emission: ['ember', 'firefly', 'arcane', 'runes'].includes(particleChoice.value) ? .15 : 0, kind: particleChoice.value, ...at } : { ...shaderData(shaderChoice.value), ...at };
        closePicker();
        void run(area(kind), 'create', payload(kind, data), result => { const row = result[rowKey(kind)]; if (row)
            selection.value = [`${kind}:${row.id}`]; });
    }
    function down(event) {
        if (!['select', 'light', 'particle', 'shader'].includes(props.tool))
            return;
        if (event.button === 1)
            return;
        if (event.button === 2 && !hitEffect(items.value, point(event), props.viewport.scale))
            return;
        event.stopPropagation();
        event.preventDefault();
        context.value = undefined;
        closePicker();
        if (event.button !== 0 || busy.value)
            return;
        const from = point(event);
        lastPoint = from;
        const hit = hitEffect(items.value, from, props.viewport.scale);
        if (hit) {
            if (event.shiftKey)
                selection.value = selection.value.includes(hit.key) ? selection.value.filter(k => k !== hit.key) : [...selection.value, hit.key];
            else if (!selection.value.includes(hit.key))
                selection.value = [hit.key];
        }
        const original = [...selection.value];
        if (!hit && !event.shiftKey && props.tool === 'select')
            selection.value = [];
        gesture = { pointer: event.pointerId, from, to: from, hit, original, additive: event.shiftKey };
        root.value?.setPointerCapture(event.pointerId);
    }
    function paintPreview(dx, dy) { const move = (kind, data) => selection.value.includes(`${kind}:${data.id}`) ? { ...data, x: data.x + dx, y: data.y + dy } : data; emit('preview', { ...props.state, particles: props.state.particles.map(p => move('particle', p)), shaders: props.state.shaders.map(p => move('shader', p)), lights: props.state.lights.map(p => move('light', p)) }); }
    function previewMove(dx, dy) { pendingDelta = { x: dx, y: dy }; if (!previewFrame)
        previewFrame = requestAnimationFrame(() => { previewFrame = 0; if (!closed)
            paintPreview(pendingDelta.x, pendingDelta.y); }); }
    function move(event) {
        lastPoint = point(event);
        if (!gesture || gesture.pointer !== event.pointerId)
            return;
        event.stopPropagation();
        gesture.to = lastPoint;
        if (gesture.hit) {
            delta.value = { x: lastPoint.x - gesture.from.x, y: lastPoint.y - gesture.from.y };
            previewMove(delta.value.x, delta.value.y);
        }
        else if (props.tool === 'select') {
            marquee.value = { from: gesture.from, to: lastPoint };
            selection.value = [...new Set([...(gesture.additive ? gesture.original : []), ...inMarquee(items.value, gesture.from, lastPoint)])];
        }
    }
    function up(event) {
        if (!gesture || gesture.pointer !== event.pointerId)
            return;
        event.stopPropagation();
        const g = gesture;
        gesture = undefined;
        marquee.value = undefined;
        cancelAnimationFrame(previewFrame);
        previewFrame = 0;
        if (event.type === 'pointercancel') {
            selection.value = g.original;
            delta.value = { x: 0, y: 0 };
            emit('preview', undefined);
            return;
        }
        const to = point(event);
        const moved = Math.hypot(to.x - g.from.x, to.y - g.from.y) * props.viewport.scale > 3;
        if (g.hit && moved) {
            delta.value = { x: to.x - g.from.x, y: to.y - g.from.y };
            paintPreview(delta.value.x, delta.value.y);
            void run(batchArea, 'transform', { effects: refs(), dx: delta.value.x, dy: delta.value.y }).finally(() => { delta.value = { x: 0, y: 0 }; });
        }
        else if (g.hit && !moved && !g.additive)
            selection.value = [g.hit.key];
        else if (!g.hit && (props.tool === 'particle' || props.tool === 'shader' || props.tool === 'light'))
            createAt(to);
        else
            emit('preview', undefined);
        if (!g.hit || !moved)
            delta.value = { x: 0, y: 0 };
    }
    function doubleClick(event) { const hit = hitEffect(items.value, point(event), props.viewport.scale); if (hit) {
        event.stopPropagation();
        selection.value = [hit.key];
        emit('tool', 'select');
        open(hit.kind, hit);
    } }
    function menu(event) { const world = point(event), hit = hitEffect(items.value, world, props.viewport.scale); if (!hit)
        return; event.preventDefault(); event.stopPropagation(); if (hit && !selection.value.includes(hit.key))
        selection.value = [hit.key]; context.value = { x: event.clientX, y: event.clientY, world }; }
    function copy() { clipboard.value = selected.value.map(e => ({ ...e, data: structuredClone({ ...e.data }) })); context.value = undefined; }
    function paste() { if (!clipboard.value.length)
        return; const at = context.value?.world ?? lastPoint; context.value = undefined; void run(batchArea, 'paste', { effects: translatedCopies(clipboard.value, at) }, r => { selection.value = r.effects.map((e) => `${e.kind}:${e.id}`); }); }
    function discardPending() { if (saveTimer)
        clearTimeout(saveTimer); saveTimer = undefined; if (shaderTimer)
        clearTimeout(shaderTimer); shaderTimer = undefined; ++editorVisit; }
    function remove(list = selected.value) { if (list.some(e => e.id === editing.value))
        discardPending(); context.value = undefined; if (!list.length)
        return; const ids = refs(list); void run(batchArea, 'delete', { effects: ids }, () => { selection.value = []; if (list.some(e => e.id === editing.value)) {
        editor.value = undefined;
        editing.value = undefined;
    } }); }
    function clear() { discardPending(); clearConfirm.value = false; void run(batchArea, 'clear', {}, () => { selection.value = []; editor.value = undefined; editing.value = undefined; }); }
    function wheel(event) { if (!event.shiftKey)
        return; event.preventDefault(); event.stopPropagation(); if (selected.value.length)
        void run(batchArea, 'transform', { effects: refs(), rotation: event.deltaY > 0 ? 15 : -15 }); }
    function keyboard(event) {
        if (props.tool === 'managed' || document.querySelector('.house-menu-scrim')?.getClientRects().length)
            return;
        if (event.target instanceof Element && event.target.closest('input,textarea,select,[contenteditable=true],.gw-window,dialog[open]'))
            return;
        const key = event.key.toLowerCase();
        if (event.key === 'Escape') {
            if (gesture) {
                cancelAnimationFrame(previewFrame);
                previewFrame = 0;
                gesture = undefined;
                delta.value = { x: 0, y: 0 };
                marquee.value = undefined;
                emit('preview', undefined);
            }
            else {
                context.value = undefined;
                clearConfirm.value = false;
                closePicker();
                closeEditor();
                selection.value = [];
            }
            event.preventDefault();
            event.stopImmediatePropagation();
            return;
        }
        if (['Delete', 'Backspace'].includes(event.key)) {
            event.preventDefault();
            event.stopImmediatePropagation();
            remove();
        }
        if (event.ctrlKey || event.metaKey) {
            if (key === 'c') {
                event.preventDefault();
                event.stopImmediatePropagation();
                copy();
            }
            if (key === 'v') {
                event.preventDefault();
                event.stopImmediatePropagation();
                paste();
            }
        }
    }
    watch(() => props.state, () => { const available = new Set(items.value.map(e => e.key)); selection.value = selection.value.filter(k => available.has(k)); });
    onMounted(() => { lastPoint = center(); document.addEventListener('keydown', keyboard, true); });
    onBeforeUnmount(() => {
        if (saveTimer && editor.value && editor.value !== 'shader' && editing.value) {
            clearTimeout(saveTimer);
            const kind = editor.value;
            const data = { ...payload(kind, draft.value), [identityKey(kind)]: editing.value };
            queue = queue.then(async () => { await writer.command(containerId, blockId, area(kind), 'update', data); }).catch(() => { });
        }
        closed = true;
        abort.abort();
        cancelAnimationFrame(previewFrame);
        if (shaderTimer)
            clearTimeout(shaderTimer);
        validator.dispose();
        document.removeEventListener('keydown', keyboard, true);
        emit('preview', undefined);
    });
    return { gwText, PhCopy, PhClipboard, PhTrash, BlockStateApi, HttpClient, DirectoryContextMenu, LightPicker, LightEditor, lightPresets, EffectEditor, EffectPicker, PARTICLE_DEFAULTS, ShaderDraftValidator, shaderPresets, effects, defaults, hitEffect, inMarquee, payload, translatedCopies, lights, batchArea, lightChoice, noun, area, identityKey, rowKey, root, items, selection, clipboard, selected, context, picker, particleChoice, shaderChoice, editor, editing, draft, error, busy, clearConfirm, delta, marquee, gesture, editorVisit, previewFrame, pendingDelta, lastPoint, closed, queue, saveTimer, shaderTimer, validator, writer, containerId, blockId, point, center, refs, run, open, closePicker, action, choose, shaderData, save, previewShader, changed, flush, closeEditor, createAt, down, paintPreview, previewMove, move, up, doubleClick, menu, copy, paste, discardPending, remove, clear, wheel, keyboard, emit: options.emit };
});
