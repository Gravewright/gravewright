import { text as gwText } from '../../../shared/config/i18n/text.js';
import { renderingPreferences } from '../../../shared/rendering/render-profile.js';
import { effectQuality } from '../../../shared/rendering/effect-quality.js';
import { lightPresets, paintAnimatedLight } from '../model/light-profiles.js';
const PhFlame = "PhFlame";
const PhWaveform = "PhWaveform";
const PhLightbulb = "PhLightbulb";
const PhX = "PhX";
import { widget } from '../../../native/widget.js';
export default widget([{ "tag": "section", "attrs": { "ref": "panel", "class": "light-picker", "role": "dialog" }, "bind": { "style": "(position)", "aria-label": "(gwText('Light types'))" }, "events": [{ "event": "keydown", "code": "emit('close');", "mods": ["esc", "stop"] }], "children": [{ "tag": "div", "attrs": { "class": "light-picker__preview", "role": "img" }, "bind": { "aria-label": "(gwText('Preview: {0}', current.name))" }, "events": [], "children": [{ "tag": "canvas", "attrs": { "ref": "canvas", "width": "430", "height": "123" }, "bind": {}, "events": [], "children": [] }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(current.name)" }] }] }, { "tag": "header", "attrs": { "class": "light-picker__header" }, "bind": {}, "events": [], "children": [{ "tag": "PhLightbulb", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(gwText('Lighting'))" }] }, { "tag": "button", "attrs": {}, "bind": { "aria-label": "(gwText('Close picker'))" }, "events": [{ "event": "click", "code": "emit('close');", "mods": [] }], "children": [{ "tag": "PhX", "attrs": {}, "bind": {}, "events": [], "children": [] }] }] }, { "tag": "div", "attrs": { "class": "light-picker__options" }, "bind": {}, "events": [{ "event": "mouseleave", "code": "hovered = undefined;", "mods": [] }], "children": [{ "tag": "button", "attrs": {}, "bind": { "key": "(p.id)", "aria-pressed": "(selected === p.id)" }, "events": [{ "event": "mouseenter", "code": "hovered = p.id;", "mods": [] }, { "event": "focus", "code": "hovered = p.id;", "mods": [] }, { "event": "click", "code": "emit('choose', p.id);", "mods": [] }], "children": [{ "tag": "component", "attrs": {}, "bind": { "is": "(icons[p.id])" }, "events": [], "children": [] }, { "value": "(p.name)" }], "each": { "names": ["p"], "value": "(lightPresets)" } }] }] }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
    const HttpClient = options.HttpClient;
    const BlockStateApi = class {
        command(_c, _b, a, b, p) { return options.command(a, b, p); }
        state() { return options.read(); }
    };
    const props = options.props;
    const emit = options.emit;
    const hovered = ref();
    const current = computed(() => lightPresets.find(p => p.id === (hovered.value ?? props.selected)) ?? lightPresets[0]);
    const panel = ref(), canvas = ref();
    const position = ref({ left: '13px', bottom: '89px' });
    let frame = 0;
    let restart = () => { };
    let stopProfile;
    const icons = { torch: PhFlame, pulse: PhWaveform, none: PhLightbulb };
    function place() { const r = document.querySelector('[data-effect-tool="light"]')?.getBoundingClientRect(); if (r)
        position.value = { left: `${Math.max(8, Math.min(innerWidth - 438, r.left))}px`, bottom: `${innerHeight - r.top + 8}px` }; }
    function outside(e) { if (e.target instanceof Element && !panel.value?.contains(e.target) && !e.target.closest('[data-effect-tool]'))
        emit('close'); }
    onMounted(() => { place(); window.addEventListener('resize', place); document.addEventListener('pointerdown', outside); const ctx = canvas.value.getContext('2d'); let last = 0; const tick = (time) => { const fps = effectQuality(renderingPreferences.current().name).fps; if (!fps || time - last >= 1000 / fps) {
        last = time;
        ctx.clearRect(0, 0, 430, 123);
        paintAnimatedLight(ctx, { ...current.value, id: 'preview', animation: current.value.id, x: 215, y: 61, enabled: true }, 215, 61, 55, fps ? time : 0);
    } if (fps)
        frame = requestAnimationFrame(tick); }; restart = () => { cancelAnimationFrame(frame); last = 0; tick(performance.now()); }; stopProfile = renderingPreferences.subscribe(restart); });
    watch(current, () => restart());
    onBeforeUnmount(() => { stopProfile?.(); cancelAnimationFrame(frame); window.removeEventListener('resize', place); document.removeEventListener('pointerdown', outside); });
    return { gwText, PhFlame, PhWaveform, PhLightbulb, PhX, renderingPreferences, effectQuality, lightPresets, paintAnimatedLight, hovered, current, panel, canvas, position, frame, restart, stopProfile, icons, place, outside, emit: options.emit };
});
