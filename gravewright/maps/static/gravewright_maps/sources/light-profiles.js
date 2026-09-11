// gravewright/maps/frontend/shared/config/i18n/text.js
var listeners = /* @__PURE__ */ new Set();
function notifyTextChange() {
  for (const listener of listeners)
    listener();
}
var currentLocale = () => "en";
var resolve = (source) => source;
function registerTextResolver(resolver, locale = () => "en") {
  resolve = resolver;
  currentLocale = locale;
  notifyTextChange();
  return () => {
    if (resolve === resolver) {
      resolve = (source) => source;
      currentLocale = () => "en";
      notifyTextChange();
    }
  };
}
function text(source, ...values) {
  return resolve(source).replace(/\{(\d+)\}/g, (match, index) => Number(index) < values.length ? String(values[Number(index)]) : match);
}
if (typeof window !== "undefined") {
  const apply = (detail) => registerTextResolver((source) => {
    const translated = detail.messages?.text?.[source];
    return typeof translated === "string" ? translated : source;
  }, () => detail.id || "en");
  window.addEventListener("gravewright:locale", (event) => apply(event.detail));
  if (window.gravewrightLocale) apply(window.gravewrightLocale);
}

// gravewright/maps/frontend/features/lighting/model/light-profiles.js
var lightPresets = [
  { id: "torch", get name() {
    return text("Torch");
  }, bright_radius: 2, dim_radius: 5, intensity: 0.9, color: "#ff9a3c", angle: 360 },
  { id: "pulse", get name() {
    return text("Pulse");
  }, bright_radius: 2, dim_radius: 5, intensity: 0.9, color: "#55aaff", angle: 360 },
  { id: "none", get name() {
    return text("Steady");
  }, bright_radius: 2, dim_radius: 4, intensity: 0.85, color: "#ffd8a8", angle: 360 }
];
function lightAnimation(light, now) {
  let hash = 0;
  for (const c of light.id)
    hash = (hash * 31 + c.charCodeAt(0)) % 9973;
  const phase = hash / 9973 * Math.PI * 2;
  if (light.animation === "pulse") {
    const wave = 0.5 + 0.5 * Math.sin(now * 2 * Math.PI / 2800 + phase);
    return 0.9 + 0.1 * wave * wave * (3 - 2 * wave);
  }
  if (["torch", "candle", "fire"].includes(light.animation ?? "")) {
    const wave = 0.5 + 0.5 * (0.5 * Math.sin(now * 2 * Math.PI / 1300 + phase) + 0.32 * Math.sin(now * 2 * Math.PI / 620 + phase * 2) + 0.18 * Math.sin(now * 2 * Math.PI / 350 + phase * 3));
    return 0.92 + 0.08 * wave;
  }
  return 1;
}
var falloffs = /* @__PURE__ */ new Map();
function falloff(color, flame) {
  const key = `${color}:${flame}`;
  if (falloffs.has(key)) return falloffs.get(key);
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 256;
  const ctx = canvas.getContext("2d"), image = ctx.createImageData(256, 256);
  const base = parseInt(color.slice(1), 16);
  const channels = [base >> 16 & 255, base >> 8 & 255, base & 255];
  const luma = 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
  const tint = channels.map((c) => Math.round(luma + (c - luma) * 0.7));
  for (let y = 0; y < 256; y++) for (let x = 0; x < 256; x++) {
    const dx = (x - 128) / 128, dy = (y - 128) / 128;
    const distance = Math.hypot(dx, dy), angle = Math.atan2(dy, dx);
    if (distance >= 1) continue;
    const wave = Math.sin(angle * 6 + 0.6 * Math.sin(angle * 6));
    const shrink = flame ? 0.26 * (0.5 + 0.5 * wave) * Math.min(1, distance / 0.25) : 0;
    const reach = Math.min(1, distance / Math.max(0.05, 1 - shrink));
    const i = (y * 256 + x) * 4;
    image.data.set([...tint, Math.round((1 - reach) ** 2 * 255)], i);
  }
  ctx.putImageData(image, 0, 0);
  if (falloffs.size >= 32) falloffs.delete(falloffs.keys().next().value);
  falloffs.set(key, canvas);
  return canvas;
}
function paintLight(ctx, light, x, y, radius) {
  paintAnimatedLight(ctx, { ...light, animation: "none" }, x, y, radius, 0);
}
function paintAnimatedLight(ctx, light, x, y, radius, now) {
  let hash = 0;
  for (const c of light.id) hash = (hash * 31 + c.charCodeAt(0)) % 9973;
  const phase = hash / 9973 * Math.PI * 2;
  const torch = ["torch", "candle", "fire"].includes(light.animation);
  const animated = torch || light.animation === "pulse";
  const flame = (p) => 0.5 + 0.5 * (0.5 * Math.sin(now * 2 * Math.PI / (1300 * 0.7) + p) + 0.32 * Math.sin(now * 2 * Math.PI / (620 * 0.7) + p * 2) + 0.18 * Math.sin(now * 2 * Math.PI / (350 * 0.7) + p * 3));
  const shape = (p) => {
    if (torch) return flame(p * 1.3 + 0.9);
    const wave = 0.5 + 0.5 * Math.sin(now * 2 * Math.PI / 2800 + p);
    return wave * wave * (3 - 2 * wave);
  };
  const bright = light.dim_radius > 0 ? light.bright_radius / light.dim_radius : 0.05;
  const layers = torch ? [{ scale: 1, phase: 0, weight: 0.5 }, { scale: 0.62, phase: 2.1, weight: 0.4 }] : [{ scale: 1, phase: 0, weight: animated ? 0.55 : 0.5 }];
  const angle = (light.angle ?? 360) * Math.PI / 180;
  ctx.save();
  ctx.translate(x, y);
  if (angle < Math.PI * 2) {
    const direction = (light.rotation ?? 0) * Math.PI / 180;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.arc(0, 0, radius, direction - angle / 2, direction + angle / 2);
    ctx.closePath();
    ctx.clip();
  }
  ctx.globalCompositeOperation = "lighter";
  if (torch) {
    const reach = radius * (bright || 1) * 0.05;
    ctx.translate(Math.sin(now / 340 + phase) * reach, Math.sin(now / 470 + phase * 2) * reach);
  }
  const factor = light.intensity * lightAnimation(light, now);
  for (const [index, layer] of layers.entries()) {
    const p = phase + layer.phase;
    const r = radius * layer.scale * (animated ? 1 + 0.3 * (shape(p) - 0.5) * 2 : 1);
    ctx.save();
    if (animated) ctx.translate(Math.sin(now / (380 + index * 47) + p) * radius * 0.025, Math.sin(now / (530 + index * 61) + p * 1.7) * radius * 0.018);
    if (torch) ctx.rotate((now / 1e3 * 0.05 * Math.PI * 2 + phase) * (index % 2 ? -1.6 : 1));
    ctx.globalAlpha = factor * layer.weight;
    ctx.drawImage(falloff(light.color, torch), -r, -r, r * 2, r * 2);
    ctx.restore();
  }
  if (bright > 0) {
    const r = radius * bright;
    ctx.globalAlpha = factor * 0.45;
    ctx.drawImage(falloff(light.color, false), -r, -r, r * 2, r * 2);
  }
  ctx.restore();
}
export {
  lightAnimation,
  lightPresets,
  paintAnimatedLight,
  paintLight
};
