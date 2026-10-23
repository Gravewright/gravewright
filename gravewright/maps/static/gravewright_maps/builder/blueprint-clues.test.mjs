import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultBlueprint, eventGraph, connectNodes, validateBlueprint, simulateGraph, blueprintContract,
    dataInputs, dataOutputs, nodeOutputs, acceptsDataType } from './blueprint-model.js';
import { sceneNetwork, networkPage } from './network-model.js';
import { createRunFormatter } from './run-format.js';
import { captureTemplate, resolveTemplate, templateParameterOptions, validateTemplateDefinition } from './blueprint-templates.js';

const id = number => `00000000-0000-4000-8000-${String(number).padStart(12, '0')}`;
const clue = { id: id(1), name: '<img src=x> Authored clue', segments: 8, value: 4, visibility: 'gm', sceneId: null };
const catalog = { clues: [clue, { ...clue, id: id(2), name: 'Another clue' }] };
const action = (patch = {}) => ({ id: 'clue', type: 'clueControl', clueId: id(1), action: 'advance', amount: 1, ...patch });
function fixture(nodes = [action()]) {
    const blueprint = defaultBlueprint('lever'), graph = blueprint.graphs.interact = eventGraph('interact');
    graph.nodes.push(...nodes.map((row, index) => ({ x: 300 + index * 300, y: 60, ...row })));
    connectNodes(graph, 'event', 'next', nodes.at(-1).id);
    return { blueprint, graph };
}
const preview = (blueprint, context = {}) => simulateGraph(blueprint, 'interact', 'off', 'off', {}, context);

test('clue control has execution continuation and a single number input without an implicit target', () => {
    const contract = blueprintContract.nodes.clueControl;
    assert.equal(contract.category, 'action'); assert.equal(contract.label, 'Control clue');
    assert.deepEqual(contract.inputs.filter(port => port.kind === 'execution').map(port => port.id), ['input']);
    assert.deepEqual(dataInputs(action()), [{ id: 'amount', kind: 'value', type: 'number', label: 'Amount' }]);
    assert.deepEqual(dataOutputs(action()), []); assert.deepEqual(nodeOutputs(action()), ['next']);
    const amount = dataInputs(action())[0];
    assert.equal(acceptsDataType(amount, 'number'), true);
    for (const type of ['boolean', 'text', 'element', 'elementset', 'state']) assert.equal(acceptsDataType(amount, type), false);
    const { graph } = fixture([{ id: 'source', type: 'getVariable', scope: 'element', name: 'Amount', valueType: 'boolean', default: true }, action()]);
    assert.throws(() => connectNodes(graph, 'source', 'value', 'clue', { input: 'amount' }), /connection/);
});

test('clue configuration requires exact fields, a UUID, a supported action and an integer from zero to twenty-four', () => {
    for (const operation of ['advance', 'reduce', 'set', 'reset', 'reveal', 'hide']) for (const amount of [0, 1, 24])
        validateBlueprint(fixture([action({ action: operation, amount })]).blueprint, catalog);
    const invalid = [{ clueId: 'bad' }, { clueId: id(1) + '\n' }, { clueId: null }, { action: 'stop' },
        { amount: -1 }, { amount: 25 }, { amount: .5 }, { amount: true }, { amount: '1' }, { amount: NaN },
        { amount: Infinity }, { target: id(2) }, { players: true }];
    for (const patch of invalid) assert.throws(() => validateBlueprint(fixture([action(patch)]).blueprint, catalog), /clue|node/);
    for (const key of ['clueId', 'action', 'amount']) {
        const node = action(); delete node[key];
        assert.throws(() => validateBlueprint(fixture([node]).blueprint, catalog), /node/);
    }
    const old = fixture().blueprint; old.version = 1;
    assert.throws(() => validateBlueprint(old, catalog), /version/);
});

test('provided clue catalogs reject stale selections and accept canonical UUID casing', () => {
    const { blueprint } = fixture();
    validateBlueprint(blueprint);
    assert.throws(() => validateBlueprint(blueprint, { clues: [] }), /Choose a clue/);
    assert.throws(() => validateBlueprint(blueprint, { clues: [{ ...clue, id: id(9) }] }), /Choose a clue/);
    validateBlueprint(blueprint, catalog);
    const letters = 'abcdefab-cdef-4abc-8def-abcdefabcdef';
    validateBlueprint(fixture([action({ clueId: letters.toUpperCase() })]).blueprint, { clues: [{ id: letters }] });
});

test('clue previews queue independent actions in execution order without changing any clue or graph', () => {
    const { blueprint, graph } = fixture([action(), action({ id: 'reduce', action: 'reduce', amount: 2 }),
        action({ id: 'set', action: 'set', amount: 24 }), action({ id: 'reset', action: 'reset' })]);
    graph.edges = [];
    let previous = 'event';
    for (const node of graph.nodes.slice(1)) { connectNodes(graph, previous, 'next', node.id); previous = node.id; }
    const original = structuredClone({ blueprint, catalog });
    const first = preview(blueprint, { clues: catalog.clues }), second = preview(blueprint, { clues: catalog.clues });
    assert.deepEqual(first.actions.map(row => [row.action, row.amount]), [['advance', 1], ['reduce', 2], ['set', 24], ['reset', 1]]);
    assert.deepEqual(first.trace, ['event', 'clue', 'reduce', 'set', 'reset']);
    first.actions[0].clueId = id(9); first.actions[1].amount = 0;
    assert.deepEqual(second.actions.map(row => row.clueId), [id(1), id(1), id(1), id(1)]);
    assert.deepEqual({ blueprint, catalog }, original);
    assert.equal(Object.hasOwn(first, 'clues'), false); assert.equal(Object.hasOwn(first, 'effects'), false);
});

test('connected amounts replace the saved fallback and reject invalid runtime numbers', () => {
    const variable = { id: 'amount', type: 'getVariable', scope: 'element', name: 'Amount', valueType: 'number', default: 2 };
    const { blueprint, graph } = fixture([variable, action({ amount: 1 })]);
    connectNodes(graph, 'amount', 'value', 'clue', { input: 'amount' });
    validateBlueprint(blueprint, catalog);
    assert.equal(preview(blueprint).actions[0].amount, 2);
    for (const amount of [0, 24]) assert.equal(preview(blueprint, { variables: { element: { Amount: { type: 'number', value: amount } } } }).actions[0].amount, amount);
    for (const amount of [-1, 25, 2.5]) assert.throws(() => preview(blueprint,
        { variables: { element: { Amount: { type: 'number', value: amount } } } }), /integer from 0 to 24/);
    assert.equal(graph.nodes.at(-1).amount, 1);
    graph.edges = graph.edges.filter(edge => edge.kind !== 'data');
    assert.equal(preview(blueprint).actions[0].amount, 1);
});

test('reset, reveal and hide ignore amount connections without evaluating an unavailable value', () => {
    const variable = { id: 'amount', type: 'getVariable', scope: 'element', name: 'Amount', valueType: 'number', default: -1 };
    for (const operation of ['reset', 'reveal', 'hide']) {
        const { blueprint, graph } = fixture([variable, action({ action: operation })]);
        connectNodes(graph, 'amount', 'value', 'clue', { input: 'amount' });
        const result = preview(blueprint, { variables: { element: { Amount: { type: 'text', value: 'Wrong current type' } } } });
        assert.deepEqual(result.trace, ['event', 'clue']); assert.deepEqual(result.values, {});
        assert.equal(result.actions[0].amount, 1); assert.equal(result.actions[0].action, operation);
    }
});

test('templates use clue bindings and expose only the amount scalar while preserving authored text', () => {
    const { blueprint } = fixture([action(), action({ id: 'second', action: 'set', amount: 3 }),
        { id: 'message', type: 'showMessage', text: id(1), audience: { scope: 'trigger' } }]);
    const original = structuredClone(blueprint), options = templateParameterOptions(blueprint);
    const expose = options.filter(row => row.path.at(-1) === 'amount');
    assert.equal(expose.length, 2);
    assert.equal(options.some(row => ['clueId', 'action'].includes(row.path.at(-1))), false);
    const definition = captureTemplate(blueprint, { catalog, expose });
    assert.deepEqual(definition.bindings.map(row => row.type), ['clue']);
    const [binding] = definition.bindings;
    assert.deepEqual(definition.blueprint.graphs.interact.nodes[1].clueId, { binding: binding.id });
    assert.deepEqual(definition.blueprint.graphs.interact.nodes[2].clueId, { binding: binding.id });
    assert.equal(definition.blueprint.graphs.interact.nodes[3].text, id(1));
    validateTemplateDefinition(definition);
    const [parameter] = definition.parameters;
    const first = resolveTemplate(definition, { catalog, bindings: { [binding.id]: id(2) }, parameters: { [parameter.id]: 24 } });
    const second = resolveTemplate(definition, { catalog, bindings: { [binding.id]: id(1) } });
    assert.equal(first.graphs.interact.nodes[1].clueId, id(2)); assert.equal(first.graphs.interact.nodes[1].amount, 24);
    assert.equal(second.graphs.interact.nodes[1].clueId, id(1)); assert.equal(second.graphs.interact.nodes[1].amount, 1);
    assert.deepEqual(blueprint, original);
    for (const amount of [-1, 25, .5, '1', true]) assert.throws(() => resolveTemplate(definition,
        { catalog, bindings: { [binding.id]: id(2) }, parameters: { [parameter.id]: amount } }), /parameter|clue/);
    for (const resource of [id(9), null]) assert.throws(() => resolveTemplate(definition,
        { catalog, bindings: { [binding.id]: resource } }), /binding|resource/);
    assert.throws(() => resolveTemplate(definition, { catalog: { clues: [] }, bindings: { [binding.id]: id(1) } }), /resource/);
    const wrong = structuredClone(definition); wrong.bindings[0].type = 'sound';
    assert.throws(() => validateTemplateDefinition(wrong), /binding/);
});

test('reset, reveal and hide templates retain saved amounts without exposing unused parameters', () => {
    for (const operation of ['reset', 'reveal', 'hide']) {
        const { blueprint } = fixture([action({ action: operation, amount: 7 })]);
        assert.deepEqual(templateParameterOptions(blueprint), []);
        const definition = captureTemplate(blueprint, { catalog });
        assert.deepEqual(definition.parameters, []);
        const [binding] = definition.bindings;
        const resolved = resolveTemplate(definition, { catalog, bindings: { [binding.id]: id(2) } });
        assert.equal(resolved.graphs.interact.nodes[1].amount, 7);
        assert.equal(resolved.graphs.interact.nodes[1].action, operation);
        const injected = structuredClone(definition);
        injected.parameters.push({ id: 'unused', label: 'Unused amount', type: 'number', default: 7,
            path: ['graphs', 'interact', 'nodes', 1, 'amount'] });
        assert.throws(() => validateTemplateDefinition(injected), /parameter/);
    }
});

test('all six clue operations queue independently without revealing or rewriting private catalog content', () => {
    const operations = ['advance', 'reduce', 'set', 'reset', 'reveal', 'hide'];
    const { blueprint, graph } = fixture(operations.map(operation => action({ id: operation, action: operation })));
    graph.edges = []; let prior = 'event';
    for (const operation of operations) { connectNodes(graph, prior, 'next', operation); prior = operation; }
    const privateCatalog = { clues: [{ ...clue, content: 'PRIVATE CONTENT', gmNotes: 'PRIVATE GM NOTES' }] };
    const before = structuredClone(privateCatalog);
    const result = preview(blueprint, privateCatalog);
    assert.deepEqual(result.actions.map(row => row.action), operations);
    assert.deepEqual(privateCatalog, before);
    assert.equal(JSON.stringify(result).includes('PRIVATE'), false);
    const definition = captureTemplate(blueprint, { catalog: privateCatalog, expose: templateParameterOptions(blueprint) });
    assert.equal(definition.parameters.length, 3);
    assert.equal(JSON.stringify(definition).includes('PRIVATE'), false);
});

test('network clue namespaces remain independent of owners and clocks with the same identifier', () => {
    const { blueprint, graph } = fixture([action(), action({ id: 'missing', clueId: id(99), action: 'reveal' }),
        action({ id: 'unused', clueId: id(98) }), { id: 'clock', type: 'clockControl', clockId: id(1), action: 'advance', amount: 1 }]);
    graph.edges = [];
    connectNodes(graph, 'event', 'next', 'clue'); connectNodes(graph, 'clue', 'next', 'missing'); connectNodes(graph, 'missing', 'next', 'clock');
    const owner = { id: id(1), name: 'Owner', kind: 'lever', blueprint };
    const network = sceneNetwork({ ...catalog, elements: [owner], clocks: [{ id: id(1), name: 'Clock sharing UUID' }] });
    assert.equal(network.nodes.find(row => row.id === id(1)).editable, true);
    assert.equal(network.nodes.find(row => row.id === `clue:${id(1)}`).name, clue.name);
    assert.equal(network.nodes.find(row => row.id === `clock:${id(1)}`).resource, 'clock');
    assert.ok(network.edges.some(row => row.from === id(1) && row.to === `clue:${id(1)}` && row.kind === 'clue'));
    assert.equal(network.nodes.find(row => row.id === `clue:${id(99)}`).missing, true);
    assert.equal(network.nodes.some(row => row.id === `clue:${id(98)}`), false);
    assert.deepEqual(networkPage(network, { problems: true }).nodes.map(row => row.id), [id(1), `clue:${id(99)}`]);
});

test('run summaries contain only clue action, numeric progress and visibility, never its authored secrets', () => {
    const formatter = createRunFormatter({ t: value => value, elements: () => [] });
    const text = formatter.stepText({ type: 'clueControl', action: 'hide', before: 3, value: 3, beforeVisibility: 'players', visibility: 'gm',
        clueId: id(1), name: 'PRIVATE NAME', content: 'PRIVATE CONTENT', gmNotes: 'PRIVATE GM NOTES' });
    assert.match(text, /^Control clue: Hide clue/); assert.match(text, /3 → 3/);
    assert.match(text, /Visible to players → GM only/); assert.equal(text.includes('PRIVATE'), false);
    for (const operation of ['advance', 'reduce', 'set', 'reset', 'reveal', 'hide'])
        assert.equal(formatter.stepText({ type: 'clueControl', action: operation }).includes('undefined'), false);
});
