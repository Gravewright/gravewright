import test from 'node:test';
import assert from 'node:assert/strict';
import { blueprintStatesFor, connectNodes, dataInputs, defaultBlueprint, eventGraph, simulateGraph, validateBlueprint } from './blueprint-model.js';

const assetId = '00000000-0000-4000-8000-000000000001';
const targetId = '00000000-0000-4000-8000-000000000002';
const ownerId = '00000000-0000-4000-8000-000000000003';
const secondTargetId = '00000000-0000-4000-8000-000000000004';
const resources = { assets: [], materials: [{ id: assetId, name: 'Target artwork' }] };
const owners = [
    { id: ownerId, kind: 'door' }, { id: ownerId, kind: 'lever' }, { id: ownerId, kind: 'torch' },
    { id: ownerId, kind: 'lever', empty: true }, { id: ownerId, kind: 'region' },
];

function fixture(owner, appearance = 'asset', target = null) {
    const blueprint = defaultBlueprint(owner.kind), event = owner.kind === 'door' ? 'interact' : 'presence:enter';
    const graph = eventGraph(event);
    blueprint.graphs[event] = graph;
    graph.nodes.push({ id: 'sprite', type: 'sprite', appearance, ...(appearance === 'asset' ? { assetId } : {}), x: 400, y: 200 });
    connectNodes(graph, 'event', 'next', 'sprite');
    if (target) {
        const group = Array.isArray(target);
        graph.nodes.push({ id: 'targets', type: group ? 'elementGroup' : 'reference', x: 20, y: 400,
            ...(group ? { name: 'Artwork targets', memberType: 'element', targetIds: target } : { targetId: target }) });
        connectNodes(graph, 'targets', group ? 'targets' : 'door', 'sprite', { input: 'target' });
    }
    return { blueprint, event, graph };
}

test('sprite Target accepts element references and groups while rejecting unrelated resource types', () => {
    const input = dataInputs({ type: 'sprite' });
    assert.deepEqual(input.map(port => [port.id, port.acceptedTypes]), [['target', ['element', 'elementset']]]);
    for (const [type, fields, output] of [
        ['lightReference', { targetId }, 'light'], ['soundReference', { trackId: targetId }, 'sound'],
        ['getVariable', { scope: 'element', name: 'value', valueType: 'text', default: '' }, 'value'],
    ]) {
        const { graph } = fixture(owners[3]);
        graph.nodes.push({ id: 'wrong', type, x: 0, y: 0, ...fields });
        const before = structuredClone(graph);
        assert.throws(() => connectNodes(graph, 'wrong', output, 'sprite', { input: 'target' }), /connection/);
        assert.deepEqual(graph, before);
    }
});

test('every owner can author sprite actions with every appearance and self, reference or group targets', () => {
    for (const owner of owners) for (const appearance of ['inherit', 'hidden', 'asset'])
        for (const target of [null, targetId, [targetId, secondTargetId]]) {
            const { blueprint, event, graph } = fixture(owner, appearance, target);
            const label = `${owner.empty ? 'empty' : owner.kind}: ${appearance}, ${JSON.stringify(target)}`;
            assert.equal(validateBlueprint(blueprint, { ...resources, element: owner }), blueprint, label);
            const before = structuredClone(blueprint);
            const current = blueprintStatesFor(owner.kind)[0], result = simulateGraph(blueprint, event, current);
            assert.equal(result.actions.length, 1, label);
            assert.deepEqual(result.actions[0], { ...graph.nodes.find(node => node.id === 'sprite'), ...(target ? { target } : {}) }, label);
            assert.deepEqual(blueprint, before, label);
        }
});

test('Empty actions may be drafted before choosing another artwork target', () => {
    const owner = owners[3], { blueprint, graph } = fixture(owner);
    graph.nodes.push({ id: 'appearance', type: 'setAppearance', assetId, x: 800, y: 200 });
    connectNodes(graph, 'sprite', 'next', 'appearance');
    assert.equal(validateBlueprint(blueprint, { ...resources, element: owner }), blueprint);
    // Explicitly naming an image-less member remains valid authored logic; the
    // authoritative runtime skips that target and reports its incompatibility.
    graph.nodes.push({ id: 'self', type: 'reference', targetId: ownerId, x: 800, y: 400 });
    connectNodes(graph, 'self', 'door', 'appearance', { input: 'target' });
    assert.equal(validateBlueprint(blueprint, { ...resources, element: owner }), blueprint);
});

test('sprite actions accept material artwork without broadening state appearance ownership', () => {
    const owner = owners[1], { blueprint } = fixture(owner);
    validateBlueprint(blueprint, { ...resources, element: owner });
    blueprint.states.off = { appearance: 'asset', assetId };
    assert.throws(() => validateBlueprint(blueprint, { ...resources, element: owner }), /configured state/);
    validateBlueprint(blueprint, { assets: resources.materials, element: owner });
    assert.throws(() => validateBlueprint(blueprint, { assets: resources.materials, element: owners[3] }), /Empty Objects cannot receive images/);
});

test('targeted sprite image resources are still required and unknown action fields remain invalid', () => {
    const owner = owners[3], { blueprint, graph } = fixture(owner, 'asset', targetId);
    assert.throws(() => validateBlueprint(blueprint, { element: owner }), /Change sprite/);
    graph.nodes.find(node => node.id === 'sprite').targetId = targetId;
    assert.throws(() => validateBlueprint(blueprint, { ...resources, element: owner }), /node/);
});
