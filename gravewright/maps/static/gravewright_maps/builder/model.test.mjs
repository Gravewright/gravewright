import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultBlueprint, eventGraph, connectNodes, upgradeBlueprint, simulateGraph, blueprintAppearance } from './blueprint-model.js';
import { detachDocumentAsset } from './asset-removal.js';
import { clone, newDocument, normalizeDocument, defaultLayers, nearestWall, doorFits, doorSegment, wallSegments,
    translateObject, translateSelection, rotateSelection, duplicateSelection, selectionBounds, objectsInRectangle,
    removeObject, fitsBounds, history, familyAssetIds, sampleAssetId, floorBrushCells, floorRectangleCells,
    floorCircleCells, floorPolygonCells, paintFloorCells, eraseFloorCells, sampleFloor, floodFloorCells, snapWallSegment,
    documentEditingMode, setEditingMode, normalizeFloorPaint, applyFloorContours, fillFloorShape, floorContainsPoint, applyTerrainStroke,
    readyMapGeometry, setBackgroundImage, createEmptyObject, doorDisplaySegment, doorRotationPoint } from './model.js';
import { terrainBrushAlpha } from './terrain-brush.js';

function documentWithLayer(name) {
    return { ...newDocument(name), layers: defaultLayers() };
}

const wall = () => ({ id: 'wall', assetId: null, x1: 2, y1: 2, x2: 10, y2: 2, thickness: .18 });
const door = () => ({ id: 'door', assetId: null, x1: 5, y1: 2, x2: 7, y2: 2, thickness: .18, state: 'closed' });
const paintBox = [[[2.125, 2.375], [4.125, 2.375], [4.125, 4.375], [2.125, 4.375]]];
const floorBox = (x, y, width, height) => [[x, y], [x + width, y], [x + width, y + height], [x, y + height]];
const floorRow = (document, id, assetId, x, y, width = 1, height = 1, extra = {}) =>
    ({ id, layerId: document.layers[0].id, assetId, x, y, width, height, rotation: 0, ...extra });
const unexpectedChoice = () => { throw new Error('An ignored repaint must not allocate or reroll.'); };
test('door pivots keep the chosen point fixed for editing and open artwork without moving collision', () => {
    const expected = { start: [5, 2, 5, 4], center: [6, 1, 6, 3], end: [7, 0, 7, 2] };
    for (const [anchor, coordinates] of Object.entries(expected)) {
        const document = documentWithLayer('Door pivots'), item = { ...door(), layerId: document.layers[0].id, rotationAnchor: anchor };
        document.doors.push(item);
        const before = clone(item), pivot = doorRotationPoint(item), opened = doorDisplaySegment({ ...item, state: 'open' });
        assert.deepEqual([opened.x1, opened.y1, opened.x2, opened.y2], coordinates);
        assert.deepEqual(item, before, 'opening artwork must leave the wall opening in place');
        assert.equal(rotateSelection(document, [{ kind: 'doors', id: item.id }], 90), true);
        assert.deepEqual([item.x1, item.y1, item.x2, item.y2], coordinates);
        assert.deepEqual(doorRotationPoint(item), pivot);
        const refs = duplicateSelection(document, [{ kind: 'doors', id: item.id }]);
        assert.equal(document.doors.find(row => row.id === refs[0].id).rotationAnchor, anchor);
        assert.deepEqual(normalizeDocument(document), document);
    }
    const legacy = door();
    assert.deepEqual(doorDisplaySegment({ ...legacy, state: 'open' }), doorSegment(null, legacy));
    assert.equal(blueprintAppearance({ ...legacy, state: 'open', rotationAnchor: 'start' }).visible, true);
    assert.equal(blueprintAppearance({ ...legacy, state: 'open' }).visible, false);
    const document = documentWithLayer('Boundary');
    document.doors.push({ ...door(), x1: 0, y1: 0, x2: 2, y2: 0, layerId: document.layers[0].id, rotationAnchor: 'end' });
    const before = clone(document);
    assert.equal(rotateSelection(document, [{ kind: 'doors', id: 'door' }]), false);
    assert.deepEqual(document, before);
    for (const value of [null, false, 0, 'left', {}, []]) {
        const invalid = clone(before); invalid.doors[0].rotationAnchor = value;
        assert.throws(() => normalizeDocument(invalid), /rotation anchor/);
    }
});
const mapImage = '00000000-0000-4000-8000-000000000021';

test('element names survive document loading and legacy door geometry promotion without changing identity', () => {
    const document = newDocument(), name = '雪🗺'.repeat(60);
    for (const kind of ['floors', 'walls', 'doors', 'decorations', 'lights', 'particles', 'shaders', 'regions'])
        document[kind].push({ id: kind, name });
    assert.deepEqual(normalizeDocument(document), document);
    assert.equal(createEmptyObject(newDocument(), { x: 1, y: 1, name }).name, name);
    for (const invalid of ['', ' ', null, 1, {}, [], 'bad\0name', 'x'.repeat(121)]) {
        const invalidDocument = newDocument(); invalidDocument.lights.push({ id: 'light', name: invalid });
        assert.throws(() => normalizeDocument(invalidDocument), /name/);
    }
    const legacy = { schemaVersion: 1, columns: 20, rows: 20, floors: [],
        walls: [wall()], doors: [{ id: 'door', assetId: null, wallId: 'wall', offset: 1, width: 2, state: 'closed', name: 'Gate 雪' }] };
    const promoted = normalizeDocument(legacy);
    assert.equal(promoted.doors[0].name, 'Gate 雪');
    assert.equal(promoted.doors[0].id, legacy.doors[0].id);
    assert.equal(legacy.schemaVersion, 1);
});

test('ready-map geometry retains common image dimensions and bounds oversized or narrow images', () => {
    assert.deepEqual(readyMapGeometry({ width: 2800, height: 2100 }), { columns: 40, rows: 30, cellSize: 70 });
    for (const [width, height] of [[8000, 4000], [4000, 8000], [400000, 1], [1, 400000], [1, 1]]) {
        const geometry = readyMapGeometry({ width, height }, 70, { maxPixels: 1_000_000 });
        assert.ok(geometry.columns >= 1 && geometry.columns <= 200);
        assert.ok(geometry.rows >= 1 && geometry.rows <= 200);
        assert.ok(geometry.columns * geometry.rows * geometry.cellSize ** 2 <= 1_000_000);
        if (Math.min(width, height) > 1) assert.ok(Math.abs(geometry.columns / geometry.rows - width / height) < .1);
    }
    for (const size of [0, NaN, 15, 257, 70.5]) assert.throws(() => readyMapGeometry({ width: 100, height: 100 }, size));
    for (const asset of [{ width: 0, height: 100 }, { width: 20, height: Infinity }, {}, null]) assert.throws(() => readyMapGeometry(asset));
});

test('ready-map background is independent of brush roles, retained on load and restored with undo', () => {
    const document = newDocument('Imported map'), steps = history(document), before = clone(document);
    assert.equal(setBackgroundImage(document, mapImage, { columns: 30, rows: 20, cellSize: 80 }), true);
    assert.deepEqual(document.backgroundImage, { assetId: mapImage });
    assert.deepEqual(document.assets, []);
    assert.deepEqual(document.layers, before.layers);
    assert.equal(steps.commit(document), true);
    assert.deepEqual(normalizeDocument(document), document);
    assert.equal(setBackgroundImage(document, mapImage), false);
    assert.deepEqual(steps.undo(), before);
    assert.deepEqual(steps.redo(), document);
    assert.equal(setBackgroundImage(document, null), true);
    assert.equal(Object.hasOwn(document, 'backgroundImage'), false);
    assert.equal(setBackgroundImage(document, null), false);
});

test('a ready-map replacement never crops or silently drops existing authored objects', () => {
    const document = newDocument();
    document.decorations.push({ id: 'existing', x: 30, y: 20, width: 2, height: 2, rotation: 0 });
    const before = clone(document);
    assert.throws(() => setBackgroundImage(document, mapImage, { columns: 20, rows: 20 }), /outside/);
    assert.deepEqual(document, before);
    for (const geometry of [{ columns: 201 }, { rows: 0 }, { cellSize: 15 }, { columns: 200, rows: 200, cellSize: 256 }]) {
        assert.throws(() => setBackgroundImage(document, mapImage, geometry));
        assert.deepEqual(document, before);
    }
    assert.throws(() => setBackgroundImage(document, 'not-an-image'));
    assert.deepEqual(document, before);
    assert.equal(setBackgroundImage(document, mapImage), true);
    assert.deepEqual(document.decorations, before.decorations);
    assert.deepEqual(document.layers, before.layers);
});

test('Empty Objects have editable native geometry, identity and behavior without an image', () => {
    const document = newDocument(), before = clone(document);
    const item = createEmptyObject(document, { id: mapImage, x: 2.125, y: 3.375, width: 2, height: 1, name: '  Switch logic  ' });
    assert.deepEqual(item, { id: mapImage, layerId: document.layers[0].id, name: 'Switch logic', empty: true,
        assetId: null, x: 2.125, y: 3.375, width: 2, height: 1, rotation: 0, lever: { state: 'off' } });
    assert.deepEqual(document, before);
    document.decorations.push(item);
    assert.deepEqual(normalizeDocument(document), document);
    assert.equal(translateObject(document, 'decorations', item.id, 1, 2), true);
    assert.equal(document.decorations[0].assetId, null);
    assert.equal(document.decorations[0].empty, true);
    assert.deepEqual(document.decorations[0].lever, { state: 'off' });
});

test('Empty Object creation rejects invalid placement, layers and duplicate identities', () => {
    const document = newDocument(), defaults = { id: mapImage, x: 2, y: 2 };
    for (const change of [{ x: -1 }, { width: 0 }, { y: NaN }, { height: 30 }, { x: 0, y: 0, rotation: 45 },
        { layerId: 'missing' }, { name: '' }, { name: 'x'.repeat(121) }, { id: 'bad' }]) {
        assert.throws(() => createEmptyObject(document, { ...defaults, ...change }));
        assert.deepEqual(document.decorations, []);
    }
    document.layers[0].locked = true;
    assert.throws(() => createEmptyObject(document, defaults));
    document.layers[0].locked = false; document.layers[0].visible = false;
    assert.throws(() => createEmptyObject(document, defaults));
    document.layers[0].visible = true;
    document.decorations.push(createEmptyObject(document, defaults));
    assert.throws(() => createEmptyObject(document, defaults));
});

test('Empty source data cannot gain an image or a torch during normalization', () => {
    for (const change of [{ assetId: mapImage }, { torch: {} }, { empty: false }, { lever: null }]) {
        const document = newDocument();
        document.decorations.push({ ...createEmptyObject(document, { id: mapImage, x: 2, y: 2 }), ...change });
        assert.throws(() => normalizeDocument(document), /Empty Object/);
    }
});

test('loading discards removed event graphs while preserving every element, asset and supported sequence', () => {
    const document = newDocument('Existing project');
    document.assets.push({ assetId: 'owned-image', role: 'decoration', name: 'Authored image' });
    for (const [array, kind] of [['doors', 'door'], ['decorations', 'lever'], ['regions', 'region']]) {
        const blueprint = defaultBlueprint(kind), event = kind === 'region' ? 'presence:enter' : 'interact';
        blueprint.graphs[event] = eventGraph(event);
        for (const removed of ['change', 'enter:closed', 'exit:off', 'interact:on']) blueprint.graphs[removed] = { nodes: [], edges: [] };
        document[array].push({ id: kind, name: 'Keep this element', assetId: 'owned-image', blueprint });
    }
    const source = clone(document), loaded = normalizeDocument(document);
    assert.deepEqual(document, source);
    assert.deepEqual(loaded.assets, source.assets);
    for (const array of ['doors', 'decorations', 'regions']) {
        assert.equal(loaded[array].length, 1);
        const event = array === 'regions' ? 'presence:enter' : 'interact';
        const expected = clone(source[array][0]); expected.blueprint.graphs = { [event]: expected.blueprint.graphs[event] };
        assert.deepEqual(loaded[array][0], expected);
    }
    assert.deepEqual(normalizeDocument(loaded), loaded);
});

test('grid ignores the same visible material even with unrelated rectangles, vectors and hidden backing in the layer', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.floors = [floorRow(doc, 'backing', 'wood', 1, 1), floorRow(doc, 'same', 'stone', 1, 1),
        floorRow(doc, 'invisible', 'wood', 1, 1, 1, 1, { paint: { color: null, opacity: 0 } }),
        floorRow(doc, 'room', 'stone', 5, 5, 5, 5, { paint: { color: null, opacity: 1 } }),
        floorRow(doc, 'vector', 'wood', 20, 20, 2, 2, { shape: { contours: [[[0, 0], [1, 0], [1, 1]]], cuts: [] } })];
    const before = clone(doc), floors = doc.floors, choices = new Map(), steps = history(doc);
    assert.equal(paintFloorCells(doc, [{ x: 1, y: 1 }, { x: 7, y: 7 }],
        { layerId, assetIds: ['stone'], choices, random: unexpectedChoice, makeId: unexpectedChoice }), true);
    assert.equal(doc.floors, floors); assert.deepEqual(doc, before); assert.equal(choices.size, 0);
    assert.equal(steps.commit(doc), false); assert.equal(steps.canUndo, false);
});

test('family grid repaint keeps existing variants and changes only cells with a different visible material', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.assets = [{ assetId: 'a', role: 'floor', family: 'Stone' }, { assetId: 'b', role: 'floor', family: 'Stone' }];
    doc.floors = [floorRow(doc, 'keep-a', 'a', 0, 0), floorRow(doc, 'replace', 'wood', 1, 0), floorRow(doc, 'keep-b', 'b', 2, 0)];
    const original = clone(doc), first = doc.floors[0], last = doc.floors[2], choices = new Map();
    let allocations = 0, samples = 0;
    const options = { layerId, assetIds: ['a', 'b'], choices, makeId: () => `new-${++allocations}`, random: () => { samples++; return .99; } };
    assert.equal(paintFloorCells(doc, [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 2, y: 0 }], options), true);
    assert.equal(allocations, 1); assert.equal(samples, 1); assert.deepEqual([...choices.keys()], ['1:0']);
    assert.equal(doc.floors[0], first); assert.equal(doc.floors[1], last);
    assert.deepEqual(doc.floors.at(-1), floorRow(doc, 'new-1', 'b', 1, 0));
    const after = clone(doc);
    assert.equal(paintFloorCells(doc, [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 2, y: 0 }], options), true);
    assert.deepEqual(doc, after); assert.equal(allocations, 1); assert.equal(samples, 1);
    assert.deepEqual(original.floors.filter(item => item.id !== 'replace'), [first, last]);
});

test('grid tests complete topmost cell coverage instead of a center or a matching floor hidden below', () => {
    for (const reverse of [false, true]) {
        const doc = documentWithLayer(), layerId = doc.layers[0].id;
        const lower = floorRow(doc, 'lower', 'stone', 0, 0, 3, 3);
        const upper = floorRow(doc, 'sliver', 'wood', .1, .1, .1, .1);
        doc.floors = reverse ? [upper, lower] : [lower, upper];
        const before = clone(doc);
        assert.equal(paintFloorCells(doc, [{ x: 0, y: 0 }], { layerId, assetIds: ['stone'], makeId: () => 'replacement' }), true);
        if (reverse) { assert.deepEqual(doc, before); continue; }
        assert.equal(doc.floors.at(-1).id, 'replacement');
        for (const point of [{ x: .15, y: .15 }, { x: .5, y: .5 }]) {
            const present = doc.floors.filter(item => floorContainsPoint(item, point));
            assert.deepEqual(present.map(item => item.id), ['replacement'], 'replacement removes covered backing too');
        }
        assert.equal(sampleFloor(doc, { x: 2, y: 2 }, { layerId }).assetId, 'stone');
    }
});

test('grid no-ops use actual vector holes and union coverage with rotation and paint style equivalence', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.floors = [floorRow(doc, 'back', 'stone', 0, 0, 3, 3),
        floorRow(doc, 'cut-cover', 'wood', 0, 0, 3, 3, { shape: { contours: [[[0, 0], [1, 0], [1, 1], [0, 1]]],
            cuts: [[[0, 0], [1 / 3, 0], [1 / 3, 1], [0, 1]]] } })];
    const before = clone(doc);
    assert.equal(paintFloorCells(doc, [{ x: 0, y: 1 }], { layerId, assetIds: ['stone'], makeId: unexpectedChoice }), true);
    assert.deepEqual(doc, before);
    doc.floors = [floorRow(doc, 'left', 'stone', 0, 0, .5, 1),
        floorRow(doc, 'right', 'stone', .5, 0, .5, 1, { paint: { color: null, opacity: 1 } })];
    const union = clone(doc);
    assert.equal(paintFloorCells(doc, [{ x: 0, y: 0 }], { layerId, assetIds: ['stone'], makeId: unexpectedChoice }), true);
    assert.deepEqual(doc, union);
    for (const extra of [{ rotation: 90 }, { paint: { color: null, opacity: .5 } }]) {
        const target = documentWithLayer(); target.floors = [floorRow(target, 'styled', 'stone', 0, 0, 1, 1, extra)];
        assert.equal(paintFloorCells(target, [{ x: 0, y: 0 }], { layerId, assetIds: ['stone'], makeId: () => 'plain' }), true);
        assert.deepEqual(target.floors, [floorRow(target, 'plain', 'stone', 0, 0)]);
    }
});

test('a same-material maximum grid repaint remains a no-op at the object limit', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id; doc.columns = doc.rows = 200; doc.cellSize = 16;
    doc.floors = [floorRow(doc, 'whole-map', 'stone', 0, 0, 200, 200)];
    doc.lights = Array.from({ length: 1999 }, (_, index) => ({ id: `lamp-${index}`, layerId, x: 1, y: 1 }));
    const before = clone(doc), cells = Array.from({ length: 40000 }, (_, index) => ({ x: index % 200, y: Math.floor(index / 200) }));
    assert.equal(paintFloorCells(doc, cells, { layerId, assetIds: ['stone'], makeId: unexpectedChoice }), true);
    assert.deepEqual(doc, before);
});

test('free repaint ignores a topmost union of eligible family variants without allocating, reordering or history', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.floors = [floorRow(doc, 'backing', 'wood', 0, 0, 4, 4), floorRow(doc, 'left', 'a', 0, 0, 2, 4),
        floorRow(doc, 'right', 'b', 2, 0, 2, 4, { paint: { color: null, opacity: 1 } })];
    const before = clone(doc), floors = doc.floors, choices = new Map(), steps = history(doc);
    assert.deepEqual(applyFloorContours(doc, [floorBox(.25, .25, 3.5, 3.5)],
        { layerId, assetIds: ['a', 'b'], choices, random: unexpectedChoice, makeId: unexpectedChoice }), { ok: true, changed: false, refs: [] });
    assert.equal(doc.floors, floors); assert.deepEqual(doc, before); assert.equal(choices.size, 0); assert.equal(steps.commit(doc), false);
    assert.equal(fillFloorShape(doc, { x: 3, y: 1 }, { layerId, assetIds: ['a', 'b'], choices, random: unexpectedChoice }).changed, false);
    assert.deepEqual(doc, before); assert.equal(choices.size, 0);
});

test('a partially different free stroke replaces its complete footprint and preserves other layers and vector holes outside it', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.layers.push({ id: 'elsewhere', name: 'Other layer', visible: true, locked: false });
    doc.floors = [floorRow(doc, 'backing', 'stone', 0, 0, 6, 6),
        floorRow(doc, 'holed', 'wood', 0, 0, 6, 6, { shape: { contours: [[[0, 0], [1, 0], [1, 1], [0, 1]]],
            cuts: [[[0, 0], [.5, 0], [.5, 1], [0, 1]]] } }),
        floorRow(doc, 'other', 'grass', 0, 0, 6, 6, { layerId: 'elsewhere' })];
    const before = clone(doc), left = [floorBox(.25, .25, 1, 1)];
    assert.equal(applyFloorContours(doc, left, { layerId, assetIds: ['stone'], makeId: unexpectedChoice }).changed, false);
    const result = applyFloorContours(doc, [floorBox(2, 2, 2, 2)], { layerId, assetIds: ['stone'], makeId: () => 'new' });
    assert.deepEqual(result, { ok: true, changed: true, refs: [{ kind: 'floors', id: 'new' }] });
    for (const point of [{ x: 2.5, y: 2.5 }, { x: 3.5, y: 3.5 }])
        assert.deepEqual(doc.floors.filter(item => item.layerId === layerId && floorContainsPoint(item, point)).map(item => item.id), ['new']);
    assert.deepEqual(doc.floors.find(item => item.id === 'other'), before.floors[2]);
    assert.equal(sampleFloor(doc, { x: 1, y: 1 }, { layerId }).id, 'backing');
    assert.equal(sampleFloor(doc, { x: 5, y: 5 }, { layerId }).id, 'holed');
    assert.deepEqual(doc.floors.find(item => item.id === 'holed').shape.cuts[0], before.floors[1].shape.cuts[0]);
});

test('mixed grid replacements reject exceeded budgets atomically without publishing cached choices', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.floors = [floorRow(doc, 'same', 'stone', 0, 0), floorRow(doc, 'room', 'wood', 1, 1, 3, 3)];
    const before = clone(doc), choices = new Map(), fragmentIds = new Map();
    assert.equal(paintFloorCells(doc, [{ x: 0, y: 0 }, { x: 2, y: 2 }], { layerId, assetIds: ['stone'], maxObjects: 4, choices, fragmentIds }), false);
    assert.deepEqual(doc, before); assert.equal(choices.size, 0); assert.equal(fragmentIds.size, 0);
});

test('new projects have one independently named empty layer while legacy default layers remain available for upgrades', () => {
    const doc = newDocument('Empty project'), loaded = normalizeDocument(doc);
    assert.equal(doc.name, 'Empty project'); assert.equal(doc.layers.length, 1);
    assert.deepEqual(doc.layers[0], { id: doc.layers[0].id, name: 'Layer 1', visible: true, locked: false });
    assert.match(doc.layers[0].id, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    const localized = newDocument('Another project', { layerName: 'Camada inicial' });
    assert.equal(localized.layers[0].name, 'Camada inicial'); assert.notEqual(localized.layers[0].id, doc.layers[0].id);
    for (const kind of ['floors', 'walls', 'doors', 'decorations', 'lights', 'particles', 'shaders']) assert.deepEqual(doc[kind], []);
    assert.deepEqual(loaded, doc); assert.notEqual(loaded.layers, doc.layers);
    loaded.layers[0].name = 'Renamed layer'; assert.equal(doc.layers[0].name, 'Layer 1');
    const deliberatelyEmpty = { ...doc, layers: [] };
    assert.deepEqual(normalizeDocument(deliberatelyEmpty), deliberatelyEmpty);
    assert.equal(documentEditingMode(doc), 'tiles'); assert.equal('editingMode' in doc, false);
    assert.deepEqual(defaultLayers(), [{ id: '00000000-0000-4000-8000-000000000001', name: 'Base', visible: true, locked: false }]);
    defaultLayers()[0].name = 'Edited fixture'; assert.equal(defaultLayers()[0].name, 'Base');
    for (const schemaVersion of [1, 2]) {
        const legacy = { ...doc, schemaVersion }; delete legacy.layers;
        assert.deepEqual(normalizeDocument(legacy).layers, defaultLayers());
        assert.equal('layers' in legacy, false);
    }
});

test('editing mode is optional for legacy documents and changes only the mode without touching geometry', () => {
    const doc = documentWithLayer(); doc.floors.push({ id: 'legacy', assetId: null, layerId: doc.layers[0].id, x: .125, y: .375, width: 4, height: 4, rotation: 90 });
    const before = clone(doc), loaded = normalizeDocument(doc);
    assert.equal(documentEditingMode(loaded), 'tiles'); assert.deepEqual(loaded, before);
    assert.equal(setEditingMode(doc, 'tiles'), false); assert.deepEqual(doc, before);
    assert.equal(setEditingMode(doc, 'paint'), true); assert.deepEqual(doc, { ...before, editingMode: 'paint' });
    assert.equal(setEditingMode(doc, 'paint'), false); assert.equal(setEditingMode(doc, 'bogus'), false);
    assert.equal(setEditingMode(doc, 'tiles'), true); assert.deepEqual(doc.floors, before.floors);
    assert.throws(() => normalizeDocument({ ...before, editingMode: 'bogus' }), /Invalid map editing mode/);
    assert.throws(() => normalizeDocument({ ...before, schemaVersion: 2, editingMode: 'paint' }), /Invalid map editing mode/);
});

test('floor paint profiles validate real colors and finite numeric opacity without mutating input', () => {
    const profile = { color: '#12AbCd', opacity: .5 };
    assert.deepEqual(normalizeFloorPaint(profile), { color: '#12abcd', opacity: .5 }); assert.notEqual(normalizeFloorPaint(profile), profile);
    assert.equal(profile.color, '#12AbCd');
    assert.deepEqual(normalizeFloorPaint(), { color: null, opacity: 1 });
    for (const value of [null, [], {}, { color: '#123', opacity: 1 }, { color: '#ffffff', opacity: true },
        { color: '#ffffff', opacity: Infinity }, { color: '#ffffff', opacity: -.1 }, { color: '#ffffff', opacity: 1.1 },
        { color: null, opacity: .5, hardness: .5 }]) assert.throws(() => normalizeFloorPaint(value), /Invalid floor paint/);
});

test('Painting strokes overlay intact backing and separate translucent strokes accumulate without sharing IDs', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    setEditingMode(doc, 'paint');
    const backing = { id: 'backing', layerId, assetId: 'wood', x: 0, y: 0, width: 8, height: 8, rotation: 90 };
    doc.floors.push(backing);
    const options = { layerId, assetIds: ['ignored-texture'], paint: { color: '#ff0000', opacity: .5 } };
    assert.equal(applyFloorContours(doc, paintBox, { ...options, makeId: () => 'first' }).changed, true);
    assert.equal(applyFloorContours(doc, paintBox, { ...options, makeId: () => 'second' }).changed, true);
    assert.equal(doc.floors.length, 3); assert.deepEqual(doc.floors[0], backing);
    assert.deepEqual(doc.floors.slice(1).map(item => [item.id, item.assetId, item.paint]),
        [['first', null, options.paint], ['second', null, options.paint]]);
    assert.notEqual(doc.floors[1].paint, doc.floors[2].paint);
    const before = clone(doc);
    assert.equal(applyFloorContours(doc, paintBox, { ...options, paint: { color: '#ff0000', opacity: 0 } }).changed, false);
    assert.deepEqual(doc, before);
    assert.equal(sampleFloor(doc, { x: 3, y: 3 }, { layerId }).id, 'second');
});

test('Painting preserves texture alpha accumulation while opaque solid color can be a true no-op', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id, options = { layerId, editingMode: 'paint', assetIds: ['transparent-png'], paint: { color: null, opacity: 1 } };
    applyFloorContours(doc, paintBox, { ...options, makeId: () => 'first' });
    assert.equal(applyFloorContours(doc, paintBox, { ...options, makeId: () => 'second' }).changed, true,
        'the model cannot assume a texture is opaque');
    const solid = { ...options, paint: { color: '#ff0000', opacity: 1 }, makeId: () => 'solid' };
    applyFloorContours(doc, paintBox, solid);
    assert.equal(applyFloorContours(doc, paintBox, solid).changed, false);
    assert.equal(doc.floors.length, 3);
});

test('Paint fill preserves identity and geometry, and switching to Tiles replaces the paint profile', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id, options = { layerId, editingMode: 'paint', paint: { color: '#ff0000', opacity: .5 } };
    applyFloorContours(doc, paintBox, { ...options, makeId: () => 'paint' });
    const before = clone(doc.floors[0]);
    assert.equal(fillFloorShape(doc, { x: 3, y: 3 }, { ...options, assetIds: ['wood'], paint: { color: null, opacity: .25 }, rotation: 90 }).changed, true);
    assert.deepEqual(doc.floors[0], { ...before, assetId: 'wood', rotation: 90, paint: { color: null, opacity: .25 } });
    assert.equal(fillFloorShape(doc, { x: 3, y: 3 }, { layerId, editingMode: 'tiles', assetIds: ['stone'] }).changed, true);
    const expected = { ...before, assetId: 'stone', rotation: 0 }; delete expected.paint;
    assert.deepEqual(doc.floors[0], expected);
});

test('Tiles repaint cuts colored strokes and retains paint metadata only on the outside remainder', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    applyFloorContours(doc, paintBox, { layerId, editingMode: 'paint', paint: { color: '#00ff00', opacity: .4 }, makeId: () => 'paint' });
    const before = clone(doc.floors[0]);
    assert.equal(paintFloorCells(doc, [{ x: 3, y: 3 }], { layerId, assetIds: [null], makeId: () => 'tile' }), true);
    assert.deepEqual(doc.floors[0].paint, before.paint); assert.deepEqual(doc.floors[0].shape.contours, before.shape.contours);
    assert.equal(doc.floors.at(-1).paint, undefined);
    assert.equal(sampleFloor(doc, { x: 3.5, y: 3.5 }, { layerId }).id, 'tile');
    assert.equal(sampleFloor(doc, { x: 2.5, y: 2.5 }, { layerId }).paint.color, '#00ff00');
});

test('Paint source limits fail atomically and mode/style/erase remain independent undo operations', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id, steps = history(doc);
    setEditingMode(doc, 'paint'); steps.commit(doc);
    const options = { layerId, paint: { color: '#123456', opacity: .5 }, makeId: () => 'paint' };
    applyFloorContours(doc, paintBox, options); steps.commit(doc);
    const painted = clone(doc), choices = new Map();
    assert.equal(applyFloorContours(doc, paintBox, { ...options, maxObjects: 1, choices }).ok, false);
    assert.deepEqual(doc, painted); assert.equal(choices.size, 0);
    assert.equal(applyFloorContours(doc, paintBox, { ...options, paint: { color: '#123456', opacity: NaN } }).error, 'Invalid floor paint.');
    assert.deepEqual(doc, painted);
    applyFloorContours(doc, paintBox, { ...options, operation: 'erase' }); steps.commit(doc);
    assert.equal(doc.floors.length, 0);
    assert.deepEqual(steps.undo(), painted);
    assert.deepEqual(steps.undo(), { ...documentWithLayer(), editingMode: 'paint' });
    assert.equal(documentEditingMode(steps.undo()), 'tiles');
});

test('grid bucket material signatures distinguish paint colors and opacity and skip invisible floors', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.columns = 4; doc.rows = 1;
    doc.floors = [
        { id: 'red', x: 0, paint: { color: '#ff0000', opacity: .5 } },
        { id: 'blue', x: 1, paint: { color: '#0000ff', opacity: .5 } },
        { id: 'solid', x: 2, paint: { color: '#ff0000', opacity: 1 } },
        { id: 'invisible', x: 3, paint: { color: '#ff0000', opacity: 0 } },
    ].map(item => ({ ...item, layerId, y: 0, width: 1, height: 1, assetId: null, rotation: 0 }));
    for (const x of [0, 1, 2]) assert.deepEqual(floodFloorCells(doc, { x: x + .5, y: .5 }, { layerId }), [{ x, y: 0 }]);
    assert.equal(sampleFloor(doc, { x: 3.5, y: .5 }, { layerId }), null);
});
test('snapped wall strokes follow whole-cell boundaries in either direction', () => {
    const doc = documentWithLayer();
    assert.deepEqual(snapWallSegment(doc, { x: 2.1, y: 2.4 }, { x: 8.8, y: 2.7 }),
        { x1: 2, y1: 2, x2: 9, y2: 2 });
    assert.deepEqual(snapWallSegment(doc, { x: 3.4, y: 1.8 }, { x: 3.7, y: 7.2 }),
        { x1: 3, y1: 2, x2: 3, y2: 7 });
    assert.deepEqual(snapWallSegment(doc, { x: 8.8, y: 2.4 }, { x: 2.1, y: 2.7 }),
        { x1: 9, y1: 2, x2: 2, y2: 2 });
    assert.deepEqual(snapWallSegment(doc, { x: 3.4, y: 7.2 }, { x: 3.7, y: 1.8 }),
        { x1: 3, y1: 7, x2: 3, y2: 2 });
});
test('snapped wall strokes choose one grid axis and clamp endpoints at map edges', () => {
    const doc = documentWithLayer(); doc.columns = 8; doc.rows = 6;
    assert.deepEqual(snapWallSegment(doc, { x: 2, y: 2 }, { x: 4, y: 4 }),
        { x1: 2, y1: 2, x2: 4, y2: 2 });
    assert.deepEqual(snapWallSegment(doc, { x: -.4, y: 2.4 }, { x: 14.9, y: 3.1 }),
        { x1: 0, y1: 2, x2: 8, y2: 2 });
    assert.deepEqual(snapWallSegment(doc, { x: 7.7, y: -1.4 }, { x: 7.4, y: 11.8 }),
        { x1: 8, y1: 0, x2: 8, y2: 6 });
    assert.deepEqual(snapWallSegment(doc, { x: 2.2, y: 2.2 }, { x: 2.3, y: 2.4 }),
        { x1: 2, y1: 2, x2: 2, y2: 2 });
});
test('walls drawn without snapping retain diagonal and fractional geometry within map bounds', () => {
    const doc = documentWithLayer();
    assert.deepEqual(snapWallSegment(doc, { x: 2.123456, y: 3.654321 }, { x: 8.765432, y: 7.345678 }, { snap: false }),
        { x1: 2.123, y1: 3.654, x2: 8.765, y2: 7.346 });
    assert.deepEqual(snapWallSegment(doc, { x: -1.2, y: 3.125 }, { x: 50, y: 40 }, { snap: false }),
        { x1: 0, y1: 3.125, x2: 40, y2: 30 });
});
test('snapping a new stroke never changes saved fractional walls or converted doors', () => {
    const doc = documentWithLayer(); doc.schemaVersion = 1;
    doc.walls.push({ ...wall(), x1: 1.1, y1: 1.1, x2: 6.3, y2: 8.9 });
    doc.doors.push({ id: 'door', wallId: 'wall', assetId: null, offset: 2, width: 3, state: 'closed' });
    const loaded = normalizeDocument(doc), saved = clone(loaded), start = { x: 3.2, y: 3.2 }, end = { x: 5.7, y: 3.1 };
    assert.deepEqual(snapWallSegment(loaded, start, end), { x1: 3, y1: 3, x2: 6, y2: 3 });
    assert.deepEqual(loaded, saved);
    assert.deepEqual(start, { x: 3.2, y: 3.2 }); assert.deepEqual(end, { x: 5.7, y: 3.1 });
    assert.equal(wallSegments(loaded, loaded.walls[0]).length, 2);
});
test('an independently drawn door removes only the collinear solid span', () => {
    const doc = documentWithLayer(); doc.walls.push(wall()); doc.doors.push(door());
    assert.deepEqual(wallSegments(doc, doc.walls[0]), [
        { x1: 2, y1: 2, x2: 5, y2: 2 }, { x1: 7, y1: 2, x2: 10, y2: 2 },
    ]);
    assert.deepEqual(doorSegment(doc, doc.doors[0]), { x1: 5, y1: 2, x2: 7, y2: 2, angle: 0, thickness: .18 });
    doc.doors[0].state = 'open';
    assert.equal(wallSegments(doc, doc.walls[0]).length, 2);
    removeObject(doc, 'doors', 'door');
    assert.deepEqual(wallSegments(doc, doc.walls[0]), [{ x1: 2, y1: 2, x2: 10, y2: 2 }]);
});
test('a door can be drawn in empty space or connect two separate wall endpoints', () => {
    const doc = documentWithLayer(); doc.doors.push(door());
    assert.equal(doorFits(doc, doc.doors[0]), true);
    doc.walls.push({ ...wall(), x2: 5 }, { ...wall(), id: 'right', x1: 7 });
    assert.deepEqual(wallSegments(doc, doc.walls[0]), [{ x1: 2, y1: 2, x2: 5, y2: 2 }]);
    assert.deepEqual(wallSegments(doc, doc.walls[1]), [{ x1: 7, y1: 2, x2: 10, y2: 2 }]);
});
test('reversed diagonal doors clip across multiple wall segments', () => {
    const doc = documentWithLayer();
    doc.walls.push({ ...wall(), x1: 0, y1: 0, x2: 3, y2: 4 }, { ...wall(), id: 'second', x1: 6, y1: 8, x2: 3, y2: 4 });
    doc.doors.push({ ...door(), x1: 4.2, y1: 5.6, x2: 1.2, y2: 1.6 });
    const first = wallSegments(doc, doc.walls[0])[0], second = wallSegments(doc, doc.walls[1])[0];
    assert.equal(first.x1, 0); assert.equal(first.y1, 0);
    assert.ok(Math.abs(first.x2 - 1.2) < 1e-12); assert.ok(Math.abs(first.y2 - 1.6) < 1e-12);
    assert.equal(second.x1, 6); assert.equal(second.y1, 8);
    assert.ok(Math.abs(second.x2 - 4.2) < 1e-12); assert.ok(Math.abs(second.y2 - 5.6) < 1e-12);
});
test('crossing and nearby parallel doors do not cut unrelated walls', () => {
    const doc = documentWithLayer(); doc.walls.push(wall());
    doc.doors.push({ ...door(), x1: 6, y1: 1, x2: 6, y2: 3 });
    doc.doors.push({ ...door(), id: 'parallel', y1: 2.001, y2: 2.001 });
    assert.deepEqual(wallSegments(doc, doc.walls[0]), [{ x1: 2, y1: 2, x2: 10, y2: 2 }]);
});
test('touching doors are valid but positive collinear overlap is rejected', () => {
    const doc = documentWithLayer(); doc.doors.push(door());
    assert.equal(doorFits(doc, { ...door(), id: 'second', x1: 7, x2: 9 }), true);
    assert.equal(doorFits(doc, { ...door(), id: 'second', x1: 8, x2: 6 }), false);
    assert.equal(doorFits(doc, { ...door(), id: 'crossing', x1: 6, y1: 1, x2: 6, y2: 3 }), true);
    assert.equal(doorFits(doc, { ...door(), id: 'parallel', y1: 2.001, y2: 2.001 }), true);
});
test('door validity enforces map bounds, length and thickness independently of walls', () => {
    const doc = documentWithLayer();
    for (const candidate of [
        { ...door(), x2: 5.1 }, { ...door(), x2: 26 }, { ...door(), x1: -1 },
        { ...door(), y2: 31 }, { ...door(), thickness: .01 }, { ...door(), x2: NaN },
    ]) assert.equal(doorFits(doc, candidate), false);
    doc.doors.push({ ...door(), x2: 41 });
    assert.equal(fitsBounds(doc), false);
});
test('moving a wall does not move its door; moving the door clamps the entire segment', () => {
    const doc = documentWithLayer(); doc.columns = 12; doc.rows = 12;
    doc.walls.push(wall()); doc.doors.push(door());
    translateObject(doc, 'walls', 'wall', 50, -50);
    assert.deepEqual([doc.walls[0].x1, doc.walls[0].x2, doc.walls[0].y1, doc.walls[0].y2], [4, 12, 0, 0]);
    assert.deepEqual(doc.doors[0], door());
    translateObject(doc, 'doors', 'door', -50, 50);
    assert.deepEqual([doc.doors[0].x1, doc.doors[0].x2, doc.doors[0].y1, doc.doors[0].y2], [0, 2, 12, 12]);
    assert.equal(fitsBounds(doc), true); assert.equal(doorFits(doc, doc.doors[0]), true);
});
test('erasing a wall preserves the independent door and remains undoable', () => {
    const doc = documentWithLayer(); doc.walls.push(wall()); doc.doors.push(door());
    const stack = history(doc); removeObject(doc, 'walls', 'wall'); stack.commit(doc);
    assert.equal(doc.walls.length, 0); assert.deepEqual(doc.doors[0], door());
    const restored = stack.undo(); assert.equal(restored.walls.length, 1); assert.equal(restored.doors.length, 1);
    assert.equal(stack.redo().doors.length, 1);
});
test('legacy drafts convert attached doors to independent endpoints without changing the source', () => {
    const doc = documentWithLayer(); doc.schemaVersion = 1;
    doc.walls.push({ ...wall(), x1: 0, y1: 0, x2: 6, y2: 8 });
    doc.doors.push({ id: 'legacy-door', wallId: 'wall', assetId: 'appearance', offset: 2, width: 3, state: 'locked' });
    const saved = clone(doc), converted = normalizeDocument(doc);
    assert.deepEqual(doc, saved); assert.equal(converted.schemaVersion, 3);
    assert.deepEqual(converted.doors[0], { id: 'legacy-door', assetId: 'appearance', x1: 1.2, y1: 1.6, x2: 3, y2: 4, thickness: .18, state: 'locked', layerId: defaultLayers()[0].id });
    converted.walls.length = 0;
    assert.equal(doorFits(converted, converted.doors[0]), true);
    assert.deepEqual(normalizeDocument(converted), converted);
});
test('a broken legacy door is reported rather than silently removed', () => {
    const doc = documentWithLayer(); doc.schemaVersion = 1;
    doc.doors.push({ id: 'legacy-door', wallId: 'missing', offset: 0, width: 1 });
    assert.throws(() => normalizeDocument(doc), /saved door geometry is invalid/);
    assert.equal(doc.doors.length, 1);
});
test('selecting and translating a converted diagonal door preserves its exact line', () => {
    const legacy = documentWithLayer(); legacy.schemaVersion = 1;
    legacy.walls.push({ ...wall(), x1: 1.1, y1: 1.1, x2: 6.3, y2: 8.9 });
    legacy.doors.push({ id: 'door', wallId: 'wall', assetId: null, offset: 2, width: 3, state: 'closed' });
    const doc = normalizeDocument(legacy), before = clone(doc.doors[0]), spans = wallSegments(doc, doc.walls[0]);
    translateObject(doc, 'doors', 'door', 0, 0);
    assert.deepEqual(doc.doors[0], before);
    translateObject(doc, 'walls', 'wall', .5, 1.5);
    translateObject(doc, 'doors', 'door', .5, 1.5);
    const moved = wallSegments(doc, doc.walls[0]);
    assert.equal(moved.length, 2); assert.equal(doorFits(doc, doc.doors[0]), true);
    for (let index = 0; index < moved.length; index++) for (const key of ['x1', 'y1', 'x2', 'y2']) {
        assert.ok(Math.abs(moved[index][key] - spans[index][key] - (key.startsWith('x') ? .5 : 1.5)) < 1e-12);
    }
});
test('a legacy diagonal door at the minimum length survives floating point conversion', () => {
    const doc = documentWithLayer(); doc.schemaVersion = 1;
    doc.walls.push({ ...wall(), x1: 1.1, y1: 1.1, x2: 6.3, y2: 8.9 });
    doc.doors.push({ id: 'door', wallId: 'wall', assetId: null, offset: 2, width: .25, state: 'closed' });
    const converted = normalizeDocument(doc);
    assert.equal(doorFits(converted, converted.doors[0]), true);
});
test('nearest wall ignores zero-length segments and respects brush tolerance', () => {
    const doc = documentWithLayer(); doc.walls.push({ ...wall(), id: 'zero', x2: 2, y2: 2 }, wall());
    assert.equal(nearestWall(doc, { x: 5, y: 2.1 }, .2).wall.id, 'wall');
    assert.equal(nearestWall(doc, { x: 5, y: 3 }, .2), undefined);
});
test('history retains independent snapshots and abandons the future after a new edit', () => {
    const doc = documentWithLayer(), stack = history(doc, 2);
    doc.name = 'One'; stack.commit(doc); doc.name = 'Two'; stack.commit(doc); doc.name = 'Three'; stack.commit(doc);
    assert.equal(stack.undo().name, 'Two'); assert.equal(stack.undo().name, 'One'); assert.equal(stack.canUndo, false);
    doc.name = 'Alternate'; stack.commit(doc); assert.equal(stack.canRedo, false);
    doc.name = 'Uncommitted'; assert.equal(stack.undo().name, 'One');
});

test('permanent asset removal rebases undo and redo while keeping unrelated draft edits', () => {
    const doc = documentWithLayer('Room');
    doc.floors.push({ id: 'floor', assetId: 'removed', x: 1, y: 2, width: 1, height: 1 });
    const stack = history(doc);
    doc.floors[0].x = 2; stack.commit(doc);
    doc.assets.push({ assetId: 'removed', role: 'floor' }); stack.commit(doc);
    doc.name = 'Pending room name'; stack.commit(doc);
    stack.undo();
    const before = clone(doc), removed = value => detachDocumentAsset(value, 'removed', []);
    const current = stack.rebase(removed);
    assert.equal(current.name, 'Room');
    assert.equal(current.floors[0].x, 2);
    assert.equal(current.floors[0].assetId, null);
    assert.deepEqual(current.assets, []);
    assert.deepEqual(doc, before);
    // The classification-only edit became equal to the preceding movement.
    const earlier = stack.undo();
    assert.equal(earlier.floors[0].x, 1);
    assert.equal(earlier.floors[0].assetId, null);
    assert.equal(stack.canUndo, false);
    const movement = stack.redo(), pending = stack.redo();
    assert.equal(movement.floors[0].x, 2);
    assert.equal(movement.name, 'Room');
    assert.equal(pending.name, 'Pending room name');
    assert.equal(pending.floors[0].assetId, null);
    assert.deepEqual(pending.assets, []);
    assert.equal(stack.canRedo, false);
    current.floors[0].x = 100;
    assert.equal(stack.undo().floors[0].x, 2);
});

test('rebasing removes history steps containing only deleted asset metadata', () => {
    const doc = documentWithLayer();
    doc.assets.push({ assetId: 'removed', role: 'floor' });
    const stack = history(doc);
    doc.assets[0].name = 'First label'; stack.commit(doc);
    doc.assets[0].name = 'Another label'; stack.commit(doc);
    stack.undo();
    assert.equal(stack.canUndo, true);
    assert.equal(stack.canRedo, true);
    const result = stack.rebase(value => detachDocumentAsset(value, 'removed', []));
    assert.deepEqual(result.assets, []);
    assert.equal(stack.canUndo, false);
    assert.equal(stack.canRedo, false);
});

test('a failed history rebase leaves every prior snapshot available', () => {
    const doc = documentWithLayer('Initial'), stack = history(doc);
    doc.name = 'First change'; stack.commit(doc);
    doc.name = 'Second change'; stack.commit(doc);
    let visited = 0;
    assert.throws(() => stack.rebase(value => {
        value.name = 'Modified transform input';
        if (++visited === 2) throw new Error('Cleanup failed');
        return value;
    }), /Cleanup failed/);
    assert.equal(stack.undo().name, 'First change');
    assert.equal(stack.redo().name, 'Second change');
});
test('version two upgrades to ordered layers without rounding endpoints or losing asset metadata', () => {
    const doc = documentWithLayer(); doc.schemaVersion = 2;
    delete doc.layers; delete doc.decorations; delete doc.lights;
    doc.walls.push({ ...wall(), x1: 1.123456789 }); doc.doors.push(door());
    doc.assets.push({ assetId: 'wood', role: 'door', name: 'Oak door', collection: 'Tavern' });
    const source = clone(doc), upgraded = normalizeDocument(doc);
    assert.deepEqual(doc, source); assert.equal(upgraded.schemaVersion, 3);
    assert.equal(upgraded.walls[0].x1, 1.123456789);
    assert.equal(upgraded.doors[0].layerId, upgraded.layers[0].id);
    assert.deepEqual(upgraded.assets, source.assets);
    assert.deepEqual(upgraded.decorations, []); assert.deepEqual(upgraded.lights, []);
    assert.notEqual(defaultLayers(), defaultLayers());
    assert.throws(() => normalizeDocument({ schemaVersion: 4 }), /Unsupported/);
});
test('group translation clamps one common offset and keeps relative geometry intact', () => {
    const doc = documentWithLayer(); doc.columns = 12; doc.rows = 12;
    doc.walls.push(wall()); doc.doors.push(door());
    doc.floors.push({ id: 'floor', x: 1, y: 3, width: 3, height: 4, rotation: 0 });
    const refs = [{ kind: 'walls', id: 'wall' }, { kind: 'doors', id: 'door' }, { kind: 'floors', id: 'floor' }];
    const before = clone(doc);
    assert.deepEqual(selectionBounds(doc, refs), { x: 1, y: 2, width: 9, height: 5 });
    assert.equal(translateSelection(doc, refs, -50, 50), true);
    for (const kind of ['walls', 'doors']) for (const key of ['x1', 'x2', 'y1', 'y2']) {
        assert.equal(doc[kind][0][key] - before[kind][0][key], key.startsWith('x') ? -1 : 5);
    }
    assert.equal(doc.floors[0].x, 0); assert.equal(doc.floors[0].y, 8);
    assert.equal(wallSegments(doc, doc.walls[0]).length, 2);
    assert.equal(fitsBounds(doc), true);
});
test('snapped group translation keeps whole-cell offsets at every fractional map edge', () => {
    for (const { x, y, dx, dy, expectedX, expectedY } of [
        { x: 17.6, y: 10, dx: 50, dy: 0, expectedX: 1, expectedY: 0 },
        { x: 1.4, y: 10, dx: -50, dy: 0, expectedX: -1, expectedY: 0 },
        { x: 10, y: 1.4, dx: 0, dy: -50, expectedX: 0, expectedY: -1 },
        { x: 10, y: 17.6, dx: 0, dy: 50, expectedX: 0, expectedY: 1 },
    ]) {
        const doc = documentWithLayer(); doc.columns = 20; doc.rows = 20;
        doc.walls.push({ ...wall(), x1: 7, y1: 7, x2: 10, y2: 7 });
        doc.decorations.push({ id: 'table', x, y, width: 1, height: 1, rotation: 0 });
        const refs = [{ kind: 'walls', id: 'wall' }, { kind: 'decorations', id: 'table' }], before = clone(doc);
        assert.equal(translateSelection(doc, refs, dx, dy, { snapStep: 1 }), true);
        for (const key of ['x1', 'x2', 'y1', 'y2']) {
            assert.equal(doc.walls[0][key] - before.walls[0][key], key.startsWith('x') ? expectedX : expectedY);
            assert.equal(Number.isInteger(doc.walls[0][key]), true);
        }
        assert.ok(Math.abs(doc.decorations[0].x - x - expectedX) < 1e-12);
        assert.ok(Math.abs(doc.decorations[0].y - y - expectedY) < 1e-12);
        assert.equal(fitsBounds(doc), true);
    }
});
test('snapped groups do not move when less than one full cell remains toward an edge', () => {
    for (const { x, y, dx, dy } of [
        { x: 18.6, y: 10, dx: 1, dy: 0 }, { x: .4, y: 10, dx: -1, dy: 0 },
        { x: 10, y: .4, dx: 0, dy: -1 }, { x: 10, y: 18.6, dx: 0, dy: 1 },
    ]) {
        const doc = documentWithLayer(); doc.columns = 20; doc.rows = 20;
        doc.walls.push({ ...wall(), x1: 7, y1: 7, x2: 10, y2: 7 });
        doc.decorations.push({ id: 'table', x, y, width: 1, height: 1, rotation: 0 });
        const refs = [{ kind: 'walls', id: 'wall' }, { kind: 'decorations', id: 'table' }], before = clone(doc);
        assert.equal(translateSelection(doc, refs, dx, dy, { snapStep: 1 }), false);
        assert.deepEqual(doc, before);
    }
});
test('snapped movement preserves legacy fractions and relative positions beside rotated decoration bounds', () => {
    const doc = documentWithLayer(); doc.columns = 20; doc.rows = 20;
    doc.walls.push({ ...wall(), x1: 4.125, y1: 4.375, x2: 7.625, y2: 8.875 });
    doc.decorations.push({ id: 'table', x: 15, y: 9, width: 4, height: 2, rotation: 45 });
    doc.lights.push({ id: 'unselected', x: 1.25, y: 2.25 });
    const refs = [{ kind: 'walls', id: 'wall' }, { kind: 'decorations', id: 'table' }], before = clone(doc);
    assert.equal(translateSelection(doc, refs, 100, 100, { snapStep: 1 }), true);
    assert.deepEqual(doc.walls[0], { ...before.walls[0], y1: 11.375, y2: 15.875 });
    assert.deepEqual(doc.decorations[0], { ...before.decorations[0], y: 16 });
    assert.deepEqual(doc.lights, before.lights);
    assert.equal(fitsBounds(doc), true);
});
test('snapped wall and door groups still reject collisions atomically and retain their openings after a valid move', () => {
    const doc = documentWithLayer(); doc.columns = 12; doc.rows = 12;
    doc.walls.push(wall()); doc.doors.push(door(), { ...door(), id: 'occupied', y1: 4, y2: 4 });
    doc.decorations.push({ id: 'table', x: 10.6, y: 2, width: 1, height: 1, rotation: 0 });
    const refs = [{ kind: 'walls', id: 'wall' }, { kind: 'doors', id: 'door' }, { kind: 'decorations', id: 'table' }];
    const before = clone(doc);
    assert.equal(translateSelection(doc, refs, 1, 2, { snapStep: 1 }), false);
    assert.deepEqual(doc, before);
    assert.equal(translateSelection(doc, refs, 1, 1, { snapStep: 1 }), true);
    assert.equal(doc.walls[0].x1, 2); assert.equal(doc.walls[0].y1, 3);
    assert.equal(doc.doors[0].x1, 5); assert.equal(doc.doors[0].y1, 3);
    assert.deepEqual(doc.doors[1], before.doors[1]);
    assert.equal(wallSegments(doc, doc.walls[0]).length, 2);
    assert.equal(doorFits(doc, doc.doors[0]), true);
});
test('free group movement retains fractional edge clamping when snapping is omitted or disabled', () => {
    const source = documentWithLayer(); source.columns = 20;
    source.walls.push({ ...wall(), x1: 10, x2: 12 });
    source.decorations.push({ id: 'table', x: 18.6, y: 2, width: 1, height: 1, rotation: 0 });
    const refs = [{ kind: 'walls', id: 'wall' }, { kind: 'decorations', id: 'table' }];
    for (const options of [undefined, { snapStep: 0 }]) {
        const doc = clone(source);
        assert.equal(translateSelection(doc, refs, 1, .25, options), true);
        assert.ok(Math.abs(doc.walls[0].x1 - 10.4) < 1e-12);
        assert.equal(doc.walls[0].y1, 2.25);
        assert.equal(doc.decorations[0].x, 19); assert.equal(doc.decorations[0].y, 2.25);
    }
});
test('a failed group transform leaves every selected and unselected object untouched', () => {
    const doc = documentWithLayer(); doc.doors.push(door(), { ...door(), id: 'occupied', y1: 4, y2: 4 });
    doc.floors.push({ id: 'floor', x: 2, y: 2, width: 1, height: 1 });
    const refs = [{ kind: 'doors', id: 'door' }, { kind: 'floors', id: 'floor' }], before = clone(doc);
    assert.equal(translateSelection(doc, refs, 0, 2), false); assert.deepEqual(doc, before);
    assert.equal(translateSelection(doc, refs, NaN, 0), false); assert.deepEqual(doc, before);
    assert.equal(rotateSelection(doc, [{ kind: 'doors', id: 'missing' }]), false); assert.deepEqual(doc, before);
    doc.layers[0].locked = true;
    assert.equal(translateSelection(doc, refs, 1, 1), false);
    assert.equal(rotateSelection(doc, refs), false); assert.deepEqual(duplicateSelection(doc, refs), []);
});
test('quarter turns rotate a whole room including independent doors and floor orientation', () => {
    const doc = documentWithLayer(); doc.columns = 20; doc.rows = 20;
    doc.floors.push({ id: 'floor', x: 4, y: 4, width: 8, height: 6, rotation: 0 });
    doc.walls.push({ ...wall(), x1: 4, y1: 4, x2: 12, y2: 4 });
    doc.doors.push({ ...door(), x1: 7, y1: 4, x2: 9, y2: 4 });
    const refs = [{ kind: 'floors', id: 'floor' }, { kind: 'walls', id: 'wall' }, { kind: 'doors', id: 'door' }];
    const before = clone(doc);
    assert.equal(rotateSelection(doc, refs), true);
    assert.deepEqual([doc.floors[0].x, doc.floors[0].y, doc.floors[0].width, doc.floors[0].height, doc.floors[0].rotation], [5, 3, 6, 8, 90]);
    assert.deepEqual([doc.walls[0].x1, doc.walls[0].y1, doc.walls[0].x2, doc.walls[0].y2], [11, 3, 11, 11]);
    assert.equal(wallSegments(doc, doc.walls[0]).length, 2);
    for (let turn = 0; turn < 3; turn++) assert.equal(rotateSelection(doc, refs), true);
    assert.deepEqual(doc, before);
});
test('rotated decorations clamp by rotated corners; invalid rotations are atomic', () => {
    const doc = documentWithLayer(); doc.columns = 10; doc.rows = 10;
    doc.decorations.push({ id: 'table', x: 3, y: 3, width: 4, height: 2, rotation: 45 });
    const refs = [{ kind: 'decorations', id: 'table' }];
    assert.ok(Math.abs(selectionBounds(doc, refs).width - Math.sqrt(18)) < 1e-12);
    assert.equal(translateSelection(doc, refs, 100, 100), true); assert.equal(fitsBounds(doc), true);
    doc.decorations[0].rotation = 0;
    assert.equal(translateSelection(doc, refs, 100, 100), true);
    const before = clone(doc);
    assert.equal(rotateSelection(doc, refs, 45), false); assert.deepEqual(doc, before);
    doc.floors.push({ id: 'floor', x: 0, y: 0, width: 1, height: 1 });
    const snapshot = clone(doc);
    assert.equal(rotateSelection(doc, [{ kind: 'floors', id: 'floor' }], 45), false); assert.deepEqual(doc, snapshot);
});
test('duplication allocates fresh IDs and remains one undo operation', () => {
    const doc = documentWithLayer(); doc.walls.push(wall()); doc.doors.push(door());
    const refs = [{ kind: 'walls', id: 'wall' }, { kind: 'doors', id: 'door' }], stack = history(doc);
    const copies = duplicateSelection(doc, refs, 2, 3);
    assert.equal(copies.length, 2); assert.equal(new Set(copies.map(ref => ref.id)).size, 2);
    assert.ok(copies.every(ref => ref.id !== 'wall' && ref.id !== 'door'));
    assert.deepEqual([doc.doors[1].x1, doc.doors[1].y1, doc.doors[1].x2, doc.doors[1].y2], [7, 5, 9, 5]);
    assert.equal(wallSegments(doc, doc.walls[1]).length, 2);
    stack.commit(doc); assert.equal(stack.undo().doors.length, 1); assert.equal(stack.redo().doors.length, 2);
    const before = clone(doc);
    assert.deepEqual(duplicateSelection(doc, refs, 0, 0), []); assert.deepEqual(doc, before);
});

function doorBlueprint() {
    return { version: 1, kind: 'door', states: { closed: { appearance: 'inherit' },
        open: { appearance: 'hidden' }, locked: { appearance: 'inherit' } },
    graphs: { 'signal:FixtureEnterOpen': { nodes: [
        { id: 'event', type: 'event', event: 'signal:FixtureEnterOpen', x: 0, y: 0 },
        { id: 'light_a', type: 'light', targetId: 'lamp', enabled: true, x: 250, y: 0 },
        { id: 'light_b', type: 'light', targetId: 'external', enabled: false, x: 500, y: 0 },
    ], edges: [{ from: 'event', output: 'next', to: 'light_a' },
        { from: 'light_a', output: 'next', to: 'light_b' }] } } };
}

test('duplicating an intelligent door deep-copies its graph and retains unselected light targets', () => {
    const doc = documentWithLayer();
    doc.doors.push({ ...door(), blueprint: doorBlueprint() });
    doc.lights.push({ id: 'lamp', x: 12, y: 6 }, { id: 'external', x: 14, y: 6 });
    const original = clone(doc.doors[0]);
    const copies = duplicateSelection(doc, [{ kind: 'doors', id: 'door' }], 0, 3);
    assert.equal(copies.length, 1);
    const copy = doc.doors[1];
    assert.deepEqual(copy.blueprint, original.blueprint);
    copy.blueprint.states.open.appearance = 'inherit';
    copy.blueprint.graphs['signal:FixtureEnterOpen'].nodes[1].enabled = false;
    assert.deepEqual(doc.doors[0], original, 'later copy edits cannot change the original graph');
    assert.deepEqual(copy.blueprint.graphs['signal:FixtureEnterOpen'].nodes.slice(1).map(node => node.targetId), ['lamp', 'external']);
});

test('duplicating a door and its light binds the copied graph to only the copied light', () => {
    const doc = documentWithLayer();
    doc.doors.push({ ...door(), blueprint: doorBlueprint() });
    doc.lights.push({ id: 'lamp', x: 12, y: 6 }, { id: 'external', x: 14, y: 6 });
    const before = clone(doc);
    // Door precedes its light to verify the complete selection is mapped first.
    const copies = duplicateSelection(doc, [{ kind: 'doors', id: 'door' }, { kind: 'lights', id: 'lamp' }], 0, 3);
    const lightCopy = copies.find(ref => ref.kind === 'lights');
    assert.equal(copies.length, 2);
    assert.deepEqual(doc.doors[1].blueprint.graphs['signal:FixtureEnterOpen'].nodes.slice(1).map(node => node.targetId),
        [lightCopy.id, 'external']);
    assert.deepEqual(doc.doors[0], before.doors[0]);
    assert.deepEqual(doc.lights.slice(0, 2), before.lights);
});

test('deleting a referenced light bridges adjacent graph actions and remains undoable', () => {
    const doc = documentWithLayer(), blueprint = doorBlueprint();
    const graph = blueprint.graphs['signal:FixtureEnterOpen'];
    graph.nodes.push({ id: 'condition', type: 'condition', state: 'open', x: 0, y: 250 },
        { id: 'second', type: 'light', targetId: 'lamp', enabled: false, x: 250, y: 250 });
    graph.edges = [{ from: 'event', output: 'next', to: 'condition' },
        { from: 'condition', output: 'true', to: 'light_a' },
        { from: 'condition', output: 'false', to: 'light_b' },
        { from: 'light_a', output: 'next', to: 'second' },
        { from: 'second', output: 'next', to: 'light_b' }];
    doc.doors.push({ ...door(), blueprint }, { ...door(), id: 'legacy', y1: 5, y2: 5 });
    doc.lights.push({ id: 'lamp', x: 12, y: 6 }, { id: 'external', x: 14, y: 6 });
    const before = clone(doc), stack = history(doc);
    removeObject(doc, 'lights', 'lamp');
    const cleaned = doc.doors[0].blueprint.graphs['signal:FixtureEnterOpen'];
    assert.deepEqual(doc.lights.map(item => item.id), ['external']);
    assert.equal(cleaned.nodes.some(node => node.targetId === 'lamp'), false);
    assert.deepEqual(cleaned.edges, [{ from: 'event', output: 'next', to: 'condition' },
        { from: 'condition', output: 'false', to: 'light_b' },
        { from: 'condition', output: 'true', to: 'light_b' }]);
    assert.deepEqual(doc.doors[1], before.doors[1]);
    stack.commit(doc);
    assert.deepEqual(stack.undo(), before, 'one undo restores the light and original actions');
    assert.deepEqual(stack.redo(), doc);
});

test('deleting a terminal light action removes incoming branches without dangling graph edges', () => {
    const doc = documentWithLayer();
    doc.doors.push({ ...door(), blueprint: doorBlueprint() });
    doc.lights.push({ id: 'lamp', x: 12, y: 6 }, { id: 'external', x: 14, y: 6 });
    removeObject(doc, 'lights', 'external');
    const graph = doc.doors[0].blueprint.graphs['signal:FixtureEnterOpen'];
    assert.deepEqual(graph.nodes.map(node => node.id), ['event', 'light_a']);
    assert.deepEqual(graph.edges, [{ from: 'event', output: 'next', to: 'light_a' }]);
});

test('version two light deletion preserves branch order, typed edges and reconvergence', () => {
    const doc = documentWithLayer(), blueprint = upgradeBlueprint(doorBlueprint());
    const graph = blueprint.graphs['signal:FixtureEnterOpen'];
    graph.nodes.push({ id: 'condition', type: 'condition', state: 'open', x: 0, y: 250 },
        { id: 'adjacent', type: 'light', targetId: 'lamp', enabled: false, x: 250, y: 250 },
        { id: 'sound_a', type: 'sound', trackId: 'creak', volume: .5, x: 500, y: 250 },
        { id: 'sound_b', type: 'sound', trackId: 'echo', volume: .5, x: 750, y: 250 },
        { id: 'shared', type: 'state', targetState: 'closed', x: 1000, y: 250 });
    graph.edges = [
        ['event', 'next', 'condition'], ['condition', 'true', 'light_a'], ['condition', 'true', 'sound_a'],
        ['condition', 'false', 'sound_b'], ['event', 'next', 'light_b'],
        ['light_a', 'next', 'sound_a'], ['light_a', 'next', 'adjacent'],
        ['adjacent', 'next', 'sound_b'], ['adjacent', 'next', 'sound_a'],
        ['sound_a', 'next', 'shared'], ['sound_b', 'next', 'shared'],
    ].map(([from, output, to]) => ({ from, output, to, kind: 'execution' }));
    doc.doors.push({ ...door(), blueprint });
    doc.lights.push({ id: 'lamp', x: 12, y: 6 }, { id: 'external', x: 14, y: 6 });
    const before = clone(doc), stack = history(doc);
    const expectedTrace = simulateGraph(blueprint, 'signal:FixtureEnterOpen', 'open').trace.filter(id => !['light_a', 'adjacent'].includes(id));
    removeObject(doc, 'lights', 'lamp');
    const cleaned = doc.doors[0].blueprint;
    assert.deepEqual(simulateGraph(cleaned, 'signal:FixtureEnterOpen', 'open').trace, expectedTrace);
    assert.deepEqual(simulateGraph(cleaned, 'signal:FixtureEnterOpen', 'closed').trace, ['event', 'condition', 'sound_b', 'shared', 'light_b']);
    assert.deepEqual(cleaned.graphs['signal:FixtureEnterOpen'].edges.slice(0, 5), [
        ['event', 'next', 'condition'], ['condition', 'true', 'sound_a'], ['condition', 'true', 'sound_b'],
        ['condition', 'false', 'sound_b'], ['event', 'next', 'light_b'],
    ].map(([from, output, to]) => ({ from, output, to, kind: 'execution' })));
    assert.equal(cleaned.graphs['signal:FixtureEnterOpen'].nodes.some(node => node.targetId === 'lamp'), false);
    stack.commit(doc);
    assert.deepEqual(stack.undo(), before);
    assert.deepEqual(stack.redo(), doc);
});

test('version two duplication remaps a selected light and retains ordered typed branches', () => {
    const doc = documentWithLayer(), blueprint = upgradeBlueprint(doorBlueprint());
    const graph = blueprint.graphs['signal:FixtureEnterOpen'];
    graph.edges.push({ from: 'event', output: 'next', to: 'light_b', kind: 'execution' });
    doc.doors.push({ ...door(), blueprint });
    doc.lights.push({ id: 'lamp', x: 12, y: 6 }, { id: 'external', x: 14, y: 6 });
    const before = clone(doc);
    const copies = duplicateSelection(doc, [{ kind: 'doors', id: 'door' }, { kind: 'lights', id: 'lamp' }], 0, 3);
    const copiedLight = copies.find(ref => ref.kind === 'lights');
    assert.equal(doc.doors[1].blueprint.version, 2);
    assert.deepEqual(doc.doors[1].blueprint.graphs['signal:FixtureEnterOpen'].edges, graph.edges);
    assert.deepEqual(doc.doors[1].blueprint.graphs['signal:FixtureEnterOpen'].nodes.slice(1).map(node => node.targetId), [copiedLight.id, 'external']);
    doc.doors[1].blueprint.graphs['signal:FixtureEnterOpen'].edges.reverse();
    assert.deepEqual(doc.doors[0], before.doors[0]);
});

test('duplicating a lever, door and light remaps cross-kind targets while preserving external references', () => {
    const doc = documentWithLayer(), leverId = 'b8f1c5e2-0c4d-4a52-9d0f-6f3a3c9b1e21';
    const lever = { id: leverId, assetId: 'handle', x: 12, y: 8, width: 1, height: 1, rotation: 0,
        lever: { state: 'off' }, blueprint: defaultBlueprint('lever') };
    const doorBlueprint = upgradeBlueprint(defaultBlueprint()), graph = eventGraph('signal:FixtureEnterOpen');
    graph.nodes.push({ id: 'ref', type: 'reference', targetId: leverId, x: 300, y: 0 });
    doorBlueprint.graphs['signal:FixtureEnterOpen'] = graph;
    const leverGraph = eventGraph('signal:FixtureEnterOn');
    leverGraph.nodes.push(
        { id: 'ref_door', type: 'reference', targetId: 'door', x: 300, y: 300 },
        { id: 'ref_self', type: 'reference', targetId: leverId, x: 300, y: 600 },
        { id: 'ref_external', type: 'reference', targetId: 'external_element', x: 300, y: 900 },
        { id: 'lamp', type: 'light', targetId: 'lamp', enabled: true, x: 300, y: 0 },
        { id: 'external_lamp', type: 'light', targetId: 'external_lamp', enabled: true, x: 600, y: 0 },
    );
    connectNodes(leverGraph, 'event', 'next', 'lamp', { version: 2 });
    connectNodes(leverGraph, 'lamp', 'next', 'external_lamp', { version: 2 });
    lever.blueprint.graphs['signal:FixtureEnterOn'] = leverGraph;
    doc.doors.push({ ...door(), blueprint: doorBlueprint });
    doc.decorations.push(lever);
    doc.lights.push({ id: 'lamp', x: 14, y: 8 }, { id: 'external_lamp', x: 16, y: 8 });
    const before = clone(doc), copies = duplicateSelection(doc,
        [{ kind: 'decorations', id: leverId }, { kind: 'doors', id: 'door' }, { kind: 'lights', id: 'lamp' }], 0, 3);
    assert.equal(copies.length, 3);
    const copied = Object.fromEntries(copies.map(ref => [ref.kind, ref.id]));
    assert.equal(doc.doors[1].blueprint.graphs['signal:FixtureEnterOpen'].nodes[1].targetId, copied.decorations);
    assert.deepEqual(doc.decorations[1].blueprint.graphs['signal:FixtureEnterOn'].nodes.slice(1).map(node => node.targetId),
        [copied.doors, copied.decorations, 'external_element', copied.lights, 'external_lamp']);
    assert.deepEqual(doc.decorations[1].lever, { state: 'off' });
    assert.deepEqual(doc.decorations[1].blueprint.graphs['signal:FixtureEnterOn'].edges, leverGraph.edges);
    assert.deepEqual(doc.doors[0], before.doors[0]);
    assert.deepEqual(doc.decorations[0], before.decorations[0]);
    assert.deepEqual(doc.lights.slice(0, 2), before.lights);
    doc.decorations[1].lever.state = 'on';
    doc.decorations[1].blueprint.states.on.appearance = 'hidden';
    assert.deepEqual(doc.decorations[0], before.decorations[0], 'copied appearance and state remain independent');
});

test('removing a light bridges lever execution paths and keeps unrelated element references', () => {
    const doc = documentWithLayer(), blueprint = defaultBlueprint('lever'), graph = eventGraph('signal:FixtureEnterOn');
    graph.nodes.push(
        { id: 'lamp', type: 'light', targetId: 'lamp', enabled: true, x: 300, y: 0 },
        { id: 'state', type: 'state', targetState: 'off', x: 600, y: 0 },
        { id: 'ref', type: 'reference', targetId: 'b8f1c5e2-0c4d-4a52-9d0f-6f3a3c9b1e21', x: 300, y: 300 },
    );
    connectNodes(graph, 'event', 'next', 'lamp', { version: 2 });
    connectNodes(graph, 'lamp', 'next', 'state', { version: 2 });
    connectNodes(graph, 'ref', 'door', 'state', { version: 2, input: 'target' });
    blueprint.graphs['signal:FixtureEnterOn'] = graph;
    doc.decorations.push({ id: 'lever', x: 10, y: 10, width: 1, height: 1, rotation: 0, lever: { state: 'off' }, blueprint });
    doc.lights.push({ id: 'lamp', x: 12, y: 10 });
    removeObject(doc, 'lights', 'lamp');
    assert.equal(doc.lights.length, 0);
    assert.deepEqual(blueprint.graphs['signal:FixtureEnterOn'].nodes.map(node => node.id), ['event', 'state', 'ref']);
    assert.deepEqual(blueprint.graphs['signal:FixtureEnterOn'].edges, [
        { from: 'event', output: 'next', to: 'state', kind: 'execution' },
        { from: 'ref', output: 'door', to: 'state', input: 'target', kind: 'data' },
    ]);
    assert.deepEqual(simulateGraph(blueprint, 'signal:FixtureEnterOn', 'on').trace, ['event', 'state', 'ref']);
    removeObject(doc, 'decorations', 'lever');
    assert.equal(doc.decorations.length, 0);
});

test('light deletion exceeding the graph limit preserves every object and graph atomically', () => {
    const doc = documentWithLayer(), first = upgradeBlueprint(doorBlueprint()), second = upgradeBlueprint(doorBlueprint());
    const graph = second.graphs['signal:FixtureEnterOpen'];
    graph.nodes = graph.nodes.slice(0, 2);
    graph.edges = [];
    for (let index = 0; index < 9; index++) {
        graph.nodes.push({ id: `before_${index}`, type: 'state', targetState: 'open', x: index * 250, y: 300 },
            { id: `after_${index}`, type: 'state', targetState: 'closed', x: index * 250, y: 600 });
        graph.edges.push({ from: 'event', output: 'next', to: `before_${index}`, kind: 'execution' },
            { from: `before_${index}`, output: 'next', to: 'light_a', kind: 'execution' },
            { from: 'light_a', output: 'next', to: `after_${index}`, kind: 'execution' });
    }
    doc.doors.push({ ...door(), blueprint: first }, { ...door(), id: 'second', y1: 5, y2: 5, blueprint: second });
    doc.lights.push({ id: 'lamp', x: 12, y: 6 });
    const before = clone(doc);
    assert.equal(graph.edges.length, 27, 'the source graph is within its bound');
    assert.throws(() => removeObject(doc, 'lights', 'lamp'), /too many nodes or connections/);
    assert.deepEqual(doc, before, 'even the earlier door and the referenced light survive failure');
});
test('rectangle selection finds intersecting geometry without selecting rotated bounding-box gaps or hidden layers', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.decorations.push({ id: 'diagonal', layerId, x: 4, y: 4, width: 4, height: 1, rotation: 45 });
    doc.walls.push({ ...wall(), layerId });
    doc.lights.push({ id: 'light', layerId, x: 15, y: 15, brightRadius: 2, dimRadius: 4 });
    assert.deepEqual(objectsInRectangle(doc, { x: 3, y: 1, width: 1, height: 2 }), [{ kind: 'walls', id: 'wall' }]);
    assert.deepEqual(objectsInRectangle(doc, { x: 4.3, y: 5.6, width: .1, height: .1 }), []);
    assert.deepEqual(objectsInRectangle(doc, { x: 5.9, y: 4.4, width: .2, height: .2 }), [{ kind: 'decorations', id: 'diagonal' }]);
    assert.deepEqual(objectsInRectangle(doc, { x: 16, y: 16, width: -2, height: -2 }), [{ kind: 'lights', id: 'light' }]);
    doc.layers[0].visible = false; assert.deepEqual(objectsInRectangle(doc, { x: 0, y: 0, width: 40, height: 30 }), []);
    doc.layers[0].visible = true; doc.layers[0].locked = true;
    assert.deepEqual(objectsInRectangle(doc, { x: 0, y: 0, width: 40, height: 30 }), []);
});

test('family material sampling includes only the named family and role and can choose every member', () => {
    const doc = documentWithLayer();
    doc.assets = [
        { assetId: 'stone-a', role: 'floor', family: 'Dungeon' },
        { assetId: 'stone-b', role: 'floor', family: 'Dungeon' },
        { assetId: 'stone-c', role: 'floor', family: 'Dungeon' },
        { assetId: 'wall', role: 'wall', family: 'Dungeon' },
        { assetId: 'grass', role: 'floor', family: 'Garden' },
        { assetId: 'plain', role: 'floor' },
    ];
    const members = familyAssetIds(doc, 'floor', 'Dungeon');
    assert.deepEqual(members, ['stone-a', 'stone-b', 'stone-c']);
    assert.deepEqual([0, .34, .99999].map(value => sampleAssetId(members, () => value)), members);
    assert.deepEqual(familyAssetIds(doc, 'floor', ''), []);
    assert.deepEqual(familyAssetIds(doc, 'floor', 'Missing'), []);
    assert.equal(sampleAssetId([]), null);
});

test('a swept floor brush fills skipped pointer cells, crosses diagonal corners and clips stamp size', () => {
    const doc = documentWithLayer(); doc.columns = 8; doc.rows = 6;
    assert.deepEqual(floorBrushCells(doc, { x: .2, y: 2.2 }, { x: 7.9, y: 2.2 }),
        Array.from({ length: 8 }, (_, x) => ({ x, y: 2 })));
    const diagonal = floorBrushCells(doc, { x: .5, y: .5 }, { x: 2.5, y: 2.5 });
    assert.deepEqual(new Set(diagonal.map(cell => `${cell.x}:${cell.y}`)), new Set(['0:0', '1:0', '0:1', '1:1', '2:1', '1:2', '2:2']));
    assert.deepEqual(floorBrushCells(doc, { x: 2.5, y: 1.5 }, { x: 3, y: 1 }), [{ x: 2, y: 1 }, { x: 3, y: 1 }]);
    assert.deepEqual(floorBrushCells(doc, { x: 7.9, y: 5.9 }, undefined, 3), [{ x: 7, y: 5 }]);
    const wide = floorBrushCells(doc, { x: 1, y: 1 }, { x: 4, y: 1 }, 2);
    assert.equal(wide.length, 10); assert.equal(new Set(wide.map(cell => `${cell.x}:${cell.y}`)).size, 10);
    assert.deepEqual(floorBrushCells(doc, { x: NaN, y: 1 }), []);
});

test('floor rectangles, center-radius circles and concave polygons enumerate actual filled cells', () => {
    const doc = documentWithLayer(); doc.columns = 5; doc.rows = 5;
    assert.deepEqual(floorRectangleCells(doc, { x: 4, y: 3 }, { x: 2, y: 1 }),
        [{ x: 2, y: 1 }, { x: 3, y: 1 }, { x: 2, y: 2 }, { x: 3, y: 2 }]);
    assert.equal(floorRectangleCells(doc, { x: -2, y: -2 }, { x: 20, y: 20 }).length, 25);
    assert.equal(floorCircleCells(doc, { x: 2.5, y: 2.5 }, { x: 3.5, y: 2.5 }).length, 5);
    assert.equal(floorCircleCells(doc, { x: 0, y: 0 }, { x: 2, y: 0 }).length, 3);
    assert.deepEqual(floorCircleCells(doc, { x: 2.5, y: 2.5 }, { x: 2.5, y: 2.5 }), [{ x: 2, y: 2 }]);
    const polygon = [{ x: 0, y: 0 }, { x: 3, y: 0 }, { x: 3, y: 1 }, { x: 1, y: 1 }, { x: 1, y: 3 }, { x: 0, y: 3 }];
    assert.deepEqual(floorPolygonCells(doc, polygon), [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 2, y: 0 }, { x: 0, y: 1 }, { x: 0, y: 2 }]);
    assert.deepEqual(floorPolygonCells(doc, polygon.toReversed()), floorPolygonCells(doc, polygon));
    assert.deepEqual(floorPolygonCells(doc, polygon.slice(0, 2)), []);
    assert.deepEqual(floorPolygonCells(doc, [{ x: .5, y: .5 }, { x: 1.5, y: 1.5 }, { x: 2.5, y: 2.5 }]), []);
});

test('painting caches concrete choices across previews and revisits and history never rerolls them', () => {
    const source = documentWithLayer(), layerId = source.layers[0].id, choices = new Map();
    const cells = floorRectangleCells(source, { x: 1, y: 1 }, { x: 4, y: 2 });
    let samples = 0;
    const random = () => [0, .4, .8][samples++ % 3];
    const options = { layerId, assetIds: ['a', 'b', 'c'], choices, random, rotation: 90 };
    const first = clone(source);
    assert.equal(paintFloorCells(first, cells.slice(0, 2), options), true);
    const firstTiles = clone(first.floors);
    const next = clone(source);
    assert.equal(paintFloorCells(next, [...cells, cells[0]], options), true);
    assert.deepEqual(next.floors.slice(0, 2), firstTiles);
    assert.deepEqual(next.floors.map(item => item.assetId), ['a', 'b', 'c']);
    assert.equal(samples, 3); assert.equal(choices.size, 3);
    const revisited = clone(source);
    assert.equal(paintFloorCells(revisited, cells, options), true);
    assert.deepEqual(revisited, next); assert.equal(samples, 3);
    const stack = history(source); stack.commit(next);
    assert.deepEqual(stack.undo(), source); assert.deepEqual(stack.redo(), next);
    assert.deepEqual(JSON.parse(JSON.stringify(next)), next);
});

test('repainting replaces cells and splits a previous rectangle while preserving outside artwork and layers', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.layers.push({ id: 'other-layer', name: 'Other', visible: true, locked: false });
    const original = { id: 'room', layerId, assetId: 'old', x: .25, y: .25, width: 3.5, height: 3.5, rotation: 270 };
    const other = { id: 'overlaid', layerId: 'other-layer', assetId: 'other', x: 1, y: 1, width: 1, height: 1, rotation: 90 };
    doc.floors.push(original, other);
    const options = { layerId, assetIds: ['new'] }, cells = [{ x: 1, y: 1 }];
    assert.equal(paintFloorCells(doc, cells, options), true);
    const remaining = doc.floors.filter(item => item.assetId === 'old');
    assert.equal(remaining.length, 4); assert.equal(remaining[0].id, original.id);
    assert.ok(remaining.every(item => item.layerId === layerId && item.rotation === 270));
    assert.equal(remaining.reduce((sum, item) => sum + item.width * item.height, 0), 11.25);
    assert.deepEqual(doc.floors.find(item => item.id === 'overlaid'), other);
    assert.equal(doc.floors.at(-1).assetId, 'new'); assert.equal(doc.floors.at(-1).width, 1);
    const count = doc.floors.length;
    for (let index = 0; index < 10; index++) assert.equal(paintFloorCells(doc, cells, options), true);
    assert.equal(doc.floors.length, count); assert.equal(fitsBounds(doc), true);
    const oldPieces = doc.floors.filter(item => item.assetId === 'old');
    assert.deepEqual(oldPieces, remaining);
});

test('fractional legacy floor slivers remain intact and repeat painting does not pile up cell stamps', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    const original = { id: 'legacy', layerId, assetId: 'old', x: .98, y: .98, width: 1.2, height: 1.2, rotation: 180 };
    doc.floors.push(original);
    for (let index = 0; index < 3; index++) {
        assert.equal(paintFloorCells(doc, [{ x: 1, y: 1 }], { layerId, assetIds: ['new'] }), true);
        assert.equal(doc.floors.length, 2);
        const remainder = doc.floors[0];
        for (const key of ['id', 'assetId', 'layerId', 'x', 'y', 'width', 'height', 'rotation']) assert.equal(remainder[key], original[key]);
        assert.equal(floorContainsPoint(remainder, { x: .99, y: 1.5 }), true, 'the narrow outside sliver survives');
        assert.equal(floorContainsPoint(remainder, { x: 1.5, y: 1.5 }), false, 'the new tile has no old hidden backing');
        assert.equal(floorContainsPoint(remainder, { x: 2.1, y: 2.1 }), true);
    }
});

test('floor painting rejects the complete operation at the combined object limit and respects locked layers', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.walls.push(wall()); doc.doors.push(door());
    const before = clone(doc), choices = new Map();
    assert.equal(paintFloorCells(doc, [{ x: 0, y: 0 }, { x: 1, y: 0 }], { layerId, maxObjects: 3, choices }), false);
    assert.deepEqual(doc, before); assert.equal(choices.size, 0);
    assert.equal(paintFloorCells(doc, [{ x: 0, y: 0 }], { layerId, maxObjects: 3, choices }), true);
    assert.equal(choices.size, 1);
    assert.equal(paintFloorCells(doc, [{ x: 0, y: 0 }], { layerId, maxObjects: 3 }), true);
    assert.equal(doc.floors.length, 1);
    const painted = clone(doc);
    assert.equal(paintFloorCells(doc, [{ x: -1, y: 0 }], { layerId }), false); assert.deepEqual(doc, painted);
    doc.layers[0].locked = true;
    const locked = clone(doc);
    assert.equal(paintFloorCells(doc, [{ x: 1, y: 0 }], { layerId }), false); assert.deepEqual(doc, locked);
});

test('a floor rectangle split that exceeds the object limit is rejected without changing existing floors', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.floors.push({ id: 'room', layerId, assetId: 'old', x: 0, y: 0, width: 3, height: 3, rotation: 90 });
    const before = clone(doc), choices = new Map();
    assert.equal(paintFloorCells(doc, [{ x: 1, y: 1 }], { layerId, assetIds: ['new'], maxObjects: 4, choices }), false);
    assert.deepEqual(doc, before); assert.equal(choices.size, 0);
});

test('effects retain native parameter data while group transforms move only their anchors and rotation', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.particles.push({ id: 'smoke', layerId, x: 2, y: 3, kind: 'smoke', scale: 12, density: .6, rotation: 20,
        color: '#8899aa', enabled: true, light_response: .8, light_emission: 0 });
    doc.shaders.push({ id: 'orb', layerId, x: 6, y: 3, radius: 15, rotation: 40, name: 'Authored shader',
        source: 'gravewright-preset://orb-1/v1', opacity: .7, intensity: .8, enabled: true });
    const refs = [{ kind: 'particles', id: 'smoke' }, { kind: 'shaders', id: 'orb' }];
    assert.equal(fitsBounds(doc), true, 'the rendered area may extend outside the project');
    assert.deepEqual(selectionBounds(doc, refs), { x: 2, y: 3, width: 4, height: 0 });
    assert.equal(rotateSelection(doc, refs, 90), true);
    assert.deepEqual(doc.particles[0], { id: 'smoke', layerId, x: 4, y: 1, kind: 'smoke', scale: 12, density: .6, rotation: 110,
        color: '#8899aa', enabled: true, light_response: .8, light_emission: 0 });
    assert.equal(doc.shaders[0].x, 4); assert.equal(doc.shaders[0].y, 5); assert.equal(doc.shaders[0].rotation, 130);
    assert.equal(doc.shaders[0].radius, 15); assert.equal(doc.shaders[0].source, 'gravewright-preset://orb-1/v1');
    assert.equal(translateSelection(doc, refs, 100, 100, { snapStep: 1 }), true);
    assert.deepEqual([doc.particles[0].x, doc.particles[0].y, doc.shaders[0].x, doc.shaders[0].y], [40, 26, 40, 30]);
    assert.equal(fitsBounds(doc), true);
    assert.equal(translateSelection(doc, refs, 1, 1, { snapStep: 1 }), false, 'anchors cannot leave the map');
});

test('effect duplication, removal and history keep independent native definitions and layer ownership', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.particles.push({ id: 'smoke', layerId, x: 5, y: 5, kind: 'smoke', rotation: 0, scale: 8, density: .4, enabled: true });
    doc.shaders.push({ id: 'shader', layerId, x: 6, y: 6, radius: 0, rotation: 0, name: 'Whole scene',
        source: 'void main() { finalColor = vec4(0.); }', opacity: 1, intensity: .6, enabled: true });
    const stack = history(doc), refs = [{ kind: 'particles', id: 'smoke' }, { kind: 'shaders', id: 'shader' }];
    const copies = duplicateSelection(doc, refs, 2, 3);
    assert.equal(copies.length, 2); assert.equal(new Set(copies.map(value => value.id)).size, 2);
    assert.deepEqual([doc.particles[1].x, doc.particles[1].y, doc.shaders[1].x, doc.shaders[1].y], [7, 8, 8, 9]);
    assert.equal(doc.shaders[1].layerId, layerId); assert.equal(doc.shaders[1].source, doc.shaders[0].source);
    doc.shaders[1].source = 'Changed copy';
    assert.notEqual(doc.shaders[0].source, doc.shaders[1].source);
    stack.commit(doc);
    removeObject(doc, 'particles', copies[0].id); removeObject(doc, 'shaders', copies[1].id); stack.commit(doc);
    const restored = stack.undo();
    assert.equal(restored.particles.length, 2); assert.equal(restored.shaders.length, 2);
    assert.equal(stack.undo().particles.length, 1); assert.equal(stack.redo().shaders.length, 2);
});

test('effect marquee selection uses center anchors and excludes hidden or locked layers', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.layers.push({ id: 'hidden', name: 'Hidden', visible: false, locked: false },
        { id: 'locked', name: 'Locked', visible: true, locked: true });
    doc.particles.push({ id: 'near', layerId, x: 3, y: 3, scale: 20 },
        { id: 'far', layerId, x: 12, y: 12, scale: 20 }, { id: 'hidden', layerId: 'hidden', x: 3, y: 3 });
    doc.shaders.push({ id: 'near', layerId, x: 4, y: 4, radius: 30 }, { id: 'locked', layerId: 'locked', x: 4, y: 4 });
    assert.deepEqual(objectsInRectangle(doc, { x: 2, y: 2, width: 3, height: 3 }),
        [{ kind: 'particles', id: 'near' }, { kind: 'shaders', id: 'near' }]);
    const before = clone(doc);
    assert.equal(translateSelection(doc, [{ kind: 'shaders', id: 'locked' }], 1, 1), false);
    assert.deepEqual(duplicateSelection(doc, [{ kind: 'shaders', id: 'locked' }]), []);
    assert.deepEqual(doc, before);
});

test('opening an earlier schema-three project leaves omitted effect arrays unchanged', () => {
    const doc = documentWithLayer();
    assert.deepEqual(doc.particles, []); assert.deepEqual(doc.shaders, []);
    delete doc.particles; delete doc.shaders;
    const before = clone(doc), normalized = normalizeDocument(doc);
    assert.deepEqual(normalized, before);
    assert.equal(Object.hasOwn(normalized, 'particles'), false);
    assert.equal(Object.hasOwn(normalized, 'shaders'), false);
    assert.equal(fitsBounds(normalized), true);
    assert.deepEqual(objectsInRectangle(normalized, { x: 0, y: 0, width: 40, height: 30 }), []);
});

test('round and centered square brushes retain bounded swept coverage while legacy corner stamps stay unchanged', () => {
    const doc = documentWithLayer(); doc.columns = 20; doc.rows = 12;
    const point = { x: 5.2, y: 5.2 };
    const disk = floorBrushCells(doc, point, point, 5, { shape: 'circle', anchor: 'center' });
    assert.equal(disk.length, 21);
    assert.ok(disk.some(cell => cell.x === 3 && cell.y === 5));
    assert.ok(!disk.some(cell => cell.x === 3 && cell.y === 3));
    const square = floorBrushCells(doc, point, point, 5, { shape: 'square', anchor: 'center' });
    assert.equal(square.length, 25); assert.ok(square.some(cell => cell.x === 3 && cell.y === 3));
    assert.deepEqual(floorBrushCells(doc, point, point, 5), floorRectangleCells(doc, { x: 5, y: 5 }, { x: 10, y: 10 }));
    const stroke = floorBrushCells(doc, { x: 1.2, y: 5.2 }, { x: 17.2, y: 5.2 }, 5, { shape: 'circle', anchor: 'center' });
    for (let x = 0; x < 20; x++) assert.ok(stroke.some(cell => cell.x === x && cell.y === 5), `Missing swept cell ${x}`);
    const reverse = floorBrushCells(doc, { x: 17.2, y: 5.2 }, { x: 1.2, y: 5.2 }, 5, { shape: 'circle', anchor: 'center' });
    const keys = rows => rows.map(cell => `${cell.x}:${cell.y}`).sort();
    assert.deepEqual(keys(stroke), keys(reverse));
    const edge = floorBrushCells(doc, { x: 0, y: 0 }, undefined, 5, { shape: 'circle', anchor: 'center' });
    assert.equal(edge.length, 8); assert.ok(edge.every(cell => cell.x >= 0 && cell.y >= 0));
});

test('area erasure splits only the active layer and retains authored texture transforms', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.layers.push({ id: 'other', visible: true, locked: false });
    const room = { id: 'room', layerId, assetId: 'stone', x: .25, y: .25, width: 3.5, height: 3.5, rotation: 270 };
    const other = { id: 'other-floor', layerId: 'other', assetId: 'wood', x: 1, y: 1, width: 1, height: 1, rotation: 90 };
    doc.floors.push(room, other); doc.walls.push(wall());
    const before = clone(doc), result = eraseFloorCells(doc, [{ x: 1, y: 1 }], { layerId });
    assert.deepEqual(result, { ok: true, changed: true });
    const remaining = doc.floors.filter(item => item.layerId === layerId);
    assert.equal(remaining.length, 4);
    assert.equal(remaining.reduce((sum, item) => sum + item.width * item.height, 0), 11.25);
    assert.ok(remaining.every(item => item.assetId === 'stone' && item.rotation === 270));
    assert.equal(remaining[0].id, 'room');
    assert.deepEqual(doc.floors.find(item => item.id === other.id), other);
    assert.deepEqual(doc.walls, before.walls);
    assert.deepEqual(room, before.floors[0], 'source row is never mutated while computing its remainders');
});

test('erasing at the object limit can remove a complete room and rejects growth or unsafe fractional slivers atomically', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.floors.push({ id: 'room', layerId, assetId: 'stone', x: 0, y: 0, width: 4, height: 4, rotation: 0 });
    doc.lights.push(...Array.from({ length: 1999 }, (_, index) => ({ id: `light-${index}`, x: 1, y: 1 })));
    delete doc.particles; delete doc.shaders;
    const before = clone(doc), fragments = new Map();
    assert.deepEqual(eraseFloorCells(doc, [{ x: 1, y: 1 }], { layerId, fragmentIds: fragments }),
        { ok: false, changed: false, error: 'This map has reached the object limit.' });
    assert.deepEqual(doc, before); assert.equal(fragments.size, 0);
    assert.deepEqual(eraseFloorCells(doc, floorRectangleCells(doc, { x: 0, y: 0 }, { x: 4, y: 4 }), { layerId }),
        { ok: true, changed: true });
    assert.equal(doc.floors.length, 0); assert.equal(doc.lights.length, 1999);
    const legacy = documentWithLayer();
    legacy.floors.push({ id: 'fractional', layerId, assetId: 'stone', x: .98, y: .98, width: 1.2, height: 1.2, rotation: 180 });
    const saved = clone(legacy);
    const result = eraseFloorCells(legacy, [{ x: 1, y: 1 }], { layerId, fragmentIds: fragments });
    assert.equal(result.ok, false); assert.match(result.error, /smaller than 0.05/);
    assert.deepEqual(legacy, saved); assert.equal(fragments.size, 0);
});

test('area erase is a true no-op for empty areas and refuses hidden or locked layers without changing data', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    const before = clone(doc);
    assert.deepEqual(eraseFloorCells(doc, [{ x: 1, y: 1 }], { layerId }), { ok: true, changed: false });
    assert.deepEqual(doc, before);
    for (const property of ['locked', 'visible']) {
        doc.layers[0][property] = property === 'locked';
        const snapshot = clone(doc);
        assert.equal(eraseFloorCells(doc, [{ x: 1, y: 1 }], { layerId }).ok, false);
        assert.equal(sampleFloor(doc, { x: 1.2, y: 1.2 }, { layerId }), null);
        assert.deepEqual(floodFloorCells(doc, { x: 1.2, y: 1.2 }, { layerId }), []);
        assert.deepEqual(doc, snapshot);
        doc.layers[0][property] = property !== 'locked';
    }
});

test('eyedropper reads the topmost active-layer floor and never alters its source', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    const first = { id: 'first', layerId, assetId: 'stone', x: 1, y: 1, width: 3, height: 3, rotation: 90 };
    const top = { ...first, id: 'top', assetId: null, x: 2, y: 2, width: 1, height: 1, rotation: 270 };
    doc.layers.push({ id: 'other', visible: true, locked: false });
    doc.floors.push(first, top, { ...top, id: 'other', layerId: 'other', assetId: 'wood' });
    assert.deepEqual(sampleFloor(doc, { x: 2.2, y: 2.2 }, { layerId }), top);
    const sample = sampleFloor(doc, { x: 1.2, y: 1.2 }, { layerId });
    assert.deepEqual(sample, first); sample.assetId = 'changed';
    assert.equal(first.assetId, 'stone');
    assert.equal(sampleFloor(doc, { x: 5, y: 5 }, { layerId }), null);
    assert.equal(sampleFloor(doc, { x: doc.columns, y: 5 }, { layerId }), null);
});

test('bucket fill follows topmost active-layer material and rotation through four-neighbor regions', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.columns = 5; doc.rows = 4;
    doc.layers.push({ id: 'other', visible: true, locked: false });
    doc.floors.push({ id: 'stone', layerId, assetId: 'stone', x: 0, y: 0, width: 5, height: 4, rotation: 0 },
        { id: 'stripe', layerId, assetId: 'grass', x: 2, y: 0, width: 1, height: 4, rotation: 0 },
        { id: 'other', layerId: 'other', assetId: 'wood', x: 0, y: 0, width: 5, height: 4, rotation: 0 });
    assert.equal(floodFloorCells(doc, { x: .2, y: .2 }, { layerId }).length, 8);
    assert.equal(floodFloorCells(doc, { x: 4.2, y: .2 }, { layerId }).length, 8);
    assert.equal(floodFloorCells(doc, { x: 2.2, y: .2 }, { layerId }).length, 4);
    doc.floors.push({ id: 'turned', layerId, assetId: 'stone', x: 0, y: 0, width: 1, height: 1, rotation: 90 });
    assert.deepEqual(floodFloorCells(doc, { x: .2, y: .2 }, { layerId }), [{ x: 0, y: 0 }]);
    assert.equal(floodFloorCells(doc, { x: 1.2, y: .2 }, { layerId }).length, 7);
});

test('bucket fill distinguishes authored default floors from empty space and bounds a maximum map', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id; doc.columns = 200; doc.rows = 200;
    assert.equal(floodFloorCells(doc, { x: 100.2, y: 100.2 }, { layerId }).length, 40000);
    doc.floors.push({ id: 'plain', layerId, assetId: null, x: 1, y: 1, width: 1, height: 1, rotation: 0 });
    assert.deepEqual(floodFloorCells(doc, { x: 1.2, y: 1.2 }, { layerId }), [{ x: 1, y: 1 }]);
    assert.equal(floodFloorCells(doc, { x: .2, y: .2 }, { layerId }).length, 39999);
    assert.deepEqual(floodFloorCells(doc, { x: -1, y: .2 }, { layerId }), []);
});

test('bucket fill treats floor-family variants as one material without mixing roles, family names or rotations', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id; doc.columns = 6; doc.rows = 1;
    doc.assets = [{ assetId: 'a', role: 'floor', family: 'Stone' }, { assetId: 'b', role: 'floor', family: 'Stone' },
        { assetId: 'c', role: 'floor', family: 'Other stone' }, { assetId: 'wall-art', role: 'wall', family: 'Stone' }];
    doc.floors.push(...['a', 'b', 'a', 'b', 'c', 'wall-art'].map((assetId, x) => ({
        id: `tile-${x}`, layerId, assetId, x, y: 0, width: 1, height: 1, rotation: x === 3 ? 90 : 0,
    })));
    assert.deepEqual(floodFloorCells(doc, { x: .2, y: .2 }, { layerId }), [{ x: 0, y: 0 }, { x: 1, y: 0 }, { x: 2, y: 0 }]);
    assert.deepEqual(floodFloorCells(doc, { x: 3.2, y: .2 }, { layerId }), [{ x: 3, y: 0 }]);
    assert.deepEqual(floodFloorCells(doc, { x: 4.2, y: .2 }, { layerId }), [{ x: 4, y: 0 }]);
    assert.deepEqual(floodFloorCells(doc, { x: 5.2, y: .2 }, { layerId }), [{ x: 5, y: 0 }]);
    doc.floors[3].rotation = 0;
    assert.equal(floodFloorCells(doc, { x: .2, y: .2 }, { layerId }).length, 4);
    assert.equal(sampleFloor(doc, { x: 1.2, y: .2 }, { layerId }).assetId, 'b', 'eyedropper retains the concrete variation');
});

test('reapplying identical concrete cell material preserves IDs and source order without history changes', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.floors.push({ id: 'tile-a', layerId, assetId: 'stone', x: 1, y: 1, width: 1, height: 1, rotation: 90 },
        { id: 'tile-b', layerId, assetId: 'stone', x: 2, y: 1, width: 1, height: 1, rotation: 90 });
    const before = clone(doc), stack = history(doc);
    assert.equal(paintFloorCells(doc, [{ x: 1, y: 1 }], { layerId, assetIds: ['stone'], rotation: 90 }), true);
    assert.deepEqual(doc, before); assert.equal(stack.commit(doc), false); assert.equal(stack.canUndo, false);
    assert.equal(paintFloorCells(doc, [{ x: 1, y: 1 }, { x: 3, y: 1 }], { layerId, assetIds: ['stone'], rotation: 90 }), true);
    assert.deepEqual(doc.floors.slice(0, 2), before.floors); assert.equal(doc.floors.length, 3);
});

test('terrain strokes append one stable operator and preserve legacy floors, styles, unrelated objects and source mode', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id, choices = new Map();
    doc.floors = [floorRow(doc, 'legacy', 'old', 0, 0, 10, 10, { paint: { color: null, opacity: .5 } })];
    doc.walls = [{ ...wall(), layerId }]; const before = clone(doc), first = doc.floors[0];
    const options = { layerId, assetIds: ['red', 'blue'], size: 2, hardness: .3, intensity: .4,
        choices, random: () => .99, makeId: () => 'stroke' };
    assert.deepEqual(applyTerrainStroke(doc, [{ x: 2.125, y: 3.375 }, { x: 5.25, y: 3.375 }], options),
        { ok: true, changed: true, refs: [{ kind: 'floors', id: 'stroke' }] });
    assert.equal(doc.floors[0], first); assert.deepEqual(doc.floors[0], before.floors[0]);
    assert.equal(doc.floors[1].assetId, 'blue'); assert.equal(doc.floors[1].brush.points.length, 2);
    assert.equal(doc.editingMode, undefined); assert.deepEqual(doc.walls, before.walls);
    const preview = clone(before);
    assert.equal(applyTerrainStroke(preview, [{ x: 2.125, y: 3.375 }, { x: 6.25, y: 3.375 }],
        { ...options, random: unexpectedChoice, makeId: unexpectedChoice }).ok, true);
    assert.equal(preview.floors.at(-1).id, 'stroke'); assert.equal(preview.floors.at(-1).assetId, 'blue');
});

test('terrain eyedropper observes ordered erasures only in the active layer and later paint restores visibility', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    doc.layers.push({ id: 'other', name: 'Other', visible: true, locked: false });
    doc.floors = [floorRow(doc, 'base', 'red', 0, 0, 10, 10), floorRow(doc, 'other-base', 'blue', 0, 0, 10, 10, { layerId: 'other' })];
    assert.equal(applyTerrainStroke(doc, [{ x: 4, y: 4 }], { layerId, size: 4, hardness: 0, intensity: 1, operation: 'erase', makeId: () => 'erase' }).ok, true);
    assert.equal(doc.floors.at(-1).assetId, null); assert.equal(sampleFloor(doc, { x: 4, y: 4 }, { layerId }), null);
    assert.equal(sampleFloor(doc, { x: 5, y: 4 }, { layerId }).id, 'base', 'partially erased source remains sampleable');
    assert.equal(sampleFloor(doc, { x: 4, y: 4 }, { layerId: 'other' }).id, 'other-base');
    assert.equal(applyTerrainStroke(doc, [{ x: 4, y: 4 }], { layerId, size: 1, intensity: .5, assetIds: ['green'], makeId: () => 'new' }).ok, true);
    assert.equal(sampleFloor(doc, { x: 4, y: 4 }, { layerId }).id, 'new');
    const before = clone(doc), steps = history(before); assert.equal(steps.commit(doc), false);
    assert.equal(doc.floors[0].assetId, 'red'); assert.equal(doc.floors[0].shape, undefined);
});

test('Tiles cannot treat radial brush bboxes or erase operators as complete matching material', () => {
    for (const operation of ['paint', 'erase']) {
        const doc = documentWithLayer(), layerId = doc.layers[0].id;
        doc.floors = [floorRow(doc, 'base', 'stone', 1, 1, 3, 3)];
        assert.equal(applyTerrainStroke(doc, [{ x: 2, y: 2 }], { layerId, size: 2, hardness: 0, intensity: .5,
            operation, assetIds: ['stone'], makeId: () => 'radial' }).ok, true);
        const brush = clone(doc.floors.at(-1).brush), before = clone(doc), choices = new Map();
        assert.equal(paintFloorCells(doc, [{ x: 1, y: 1 }], { layerId, assetIds: ['stone'], choices, makeId: () => 'tile' }), true);
        assert.equal(doc.floors.at(-1).id, 'tile');
        const remainder = doc.floors.find(item => item.id === 'radial');
        assert.deepEqual(remainder.brush, brush); assert.equal(remainder.width, before.floors.at(-1).width);
        assert.equal(remainder.x, before.floors.at(-1).x); assert.equal(floorContainsPoint(remainder, { x: 1.75, y: 1.75 }), false);
        assert.ok(terrainBrushAlpha(remainder, { x: 2.25, y: 2.25 }) > 0);
    }
});

test('terrain translation, quarter rotation, duplication and undo retain normalized dabs and elliptical radii', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    applyTerrainStroke(doc, [{ x: 5.25, y: 5.5 }, { x: 5.25, y: 8.5 }],
        { layerId, size: 2, hardness: .6, intensity: .5, makeId: () => 'stroke' });
    const before = clone(doc), steps = history(doc), refs = [{ kind: 'floors', id: 'stroke' }], initial = clone(doc.floors[0]);
    assert.equal(translateSelection(doc, refs, 2.25, 1.125), true);
    assert.deepEqual(doc.floors[0].brush, initial.brush);
    const shifted = clone(doc.floors[0]);
    assert.equal(rotateSelection(doc, refs, 90), true);
    const rotated = doc.floors[0];
    assert.equal(rotated.width, shifted.height); assert.equal(rotated.height, shifted.width);
    assert.deepEqual(rotated.brush.radius, shifted.brush.radius.toReversed());
    assert.deepEqual(rotated.brush.points, shifted.brush.points.map(([u, v, alpha]) => [1 - v, u, alpha]));
    const copies = duplicateSelection(doc, refs); assert.equal(copies.length, 1);
    const copy = doc.floors.find(item => item.id === copies[0].id);
    assert.deepEqual(copy.brush, rotated.brush); assert.notEqual(copy.brush, rotated.brush);
    assert.equal(steps.commit(doc), true); assert.deepEqual(steps.undo(), before); assert.deepEqual(steps.redo(), doc);
});

test('terrain limits, invalid settings and protected layers reject the complete operation without publishing choices', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id;
    for (const options of [{ size: .01 }, { hardness: -1 }, { intensity: NaN }, { operation: 'smudge' }, { rotation: 45 }]) {
        const before = clone(doc), choices = new Map();
        assert.equal(applyTerrainStroke(doc, [{ x: 1, y: 1 }], { layerId, ...options, choices, makeId: unexpectedChoice }).ok, false);
        assert.deepEqual(doc, before); assert.equal(choices.size, 0);
    }
    for (const options of [{ intensity: 0 }, { intensity: .0001 }, { operation: 'erase' }]) {
        const before = clone(doc);
        assert.equal(applyTerrainStroke(doc, [{ x: 1, y: 1 }], { layerId, ...options, makeId: unexpectedChoice }).changed, false);
        assert.deepEqual(doc, before);
    }
    for (const change of [{ visible: false }, { locked: true }]) {
        Object.assign(doc.layers[0], { visible: true, locked: false }, change); const before = clone(doc);
        assert.equal(applyTerrainStroke(doc, [{ x: 1, y: 1 }], { layerId }).ok, false); assert.deepEqual(doc, before);
    }
    Object.assign(doc.layers[0], { visible: true, locked: false });
    const many = Array.from({ length: 2049 }, () => ({ x: 1, y: 1 })), before = clone(doc);
    assert.equal(applyTerrainStroke(doc, many, { layerId, makeId: unexpectedChoice }).error, 'The map has too many terrain brush dabs.');
    assert.deepEqual(doc, before);
    doc.lights = Array.from({ length: 2000 }, (_, index) => ({ id: `light-${index}`, layerId, x: 1, y: 1 }));
    const maxed = clone(doc);
    assert.equal(applyTerrainStroke(doc, [{ x: 1, y: 1 }], { layerId, makeId: unexpectedChoice }).error, 'This map has reached the object limit.');
    assert.deepEqual(doc, maxed);
});

test('terrain work, cumulative dab and source-byte budgets leave original arrays and preview caches intact', () => {
    const doc = documentWithLayer(), layerId = doc.layers[0].id, choices = new Map();
    const points = Array.from({ length: 2048 }, () => ({ x: 20, y: 15 })), floors = doc.floors;
    assert.equal(applyTerrainStroke(doc, points, { layerId, size: 20, choices }).error, 'The map terrain brushes are too complex.');
    assert.equal(doc.floors, floors); assert.equal(choices.size, 0);
    const small = Array.from({ length: 2048 }, () => ({ x: 2, y: 2 }));
    for (let index = 0; index < 4; index++) assert.equal(applyTerrainStroke(doc, small,
        { layerId, size: .05, makeId: () => `stroke-${index}` }).ok, true);
    const before = clone(doc);
    assert.equal(applyTerrainStroke(doc, [{ x: 2, y: 2 }], { layerId, size: .05, choices }).error, 'The map has too many terrain brush dabs.');
    assert.deepEqual(doc, before); assert.equal(choices.size, 0);
    const huge = documentWithLayer(); huge.name = 'x'.repeat(999500); const original = clone(huge);
    assert.equal(applyTerrainStroke(huge, Array(100).fill({ x: 2, y: 2 }), { layerId: huge.layers[0].id, choices }).error, 'The map project is too large.');
    assert.deepEqual(huge, original); assert.equal(choices.size, 0);
});
