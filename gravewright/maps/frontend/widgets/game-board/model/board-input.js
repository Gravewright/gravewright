/** How long a press has to hold still before it drops a ping on the board. */
export const LONG_PRESS_MS = 700;
/** Past this many pixels the press is a drag, not a ping. */
export const MOVE_THRESHOLD = 10;
export const MIN_SCALE = 0.35;
export const MAX_SCALE = 3.2;
const ZOOM_STEP = 1.15;
/** True once the pointer has travelled far enough that the gesture stops being a press. */
export function movedBeyondThreshold(origin, current, threshold = MOVE_THRESHOLD) {
    return Math.hypot(current.x - origin.x, current.y - origin.y) > threshold;
}
/**
 * Zooms around the pointer instead of the stage origin, so the pixel under the cursor stays put.
 * `deltaY` follows the wheel convention: negative scrolls in.
 */
export function zoomAround(pointer, position, scale, deltaY) {
    const anchor = { x: (pointer.x - position.x) / scale, y: (pointer.y - position.y) / scale };
    const next = Math.max(MIN_SCALE, Math.min(MAX_SCALE, scale * (deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP)));
    return { scale: next, position: { x: pointer.x - anchor.x * next, y: pointer.y - anchor.y * next } };
}
