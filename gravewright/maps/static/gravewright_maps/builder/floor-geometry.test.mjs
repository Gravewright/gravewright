import test from 'node:test';
import assert from 'node:assert/strict';
import { performance } from 'node:perf_hooks';
import { floorFreeContours, floorShapeFromRings, floorContainsPoint, floorShapeRings, cutFloorContours,
    floorRegionHasArea, floorRegionCoveredBy, floorGeometryError } from './floor-geometry.js';
import { newDocument, defaultLayers, clone, applyFloorContours, paintFloorCells, eraseFloorCells, sampleFloor, floodFloorCells,
    fillFloorShape, translateSelection, rotateSelection, duplicateSelection, objectsInRectangle } from './model.js';

function documentWithLayer(name) {
    return { ...newDocument(name), layers: defaultLayers() };
}

const square = (x, y, size) => [[x, y], [x + size, y], [x + size, y + size], [x, y + size]];
function fixture() {
    const document = documentWithLayer(), layerId = document.layers[0].id;
    return { document, layerId, options: { layerId, assetIds: ['stone'], makeId: () => 'free' } };
}
function vector(contours, extra = {}) {
    return { id: 'free', layerId: documentWithLayer().layers[0].id, assetId: 'stone', rotation: 0, ...floorShapeFromRings(contours), ...extra };
}

test('free rectangles retain fractional edges and circles use a smooth contour rather than cell stamps', () => {
    const document = documentWithLayer();
    const rectangle = floorFreeContours(document, { mode: 'rectangle', start: { x: 1.125, y: 2.375 }, end: { x: 3.275, y: 4.625 } });
    assert.deepEqual(rectangle, [[[1.125, 2.375], [3.275, 2.375], [3.275, 4.625], [1.125, 4.625]]]);
    const circle = vector(floorFreeContours(document, { mode: 'circle', start: { x: 5.125, y: 5.375 }, end: { x: 6.375, y: 5.375 } }));
    assert.ok(circle.shape.contours[0].length > 24);
    assert.equal(floorContainsPoint(circle, { x: 6.3, y: 5.375 }), true);
    assert.equal(floorContainsPoint(circle, { x: 6.3, y: 6.55 }), false, 'bbox corners remain empty');
    assert.equal(circle.x, 3.875); assert.equal(circle.width, 2.5);
});

test('round and square free brushes sweep skipped pointer positions continuously at sub-cell sizes', () => {
    const document = documentWithLayer(), start = { x: 1.125, y: 2.375 }, end = { x: 8.875, y: 3.125 };
    for (const shape of ['circle', 'square']) {
        const item = vector(floorFreeContours(document, { start, end, points: [start, end], size: .25, shape, anchor: 'center' }));
        for (let index = 0; index <= 30; index++) {
            const t = index / 30;
            assert.equal(floorContainsPoint(item, { x: start.x + t * (end.x - start.x), y: start.y + t * (end.y - start.y) }), true);
        }
        assert.equal(floorContainsPoint(item, { x: 4, y: 4 }), false);
        assert.ok(item.height < 1.01, 'the narrow diagonal stroke does not grow to grid rows');
    }
});

test('contours and cuts union independently; each self-intersecting ring uses even-odd coverage', () => {
    const item = vector([square(1, 1, 3), square(3, 1, 3)]);
    assert.equal(floorContainsPoint(item, { x: 3.5, y: 2 }), true, 'overlapping contours do not cancel');
    const cut = cutFloorContours(item, [square(2, 1.5, 2), square(3, 1.5, 2)]);
    assert.equal(floorContainsPoint(cut, { x: 3.5, y: 2 }), false, 'overlapping cuts do not restore coverage');
    const bowtie = vector([[[1, 1], [4, 4], [1, 4], [4, 1]]]);
    assert.equal(floorContainsPoint(bowtie, { x: 2.5, y: 1.5 }), true);
    assert.equal(floorContainsPoint(bowtie, { x: 1.25, y: 2.5 }), false);
    assert.equal(floorRegionHasArea(floorShapeRings(bowtie)), true);
    const twice = [...square(0, 0, 8), ...square(0, 0, 8)];
    assert.equal(floorRegionHasArea([square(2, 2, 1)], [twice]), true, 'a twice-wound cut is empty under even-odd fill');
    const star = Array.from({ length: 5 }, (_, index) => {
        const angle = (index * 2 % 5) * Math.PI * 2 / 5;
        return [4 + 3 * Math.cos(angle), 4 + 3 * Math.sin(angle)];
    });
    assert.equal(floorRegionHasArea([square(3.95, 3.95, .1)], [star]), true, 'a star center cannot use the convex full-mask shortcut');
});

test('free erasure clips masks to each floor, keeps other layers and deduplicates repeated erasure', () => {
    const { document, layerId, options } = fixture();
    document.layers.push({ id: 'other', name: 'Other', visible: true, locked: false });
    document.floors.push({ id: 'room', layerId, assetId: 'wood', x: .125, y: .375, width: 5, height: 5, rotation: 90 },
        { id: 'other-floor', layerId: 'other', assetId: 'wood', x: 0, y: 0, width: 5, height: 5, rotation: 0 });
    const source = clone(document), cuts = [square(-1, 1.125, 3.333)];
    assert.deepEqual(applyFloorContours(document, cuts, { ...options, operation: 'erase' }), { ok: true, changed: true, refs: [] });
    const room = document.floors[0];
    assert.equal(room.id, 'room'); assert.equal(room.rotation, 90); assert.equal(room.x, .125);
    assert.ok(room.shape.cuts.flat(2).every(value => value >= 0 && value <= 1));
    assert.equal(floorContainsPoint(room, { x: 1.5, y: 2 }), false);
    assert.equal(floorContainsPoint(room, { x: 4, y: 2 }), true);
    assert.deepEqual(document.floors[1], source.floors[1]);
    const after = clone(document);
    assert.deepEqual(applyFloorContours(document, cuts, { ...options, operation: 'erase' }), { ok: true, changed: false, refs: [] });
    assert.deepEqual(document, after);
});

test('grid painting and erasing mask vector coverage without reshaping its bounding box or restoring holes', () => {
    const { document, layerId, options } = fixture();
    const circle = floorFreeContours(document, { mode: 'circle', start: { x: 4.25, y: 4.25 }, end: { x: 6.25, y: 4.25 } });
    assert.equal(applyFloorContours(document, circle, options).ok, true);
    const original = clone(document.floors[0]);
    assert.equal(paintFloorCells(document, [{ x: 4, y: 4 }], { layerId, assetIds: ['wood'], makeId: () => 'tile' }), true);
    const masked = document.floors.find(item => item.id === 'free');
    for (const key of ['x', 'y', 'width', 'height']) assert.equal(masked[key], original[key]);
    assert.deepEqual(masked.shape.contours, original.shape.contours);
    assert.equal(floorContainsPoint(masked, { x: 4.5, y: 4.5 }), false);
    assert.equal(floorContainsPoint(masked, { x: 5.5, y: 4.5 }), true);
    assert.equal(sampleFloor(document, { x: 4.5, y: 4.5 }, { layerId }).assetId, 'wood');
    assert.equal(eraseFloorCells(document, [{ x: 5, y: 4 }], { layerId }).ok, true);
    assert.equal(floorContainsPoint(document.floors[0], { x: 5.5, y: 4.5 }), false);
    assert.equal(sampleFloor(document, { x: 2.3, y: 2.3 }, { layerId }), null, 'empty circle bbox corner is not a floor');
});

test('grid bucket sees actual vector holes while free fill retains exactly the clicked shape and identity', () => {
    const { document, layerId, options } = fixture();
    document.columns = 8; document.rows = 8;
    document.floors.push(vector([square(1, 1, 4)]));
    applyFloorContours(document, [square(2, 2, 2)], { ...options, operation: 'erase' });
    assert.equal(floodFloorCells(document, { x: 1.2, y: 1.2 }, { layerId }).length, 12);
    assert.equal(floodFloorCells(document, { x: 2.2, y: 2.2 }, { layerId }).length, 4);
    const before = clone(document.floors[0]), choices = new Map();
    assert.equal(fillFloorShape(document, { x: 1.2, y: 1.2 }, { layerId, assetIds: ['wood'], rotation: 270, choices }).changed, true);
    assert.deepEqual(document.floors[0], { ...before, assetId: 'wood', rotation: 270 });
    assert.equal(fillFloorShape(document, { x: 2.2, y: 2.2 }, { layerId, assetIds: ['wood'] }).error,
        'Choose a painted floor to fill without grid snapping.');
    assert.equal(fillFloorShape(document, { x: 1.2, y: 1.2 }, { layerId, assetIds: ['changed'], rotation: 270, choices }).changed, false,
        'a repeated preview keeps its concrete family choice');
});

test('shape translation, quarter rotation, duplication and marquee all preserve true coverage and cuts', () => {
    const { document, layerId, options } = fixture();
    const triangle = [[[2.125, 3.375], [5.125, 3.375], [2.125, 5.375]]];
    applyFloorContours(document, triangle, options);
    applyFloorContours(document, [square(2.375, 3.625, .25)], { ...options, operation: 'erase' });
    const source = clone(document.floors[0]), ref = [{ kind: 'floors', id: 'free' }];
    assert.deepEqual(objectsInRectangle(document, { x: 4.8, y: 5.1, width: .1, height: .1 }), []);
    assert.deepEqual(objectsInRectangle(document, { x: 2.4, y: 3.65, width: .1, height: .1 }), [], 'marquee wholly inside a cut is empty');
    assert.equal(translateSelection(document, ref, .375, .625), true);
    assert.deepEqual(document.floors[0].shape, source.shape);
    const moved = clone(document.floors[0]);
    assert.equal(rotateSelection(document, ref, 90), true);
    assert.equal(document.floors[0].width, moved.height);
    assert.equal(document.floors[0].height, moved.width);
    for (let turn = 0; turn < 3; turn++) assert.equal(rotateSelection(document, ref, 90), true);
    assert.deepEqual(document.floors[0], moved);
    const copies = duplicateSelection(document, ref, 1, 1);
    assert.equal(copies.length, 1); assert.deepEqual(document.floors[1].shape, moved.shape);
    document.floors[1].shape.cuts[0][0][0] = .8;
    assert.deepEqual(document.floors[0].shape, moved.shape, 'copies never share mutable contour points');
    assert.equal(sampleFloor(document, { x: moved.x + .4, y: moved.y + .4 }, { layerId })?.id, undefined, 'translated cut still erases');
});

test('free operation limits and source-byte guard reject atomically, including omitted native-effect arrays', () => {
    const { document, layerId, options } = fixture();
    delete document.particles; delete document.shaders;
    document.floors.push(vector([square(1, 1, 4)]));
    const before = clone(document), choices = new Map();
    const tooMany = Array.from({ length: 129 }, (_, index) => square(index / 1000 + 2, 2, .1));
    assert.equal(applyFloorContours(document, tooMany, { ...options, choices }).ok, false);
    assert.deepEqual(document, before); assert.equal(choices.size, 0);
    document.layers[0].locked = true;
    assert.equal(applyFloorContours(document, [square(2, 2, 1)], options).ok, false);
    document.layers[0].locked = false;
    document.name = 'x'.repeat(1000000);
    const huge = clone(document);
    assert.equal(applyFloorContours(document, [square(6, 6, 1)], options).error, 'The map project is too large.');
    assert.deepEqual(document, huge);
    assert.equal(fillFloorShape(document, { x: 1.5, y: 1.5 }, { layerId, assetIds: ['wood'] }).error, 'The map project is too large.');
    assert.deepEqual(document, huge);
});

test('empty erasure and painting the same visible material are genuine no-ops, while other material above still changes', () => {
    const { document, options } = fixture();
    const shape = [square(1.125, 1.375, 4)];
    applyFloorContours(document, shape, options);
    const before = clone(document);
    assert.equal(applyFloorContours(document, [square(2, 2, .25)], options).changed, false);
    assert.equal(applyFloorContours(document, [square(8, 8, .25)], { ...options, operation: 'erase' }).changed, false);
    assert.deepEqual(document, before);
    applyFloorContours(document, [square(2, 2, .25)], { ...options, assetIds: ['wood'], makeId: () => 'wood' });
    assert.equal(applyFloorContours(document, [square(2, 2, .25)], options).changed, true);
    assert.equal(document.floors.at(-1).assetId, 'stone');
    const after = clone(document), emptyEvenOdd = [...square(8, 8, 2), ...square(8, 8, 2)];
    assert.equal(applyFloorContours(document, [emptyEvenOdd], options).changed, false);
    assert.deepEqual(document, after, 'an even-odd polygon with no filled area never allocates an invisible source object');
});

test('large circles keep adaptive curve tolerance and every generated ring within source caps', () => {
    const document = documentWithLayer(); document.columns = 200; document.rows = 200; document.cellSize = 16;
    const rings = floorFreeContours(document, { mode: 'circle', start: { x: 100, y: 100 }, end: { x: 200, y: 100 } });
    assert.ok(rings.length > 1);
    assert.ok(rings.every(ring => ring.length <= 256));
    for (const ring of rings) for (let index = 1; index < ring.length - 1; index++) {
        const a = ring[index], b = ring[index + 1];
        const distance = Math.hypot((a[0] + b[0]) / 2 - 100, (a[1] + b[1]) / 2 - 100);
        assert.ok(100 - distance < .00201);
    }
    assert.equal(floorGeometryError(document, [vector(rings)]), null);
});

test('raw and generated over-budget paths fail predictably before bbox conversion', () => {
    const document = documentWithLayer(), points = Array.from({ length: 2001 }, (_, index) => ({ x: index % 30, y: index % 2 ? 4 : 1 }));
    assert.throws(() => floorFreeContours(document, { start: points[0], end: points.at(-1), points, shape: 'circle', size: 20 }), /too complex/);
    assert.throws(() => floorFreeContours(document, { start: points[0], end: points[199], points: points.slice(0, 200), shape: 'circle', size: 20 }), /too complex/);
});

test('fully covered intricate contours remove without retaining large invisible masks', t => {
    const { document, options } = fixture();
    const contours = Array.from({ length: 80 }, (_, index) => square(1 + index % 10 * .4, 1 + Math.floor(index / 10) * .4, .25));
    document.floors.push(vector(contours));
    const start = performance.now();
    const result = applyFloorContours(document, [square(0, 0, 8)], { ...options, operation: 'erase' });
    const elapsed = performance.now() - start;
    assert.equal(result.ok, true); assert.equal(document.floors.length, 0);
    t.diagnostic(`320-edge source erased in ${elapsed.toFixed(3)} ms (observed, no timing assertion)`);
});

const matchingStone = item => item.assetId === 'stone';
const tile = (x, y, extra = {}) => ({ id: `${x}:${y}`, assetId: 'stone', x, y, width: 1, height: 1, ...extra });

test('visible coverage combines adjacent tiles and rejects even a narrow uncovered seam', () => {
    const contours = [square(0, 0, 2)], floors = [tile(0, 0), tile(1, 0), tile(0, 1), tile(1, 1)];
    const original = structuredClone(floors);
    assert.equal(floorRegionCoveredBy(contours, floors, matchingStone), true);
    assert.deepEqual(floors, original, 'the proof never edits rows, geometry or paint order');
    floors[1].x += .00001; floors[3].x += .00001;
    assert.equal(floorRegionCoveredBy(contours, floors, matchingStone), false, 'center probes would miss this seam');
    assert.equal(floorRegionCoveredBy(contours, floors.slice(0, 3), matchingStone), false);
});

test('matching vector regions can cover a brush together without a single containing floor', () => {
    const contours = [square(1, 1, 3)];
    const floors = [vector([[[1, 1], [4, 1], [1, 4]]]), vector([[[4, 1], [4, 4], [1, 4]]])];
    assert.equal(floorRegionCoveredBy(contours, floors, matchingStone), true);
    floors[1] = vector([[[4, 1.01], [4, 4], [1.01, 4]]]);
    assert.equal(floorRegionCoveredBy(contours, floors, matchingStone), false);
});

test('coverage respects holes, independently filled cuts and matching floors restoring holes', () => {
    const contours = [square(1, 1, 4)], room = cutFloorContours(vector(contours), [square(2, 2, 1)]);
    assert.equal(floorRegionCoveredBy(contours, [room], matchingStone), false);
    assert.equal(floorRegionCoveredBy(contours, [room, tile(2, 2)], matchingStone), true);
    const twiceWoundCut = [...square(2, 2, 1), ...square(2, 2, 1)];
    const emptyCut = { ...vector(contours), shape: { contours: [square(0, 0, 1)],
        cuts: [twiceWoundCut.map(([x, y]) => [(x - 1) / 4, (y - 1) / 4])] } };
    assert.equal(floorRegionCoveredBy(contours, [emptyCut], matchingStone), true, 'an even-odd empty cut hides nothing');
});

test('only topmost visible surfaces determine coverage, including occluded mismatches and zero opacity', () => {
    const contours = [square(0, 0, 4)], room = vector(contours), wood = tile(1, 1, { assetId: 'wood' });
    assert.equal(floorRegionCoveredBy(contours, [room, wood], matchingStone), false);
    assert.equal(floorRegionCoveredBy(contours, [wood, room], matchingStone), true);
    assert.equal(floorRegionCoveredBy(contours, [room, wood, tile(1, 1)], matchingStone), true);
    assert.equal(floorRegionCoveredBy(contours, [room, { ...wood, paint: { color: null, opacity: 0 } }], matchingStone), true);
    assert.equal(floorRegionCoveredBy(contours, [room, { ...wood, paint: { color: null, opacity: .1 } }], matchingStone), false);
    assert.equal(floorRegionCoveredBy(contours, [room, tile(20, 20, { assetId: 'wood' })], matchingStone), true);
});

test('coverage leaves family, rotation and legacy style equivalence to the supplied material predicate', () => {
    const variants = new Set(['stone', 'stone-variant']);
    const contours = [[[0, 0], [2, 0], [2, 1], [0, 1]]];
    const matches = item => variants.has(item.assetId) && (item.rotation || 0) === 90 && !item.paint;
    const floors = [tile(0, 0, { rotation: 90 }), tile(1, 0, { assetId: 'stone-variant', rotation: 90 })];
    assert.equal(floorRegionCoveredBy(contours, floors, matches), true);
    assert.equal(floorRegionCoveredBy(contours, [...floors, tile(1, 0)], matches), false);
    assert.equal(floorRegionCoveredBy(contours, [...floors, tile(1, 0, { rotation: 90, paint: { color: null, opacity: .5 } })], matches), false);
});

test('crossing edges expose a narrow gap between vertex heights that a midpoint-only proof would miss', () => {
    const contours = [[[2, 0], [4, 0], [4, 4], [2, 4]]];
    const floors = [
        vector([[[2, 0], [3, 0], [2, 4]]]), vector([[[2, 0], [5, 4], [2, 4]]]),
        vector([[[3, 0], [4, 0], [4, 4]]]), vector([[[4, 0], [4, 4], [1, 4]]]),
    ];
    assert.ok([2.25, 2.75, 3.25, 3.75].every(x => floors.some(item => floorContainsPoint(item, { x, y: 2 }))));
    assert.ok(!floors.some(item => floorContainsPoint(item, { x: 3, y: .75 })));
    assert.equal(floorRegionCoveredBy(contours, floors, matchingStone), false);
});

test('two thousand adjacent unit floors prove a union without pairwise edge intersections', t => {
    const floors = Array.from({ length: 2000 }, (_, index) => tile(index % 40, Math.floor(index / 40)));
    const contours = [[[0, 0], [40, 0], [40, 50], [0, 50]]], before = structuredClone(floors);
    const started = performance.now();
    assert.equal(floorRegionCoveredBy(contours, floors, matchingStone), true);
    t.diagnostic(`2000-tile union coverage proved in ${(performance.now() - started).toFixed(3)} ms (observed, no timing assertion)`);
    assert.deepEqual(floors, before);
});

test('crossings near long-edge endpoints cannot hide a small positive-area gap', () => {
    const gap = 4e-8;
    const floor = points => ({ ...tile(0, 0), width: 200, height: 200,
        shape: { contours: [points.map(([x, y]) => [x / 200, y / 200])], cuts: [] } });
    const floors = [
        floor([[0, 0], [100, 0], [80, 200], [0, 200]]),
        floor([[0, 0], [100 - gap, 0], [160 - gap, 200], [0, 200]]),
        floor([[100, 0], [200, 0], [200, 200], [120, 200]]),
        floor([[100 + gap, 0], [200, 0], [200, 200], [40 + gap, 200]]),
    ];
    assert.equal(floorRegionCoveredBy([[[99, 0], [101, 0], [101, 200], [99, 200]]], floors, matchingStone), false);
});

test('an over-budget exact proof throws instead of silently replacing an unknown same-material region', () => {
    const row = vector([square(0, 0, 1)]);
    row.shape.cuts = Array.from({ length: 15 }, (_, ringIndex) => {
        const ring = Array.from({ length: 128 }, (_, index) => {
            const angle = (index + ringIndex / 20) * Math.PI * 2 / 128;
            return [.5 + .4 * Math.cos(angle), .5 + .4 * Math.sin(angle)];
        });
        return [...ring, ...ring];
    });
    const before = structuredClone(row);
    assert.throws(() => floorRegionCoveredBy([square(0, 0, 1)], [row], matchingStone),
        { name: 'RangeError', message: 'The map floor shapes are too complex.' });
    assert.deepEqual(row, before);
});
