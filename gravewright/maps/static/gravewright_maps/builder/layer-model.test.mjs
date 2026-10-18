import test from 'node:test';
import assert from 'node:assert/strict';
import { clone, history, newDocument, objectKinds } from './model.js';
import { floorGeometryError } from './floor-geometry.js';
import { layerContents, layerSummaries, canMergeLayerDown, mergeLayerDown, moveSelectionToLayer,
    reorderLayer, duplicateLayer } from './layer-model.js';

const id = number => `00000000-0000-4000-8000-${String(number).padStart(12, '0')}`;
const layer = (number, options = {}) => ({ id: id(number), name: `Layer ${number}`, visible: true, locked: false, ...options });
function documentWithLayers(count = 3) {
    const document = newDocument();
    document.layers = Array.from({ length: count }, (_, index) => layer(index + 1));
    return document;
}
function object(kind, number, layerNumber) {
    const base = { id: id(number), layerId: id(layerNumber) };
    if (kind === 'regions') return { ...base, name: 'Pressure plate', enabled: true, x: 2, y: 3, width: 2, height: 1 };
    if (kind === 'floors') return { ...base, assetId: id(900), x: 2, y: 3, width: 4, height: 2, rotation: 0 };
    if (kind === 'walls' || kind === 'doors') return { ...base, assetId: null, x1: 1, y1: 3, x2: 4, y2: 3,
        thickness: .18, ...(kind === 'doors' ? { state: 'closed' } : {}) };
    if (kind === 'decorations') return { ...base, assetId: id(901), x: 2, y: 3, width: 1, height: 2, rotation: 23, layer: 'over' };
    if (kind === 'lights') return { ...base, x: 3, y: 4, color: '#abcdef', brightRadius: 4, dimRadius: 8,
        enabled: false, animation: { type: 'torch', speed: 2, intensity: .8 } };
    if (kind === 'particles') return { ...base, kind: 'smoke', x: 3, y: 4, scale: 2, density: .4, color: '#cdefab',
        enabled: false, rotation: 75, light_response: .6, light_emission: .2 };
    return { ...base, name: 'Authored shader', source: 'void main() { gl_FragColor = vec4(1.0); }', x: 2, y: 3,
        radius: 4, scale: 3, intensity: .2, opacity: .8, speed: 2, color: '#fedcba', rotation: 25,
        blend_mode: 'screen', enabled: false, light_response: .3, light_emission: .4 };
}
const orderedIds = (document, kind) => document.layers.flatMap(current =>
    (document[kind] || []).filter(row => row.layerId === current.id).map(row => row.id));

test('an empty project is a valid layer collection and cannot create orphan objects through layer operations', () => {
    const document = documentWithLayers(0), before = clone(document);
    assert.deepEqual(document.layers, []); assert.deepEqual(layerSummaries(document), []);
    assert.deepEqual(layerContents(document, id(1)), []);
    assert.equal(reorderLayer(document, id(1), 0), false);
    assert.equal(duplicateLayer(document, id(1), 'Copy'), null);
    assert.equal(mergeLayerDown(document, id(1)), null);
    assert.equal(moveSelectionToLayer(document, [{ kind: 'floors', id: id(100) }], id(1)), false);
    assert.deepEqual(document, before);
    document.layers.push(layer(1));
    assert.equal(layerSummaries(document).length, 1);
    assert.deepEqual(duplicateLayer(document, id(1), 'First copy').refs, []);
});

test('layer reordering uses the final bottom-to-top index and preserves every object identity and array', () => {
    const document = documentWithLayers(4);
    for (const [index, kind] of objectKinds.entries()) document[kind].push(object(kind, 100 + index, 2));
    document.layers[1].locked = true; document.layers[1].visible = false;
    const before = clone(document), arrays = objectKinds.map(kind => document[kind]);
    assert.equal(reorderLayer(document, id(2), 3), true);
    assert.deepEqual(document.layers.map(row => row.id), [id(1), id(3), id(4), id(2)]);
    assert.equal(reorderLayer(document, id(2), 0), true);
    assert.deepEqual(document.layers.map(row => row.id), [id(2), id(1), id(3), id(4)]);
    assert.deepEqual(document.layers[0], before.layers[1]);
    for (const [index, kind] of objectKinds.entries()) {
        assert.equal(document[kind], arrays[index]); assert.deepEqual(document[kind], before[kind]);
    }
    const moved = clone(document), steps = history(document);
    for (const index of [-1, 4, 1.5, NaN, Infinity, '1', null, undefined, 0]) {
        assert.equal(reorderLayer(document, id(2), index), false); assert.deepEqual(document, moved);
    }
    assert.equal(reorderLayer(document, id(999), 0), false);
    assert.equal(steps.commit(document), false);
});

test('duplicating a complete layer remaps copied Smart Object targets and preserves external targets and authored geometry', () => {
    const document = documentWithLayers();
    for (const [index, kind] of objectKinds.entries()) document[kind].push(object(kind, 100 + index, 2));
    document.floors[0].shape = { contours: [[[0, 0], [1, 0], [1, 1], [0, 1]]], cuts: [[[.2, .2], [.4, .2], [.3, .4]]] };
    document.floors[0].paint = { color: null, opacity: .45 };
    document.decorations[0].lever = { state: 'off' };
    document.lights.push(object('lights', 204, 1));
    document.decorations.push({ ...object('decorations', 203, 1), lever: { state: 'on' } });
    const targets = [
        { id: 'lever', type: 'reference', targetId: id(103) },
        { id: 'door', type: 'reference', targetId: id(102) },
        { id: 'self-light', type: 'light', targetId: id(104), enabled: true },
        { id: 'external-element', type: 'reference', targetId: id(203) },
        { id: 'external-light', type: 'light', targetId: id(204), enabled: false },
        { id: 'sound', type: 'sound', trackId: id(300), volume: .7 },
    ];
    for (const [kind, event] of [['doors', 'signal:FixtureEnterOpen'], ['decorations', 'signal:FixtureEnterOn']]) document[kind][0].blueprint = {
        version: 2, graphs: { [event]: { nodes: clone(targets), edges: [
            { from: 'lever', output: 'door', to: 'door', input: 'target', kind: 'data' },
        ] } },
    };
    const before = clone(document), steps = history(document), result = duplicateLayer(document, id(2), '  Copy of room  ');
    assert.equal(result.refs.length, objectKinds.length);
    assert.match(result.layerId, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    assert.deepEqual(document.layers.map(row => row.id), [id(1), id(2), result.layerId, id(3)]);
    assert.deepEqual(document.layers[2], { id: result.layerId, name: 'Copy of room', visible: true, locked: false });
    const copied = new Map(result.refs.map(ref => [ref.kind, ref.id])), originalIds = new Set(objectKinds.flatMap(kind => before[kind].map(row => row.id)));
    assert.equal(new Set(result.refs.map(ref => ref.id)).size, objectKinds.length);
    assert.equal(result.refs.some(ref => originalIds.has(ref.id)), false);
    for (const kind of objectKinds) {
        const source = before[kind][0], copy = document[kind].find(row => row.id === copied.get(kind));
        const expected = { ...clone(source), id: copy.id, layerId: result.layerId };
        if (kind === 'walls' || kind === 'doors') for (const key of ['x1', 'y1', 'x2', 'y2']) expected[key]++;
        else { expected.x++; expected.y++; }
        if (expected.blueprint) for (const graph of Object.values(expected.blueprint.graphs)) for (const node of graph.nodes) {
            if (node.targetId === id(103)) node.targetId = copied.get('decorations');
            if (node.targetId === id(102)) node.targetId = copied.get('doors');
            if (node.targetId === id(104)) node.targetId = copied.get('lights');
        }
        assert.deepEqual(copy, expected);
        assert.deepEqual(document[kind].filter(row => originalIds.has(row.id)), before[kind]);
    }
    assert.deepEqual(document.assets, before.assets);
    assert.equal(steps.commit(document), true); assert.deepEqual(steps.undo(), before); assert.deepEqual(steps.redo(), document);
    document.floors.at(-1).shape.cuts[0][0][0] = .1;
    document.decorations.at(-1).lever.state = 'on';
    assert.deepEqual(document.floors[0], before.floors[0]); assert.deepEqual(document.decorations[0], before.decorations[0]);
});

test('layer copies can reveal hidden contents and preserve omitted arrays without unlocking a protected source', () => {
    const document = documentWithLayers(1); delete document.particles; delete document.shaders;
    document.layers[0].visible = false; document.floors.push(object('floors', 100, 1));
    const result = duplicateLayer(document, id(1), 'Visible copy');
    assert.ok(result); assert.equal(document.layers[0].visible, false);
    assert.deepEqual(document.layers[1], { id: result.layerId, name: 'Visible copy', visible: true, locked: false });
    assert.equal('particles' in document, false); assert.equal('shaders' in document, false);
    document.layers[0].locked = true;
    const before = clone(document);
    assert.equal(duplicateLayer(document, id(1), 'Locked copy'), null); assert.deepEqual(document, before);
});

test('layer duplication rejects invalid names, object and layer overflow, exact-offset bounds and door conflicts atomically', () => {
    for (const name of ['', '   ', 'a'.repeat(81), 'bad\0name', null, 1]) {
        const document = documentWithLayers(1), before = clone(document);
        assert.equal(duplicateLayer(document, id(1), name), null); assert.deepEqual(document, before);
    }
    const cases = [];
    cases.push(documentWithLayers(32));
    const excessive = documentWithLayers(1);
    excessive.lights = Array.from({ length: 1001 }, (_, index) => object('lights', index + 100, 1)); cases.push(excessive);
    for (const position of [{ x: 36, y: 3 }, { x: 2, y: 28 }]) {
        const document = documentWithLayers(1); document.floors.push({ ...object('floors', 100, 1), ...position }); cases.push(document);
    }
    const occupied = documentWithLayers(2);
    occupied.doors = [object('doors', 100, 1), { ...object('doors', 101, 2), x1: 2, x2: 5, y1: 4, y2: 4 }]; cases.push(occupied);
    for (const document of cases) {
        const before = clone(document);
        assert.equal(duplicateLayer(document, id(1), 'Copy'), null); assert.deepEqual(document, before);
    }
    const exact = documentWithLayers(31);
    exact.lights = Array.from({ length: 1000 }, (_, index) => object('lights', index + 100, 1));
    assert.equal(duplicateLayer(exact, id(1), 'Copy').refs.length, 1000);
    assert.equal(exact.layers.length, 32); assert.equal(exact.lights.length, 2000);
});

test('copying complex floor shapes or large shader source respects whole-document budgets before mutation', () => {
    const vector = documentWithLayers(1); vector.cellSize = 16;
    const ring = Array.from({ length: 256 }, (_, index) => {
        const angle = index * Math.PI / 128; return [.5 + .4 * Math.cos(angle), .5 + .4 * Math.sin(angle)];
    });
    vector.floors = Array.from({ length: 33 }, (_, index) => ({ ...object('floors', 100 + index, 1), width: 1, height: 1,
        shape: { contours: [clone(ring)], cuts: [] } }));
    const shader = documentWithLayers(1); shader.shaders = [{ ...object('shaders', 100, 1), source: 'x'.repeat(500000) }];
    for (const document of [vector, shader]) {
        assert.equal(floorGeometryError(document), null);
        const before = clone(document);
        assert.equal(duplicateLayer(document, id(1), 'Copy'), null); assert.deepEqual(document, before);
    }
});

test('layer summaries count all object kinds in stored order and expose independent references', () => {
    const document = documentWithLayers();
    for (const [index, kind] of objectKinds.entries()) document[kind].push(object(kind, 100 + index, index % 2 + 1));
    document.layers[2].locked = true;
    const summaries = layerSummaries(document);
    assert.deepEqual(summaries.map(row => [row.id, row.index, row.count, row.canMergeDown]), [
        [id(1), 0, 4, false], [id(2), 1, 4, true], [id(3), 2, 0, false],
    ]);
    assert.deepEqual(summaries[0].counts, { floors: 1, walls: 0, doors: 1, decorations: 0, lights: 1, particles: 0, shaders: 1, regions: 0 });
    assert.deepEqual(summaries[1].refs, [
        { kind: 'walls', id: id(101) }, { kind: 'decorations', id: id(103) }, { kind: 'particles', id: id(105) }, { kind: 'regions', id: id(107) },
    ]);
    summaries[0].name = 'Changed'; summaries[0].refs[0].id = 'changed'; summaries[0].counts.floors = 99;
    assert.equal(document.layers[0].name, 'Layer 1');
    assert.equal(document.floors[0].id, id(100));
    assert.equal(layerSummaries(document)[0].counts.floors, 1);
});

test('selecting contents can include hidden or locked layers only for inspection', () => {
    const document = documentWithLayers(); document.floors.push(object('floors', 100, 2));
    const refs = [{ kind: 'floors', id: id(100) }];
    assert.deepEqual(layerContents(document, id(2), { editable: true }), refs);
    for (const property of ['visible', 'locked']) {
        document.layers[1][property] = property === 'locked';
        assert.deepEqual(layerContents(document, id(2)), refs);
        assert.deepEqual(layerContents(document, id(2), { editable: true }), []);
        document.layers[1][property] = property === 'visible';
    }
    assert.deepEqual(layerContents(document, id(999)), []);
    const independent = layerContents(document, id(2)); independent[0].id = 'changed';
    assert.deepEqual(layerContents(document, id(2)), refs);
});

test('merge keeps paint precedence despite interleaved original arrays and targets only the adjacent lower layer', () => {
    const document = documentWithLayers(4);
    document.floors = [object('floors', 103, 3), object('floors', 105, 4), object('floors', 101, 2),
        object('floors', 104, 3), object('floors', 102, 2), object('floors', 100, 1)];
    const before = orderedIds(document, 'floors');
    assert.deepEqual(before, [100, 101, 102, 103, 104, 105].map(id));
    const result = mergeLayerDown(document, id(3));
    assert.equal(result.layerId, id(2));
    assert.deepEqual(document.layers.map(row => row.id), [id(1), id(2), id(4)]);
    assert.deepEqual(document.floors.map(row => row.id), before);
    assert.deepEqual(orderedIds(document, 'floors'), before);
    assert.deepEqual(result.refs, [101, 102, 103, 104].map(number => ({ kind: 'floors', id: id(number) })));
    assert.deepEqual(result.moved, [103, 104].map(number => ({ kind: 'floors', id: id(number) })));
    assert.equal(document.floors.find(row => row.id === id(100)).layerId, id(1));
    assert.equal(document.floors.find(row => row.id === id(105)).layerId, id(4));
});

test('merge preserves all object identities, geometry, native effects, and door/lever blueprint UUID targets', () => {
    const document = documentWithLayers();
    for (const [index, kind] of objectKinds.entries()) document[kind] = [object(kind, 100 + index, 3), object(kind, 200 + index, 2)];
    document.doors[0].blueprint = { version: 2, graphs: { 'signal:FixtureEnterOpen': { nodes: [
        { id: 'reference', type: 'reference', targetId: id(103), x: 0, y: 0 },
        { id: 'light', type: 'light', targetId: id(104), enabled: true, x: 1, y: 0 },
    ], edges: [{ from: 'reference', to: 'light' }] } } };
    document.decorations[0].lever = { initialState: 'off' };
    document.decorations[0].blueprint = { version: 2, graphs: { 'signal:FixtureEnterOn': { nodes: [
        { id: 'reference', type: 'reference', targetId: id(102), x: 0, y: 0 },
    ], edges: [] } } };
    const before = clone(document), order = Object.fromEntries(objectKinds.map(kind => [kind, orderedIds(document, kind)]));
    const result = mergeLayerDown(document, id(3));
    assert.equal(result.moved.length, objectKinds.length); assert.equal(result.refs.length, 2 * objectKinds.length);
    for (const kind of objectKinds) {
        assert.deepEqual(document[kind].map(row => row.id), order[kind]);
        assert.equal(document[kind].length, before[kind].length);
        for (const row of document[kind]) {
            const original = before[kind].find(item => item.id === row.id);
            assert.deepEqual(row, { ...original, layerId: id(2) });
        }
    }
    assert.deepEqual(document.assets, before.assets);
    assert.equal(document.doors.length, 2);
});

test('merge retains omitted legacy effect arrays and allows removing an empty upper layer', () => {
    const document = documentWithLayers(2); delete document.particles; delete document.shaders;
    const original = clone(document.layers[0]);
    assert.equal(canMergeLayerDown(document, id(2)), true);
    assert.deepEqual(mergeLayerDown(document, id(2)), { layerId: id(1), refs: [], moved: [] });
    assert.deepEqual(document.layers, [original]);
    assert.equal('particles' in document, false); assert.equal('shaders' in document, false);
    assert.equal(canMergeLayerDown(document, id(1)), false);
    assert.equal(mergeLayerDown(document, id(1)), null);
});

test('merging an upper terrain erasure cannot erase backing from the adjacent lower layer', () => {
    const document = documentWithLayers(2);
    const brush = { operation: 'erase', points: [[.5, .5, .5]], radius: [.5, .5], hardness: 0 };
    document.floors = [object('floors', 100, 1), { ...object('floors', 101, 2), assetId: null, brush }];
    const before = clone(document), floors = document.floors, layers = document.layers, steps = history(document);
    assert.equal(canMergeLayerDown(document, id(2)), false);
    assert.equal(layerSummaries(document).find(row => row.id === id(2)).canMergeDown, false);
    assert.equal(mergeLayerDown(document, id(2)), null);
    assert.equal(document.floors, floors); assert.equal(document.layers, layers);
    assert.deepEqual(document, before); assert.equal(steps.commit(document), false);
    document.floors.shift(); document.walls.push(object('walls', 102, 1));
    assert.equal(canMergeLayerDown(document, id(2)), true, 'the lower layer has no floor backing to erase');
    assert.equal(mergeLayerDown(document, id(2)).layerId, id(1));
    assert.deepEqual(document.floors[0].brush, brush);
});

test('merge refuses missing, lowest, hidden or locked layers without changing the document', () => {
    for (const options of [{ source: id(999) }, { source: id(1) },
        { index: 1, visible: false }, { index: 1, locked: true }, { index: 0, visible: false }, { index: 0, locked: true }]) {
        const document = documentWithLayers(2); document.floors.push(object('floors', 100, 2));
        if ('index' in options) Object.assign(document.layers[options.index], options);
        const before = clone(document), source = options.source || id(2);
        assert.equal(canMergeLayerDown(document, source), false);
        assert.equal(mergeLayerDown(document, source), null); assert.deepEqual(document, before);
    }
    const document = documentWithLayers(1), before = clone(document);
    assert.equal(mergeLayerDown(document, id(1)), null); assert.deepEqual(document, before);
});

test('moves preserve geometry, ordering and graph targets while deduplicating selection references', () => {
    const document = documentWithLayers();
    for (const [index, kind] of objectKinds.entries()) document[kind] = [object(kind, 100 + index, 1), object(kind, 200 + index, 2)];
    document.doors[0].blueprint = { version: 2, graphs: { 'signal:FixtureEnterOpen': {
        nodes: [{ id: 'light', type: 'light', targetId: id(104), enabled: true }], edges: [],
    } } };
    const before = clone(document), refs = objectKinds.map((kind, index) => ({ kind, id: id(100 + index) }));
    assert.equal(moveSelectionToLayer(document, [...refs, refs[0]], id(3)), true);
    for (const kind of objectKinds) assert.deepEqual(document[kind], [
        { ...before[kind][0], layerId: id(3) }, before[kind][1],
    ]);
    assert.deepEqual(document.layers, before.layers); assert.deepEqual(document.assets, before.assets);
    assert.equal(moveSelectionToLayer(document, refs, id(3)), false);
});

test('moves validate the whole selection and both layer permissions before applying any change', () => {
    const cases = [
        { refs: [] }, { refs: null }, { target: id(999) }, { targetVisible: false }, { targetLocked: true },
        { sourceVisible: false }, { sourceLocked: true },
        { second: { kind: 'floors', id: id(999) } }, { second: { kind: 'unknown', id: id(100) } }, { second: null },
    ];
    for (const options of cases) {
        const document = documentWithLayers(); document.floors.push(object('floors', 100, 1));
        document.walls.push(object('walls', 101, 2));
        if ('targetVisible' in options) document.layers[2].visible = options.targetVisible;
        if ('targetLocked' in options) document.layers[2].locked = options.targetLocked;
        if ('sourceVisible' in options) document.layers[1].visible = options.sourceVisible;
        if ('sourceLocked' in options) document.layers[1].locked = options.sourceLocked;
        const before = clone(document), refs = 'refs' in options ? options.refs
            : [{ kind: 'floors', id: id(100) }, 'second' in options ? options.second : { kind: 'walls', id: id(101) }];
        assert.equal(moveSelectionToLayer(document, refs, options.target || id(3)), false);
        assert.deepEqual(document, before);
    }
});

test('moving into an existing source layer changes only the other selected objects and preserves omitted arrays', () => {
    const document = documentWithLayers(2); delete document.particles; delete document.shaders;
    document.floors = [object('floors', 100, 1), object('floors', 101, 2)];
    const first = clone(document.floors[0]);
    assert.equal(moveSelectionToLayer(document, [{ kind: 'floors', id: id(100) }, { kind: 'floors', id: id(101) }], id(1)), true);
    assert.deepEqual(document.floors[0], first); assert.equal(document.floors[1].layerId, id(1));
    assert.equal('particles' in document, false); assert.equal('shaders' in document, false);
});

test('mutations reject invalid references and documents beyond layer or object limits atomically', () => {
    const invalidDocuments = [documentWithLayers(33)];
    const emptyOrphan = documentWithLayers(0); emptyOrphan.floors.push(object('floors', 100, 1)); invalidDocuments.push(emptyOrphan);
    const duplicateLayers = documentWithLayers(); duplicateLayers.layers[1].id = id(1); invalidDocuments.push(duplicateLayers);
    const orphan = documentWithLayers(); orphan.floors.push(object('floors', 100, 999)); invalidDocuments.push(orphan);
    const duplicate = documentWithLayers(); duplicate.floors.push(object('floors', 100, 1));
    duplicate.lights.push(object('lights', 100, 2)); invalidDocuments.push(duplicate);
    const malformed = documentWithLayers(); malformed.particles = null; invalidDocuments.push(malformed);
    const excessive = documentWithLayers(); excessive.floors = Array.from({ length: 2001 }, (_, index) => object('floors', index + 100, 1));
    invalidDocuments.push(excessive);
    for (const document of invalidDocuments) {
        const before = clone(document);
        assert.equal(canMergeLayerDown(document, id(2)), false);
        assert.equal(mergeLayerDown(document, id(2)), null);
        assert.equal(moveSelectionToLayer(document, [{ kind: 'floors', id: id(100) }], id(2)), false);
        assert.equal(reorderLayer(document, id(1), 1), false);
        assert.equal(duplicateLayer(document, id(1), 'Copy'), null);
        assert.deepEqual(document, before);
    }
});

test('layer and object counts exactly at server limits remain editable', () => {
    const document = documentWithLayers(32);
    document.floors = Array.from({ length: 2000 }, (_, index) => object('floors', index + 100, 32));
    assert.equal(layerSummaries(document)[31].count, 2000);
    assert.equal(canMergeLayerDown(document, id(32)), true);
    assert.equal(moveSelectionToLayer(document, [{ kind: 'floors', id: id(100) }], id(31)), true);
    assert.equal(mergeLayerDown(document, id(32)).refs.length, 2000);
    assert.equal(document.layers.length, 31); assert.equal(document.floors.length, 2000);
});
