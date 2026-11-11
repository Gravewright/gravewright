// native/builder-editor-model.js
import { defaults } from "../features/effects/model/effects.js";
import { PARTICLE_DEFAULTS } from "../features/effects/model/particle-profiles.js";
import { shaderPresets } from "../features/scene-layers/lib/shader-presets.js";
var fields = {
  lights: ["bright_radius", "dim_radius", "intensity", "color", "enabled", "angle", "rotation", "animation"],
  particles: ["kind", "scale", "density", "color", "enabled", "rotation", "light_response", "light_emission"],
  shaders: ["name", "source", "radius", "scale", "intensity", "opacity", "speed", "color", "rotation", "blend_mode", "enabled", "light_response", "light_emission"]
};
var radiusFields = { bright_radius: "brightRadius", dim_radius: "dimRadius" };
var presetSource = /^gravewright-preset:\/\/([^/]+)\/v1$/;
function builderNativeDraft(kind, item) {
  if (!Object.hasOwn(fields, kind)) throw new Error("Invalid effect.");
  const draft = { ...defaults(), ...structuredClone(item) };
  if (kind === "lights") {
    draft.bright_radius = item.brightRadius;
    draft.dim_radius = item.dimRadius;
  } else if (kind === "shaders") {
    const match = presetSource.exec(draft.source);
    if (match) {
      const preset = shaderPresets.find((value) => value.id === match[1]);
      if (!preset) throw new Error("Unknown shader preset.");
      draft.source = preset.source;
    }
  }
  return draft;
}
function validateBuilderNativeDraft(kind, draft) {
  if (!Object.hasOwn(fields, kind)) throw new Error("Invalid effect.");
  const invalid = kind === "lights" ? "Invalid light." : "Invalid effect.";
  const ranges = kind === "lights" ? { bright_radius: [0, 200], dim_radius: [0, 200], intensity: [0, 1], angle: [5, 360], rotation: [-36e3, 36e3] } : {
    scale: [0.1, 20],
    rotation: [-36e3, 36e3],
    light_response: [0, 1],
    light_emission: [0, 2],
    ...kind === "particles" ? { density: [0, 1] } : { radius: [0, 1e6], intensity: [0, 1], opacity: [0, 1], speed: [0, 8] }
  };
  for (const [key, [min, max]] of Object.entries(ranges)) {
    if (typeof draft[key] !== "number" || !Number.isFinite(draft[key]) || draft[key] < min || draft[key] > max) throw new Error(invalid);
  }
  if (typeof draft.enabled !== "boolean" || !/^#[0-9a-f]{6}$/i.test(draft.color)) throw new Error(invalid);
  if (kind === "lights" && !["none", "torch", "pulse", "candle", "fire", "arcane", "smoke"].includes(draft.animation)) throw new Error(invalid);
  if (kind === "particles" && !Object.hasOwn(PARTICLE_DEFAULTS, draft.kind)) throw new Error(invalid);
  if (kind === "shaders") {
    if (typeof draft.name !== "string" || !draft.name.trim() || draft.name.length > 120) throw new Error("Use a name with 1 to 120 characters.");
    if (!["normal", "add", "screen", "multiply"].includes(draft.blend_mode)) throw new Error(invalid);
    if (typeof draft.source !== "string" || !draft.source.trim() || draft.source.length > 32e3 || draft.source.includes("\0")) throw new Error("Invalid shader source.");
  }
}
function builderNativeItem(kind, original, draft) {
  validateBuilderNativeDraft(kind, draft);
  const initial = builderNativeDraft(kind, original), next = structuredClone(original);
  const normalized = { ...draft, rotation: (draft.rotation % 360 + 360) % 360 };
  if (kind === "lights" && normalized.dim_radius > 0) normalized.dim_radius = Math.max(normalized.dim_radius, normalized.bright_radius);
  for (const key of fields[kind]) {
    if (Object.is(normalized[key], initial[key])) continue;
    let value = normalized[key];
    if (key === "name") value = value.trim();
    if (key === "source") {
      const preset = shaderPresets.find((entry) => entry.source === value);
      if (preset) value = `gravewright-preset://${preset.id}/v1`;
    }
    next[kind === "lights" ? radiusFields[key] || key : key] = value;
  }
  return next;
}
export {
  builderNativeDraft,
  builderNativeItem,
  validateBuilderNativeDraft
};
