import { text as gwText } from '../../../shared/config/i18n/text.js';
import { shaderPresets } from '../../scene-layers/lib/shader-presets.js';
import { effectLabels } from '../model/legacy-labels.js';
import EffectPreview from './EffectPreview.native.js';
const PhCloud = "PhCloud";
const PhFireSimple = "PhFireSimple";
const PhDotsThreeOutline = "PhDotsThreeOutline";
const PhSparkle = "PhSparkle";
const PhCloudRain = "PhCloudRain";
const PhSnowflake = "PhSnowflake";
const PhLightbulb = "PhLightbulb";
const PhLeaf = "PhLeaf";
const PhCirclesThreePlus = "PhCirclesThreePlus";
const PhWind = "PhWind";
const PhDrop = "PhDrop";
const PhPentagram = "PhPentagram";
const PhCode = "PhCode";
const PhCodeBlock = "PhCodeBlock";
const PhX = "PhX";
import { widget } from '../../../native/widget.js';
export default widget([{ "tag": "section", "attrs": { "ref": "panel", "class": "effect-picker", "role": "dialog" }, "bind": { "class": "({ 'effect-picker--shader': kind === 'shader' })", "style": "(position)", "aria-label": "(title)" }, "events": [{ "event": "keydown", "code": "emit('close');", "mods": ["esc", "stop"] }], "children": [{ "tag": "EffectPreview", "attrs": {}, "bind": { "kind": "(kind)", "choice": "(previewChoice)", "label": "(previewLabel)" }, "events": [], "children": [] }, { "tag": "header", "attrs": { "class": "effect-picker__header" }, "bind": {}, "events": [], "children": [{ "tag": "component", "attrs": {}, "bind": { "is": "(kind === 'shader' ? PhCode : PhSparkle)" }, "events": [], "children": [] }, { "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(title)" }] }, { "tag": "button", "attrs": { "type": "button" }, "bind": { "aria-label": "(gwText('Close picker'))" }, "events": [{ "event": "click", "code": "emit('close');", "mods": [] }], "children": [{ "tag": "PhX", "attrs": {}, "bind": {}, "events": [], "children": [] }] }] }, { "tag": "div", "attrs": { "class": "effect-picker__particles" }, "bind": { "aria-label": "(gwText('Particle types'))" }, "events": [{ "event": "mouseleave", "code": "hovered = undefined;", "mods": [] }], "children": [{ "tag": "button", "attrs": { "type": "button" }, "bind": { "key": "(id)", "aria-pressed": "(particle === id)" }, "events": [{ "event": "mouseenter", "code": "hovered = id;", "mods": [] }, { "event": "focus", "code": "hovered = id;", "mods": [] }, { "event": "click", "code": "emit('choose', id);", "mods": [] }], "children": [{ "tag": "component", "attrs": {}, "bind": { "is": "(icon)" }, "events": [], "children": [] }, { "tag": "span", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(effectLabels[`lighting.particles.${id}`])" }] }], "each": { "names": ["icon", "id"], "value": "(icons)" } }], "when": "(kind === 'particle')" }, { "tag": "template", "attrs": {}, "bind": {}, "events": [], "children": [{ "tag": "div", "attrs": { "class": "effect-picker__presets", "role": "listbox" }, "bind": { "aria-label": "(gwText('Shader presets'))" }, "events": [{ "event": "mouseleave", "code": "hovered = undefined;", "mods": [] }], "children": [{ "tag": "button", "attrs": { "type": "button", "role": "option" }, "bind": { "key": "(preset.id)", "data-shader-preset": "(preset.id)", "aria-selected": "(shader === preset.id)", "title": "(preset.description)" }, "events": [{ "event": "mouseenter", "code": "hovered = preset.id;", "mods": [] }, { "event": "focus", "code": "hovered = preset.id;", "mods": [] }, { "event": "click", "code": "emit('choose', preset.id);", "mods": [] }], "children": [{ "tag": "span", "attrs": { "class": "effect-picker__swatch" }, "bind": { "style": "({ '--preset-color': preset.color })" }, "events": [], "children": [] }, { "tag": "span", "attrs": { "class": "effect-picker__label" }, "bind": {}, "events": [], "children": [{ "tag": "strong", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(preset.name)" }] }, { "tag": "small", "attrs": {}, "bind": {}, "events": [], "children": [{ "value": "(preset.category)" }] }] }], "each": { "names": ["preset"], "value": "(shaderPresets)" } }] }, { "tag": "button", "attrs": { "class": "effect-picker__custom", "type": "button" }, "bind": { "aria-pressed": "(!shader)" }, "events": [{ "event": "mouseenter", "code": "hovered = '';", "mods": [] }, { "event": "focus", "code": "hovered = '';", "mods": [] }, { "event": "click", "code": "emit('choose', '');", "mods": [] }], "children": [{ "tag": "PhCodeBlock", "attrs": {}, "bind": {}, "events": [], "children": [] }, { "value": "(gwText('Custom shader'))" }] }], "otherwise": true }] }], (options, { ref, computed, watch, onMounted, onBeforeUnmount, nextTick, defineExpose }) => {
    const HttpClient = options.HttpClient;
    const BlockStateApi = class {
        command(_c, _b, a, b, p) { return options.command(a, b, p); }
        state() { return options.read(); }
    };
    const props = options.props;
    const emit = options.emit;
    const icons = { smoke: PhCloud, ember: PhFireSimple, dust: PhDotsThreeOutline, arcane: PhSparkle, rain: PhCloudRain, snow: PhSnowflake, firefly: PhLightbulb, leaves: PhLeaf, bubbles: PhCirclesThreePlus, ash: PhWind, blood: PhDrop, runes: PhPentagram };
    const title = computed(() => props.kind === 'particle' ? gwText('Particles') : gwText('Shader presets'));
    const hovered = ref();
    const previewChoice = computed(() => hovered.value ?? (props.kind === 'particle' ? props.particle : props.shader));
    const previewLabel = computed(() => props.kind === 'particle' ? effectLabels[`lighting.particles.${previewChoice.value}`] ?? gwText('Particles') : shaderPresets.find(p => p.id === previewChoice.value)?.name ?? gwText('Custom shader'));
    const panel = ref();
    const position = ref({ left: '13px', bottom: '89px' });
    function place() { const trigger = document.querySelector(`[data-effect-tool="${props.kind}"]`); if (!trigger)
        return; const r = trigger.getBoundingClientRect(); const width = panel.value?.getBoundingClientRect().width ?? (props.kind === 'shader' ? 754 : 430); position.value = { left: `${Math.max(8, Math.min(innerWidth - width - 8, r.left))}px`, bottom: `${innerHeight - r.top + 8}px` }; }
    function outside(event) { if (event.target instanceof Element && !panel.value?.contains(event.target) && !event.target.closest('[data-effect-tool]'))
        emit('close'); }
    onMounted(() => { place(); window.addEventListener('resize', place); document.addEventListener('pointerdown', outside); });
    onBeforeUnmount(() => { window.removeEventListener('resize', place); document.removeEventListener('pointerdown', outside); });
    return { gwText, PhCloud, PhFireSimple, PhDotsThreeOutline, PhSparkle, PhCloudRain, PhSnowflake, PhLightbulb, PhLeaf, PhCirclesThreePlus, PhWind, PhDrop, PhPentagram, PhCode, PhCodeBlock, PhX, shaderPresets, effectLabels, EffectPreview, icons, title, hovered, previewChoice, previewLabel, panel, position, place, outside, emit: options.emit };
});
