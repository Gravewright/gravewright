import test from 'node:test';
import assert from 'node:assert/strict';
import { clone, defaultLayers, history, newDocument, objectKinds, wallSegments } from './model.js';
import { addWall, extendWall, moveWallNode, snapWallPoint, splitWall, wallNodes } from './wall-edit.js';

const layerId = defaultLayers()[0].id;
function fixture() {
    return { ...newDocument('Synthetic wall network'), cellSize: 32, layers: defaultLayers(),
        assets: [{ assetId: 'stone', role: 'wall', name: 'Authored wall strip' }] };
}
const wall = (id, x1, y1, x2, y2, extra = {}) =>
    ({ id, layerId, assetId: 'stone', thickness: .2, x1, y1, x2, y2, ...extra });
const refs = (...ids) => ids.map(id => ({ kind: 'walls', id }));
const noAllocation = () => { throw new Error('A no-op must not allocate identifiers.'); };
const ids = prefix => { let next = 0; return () => `${prefix}-${++next}`; };
const coordinates = walls => walls.map(({ x1, y1, x2, y2 }) => [x1, y1, x2, y2]);

test('wall edits respect exact imported raster edges instead of the padded workspace cells', () => {
    const document = fixture(); Object.assign(document, { columns: 4, rows: 3, cellSize: 50,
        sceneGeometry: { width: 197, height: 145, gridSize: 50.5, gridOffsetX: 0, gridOffsetY: 0 } });
    assert.equal(addWall(document, wall('edge', 1, 1, 3.94, 1)).ok, true);
    const before = clone(document);
    assert.equal(addWall(document, wall('outside', 1, 2, 3.95, 2)).ok, false);
    assert.equal(extendWall(document, 'edge', 2, { x: 4, y: 1 }, { id: 'extension' }).ok, false);
    assert.deepEqual(document, before);
});

test('collision-only wall networks keep their presentation when extended and allow distinct artwork strokes', () => {
    const document = fixture(); document.walls = [wall('existing', 2, 2, 6, 2, { artwork: false })];
    assert.equal(extendWall(document, 'existing', 2, { x: 6, y: 5 }, { id: 'extension' }).ok, true);
    assert.equal(document.walls[1].artwork, false, 'extending collision geometry must not paint over the background');
    assert.equal(splitWall(document, 'existing', { x: 4, y: 2 }, { makeId: ids('split') }).ok, true);
    assert.equal(document.walls.filter(item => item.artwork === false).length, 3);
    const painted = wall('painted', 2, 2, 6, 2);
    assert.equal(addWall(document, painted).changed, true, 'collision geometry cannot suppress authored artwork');
    assert.equal(document.walls.at(-1).id, 'painted');
    assert.equal(addWall(document, { ...painted, id: 'same', artwork: true }, { makeId: noAllocation }).changed, false);
});

test('overlap suppression distinguishes native barrier settings and treats omitted defaults as equivalent', () => {
    const document = fixture(); document.walls = [wall('existing', 2, 2, 8, 2)];
    const defaults = { presentation: 'normal', discovered: false, vertical: { top: null, bottom: null },
        behavior: { sound: 'block', light: 'block', vision: 'block', movement: 'block' } };
    assert.equal(addWall(document, wall('same', 2, 2, 8, 2, defaults), { makeId: noAllocation }).changed, false);
    for (const properties of [{ presentation: 'window' }, { discovered: true }, { behavior: { light: 'pass' } },
        { behavior: { sound: 'attenuate' } }, { vertical: { bottom: 0, top: 3 } }]) {
        const candidate = clone(document);
        assert.equal(addWall(candidate, wall('different', 2, 2, 8, 2, properties)).changed, true);
        assert.equal(candidate.walls.length, 2);
        assert.deepEqual(candidate.walls[1], wall('different', 2, 2, 8, 2, properties));
    }
});

test('extending and splitting retain independent copies of authored native wall settings', () => {
    const document = fixture(), properties = { presentation: 'window', discovered: true,
        behavior: { movement: 'block', vision: 'pass', light: 'pass', sound: 'attenuate' }, vertical: { bottom: -2, top: 4 } };
    document.walls = [wall('existing', 2, 2, 6, 2, properties)];
    assert.equal(extendWall(document, 'existing', 2, { x: 6, y: 5 }, { id: 'extension' }).ok, true);
    assert.deepEqual(document.walls[1].behavior, properties.behavior);
    assert.deepEqual(document.walls[1].vertical, properties.vertical);
    assert.equal(document.walls[1].presentation, 'window'); assert.equal(document.walls[1].discovered, true);
    document.walls[1].behavior.light = 'block'; document.walls[1].vertical.top = 8;
    assert.equal(document.walls[0].behavior.light, 'pass'); assert.equal(document.walls[0].vertical.top, 4);
    assert.equal(splitWall(document, 'existing', { x: 4, y: 2 }, { makeId: ids('split') }).ok, true);
    for (const source of document.walls.slice(0, 2)) {
        assert.equal(source.presentation, 'window'); assert.deepEqual(source.behavior, properties.behavior);
        assert.deepEqual(source.vertical, properties.vertical);
    }
    document.walls[1].behavior.sound = 'pass'; document.walls[1].vertical.bottom = -4;
    assert.equal(document.walls[0].behavior.sound, 'attenuate'); assert.equal(document.walls[0].vertical.bottom, -2);
});

test('repainting a collinear union in either direction preserves source identities, crossings and history', () => {
    for (const reverse of [false, true]) {
        const document = fixture();
        document.walls = [wall('left', 1, 2, 4, 2), wall('right', 4, 2, 8, 2), wall('crossing', 3, 0, 3, 5)];
        const before = clone(document), originalArray = document.walls, steps = history(document), fragmentIds = new Map();
        const candidate = reverse ? wall('gesture', 8, 2, 1, 2) : wall('gesture', 1, 2, 8, 2);
        assert.deepEqual(addWall(document, candidate, { makeId: noAllocation, fragmentIds }), { ok: true, changed: false, refs: [] });
        assert.equal(document.walls, originalArray); assert.deepEqual(document, before); assert.equal(fragmentIds.size, 0);
        assert.equal(steps.commit(document), false); assert.equal(steps.canUndo, false);
    }
});

test('partial overlap trims only the new segment and retains stable gap identities and authored orientation', () => {
    const source = fixture(); source.walls = [wall('first', 2, 2, 4, 2), wall('second', 6, 2, 8, 2)];
    const before = clone(source), first = source.walls[0], fragmentIds = new Map(), makeId = ids('gap');
    const input = wall('gesture', 0, 2, 10, 2);
    const result = addWall(source, input, { fragmentIds, makeId });
    assert.equal(result.ok, true); assert.equal(result.changed, true);
    assert.equal(source.walls[0], first); assert.deepEqual(source.walls.slice(0, 2), before.walls);
    assert.deepEqual(coordinates(source.walls.slice(2)), [[0, 2, 2, 2], [4, 2, 6, 2], [8, 2, 10, 2]]);
    assert.deepEqual(result.refs, refs('gesture', 'gap-1', 'gap-2')); assert.equal(fragmentIds.size, 2);
    const repeated = clone(before);
    assert.deepEqual(addWall(repeated, input, { fragmentIds, makeId: noAllocation }), result);
    assert.deepEqual(repeated, source); assert.deepEqual(input, wall('gesture', 0, 2, 10, 2));
    const reverse = clone(before);
    assert.equal(addWall(reverse, wall('reverse', 10, 2, 0, 2), { makeId: ids('reverse') }).ok, true);
    assert.deepEqual(coordinates(reverse.walls.slice(2)), [[10, 2, 8, 2], [6, 2, 4, 2], [2, 2, 0, 2]]);
});

test('overlap suppression distinguishes materials, thickness and named layers, and supports free diagonal segments', () => {
    for (const extra of [{ assetId: 'wood' }, { thickness: .3 }, { layerId: 'other' }]) {
        const document = fixture(); document.layers.push({ id: 'other', name: 'Other', visible: true, locked: false });
        document.walls = [wall('existing', 2, 2, 8, 2)];
        assert.equal(addWall(document, wall('new', 2, 2, 8, 2, extra)).changed, true);
        assert.deepEqual(document.walls, [wall('existing', 2, 2, 8, 2), wall('new', 2, 2, 8, 2, extra)]);
    }
    const diagonal = fixture(); diagonal.walls = [wall('diagonal', 2.125, 3.25, 5.125, 6.25)];
    const before = clone(diagonal);
    assert.equal(addWall(diagonal, wall('same', 4.125, 5.25, 2.125, 3.25), { makeId: noAllocation }).changed, false);
    assert.deepEqual(diagonal, before);
    assert.equal(addWall(diagonal, wall('longer', 1.125, 2.25, 6.125, 7.25), { makeId: ids('tail') }).ok, true);
    assert.deepEqual(coordinates(diagonal.walls.slice(1)), [[1.125, 2.25, 2.125, 3.25], [5.125, 6.25, 6.125, 7.25]]);
});

test('a new T endpoint splits its source in the same atomic edit without changing any independent door', () => {
    const document = fixture(); document.walls = [wall('main', 2, 5, 8, 5)];
    document.doors = [{ ...wall('door', 4, 5, 6, 5), state: 'open', blueprint: { version: 1, graphs: {} } }];
    const before = clone(document), doors = document.doors, steps = history(document);
    const result = addWall(document, wall('branch', 5, 5, 5, 9), { makeId: ids('join') });
    assert.equal(result.ok, true); assert.deepEqual(result.refs, refs('main', 'join-1', 'branch'));
    assert.deepEqual(coordinates(document.walls), [[2, 5, 5, 5], [5, 5, 8, 5], [5, 5, 5, 9]]);
    assert.equal(document.walls[0].id, 'main'); assert.ok(document.walls.every(row => row.assetId === 'stone' && row.thickness === .2));
    assert.equal(document.doors, doors); assert.deepEqual(document.doors, before.doors);
    const joint = wallNodes(document, { layerId }).find(node => node.x === 5 && node.y === 5);
    assert.deepEqual(joint.ends, [{ wallId: 'main', endpoint: 2 }, { wallId: 'join-1', endpoint: 1 }, { wallId: 'branch', endpoint: 1 }]);
    assert.deepEqual(coordinates(document.walls.slice(0, 2).flatMap(row => wallSegments(document, row))), [[2, 5, 4, 5], [6, 5, 8, 5]]);
    assert.equal(steps.commit(document), true); assert.deepEqual(steps.undo(), before); assert.deepEqual(steps.redo(), document);
    const disconnected = clone(before);
    assert.equal(addWall(disconnected, wall('branch', 5, 5, 5, 9), { connect: false }).ok, true);
    assert.equal(disconnected.walls.length, 2); assert.deepEqual(disconnected.walls[0], before.walls[0]);
});

test('multiple T attachments split each source deterministically and preserve preview fragment identities', () => {
    const source = fixture(); source.walls = [wall('bottom', 0, 2, 10, 2), wall('top', 0, 8, 10, 8)];
    const candidate = wall('vertical', 5, 2, 5, 8), fragmentIds = new Map(), first = clone(source);
    const result = addWall(first, candidate, { makeId: ids('join'), fragmentIds });
    assert.equal(result.refs.length, 5); assert.equal(fragmentIds.size, 2);
    const repeated = clone(source);
    assert.deepEqual(addWall(repeated, candidate, { makeId: noAllocation, fragmentIds }), result);
    assert.deepEqual(repeated, first); assert.deepEqual(source.walls.map(row => row.id), ['bottom', 'top']);
});

test('new spans and T connections reject short fragments, bounds, invalid IDs and the combined object limit atomically', () => {
    const fixtures = [];
    const tinyRemainder = fixture(); tinyRemainder.walls = [wall('existing', 2.05, 2, 8, 2)];
    fixtures.push([tinyRemainder, wall('new', 2, 2, 8, 2)]);
    const tinyJoin = fixture(); tinyJoin.walls = [wall('existing', 2, 5, 8, 5)];
    fixtures.push([tinyJoin, wall('new', 2.05, 5, 2.05, 8)]);
    const maxed = fixture(); maxed.walls = [wall('existing', 2, 5, 8, 5)];
    maxed.lights = Array.from({ length: 1998 }, (_, index) => ({ id: `lamp-${index}`, layerId, x: 1, y: 1 }));
    fixtures.push([maxed, wall('new', 5, 5, 5, 8)]);
    fixtures.push([fixture(), wall('new', -1, 2, 3, 2)]);
    fixtures.push([fixture(), wall('new', 2, 2, 3, 2, { thickness: 0 })]);
    for (const [document, incoming] of fixtures) {
        const before = clone(document), fragmentIds = new Map();
        assert.equal(addWall(document, incoming, { fragmentIds, makeId: noAllocation }).ok, false);
        assert.deepEqual(document, before); assert.equal(fragmentIds.size, 0);
    }
    const collision = fixture(); collision.walls = [wall('taken', 2, 2, 4, 2)];
    const before = clone(collision);
    assert.equal(addWall(collision, wall('taken', 8, 2, 10, 2)).ok, false); assert.deepEqual(collision, before);
    assert.equal(addWall(collision, wall('new', 8, 2, 10, 2), { maxObjects: 0 }).ok, false);
    const exact = fixture(); exact.lights = Array.from({ length: 1999 }, (_, index) => ({ id: `lamp-${index}`, layerId, x: 1, y: 1 }));
    assert.equal(addWall(exact, wall('last', 0, 0, .1, 0)).ok, true);
    assert.equal(objectKinds.reduce((sum, kind) => sum + exact[kind].length, 0), 2000);
    assert.equal(addWall(exact, wall('same', 0, 0, .1, 0), { makeId: noAllocation }).changed, false);
});

test('snap prefers endpoints over nearby projections and preserves unsnapped fractional coordinates exactly', () => {
    const document = fixture(); document.walls = [wall('first', 2, 3, 8, 3), wall('second', 9, 1, 9, 6)];
    const before = clone(document);
    assert.deepEqual(snapWallPoint(document, { x: 2.18, y: 3.03 }, { layerId, tolerance: .25 }),
        { x: 2, y: 3, snapped: true, wallId: 'first', endpoint: 1 });
    assert.deepEqual(snapWallPoint(document, { x: 4.375, y: 3.12 }, { layerId, tolerance: .2 }),
        { x: 4.375, y: 3, snapped: true, wallId: 'first' });
    assert.deepEqual(snapWallPoint(document, { x: 8.1, y: 3 }, { layerId, tolerance: .2 }),
        { x: 8, y: 3, snapped: true, wallId: 'first', endpoint: 2 });
    assert.deepEqual(snapWallPoint(document, { x: 4.123456789, y: 4.987654321 }, { layerId, tolerance: .2 }),
        { x: 4.123456789, y: 4.987654321, snapped: false });
    assert.deepEqual(snapWallPoint(document, { x: 4.375, y: 3.12 }, { layerId, tolerance: .2, excludeIds: ['first'] }),
        { x: 4.375, y: 3.12, snapped: false });
    assert.deepEqual(document, before);
});

test('snap and nodes respect hidden, locked and other layers and never attach to independent doors', () => {
    const document = fixture();
    document.layers.push({ id: 'other', name: 'Other', visible: true, locked: false });
    document.walls = [wall('other-wall', 2, 3, 8, 3, { layerId: 'other' })];
    document.doors = [{ ...wall('door', 2, 3, 8, 3), state: 'closed' }];
    assert.equal(snapWallPoint(document, { x: 2, y: 3 }, { layerId }).snapped, false);
    assert.deepEqual(wallNodes(document, { layerId }), []);
    assert.equal(wallNodes(document).length, 2);
    for (const property of ['visible', 'locked']) {
        document.layers[1][property] = property === 'locked';
        assert.equal(snapWallPoint(document, { x: 2, y: 3 }, { layerId: 'other' }).snapped, false);
        assert.deepEqual(wallNodes(document), []);
        document.layers[1][property] = property === 'visible';
    }
});

test('node keys are stable and shared only within a layer, across wall materials and endpoint orientations', () => {
    const document = fixture(); document.layers.push({ id: 'other', name: 'Other', visible: true, locked: false });
    document.walls = [wall('a', 2, 2, 5, 2), wall('b', 5, 2, 5, 6, { assetId: 'wood', thickness: .5 }),
        wall('c', 8, 2, 5, 2), wall('other', 5, 2, 10, 2, { layerId: 'other' })];
    const nodes = wallNodes(document), joint = nodes.find(node => node.ends.length === 3);
    assert.deepEqual(joint.ends, [{ wallId: 'a', endpoint: 2 }, { wallId: 'b', endpoint: 1 }, { wallId: 'c', endpoint: 2 }]);
    assert.deepEqual(wallNodes(document), nodes);
    assert.equal(new Set(nodes.map(node => node.key)).size, nodes.length);
    joint.ends[0].wallId = 'changed'; joint.x = 99;
    assert.equal(wallNodes(document).find(node => node.ends.length === 3).x, 5);
    assert.equal(document.walls[0].id, 'a');
    document.walls[1].x1 += 1e-9;
    assert.equal(wallNodes(document, { layerId }).find(node => node.ends.length === 3).x, 5);
});

test('moving a joint edits every connected wall as one undo step and leaves doors and other layers intact', () => {
    const document = fixture(); document.layers.push({ id: 'other', name: 'Other', visible: true, locked: false });
    document.walls = [wall('a', 2, 2, 5, 2), wall('b', 5, 2, 5, 6, { assetId: 'wood', thickness: .5 }),
        wall('c', 8, 2, 5, 2), wall('other', 5, 2, 10, 2, { layerId: 'other' })];
    document.doors = [{ ...wall('door', 3, 2, 4, 2), state: 'closed' }];
    const node = wallNodes(document, { layerId }).find(value => value.ends.length === 3), before = clone(document), steps = history(document);
    assert.deepEqual(moveWallNode(document, node.key, { x: 6.125, y: 3.375 }, { layerId }),
        { ok: true, changed: true, refs: refs('a', 'b', 'c') });
    assert.deepEqual(coordinates(document.walls), [[2, 2, 6.125, 3.375], [6.125, 3.375, 5, 6], [8, 2, 6.125, 3.375], [5, 2, 10, 2]]);
    assert.deepEqual(document.doors, before.doors); assert.deepEqual(document.assets, before.assets);
    assert.equal(document.walls[1].assetId, 'wood'); assert.equal(document.walls[1].thickness, .5);
    assert.equal(steps.commit(document), true); assert.deepEqual(steps.undo(), before); assert.deepEqual(steps.redo(), document);
});

test('node no-ops and rejected moves preserve every source object and protected layer', () => {
    const document = fixture(); document.walls = [wall('a', 2, 2, 5, 2), wall('b', 5, 2, 5, 6)];
    const node = wallNodes(document, { layerId }).find(value => value.ends.length === 2), before = clone(document), original = document.walls;
    assert.deepEqual(moveWallNode(document, node.key, node, { layerId }), { ok: true, changed: false, refs: [] });
    assert.equal(document.walls, original);
    for (const point of [{ x: 2, y: 2 }, { x: 2.05, y: 2 }, { x: -1, y: 3 }, { x: 41, y: 3 }, { x: NaN, y: 3 }]) {
        assert.equal(moveWallNode(document, node.key, point, { layerId }).ok, false); assert.deepEqual(document, before);
    }
    for (const property of ['locked', 'visible']) {
        document.layers[0][property] = property === 'locked';
        const protectedSource = clone(document);
        assert.equal(moveWallNode(document, node.key, { x: 6, y: 3 }, { layerId }).ok, false);
        assert.deepEqual(document, protectedSource);
        document.layers[0][property] = property === 'visible';
    }
});

test('split projects onto the chosen wall, retains its original first ID and art, and caches the other half', () => {
    const source = fixture(); source.walls = [wall('original', 2, 3, 8, 3)];
    source.doors = [{ ...wall('door', 4, 3, 6, 3), state: 'open' }];
    const before = clone(source), fragmentIds = new Map(), first = clone(source);
    assert.deepEqual(splitWall(first, 'original', { x: 5, y: 3.1 }, { makeId: () => 'second', fragmentIds, tolerance: .2 }),
        { ok: true, changed: true, refs: refs('original', 'second') });
    assert.deepEqual(first.walls, [wall('original', 2, 3, 5, 3), wall('second', 5, 3, 8, 3)]);
    assert.deepEqual(first.doors, before.doors); assert.deepEqual(source, before);
    const repeated = clone(source);
    assert.equal(splitWall(repeated, 'original', { x: 5, y: 3 }, { fragmentIds, makeId: noAllocation }).ok, true);
    assert.deepEqual(repeated, first);
    const final = clone(first);
    assert.deepEqual(splitWall(first, 'original', { x: 5, y: 3 }, { makeId: noAllocation }), { ok: true, changed: false, refs: [] });
    assert.deepEqual(first, final);
});

test('split validates distance, minimum parts and combined limits before changing the source', () => {
    const document = fixture(); document.walls = [wall('original', 2, 3, 8, 3)];
    const before = clone(document);
    for (const [point, options] of [[{ x: 5, y: 4 }, {}], [{ x: 2.05, y: 3 }, {}], [{ x: 7.95, y: 3 }, {}],
        [{ x: 5, y: 3 }, { maxObjects: 1 }], [{ x: 5, y: 3 }, { tolerance: -1 }]]) {
        const fragmentIds = new Map();
        assert.equal(splitWall(document, 'original', point, { ...options, fragmentIds, makeId: noAllocation }).ok, false);
        assert.deepEqual(document, before); assert.equal(fragmentIds.size, 0);
    }
    assert.equal(splitWall(document, 'original', { x: 2, y: 3 }, { makeId: noAllocation }).changed, false);
    assert.equal(splitWall(document, 'missing', { x: 5, y: 3 }).ok, false);
});

test('extension inherits art and thickness, preserves the original wall and joins a target segment atomically', () => {
    const source = fixture(); source.walls = [wall('source', 1, 2, 3, 2, { assetId: 'wood', thickness: .35 }), wall('target', 7, 0, 7, 8)];
    const before = clone(source), fragmentIds = new Map(), first = clone(source);
    const result = extendWall(first, 'source', 2, { x: 7, y: 2 }, { id: 'gesture', makeId: ids('join'), fragmentIds });
    assert.equal(result.ok, true); assert.deepEqual(first.walls[0], before.walls[0]);
    assert.deepEqual(first.walls.at(-1), wall('gesture', 3, 2, 7, 2, { assetId: 'wood', thickness: .35 }));
    assert.equal(new Set(first.walls.map(row => row.id)).size, first.walls.length);
    assert.equal(wallNodes(first, { layerId }).find(node => node.x === 7 && node.y === 2).ends.length, 3);
    const repeated = clone(source);
    assert.deepEqual(extendWall(repeated, 'source', 2, { x: 7, y: 2 }, { id: 'gesture', makeId: noAllocation, fragmentIds }), result);
    assert.deepEqual(repeated, first);
    const movedPreview = clone(source);
    assert.equal(extendWall(movedPreview, 'source', 2, { x: 7, y: 3 }, { id: 'gesture', makeId: ids('moved'), fragmentIds }).ok, true);
    assert.equal(movedPreview.walls.at(-1).id, 'gesture');
    assert.equal(new Set(movedPreview.walls.map(row => row.id)).size, movedPreview.walls.length);
    assert.deepEqual(source, before);
});

test('extension can begin at either end, ignores covered retracing, and rejects collapsed or invalid endpoints', () => {
    const document = fixture(); document.walls = [wall('original', 2, 3, 8, 3)];
    const before = clone(document);
    assert.equal(extendWall(document, 'original', 2, { x: 5, y: 3 }, { makeId: noAllocation }).changed, false);
    assert.equal(extendWall(document, 'original', 1, { x: 2, y: 3 }, { makeId: noAllocation }).changed, false);
    assert.deepEqual(document, before);
    assert.equal(extendWall(document, 'original', 3, { x: 1, y: 1 }).ok, false);
    assert.equal(extendWall(document, 'original', 1, { x: 2.01, y: 3.01 }).ok, false);
    assert.equal(extendWall(document, 'original', 1, { x: -1, y: 3 }).ok, false);
    assert.deepEqual(document, before);
    assert.equal(extendWall(document, 'original', 1, { x: 0, y: 3 }, { id: 'extension' }).ok, true);
    assert.deepEqual(document.walls.at(-1), wall('extension', 2, 3, 0, 3));
});

test('every wall operation rejects unsupported, malformed, hidden or locked documents without partial changes', () => {
    const cases = [];
    for (const schemaVersion of [1, 2, 4]) { const document = fixture(); document.schemaVersion = schemaVersion; cases.push(document); }
    for (const change of [{ visible: false }, { locked: true }]) {
        const document = fixture(); Object.assign(document.layers[0], change); cases.push(document);
    }
    const duplicate = fixture(); duplicate.lights = [{ id: 'original', layerId, x: 1, y: 1 }]; cases.push(duplicate);
    const orphan = fixture(); orphan.layers = []; cases.push(orphan);
    for (const document of cases) {
        document.walls = [wall('original', 2, 3, 8, 3)];
        const before = clone(document);
        assert.equal(addWall(document, wall('new', 2, 5, 8, 5)).ok, false);
        assert.equal(splitWall(document, 'original', { x: 5, y: 3 }).ok, false);
        assert.equal(extendWall(document, 'original', 2, { x: 9, y: 3 }).ok, false);
        assert.deepEqual(wallNodes(document), []);
        assert.equal(snapWallPoint(document, { x: 2, y: 3 }, { layerId }).snapped, false);
        assert.deepEqual(document, before);
    }
    assert.equal(addWall(null, wall('new', 2, 5, 8, 5)).ok, false);
    assert.equal(splitWall(null, 'missing', { x: 1, y: 1 }).ok, false);
    assert.equal(extendWall(null, 'missing', 1, { x: 1, y: 1 }).ok, false);
    for (const walls of [null, {}, 'invalid']) {
        const malformed = { ...fixture(), walls }, before = clone(malformed);
        assert.equal(splitWall(malformed, 'missing', { x: 1, y: 1 }).ok, false);
        assert.equal(extendWall(malformed, 'missing', 1, { x: 1, y: 1 }).ok, false);
        assert.deepEqual(malformed, before);
    }
});

test('source size and painted-surface budgets reject an entire edit while retaining every original row', () => {
    const document = fixture(); document.columns = document.rows = 200; document.cellSize = 256;
    const before = clone(document);
    assert.equal(addWall(document, wall('diagonal', 0, 0, 200, 200)).ok, false);
    assert.deepEqual(document, before);
    const huge = fixture(); huge.name = 'x'.repeat(999500);
    const fragmentIds = new Map(), original = clone(huge);
    assert.equal(addWall(huge, wall('new', 2, 3, 8, 3), { fragmentIds }).ok, false);
    assert.deepEqual(huge, original); assert.equal(fragmentIds.size, 0);
});
