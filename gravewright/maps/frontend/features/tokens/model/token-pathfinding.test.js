import assert from 'node:assert/strict';
import { suggestTokenRoute } from './token-pathfinding.js';
import { routeMeasurements } from './token-route.js';
import { movementBlocked } from './token-interaction.js';
const token = { id: 'a', actorId: 'actor', mapId: 'scene', name: 'Hero', version: 1, linkMode: 'linked', gridX: 0, gridY: 0, cells: 1 };
const first = [token], last = [{ ...token, gridX: 4 }];
const chosen = [first, [{ ...token, gridY: 6 }], [{ ...token, gridX: 4, gridY: 6 }], last];
const limits = { milliseconds: 1000 };
const original = structuredClone(chosen);
assert.deepEqual(suggestTokenRoute(chosen, [], 10, 80, 80, limits), [first, last]);
assert.deepEqual(chosen, original, 'Suggestions must never overwrite the selected route');
assert.equal(suggestTokenRoute([first, last], [], 10, 80, 80, limits), undefined, 'Equal routes have no alternate CTA');
const wall = { id: 'wall', kind: 'wall', x1: 20, y1: 0, x2: 20, y2: 30 };
const alternative = suggestTokenRoute(chosen, [wall], 10, 80, 80, limits);
assert.ok(alternative && alternative.length > 2, 'A* must go around the blocked direct segment');
assert.deepEqual(alternative[0], first);
assert.deepEqual(alternative.at(-1), last);
assert.ok(routeMeasurements(alternative, 5).total < routeMeasurements(chosen, 5).total);
for (let i = 1; i < alternative.length; i++)
    assert.equal(movementBlocked(alternative[i - 1][0], alternative[i][0], [wall], 10), false);
assert.equal(suggestTokenRoute(chosen, [{ ...wall, y2: 80 }], 10, 80, 80, limits), undefined, 'A sealed wall has no valid route');
assert.equal(suggestTokenRoute(chosen, [wall], 10, 80, 80, { nodes: 0 }), undefined, 'Search budget failure preserves the chosen path');
assert.deepEqual(suggestTokenRoute(chosen, [{ ...wall, kind: 'door', door_state: 'open' }], 10, 80, 80, limits), [first, last]);
assert.deepEqual(suggestTokenRoute(chosen, [{ ...wall, movement_behavior: 'pass' }], 10, 80, 80, limits), [first, last]);
assert.deepEqual(suggestTokenRoute(chosen, [{ ...wall, vertical_bottom: 10 }], 10, 80, 80, limits), [first, last]);
const fractional = chosen.map(step => step.map(t => ({ ...t, gridX: t.gridX + .2, gridY: t.gridY + .1 })));
fractional.at(-1)[0].gridX = 4.7;
const exact = suggestTokenRoute(fractional, [wall], 10, 80, 80, limits);
assert.ok(exact);
assert.equal(exact.at(-1)[0].gridX, 4.7);
const group = chosen.map(step => [step[0], { ...step[0], id: 'b', gridY: step[0].gridY + 1 }]);
const groupPath = suggestTokenRoute(group, [wall], 10, 80, 90, limits);
assert.ok(groupPath);
for (let i = 1; i < groupPath.length; i++)
    for (let j = 0; j < 2; j++)
        assert.equal(movementBlocked(groupPath[i - 1][j], groupPath[i][j], [wall], 10), false);
for (const step of groupPath)
    assert.equal(step[1].gridY - step[0].gridY, 1);
const clamped = structuredClone(group);
clamped.at(-1)[1].gridX--;
assert.equal(suggestTokenRoute(clamped, [], 10, 80, 90, limits), undefined);
assert.equal(suggestTokenRoute([], [], 10, 80, 90, limits), undefined);
assert.equal(suggestTokenRoute(chosen, [], 0, 80, 90, limits), undefined);

// The direct chosen line can be invalid: show a longer, safe detour rather than no CTA.
const detour = suggestTokenRoute([first, last], [wall], 10, 80, 80, limits);
assert.ok(detour && routeMeasurements(detour, 1).total > 4);
for (let i = 1; i < detour.length; i++)
    assert.equal(movementBlocked(detour[i - 1][0], detour[i][0], [wall], 10), false);
assert.ok(suggestTokenRoute([first, last], [{ ...wall, kind: 'door', door_state: 'locked' }], 10, 80, 80, limits));

// Independent exhaustive Dijkstra oracle on the same eight-neighbor grid.
const costs = new Map([['0,0', 0]]), visited = new Set();
for (;;) {
    const next = [...costs].filter(([key]) => !visited.has(key)).sort((a, b) => a[1] - b[1])[0];
    assert.ok(next, 'Destination must be reachable');
    const [id, cost] = next;
    if (id === '4,0') {
        assert.ok(Math.abs(cost - routeMeasurements(detour, 1).total) < 1e-8, 'A* must find the shortest traversable grid path');
        break;
    }
    visited.add(id);
    const [x, y] = id.split(',').map(Number);
    for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) {
        const nx = x + dx, ny = y + dy;
        if ((!dx && !dy) || nx < 0 || ny < 0 || nx > 7 || ny > 7 || movementBlocked({ ...token, gridX: x, gridY: y }, { gridX: nx, gridY: ny }, [wall], 10)) continue;
        const key = `${nx},${ny}`, candidate = cost + Math.hypot(dx, dy);
        if (candidate < (costs.get(key) ?? Infinity)) costs.set(key, candidate);
    }
}
