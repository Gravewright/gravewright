import assert from 'node:assert/strict';
import { interpolateTokens, TOKEN_SETTLE_MS } from './token-motion.js';
import { position, movementBlocked } from './token-interaction.js';
import { selectedVision } from './token-vision.js';
const a = { id: 'a', actorId: 'actor', mapId: 'scene', name: 'Hero', version: 1, linkMode: 'linked', gridX: 2, gridY: 3, cells: 1 };
const b = { ...a, id: 'b', gridX: 4 };
const target = [{ ...a, gridX: 3, version: 2 }, { ...b, gridX: 5, version: 2 }];
assert.equal(TOKEN_SETTLE_MS, 120);
assert.deepEqual(interpolateTokens([a, b], target, 1), target);
const middle = interpolateTokens([a, b], target, .5);
assert.ok(middle[0].gridX > 2 && middle[0].gridX < 3);
assert.equal(middle[1].gridX - middle[0].gridX, 2);
assert.equal(middle[0].version, 2);
assert.equal(interpolateTokens(middle, target, 0)[0].gridX, middle[0].gridX);
assert.deepEqual(interpolateTokens([a, b], [], .5), []);
assert.deepEqual(interpolateTokens([], target, .5), target);
const free = position(a, { x: 21, y: 7 }, 70, 1400, 900, false);
assert.ok(Math.abs(free.gridX - 2.3) < 1e-8);
assert.equal(position({ ...a, ...free }, { x: 0, y: 0 }, 70, 1400, 900, true).gridX, 2);
assert.equal(position({ ...a, ...free }, { x: 0, y: 0 }, 70, 1400, 900, false).gridX, free.gridX);
// The same displayed positions drive vision, rather than the final server coordinates.
assert.equal(selectedVision(middle, ['a'], 70)[0].x, (middle[0].gridX + .5) * 70);
// A final snap is checked independently of the valid free-drag segment.
const at = { ...a, gridX: 2.6, gridY: 0 };
const wall = { id: 'wall', kind: 'wall', x1: 225, x2: 225, y1: -100, y2: 100 };
assert.equal(movementBlocked(at, { ...at, gridX: 3 }, [wall], 70), true);
