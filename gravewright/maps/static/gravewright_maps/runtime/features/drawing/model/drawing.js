// gravewright/maps/frontend/features/drawing/model/drawing.js
function bounds(row) {
  const xs = row.points.map((p) => p.x), ys = row.points.map((p) => p.y), pad = row.width / 2 + 2;
  const x = Math.min(...xs), y = Math.min(...ys);
  return { x: x - pad, y: y - pad, width: Math.max(1, Math.max(...xs) - x, row.kind === "text" ? row.text.length * row.fontSize * 0.65 : 0) + pad * 2, height: Math.max(1, Math.max(...ys) - y, row.kind === "text" ? row.fontSize * 1.3 : 0) + pad * 2 };
}
function translated(row, dx, dy) {
  return { ...row, points: row.points.map((p) => ({ x: p.x + dx, y: p.y + dy })) };
}
function arrowHead(row) {
  const a = row.points[0], b = row.points.at(-1), angle = Math.atan2(b.y - a.y, b.x - a.x), size = Math.max(13, row.width * 3);
  return [-0.5, 0.5].map((offset) => ({ x: b.x - Math.cos(angle + offset) * size, y: b.y - Math.sin(angle + offset) * size }));
}
function path(row) {
  const a = row.points[0], b = row.points.at(-1);
  if (row.kind === "rect")
    return `M${a.x},${a.y}H${b.x}V${b.y}H${a.x}Z`;
  if (row.kind === "ellipse") {
    const rx = Math.abs(b.x - a.x) / 2, ry = Math.abs(b.y - a.y) / 2, cx = (a.x + b.x) / 2, cy = (a.y + b.y) / 2;
    return `M${cx - rx},${cy}a${rx},${ry} 0 1,0 ${rx * 2},0a${rx},${ry} 0 1,0 ${-rx * 2},0`;
  }
  let d = row.points.map((p, i) => `${i ? "L" : "M"}${p.x},${p.y}`).join(" ");
  if (row.points.length === 1)
    d += `l0.01,0`;
  if (row.kind === "arrow")
    d += arrowHead(row).map((p) => `M${b.x},${b.y}L${p.x},${p.y}`).join("");
  return d;
}
function hit(row, p, tolerance) {
  const origin = row.points[0], r = -(row.rotation ?? 0) * Math.PI / 180, dx = p.x - origin.x, dy = p.y - origin.y;
  p = { x: origin.x + dx * Math.cos(r) - dy * Math.sin(r), y: origin.y + dx * Math.sin(r) + dy * Math.cos(r) };
  const a = row.points[0], b = row.points.at(-1), box = bounds(row), t = tolerance + row.width / 2;
  if (p.x < box.x - t || p.y < box.y - t || p.x > box.x + box.width + t || p.y > box.y + box.height + t)
    return false;
  if (row.kind === "text")
    return true;
  if (row.kind === "ellipse") {
    const rx = Math.abs(b.x - a.x) / 2, ry = Math.abs(b.y - a.y) / 2;
    if (rx < 1 || ry < 1)
      return false;
    const r2 = Math.hypot((p.x - (a.x + b.x) / 2) / rx, (p.y - (a.y + b.y) / 2) / ry);
    return row.fill !== "none" ? r2 <= 1 + t / Math.min(rx, ry) : Math.abs(r2 - 1) <= t / Math.min(rx, ry);
  }
  if (row.kind === "rect" && row.fill !== "none")
    return true;
  const points = row.kind === "rect" ? [a, { x: b.x, y: a.y }, b, { x: a.x, y: b.y }, a] : row.points;
  if (points.length === 1)
    return Math.hypot(p.x - a.x, p.y - a.y) <= t;
  return points.slice(1).some((q, i) => {
    const o = points[i], dx2 = q.x - o.x, dy2 = q.y - o.y, n = dx2 * dx2 + dy2 * dy2, k = n ? Math.max(0, Math.min(1, ((p.x - o.x) * dx2 + (p.y - o.y) * dy2) / n)) : 0;
    return Math.hypot(p.x - o.x - k * dx2, p.y - o.y - k * dy2) <= t;
  });
}
export {
  arrowHead,
  bounds,
  hit,
  path,
  translated
};
