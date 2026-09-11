import assert from 'node:assert/strict';
import { distancePerCell, selectedVision } from './token-vision.js';
const token = { id: 'a', actorId: 'actor', mapId: 'scene', version: 1, name: 'Hero', linkMode: 'linked', gridX: 2, gridY: 3, cells: 2, heightCells: 1, visionRange: 8, elevation: 4 };
assert.deepEqual(selectedVision([token], ['a'], 50), [{ x: 150, y: 175, radius: 400, elevation: 4 }]);
assert.deepEqual(selectedVision([token], [], 50), []);
assert.deepEqual(selectedVision([{ ...token, visionEnabled: false }], ['a'], 50), []);
assert.equal(selectedVision([{ ...token, visionRange: 0 }], ['a'], 50)[0]?.radius, 0);
assert.equal(selectedVision([token, { ...token, id: 'b', gridX: 5 }], ['a', 'b'], 50).length, 2);
// 8 cells means 40 ft on a 5 ft grid, 12 m on a 1.5 m grid, and 8 m on a 1 m grid.
for (const [scale, distance] of [[5, 40], [1.5, 12], [1, 8]]) {
    assert.equal(token.visionRange * distancePerCell(scale), distance);
    assert.equal(distance / distancePerCell(scale), token.visionRange);
}
assert.equal(distancePerCell(0), 1);
assert.equal(distancePerCell(NaN), 1);
assert.deepEqual(selectedVision([token], ['a'], 50, { x: 13, y: 7 }), [{ x: 163, y: 182, radius: 400, elevation: 4 }]);
