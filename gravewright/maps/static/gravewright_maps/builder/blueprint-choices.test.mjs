import test from 'node:test';
import assert from 'node:assert/strict';
import { blueprintContract, controlNodeTypes, switchCaseIds, randomBranchIds, defaultBlueprint, upgradeBlueprint,
    eventGraph, connectNodes, executionOutputs, dataInputs, dataOutputs, isPureNode, nodeOutputs,
    validateBlueprint, simulateGraph } from './blueprint-model.js';

const event = 'signal:FixtureInteractClosed';
const execution = (graph, from, output, to) => connectNodes(graph, from, output, to, { version: 2 });
const run = (blueprint, context = {}) => simulateGraph(blueprint, event, 'closed', 'closed', {}, context);
function choiceBlueprint(choice = { type: 'switch', valueType: 'number', value: 1,
    cases: [{ id: 'case1', value: 1 }, { id: 'case2', value: 2 }] }) {
    const blueprint = upgradeBlueprint(defaultBlueprint()), graph = eventGraph(event);
    blueprint.graphs[event] = graph;
    graph.nodes.push({ ...choice, id: 'choice', x: 300, y: 60 });
    execution(graph, 'event', 'next', 'choice');
    for (const [index, output] of nodeOutputs(graph.nodes[1]).entries()) {
        const id = `action_${output}`;
        graph.nodes.push({ id, type: 'setVariable', scope: 'element', name: 'Chosen', valueType: 'text', value: output, x: 600, y: index * 300 });
        execution(graph, 'choice', output, id);
    }
    return blueprint;
}
const randomBlueprint = (weights = [1, 1]) => choiceBlueprint({ type: 'random', weights });

test('choice ports preserve configured Switch IDs and derive Random outputs from its branch count', () => {
    const blueprint = choiceBlueprint({ type: 'switch', valueType: 'text', value: 'x',
        cases: [{ id: 'case4', value: 'y' }, { id: 'case1', value: 'x' }] });
    const node = blueprint.graphs[event].nodes[1];
    validateBlueprint(blueprint);
    assert.deepEqual(switchCaseIds, ['case1', 'case2', 'case3', 'case4']);
    assert.deepEqual(randomBranchIds, ['branch1', 'branch2', 'branch3', 'branch4']);
    assert.deepEqual(executionOutputs(node).map(port => [port.id, port.kind, port.label]),
        [['case4', 'execution', '4'], ['case1', 'execution', '1'], ['default', 'execution', 'Default']]);
    assert.deepEqual(nodeOutputs(node), ['case4', 'case1', 'default']);
    assert.deepEqual(dataInputs(node), [{ id: 'value', kind: 'value', type: 'text', label: 'Value' }]);
    assert.deepEqual(dataOutputs(node), []);
    assert.deepEqual(nodeOutputs({ type: 'random', weights: [0, 1, 2, 3] }), randomBranchIds);
    assert.deepEqual(dataInputs({ type: 'random', weights: [1, 1] }), []);
    for (const type of ['switch', 'random']) {
        assert.equal(blueprintContract.nodes[type].category, 'control');
        assert.equal(isPureNode({ type }), false);
        assert.equal(controlNodeTypes.includes(type), false);
    }
    assert.equal(Object.hasOwn(run(blueprint), 'memory'), false);
});

test('Switch matches Boolean, numeric and text fallbacks without discarding false, zero or empty text', () => {
    for (const [valueType, value, other] of [['boolean', false, true], ['number', 0, 1], ['text', '', 'other']]) {
        const blueprint = choiceBlueprint({ type: 'switch', valueType, value,
            cases: [{ id: 'case3', value: other }, { id: 'case1', value }] });
        validateBlueprint(blueprint);
        const result = run(blueprint);
        assert.equal(result.decisions.choice, 'case1');
        assert.deepEqual(result.actions.map(node => node.value), ['case1']);
        assert.deepEqual(result.values, {});
    }
});

test('a connected typed input overrides Switch fallback and reads the initial variable snapshot', () => {
    const blueprint = choiceBlueprint(), graph = blueprint.graphs[event];
    graph.nodes.push({ id: 'read', type: 'getVariable', scope: 'scene', name: 'Stage', valueType: 'number', default: 2, x: 100, y: 500 },
        { id: 'write', type: 'setVariable', scope: 'scene', name: 'Stage', valueType: 'number', value: 1, x: 100, y: 800 });
    graph.edges = graph.edges.filter(edge => edge.from !== 'event');
    execution(graph, 'event', 'next', 'write');
    execution(graph, 'write', 'next', 'choice');
    connectNodes(graph, 'read', 'value', 'choice', { version: 2, input: 'value' });
    const variables = { scene: { Stage: { type: 'number', value: 2 } } }, result = run(blueprint, { variables });
    assert.deepEqual(result.trace, ['event', 'write', 'choice', 'read', 'action_case2']);
    assert.equal(result.decisions.choice, 'case2');
    assert.equal(result.values.read, 2);
    assert.deepEqual(result.actions.map(node => node.value), [1, 'case2']);
    assert.equal(variables.scene.Stage.value, 2);
    graph.nodes.find(node => node.id === 'read').valueType = 'text';
    graph.nodes.find(node => node.id === 'read').default = '2';
    assert.throws(() => validateBlueprint(blueprint), /connection/);
});

test('Switch selects Default for an unmatched value and never falls through from a disconnected match', () => {
    const blueprint = choiceBlueprint(), graph = blueprint.graphs[event], choice = graph.nodes[1];
    choice.value = 3;
    assert.deepEqual(run(blueprint).actions.map(node => node.value), ['default']);
    choice.value = 1;
    graph.edges = graph.edges.filter(edge => edge.from !== 'choice' || edge.output !== 'case1');
    const result = run(blueprint);
    assert.equal(result.decisions.choice, 'case1');
    assert.deepEqual(result.trace, ['event', 'choice']);
    assert.deepEqual(result.actions, []);
});

test('Switch keeps stable case connections after ordering changes and rejects obsolete ports', () => {
    const blueprint = choiceBlueprint(), graph = blueprint.graphs[event], choice = graph.nodes[1];
    choice.cases.reverse();
    validateBlueprint(blueprint);
    assert.deepEqual(nodeOutputs(choice), ['case2', 'case1', 'default']);
    assert.equal(run(blueprint).decisions.choice, 'case1');
    assert.deepEqual(run(blueprint).actions.map(node => node.value), ['case1']);
    choice.cases = choice.cases.filter(row => row.id !== 'case1');
    assert.throws(() => validateBlueprint(blueprint), /connection/);
    graph.edges = graph.edges.filter(edge => edge.from !== 'choice' || edge.output !== 'case1');
    validateBlueprint(blueprint);
    assert.equal(run(blueprint).decisions.choice, 'default');
});

test('Switch validates exact case shapes, unique IDs and typed values without coercion', () => {
    const blueprint = choiceBlueprint(), graph = blueprint.graphs[event], original = structuredClone(graph.nodes[1]);
    for (const patch of [{ cases: [] }, { cases: null }, { cases: {} }, { cases: [null] }, { cases: Array(2) },
        { cases: [{ id: 'case1', value: 1 }, { id: 'case1', value: 2 }] },
        { cases: [{ id: 'case1', value: 1 }, { id: 'case2', value: 1 }] },
        { cases: [{ id: 'case1', value: 0 }, { id: 'case2', value: -0 }] },
        { cases: [{ id: 'case5', value: 1 }] }, { cases: [{ id: 'case1\n', value: 1 }] },
        { cases: [{ id: 'default', value: 1 }] }, { cases: [{ id: 'case1', value: 1, label: 'extra' }] },
        { cases: [{ id: 'case1' }] }, { cases: [{ id: 'case1', value: '1' }] },
        { cases: [{ id: 'case1', value: NaN }] }, { cases: [{ id: 'case1', value: 1000001 }] },
        { valueType: 'state' }, { value: true }, { value: '1' }, { value: Infinity }, { default: 1 }]) {
        graph.nodes[1] = { ...original, ...patch };
        assert.throws(() => validateBlueprint(blueprint), /switch|node/);
    }
    graph.nodes[1] = { ...original, valueType: 'boolean', value: false, cases: [
        { id: 'case1', value: false }, { id: 'case2', value: true }, { id: 'case3', value: false }] };
    assert.throws(() => validateBlueprint(blueprint), /switch/);
});

test('Switch shares scalar limits for Unicode text and finite numbers and keeps case-sensitive text', () => {
    const blueprint = choiceBlueprint({ type: 'switch', valueType: 'text', value: 'Ready',
        cases: [{ id: 'case1', value: 'ready' }, { id: 'case2', value: 'Ready' }] }), graph = blueprint.graphs[event];
    validateBlueprint(blueprint);
    assert.equal(run(blueprint).decisions.choice, 'case2');
    graph.nodes[1].value = '🔥'.repeat(256);
    graph.nodes[1].cases[1].value = graph.nodes[1].value;
    validateBlueprint(blueprint);
    assert.equal(run(blueprint).decisions.choice, 'case2');
    graph.nodes[1].value += '🔥';
    assert.throws(() => validateBlueprint(blueprint), /switch/);
    for (const value of [-1000000, 1000000]) validateBlueprint(choiceBlueprint({ type: 'switch', valueType: 'number', value,
        cases: [{ id: 'case1', value }] }));
});

test('Random applies weighted interval boundaries and zero-weight branches are never selected', () => {
    const blueprint = randomBlueprint([0, 2, 0, 3]), calls = [];
    for (const [draw, expected] of [[0, 'branch2'], [1, 'branch2'], [2, 'branch4'], [4, 'branch4']]) {
        const result = run(blueprint, { randomDraw: (id, total) => { calls.push([id, total]); return draw; } });
        assert.equal(result.decisions.choice, expected);
        assert.deepEqual(result.actions.map(node => node.value), [expected]);
    }
    assert.deepEqual(calls, Array(4).fill(['choice', 5]));
});

test('Random draws across disconnected branches without rerolling or choosing a connected alternative', () => {
    const blueprint = randomBlueprint([1, 3]), graph = blueprint.graphs[event];
    graph.edges = graph.edges.filter(edge => edge.from !== 'choice' || edge.output === 'branch1');
    let calls = 0;
    const result = run(blueprint, { randomDraw: () => { calls += 1; return 3; } });
    assert.equal(calls, 1);
    assert.equal(result.decisions.choice, 'branch2');
    assert.deepEqual(result.trace, ['event', 'choice']);
    assert.deepEqual(result.actions, []);
});

test('Random requires two to four nonnegative integer weights with a nonzero bounded total', () => {
    const blueprint = randomBlueprint(), graph = blueprint.graphs[event];
    for (const weights of [null, {}, [], [1], [1, 1, 1, 1, 1], [0, 0], [-1, 1], [1001, 1], [.5, 1],
        ['1', 1], [true, 1], [NaN, 1], [Infinity, 1], Array(2), [undefined, 1]]) {
        graph.nodes[1].weights = weights;
        assert.throws(() => validateBlueprint(blueprint), /weights/);
    }
    for (const weights of [[0, 1], [1000, 1000], [1000, 1000, 1000, 1000]]) validateBlueprint(randomBlueprint(weights));
    graph.nodes[1].weights = [1, 1];
    graph.nodes[1].seed = 'extra';
    assert.throws(() => validateBlueprint(blueprint), /node/);
});

test('a reached Random refuses invalid sampler results instead of coercing or clamping them', () => {
    const blueprint = randomBlueprint([2, 3]);
    for (const draw of [-1, 5, .5, NaN, Infinity, '0', true, undefined, null]) {
        assert.throws(() => run(blueprint, { randomDraw: () => draw }), /random draw/);
    }
    assert.throws(() => run(blueprint, { randomDraw: 0 }), /random draw/);
});

test('the default local sampler uses Math.random only for a reached Random node', () => {
    const previous = Math.random;
    let calls = 0;
    try {
        Math.random = () => { calls += 1; return .999; };
        assert.equal(run(randomBlueprint([1, 2, 3, 4])).decisions.choice, 'branch4');
        assert.equal(calls, 1);
        run(choiceBlueprint());
        assert.equal(calls, 1);
    } finally { Math.random = previous; }
});

test('unreached Random nodes do not sample and existing condition decisions remain Boolean', () => {
    const blueprint = randomBlueprint(), graph = blueprint.graphs[event];
    graph.nodes.push({ id: 'check', type: 'condition', state: 'open', x: 100, y: 60 });
    graph.edges = graph.edges.filter(edge => edge.from !== 'event');
    execution(graph, 'event', 'next', 'check');
    execution(graph, 'check', 'true', 'choice');
    const result = run(blueprint, { randomDraw: 'invalid but never used' });
    assert.deepEqual(result.trace, ['event', 'check']);
    assert.equal(result.decisions.check, false);
    assert.equal(Object.hasOwn(result.decisions, 'choice'), false);
});

test('convergent Sequence branches draw once and execute one chosen branch once per event', () => {
    const blueprint = randomBlueprint(), graph = blueprint.graphs[event];
    graph.nodes.push({ id: 'order', type: 'sequence', x: 100, y: 60 });
    graph.edges = graph.edges.filter(edge => edge.from !== 'event');
    execution(graph, 'event', 'next', 'order');
    execution(graph, 'order', 'then1', 'choice');
    execution(graph, 'order', 'then2', 'choice');
    let calls = 0;
    const result = run(blueprint, { randomDraw: () => { calls += 1; return 1; } });
    assert.equal(calls, 1);
    assert.deepEqual(result.trace, ['event', 'order', 'choice', 'action_branch2']);
    assert.deepEqual(result.actions.map(node => node.value), ['branch2']);
});

test('a Delay suspends choices not yet visited while keeping already chosen outputs in the trace', () => {
    const blueprint = randomBlueprint(), graph = blueprint.graphs[event];
    graph.nodes[2] = { id: 'action_branch1', type: 'delay', seconds: 2, x: 600, y: 60 };
    const result = run(blueprint, { randomDraw: () => 0 });
    assert.equal(result.decisions.choice, 'branch1');
    assert.deepEqual(result.delay, { nodeId: 'action_branch1', seconds: 2 });
    graph.nodes.push({ id: 'first_wait', type: 'delay', seconds: 1, x: 100, y: 60 });
    graph.edges = graph.edges.filter(edge => edge.from !== 'event');
    execution(graph, 'event', 'next', 'first_wait');
    execution(graph, 'first_wait', 'next', 'choice');
    const waiting = run(blueprint, { randomDraw: () => { throw Error('unreachable random draw'); } });
    assert.deepEqual(waiting.trace, ['event', 'first_wait']);
    assert.equal(Object.hasOwn(waiting.decisions, 'choice'), false);
});

test('choice nodes remain version two and reject execution wires to unavailable branches', () => {
    for (const blueprint of [choiceBlueprint(), randomBlueprint()]) {
        const graph = blueprint.graphs[event];
        assert.throws(() => execution(graph, 'choice', 'next', graph.nodes[2].id), /connection/);
        assert.throws(() => execution(graph, 'choice', 'branch4', graph.nodes[2].id), /connection/);
        blueprint.version = 1;
        for (const edge of graph.edges) delete edge.kind;
        assert.throws(() => validateBlueprint(blueprint), /Unsupported/);
    }
});

test('choices compose with persistent controls without changing their Boolean decisions or memory', () => {
    const blueprint = choiceBlueprint(), graph = blueprint.graphs[event];
    graph.nodes.push({ id: 'gate', type: 'once', x: 100, y: 60 });
    graph.edges = graph.edges.filter(edge => edge.from !== 'event');
    execution(graph, 'event', 'next', 'gate');
    execution(graph, 'gate', 'true', 'choice');
    const first = run(blueprint);
    assert.equal(first.decisions.gate, true);
    assert.equal(first.decisions.choice, 'case1');
    const second = run(blueprint, { memory: first.memory });
    assert.equal(second.decisions.gate, false);
    assert.equal(Object.hasOwn(second.decisions, 'choice'), false);
    assert.deepEqual(second.actions, []);
    assert.equal(first.memory[event].gate.value, true);
});

test('choice simulation preserves frozen authored data and context and returns independent result objects', () => {
    function freeze(value) {
        if (value && typeof value === 'object') {
            Object.values(value).forEach(freeze);
            Object.freeze(value);
        }
        return value;
    }
    const blueprint = freeze(randomBlueprint()), before = structuredClone(blueprint);
    const context = freeze({ randomDraw: () => 1, variables: { scene: {} }, now: 1000 });
    const first = run(blueprint, context);
    first.decisions.choice = 'branch1';
    first.actions[0].value = 'changed';
    assert.equal(run(blueprint, context).decisions.choice, 'branch2');
    assert.equal(run(blueprint, context).actions[0].value, 'branch2');
    assert.deepEqual(blueprint, before);
    assert.deepEqual(context.variables, { scene: {} });
});
