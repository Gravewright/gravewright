import assert from 'node:assert/strict';
import test from 'node:test';
import { SceneLayers } from '../lib/scene-layers.js';

const source = { sourceId: 'hero', x: 10, y: 20, radius: 50, elevation: 0 };
const state = { lighting: { mode: 'dynamic', darkness: 1 }, vision: [source], previewTokenVision: false,
    walls: Array.from({ length: 128 }, (_, i) => ({ x1: i + 100, x2: i + 100, y1: 0, y2: 50 })) };

function fixture() {
    const frames = new Map();
    let frame = 0;
    globalThis.requestAnimationFrame = callback => { frames.set(++frame, callback); return frame; };
    globalThis.cancelAnimationFrame = id => frames.delete(id);
    const layers = new SceneLayers({ invalidate() {} });
    const painted = [];
    layers.paintDarkness = (...args) => painted.push(args[5]);
    return { layers, frames, painted, flush() { const work = [...frames.values()]; frames.clear(); work.forEach(fn => fn()); } };
}
class FakeWorker {
    static current;
    messages = [];
    constructor() { FakeWorker.current = this; }
    postMessage(message) { this.messages.push(message); }
    terminate() { this.terminated = true; }
    answer(id) { this.onmessage({ data: { id, polygons: [new Float64Array([1, 2, 3, 4])] } }); }
}
test('continuous motion coalesces to the latest snapshot once per animation frame', () => {
    const f = fixture(), received = [];
    f.layers.darkness = (...args) => received.push(args[0].vision[0].x);
    for (let x = 0; x < 50; x++) f.layers.queueVision({ ...state, vision: [{ ...source, x }] }, 10, 1000, 1000, false);
    assert.equal(f.frames.size, 1);
    assert.equal(f.painted.length, 1, 'only the initial observer change closes the veil');
    f.flush();
    assert.deepEqual(received, [49]);
    f.layers.dispose();
});
test('observer revocation rejects a worker result before the queued RAF executes', () => {
    const original = globalThis.Worker;
    globalThis.Worker = FakeWorker;
    const f = fixture();
    try {
        f.layers.darkness(state, 10, 1000, 1000, false);
        const worker = FakeWorker.current;
        f.layers.queueVision({ ...state, vision: [{ ...source, sourceId: 'other' }] }, 10, 1000, 1000, false);
        const before = f.painted.length;
        assert.deepEqual(f.painted.at(-1), [], 'old observer is hidden synchronously');
        worker.answer(1);
        assert.equal(f.painted.length, before, 'late observer result cannot repaint before RAF');
        f.flush();
        worker.answer(2);
        assert.equal(f.painted.at(-1)[0][0], 1);
        f.layers.dispose();
        assert.ok(worker.terminated);
        worker.answer(2);
        assert.equal(f.frames.size, 0);
    } finally { f.layers.dispose(); globalThis.Worker = original; }
});
test('moving the same observer reuses its veil until the next worker result', () => {
    const original = globalThis.Worker;
    globalThis.Worker = FakeWorker;
    const f = fixture();
    try {
        f.layers.darkness(state, 10, 1000, 1000, false);
        const worker = FakeWorker.current;
        assert.deepEqual(f.painted.at(-1), [], 'initial pending vision starts closed');
        worker.answer(1);
        const before = f.painted.length;
        for (let x = 0; x < 50; x++) f.layers.queueVision({ ...state, vision: [{ ...source, x }] }, 10, 1000, 1000, false);
        f.flush();
        assert.equal(f.painted.length, before, 'pending movement does not repaint the previous veil');
        worker.answer(2);
        assert.equal(f.painted.length, before + 1, 'completed movement paints one new veil');
    } finally { f.layers.dispose(); globalThis.Worker = original; }
});
test('the GM reuses the static veil and cancels an unflushed token preview', () => {
    const f = fixture();
    try {
        f.layers.darkness(state, 10, 1000, 1000, true);
        const before = f.painted.length;
        for (let x = 0; x < 50; x++) f.layers.queueVision({ ...state, vision: [{ ...source, x }] }, 10, 1000, 1000, true);
        assert.equal(f.painted.length, before);
        assert.equal(f.frames.size, 0);
        f.layers.queueVision({ ...state, previewTokenVision: true }, 10, 1000, 1000, true);
        assert.equal(f.frames.size, 1);
        f.layers.queueVision(state, 10, 1000, 1000, true);
        assert.equal(f.frames.size, 0, 'stale preview cannot run after returning to GM view');
        const returned = f.painted.length;
        f.flush();
        assert.equal(f.painted.length, returned);
    } finally { f.layers.dispose(); }
});
test('range, elevation, preview and empty-selection changes close old vision immediately', () => {
    for (const next of [{ ...state, vision: [{ ...source, radius: 20 }] },
        { ...state, vision: [{ ...source, elevation: 8 }] }, { ...state, vision: [] }]) {
        const f = fixture();
        f.layers.queueVision(state, 10, 1000, 1000, false);
        const before = f.painted.length;
        f.layers.queueVision(next, 10, 1000, 1000, false);
        assert.equal(f.painted.length, before + 1);
        assert.deepEqual(f.painted.at(-1), []);
        f.layers.dispose();
        assert.equal(f.frames.size, 0);
    }
    const f = fixture();
    f.layers.queueVision(state, 10, 1000, 1000, true);
    f.layers.queueVision({ ...state, previewTokenVision: true }, 10, 1000, 1000, true);
    assert.equal(f.painted.length, 2);
    f.layers.dispose();
});
