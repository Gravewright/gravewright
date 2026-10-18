import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultBlueprint, upgradeBlueprint, eventGraph, connectNodes, validateBlueprint, simulateGraph, dataInputs, dataOutputs,
    acceptsDataType, eventContextProperties, eventContextTypes, validateEventContextSnapshot } from './blueprint-model.js';
import { newDocument, normalizeDocument, duplicateSelection, removeObject } from './model.js';

const id = number => `00000000-0000-4000-8000-${String(number).padStart(12, '0')}`;
const event = 'signal:FixtureInteractClosed', resources = { lights: [{ id: id(10) }, { id: id(11) }], sounds: [{ id: id(20) }, { id: id(21) }] };
function fixture(nodes = []) {
    const blueprint = upgradeBlueprint(defaultBlueprint()), graph = eventGraph(event);
    blueprint.graphs[event] = graph;
    graph.nodes.push(...nodes.map((node, index) => ({ x: 300 + index * 300, y: 60, ...node })));
    return { blueprint, graph };
}
const wire = (graph, from, output, to, input) => connectNodes(graph, from, output, to, { version: 2, ...(input ? { input } : {}) });
const run = (blueprint, context = {}, elements = {}) => simulateGraph(blueprint, event, 'closed', 'open', elements, context);
const group = (memberType = 'element', targetIds = [id(2), id(1)]) => ({ id: 'group', type: 'elementGroup', name: 'Ordered targets', memberType, targetIds });

test('group ports are typed sets and only compatible action Targets accept them', () => {
    for (const [memberType, type] of [['element', 'elementset'], ['light', 'lightset'], ['sound', 'soundset']]) {
        assert.deepEqual(dataOutputs(group(memberType)), [{ id: 'targets', kind: 'value', type, label: 'Targets' }]);
    }
    for (const type of ['state', 'interact', 'flame', 'reveal', 'barrier', 'emitEvent', 'setInteraction', 'setRegion']) {
        const target = dataInputs({ type }).find(row => row.id === 'target');
        assert.equal(acceptsDataType(target, 'element'), true);
        assert.equal(acceptsDataType(target, 'elementset'), true);
        assert.equal(acceptsDataType(target, 'lightset'), false);
    }
    assert.equal(acceptsDataType(dataInputs({ type: 'property' })[0], 'elementset'), false);
    assert.equal(acceptsDataType(undefined, 'element'), false);
    for (const type of ['move', 'rotate']) for (const input of ['element', 'elementset', 'light', 'lightset']) {
        assert.equal(acceptsDataType(dataInputs({ type })[0], input), true);
    }
});

test('an ordered group becomes one queued action with an independent target array', () => {
    const { blueprint, graph } = fixture([group(), { id: 'move', type: 'move', dx: .25, dy: -2 }]);
    wire(graph, 'event', 'next', 'move'); wire(graph, 'group', 'targets', 'move', 'target');
    validateBlueprint(blueprint);
    const result = run(blueprint);
    assert.deepEqual(result.trace, ['event', 'move', 'group']);
    assert.deepEqual(result.actions[0].target, [id(2), id(1)]);
    assert.deepEqual(result.values.group, [id(2), id(1)]);
    result.actions[0].target.reverse(); result.values.group.push(id(3));
    assert.deepEqual(graph.nodes[1].targetIds, [id(2), id(1)]);
    assert.deepEqual(run(blueprint).actions[0].target, [id(2), id(1)]);
});

test('groups require a bounded human name and one to thirty-two unique UUID members', () => {
    const { blueprint, graph } = fixture([group()]), original = structuredClone(graph.nodes[1]);
    for (const patch of [{ name: '' }, { name: ' ' }, { name: 'a'.repeat(81) }, { name: 'bad\0name' }, { name: null },
        { memberType: 'token' }, { targetIds: [] }, { targetIds: Array(2) }, { targetIds: null }, { targetIds: ['bad'] },
        { targetIds: [id(1), id(1)] }, { targetIds: [id(1), id(1).toUpperCase()] }, { targetIds: [id(1) + '\n'] },
        { targetIds: Array.from({ length: 33 }, (_, index) => id(index + 1)) }, { extra: true }]) {
        graph.nodes[1] = { ...original, ...patch };
        assert.throws(() => validateBlueprint(blueprint), /group|node/);
    }
    graph.nodes[1] = { ...original, name: '🔥'.repeat(80), targetIds: Array.from({ length: 32 }, (_, index) => id(index + 1)) };
    validateBlueprint(blueprint);
});

test('light and sound references keep fallback bindings and accept their corresponding typed groups', () => {
    for (const memberType of ['light', 'sound']) {
        const targetIds = memberType === 'light' ? [id(11), id(10)] : [id(21), id(20)];
        const action = memberType === 'light' ? { id: 'action', type: 'light', targetId: id(10), enabled: false }
            : { id: 'action', type: 'sound', trackId: id(20), volume: .5 };
        const { blueprint, graph } = fixture([group(memberType, targetIds), action]);
        wire(graph, 'event', 'next', 'action'); wire(graph, 'group', 'targets', 'action', 'target');
        validateBlueprint(blueprint, resources);
        assert.deepEqual(run(blueprint).actions[0].target, targetIds);
        const reference = memberType === 'light' ? { id: 'ref', type: 'lightReference', targetId: id(11), x: 100, y: 500 }
            : { id: 'ref', type: 'soundReference', trackId: id(21), x: 100, y: 500 };
        graph.nodes.push(reference); graph.edges = graph.edges.filter(edge => edge.kind !== 'data');
        wire(graph, 'ref', memberType, 'action', 'target');
        validateBlueprint(blueprint, resources);
        assert.equal(run(blueprint).actions[0].target, targetIds[0]);
        assert.throws(() => validateBlueprint(blueprint), /light|sound/);
        delete graph.nodes[2][memberType === 'light' ? 'targetId' : 'trackId'];
        assert.throws(() => validateBlueprint(blueprint, resources), /node/);
    }
});

test('typed resources cannot connect to unrelated targets or replace scalar state inputs', () => {
    const { graph } = fixture([group('sound', [id(20)]), { id: 'move', type: 'move', dx: 1, dy: 0 },
        { id: 'property', type: 'property', property: 'state' }, { id: 'light', type: 'lightReference', targetId: id(10) }]);
    assert.throws(() => wire(graph, 'group', 'targets', 'move', 'target'), /connection/);
    assert.throws(() => wire(graph, 'group', 'targets', 'property', 'target'), /connection/);
    assert.throws(() => wire(graph, 'light', 'light', 'property', 'target'), /connection/);
});

test('new actions validate finite geometry and strict flags but leave native geometry application to the server', () => {
    for (const action of [{ type: 'move', dx: -1000, dy: 1000 }, { type: 'rotate', degrees: -36000 },
        { type: 'rotate', degrees: 45 }, { type: 'setInteraction', enabled: false }, { type: 'setRegion', enabled: true }]) {
        const { blueprint, graph } = fixture([{ ...action, id: 'action' }]);
        wire(graph, 'event', 'next', 'action'); validateBlueprint(blueprint);
        assert.deepEqual(run(blueprint).actions.map(node => node.type), [action.type]);
        assert.equal(Object.hasOwn(run(blueprint).actions[0], 'target'), false);
    }
    for (const action of [{ type: 'move', dx: '1', dy: 0 }, { type: 'move', dx: 1000.1, dy: 0 }, { type: 'move', dx: 0, dy: Infinity },
        { type: 'rotate', degrees: 36000.1 }, { type: 'rotate', degrees: true }, { type: 'rotate', degrees: NaN },
        { type: 'setInteraction', enabled: 0 }, { type: 'setRegion', enabled: 'true' }]) {
        const { blueprint } = fixture([{ ...action, id: 'action' }]);
        assert.throws(() => validateBlueprint(blueprint), /action/);
    }
});

function contextBlueprint(property) {
    const type = eventContextTypes[property], scalar = type !== 'state';
    const { blueprint, graph } = fixture([{ id: 'read', type: 'eventContext', property }, scalar
        ? { id: 'use', type: 'setVariable', scope: 'element', name: 'Result', valueType: type, value: type === 'text' ? '' : type === 'boolean' ? false : 0 }
        : { id: 'use', type: 'compare', state: 'closed' }, ...scalar ? [] : [{ id: 'check', type: 'condition', state: 'closed' }]]);
    wire(graph, 'read', 'value', 'use', 'value');
    if (scalar) wire(graph, 'event', 'next', 'use');
    else { wire(graph, 'event', 'next', 'check'); wire(graph, 'use', 'result', 'check', 'test'); }
    return blueprint;
}
test('Event context exposes readonly types and safe defaults, with current graph state overriding metadata', () => {
    const defaults = { event, sourceId: '', userId: '', userName: '', tokenId: '', actorId: '', presence: '', count: 0, hasToken: false, state: 'closed', previous: 'open' };
    for (const property of eventContextProperties) {
        const blueprint = contextBlueprint(property);
        validateBlueprint(blueprint);
        assert.equal(dataOutputs(blueprint.graphs[event].nodes[1])[0].type, eventContextTypes[property]);
        assert.equal(run(blueprint).values.read, defaults[property]);
    }
    for (const [property, expected] of [['event', event], ['state', 'closed'], ['previous', 'open']]) {
        assert.equal(run(contextBlueprint(property), { eventContext: { event: 'spoofed', state: 'locked', previous: 'locked' } }).values.read, expected);
    }
});

test('Event context supplies original trigger identity, token count and derived hasToken only through private preview metadata', () => {
    const metadata = { sourceId: id(1), userId: id(2), userName: 'Synthetic GM', tokenId: id(3), actorId: id(4), presence: 'enter', count: 2 };
    const before = structuredClone(metadata);
    for (const [property, value] of Object.entries(metadata)) assert.equal(run(contextBlueprint(property), { eventContext: metadata }).values.read, value);
    assert.equal(run(contextBlueprint('hasToken'), { eventContext: metadata }).values.read, true);
    assert.equal(run(contextBlueprint('hasToken'), { eventContext: { ...metadata, hasToken: false } }).values.read, false);
    assert.deepEqual(metadata, before);
});

test('Event context rejects arbitrary payloads, invalid count/types and nonconfigured properties', () => {
    for (const snapshot of [null, [], { role: 'gm' }, { count: true }, { count: -1 }, { count: .5 }, { count: 1000001 },
        { tokenId: null }, { hasToken: 'true' }, { userName: '🔥'.repeat(257) }, { state: 'arbitrary' }]) {
        assert.throws(() => validateEventContextSnapshot(snapshot), /event context/);
    }
    const { blueprint } = fixture([{ id: 'read', type: 'eventContext', property: 'role' }]);
    assert.throws(() => validateBlueprint(blueprint), /event context/);
});

test('group and context values remain lazy behind Delay and do not execute receiving graphs', () => {
    const { blueprint, graph } = fixture([group(), { id: 'wait', type: 'delay', seconds: 1 }, { id: 'move', type: 'move', dx: 1, dy: 1 }]);
    wire(graph, 'event', 'next', 'wait'); wire(graph, 'wait', 'next', 'move'); wire(graph, 'group', 'targets', 'move', 'target');
    const result = run(blueprint);
    assert.deepEqual(result.trace, ['event', 'wait']); assert.deepEqual(result.values, {}); assert.deepEqual(result.actions, []);
});

test('new nodes retain version two boundaries while ordinary image references can safely read no state', () => {
    for (const node of [group(), { id: 'action', type: 'move', dx: 1, dy: 1 }, { id: 'read', type: 'eventContext', property: 'event' }]) {
        const { blueprint } = fixture([node]); blueprint.version = 1;
        assert.throws(() => validateBlueprint(blueprint), /Unsupported/);
    }
    const { blueprint, graph } = fixture([{ id: 'image', type: 'reference', targetId: id(1) }, { id: 'read', type: 'property', property: 'state' },
        { id: 'compare', type: 'compare', state: 'open' }, { id: 'check', type: 'condition', state: 'open' }]);
    wire(graph, 'image', 'door', 'read', 'target'); wire(graph, 'read', 'value', 'compare', 'value');
    wire(graph, 'compare', 'result', 'check', 'test'); wire(graph, 'event', 'next', 'check');
    validateBlueprint(blueprint);
    assert.equal(run(blueprint, {}, { [id(1)]: null }).values.read, null);
    assert.equal(run(blueprint, {}, { [id(1)]: null }).values.compare, false);
});

test('source copies remap explicit generic image/light/group targets while authored UUID text and campaign sounds stay intact', () => {
    const document = newDocument(), layerId = document.layers[0].id;
    const { blueprint, graph } = fixture([group('element', [id(2), id(9)]), { ...group('light', [id(10)]), id: 'lights' },
        { ...group('sound', [id(20)]), id: 'sounds' }, { id: 'image', type: 'reference', targetId: id(2) },
        { id: 'light', type: 'lightReference', targetId: id(10) }, { id: 'text', type: 'getVariable', scope: 'element', name: 'Authored', valueType: 'text', default: id(2) }]);
    document.decorations.push({ id: id(1), layerId, assetId: id(30), x: 4, y: 4, width: 1, height: 1, rotation: 0,
        lever: { state: 'off' }, interactionEnabled: false, blueprint },
    { id: id(2), layerId, assetId: id(30), x: 6, y: 4, width: 1, height: 1, rotation: 0 });
    document.lights.push({ id: id(10), layerId, x: 8, y: 4 });
    const originals = structuredClone(document), copies = duplicateSelection(document,
        [{ kind: 'decorations', id: id(1) }, { kind: 'decorations', id: id(2) }, { kind: 'lights', id: id(10) }], 0, 3);
    assert.equal(copies.length, 3);
    const duplicate = document.decorations.find(row => row.id === copies[0].id), nodes = duplicate.blueprint.graphs[event].nodes;
    assert.deepEqual(nodes.find(row => row.id === 'group').targetIds, [copies[1].id, id(9)]);
    assert.deepEqual(nodes.find(row => row.id === 'lights').targetIds, [copies[2].id]);
    assert.deepEqual(nodes.find(row => row.id === 'sounds').targetIds, [id(20)]);
    assert.equal(nodes.find(row => row.id === 'image').targetId, copies[1].id);
    assert.equal(nodes.find(row => row.id === 'light').targetId, copies[2].id);
    assert.equal(nodes.find(row => row.id === 'text').default, id(2));
    assert.equal(duplicate.interactionEnabled, false);
    assert.deepEqual(graph, originals.decorations[0].blueprint.graphs[event]);
});

test('opening source documents preserves omitted interaction flags and rejects coercion without changing the original', () => {
    const document = newDocument(); document.decorations.push({ id: id(1) }); document.doors.push({ id: id(2), interactionEnabled: false });
    const before = structuredClone(document), normalized = normalizeDocument(document);
    assert.equal(Object.hasOwn(normalized.decorations[0], 'interactionEnabled'), false);
    assert.equal(normalized.doors[0].interactionEnabled, false);
    document.decorations[0].interactionEnabled = 'false';
    assert.throws(() => normalizeDocument(document), /interaction/);
    delete document.decorations[0].interactionEnabled; assert.deepEqual(document, before);
});

test('deleting a fallback light bridges only execution and keeps unrelated multi-input data wires', () => {
    const document = newDocument(), { blueprint, graph } = fixture([
        { id: 'target', type: 'lightReference', targetId: id(11) }, { id: 'light', type: 'light', targetId: id(10), enabled: true },
        { id: 'read', type: 'getVariable', scope: 'element', name: 'Ready', valueType: 'boolean', default: true },
        { id: 'all', type: 'all' }, { id: 'check', type: 'condition', state: 'closed' }]);
    wire(graph, 'event', 'next', 'light'); wire(graph, 'light', 'next', 'check'); wire(graph, 'target', 'light', 'light', 'target');
    wire(graph, 'read', 'value', 'all', 'a'); wire(graph, 'read', 'value', 'all', 'b'); wire(graph, 'all', 'result', 'check', 'test');
    document.doors.push({ id: id(1), blueprint }); document.lights.push({ id: id(10) }, { id: id(11) });
    removeObject(document, 'lights', id(10));
    const updated = document.doors[0].blueprint;
    validateBlueprint(updated);
    assert.deepEqual(updated.graphs[event].edges.filter(edge => edge.kind === 'execution'),
        [{ from: 'event', output: 'next', to: 'check', kind: 'execution' }]);
    assert.equal(updated.graphs[event].edges.filter(edge => edge.to === 'all').length, 2);
    assert.equal(updated.graphs[event].edges.some(edge => edge.from === 'target'), false);
    assert.equal(updated.graphs[event].nodes.some(node => node.id === 'target'), true);
});

test('deleting a referenced light preserves stale groups, refs and connected targets instead of changing them to Self', () => {
    const document = newDocument(), { blueprint, graph } = fixture([group('light', [id(10)]),
        { id: 'target', type: 'lightReference', targetId: id(10) }, { id: 'move', type: 'move', dx: 1, dy: 0 }]);
    wire(graph, 'event', 'next', 'move'); wire(graph, 'group', 'targets', 'move', 'target');
    document.doors.push({ id: id(1), blueprint }); document.lights.push({ id: id(10) });
    const before = structuredClone(blueprint);
    removeObject(document, 'lights', id(10));
    assert.deepEqual(document.doors[0].blueprint, before);
    validateBlueprint(blueprint);
    assert.deepEqual(run(blueprint).actions[0].target, [id(10)]);
});
