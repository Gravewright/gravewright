import test from 'node:test';
import assert from 'node:assert/strict';
import { performance } from 'node:perf_hooks';
import { wallJoinGeometry } from './wall-joins.js';

const wall = (id, a, b, extra = {}) => ({ id, layerId: 'base', assetId: 'stone', thickness: 1,
    x1: a[0], y1: a[1], x2: b[0], y2: b[1], ...extra });
const spans = walls => walls.map(item => ({ wall: item, x1: item.x1, y1: item.y1, x2: item.x2, y2: item.y2 }));
const world = frame => frame.polygons.map(ring => ring.map(([x, y]) => [frame.origin.x + x * frame.direction.x - y * frame.direction.y,
    frame.origin.y + x * frame.direction.y + y * frame.direction.x]));
const area = ring => Math.abs(ring.reduce((sum, a, index) => { const b = ring[(index + 1) % ring.length]; return sum + a[0] * b[1] - a[1] * b[0]; }, 0)) / 2;
function contains(ring, x, y) {
    let inside = false;
    for (let index = 0, previous = ring.length - 1; index < ring.length; previous = index++) {
        const a = ring[previous], b = ring[index];
        if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) inside = !inside;
    }
    return inside;
}
const ownersAt = (geometry, x, y) => [...geometry].filter(([, frame]) => world(frame).some(ring => contains(ring, x, y))).map(([id]) => id);

test('isolated walls preserve authored direction and a detached source remains untouched', () => {
    const walls = [wall('reverse', [8, 2], [1, 2])], doc = { walls, doors: [] }, before = structuredClone(doc);
    const frame = wallJoinGeometry(doc, spans(walls)).get('reverse');
    assert.deepEqual(frame.origin, { x: 8, y: 2 }); assert.deepEqual(frame.direction, { x: -1, y: 0 });
    assert.equal(frame.phase, 0); assert.equal(frame.polygons.length, 1); assert.equal(area(frame.polygons[0]), 7);
    assert.deepEqual(doc, before);
});

test('touching and reversed compatible collinears share a canonical frame without resetting at a split', () => {
    const walls = [wall('first', [1, 3], [4, 3]), wall('second', [8, 3], [4, 3])];
    const result = wallJoinGeometry({ walls, doors: [] }, spans(walls));
    for (const frame of result.values()) {
        assert.deepEqual(frame.origin, { x: 1, y: 3 }); assert.deepEqual(frame.direction, { x: 1, y: 0 }); assert.equal(frame.phase, 0);
    }
    assert.deepEqual(result.get('second').polygons[0].map(point => point[0]).sort((a, b) => a - b), [3, 3, 7, 7]);
    const different = structuredClone(walls); different[1].assetId = 'wood';
    assert.deepEqual(wallJoinGeometry({ walls: different, doors: [] }, spans(different)).get('second').origin, { x: 8, y: 3 });
});

test('L miters meet on one diagonal without the missing outside square or overlapping caps', () => {
    const walls = [wall('east', [2, 2], [6, 2]), wall('south', [6, 2], [6, 6])];
    const result = wallJoinGeometry({ walls, doors: [] }, spans(walls));
    assert.ok(Math.abs([...result.values()].flatMap(frame => frame.polygons).reduce((sum, ring) => sum + area(ring), 0) - 8) < 1e-9);
    for (const [x, y] of [[6.25, 1.75], [5.75, 2.25], [6.25, 2.25], [5.75, 1.75]])
        assert.equal(ownersAt(result, x + .013, y + .019).length, 1, [x, y]);
    assert.equal(ownersAt(result, 6.6, 1.4).length, 0);
});

test('T endpoints split the through-wall virtually and fill the center once', () => {
    const walls = [wall('through', [1, 4], [9, 4]), wall('branch', [5, 4], [5, 8])];
    const result = wallJoinGeometry({ walls, doors: [] }, spans(walls));
    assert.equal(walls.length, 2);
    for (const [x, y] of [[4.75, 3.75], [5.25, 3.75], [4.75, 4.25], [5.25, 4.25], [5.25, 4.75]])
        assert.equal(ownersAt(result, x + .013, y + .019).length, 1, [x, y]);
    const total = [...result.values()].flatMap(frame => frame.polygons).reduce((sum, ring) => sum + area(ring), 0);
    assert.ok(Math.abs(total - 11.5) < 1e-9, total);
});

test('junctions never cross project layers and material changes do not prevent geometry joining', () => {
    const walls = [wall('east', [2, 2], [6, 2]), wall('south', [6, 2], [6, 6], { assetId: 'wood' })];
    assert.equal(ownersAt(wallJoinGeometry({ walls, doors: [] }, spans(walls)), 6.25, 1.75).length, 1);
    walls[1].layerId = 'other';
    assert.equal(ownersAt(wallJoinGeometry({ walls, doors: [] }, spans(walls)), 6.25, 1.75).length, 0);
});

test('door cuts remain hard caps and retain the original texture origin on both sides', () => {
    const source = wall('source', [1, 3], [11, 3]), branch = wall('branch', [4.5, 3], [4.5, 6]);
    const doc = { walls: [source, branch], doors: [wall('door', [2.5, 3], [4.5, 3])] };
    const result = wallJoinGeometry(doc, [{ wall: source, x1: 1, y1: 3, x2: 2.5, y2: 3 },
        { wall: source, x1: 4.5, y1: 3, x2: 11, y2: 3 }, ...spans([branch])]);
    assert.deepEqual(result.get('source').origin, { x: 1, y: 3 });
    assert.equal(ownersAt(result, 3.5, 2.8).length, 0);
    assert.equal(ownersAt(result, 4.25, 2.75).length, 0, 'a join must not extend the cut end into the opening');
});

test('acute and unequal-thickness joins remain finite, bounded and within each texture strip', () => {
    const walls = [wall('one', [2, 2], [12, 2], { thickness: .2 }), wall('two', [2, 2], [12, 2.01], { thickness: 1 })];
    for (const [id, frame] of wallJoinGeometry({ walls, doors: [] }, spans(walls))) {
        const half = walls.find(item => item.id === id).thickness / 2;
        for (const ring of frame.polygons) for (const [x, y] of ring) {
            assert.ok(Number.isFinite(x) && Number.isFinite(y)); assert.ok(Math.abs(y) <= half + 1e-7, [id, x, y]);
            assert.ok(x >= -2.000001 && x <= 12.000001);
        }
    }
});

test('legacy collinear overlaps and duplicate reversed sources render once, including a T on the trimmed boundary', () => {
    const walls = [wall('first', [1, 4], [6, 4]), wall('overlap', [10, 4], [4, 4]),
        wall('duplicate', [6, 4], [1, 4]), wall('branch', [6, 4], [6, 8])];
    const doc = { walls, doors: [] }, before = structuredClone(doc), result = wallJoinGeometry(doc, spans(walls));
    assert.deepEqual(doc, before);
    assert.equal(result.get('duplicate').polygons.length, 0);
    for (const [x, y] of [[4.25, 4.25], [5.75, 3.75], [6.25, 4.25], [6.25, 4.75], [9.25, 3.75]])
        assert.equal(ownersAt(result, x + .013, y + .019).length, 1, [x, y]);
});

test('a diagonal door crossing a node does not suppress joins on unrelated wall lines', () => {
    const walls = [wall('east', [1, 3], [5, 3]), wall('south', [5, 3], [5, 7])];
    const baseline = wallJoinGeometry({ walls, doors: [] }, spans(walls));
    const actual = wallJoinGeometry({ walls, doors: [wall('door', [4, 2], [6, 4])] }, spans(walls));
    assert.deepEqual(actual, baseline);
    assert.equal(ownersAt(actual, 5.25, 2.75).length, 1);
});

test('a collinear independent door on another layer still keeps its opening edge hard', () => {
    const walls = [wall('east', [1, 3], [5, 3]), wall('south', [5, 3], [5, 7])];
    const result = wallJoinGeometry({ walls, doors: [wall('door', [5, 3], [7, 3], { layerId: 'other' })] }, spans(walls));
    assert.equal(ownersAt(result, 5.25, 2.75).length, 0);
});

test('two thousand segments build a bounded derived mesh without pairwise full-document scans', t => {
    const walls = [];
    for (let index = 0; index < 1000; index++) {
        const x = index % 50 * 4, y = Math.floor(index / 50) * 8 + 2;
        walls.push(wall(`${index}-a`, [x, y], [x + 2, y]), wall(`${index}-b`, [x + 2, y], [x + 2, y + 2]));
    }
    const start = performance.now(), result = wallJoinGeometry({ walls, doors: [] }, spans(walls));
    assert.equal(result.size, 2000);
    t.diagnostic(`2000-segment mesh: ${(performance.now() - start).toFixed(3)} ms observed, no timing assertion`);
});
