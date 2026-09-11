import { text as gwText } from '../../../shared/config/i18n/text.js';
import { lightPresets } from '../../lighting/model/light-profiles.js';
import { PARTICLE_DEFAULTS } from '../../effects/model/particle-profiles.js';
import { ShaderDraftValidator } from '../../effects/model/shader-validation.js';
import { shaderPresets } from '../lib/shader-presets.js';
import { effects, defaults, hitEffect, inMarquee, payload, translatedCopies } from '../../effects/model/effects.js';
const box = (value) => ({ value });
const derive = (read) => ({ get value() { return read(); } });
export function sourceController(element, options) {
    const props = { ...options.props }, emit = options.emit;
    const api = { state: () => options.read() }, writer = { command: (_a, _b, area, action, data) => options.command(area, action, data) };
    const lights = props.layer === 'lighting';
    const batchArea = lights ? 'light-selection' : 'effects';
    const lightChoice = box('torch');
    const noun = lights ? gwText('lights') : gwText('effects');
    const area = (kind) => kind === 'light' ? 'lights' : kind === 'particle' ? 'particles' : 'shaders';
    const identityKey = (kind) => kind === 'light' ? 'light_id' : kind === 'particle' ? 'emitter_id' : 'shader_id';
    const rowKey = (kind) => kind === 'light' ? 'light' : kind === 'particle' ? 'emitter' : 'shader';
    const root = box();
    const items = derive(() => effects(props.state, props.layer));
    const selection = box([]), clipboard = box([]);
    const selected = derive(() => items.value.filter(e => selection.value.includes(e.key)));
    const context = box();
    const picker = box(), particleChoice = box('smoke'), shaderChoice = box('orb-1');
    const editor = box(), editing = box();
    const draft = box(defaults()), error = box(''), busy = box(false), clearConfirm = box(false);
    const delta = box({ x: 0, y: 0 });
    const marquee = box();
    let gesture;
    let editorVisit = 0, previewFrame = 0;
    let pendingDelta = { x: 0, y: 0 };
    let lastPoint = { x: 0, y: 0 }, closed = false, queue = Promise.resolve();
    let saveTimer;
    let shaderTimer;
    const validator = new ShaderDraftValidator();
    const abort = new AbortController();
    const containerId = props.containerId, blockId = props.blockId;
    function point(event) { const r = root.value.getBoundingClientRect(); return { x: (event.clientX - r.left - props.viewport.x) / props.viewport.scale, y: (event.clientY - r.top - props.viewport.y) / props.viewport.scale }; }
    function center() { const r = root.value?.getBoundingClientRect(); return { x: ((r?.width ?? 0) / 2 - props.viewport.x) / props.viewport.scale, y: ((r?.height ?? 0) / 2 - props.viewport.y) / props.viewport.scale }; }
    function refs(list = selected.value) { return list.map(e => ({ id: e.id, kind: e.kind })); }
    function run(area, action, data, after) {
        const operation = async () => { if (closed)
            return; busy.value = true; error.value = ''; options.repaint(); try {
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
                options.repaint();
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
    } if (editor.value === 'light' && editing.value) {
        emit('preview', { ...props.state, lights: props.state.lights.map(light => light.id === editing.value ? { ...light, ...draft.value } : light) });
        if (!saveTimer) saveTimer = setTimeout(() => save(), 100);
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
        if (props.tool === 'managed')
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
    root.value = element;
    lastPoint = center();
    const events = { pointerdown: down, pointermove: move, pointerup: up, pointercancel: up, dblclick: doubleClick, contextmenu: menu, wheel };
    const listeners = Object.entries(events).map(([name, fn]) => { const handler = (e) => { fn(e); options.repaint(); }; element.addEventListener(name, handler); return [name, handler]; });
    const key = (e) => { keyboard(e); options.repaint(); };
    document.addEventListener('keydown', key, true);
    return { get view() { return { items: items.value, selection: selection.value, selected: selected.value, clipboard: clipboard.value, context: context.value, picker: picker.value, lightChoice: lightChoice.value, editor: editor.value, editing: editing.value, draft: draft.value, error: error.value, busy: busy.value, clearConfirm: clearConfirm.value, delta: delta.value, marquee: marquee.value }; }, call(name, ...args) { const methods = { open, action, choose, closePicker, closeEditor, changed, save, copy, paste, remove, clear, closeMenu: () => context.value = undefined, closeClear: () => clearConfirm.value = false }; const result = methods[name](...args); options.repaint(); return result; }, update(next) { Object.assign(props, next); const available = new Set(items.value.map(e => e.key)); selection.value = selection.value.filter(k => available.has(k)); options.repaint(); }, destroy() { if (saveTimer && editor.value === 'light' && editing.value) {
            const data = { ...payload('light', draft.value), light_id: editing.value };
            queue = queue.then(() => writer.command(containerId, blockId, 'lights', 'update', data)).catch(() => { });
        } closed = true; abort.abort(); clearTimeout(saveTimer); clearTimeout(shaderTimer); cancelAnimationFrame(previewFrame); validator.dispose(); for (const [name, fn] of listeners)
            element.removeEventListener(name, fn); document.removeEventListener('keydown', key, true); } };
}
