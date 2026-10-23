import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultBlueprint, eventGraph, connectNodes, validateBlueprint, simulateGraph, blueprintContract,
    dataInputs, dataOutputs, nodeOutputs, acceptsDataType } from './blueprint-model.js';
import { captureTemplate, resolveTemplate, templateParameterOptions, validateTemplateDefinition } from './blueprint-templates.js';

const id = number => `00000000-0000-4000-8000-${String(number).padStart(12, '0')}`;
const clock = { id: id(1), name: '<img src=x> Authored clock', segments: 8, value: 4, visibility: 'gm', sceneId: null };
const catalog = { clocks: [clock, { ...clock, id: id(2), name: 'Another clock' }] };
const action = (patch = {}) => ({ id: 'clock', type: 'clockControl', clockId: id(1), action: 'advance', amount: 1, ...patch });
function fixture(nodes = [action()]) {
    const blueprint = defaultBlueprint('lever'), graph = blueprint.graphs.interact = eventGraph('interact');
    graph.nodes.push(...nodes.map((row, index) => ({ x: 300 + index * 300, y: 60, ...row })));
    connectNodes(graph, 'event', 'next', nodes.at(-1).id);
    return { blueprint, graph };
}
const preview = (blueprint, context = {}) => simulateGraph(blueprint, 'interact', 'off', 'off', {}, context);

test('clock control has execution continuation and a single number input without an implicit target', () => {
    const contract = blueprintContract.nodes.clockControl;
    assert.equal(contract.category, 'action'); assert.equal(contract.label, 'Control clock');
    assert.deepEqual(contract.inputs.filter(port => port.kind === 'execution').map(port => port.id), ['input']);
    assert.deepEqual(dataInputs(action()), [{ id: 'amount', kind: 'value', type: 'number', label: 'Amount' }]);
    assert.deepEqual(dataOutputs(action()), []); assert.deepEqual(nodeOutputs(action()), ['next']);
    const amount = dataInputs(action())[0];
    assert.equal(acceptsDataType(amount, 'number'), true);
    for (const type of ['boolean', 'text', 'element', 'elementset', 'state']) assert.equal(acceptsDataType(amount, type), false);
    const { graph } = fixture([{ id: 'source', type: 'getVariable', scope: 'element', name: 'Amount', valueType: 'boolean', default: true }, action()]);
    assert.throws(() => connectNodes(graph, 'source', 'value', 'clock', { input: 'amount' }), /connection/);
});

test('clock configuration requires exact fields, a UUID, a supported action and an integer from zero to twenty-four', () => {
    for (const operation of ['advance', 'reduce', 'set', 'reset']) for (const amount of [0, 1, 24])
        validateBlueprint(fixture([action({ action: operation, amount })]).blueprint, catalog);
    const invalid = [{ clockId: 'bad' }, { clockId: id(1) + '\n' }, { clockId: null }, { action: 'stop' },
        { amount: -1 }, { amount: 25 }, { amount: .5 }, { amount: true }, { amount: '1' }, { amount: NaN },
        { amount: Infinity }, { target: id(2) }, { players: true }];
    for (const patch of invalid) assert.throws(() => validateBlueprint(fixture([action(patch)]).blueprint, catalog), /clock|node/);
    for (const key of ['clockId', 'action', 'amount']) {
        const node = action(); delete node[key];
        assert.throws(() => validateBlueprint(fixture([node]).blueprint, catalog), /node/);
    }
    const old = fixture().blueprint; old.version = 1;
    assert.throws(() => validateBlueprint(old, catalog), /version/);
});

test('provided clock catalogs reject stale selections and accept canonical UUID casing', () => {
    const { blueprint } = fixture();
    validateBlueprint(blueprint);
    assert.throws(() => validateBlueprint(blueprint, { clocks: [] }), /Choose a clock/);
    assert.throws(() => validateBlueprint(blueprint, { clocks: [{ ...clock, id: id(9) }] }), /Choose a clock/);
    validateBlueprint(blueprint, catalog);
    const letters = 'abcdefab-cdef-4abc-8def-abcdefabcdef';
    validateBlueprint(fixture([action({ clockId: letters.toUpperCase() })]).blueprint, { clocks: [{ id: letters }] });
});

test('clock previews queue independent actions in execution order without changing any clock or graph', () => {
    const { blueprint, graph } = fixture([action(), action({ id: 'reduce', action: 'reduce', amount: 2 }),
        action({ id: 'set', action: 'set', amount: 24 }), action({ id: 'reset', action: 'reset' })]);
    graph.edges = [];
    let previous = 'event';
    for (const node of graph.nodes.slice(1)) { connectNodes(graph, previous, 'next', node.id); previous = node.id; }
    const original = structuredClone({ blueprint, catalog });
    const first = preview(blueprint, { clocks: catalog.clocks }), second = preview(blueprint, { clocks: catalog.clocks });
    assert.deepEqual(first.actions.map(row => [row.action, row.amount]), [['advance', 1], ['reduce', 2], ['set', 24], ['reset', 1]]);
    assert.deepEqual(first.trace, ['event', 'clock', 'reduce', 'set', 'reset']);
    first.actions[0].clockId = id(9); first.actions[1].amount = 0;
    assert.deepEqual(second.actions.map(row => row.clockId), [id(1), id(1), id(1), id(1)]);
    assert.deepEqual({ blueprint, catalog }, original);
    assert.equal(Object.hasOwn(first, 'clocks'), false); assert.equal(Object.hasOwn(first, 'effects'), false);
});

test('connected amounts replace the saved fallback and reject invalid runtime numbers', () => {
    const variable = { id: 'amount', type: 'getVariable', scope: 'element', name: 'Amount', valueType: 'number', default: 2 };
    const { blueprint, graph } = fixture([variable, action({ amount: 1 })]);
    connectNodes(graph, 'amount', 'value', 'clock', { input: 'amount' });
    validateBlueprint(blueprint, catalog);
    assert.equal(preview(blueprint).actions[0].amount, 2);
    for (const amount of [0, 24]) assert.equal(preview(blueprint, { variables: { element: { Amount: { type: 'number', value: amount } } } }).actions[0].amount, amount);
    for (const amount of [-1, 25, 2.5]) assert.throws(() => preview(blueprint,
        { variables: { element: { Amount: { type: 'number', value: amount } } } }), /integer from 0 to 24/);
    assert.equal(graph.nodes.at(-1).amount, 1);
    graph.edges = graph.edges.filter(edge => edge.kind !== 'data');
    assert.equal(preview(blueprint).actions[0].amount, 1);
});

test('reset ignores its amount connection without evaluating an unavailable value', () => {
    const variable = { id: 'amount', type: 'getVariable', scope: 'element', name: 'Amount', valueType: 'number', default: -1 };
    const { blueprint, graph } = fixture([variable, action({ action: 'reset' })]);
    connectNodes(graph, 'amount', 'value', 'clock', { input: 'amount' });
    const result = preview(blueprint, { variables: { element: { Amount: { type: 'text', value: 'Wrong current type' } } } });
    assert.deepEqual(result.trace, ['event', 'clock']); assert.deepEqual(result.values, {});
    assert.equal(result.actions[0].amount, 1);
});

test('templates use clock bindings and expose only the amount scalar while preserving authored text', () => {
    const { blueprint } = fixture([action(), action({ id: 'second', action: 'set', amount: 3 }),
        { id: 'message', type: 'showMessage', text: id(1), audience: { scope: 'trigger' } }]);
    const original = structuredClone(blueprint), options = templateParameterOptions(blueprint);
    const expose = options.filter(row => row.path.at(-1) === 'amount');
    assert.equal(expose.length, 2);
    assert.equal(options.some(row => ['clockId', 'action'].includes(row.path.at(-1))), false);
    const definition = captureTemplate(blueprint, { catalog, expose });
    assert.deepEqual(definition.bindings.map(row => row.type), ['clock']);
    const [binding] = definition.bindings;
    assert.deepEqual(definition.blueprint.graphs.interact.nodes[1].clockId, { binding: binding.id });
    assert.deepEqual(definition.blueprint.graphs.interact.nodes[2].clockId, { binding: binding.id });
    assert.equal(definition.blueprint.graphs.interact.nodes[3].text, id(1));
    validateTemplateDefinition(definition);
    const [parameter] = definition.parameters;
    const first = resolveTemplate(definition, { catalog, bindings: { [binding.id]: id(2) }, parameters: { [parameter.id]: 24 } });
    const second = resolveTemplate(definition, { catalog, bindings: { [binding.id]: id(1) } });
    assert.equal(first.graphs.interact.nodes[1].clockId, id(2)); assert.equal(first.graphs.interact.nodes[1].amount, 24);
    assert.equal(second.graphs.interact.nodes[1].clockId, id(1)); assert.equal(second.graphs.interact.nodes[1].amount, 1);
    assert.deepEqual(blueprint, original);
    for (const amount of [-1, 25, .5, '1', true]) assert.throws(() => resolveTemplate(definition,
        { catalog, bindings: { [binding.id]: id(2) }, parameters: { [parameter.id]: amount } }), /parameter|clock/);
    for (const resource of [id(9), null]) assert.throws(() => resolveTemplate(definition,
        { catalog, bindings: { [binding.id]: resource } }), /binding|resource/);
    assert.throws(() => resolveTemplate(definition, { catalog: { clocks: [] }, bindings: { [binding.id]: id(1) } }), /resource/);
    const wrong = structuredClone(definition); wrong.bindings[0].type = 'sound';
    assert.throws(() => validateTemplateDefinition(wrong), /binding/);
});

test('reset templates retain their required saved amount without exposing an unused parameter', () => {
    const { blueprint } = fixture([action({ action: 'reset', amount: 7 })]);
    assert.deepEqual(templateParameterOptions(blueprint), []);
    const definition = captureTemplate(blueprint, { catalog });
    assert.deepEqual(definition.parameters, []);
    const [binding] = definition.bindings;
    const resolved = resolveTemplate(definition, { catalog, bindings: { [binding.id]: id(2) } });
    assert.equal(resolved.graphs.interact.nodes[1].amount, 7);
    assert.equal(resolved.graphs.interact.nodes[1].action, 'reset');
    const injected = structuredClone(definition);
    injected.parameters.push({ id: 'unused', label: 'Unused amount', type: 'number', default: 7,
        path: ['graphs', 'interact', 'nodes', 1, 'amount'] });
    assert.throws(() => validateTemplateDefinition(injected), /parameter/);
});
