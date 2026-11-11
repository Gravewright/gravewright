// features/measurement/model/measurement.js
import { formatNumber, text as gwText } from "../../../shared/config/i18n/text.js";
var unitsPerPixel = (cell, value) => (Number.isFinite(value) && value > 0 ? value : 1) / (Number.isFinite(cell) && cell > 0 ? cell : 70);
function dragMeasure(seed, end, constrain = false) {
  if (seed.kind === "line" && seed.points) {
    const anchor = seed.points.at(-1);
    let dx2 = end.x - seed.origin.x - anchor.x, dy2 = end.y - seed.origin.y - anchor.y;
    const distance = Math.hypot(dx2, dy2);
    if (constrain) {
      const angle = Math.round(Math.atan2(dy2, dx2) / (Math.PI / 4)) * Math.PI / 4;
      dx2 = Math.cos(angle) * distance;
      dy2 = Math.sin(angle) * distance;
    }
    const points = [...seed.points, { x: anchor.x + dx2, y: anchor.y + dy2 }];
    const length2 = points.slice(1).reduce((total, p, i) => total + Math.hypot(p.x - points[i].x, p.y - points[i].y), 0);
    return { ...seed, points, length: length2, direction: 0 };
  }
  let dx = end.x - seed.origin.x, dy = end.y - seed.origin.y;
  if (seed.kind === "rect") {
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
  return { ...seed, length, direction, width: seed.kind === "wide-cone" ? length / 3 : seed.width };
}
function measurePath(m) {
  const l = Math.max(0.01, m.length), w = Math.max(0.01, m.width);
  if (m.kind === "line")
    return m.points ? m.points.map((p, i) => `${i ? "L" : "M"}${p.x} ${p.y}`).join("") : `M0 0H${l}`;
  if (m.kind === "circle")
    return `M${-l} 0a${l} ${l} 0 1 0 ${2 * l} 0a${l} ${l} 0 1 0 ${-2 * l} 0`;
  if (m.kind === "rect")
    return `M0 0H${l}V${w}H0Z`;
  if (m.kind === "cone") {
    const half = l * Math.tan(m.angle * Math.PI / 360);
    return `M0 0L${l} ${-half}V${half}Z`;
  }
  const r = Math.min(w / 2, l * 0.49), c = l - r, tx = c - r * r / c, ty = r * Math.sqrt(Math.max(0, 1 - r * r / (c * c)));
  return `M0 0L${tx} ${-ty}A${r} ${r} 0 1 1 ${tx} ${ty}Z`;
}
function area(m) {
  if (m.kind === "line")
    return 0;
  if (m.kind === "circle")
    return Math.PI * m.length * m.length;
  if (m.kind === "rect")
    return m.length * m.width;
  if (m.kind === "cone")
    return m.length * m.length * Math.tan(m.angle * Math.PI / 360);
  const r = Math.min(m.width / 2, m.length * 0.49), c = m.length - r;
  if (c <= 0)
    return 0;
  const alpha = Math.acos(-r / c), ty = r * Math.sqrt(Math.max(0, 1 - r * r / (c * c)));
  return c * ty + r * r * alpha;
}
function summary(m, factor, unit) {
  const n = formatNumber;
  const length = m.length * factor, width = m.width * factor, measure = (v) => `${n(v)} ${unit}`.trim();
  if (m.kind === "line")
    return measure(length);
  if (m.kind === "circle")
    return `R ${measure(length)} \xB7 \xD8 ${measure(length * 2)} \xB7 ${n(area(m) * factor * factor)} ${unit}\xB2`;
  if (m.kind === "rect")
    return `${measure(length)} \xD7 ${measure(width)} \xB7 ${n(area(m) * factor * factor)} ${unit}\xB2`;
  return `${measure(length)} \xB7 ${m.kind === "cone" ? `${n(m.angle)}\xB0` : `${gwText("width")} ${measure(width)}`} \xB7 ${n(area(m) * factor * factor)} ${unit}\xB2`;
}
export {
  area,
  dragMeasure,
  measurePath,
  summary,
  unitsPerPixel
};
