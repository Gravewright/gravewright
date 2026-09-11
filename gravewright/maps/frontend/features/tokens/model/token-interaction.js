export function hitToken(point, tokens, cell) { return [...tokens].reverse().find(t => point.x >= t.gridX * cell && point.x <= (t.gridX + t.cells) * cell && point.y >= t.gridY * cell && point.y <= (t.gridY + (t.heightCells ?? t.cells)) * cell); }
export function inMarquee(token, a, b, cell) { const x = (token.gridX + token.cells / 2) * cell, y = (token.gridY + (token.heightCells ?? token.cells) / 2) * cell; return x >= Math.min(a.x, b.x) && x <= Math.max(a.x, b.x) && y >= Math.min(a.y, b.y) && y <= Math.max(a.y, b.y); }
export function position(token, delta, cell, width, height, grid) { return { gridX: Math.max(0, Math.min(Math.max(0, width / cell - token.cells), grid ? Math.round(token.gridX + delta.x / cell) : token.gridX + delta.x / cell)), gridY: Math.max(0, Math.min(Math.max(0, height / cell - (token.heightCells ?? token.cells)), grid ? Math.round(token.gridY + delta.y / cell) : token.gridY + delta.y / cell)) }; }
/** Same constant-elevation segment test as the authoritative server. */
export function movementBlocked(token, to, walls, cell) {
    const a = { x: (token.gridX + token.cells / 2) * cell, y: (token.gridY + (token.heightCells ?? token.cells) / 2) * cell }, b = { x: (to.gridX + token.cells / 2) * cell, y: (to.gridY + (token.heightCells ?? token.cells) / 2) * cell }, rx = b.x - a.x, ry = b.y - a.y;
    return walls.some(w => {
        if (w.movement_behavior === 'pass' || (w.kind === 'door' && w.door_state === 'open') || (w.vertical_bottom != null && (token.elevation ?? 0) < w.vertical_bottom) || (w.vertical_top != null && (token.elevation ?? 0) > w.vertical_top))
            return false;
        const sx = w.x2 - w.x1, sy = w.y2 - w.y1, den = rx * sy - ry * sx;
        if (Math.abs(den) < 1e-9)
            return false;
        const qx = w.x1 - a.x, qy = w.y1 - a.y, t = (qx * sy - qy * sx) / den, u = (qx * ry - qy * rx) / den;
        return t >= 0 && t <= 1 && u >= 0 && u <= 1;
    });
}
