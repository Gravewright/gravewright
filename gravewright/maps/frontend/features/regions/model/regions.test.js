import test from 'node:test';
import assert from 'node:assert/strict';
import { containsRegion } from './regions.js';

test('circular region picking excludes the bounding box corners', () => {
    const circle = { shape: 'circle', x: 40, y: 50, radius: 10 };
    assert.equal(containsRegion(circle, { x: 49, y: 59 }), false);
    assert.equal(containsRegion(circle, { x: 50, y: 50 }), true);
    assert.equal(containsRegion(circle, { x: 51, y: 50 }, 1), true);
});

test('polygon region picking respects concave areas and includes edge tolerance', () => {
    const polygon = { shape: 'polygon', points: [{ x: 0, y: 0 }, { x: 20, y: 0 },
        { x: 20, y: 10 }, { x: 10, y: 10 }, { x: 10, y: 20 }, { x: 0, y: 20 }] };
    assert.equal(containsRegion(polygon, { x: 5, y: 15 }), true);
    assert.equal(containsRegion(polygon, { x: 15, y: 15 }), false);
    assert.equal(containsRegion(polygon, { x: 10, y: 15 }), true);
    assert.equal(containsRegion(polygon, { x: 11, y: 15 }, 1), true);
});
