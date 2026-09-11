// gravewright/maps/frontend/calibration.js
var gwText = (text) => text;
var median = (values) => {
  const sorted = [...values].sort((a, b) => a - b), middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
};
function calculateCalibration(samples) {
  if (samples.length !== 3 || samples.some((s) => Object.values(s).some((v) => !Number.isFinite(v)) || s.width < 1 || s.height < 1))
    throw new Error(gwText("Mark three complete cells."));
  const roughSize = median(samples.flatMap((s) => [s.width, s.height]));
  const origin = samples[0], end = samples[2];
  const spanX = end.x + end.width - origin.x, spanY = end.y + end.height - origin.y;
  const columns = Math.round(spanX / roughSize), rows = Math.round(spanY / roughSize);
  if (columns < 2 || rows < 2)
    throw new Error(gwText("Mark the last cell below and to the right of the first."));
  if (samples.some((s) => Math.abs(s.width - roughSize) > roughSize * 0.35 || Math.abs(s.height - roughSize) > roughSize * 0.35))
    throw new Error(gwText("Mark a single cell of similar size at each step."));
  let size = (spanX + spanY) / (columns + rows);
  if (Math.abs(size - Math.round(size)) <= Math.max(0.08, size * 25e-4))
    size = Math.round(size);
  const offset = (value) => {
    const n = (value % size + size) % size;
    return Math.min(n, size - n) <= Math.max(0.75, size * 0.01) ? 0 : n;
  };
  return { size, offsetX: offset(origin.x), offsetY: offset(origin.y) };
}
function calibrationSettings(value, imageScale) {
  if (!Number.isFinite(imageScale) || imageScale <= 0)
    throw new Error(gwText("Invalid image scale."));
  return { gridSize: Number((value.size / imageScale).toFixed(4)), gridOffsetX: Number((value.offsetX / imageScale).toFixed(3)), gridOffsetY: Number((value.offsetY / imageScale).toFixed(3)), gridVisible: true };
}
export {
  calculateCalibration,
  calibrationSettings
};
