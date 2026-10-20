// gravewright/maps/frontend/widgets/game-board/model/board-input.js
var LONG_PRESS_MS = 700;
var MOVE_THRESHOLD = 10;
var MIN_SCALE = 0.35;
var MAX_SCALE = 3.2;
var ZOOM_STEP = 1.15;
function movedBeyondThreshold(origin, current, threshold = MOVE_THRESHOLD) {
  return Math.hypot(current.x - origin.x, current.y - origin.y) > threshold;
}
function zoomAround(pointer, position, scale, deltaY) {
  const anchor = { x: (pointer.x - position.x) / scale, y: (pointer.y - position.y) / scale };
  const next = Math.max(MIN_SCALE, Math.min(MAX_SCALE, scale * (deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP)));
  return { scale: next, position: { x: pointer.x - anchor.x * next, y: pointer.y - anchor.y * next } };
}
export {
  LONG_PRESS_MS,
  MAX_SCALE,
  MIN_SCALE,
  MOVE_THRESHOLD,
  movedBeyondThreshold,
  zoomAround
};
