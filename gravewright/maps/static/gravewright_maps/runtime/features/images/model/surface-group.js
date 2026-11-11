// features/images/model/surface-group.js
function surfaceGroupBounds(rows, width, height) {
  const points = rows.flatMap((row) => {
    const w = row.natural_width * row.scale / 2, h = row.natural_height * row.scale / 2;
    const c = Math.cos(row.rotation * Math.PI / 180), s = Math.sin(row.rotation * Math.PI / 180);
    return [[-w, -h], [w, -h], [w, h], [-w, h]].map(([x, y]) => [row.x + x * c - y * s, row.y + x * s + y * c]);
  });
  const left = Math.max(0, Math.floor(Math.min(...points.map(([x]) => x))));
  const top = Math.max(0, Math.floor(Math.min(...points.map(([, y]) => y))));
  const right = Math.min(width, Math.ceil(Math.max(...points.map(([x]) => x))));
  const bottom = Math.min(height, Math.ceil(Math.max(...points.map(([, y]) => y))));
  if (![left, top, right, bottom].every(Number.isFinite) || (right - left) * (bottom - top) > 16777216)
    throw new TypeError("Invalid dynamic surface group.");
  return right > left && bottom > top ? { left, top, width: right - left, height: bottom - top } : null;
}
function surfaceGroupsLayout(groups, width, height) {
  if (groups.length > 32) throw new TypeError("Too many dynamic surface groups.");
  let pixels = 0;
  const result = groups.map((rows) => {
    const bounds = surfaceGroupBounds(rows, width, height);
    if (bounds) pixels += bounds.width * bounds.height;
    if (pixels > 67108864) throw new TypeError("Dynamic surface buffers exceed the pixel limit.");
    return { rows, bounds };
  });
  return result.filter((value) => value.bounds);
}
function surfaceGroupCanvas(rows, images, bounds) {
  const canvas = document.createElement("canvas");
  canvas.width = bounds.width;
  canvas.height = bounds.height;
  const context = canvas.getContext("2d");
  for (const row of [...rows].sort((a, b) => a.surfacePlane.order - b.surfacePlane.order)) {
    const image = images.get(row.id);
    if (!image) continue;
    context.save();
    context.globalCompositeOperation = row.surfacePlane.operation === "erase" ? "destination-out" : "source-over";
    context.globalAlpha = ["gm", "gm-image-layer"].includes(row.layer) ? 0.55 : 1;
    context.translate(row.x - bounds.left, row.y - bounds.top);
    context.rotate(row.rotation * Math.PI / 180);
    context.scale(row.scale, row.scale);
    context.drawImage(image, -row.natural_width / 2, -row.natural_height / 2, row.natural_width, row.natural_height);
    context.restore();
  }
  return canvas;
}
export {
  surfaceGroupBounds,
  surfaceGroupCanvas,
  surfaceGroupsLayout
};
