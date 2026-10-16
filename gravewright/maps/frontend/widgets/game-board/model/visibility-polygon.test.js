import assert from "node:assert/strict";
import { test } from "node:test";
import { createVisibilityContext, visibilityPolygon } from "./visibility-polygon.js";
import { WallRayIndex } from "./wall-ray-index.js";
const wall = { id: "wall", x1: 10, x2: 10, y1: -100, y2: 100, kind: "wall" };
const polygon = visibilityPolygon({ x: 0, y: 0 }, 50, [wall]);
assert.ok(polygon.every(p => p.x <= 10.0001));
const open = visibilityPolygon({ x: 0, y: 0 }, 50, [{ ...wall, kind: "door", door_state: "open" }]);
assert.ok(open.some(p => p.x > 40));
assert.ok(open.every(p => Math.hypot(p.x, p.y) <= 50.0001));
const angles = polygon.map(p => (Math.atan2(p.y, p.x) + Math.PI * 2) % (Math.PI * 2));
assert.ok(angles.every((a, i) => i === 0 || a >= angles[i - 1] - 1e-10));
const cone = visibilityPolygon({ x: 0, y: 0, angle: 90, rotation: 0 }, 50, [wall]);
assert.ok(cone.every(p => p.x >= -1e-8 && p.x <= 10.0001 && Math.abs(p.y) <= p.x + 1e-8));
const rotated = visibilityPolygon({ x: 0, y: 0, angle: 60, rotation: 180 }, 50, []);
assert.ok(rotated.slice(1, -1).every(p => p.x < 0 && Math.abs(p.y) <= 25.0001));
// Elevation intervals are inclusive and do not change unbounded legacy walls.
const low = { ...wall, vertical_bottom: 0, vertical_top: 3 };
assert.ok(visibilityPolygon({ x: 0, y: 0, elevation: 3 }, 50, [low]).every(p => p.x <= 10.0001));
assert.ok(visibilityPolygon({ x: 0, y: 0, elevation: 4 }, 50, [low]).some(p => p.x > 40));
assert.ok(visibilityPolygon({ x: 0, y: 0, elevation: -1 }, 50, [low]).some(p => p.x > 40));
assert.ok(visibilityPolygon({ x: 0, y: 0, elevation: 400 }, 50, [wall]).every(p => p.x <= 10.0001));
assert.ok(visibilityPolygon({ x: 0, y: 0 }, 50, [{ ...wall, vision_behavior: 'pass' }]).some(p => p.x > 40));

// The previous recursive traversal is retained as a differential oracle. In
// particular, it uses a fresh index over each source's filtered walls.
function originalCast(index, origin, dx, dy, radius) {
    let distance = radius;
    const entry = node => {
        let near = 0, far = distance;
        for (const [p, d, min, max] of [[origin.x, dx, node.minX, node.maxX], [origin.y, dy, node.minY, node.maxY]]) {
            if (Math.abs(d) < 1e-12) {
                if (p < min || p > max)
                    return Infinity;
                continue;
            }
            const a = (min - p) / d, b = (max - p) / d;
            near = Math.max(near, Math.min(a, b));
            far = Math.min(far, Math.max(a, b));
            if (near > far)
                return Infinity;
        }
        return near;
    };
    const visit = node => {
        if (entry(node) > distance)
            return;
        if (node.walls) {
            for (const w of node.walls) {
                const sx = w.x2 - w.x1, sy = w.y2 - w.y1, den = dx * sy - dy * sx;
                if (Math.abs(den) < 1e-10)
                    continue;
                const ox = w.x1 - origin.x, oy = w.y1 - origin.y;
                const t = (ox * sy - oy * sx) / den, u = (ox * dy - oy * dx) / den;
                if (t >= 0 && u >= 0 && u <= 1)
                    distance = Math.min(distance, t);
            }
            return;
        }
        if (entry(node.left) <= entry(node.right)) {
            visit(node.left);
            visit(node.right);
        }
        else {
            visit(node.right);
            visit(node.left);
        }
    };
    if (index.root)
        visit(index.root);
    return distance;
}

function originalPolygon(origin, radius, walls) {
    const elevation = origin.elevation ?? 0;
    const segments = walls.filter(w => (w.vertical_bottom == null || elevation >= w.vertical_bottom) && (w.vertical_top == null || elevation <= w.vertical_top) && Math.max(w.x1, w.x2) >= origin.x - radius && Math.min(w.x1, w.x2) <= origin.x + radius && Math.max(w.y1, w.y2) >= origin.y - radius && Math.min(w.y1, w.y2) <= origin.y + radius && w.door_state !== "open" && w.blocks_sight !== 0 && w.vision_behavior !== "pass");
    const index = new WallRayIndex(segments);
    const angles = Array.from({ length: 128 }, (_, i) => i * Math.PI * 2 / 128);
    for (const w of segments)
        for (const p of [{ x: w.x1, y: w.y1 }, { x: w.x2, y: w.y2 }]) {
            const a = Math.atan2(p.y - origin.y, p.x - origin.x);
            angles.push(a - 0.00001, a, a + 0.00001);
        }
    const cone = (origin.angle ?? 360) < 360, direction = (origin.rotation ?? 0) * Math.PI / 180, half = (origin.angle ?? 360) * Math.PI / 360;
    const relative = angle => Math.atan2(Math.sin(angle - direction), Math.cos(angle - direction));
    if (cone)
        angles.push(direction - half, direction + half);
    const points = angles.filter(a => !cone || Math.abs(relative(a)) <= half + 1e-9)
        .map(a => (a + Math.PI * 2) % (Math.PI * 2))
        .sort((a, b) => cone ? relative(a) - relative(b) : a - b)
        .map(angle => {
            const dx = Math.cos(angle), dy = Math.sin(angle), distance = originalCast(index, origin, dx, dy, radius);
            return { x: origin.x + dx * distance, y: origin.y + dy * distance };
        });
    return cone ? [{ x: origin.x, y: origin.y }, ...points, { x: origin.x, y: origin.y }] : points;
}

test("shared wall index exactly preserves polygons across doors, heights, ranges and cones", () => {
    let seed = 0x81f923;
    const random = () => ((seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0) / 2 ** 32);
    const walls = Array.from({ length: 240 }, (_, i) => {
        const x1 = random() * 2000 - 1000, y1 = random() * 2000 - 1000;
        return {
            id: String(i), x1, y1, x2: x1 + random() * 500 - 250, y2: y1 + random() * 500 - 250,
            door_state: i % 7 === 0 ? "open" : "closed", blocks_sight: i % 11 === 0 ? 0 : 1,
            vision_behavior: i % 13 === 0 ? "pass" : "block",
            vertical_bottom: i % 3 === 0 ? -2 : null, vertical_top: i % 4 === 0 ? 3 : null,
        };
    });
    const context = createVisibilityContext(walls), index = context.index;
    for (let i = 0; i < 60; i++) {
        const source = { x: random() * 2400 - 1200, y: random() * 2400 - 1200, elevation: [-3, -2, 0, 3, 4][i % 5], angle: [360, 90, 180, 1, 270][i % 5], rotation: random() * 1080 - 540 };
        const radius = [0, 80, 450, 4000][i % 4];
        const expected = originalPolygon(source, radius, walls);
        assert.deepEqual(visibilityPolygon(source, radius, walls, context), expected, `shared source ${i}`);
        assert.deepEqual(visibilityPolygon(source, radius, walls), expected, `standalone source ${i}`);
        assert.equal(context.index, index);
    }
});

test("shared index preserves endpoint, collinear, overlapping and radius-boundary rays", () => {
    const walls = [
        { x1: 10, y1: -20, x2: 10, y2: 20 },
        { x1: 10, y1: -20, x2: 10, y2: 20 },
        { x1: 0, y1: 0, x2: 20, y2: 0 },
        { x1: -10, y1: 0, x2: 0, y2: 0 },
        { x1: 0, y1: 0, x2: 0, y2: 0 },
        { x1: -10, y1: 10, x2: 10, y2: 10, vertical_bottom: 2, vertical_top: 2 },
        { x1: -10, y1: -10, x2: 10, y2: -10, door_state: "open" },
        ...Array.from({ length: 24 }, (_, i) => ({ x1: 100 + i, y1: -50, x2: 100 + i, y2: 50 })),
    ];
    const context = createVisibilityContext(walls);
    for (const source of [{ x: 0, y: 0 }, { x: 10, y: 20, elevation: 2 }, { x: 10, y: 0, angle: 90, rotation: -180 }, { x: 0, y: 0, elevation: 3 }])
        for (const radius of [0, 10, 20, 1000])
            assert.deepEqual(visibilityPolygon(source, radius, walls, context), originalPolygon(source, radius, walls));
});

test("rebuilding the context observes changed door, blocking and geometry data", () => {
    const walls = [{ ...wall, door_state: "open" }];
    assert.ok(visibilityPolygon({ x: 0, y: 0 }, 50, walls, createVisibilityContext(walls)).some(p => p.x > 40));
    walls[0].door_state = "closed";
    assert.ok(visibilityPolygon({ x: 0, y: 0 }, 50, walls, createVisibilityContext(walls)).every(p => p.x <= 10.0001));
    walls[0].vision_behavior = "pass";
    assert.ok(visibilityPolygon({ x: 0, y: 0 }, 50, walls, createVisibilityContext(walls)).some(p => p.x > 40));
    walls[0].vision_behavior = "block";
    walls[0].x1 = walls[0].x2 = 20;
    assert.ok(visibilityPolygon({ x: 0, y: 0 }, 50, walls, createVisibilityContext(walls)).every(p => p.x <= 20.0001));
});

test("finite-range room corners retain the previous filtered-tree rounding", () => {
    const walls = [], push = (x1, y1, x2, y2) => walls.push({ x1, y1, x2, y2 });
    for (let row = 0; row < 5; row++)
        for (let column = 0; column < 10; column++) {
            const x = column * 700, y = row * 1000;
            push(x, y, x + 300, y); push(x + 400, y, x + 700, y);
            push(x, y + 1000, x + 300, y + 1000); push(x + 400, y + 1000, x + 700, y + 1000);
            push(x, y, x, y + 450); push(x, y + 550, x, y + 1000);
            push(x + 700, y, x + 700, y + 450); push(x + 700, y + 550, x + 700, y + 1000);
        }
    const source = { x: 3580, y: 2510 }, context = createVisibilityContext(walls);
    assert.deepEqual(visibilityPolygon(source, 1200, walls, context), originalPolygon(source, 1200, walls));
    const cached = [...context.subsets.values()];
    assert.equal(cached.length, 1);
    assert.deepEqual(visibilityPolygon(source, 1200, walls, context), originalPolygon(source, 1200, walls));
    assert.deepEqual([...context.subsets.values()], cached);
});

test("moving sources cannot retain an unbounded number of filtered wall indices", () => {
    const walls = Array.from({ length: 80 }, (_, i) => ({ x1: i * 20, x2: i * 20, y1: -100, y2: 100 }));
    const context = createVisibilityContext(walls);
    for (let i = 0; i < 40; i++) {
        const source = { x: i * 25 + 1, y: 0 };
        assert.deepEqual(visibilityPolygon(source, 60, walls, context), originalPolygon(source, 60, walls));
        assert.ok(context.subsets.size <= 8);
    }
});
