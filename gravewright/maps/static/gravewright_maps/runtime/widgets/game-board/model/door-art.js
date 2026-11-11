// widgets/game-board/model/door-art.js
function doorArt(wall) {
  if (wall.kind !== "door") return;
  const appearance = wall.blueprintAppearance;
  let assetId;
  if (appearance !== void 0) {
    if (!appearance || appearance.visible !== true) return;
    assetId = appearance.assetId;
  } else {
    if (wall.door_state === "open" && wall.rotationAnchor === void 0) return;
    assetId = wall.asset_id;
  }
  if (typeof assetId !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(assetId)) return;
  const dx = wall.x2 - wall.x1, dy = wall.y2 - wall.y1;
  const width = Math.hypot(dx, dy), height = wall.thickness ?? 14;
  if (![wall.x1, wall.y1, width, height].every(Number.isFinite) || width <= 0 || height <= 0 || height > 512) return;
  let x = wall.x1, y = wall.y1, angle = Math.atan2(dy, dx) * 180 / Math.PI;
  if (wall.door_state === "open" && ["start", "center", "end"].includes(wall.rotationAnchor)) {
    const offset = wall.rotationAnchor === "start" ? 0 : wall.rotationAnchor === "end" ? 1 : 0.5;
    const pivotX = x + dx * offset, pivotY = y + dy * offset;
    x = pivotX - (wall.y1 - pivotY);
    y = pivotY + (wall.x1 - pivotX);
    angle += 90;
  }
  return { src: `/game/map-assets/${assetId}`, x, y, width, height, angle };
}
export {
  doorArt
};
