function phaseOf(id) { let hash = 0; for (let i = 0; i < id.length; i++)
    hash = (hash * 31 + id.charCodeAt(i)) % 9973; return hash / 9973 * Math.PI * 2; }
export const PARTICLE_KINDS = {
    smoke: {
        count: 22, life: 6200, rise: 2.4, spread: 0.5, drift: 0.55,
        size: 0.4, grow: 2.4, alpha: 0.28, blend: "normal", color: "#9aa3ad",
    },
    ember: {
        count: 26, life: 2300, rise: 2.2, spread: 0.42, drift: 0.3,
        size: 0.08, grow: 0.4, alpha: 0.95, blend: "add", color: "#ff9040",
    },
    dust: {
        count: 30, life: 8000, rise: 0.25, spread: 0.9, drift: 0.9,
        size: 0.05, grow: 0.1, alpha: 0.35, blend: "normal", color: "#d8cdb4",
    },
    arcane: {
        count: 16, life: 4200, rise: 0, orbit: 0.62, spread: 1, drift: 0,
        size: 0.07, grow: 0.2, alpha: 0.8, blend: "add", color: "#c9a6ff",
    },
    rain: {
        count: 46, life: 1350, rise: -3.8, spread: 0.95, drift: 0.08, wind: 0.7,
        size: 0.16, grow: 0, aspect: 0.12, alpha: 0.62, blend: "screen", color: "#9bc9e8", rotation: -0.18,
    },
    snow: {
        count: 38, life: 7200, rise: -0.75, spread: 1.1, drift: 0.85, wind: 0.22,
        size: 0.07, grow: 0.25, alpha: 0.8, blend: "normal", color: "#edf7ff",
    },
    firefly: {
        count: 18, life: 5600, rise: 0, orbit: 0.38, spread: 1, drift: 0.35,
        size: 0.055, grow: 0.15, alpha: 0.95, pulse: 3.5, blend: "add", color: "#ffe46b",
    },
    leaves: {
        count: 24, life: 6800, rise: -0.9, spread: 1.15, drift: 1.1, wind: 0.5,
        size: 0.12, grow: 0.05, aspect: 0.55, spin: 8, alpha: 0.72, blend: "normal", color: "#a87035",
    },
    bubbles: {
        count: 22, life: 5200, rise: 1.5, spread: 0.7, drift: 0.7,
        size: 0.08, grow: 0.65, alpha: 0.48, blend: "screen", color: "#8de8ff",
    },
    ash: {
        count: 34, life: 9000, rise: -0.35, spread: 1.25, drift: 1.0, wind: 0.35,
        size: 0.045, grow: 0.1, aspect: 0.65, spin: 5, alpha: 0.5, blend: "normal", color: "#77736e",
    },
    blood: {
        count: 28, life: 1800, burst: true, spread: 1.2, gravity: 1.9, wind: 0.08,
        size: 0.07, grow: 0.35, aspect: 0.5, spin: 7, alpha: 0.9, blend: "normal", color: "#a10f20",
    },
    runes: {
        count: 12, life: 6400, rise: 0, orbit: 0.42, spread: 0.82, drift: 0,
        size: 0.11, grow: 0, aspect: 0.35, spin: -2, pulse: 2.2, alpha: 0.9, blend: "add", color: "#69a7ff",
    },
};
export const PARTICLE_DEFAULTS = {
    smoke: { scale: 3, density: 0.6, color: "#9aa3ad" },
    ember: { scale: 2, density: 0.5, color: "#ff9040" },
    dust: { scale: 6, density: 0.45, color: "#d8cdb4" },
    arcane: { scale: 2.5, density: 0.6, color: "#c9a6ff" },
    rain: { scale: 8, density: 0.7, color: "#9bc9e8" },
    snow: { scale: 8, density: 0.65, color: "#edf7ff" },
    firefly: { scale: 5, density: 0.55, color: "#ffe46b" },
    leaves: { scale: 7, density: 0.55, color: "#a87035" },
    bubbles: { scale: 4, density: 0.6, color: "#8de8ff" },
    ash: { scale: 8, density: 0.6, color: "#77736e" },
    blood: { scale: 3, density: 0.7, color: "#a10f20" },
    runes: { scale: 3, density: 0.65, color: "#69a7ff" },
};
export function particlesOf(emitter, now, cellSize) {
    const spec = PARTICLE_KINDS[emitter.kind];
    if (!spec || !(cellSize > 0))
        return [];
    if (!emitter.enabled)
        return [];
    const scale = Math.max(0.5, Number(emitter.scale) || 1);
    const density = Math.max(0, Math.min(1, Number(emitter.density ?? 0.6)));
    const count = Math.round(spec.count * density);
    const seed = phaseOf(emitter.id || "");
    const reach = cellSize * scale;
    const angle = (emitter.rotation || 0) * Math.PI / 180;
    const out = [];
    for (let index = 0; index < count; index += 1) {
        const own = (index * 0.6180339887 + seed) % 1;
        const age = ((now / spec.life + own) % 1 + 1) % 1;
        const around = own * Math.PI * 2;
        const sway = Math.sin(now / 900 + around * 3) * (spec.drift || 0);
        const orbit = spec.orbit || 0;
        const radial = spec.burst
            ? { x: Math.cos(around) * spec.spread * age,
                y: Math.sin(around) * spec.spread * age + (spec.gravity || 0) * age * age }
            : orbit
                ? { x: Math.cos(around + now / 1000 * orbit) * spec.spread,
                    y: Math.sin(around + now / 1000 * orbit) * spec.spread * 0.6 }
                : { x: Math.sin(around) * spec.spread * (0.35 + age) + sway * age,
                    y: -(spec.rise || 0) * age };
        radial.x += (spec.wind || 0) * age;
        const fade = Math.sin(age * Math.PI);
        out.push({
            age,
            x: emitter.x + (radial.x * Math.cos(angle) - radial.y * Math.sin(angle)) * reach,
            y: emitter.y + (radial.x * Math.sin(angle) + radial.y * Math.cos(angle)) * reach,
            size: spec.size * (1 + spec.grow * age) * reach,
            alpha: spec.alpha * fade * (spec.pulse ? 0.55 + 0.45 * Math.sin(now / 1000 * spec.pulse + around * 5) : 1),
            tint: emitter.color || spec.color,
            blend: spec.blend,
            aspect: spec.aspect || 1,
            rotation: angle + (spec.rotation ?? (around + age * (spec.spin || (orbit ? 2 : 0.8)))),
        });
    }
    return out;
}
