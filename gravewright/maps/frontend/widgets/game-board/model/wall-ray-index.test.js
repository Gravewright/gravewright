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

test('a shared index filters inclusive wall heights only when an elevation is supplied', () => {
    const walls = [
        { x1: 10, x2: 10, y1: -20, y2: 20, vertical_bottom: 2, vertical_top: 3 },
        { x1: 20, x2: 20, y1: -20, y2: 20, vertical_bottom: -2, vertical_top: 0 },
        { x1: 30, x2: 30, y1: -20, y2: 20 },
    ];
    const index = new WallRayIndex(walls), origin = { x: 0, y: 0 };
    for (const [height, expected] of [[-3, 30], [-2, 20], [0, 20], [1, 30], [2, 10], [3, 10], [4, 30]])
        assert.equal(index.cast(origin, 1, 0, 100, height), expected);
    assert.equal(index.cast({ ...origin, elevation: 4 }, 1, 0, 100), 10);
    assert.equal(index.cast(origin, 1, 0, 5, 2), 5);
});

test('repeated casts reset their reusable traversal stack and retain nearest-hit ties', () => {
    const walls = Array.from({ length: 100 }, (_, i) => ({ x1: 10 + i, x2: 10 + i, y1: -200, y2: 200 }));
    walls.push({ x1: 10, x2: 10, y1: -100, y2: 100 });
    const index = new WallRayIndex(walls), stack = index.stack;
    for (let i = 0; i < 100; i++) {
        assert.equal(index.cast({ x: 0, y: 0 }, 1, 0, 1000), 10);
        assert.equal(index.cast({ x: 0, y: 0 }, -1, 0, 1000), 1000);
        assert.equal(index.cast({ x: 0, y: 0 }, 1e-13, 1, 1000), 1000);
        assert.equal(index.cast({ x: 10, y: 0 }, 1, 0, 1000), 0);
    }
    assert.equal(index.stack, stack);
});
