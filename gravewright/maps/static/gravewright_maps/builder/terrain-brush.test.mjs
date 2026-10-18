import test from 'node:test';
import assert from 'node:assert/strict';
import { terrainBrushAlpha, terrainBrushBounds, terrainBrushMask, terrainBrushError, terrainBrushLimits } from './terrain-brush.js';

const floor = (overrides = {}) => ({ id: 'stroke', assetId: 'stone', x: 2, y: 3, width: 4, height: 4,
    brush: { operation: 'paint', points: [[.5, .5, .5]], radius: [.5, .5], hardness: 0 }, ...overrides });

test('radial strength falls smoothly outside hardness and repeated dabs accumulate the entire profile', () => {
    const item = floor(), before = structuredClone(item);
    assert.equal(terrainBrushAlpha(item, { x: 4, y: 5 }), 128 / 255);
    assert.equal(terrainBrushAlpha(item, { x: 5, y: 5 }), 64 / 255);
    assert.equal(terrainBrushAlpha(item, { x: 6, y: 5 }), 0);
    item.brush.points.push([.5, .5, .5]);
    assert.equal(terrainBrushAlpha(item, { x: 4, y: 5 }), 192 / 255);
    assert.equal(terrainBrushAlpha(item, { x: 5, y: 5 }), 112 / 255, 'dwell does not collapse into one stronger linear gradient');
    item.brush.hardness = 1;
    assert.equal(terrainBrushAlpha(item, { x: 5.9, y: 5 }), 192 / 255);
    assert.equal(terrainBrushAlpha(item, { x: 6, y: 5 }), 0);
    assert.deepEqual(before.brush.points, [[.5, .5, .5]]);
});

test('the byte raster samples absolute pixel centers and retains fractional bbox placement', () => {
    const item = floor({ x: .125, y: .375, width: 2.25, height: 1.5 });
    const before = structuredClone(item), bounds = terrainBrushBounds(item, 16), mask = terrainBrushMask(item, 16);
    assert.deepEqual(bounds, { left: 2, top: 6, width: 36, height: 24 });
    assert.equal(mask.alpha.length, bounds.width * bounds.height);
    for (let row = 0; row < bounds.height; row++) for (let column = 0; column < bounds.width; column++) {
        const point = { x: (bounds.left + column + .5) / 16, y: (bounds.top + row + .5) / 16 };
        assert.ok(Math.abs(mask.alpha[row * bounds.width + column] - terrainBrushAlpha(item, point) * 255) <= 1);
    }
    assert.deepEqual(item, before);
    item.brush.operation = 'erase'; item.assetId = null;
    assert.deepEqual(terrainBrushMask(item, 16).alpha, mask.alpha, 'erase changes compositing, never the kernel');
});

test('strict brush fields, finite local coordinates, radius and ownership reject malformed source', () => {
    const changes = [null, {}, { ...floor().brush, operation: 'smudge' }, { ...floor().brush, extra: 1 },
        { ...floor().brush, radius: [0, .5] }, { ...floor().brush, radius: [.5, Infinity] },
        { ...floor().brush, points: [[.5, .5, true]] }, { ...floor().brush, points: [[-.1, .5, 1]] },
        { ...floor().brush, hardness: NaN }, { ...floor().brush, points: [] }, { ...floor().brush, operation: 'erase' }];
    for (const brush of changes) assert.equal(terrainBrushError({ cellSize: 32 }, [floor({ brush })]), 'Invalid floor brush.');
    assert.equal(terrainBrushError({ cellSize: 32 }, [floor({ brush: { ...floor().brush, radius: [10000, 10000], points: [[.5, .5, 0]] } })]), null);
    assert.equal(terrainBrushError({ cellSize: NaN }, []), 'Invalid floor brush.');
});

test('dab, document and clipped raster budgets are checked before allocating oversized buffers', () => {
    const item = floor(); item.brush.points = Array.from({ length: terrainBrushLimits.dabs }, () => [.5, .5, 0]);
    assert.equal(terrainBrushError({ cellSize: 16 }, [item]), null);
    item.brush.points.push([.5, .5, 0]);
    assert.equal(terrainBrushError({ cellSize: 16 }, [item]), 'The map has too many terrain brush dabs.');
    item.brush.points.pop();
    assert.equal(terrainBrushError({ cellSize: 16 }, Array(5).fill(item)), 'The map has too many terrain brush dabs.');
    const huge = floor({ x: 0, y: 0, width: 200, height: 200 });
    assert.equal(terrainBrushError({ cellSize: 256 }, [huge]), 'The map terrain brushes are too complex.');
    assert.throws(() => terrainBrushMask(huge, 256), { name: 'RangeError', message: 'The map terrain brushes are too complex.' });
});
