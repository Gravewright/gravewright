import { text as gwText } from '../../../shared/config/i18n/text.js';
const solid = { movement: 'block', vision: 'block', light: 'block', sound: 'block' };
export const wallPresets = [
    { id: 'normal', get name() { return gwText('Wall'); }, color: '#d6b578', get description() { return gwText('Blocks movement, vision, light, and sound.'); }, presentation: 'normal', behavior: { ...solid } },
    { id: 'secret', get name() { return gwText('Secret'); }, color: '#b58ce0', get description() { return gwText('Hides what is behind it but allows tokens to pass.'); }, presentation: 'secret', behavior: { ...solid, movement: 'pass', sound: 'pass' } },
    { id: 'elevation', get name() { return gwText('Elevation'); }, color: '#d8a373', get description() { return gwText('Blocks only within the configured height range.'); }, presentation: 'normal', behavior: { ...solid }, vertical: { bottom: 0, top: 3 } },
    { id: 'window', get name() { return gwText('Window'); }, color: '#86d0e6', get description() { return gwText('Allows vision and light through; blocks tokens and attenuates sound.'); }, presentation: 'window', behavior: { movement: 'block', vision: 'pass', light: 'pass', sound: 'attenuate' } },
    { id: 'bars', get name() { return gwText('Fence'); }, color: '#a7bccb', get description() { return gwText('Blocks tokens; allows vision, light, and sound through.'); }, presentation: 'bars', behavior: { movement: 'block', vision: 'pass', light: 'pass', sound: 'pass' } },
    { id: 'invisible', get name() { return gwText('Invisible barrier'); }, color: '#8ab7ff', get description() { return gwText('Blocks movement only. Its marker is visible only to the GM.'); }, presentation: 'invisible', behavior: { movement: 'block', vision: 'pass', light: 'pass', sound: 'pass' } },
];
export function wallPreset(w) { return wallPresets.find(p => p.id === (w.vertical_bottom != null || w.vertical_top != null ? 'elevation' : w.presentation ?? 'normal')) ?? wallPresets[0]; }
export function wallPayload(w) { return { kind: w.kind, x1: w.x1, y1: w.y1, x2: w.x2, y2: w.y2, presentation: w.presentation ?? 'normal', behavior: { movement: w.movement_behavior ?? 'block', vision: w.vision_behavior ?? 'block', light: w.light_behavior ?? 'block', sound: w.sound_behavior ?? 'block' }, vertical: { bottom: w.vertical_bottom ?? null, top: w.vertical_top ?? null } }; }
export function project(p, w) { const dx = w.x2 - w.x1, dy = w.y2 - w.y1, t = Math.max(0, Math.min(1, ((p.x - w.x1) * dx + (p.y - w.y1) * dy) / (dx * dx + dy * dy || 1))); return { x: w.x1 + t * dx, y: w.y1 + t * dy }; }
export function hitWall(p, walls, tolerance) { return [...walls].reverse().find(w => { const q = project(p, w); return Math.hypot(q.x - p.x, q.y - p.y) <= tolerance; }); }
export function hitNode(p, walls, tolerance, exclude) {
    let best;
    for (const wall of walls)
        for (const endpoint of [1, 2]) {
            const x = wall[`x${endpoint}`], y = wall[`y${endpoint}`], distance = Math.hypot(p.x - x, p.y - y);
            if (exclude && Math.hypot(x - exclude.x, y - exclude.y) <= 1)
                continue;
            if (distance <= tolerance) {
                best = { wall, endpoint, x, y };
                tolerance = distance;
            }
        }
    return best;
}
export function snap(p, walls, tolerance, cell, grid, exclude) { const node = hitNode(p, walls, tolerance, exclude); return node ? { x: node.x, y: node.y } : grid ? { x: Math.round(p.x / cell) * cell, y: Math.round(p.y / cell) * cell } : p; }
export function enclosed(w, a, b) { return [1, 2].every(n => w[`x${n}`] >= Math.min(a.x, b.x) && w[`x${n}`] <= Math.max(a.x, b.x) && w[`y${n}`] >= Math.min(a.y, b.y) && w[`y${n}`] <= Math.max(a.y, b.y)); }
