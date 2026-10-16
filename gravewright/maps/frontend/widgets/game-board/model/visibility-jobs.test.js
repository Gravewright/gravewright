import assert from 'node:assert/strict';
import test from 'node:test';
import { VisibilityJobs, visionPolygons } from './visibility-jobs.js';
import { createVisibilityContext, visibilityPolygon } from './visibility-polygon.js';

const walls = Array.from({ length: 128 }, (_, i) => ({ x1: 50 + i, x2: 50 + i, y1: -100, y2: 100 }));
const sources = [{ sourceId: 'hero', x: 0, y: 0, radius: 80, elevation: 0 }];
class FakeWorker {
    messages = [];
    terminated = false;
    postMessage(message) { this.messages.push(message); }
    terminate() { this.terminated = true; }
    answer(id, polygons = [new Float64Array([1, 2, 3, 4])]) { this.onmessage({ data: { id, polygons } }); }
}
test('worker payload preserves every polygon coordinate, range, cone and elevation', () => {
    const context = createVisibilityContext(walls);
    for (const source of [sources[0], { ...sources[0], radius: 0 }, { ...sources[0], angle: 80, rotation: 10, elevation: 3 }]) {
        const expected = visibilityPolygon(source, source.radius > 0 ? source.radius : 500, walls, context).flatMap(p => [p.x, p.y]);
        assert.deepEqual([...visionPolygons([source], 500, walls, context)[0]], expected);
    }
});
test('only one active and the newest pending drag snapshot are posted', () => {
    const worker = new FakeWorker(), completed = [];
    const jobs = new VisibilityJobs(walls, () => worker);
    for (let x = 0; x < 50; x++) jobs.request([{ ...sources[0], x }], 500, () => completed.push(x));
    assert.equal(worker.messages.length, 2);
    assert.equal(worker.messages[0].type, 'walls');
    worker.answer(1);
    assert.deepEqual(completed, [0]);
    assert.equal(worker.messages.length, 3);
    assert.equal(worker.messages[2].sources[0].x, 49);
    worker.answer(50);
    assert.deepEqual(completed, [0, 49]);
    jobs.dispose();
    assert.ok(worker.terminated);
});
test('selection cancellation and disposal reject late worker responses', () => {
    const worker = new FakeWorker(), completed = [];
    const jobs = new VisibilityJobs(walls, () => worker);
    jobs.request(sources, 500, () => completed.push('old'));
    jobs.cancel();
    jobs.request([{ ...sources[0], sourceId: 'other' }], 500, () => completed.push('new'));
    worker.answer(1);
    assert.deepEqual(completed, []);
    jobs.dispose();
    worker.answer(2);
    assert.deepEqual(completed, []);
});
test('empty vision cancels old observers immediately', () => {
    const worker = new FakeWorker(), completed = [];
    const jobs = new VisibilityJobs(walls, () => worker);
    jobs.request(sources, 500, () => completed.push('old'));
    jobs.request([], 500, value => completed.push(value));
    worker.answer(1);
    assert.deepEqual(completed, [[]]);
    jobs.dispose();
});
test('blocked workers fall back to the newest snapshot with the same geometry', () => {
    const worker = new FakeWorker(), completed = [];
    const jobs = new VisibilityJobs(walls, () => worker);
    jobs.request(sources, 500, () => completed.push('old'));
    const next = [{ ...sources[0], x: 15 }];
    jobs.request(next, 500, value => completed.push(value));
    worker.onerror({ preventDefault() {} });
    assert.equal(completed.length, 1);
    assert.deepEqual(completed[0], visionPolygons(next, 500, walls));
    assert.ok(worker.terminated);
    jobs.dispose();
});
test('small scenes do not start a worker and keep synchronous visibility', () => {
    const jobs = new VisibilityJobs(walls.slice(0, 1), () => { throw Error('Unexpected worker'); });
    let called = false;
    jobs.request(sources, 500, value => { called = true; assert.deepEqual(value, visionPolygons(sources, 500, walls.slice(0, 1))); });
    assert.ok(called);
    jobs.dispose();
});
