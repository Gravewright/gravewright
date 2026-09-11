import { formatNumber, text as gwText } from "../../../shared/config/i18n/text.js";
export const unitsPerPixel = (cell, value) => (Number.isFinite(value) && value > 0 ? value : 1) / (Number.isFinite(cell) && cell > 0 ? cell : 70);
export function dragMeasure(seed, end, constrain = false) {
    let dx = end.x - seed.origin.x, dy = end.y - seed.origin.y;
    if (seed.kind === 'rect') {
        if (constrain) {
            const n = Math.max(Math.abs(dx), Math.abs(dy));
            dx = Math.sign(dx || 1) * n;
            dy = Math.sign(dy || 1) * n;
        }
        return { ...seed, origin: { x: seed.origin.x + Math.min(0, dx), y: seed.origin.y + Math.min(0, dy) }, length: Math.abs(dx), width: Math.abs(dy), direction: 0 };
    }
    let direction = Math.atan2(dy, dx) * 180 / Math.PI;
    if (constrain)
        direction = Math.round(direction / 45) * 45;
    const length = Math.hypot(dx, dy);
    return { ...seed, length, direction, width: seed.kind === 'wide-cone' ? length / 3 : seed.width };
}
export function measurePath(m) {
    const l = Math.max(.01, m.length), w = Math.max(.01, m.width);
    if (m.kind === 'line')
        return `M0 0H${l}`;
    if (m.kind === 'circle')
        return `M${-l} 0a${l} ${l} 0 1 0 ${2 * l} 0a${l} ${l} 0 1 0 ${-2 * l} 0`;
    if (m.kind === 'rect')
        return `M0 0H${l}V${w}H0Z`;
    if (m.kind === 'cone') {
        const half = l * Math.tan(m.angle * Math.PI / 360);
        return `M0 0L${l} ${-half}V${half}Z`;
    }
    // Tangents from the origin to a circular cap: a rounded template, not a circular sector.
    const r = Math.min(w / 2, l * .49), c = l - r, tx = c - r * r / c, ty = r * Math.sqrt(Math.max(0, 1 - r * r / (c * c)));
    return `M0 0L${tx} ${-ty}A${r} ${r} 0 1 1 ${tx} ${ty}Z`;
}
export function area(m) {
    if (m.kind === 'line')
        return 0;
    if (m.kind === 'circle')
        return Math.PI * m.length * m.length;
    if (m.kind === 'rect')
        return m.length * m.width;
    if (m.kind === 'cone')
        return m.length * m.length * Math.tan(m.angle * Math.PI / 360);
    const r = Math.min(m.width / 2, m.length * .49), c = m.length - r;
    if (c <= 0)
        return 0;
    const alpha = Math.acos(-r / c), ty = r * Math.sqrt(Math.max(0, 1 - r * r / (c * c)));
    return c * ty + r * r * alpha;
}
export function summary(m, factor, unit) {
    const n = formatNumber;
    const length = m.length * factor, width = m.width * factor, measure = (v) => `${n(v)} ${unit}`.trim();
    if (m.kind === 'line')
        return measure(length);
    if (m.kind === 'circle')
        return `R ${measure(length)} · Ø ${measure(length * 2)} · ${n(area(m) * factor * factor)} ${unit}²`;
    if (m.kind === 'rect')
        return `${measure(length)} × ${measure(width)} · ${n(area(m) * factor * factor)} ${unit}²`;
    return `${measure(length)} · ${m.kind === 'cone' ? `${n(m.angle)}°` : `${gwText('width')} ${measure(width)}`} · ${n(area(m) * factor * factor)} ${unit}²`;
}
