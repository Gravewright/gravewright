import assert from 'node:assert/strict';
import test from 'node:test';
import { LightPolygons, lightRadius, lightWalls } from './light-polygons.js';
import { VisibilityJobs } from './visibility-jobs.js';
import { createVisibilityContext, visibilityPolygon } from './visibility-polygon.js';

const cell = 50, width = 2000, height = 1200;
const light = (id, x, y, extra = {}) => ({ id, x, y, enabled: true, bright_radius: 2, dim_radius: 4, angle: 360,
    rotation: 0, ...extra });
const door = (state, x = 220) => ({ id: 'door', x1: x, y1: 100, x2: x, y2: 300, door_state: state, kind: 'door' });
const ring = Array.from({ length: 24 }, (_, i) => ({ id: `w${i}`, x1: 1000 + i * 20, y1: 900, x2: 1010 + i * 20, y2: 960 }));
const flat = (source, walls) => visibilityPolygon(source, lightRadius(source, cell, width, height), walls,
    createVisibilityContext(walls)).flatMap(p => [p.x, p.y]);

class FakeWorker {
    messages = [];
    postMessage(message) { this.messages.push(message); }
    terminate() { this.terminated = true; }
    answer(polygons) { const id = this.messages.at(-1).id; this.onmessage({ data: { id, polygons } }); }
}

test('light polygons match the visibility polygon of each light and are reused while nothing changes', () => {
    const walls = lightWalls([door('closed'), ...ring]);
    const lights = [light('near', 150, 200), light('far', 1500, 300), light('off', 10, 10, { enabled: false }),
        light('cone', 600, 600, { angle: 90, rotation: 45, elevation: 2 })];
    const polygons = new LightPolygons();
    const rows = polygons.update(lights, walls, cell, width, height);
    assert.deepEqual(rows.map(row => row.light.id), ['near', 'far', 'cone']);
    for (const row of rows) assert.deepEqual([...row.polygon], flat(row.light, walls));
    assert.equal(polygons.calculated, 3);
    const again = polygons.update(lights.map(row => ({ ...row })), walls, cell, width, height);
    assert.equal(polygons.calculated, 3, 'an identical snapshot calculates nothing');
    assert.ok(again.every((row, index) => row.polygon === rows[index].polygon));
    polygons.dispose();
});

test('a door recalculates only the lights whose reach includes it', () => {
    const closed = lightWalls([door('closed'), ...ring]), open = lightWalls([door('open'), ...ring]);
    const lights = [light('near', 150, 200), light('far', 1500, 300)];
    const polygons = new LightPolygons();
    const before = polygons.update(lights, closed, cell, width, height);
    const after = polygons.update(lights, open, cell, width, height);
    assert.equal(polygons.calculated, 3, 'one light was recalculated for the door');
    assert.notDeepEqual([...after[0].polygon], [...before[0].polygon], 'the opened door lets the near light through');
    assert.deepEqual([...after[0].polygon], flat(lights[0], open));
    assert.equal(after[1].polygon, before[1].polygon, 'the distant light keeps its polygon');
    // Removing and re-adding a wall are changes too, wherever the wall sits in the list.
    polygons.update(lights, open.slice(1), cell, width, height);
    assert.equal(polygons.calculated, 4);
    polygons.update(lights, [...open.slice(1), open[0]], cell, width, height);
    assert.equal(polygons.calculated, 5);
    polygons.dispose();
});

test('worker misses keep the previous polygon, translated, until the newest answer arrives', () => {
    const walls = lightWalls(Array.from({ length: 130 }, (_, i) => ({ id: `w${i}`, x1: 400 + i, y1: 0, x2: 400 + i, y2: 50 })));
    const worker = new FakeWorker(), updates = [];
    const polygons = new LightPolygons({ onUpdate: rows => updates.push(rows),
        createJobs: value => new VisibilityJobs(value, () => worker) });
    const torch = light('torch', 100, 100);
    assert.deepEqual(polygons.update([torch], walls, cell, width, height), [], 'a new light waits for its polygon');
    assert.equal(polygons.pending, true);
    assert.equal(worker.messages[0].type, 'walls');
    worker.answer([new Float64Array([0, 0, 10, 0, 10, 10])]);
    assert.equal(polygons.pending, false);
    assert.deepEqual([...updates.at(-1)[0].polygon], [0, 0, 10, 0, 10, 10]);
    const moved = polygons.update([{ ...torch, x: 130, y: 90 }], walls, cell, width, height);
    assert.deepEqual([...moved[0].polygon], [30, -10, 40, -10, 40, 0], 'the old shape follows the light meanwhile');
    assert.equal(worker.messages.at(-1).sources[0].x, 130);
    worker.answer([new Float64Array([1, 2, 3, 4, 5, 6])]);
    assert.deepEqual([...updates.at(-1)[0].polygon], [1, 2, 3, 4, 5, 6]);
    polygons.dispose();
    assert.ok(worker.terminated);
});

test('a wall change revokes an answer computed for the previous walls', () => {
    const walls = lightWalls(Array.from({ length: 130 }, (_, i) => ({ id: `w${i}`, x1: 400 + i, y1: 0, x2: 400 + i, y2: 50 })));
    const worker = new FakeWorker(), updates = [];
    const polygons = new LightPolygons({ onUpdate: rows => updates.push(rows),
        createJobs: value => new VisibilityJobs(value, () => worker) });
    const torch = light('torch', 450, 25);
    polygons.update([torch], walls, cell, width, height);
    const stale = worker.messages.at(-1).id;
    polygons.update([torch], walls.slice(1), cell, width, height);
    assert.equal(worker.messages.at(-1).type, 'walls', 'the worker is reused with the new walls');
    worker.onmessage({ data: { id: stale, polygons: [new Float64Array([9, 9, 9, 9, 9, 9])] } });
    assert.equal(updates.length, 0, 'the old answer is discarded');
    assert.equal(worker.messages.at(-1).type, 'vision', 'the current miss is requested after it');
    worker.answer([new Float64Array([1, 1, 2, 2, 3, 3])]);
    assert.deepEqual([...updates.at(-1)[0].polygon], [1, 1, 2, 2, 3, 3]);
    polygons.dispose();
});
