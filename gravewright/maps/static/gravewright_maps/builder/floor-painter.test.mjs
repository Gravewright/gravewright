import test from 'node:test';
import assert from 'node:assert/strict';
import { clone, newDocument, defaultLayers, floorContainsPoint, applyFloorContours } from './model.js';
import { createFloorPainter } from './floor-painter.js';

function fixture(mode = 'brush', overrides = {}) {
    const document = { ...newDocument(), layers: defaultLayers() }, events = { previews: [], commits: [], errors: [], cancels: 0 };
    const options = { mode, size: 1, layerId: document.layers[0].id, assetIds: ['stone'], rotation: 0, maxObjects: 2000, ...overrides };
    const painter = createFloorPainter({ getDocument: () => document, getOptions: () => options,
        onPreview: (candidate, meta) => events.previews.push({ candidate, meta }),
        onCommit: (candidate, refs) => events.commits.push({ candidate, refs }),
        onCancel: () => events.cancels++, onError: message => events.errors.push(message) });
    return { painter, document, options, events };
}

test('free floor gestures clamp previews and committed geometry to imported raster edges', () => {
    const { painter, document, events } = fixture('rectangle', { snap: false });
    Object.assign(document, { columns: 4, rows: 3, cellSize: 50,
        sceneGeometry: { width: 197, height: 145, gridSize: 50.5, gridOffsetX: 0, gridOffsetY: 0 } });
    painter.start({ x: 3, y: 2 }); painter.move({ x: 7, y: 6 });
    assert.deepEqual(events.previews.at(-1).meta.cursor, { x: 3.94, y: 2.9 });
    assert.equal(painter.end({ x: 7, y: 6 }), true);
    const floor = events.commits[0].candidate.floors[0];
    assert.ok(Math.abs(floor.x + floor.width - 3.94) < 1e-8);
    assert.ok(Math.abs(floor.y + floor.height - 2.9) < 1e-8);
    assert.deepEqual(events.errors, []);
});

test('repainting the same family over large adjoining floors is a no-op gesture with and without snapping', () => {
    const previousRandom = Math.random;
    Math.random = () => { throw new Error('A same-family gesture must not reroll variants.'); };
    try {
        for (const snap of [true, false]) {
            const { painter, document, options, events } = fixture('brush', { snap, assetIds: ['a', 'b'] });
            document.floors = [
                { id: 'left', layerId: options.layerId, assetId: 'a', x: 0, y: 0, width: 2, height: 2, rotation: 0 },
                { id: 'right', layerId: options.layerId, assetId: 'b', x: 2, y: 0, width: 2, height: 2, rotation: 0 },
            ];
            const before = clone(document);
            painter.start({ x: .2, y: .2 }); painter.move({ x: 2.2, y: .2 });
            assert.equal(events.previews.at(-1).meta.changed, false); assert.equal(events.previews.at(-1).meta.invalid, false);
            assert.deepEqual(events.previews.at(-1).candidate, before);
            assert.equal(painter.end({ x: 2.2, y: .2 }), false);
            assert.equal(events.commits.length, 0); assert.equal(events.cancels, 1); assert.deepEqual(document, before);
            assert.deepEqual(events.errors, []);
        }
    } finally { Math.random = previousRandom; }
});

test('a mixed grid gesture publishes only changed-cell refs and retains its family choices across previews', () => {
    const previousRandom = Math.random; let samples = 0;
    Math.random = () => { samples++; return .99; };
    try {
        const { painter, document, options, events } = fixture('brush', { assetIds: ['a', 'b'] });
        document.floors = ['a', 'wood', 'b'].map((assetId, x) =>
            ({ id: `old-${x}`, layerId: options.layerId, assetId, x, y: 0, width: 1, height: 1, rotation: 0 }));
        const before = clone(document);
        painter.start({ x: .2, y: .2 }); painter.move({ x: 2.2, y: .2 });
        const candidate = clone(events.previews.at(-1).candidate), replacement = candidate.floors.at(-1);
        assert.deepEqual(candidate.floors.slice(0, 2), [before.floors[0], before.floors[2]]);
        assert.equal(replacement.assetId, 'b'); assert.equal(replacement.x, 1); assert.equal(samples, 1);
        painter.move({ x: .2, y: .2 }); painter.move({ x: 2.2, y: .2 });
        assert.deepEqual(events.previews.at(-1).candidate, candidate);
        assert.equal(painter.end({ x: 2.2, y: .2 }), true); assert.equal(samples, 1);
        assert.deepEqual(events.commits[0].refs, [{ kind: 'floors', id: replacement.id }]);
        assert.equal(events.commits.length, 1); assert.deepEqual(document, before);
    } finally { Math.random = previousRandom; }
});

test('a free gesture first samples its family when leaving the same material and reuses that choice if its preview recovers', () => {
    const previousRandom = Math.random; let samples = 0;
    Math.random = () => { samples++; return .99; };
    try {
        const { painter, document, options, events } = fixture('rectangle', { snap: false, assetIds: ['a', 'b'] });
        document.floors = [{ id: 'room', layerId: options.layerId, assetId: 'a', x: 0, y: 0, width: 2, height: 2, rotation: 0 }];
        const before = clone(document);
        painter.start({ x: .25, y: .25 }); painter.move({ x: 1.5, y: 1.5 });
        assert.equal(events.previews.at(-1).meta.changed, false); assert.equal(samples, 0);
        painter.move({ x: 3, y: 1.5 });
        const expanded = clone(events.previews.at(-1).candidate), id = expanded.floors.at(-1).id;
        assert.equal(samples, 1); assert.equal(expanded.floors.at(-1).assetId, 'b');
        painter.move({ x: 1.5, y: 1.5 }); assert.equal(events.previews.at(-1).meta.changed, false);
        painter.move({ x: 3, y: 1.5 }); assert.deepEqual(events.previews.at(-1).candidate, expanded);
        assert.equal(painter.end({ x: 3, y: 1.5 }), true); assert.equal(samples, 1);
        assert.deepEqual(events.commits[0].refs, [{ kind: 'floors', id }]); assert.deepEqual(document, before);
    } finally { Math.random = previousRandom; }
});

test('snap off paints one truly continuous round stroke with a stable ID and family material', () => {
    const { painter, document, options, events } = fixture('brush', { snap: false, size: .35, shape: 'circle', anchor: 'center', assetIds: ['a', 'b'] });
    const before = clone(document);
    painter.start({ x: 1.125, y: 2.375 });
    const initial = clone(events.previews.at(-1).candidate.floors[0]);
    options.snap = true; options.size = 8;
    painter.move({ x: 7.875, y: 3.125 });
    const preview = events.previews.at(-1);
    assert.equal(preview.candidate.floors.length, 1); assert.equal(preview.meta.snap, false);
    assert.equal(preview.candidate.floors[0].id, initial.id); assert.equal(preview.candidate.floors[0].assetId, initial.assetId);
    assert.equal(floorContainsPoint(preview.candidate.floors[0], { x: 4.5, y: 2.75 }), true);
    assert.equal(floorContainsPoint(preview.candidate.floors[0], { x: 4.5, y: 3.5 }), false);
    assert.deepEqual(document, before);
    assert.equal(painter.end({ x: 7.875, y: 3.125 }), true);
    assert.equal(events.commits.length, 1); assert.deepEqual(events.commits[0].refs, [{ kind: 'floors', id: initial.id }]);
});

test('Painting forces continuous geometry and freezes style, backing, and IDs for one atomic gesture', () => {
    const { painter, document, options, events } = fixture('brush', { editingMode: 'paint', snap: true,
        size: .5, shape: 'circle', anchor: 'center', paint: { color: '#ff0000', opacity: .5 } });
    document.floors.push({ id: 'backing', layerId: options.layerId, assetId: 'stone', x: 0, y: 0, width: 8, height: 8, rotation: 0 });
    const before = clone(document);
    painter.start({ x: 1.125, y: 2.375 });
    const id = events.previews.at(-1).candidate.floors.at(-1).id;
    options.paint.color = '#0000ff'; options.paint.opacity = 1; options.editingMode = 'tiles';
    painter.move({ x: 5.875, y: 2.375 }); painter.move({ x: 1.125, y: 2.375 });
    assert.equal(events.previews.at(-1).meta.snap, false); assert.equal(events.previews.at(-1).meta.editingMode, 'paint');
    assert.equal(painter.end({ x: 5.875, y: 2.375 }), true);
    const candidate = events.commits[0].candidate;
    assert.equal(candidate.floors.length, 2); assert.deepEqual(candidate.floors[0], before.floors[0]);
    assert.deepEqual(candidate.floors.at(-1).paint, { color: '#ff0000', opacity: .5 });
    assert.equal(candidate.floors.at(-1).id, id); assert.equal(candidate.floors.at(-1).assetId, null);
    assert.deepEqual(document, before);
});

test('Painting zero-opacity strokes and cancelled gestures never commit, and invalid styles fail without source changes', () => {
    const { painter, document, options, events } = fixture('brush', { editingMode: 'paint', paint: { color: '#ff0000', opacity: 0 } });
    const before = clone(document);
    painter.start({ x: 2, y: 2 }); assert.equal(painter.end({ x: 5, y: 2 }), false);
    assert.equal(events.commits.length, 0); assert.equal(events.cancels, 1);
    options.paint.opacity = .5;
    painter.start({ x: 2, y: 2 }); assert.equal(painter.cancel(), true);
    options.paint.opacity = true;
    painter.start({ x: 2, y: 2 }); assert.equal(painter.end({ x: 5, y: 2 }), false);
    assert.deepEqual(events.errors, ['Invalid floor paint.']); assert.equal(events.commits.length, 0);
    assert.deepEqual(document, before);
});

test('Tiles snap-off gestures keep replacement behavior and ignore inactive Painting style controls', () => {
    const { painter, document, options, events } = fixture('rectangle', { editingMode: 'tiles', snap: false,
        paint: { color: '#ff0000', opacity: .5 } });
    document.floors.push({ id: 'backing', layerId: options.layerId, assetId: 'old', x: 0, y: 0, width: 8, height: 8, rotation: 0 });
    painter.start({ x: 2.125, y: 2.375 }); painter.end({ x: 4.125, y: 4.375 });
    const candidate = events.commits[0].candidate;
    assert.equal(candidate.floors.at(-1).paint, undefined);
    assert.equal(candidate.floors.at(-1).assetId, 'stone');
    assert.equal(floorContainsPoint(candidate.floors[0], { x: 3, y: 3 }), false);
});

test('Painting area erasure cuts every overlay on the active layer and preserves another layer', () => {
    const { painter, document, options, events } = fixture('rectangle', { editingMode: 'paint', operation: 'erase' });
    document.layers.push({ id: 'base-layer', name: 'Base art', visible: true, locked: false });
    const row = { x: 0, y: 0, width: 8, height: 8, rotation: 0, assetId: null };
    document.floors.push({ ...row, id: 'base', layerId: 'base-layer' },
        { ...row, id: 'first', layerId: options.layerId, paint: { color: '#ff0000', opacity: .5 } },
        { ...row, id: 'second', layerId: options.layerId, paint: { color: '#0000ff', opacity: .25 } });
    const before = clone(document);
    painter.start({ x: 2.125, y: 2.375 }); painter.end({ x: 4.125, y: 4.375 });
    const candidate = events.commits[0].candidate;
    assert.deepEqual(candidate.floors[0], before.floors[0]);
    assert.deepEqual(events.commits[0].refs, []);
    assert.ok(candidate.floors.slice(1).every(item => !floorContainsPoint(item, { x: 3, y: 3 })));
    assert.deepEqual(candidate.floors.slice(1).map(item => item.paint), before.floors.slice(1).map(item => item.paint));
    assert.deepEqual(document, before);
});

test('snap off rectangle, circle and polygon keep float boundaries instead of enumerating cells', () => {
    for (const mode of ['rectangle', 'circle']) {
        const { painter, events } = fixture(mode, { snap: false });
        painter.start({ x: 2.125, y: 2.375 }); painter.end({ x: 3.375, y: 3.625 });
        const floors = events.commits[0].candidate.floors;
        assert.equal(floors.length, 1); assert.ok(floors[0].shape.contours.length);
        if (mode === 'rectangle') { assert.equal(floors[0].x, 2.125); assert.equal(floors[0].width, 1.25); }
        else assert.equal(floorContainsPoint(floors[0], { x: floors[0].x + .01, y: floors[0].y + .01 }), false);
    }
    const { painter, events } = fixture('polygon', { snap: false });
    for (const point of [{ x: 1.125, y: 1.375 }, { x: 4.125, y: 1.375 }, { x: 1.125, y: 3.375 }]) painter.start(point);
    painter.move({ x: 7, y: 7 });
    assert.equal(painter.finish(), true);
    const item = events.commits[0].candidate.floors[0];
    assert.equal(item.shape.contours[0].length, 3); assert.equal(item.x, 1.125); assert.equal(item.height, 2);
});

test('snap off area erasure commits masks once and repeated/empty erasure adds no history', () => {
    const { painter, document, options, events } = fixture('circle', { snap: false, operation: 'erase' });
    document.floors.push({ id: 'room', layerId: options.layerId, assetId: 'wood', x: .125, y: .375, width: 6, height: 6, rotation: 90 });
    const before = clone(document);
    painter.start({ x: 3.125, y: 3.375 }); painter.end({ x: 3.875, y: 3.375 });
    assert.equal(events.commits.length, 1); assert.deepEqual(events.commits[0].refs, []); assert.deepEqual(document, before);
    Object.assign(document, clone(events.commits[0].candidate));
    painter.start({ x: 3.125, y: 3.375 }); assert.equal(painter.end({ x: 3.875, y: 3.375 }), false);
    assert.equal(events.commits.length, 1); assert.equal(events.cancels, 1);
    assert.equal(floorContainsPoint(document.floors[0], { x: 3.125, y: 3.375 }), false);
    assert.equal(floorContainsPoint(document.floors[0], { x: 4, y: 4.5 }), true);
});

test('snap off fill preserves shape identity and holes, and empty fill reports its useful error', () => {
    const { painter, document, options, events } = fixture('fill', { snap: false, assetIds: ['wood'], rotation: 270 });
    applyFloorContours(document, [[[1.125, 1.375], [5.125, 1.375], [1.125, 4.375]]], { layerId: options.layerId, assetIds: ['stone'] });
    const before = clone(document.floors[0]);
    painter.start({ x: 1.5, y: 1.75 }); painter.end({ x: 8, y: 8 });
    assert.deepEqual(events.commits[0].candidate.floors[0], { ...before, assetId: 'wood', rotation: 270 });
    painter.start({ x: 8, y: 8 }); assert.equal(painter.end({ x: 8, y: 8 }), false);
    assert.deepEqual(events.errors, ['Choose a painted floor to fill without grid snapping.']);
});

test('over-budget continuous strokes fail atomically without throwing or leaking source changes', () => {
    const { painter, document, events } = fixture('brush', { snap: false, size: 20, shape: 'circle', anchor: 'center' });
    const before = clone(document);
    assert.doesNotThrow(() => {
        painter.start({ x: 11, y: 11 });
        for (let index = 0; index < 180; index++) painter.move({ x: 11 + index % 10, y: index % 2 ? 18 : 11 });
    });
    assert.equal(events.previews.at(-1).meta.invalid, true);
    assert.equal(painter.end({ x: 15, y: 18 }), false);
    assert.deepEqual(events.errors, ['The map floor shapes are too complex.']);
    assert.equal(events.commits.length, 0); assert.equal(events.cancels, 1); assert.deepEqual(document, before);
});

test('a freehand gesture previews complete swept cells without changing source and commits once', () => {
    const { painter, document, options, events } = fixture();
    const source = clone(document);
    assert.equal(painter.start({ x: 1.2, y: 2.2 }), true);
    assert.equal(painter.active, true); assert.equal(painter.polygon, false);
    options.assetIds = ['changed-mid-stroke']; options.size = 8;
    painter.move({ x: 5.2, y: 2.2 }); painter.move({ x: 1.2, y: 2.2 });
    assert.deepEqual(document, source);
    assert.equal(events.previews.at(-1).candidate.floors.length, 5);
    assert.equal(painter.end({ x: 5.2, y: 2.2 }), true);
    assert.equal(events.commits.length, 1); assert.equal(events.commits[0].refs.length, 5);
    assert.ok(events.commits[0].candidate.floors.every(item => item.assetId === 'stone'));
    assert.equal(painter.active, false); assert.equal(painter.end({ x: 1, y: 2 }), false);
});

test('family choices and IDs remain stable when a rectangular preview shrinks and expands', () => {
    const previousRandom = Math.random;
    let samples = 0;
    Math.random = () => [0, .4, .8][samples++ % 3];
    try {
        const { painter, events } = fixture('rectangle', { assetIds: ['a', 'b', 'c'] });
        painter.start({ x: 1, y: 1 }); painter.move({ x: 4, y: 2 });
        const original = clone(events.previews.at(-1).candidate.floors);
        assert.deepEqual(original.map(item => item.assetId), ['a', 'b', 'c']);
        painter.move({ x: 2, y: 2 }); painter.move({ x: 4, y: 2 });
        assert.deepEqual(events.previews.at(-1).candidate.floors, original);
        painter.end({ x: 4, y: 2 }); assert.deepEqual(events.commits[0].candidate.floors, original);
        assert.equal(samples, 3);
    } finally { Math.random = previousRandom; }
});

test('a circle uses the initial center and cancels cleanly before committing', () => {
    const { painter, document, events } = fixture('circle');
    painter.start({ x: 2.5, y: 2.5 }); painter.move({ x: 3.5, y: 2.5 });
    assert.equal(events.previews.at(-1).candidate.floors.length, 5);
    assert.equal(painter.cancel(), true); assert.equal(painter.cancel(), false);
    assert.equal(events.cancels, 1); assert.equal(events.commits.length, 0); assert.equal(document.floors.length, 0);
});

test('polygon clicks do not capture a drag and only committed vertices finish the shape', () => {
    const { painter, document, events } = fixture('polygon');
    assert.equal(painter.start({ x: 0, y: 0 }), false); assert.equal(painter.polygon, true);
    assert.equal(painter.end({ x: 0, y: 0 }), false);
    painter.start({ x: 3, y: 0 });
    assert.equal(painter.finish(), false); assert.equal(events.errors.length, 1); assert.equal(painter.active, true);
    painter.start({ x: 3, y: 3 }); painter.start({ x: 3, y: 3 });
    painter.move({ x: 0, y: 3 });
    assert.equal(events.previews.at(-1).candidate.floors.length, 9);
    assert.equal(painter.finish(), true);
    assert.equal(events.commits.length, 1);
    assert.equal(events.commits[0].candidate.floors.length, 6);
    assert.equal(events.commits[0].refs.length, 6); assert.equal(document.floors.length, 0);
    assert.equal(painter.active, false); assert.equal(painter.polygon, false);
});

test('a polygon can be escaped without publishing its transient filled preview', () => {
    const { painter, events } = fixture('polygon');
    for (const point of [{ x: 0, y: 0 }, { x: 3, y: 0 }, { x: 3, y: 3 }]) painter.start(point);
    assert.ok(events.previews.at(-1).candidate.floors.length > 0);
    painter.cancel(); assert.equal(events.cancels, 1); assert.equal(events.commits.length, 0);
});

test('a polygon with three collinear vertices finishes as a no-op', () => {
    const { painter, events } = fixture('polygon');
    for (const point of [{ x: .5, y: .5 }, { x: 1.5, y: 1.5 }, { x: 2.5, y: 2.5 }]) painter.start(point);
    assert.equal(painter.finish(), false);
    assert.equal(events.cancels, 1); assert.equal(events.commits.length, 0); assert.equal(events.errors.length, 0);
});

test('over-limit strokes reject the whole gesture, while a resized valid shape can recover', () => {
    const brush = fixture('brush', { maxObjects: 2 });
    brush.painter.start({ x: 0, y: 0 }); brush.painter.move({ x: 3, y: 0 });
    assert.equal(brush.events.previews.at(-1).meta.invalid, true);
    assert.equal(brush.painter.end({ x: 3, y: 0 }), false);
    assert.deepEqual(brush.events.errors, ['This map has reached the object limit.']);
    assert.equal(brush.events.cancels, 1); assert.equal(brush.events.commits.length, 0);
    assert.equal(brush.document.floors.length, 0);
    const rectangle = fixture('rectangle', { maxObjects: 2 });
    rectangle.painter.start({ x: 0, y: 0 }); rectangle.painter.move({ x: 3, y: 3 });
    assert.equal(rectangle.events.previews.at(-1).meta.invalid, true);
    rectangle.painter.end({ x: 2, y: 1 });
    assert.equal(rectangle.events.commits[0].candidate.floors.length, 2);
    assert.equal(rectangle.events.errors.length, 0);
});

test('round brush freezes its shape and size for one continuous, gap-free gesture', () => {
    const { painter, options, events } = fixture('brush', { shape: 'circle', size: 5 });
    painter.start({ x: 5.2, y: 5.2 });
    assert.equal(events.previews.at(-1).candidate.floors.length, 21);
    assert.deepEqual(Object.fromEntries(['shape', 'anchor', 'size', 'operation'].map(key => [key, events.previews.at(-1).meta[key]])),
        { shape: 'circle', anchor: 'center', size: 5, operation: 'paint' });
    options.shape = 'square'; options.size = 1;
    painter.move({ x: 15.2, y: 5.2 }); painter.end({ x: 15.2, y: 5.2 });
    const rows = events.commits[0].candidate.floors;
    for (let x = 3; x < 18; x++) assert.ok(rows.some(item => item.x === x && item.y === 5));
    assert.equal(events.commits.length, 1);
    assert.equal(events.previews.at(-1).meta.size, 5);
});

test('area eraser commits one changed draft with no selection refs and keeps the source untouched', () => {
    const { painter, document, options, events } = fixture('brush', { operation: 'erase', size: 1 });
    document.floors.push({ id: 'room', layerId: options.layerId, assetId: 'stone', x: 0, y: 0, width: 8, height: 3, rotation: 0 });
    const before = clone(document);
    painter.start({ x: 1.2, y: 1.2 }); painter.move({ x: 6.2, y: 1.2 });
    assert.deepEqual(document, before);
    assert.equal(painter.end({ x: 6.2, y: 1.2 }), true);
    assert.deepEqual(events.commits[0].refs, []);
    assert.equal(events.commits[0].candidate.floors.reduce((sum, item) => sum + item.width * item.height, 0), 18);
    assert.equal(events.commits.length, 1);
    assert.equal(events.previews.at(-1).meta.operation, 'erase');
});

test('erase cancellation, empty erasure and identical paint never publish redundant history entries', () => {
    const erase = fixture('brush', { operation: 'erase' });
    erase.painter.start({ x: 2.2, y: 2.2 });
    assert.equal(erase.painter.end({ x: 2.2, y: 2.2 }), false);
    assert.equal(erase.events.commits.length, 0); assert.equal(erase.events.cancels, 1);
    erase.document.floors.push({ id: 'tile', layerId: erase.options.layerId, assetId: 'stone', x: 2, y: 2, width: 1, height: 1, rotation: 0 });
    const before = clone(erase.document);
    erase.painter.start({ x: 2.2, y: 2.2 });
    assert.equal(erase.events.previews.at(-1).candidate.floors.length, 0);
    erase.painter.cancel(); assert.deepEqual(erase.document, before); assert.equal(erase.events.commits.length, 0);
    const paint = fixture(); paint.document.floors = clone(erase.document.floors);
    paint.painter.start({ x: 2.2, y: 2.2 });
    assert.equal(paint.painter.end({ x: 2.2, y: 2.2 }), false);
    assert.equal(paint.events.commits.length, 0); assert.equal(paint.events.cancels, 1);
});

test('erasing and repainting cache remainder IDs across repeated previews', () => {
    for (const operation of ['paint', 'erase']) {
        const { painter, document, options, events } = fixture('rectangle', { operation, assetIds: ['wood'] });
        document.floors.push({ id: 'room', layerId: options.layerId, assetId: 'stone', x: 0, y: 0, width: 6, height: 6, rotation: 0 });
        painter.start({ x: 2, y: 2 }); painter.move({ x: 4, y: 4 });
        const expanded = clone(events.previews.at(-1).candidate);
        painter.move({ x: 3, y: 3 }); painter.move({ x: 4, y: 4 });
        assert.deepEqual(events.previews.at(-1).candidate, expanded, operation);
        painter.end({ x: 4, y: 4 }); assert.deepEqual(events.commits[0].candidate, expanded, operation);
    }
});

test('unsafe fractional erase reports its actual reason and leaves the entire source intact', () => {
    const { painter, document, options, events } = fixture('brush', { operation: 'erase' });
    document.floors.push({ id: 'legacy', layerId: options.layerId, assetId: 'stone', x: .98, y: .98, width: 1.2, height: 1.2, rotation: 0 });
    const before = clone(document);
    painter.start({ x: 1.2, y: 1.2 });
    assert.equal(events.previews.at(-1).meta.invalid, true);
    assert.equal(painter.end({ x: 1.2, y: 1.2 }), false);
    assert.match(events.errors[0], /smaller than 0.05/);
    assert.equal(events.commits.length, 0); assert.deepEqual(document, before);
});

test('bucket fill keeps the initial connected region and family choices stable until pointer release', () => {
    const previousRandom = Math.random; let samples = 0;
    Math.random = () => [0, .8][samples++ % 2];
    try {
        const { painter, document, options, events } = fixture('fill', { assetIds: ['stone-a', 'stone-b'] });
        document.columns = 4; document.rows = 2;
        document.floors.push({ id: 'wall-material', layerId: options.layerId, assetId: 'grass', x: 2, y: 0, width: 1, height: 2, rotation: 0 });
        painter.start({ x: .2, y: .2 });
        const first = clone(events.previews.at(-1).candidate);
        painter.move({ x: 3.2, y: 1.2 });
        assert.deepEqual(events.previews.at(-1).candidate, first);
        assert.equal(painter.end({ x: 3.2, y: 1.2 }), true);
        assert.equal(events.commits[0].refs.length, 4); assert.equal(samples, 4);
        assert.ok(events.commits[0].candidate.floors.filter(item => item.id !== 'wall-material').every(item => item.x < 2));
        assert.equal(events.commits.length, 1);
    } finally { Math.random = previousRandom; }
});

test('fill rejects an over-limit whole region and every painting operation respects layer locks', () => {
    const { painter, document, events } = fixture('fill', { maxObjects: 2 });
    const before = clone(document);
    painter.start({ x: .2, y: .2 }); assert.equal(painter.end({ x: .2, y: .2 }), false);
    assert.equal(events.commits.length, 0); assert.deepEqual(document, before);
    assert.deepEqual(events.errors, ['This map has reached the object limit.']);
    for (const operation of ['paint', 'erase']) for (const state of ['locked', 'hidden']) {
        const current = fixture('brush', { operation });
        current.document.layers[0][state === 'locked' ? 'locked' : 'visible'] = state === 'locked';
        assert.equal(current.painter.start({ x: 1.2, y: 1.2 }), false);
        assert.equal(current.painter.active, false); assert.equal(current.events.previews.length, 0);
        assert.deepEqual(current.events.errors, ['Choose a visible, unlocked layer before painting.']);
    }
});
