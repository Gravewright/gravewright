import { text as gwText } from '../../../shared/config/i18n/text.js';
import { bounds as drawingBounds, hit as hitDrawing } from '../../drawing/model/drawing.js';
export function rotate(p, c, degrees) { const a = degrees * Math.PI / 180, dx = p.x - c.x, dy = p.y - c.y; return { x: c.x + dx * Math.cos(a) - dy * Math.sin(a), y: c.y + dx * Math.sin(a) + dy * Math.cos(a) }; }
export function transformedPoint(p, center, dx, dy, rotation) { const q = rotate(p, center, rotation); return { x: q.x + dx, y: q.y + dy }; }
export function corners(o) { return [{ x: o.x - o.width / 2, y: o.y - o.height / 2 }, { x: o.x + o.width / 2, y: o.y - o.height / 2 }, { x: o.x + o.width / 2, y: o.y + o.height / 2 }, { x: o.x - o.width / 2, y: o.y + o.height / 2 }].map(p => rotate(p, o, o.rotation)); }
export function hit(o, p, tolerance = 5) {
    if (o.kind === 'drawing')
        return hitDrawing(o.data, p, tolerance);
    if (o.kind === 'measure') {
        const m = o.data, q = rotate(p, m.origin, -m.direction), x = q.x - m.origin.x, y = q.y - m.origin.y;
        if (m.kind === 'circle')
            return Math.hypot(x, y) <= m.length + tolerance;
        if (m.kind === 'line')
            return x >= -tolerance && x <= m.length + tolerance && Math.abs(y) <= tolerance;
        if (m.kind === 'rect')
            return x >= -tolerance && y >= -tolerance && x <= m.length + tolerance && y <= m.width + tolerance;
        if (m.kind === 'cone')
            return x >= -tolerance && x <= m.length + tolerance && Math.abs(y) <= Math.max(0, x) * Math.tan(m.angle * Math.PI / 360) + tolerance;
        const r = Math.min(m.width / 2, m.length * .49), c = m.length - r, tx = c - r * r / c, ty = r * Math.sqrt(1 - r * r / (c * c));
        return x <= tx ? x >= -tolerance && Math.abs(y) <= x * ty / Math.max(.01, tx) + tolerance : Math.hypot(x - c, y) <= r + tolerance;
    }
    if (o.kind === 'wall') {
        const a = o.points[0], b = o.points[1], dx = b.x - a.x, dy = b.y - a.y, n = dx * dx + dy * dy, t = n ? Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / n)) : 0;
        return Math.hypot(p.x - a.x - t * dx, p.y - a.y - t * dy) <= tolerance;
    }
    const q = rotate(p, o, -o.rotation);
    return Math.abs(q.x - o.x) <= o.width / 2 + tolerance && Math.abs(q.y - o.y) <= o.height / 2 + tolerance;
}
export function centerOf(rows) { const points = rows.flatMap(corners); return { x: (Math.min(...points.map(p => p.x)) + Math.max(...points.map(p => p.x))) / 2, y: (Math.min(...points.map(p => p.y)) + Math.max(...points.map(p => p.y))) / 2 }; }
export function sceneObjects(state, tokens, cell, gm, measures, origin = { x: 0, y: 0 }) {
    const out = [];
    function add(kind, data, x, y, width = 18, height = 18, rotation = 0, rank = 10, label = kind, points) { out.push({ key: `${kind}:${data.id}`, id: data.id, kind, data, x, y, width, height, rotation, rank, label, points }); }
    for (const t of tokens.filter(t => gm || t.canControl))
        add('token', t, origin.x + (t.gridX + t.cells / 2) * cell, origin.y + (t.gridY + (t.heightCells ?? t.cells) / 2) * cell, t.cells * cell, (t.heightCells ?? t.cells) * cell, 0, 30, t.name);
    for (const c of state.cards.filter(c => c.can_manage))
        add('card', c, c.x, c.y, 56 * c.scale, 80 * c.scale, c.rotation, 25, c.card?.face_state === 'face_up' ? c.card?.name || gwText('Card') : gwText('Card (back)'));
    if (gm) {
        for (const i of state.images)
            add('image', i, i.x, i.y, i.natural_width * i.scale, i.natural_height * i.scale, i.rotation, 5, gwText('Image'));
        for (const w of state.walls)
            add('wall', w, (w.x1 + w.x2) / 2, (w.y1 + w.y2) / 2, Math.hypot(w.x2 - w.x1, w.y2 - w.y1), 4, Math.atan2(w.y2 - w.y1, w.x2 - w.x1) * 180 / Math.PI, 15, gwText('Wall'), [{ x: w.x1, y: w.y1 }, { x: w.x2, y: w.y2 }]);
        for (const [kind, list] of [['light', state.lights], ['particle', state.particles], ['shader', state.shaders], ['sound', state.spatialSounds]])
            for (const o of list)
                add(kind, o, o.x, o.y, 18, 18, 0, 35, ({ get light() { return gwText('Light'); }, get particle() { return gwText('Particles'); }, shader: 'Shader', get sound() { return gwText('Audio'); } })[kind]);
        for (const d of state.drawings?.rows ?? []) {
            const b = drawingBounds(d), anchor = d.points[0], center = rotate({ x: b.x + b.width / 2, y: b.y + b.height / 2 }, anchor, d.rotation ?? 0);
            add('drawing', d, center.x, center.y, b.width, b.height, d.rotation ?? 0, 10, gwText('Drawing'));
        }
        for (const z of state.zones) {
            const g = z.geometry, points = g.shape === 'polygon' ? g.points ?? [] : g.shape === 'rect' ? [{ x: g.x ?? 0, y: g.y ?? 0 }, { x: (g.x ?? 0) + (g.width ?? 0), y: (g.y ?? 0) + (g.height ?? 0) }] : [{ x: (g.x ?? 0) - (g.radius ?? 0), y: (g.y ?? 0) - (g.radius ?? 0) }, { x: (g.x ?? 0) + (g.radius ?? 0), y: (g.y ?? 0) + (g.radius ?? 0) }];
            if (!points.length)
                continue;
            const xs = points.map(p => p.x), ys = points.map(p => p.y);
            add('zone', z, (Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2, Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys), 0, 4, gwText('Zone'));
        }
    }
    for (const m of measures) {
        let w = m.length, h = m.kind === 'rect' ? m.width : m.kind === 'cone' ? 2 * m.length * Math.tan(m.angle * Math.PI / 360) : m.kind === 'wide-cone' ? m.width : 4;
        const local = m.kind === 'circle' ? { x: 0, y: 0 } : { x: w / 2, y: m.kind === 'rect' ? h / 2 : 0 };
        if (m.kind === 'circle')
            w = h = 2 * m.length;
        const p = rotate({ x: m.origin.x + local.x, y: m.origin.y + local.y }, m.origin, m.direction);
        add('measure', m, p.x, p.y, w, h, m.direction, 12, gwText('Measurement'));
    }
    return out.sort((a, b) => a.rank - b.rank);
}
