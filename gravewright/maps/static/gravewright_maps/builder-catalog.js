// native/builder-catalog.js
import { lightPresets } from "./runtime/features/lighting/model/light-profiles.js";
import { PARTICLE_DEFAULTS } from "./runtime/features/effects/model/particle-profiles.js";
import { effectLabels } from "./runtime/features/effects/model/legacy-labels.js";
import { shaderPresets } from "./runtime/features/scene-layers/lib/shader-presets.js";
import { defaults, payload } from "./runtime/features/effects/model/effects.js";
import { effectLights } from "./runtime/widgets/game-board/model/effect-lighting.js";
var particlePresets = Object.entries(PARTICLE_DEFAULTS).map(([id, fields]) => ({
  id,
  get name() {
    return effectLabels[`lighting.particles.${id}`] || id;
  },
  ...fields
}));
function createLight(id = "torch", x = 0, y = 0) {
  const preset = lightPresets.find((value) => value.id === id);
  if (!preset) throw new Error("Unknown light preset.");
  return {
    x,
    y,
    brightRadius: preset.bright_radius,
    dimRadius: preset.dim_radius,
    intensity: preset.intensity,
    color: preset.color,
    angle: preset.angle,
    rotation: 0,
    animation: id,
    enabled: true
  };
}
function createParticle(kind = "smoke", x = 0, y = 0) {
  if (!Object.hasOwn(PARTICLE_DEFAULTS, kind)) throw new Error("Unknown particle preset.");
  return payload("particle", {
    ...defaults(),
    ...PARTICLE_DEFAULTS[kind],
    kind,
    x,
    y,
    light_response: ["smoke", "dust", "rain", "snow", "leaves", "bubbles", "ash", "blood"].includes(kind) ? 0.8 : 0,
    light_emission: ["ember", "firefly", "arcane", "runes"].includes(kind) ? 0.15 : 0
  });
}
function createShader(id = "orb-1", x = 0, y = 0) {
  const preset = shaderPresets.find((value) => value.id === id);
  if (!preset) throw new Error("Unknown shader preset.");
  return payload("shader", {
    ...defaults(),
    scale: 1,
    color: "#8fb6ff",
    ...preset,
    source: `gravewright-preset://${id}/v1`,
    x,
    y
  });
}
export {
  createLight,
  createParticle,
  createShader,
  effectLights,
  lightPresets,
  PARTICLE_DEFAULTS as particleDefaults,
  particlePresets,
  shaderPresets
};
