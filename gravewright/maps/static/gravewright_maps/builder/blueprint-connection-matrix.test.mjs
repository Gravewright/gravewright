import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { blueprintContract, connectNodes, defaultBlueprint, eventGraph, validateBlueprint } from './blueprint-model.js';

// Shared expectations specify authored semantics independently of either runtime.
const { resources, providers, consumers } = JSON.parse(readFileSync(new URL('../../../../../tests/fixtures/map_builder_connections.json', import.meta.url), 'utf8'));
const node = (type, fields = {}) => ({ id: type, type, x: 20, y: 20, ...fields });

test('the shared matrix covers every registered value input and output', () => {
    const ports = direction => Object.entries(blueprintContract.nodes).flatMap(([type, contract]) =>
        contract[direction].filter(port => port.kind === 'value').map(port => `${type}.${port.id}`)).sort();
    assert.deepEqual([...new Set(consumers.map(([type, port]) => `${type}.${port}`))].sort(), ports('inputs'));
    assert.deepEqual([...new Set(providers.map(([type, port]) => `${type}.${port}`))].sort(), ports('outputs'));
});

for (const [type, input, accepted, parameters] of consumers) {
    test(`${type}.${input} accepts exactly ${accepted.join(', ')} from ${providers.length} producer variants`, () => {
        for (const [producer, output, produced, configuration] of providers) {
            const blueprint = defaultBlueprint('lever'), graph = eventGraph('interact');
            blueprint.graphs.interact = graph;
            graph.nodes.push(node(producer, { ...configuration, id: 'producer' }), node(type, { ...parameters, id: 'consumer' }));
            const before = structuredClone(graph), label = `${producer} (${produced}) -> ${type}.${input}`;
            if (accepted.includes(produced)) {
                connectNodes(graph, 'producer', output, 'consumer', { input });
                validateBlueprint(blueprint, resources);
                assert.deepEqual(graph.edges, [{ from: 'producer', output, to: 'consumer', input, kind: 'data' }], label);
                assert.throws(() => connectNodes(graph, 'producer', output, 'consumer', { input }), /one connection/, label);
                assert.equal(graph.edges.length, 1, label);
            } else {
                assert.throws(() => connectNodes(graph, 'producer', output, 'consumer', { input }), /connection/, label);
                assert.deepEqual(graph, before, label);
            }
        }
    });
}

test('value producers cannot acquire Target sockets on event or untargeted presentation nodes', () => {
    for (const [type, parameters] of [['event', { event: 'interact' }],
        ['showMessage', { text: 'Message', audience: { scope: 'trigger' } }]]) {
        for (const [producer, output, , configuration] of providers) {
            const graph = { nodes: [node(producer, { ...configuration, id: 'producer' }), node(type, { ...parameters, id: 'consumer' })], edges: [] };
            assert.throws(() => connectNodes(graph, 'producer', output, 'consumer', { input: 'target' }), /connection/);
            assert.deepEqual(graph.edges, []);
        }
    }
});
