/** Convert PDF coordinates (including rotated/reversed axes) into overlay bounds. */
export function fieldBounds(viewport, rect, offsetTop = 0) {
    const [x1, y1] = viewport.convertToViewportPoint(rect[0], rect[1]);
    const [x2, y2] = viewport.convertToViewportPoint(rect[2], rect[3]);
    return { left: Math.min(x1, x2), top: Math.min(y1, y2) + offsetTop,
        width: Math.abs(x2 - x1), height: Math.abs(y2 - y1), hidden: false };
}
