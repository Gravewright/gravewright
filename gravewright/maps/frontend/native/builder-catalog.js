/** Builder authoring uses the table's catalogs and persisted native fields. */
import { lightPresets } from '../features/lighting/model/light-profiles.js';
import { PARTICLE_DEFAULTS } from '../features/effects/model/particle-profiles.js';
import { effectLabels } from '../features/effects/model/legacy-labels.js';
import { shaderPresets } from '../features/scene-layers/lib/shader-presets.js';
import { defaults, payload } from '../features/effects/model/effects.js';

export { lightPresets, shaderPresets, PARTICLE_DEFAULTS as particleDefaults };
export { effectLights } from '../widgets/game-board/model/effect-lighting.js';
export const particlePresets = Object.entries(PARTICLE_DEFAULTS).map(([id, fields]) => ({
    id, get name() { return effectLabels[`lighting.particles.${id}`] || id; }, ...fields,
}));

export function createLight(id = 'torch', x = 0, y = 0) {
    const preset = lightPresets.find(value => value.id === id);
    if (!preset) throw new Error('Unknown light preset.');
    return { x, y, brightRadius: preset.bright_radius, dimRadius: preset.dim_radius,
        intensity: preset.intensity, color: preset.color, angle: preset.angle,
        rotation: 0, animation: id, enabled: true };
}
export function createParticle(kind = 'smoke', x = 0, y = 0) {
    if (!Object.hasOwn(PARTICLE_DEFAULTS, kind)) throw new Error('Unknown particle preset.');
    return payload('particle', { ...defaults(), ...PARTICLE_DEFAULTS[kind], kind, x, y,
        light_response: ['smoke', 'dust', 'rain', 'snow', 'leaves', 'bubbles', 'ash', 'blood'].includes(kind) ? .8 : 0,
        light_emission: ['ember', 'firefly', 'arcane', 'runes'].includes(kind) ? .15 : 0 });
}
export function createShader(id = 'orb-1', x = 0, y = 0) {
    const preset = shaderPresets.find(value => value.id === id);
    if (!preset) throw new Error('Unknown shader preset.');
    // Native preset URIs preserve the table's reviewed preset source contract.
    return payload('shader', { ...defaults(), scale: 1, color: '#8fb6ff', ...preset,
        source: `gravewright-preset://${id}/v1`, x, y });
}
