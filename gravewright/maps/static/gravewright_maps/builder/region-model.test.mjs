import test from 'node:test';
import assert from 'node:assert/strict';
import { newDocument, normalizeDocument, clone, fitsBounds, translateSelection, rotateSelection,
    duplicateSelection, objectsInRectangle, selectionBounds, removeObject, history } from './model.js';
import { createRegion, regionBounds, regionContainsPoint, validateRegionGeometry, regionInstance, configurePressurePlate,
    normalizeRegionFilters, regionMatchesFilters } from './region-model.js';
import { defaultBlueprint, eventGraph, connectNodes, validateBlueprint, simulateGraph, elementInstanceNode, blueprintEventsFor } from './blueprint-model.js';
import { duplicateLayer, moveSelectionToLayer, layerContents } from './layer-model.js';

const id = number => `00000000-0000-4000-8000-${String(number).padStart(12, '0')}`;
function fixture() {
    const document = newDocument();
    document.layers = [{ id: id(1), name: 'Ground', visible: true, locked: false }, { id: id(2), name: 'Mechanisms', visible: true, locked: false }];
    return document;
}
const addRegion = (document, extra = {}) => {
    const region = createRegion(document, { x: 2, y: 3 }, { x: 5, y: 5 }, { id: id(10), layerId: id(1), name: 'Plate', ...extra });
    document.regions.push(region); return region;
};

test('optional region filters normalize only an edited draft and preserve omitted legacy source settings', () => {
    const partial = { actorIds: [id(2).toUpperCase()], visibility: 'hidden' }, before = clone(partial);
    assert.deepEqual(normalizeRegionFilters(partial), { tokenIds: [], actorIds: [id(2)], dispositions: [], visibility: 'hidden' });
    assert.deepEqual(partial, before);
    assert.deepEqual(normalizeRegionFilters(), { tokenIds: [], actorIds: [], dispositions: [], visibility: 'any' });
    const document = fixture(), legacy = addRegion(document);
    assert.equal(Object.hasOwn(legacy, 'filters'), false);
    const filtered = createRegion(document, { x: 1, y: 1 }, { x: 2, y: 2 }, { layerId: id(1), filters: partial });
    assert.deepEqual(filtered.filters, normalizeRegionFilters(partial));
    assert.equal(document.regions.length, 1);
});

test('region filters validate bounds, UUID uniqueness, enum values and optional object fields strictly', () => {
    for (const filters of [null, [], { extra: 1 }, { tokenIds: 'all' }, { actorIds: [null] }, { tokenIds: Array(2) },
        { actorIds: [id(1), id(1).toUpperCase()] }, { tokenIds: [id(1) + '\n'] }, { tokenIds: ['invalid'] },
        { tokenIds: Array.from({ length: 65 }, (_, index) => id(index + 1)) }, { dispositions: ['friendly', 'friendly'] },
        { dispositions: ['all'] }, { dispositions: 'hostile' }, { visibility: 'all' }, { visibility: true }]) {
        assert.throws(() => normalizeRegionFilters(filters), /filters/);
        assert.equal(regionMatchesFilters(filters, { id: id(1), actorId: id(2), hidden: false }), false);
    }
    assert.equal(normalizeRegionFilters({ tokenIds: Array.from({ length: 64 }, (_, index) => id(index + 1)) }).tokenIds.length, 64);
});

test('region filters combine criteria with AND and list members with OR, independently of control permissions', () => {
    const filters = { tokenIds: [id(1), id(2)], actorIds: [id(3)], dispositions: ['friendly', 'neutral'], visibility: 'visible' };
    const token = { id: id(2), actorId: id(3), disposition: 'neutral', hidden: false, canControl: false };
    assert.equal(regionMatchesFilters(filters, token), true);
    for (const patch of [{ id: id(4) }, { actorId: id(4) }, { disposition: 'hostile' }, { hidden: true }])
        assert.equal(regionMatchesFilters(filters, { ...token, ...patch }), false);
    assert.equal(regionMatchesFilters(undefined, { ...token, hidden: true }), true);
    assert.equal(regionMatchesFilters({ visibility: 'hidden' }, { ...token, hidden: true }), true);
    assert.equal(regionMatchesFilters({ dispositions: ['unknown'] }, { ...token, disposition: 'unknown' }), true);
    assert.equal(regionMatchesFilters({ dispositions: ['unknown'] }, { ...token, disposition: undefined }), false);
});

test('filtering stays separate from presence geometry and invalid authored filters cannot pass geometry validation', () => {
    const document = fixture(), region = addRegion(document);
    region.filters = { visibility: 'hidden' };
    assert.equal(validateRegionGeometry(document, region), true);
    assert.equal(regionContainsPoint(region, { x: 3, y: 4 }), true);
    assert.equal(regionMatchesFilters(region.filters, { id: id(1), hidden: false }), false);
    region.filters.visibility = 'wrong';
    assert.equal(validateRegionGeometry(document, region), false);
});

test('copying a region preserves external token and actor filter identities without rewriting matching source-object UUIDs', () => {
    const document = fixture(), region = addRegion(document);
    region.filters = { tokenIds: [region.id], actorIds: [id(11)], dispositions: ['hostile'], visibility: 'any' };
    const before = clone(region), copies = duplicateSelection(document, [{ kind: 'regions', id: region.id }], 0, 3);
    assert.equal(copies.length, 1);
    const copy = document.regions.find(row => row.id === copies[0].id);
    assert.deepEqual(copy.filters, before.filters);
    copy.filters.tokenIds.push(id(12));
    assert.deepEqual(region, before);
});

test('region creation snaps or preserves free coordinates without mutating the source, including map edges', () => {
    const document = fixture(), before = clone(document);
    assert.deepEqual(createRegion(document, { x: 5.2, y: 6.8 }, { x: 2.4, y: 3.2 }, { id: id(10), layerId: id(1), name: '  Entry  ' }),
        { id: id(10), layerId: id(1), name: 'Entry', enabled: true, x: 2, y: 3, width: 3, height: 4 });
    const free = createRegion(document, { x: 2.125, y: 3.375 }, { x: 4.75, y: 5.875 }, { layerId: id(1), snap: false });
    assert.deepEqual(regionBounds(free), { x: 2.125, y: 3.375, width: 2.625, height: 2.5 });
    assert.deepEqual(regionBounds(createRegion(document, { x: 40, y: 30 }, { x: 40, y: 30 }, { layerId: id(1) })),
        { x: 39, y: 29, width: 1, height: 1 });
    assert.deepEqual(document, before);
    const named = createRegion(document, { x: 1, y: 1 }, { x: 2, y: 2 }, { layerId: id(1), name: '雪🗺'.repeat(60) });
    assert.equal(Array.from(named.name).length, 120);
    for (const options of [{ layerId: id(9) }, { layerId: id(1), name: ' ' }, { layerId: id(1), name: 'a'.repeat(121) }, { layerId: id(1), enabled: 'true' }])
        assert.equal(createRegion(document, { x: 1, y: 1 }, { x: 2, y: 2 }, options), null);
    document.layers[0].locked = true;
    assert.equal(createRegion(document, { x: 1, y: 1 }, { x: 2, y: 2 }, { layerId: id(1) }), null);
});

test('old projects keep omitted regions omitted on open and presence geometry rejects invalid elevation or bounds', () => {
    const document = fixture(); delete document.regions;
    assert.deepEqual(normalizeDocument(document), document);
    const region = { x: 2, y: 3, width: 3, height: 2, vertical: { bottom: -2, top: 5 } };
    assert.equal(validateRegionGeometry(document, region), true);
    assert.equal(regionContainsPoint(region, { x: 2, y: 3 }, -2), true);
    assert.equal(regionContainsPoint(region, { x: 5, y: 5 }, 5), true);
    assert.equal(regionContainsPoint(region, { x: 3, y: 4 }, 6), false);
    assert.equal(regionContainsPoint(region, { x: 1.99, y: 4 }), false);
    for (const patch of [{ width: 0 }, { x: -1 }, { y: Infinity }, { width: 100 }, { vertical: { bottom: 4, top: 3 } }, { vertical: { bottom: null } }, { vertical: { bottom: '0', top: 3 } }])
        assert.equal(validateRegionGeometry(document, { ...region, ...patch }), false, JSON.stringify(patch));
});

test('regions participate in selection, clamped movement and quarter-turn rotation while preserving the authored schema', () => {
    const document = fixture(), region = addRegion(document), refs = [{ kind: 'regions', id: region.id }];
    assert.deepEqual(selectionBounds(document, refs), { x: 2, y: 3, width: 3, height: 2 });
    assert.deepEqual(objectsInRectangle(document, { x: 3, y: 4, width: 1, height: 1 }), refs);
    assert.equal(rotateSelection(document, refs, 45), false);
    assert.equal(rotateSelection(document, refs, 90), true);
    assert.deepEqual(regionBounds(region), { x: 2.5, y: 2.5, width: 2, height: 3 });
    assert.equal('rotation' in region, false);
    assert.equal(translateSelection(document, refs, 100, 100), true);
    assert.deepEqual(regionBounds(region), { x: 38, y: 27, width: 2, height: 3 });
    assert.equal(fitsBounds(document), true);
    document.layers[0].locked = true;
    assert.equal(translateSelection(document, refs, -1, -1), false);
});

test('pressure plate produces first-token open and last-token close graphs with typed external targets', () => {
    const document = fixture(), region = addRegion(document), before = clone(region);
    assert.equal(configurePressurePlate(region, 'invalid'), false); assert.deepEqual(region, before);
    assert.equal(configurePressurePlate(region, id(11)), true);
    assert.equal(validateBlueprint(region.blueprint), region.blueprint);
    assert.deepEqual(simulateGraph(region.blueprint, 'presence:enter', 'occupied', 'occupied', {}, { eventContext: { count: 1 } }).actions.map(action => [action.type, action.targetState, action.target]),
        [['state', 'open', id(11)]]);
    assert.deepEqual(simulateGraph(region.blueprint, 'presence:exit', 'empty', 'empty', {}, { eventContext: { count: 0 } }).actions.map(action => [action.type, action.targetState, action.target]),
        [['state', 'closed', id(11)]]);
    assert.deepEqual(simulateGraph(region.blueprint, 'presence:enter', 'occupied', 'occupied', {}, { eventContext: { count: 2 } }).actions, []);
    assert.deepEqual(simulateGraph(region.blueprint, 'presence:exit', 'occupied', 'occupied', {}, { eventContext: { count: 1 } }).actions, []);
    assert.deepEqual(elementInstanceNode(regionInstance(region), 'region').outputs.map(port => port.id),
        ['presence:enter', 'presence:exit', 'destroy']);
    assert.equal('state' in region, false);
});

test('presence events are per-token events independent of occupancy and cannot author a region state or image', () => {
    const blueprint = defaultBlueprint('region');
    assert.deepEqual(blueprintEventsFor('region'), ['presence:enter', 'presence:exit', 'destroy']);
    for (const event of blueprintEventsFor('region')) {
        blueprint.graphs[event] = eventGraph(event);
        assert.deepEqual(simulateGraph(blueprint, event, 'occupied', 'occupied').trace, ['event']);
    }
    assert.equal(validateBlueprint(blueprint), blueprint);
    const invalidEvent = clone(blueprint); invalidEvent.graphs.interact = eventGraph('interact');
    assert.throws(() => validateBlueprint(invalidEvent), /event/);
    const art = clone(blueprint); art.states.empty.appearance = 'hidden';
    assert.throws(() => validateBlueprint(art), /image/);
    const state = clone(blueprint);
    state.graphs['presence:enter'].nodes.push({ id: 'set', type: 'state', targetState: 'occupied', x: 200, y: 50 });
    assert.throws(() => validateBlueprint(state), /state/);
    const graph = blueprint.graphs['presence:exit'];
    graph.nodes.push({ id: 'condition', type: 'condition', state: 'occupied', x: 200, y: 50 });
    connectNodes(graph, 'event', 'next', 'condition', { version: 2 });
    assert.equal(validateBlueprint(blueprint), blueprint);
    assert.deepEqual(simulateGraph(blueprint, 'presence:exit', 'occupied').trace, ['event', 'condition']);
});

test('group and layer copies remap region and door references while moves, deletion and undo preserve isolation', () => {
    const document = fixture(), region = addRegion(document);
    document.doors.push({ id: id(11), layerId: id(1), assetId: null, x1: 6, y1: 2, x2: 6, y2: 3, thickness: .18, state: 'closed' });
    configurePressurePlate(region, id(11));
    const door = document.doors[0]; door.blueprint = defaultBlueprint();
    door.blueprint.graphs.interact = eventGraph('interact');
    door.blueprint.graphs.interact.nodes.push({ id: 'region', type: 'reference', targetId: region.id, x: 400, y: 100 });
    door.blueprint.version = 2;
    const copy = duplicateSelection(document, [{ kind: 'regions', id: region.id }, { kind: 'doors', id: door.id }], 2, 0);
    assert.equal(copy.length, 2);
    const regionCopy = document.regions.find(row => row.id === copy[0].id), doorCopy = document.doors.find(row => row.id === copy[1].id);
    assert.equal(regionCopy.blueprint.graphs['presence:enter'].nodes.find(row => row.type === 'reference').targetId, doorCopy.id);
    assert.equal(doorCopy.blueprint.graphs.interact.nodes.find(row => row.type === 'reference').targetId, regionCopy.id);
    const layerCopy = duplicateLayer(document, id(1), 'Copy');
    assert.equal(layerCopy.refs.filter(ref => ref.kind === 'regions').length, 2);
    assert.equal(moveSelectionToLayer(document, [{ kind: 'regions', id: region.id }], id(2)), true);
    assert.deepEqual(layerContents(document, id(2)), [{ kind: 'regions', id: region.id }]);
    const before = clone(document), steps = history(document);
    removeObject(document, 'regions', region.id);
    assert.equal(document.regions.some(row => row.id === region.id), false);
    assert.equal(steps.commit(document), true); assert.deepEqual(steps.undo(), before);
});

test('removing a native light rewrites region Blueprint continuations just like other smart objects', () => {
    const document = fixture(), region = addRegion(document); region.blueprint = defaultBlueprint('region');
    document.lights.push({ id: id(12), layerId: id(1), x: 2, y: 3 });
    const graph = region.blueprint.graphs['presence:enter'] = eventGraph('presence:enter');
    graph.nodes.push({ id: 'light', type: 'light', targetId: id(12), enabled: true, x: 300, y: 50 },
        { id: 'flame', type: 'flame', enabled: false, x: 600, y: 50 });
    connectNodes(graph, 'event', 'next', 'light', { version: 2 }); connectNodes(graph, 'light', 'next', 'flame', { version: 2 });
    removeObject(document, 'lights', id(12));
    assert.deepEqual(region.blueprint.graphs['presence:enter'].edges, [{ from: 'event', output: 'next', to: 'flame', kind: 'execution' }]);
    assert.equal(validateBlueprint(region.blueprint), region.blueprint);
});

test('region copy budgets reject a group or layer atomically before exceeding the server region limit', () => {
    const document = fixture(), region = addRegion(document);
    document.regions = Array.from({ length: 128 }, (_, index) => ({ ...region, id: id(index + 100) }));
    const before = clone(document), refs = [{ kind: 'regions', id: document.regions[0].id }];
    assert.equal(createRegion(document, { x: 1, y: 1 }, { x: 2, y: 2 }, { layerId: id(1) }), null);
    assert.deepEqual(duplicateSelection(document, refs), []);
    assert.equal(duplicateLayer(document, id(1), 'Over budget'), null);
    assert.deepEqual(document, before);
});
