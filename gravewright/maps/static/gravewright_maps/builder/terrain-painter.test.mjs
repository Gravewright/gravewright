import test from 'node:test';
import assert from 'node:assert/strict';
import { newDocument, clone, history, floorContainsPoint } from './model.js';
import { terrainBrushAlpha, terrainBrushLimits } from './terrain-brush.js';
import { createTerrainPainter } from './terrain-painter.js';

function fixture(extra = {}) {
    const document = newDocument(), options = { layerId: document.layers[0].id, size: 2, hardness: 0,
        intensity: .25, operation: 'paint', assetIds: ['red', 'blue'], snap: true, ...extra };
    const events = { previews: [], commits: [], errors: [], cancels: 0 }, timers = new Map();
    let nextTimer = 0;
    const painter = createTerrainPainter({ getDocument: () => document, getOptions: () => options,
        onPreview: (candidate, meta) => { events.previews = [{ candidate, meta }]; }, onCommit: (candidate, refs) => events.commits.push({ candidate, refs }),
        onError: error => events.errors.push(error), onCancel: () => events.cancels++,
        schedule: callback => { const id = nextTimer++; timers.set(id, callback); return id; }, unschedule: id => timers.delete(id) });
    return { document, options, events, painter, timers, tick() { for (const callback of [...timers.values()]) callback(); } };
}

test('terrain gestures clamp their centers and coverage to exact imported raster edges', () => {
    const { painter, document, events, timers } = fixture({ size: .5, intensity: 1, assetIds: ['stone'] });
    Object.assign(document, { columns: 4, rows: 3, cellSize: 50,
        sceneGeometry: { width: 197, height: 145, gridSize: 50.5, gridOffsetX: 0, gridOffsetY: 0 } });
    painter.start({ x: 3.8, y: 2.8 }); painter.move({ x: 7, y: 6 });
    assert.deepEqual(events.previews.at(-1).meta.cursor, { x: 3.94, y: 2.9 });
    assert.equal(painter.end({ x: 7, y: 6 }), true);
    const floor = events.commits[0].candidate.floors[0];
    assert.ok(floor.x + floor.width <= 3.94 + 1e-8);
    assert.ok(floor.y + floor.height <= 2.9 + 1e-8);
    assert.equal(timers.size, 0); assert.deepEqual(events.errors, []);
});

test('a free round gesture freezes material, strength, size and ID while filling pointer-event gaps', () => {
    const oldRandom = Math.random; let samples = 0; Math.random = () => { samples++; return .99; };
    try {
        const { document, options, events, painter, timers } = fixture(), before = clone(document);
        assert.equal(painter.start({ x: 2.125, y: 3.375 }), true);
        const initial = events.previews.at(-1).candidate.floors.at(-1);
        options.intensity = 1; options.size = 20; options.assetIds = ['changed']; options.snap = false;
        painter.move({ x: 8.175, y: 3.375 });
        const candidate = events.previews.at(-1).candidate, item = candidate.floors.at(-1);
        assert.equal(item.id, initial.id); assert.equal(item.assetId, 'blue'); assert.equal(samples, 1);
        assert.equal(item.brush.radius[0] * item.width, 1); assert.ok(item.brush.points.every(point => point[2] === .25));
        for (let x = 2.125; x < 8.175; x += .05) assert.equal(floorContainsPoint(item, { x, y: 3.375 }), true);
        assert.equal(painter.end({ x: 8.175, y: 3.375 }), true);
        assert.equal(events.commits.length, 1); assert.equal(events.commits[0].candidate.floors.length, 1);
        assert.deepEqual(events.commits[0].refs, [{ kind: 'floors', id: initial.id }]);
        assert.deepEqual(document, before); assert.equal(timers.size, 0); assert.equal(painter.active, false);
    } finally { Math.random = oldRandom; }
});

test('spatial resampling is independent of pointer frequency and Snap state', () => {
    const rows = [];
    for (const [steps, snap] of [[1, true], [40, false]]) {
        const { painter, events } = fixture({ assetIds: ['same'], intensity: .1, snap });
        painter.start({ x: 2, y: 3 });
        for (let step = 1; step <= steps; step++) painter.move({ x: 2 + 6 * step / steps, y: 3 });
        painter.end({ x: 8, y: 3 }); rows.push(events.commits[0].candidate.floors[0]);
    }
    assert.equal(rows[0].brush.points.length, rows[1].brush.points.length);
    for (const point of [{ x: 2, y: 3 }, { x: 4.37, y: 3.29 }, { x: 7.5, y: 3.9 }])
        assert.equal(terrainBrushAlpha(rows[0], point), terrainBrushAlpha(rows[1], point));
});

test('holding repeats real radial dabs every scheduled tick but commits only one undo step', () => {
    const { document, painter, events, tick, timers } = fixture({ assetIds: ['stone'] }), steps = history(document), before = clone(document);
    painter.start({ x: 4, y: 4 }); const initial = events.previews.at(-1).candidate.floors[0];
    tick(); tick(); tick();
    const held = events.previews.at(-1).candidate.floors[0];
    assert.equal(held.brush.points.length, 4); assert.equal(held.id, initial.id);
    assert.ok(terrainBrushAlpha(held, { x: 4, y: 4 }) > terrainBrushAlpha(initial, { x: 4, y: 4 }));
    assert.ok(terrainBrushAlpha(held, { x: 4.75, y: 4 }) > terrainBrushAlpha(initial, { x: 4.75, y: 4 }));
    painter.end({ x: 4, y: 4 }); assert.equal(timers.size, 0);
    assert.equal(steps.commit(events.commits[0].candidate), true); assert.deepEqual(steps.undo(), before);
    assert.equal(steps.canUndo, false); assert.deepEqual(steps.redo(), events.commits[0].candidate);
});

test('cancel, disposal and zero intensity leave source unchanged and release every timer', () => {
    for (const action of ['cancel', 'dispose']) {
        const { painter, document, events, tick, timers } = fixture(), before = clone(document);
        painter.start({ x: 4, y: 4 }); tick(); painter[action](); tick();
        assert.equal(timers.size, 0); assert.equal(events.commits.length, 0); assert.equal(events.cancels, 1); assert.deepEqual(document, before);
        if (action === 'dispose') assert.equal(painter.start({ x: 4, y: 4 }), false);
    }
    const { painter, events, timers } = fixture({ intensity: 0 });
    painter.start({ x: 4, y: 4 }); assert.equal(timers.size, 0); assert.equal(painter.end({ x: 4, y: 4 }), false);
    assert.equal(events.commits.length, 0); assert.equal(events.cancels, 1);
});

test('overlong strokes and holds reject atomically, stop scheduling and do not leak cached preview rows', () => {
    const { painter, document, events, timers } = fixture({ size: .05 }), before = clone(document);
    painter.start({ x: 0, y: 0 }); painter.move({ x: 40, y: 0 });
    assert.equal(events.previews.at(-1).meta.invalid, true); assert.equal(timers.size, 0);
    assert.equal(painter.end({ x: 40, y: 0 }), false); assert.deepEqual(document, before);
    assert.deepEqual(events.errors, ['The map has too many terrain brush dabs.']); assert.equal(events.commits.length, 0);
    const held = fixture(); held.painter.start({ x: 2, y: 2 });
    for (let index = 0; index < terrainBrushLimits.dabs; index++) held.tick();
    assert.equal(held.timers.size, 0); assert.equal(held.painter.end({ x: 2, y: 2 }), false);
    assert.equal(held.events.commits.length, 0); assert.equal(held.events.errors[0], 'The map has too many terrain brush dabs.');
});

test('protected layers refuse the gesture before scheduling work', () => {
    for (const change of [{ visible: false }, { locked: true }]) {
        const { document, painter, events, timers } = fixture(); Object.assign(document.layers[0], change);
        const before = clone(document);
        assert.equal(painter.start({ x: 2, y: 2 }), false); assert.equal(timers.size, 0);
        assert.deepEqual(document, before); assert.deepEqual(events.errors, ['Choose a visible, unlocked layer before painting.']);
    }
});
