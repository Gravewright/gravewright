import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultBlueprint, eventGraph, connectNodes, validateBlueprint, simulateGraph } from './blueprint-model.js';

const target = '00000000-0000-4000-8000-000000000001';
function fixture(type = 'interact') {
    const blueprint = defaultBlueprint('lever'), graph = eventGraph('presence:enter');
    blueprint.graphs['presence:enter'] = graph;
    graph.nodes.push({ id: 'reference', type: 'reference', targetId: target, x: 20, y: 200 },
        { id: 'action', type, ...(type === 'state' ? { targetState: 'on' } : {}), x: 400, y: 200 });
    connectNodes(graph, 'event', 'next', 'action');
    connectNodes(graph, 'reference', 'door', 'action', { input: 'target' });
    return blueprint;
}

test('an explicit target interaction is previewed without inventing target state or image changes', () => {
    const blueprint = fixture(), before = structuredClone(blueprint), states = { [target]: 'off' };
    validateBlueprint(blueprint);
    const result = simulateGraph(blueprint, 'presence:enter', 'off', 'off', states);
    assert.deepEqual(result.actions.map(action => [action.type, action.target]), [['interact', target]]);
    assert.deepEqual(states, { [target]: 'off' });
    assert.deepEqual(blueprint, before);
    const group = blueprint.graphs['presence:enter'].nodes.find(node => node.id === 'reference');
    Object.assign(group, { type: 'elementGroup', memberType: 'element', name: 'Targets', targetIds: [target] });
    delete group.targetId;
    blueprint.graphs['presence:enter'].edges.find(edge => edge.kind === 'data').output = 'targets';
    validateBlueprint(blueprint);
    assert.deepEqual(simulateGraph(blueprint, 'presence:enter', 'off').actions[0].target, [target]);
});

test('state actions stay independent of explicit interaction and new interaction fields are strict', () => {
    const blueprint = fixture('state');
    assert.deepEqual(simulateGraph(blueprint, 'presence:enter', 'off').actions.map(action => action.type), ['state']);
    const interaction = fixture(), action = interaction.graphs['presence:enter'].nodes.find(node => node.id === 'action');
    action.event = 'change';
    assert.throws(() => validateBlueprint(interaction), /node/);
});
