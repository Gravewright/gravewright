import { test } from 'node:test';
import assert from 'node:assert/strict';
import { WallRayIndex } from './wall-ray-index.js';
const walls = Array.from({ length: 80 }, (_, i) => ({ id: String(i), kind: 'wall', x1: Math.sin(i * 7) * 500, y1: Math.cos(i * 11) * 500, x2: Math.sin(i * 7 + 1) * 500, y2: Math.cos(i * 11 + 1) * 500 }));
test('BVH returns the same exact hit as exhaustive intersections, including axis-aligned rays', () => {
    const index = new WallRayIndex(walls);
    for (const origin of [{ x: 0, y: 0 }, { x: 400, y: -250 }, { x: 2000, y: 2000 }])
        for (let i = 0; i < 360; i++) {
            const dx = Math.cos(i * Math.PI / 180), dy = Math.sin(i * Math.PI / 180);
            let expected = 1400;
            for (const w of walls) {
                const sx = w.x2 - w.x1, sy = w.y2 - w.y1, den = dx * sy - dy * sx;
                if (Math.abs(den) < 1e-10)
                    continue;
                const ox = w.x1 - origin.x, oy = w.y1 - origin.y, t = (ox * sy - oy * sx) / den, u = (ox * dy - oy * dx) / den;
                if (t >= 0 && u >= 0 && u <= 1)
                    expected = Math.min(expected, t);
            }
            assert.ok(Math.abs(index.cast(origin, dx, dy, 1400) - expected) < 1e-8);
        }
    assert.equal(new WallRayIndex([]).cast({ x: 0, y: 0 }, 1, 0, 100), 100);
});
