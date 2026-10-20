// gravewright/maps/frontend/features/regions/model/regions.js
import { normalizeRegionFilters, regionMatchesFilters, regionFilterDispositions, regionFilterVisibility } from "/static/gravewright_maps/region-filters.js";
function containsRegion(geometry, point, tolerance = 0) {
  if (!geometry || !point) return false;
  if (geometry.shape === "circle")
    return Math.hypot(point.x - geometry.x, point.y - geometry.y) <= geometry.radius + tolerance;
  if (geometry.shape === "rect")
    return point.x >= geometry.x - tolerance && point.y >= geometry.y - tolerance && point.x <= geometry.x + geometry.width + tolerance && point.y <= geometry.y + geometry.height + tolerance;
  const vertices = geometry.points || [];
  let inside = false;
  for (let i = 0, j = vertices.length - 1; i < vertices.length; j = i++) {
    const a = vertices[j], b = vertices[i], dx = b.x - a.x, dy = b.y - a.y, length = dx * dx + dy * dy;
    const t = length ? Math.max(0, Math.min(1, ((point.x - a.x) * dx + (point.y - a.y) * dy) / length)) : 0;
    if (Math.hypot(point.x - a.x - t * dx, point.y - a.y - t * dy) <= tolerance) return true;
    if (a.y > point.y !== b.y > point.y && point.x < (b.x - a.x) * (point.y - a.y) / (b.y - a.y) + a.x) inside = !inside;
  }
  return inside;
}
export {
  containsRegion,
  normalizeRegionFilters,
  regionFilterDispositions,
  regionFilterVisibility,
  regionMatchesFilters
};
