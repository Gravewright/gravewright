import test from 'node:test';
import assert from 'node:assert/strict';
import { blueprintContract, controlNodeTypes, defaultBlueprint, upgradeBlueprint, eventGraph, connectNodes,
    dataInputs, dataOutputs, isPureNode, nodeOutputs, validateBlueprint, simulateGraph } from './blueprint-model.js';

const event = 'signal:FixtureInteractClosed';
function delayBlueprint(seconds = 3, key = event) {
    const blueprint = upgradeBlueprint(defaultBlueprint()), graph = eventGraph(key);
    blueprint.graphs[key] = graph;
    graph.nodes.push(
        { id: 'before', type: 'state', targetState: 'open', x: 300, y: 60 },
        { id: 'wait', type: 'delay', seconds, x: 600, y: 60 },
        { id: 'after', type: 'state', targetState: 'closed', x: 900, y: 60 },
    );
    for (const [from, to] of [['event', 'before'], ['before', 'wait'], ['wait', 'after']]) {
        connectNodes(graph, from, 'next', to, { version: 2 });
    }
    return blueprint;
}
const run = (blueprint, context = {}, key = event) => simulateGraph(blueprint, key, 'closed', 'closed', {}, context);

test('Delay is a version two execution control with no value ports or persistent gate memory', () => {
    const blueprint = delayBlueprint(), node = blueprint.graphs[event].nodes[2];
    validateBlueprint(blueprint);
    assert.equal(blueprintContract.nodes.delay.category, 'control');
    assert.equal(blueprintContract.nodes.delay.label, 'Delay');
    assert.deepEqual(blueprintContract.nodes.delay.inputs.map(port => port.kind), ['execution']);
    assert.deepEqual(nodeOutputs(node), ['next']);
    assert.deepEqual(dataInputs(node), []);
    assert.deepEqual(dataOutputs(node), []);
    assert.equal(isPureNode(node), false);
    assert.equal(controlNodeTypes.includes('delay'), false);
    assert.throws(() => { blueprintContract.nodes.delay.outputs[0].label = 'Changed'; }, TypeError);
    assert.equal(Object.hasOwn(run(blueprint), 'memory'), false);
});

test('a preview executes preceding actions and stops at the first wait without advancing time', () => {
    const blueprint = delayBlueprint(), result = run(blueprint, { now: 1000 });
    assert.deepEqual(result.trace, ['event', 'before', 'wait']);
    assert.deepEqual(result.actions.map(action => action.id), ['before']);
    assert.deepEqual(result.delay, { nodeId: 'wait', seconds: 3 });
    assert.deepEqual(result.values, {});
    assert.deepEqual(run(blueprint, { now: 100000 }), result, 'a later preview clock does not execute the continuation');
});

test('Delay pauses the remaining Sequence branches in their authored order', () => {
    const blueprint = delayBlueprint(), graph = blueprint.graphs[event];
    graph.nodes.push({ id: 'order', type: 'sequence', x: 100, y: 100 },
        { id: 'later_branch', type: 'state', targetState: 'locked', x: 300, y: 500 });
    graph.edges = graph.edges.filter(edge => edge.from !== 'event');
    connectNodes(graph, 'event', 'next', 'order', { version: 2 });
    connectNodes(graph, 'order', 'then1', 'before', { version: 2 });
    connectNodes(graph, 'order', 'then2', 'later_branch', { version: 2 });
    const result = run(blueprint);
    assert.deepEqual(result.trace, ['event', 'order', 'before', 'wait']);
    assert.deepEqual(result.actions.map(action => action.id), ['before']);
    assert.equal(result.trace.includes('later_branch'), false);
});

test('fanout pauses at the first encountered wait and cannot replay a convergent action', () => {
    const blueprint = delayBlueprint(), graph = blueprint.graphs[event];
    graph.nodes.push({ id: 'branch', type: 'state', targetState: 'open', x: 300, y: 500 });
    connectNodes(graph, 'event', 'next', 'branch', { version: 2 });
    connectNodes(graph, 'branch', 'next', 'after', { version: 2 });
    assert.deepEqual(run(blueprint).trace, ['event', 'before', 'wait']);
    graph.edges.reverse();
    const reordered = run(blueprint);
    assert.deepEqual(reordered.trace, ['event', 'branch', 'after', 'before', 'wait']);
    assert.deepEqual(reordered.actions.map(action => action.id), ['branch', 'after', 'before']);
    assert.equal(reordered.trace.filter(id => id === 'after').length, 1);
});

test('multiple waits report only the first reached wait, including a disconnected continuation', () => {
    const blueprint = delayBlueprint(.1001), graph = blueprint.graphs[event];
    graph.nodes.push({ id: 'second_wait', type: 'delay', seconds: 9, x: 1200, y: 60 });
    connectNodes(graph, 'after', 'next', 'second_wait', { version: 2 });
    assert.deepEqual(run(blueprint).delay, { nodeId: 'wait', seconds: .1001 });
    graph.edges = graph.edges.filter(edge => edge.from !== 'wait');
    const terminal = run(blueprint);
    assert.deepEqual(terminal.delay, { nodeId: 'wait', seconds: .1001 });
    assert.deepEqual(terminal.trace, ['event', 'before', 'wait']);
});

test('an unreachable Delay leaves normal execution, branch selection and result shape unchanged', () => {
    const blueprint = delayBlueprint(), graph = blueprint.graphs[event];
    graph.nodes.push({ id: 'check', type: 'condition', state: 'open', x: 100, y: 60 });
    graph.edges = graph.edges.filter(edge => edge.from !== 'event');
    connectNodes(graph, 'event', 'next', 'check', { version: 2 });
    connectNodes(graph, 'check', 'true', 'before', { version: 2 });
    connectNodes(graph, 'check', 'false', 'after', { version: 2 });
    validateBlueprint(blueprint);
    const result = run(blueprint);
    assert.deepEqual(result.trace, ['event', 'check', 'after']);
    assert.deepEqual(result.actions.map(action => action.id), ['after']);
    assert.equal(Object.hasOwn(result, 'delay'), false);
});

test('a wait does not read lazy values or queue variable writes from the continuation', () => {
    const blueprint = delayBlueprint(), graph = blueprint.graphs[event];
    graph.nodes[3] = { id: 'after', type: 'setVariable', scope: 'scene', name: 'Progress', valueType: 'number', value: 3, x: 900, y: 60 };
    graph.nodes.push({ id: 'read', type: 'getVariable', scope: 'element', name: 'Value', valueType: 'number', default: 2, x: 600, y: 500 });
    connectNodes(graph, 'read', 'value', 'after', { version: 2, input: 'value' });
    const context = { variables: { element: { Value: { type: 'text', value: 'incompatible but not yet read' } } } };
    const result = run(blueprint, context);
    assert.deepEqual(result.values, {});
    assert.deepEqual(result.actions.map(action => action.id), ['before']);
    assert.deepEqual(result.delay, { nodeId: 'wait', seconds: 3 });
});

test('controls preceding a wait update once while downstream controls retain their prior progress', () => {
    const blueprint = delayBlueprint(), graph = blueprint.graphs[event];
    graph.nodes[1] = { id: 'before', type: 'counter', target: 1, x: 300, y: 60 };
    graph.nodes[3] = { id: 'after', type: 'counter', target: 3, x: 900, y: 60 };
    graph.edges = graph.edges.filter(edge => edge.from !== 'before');
    connectNodes(graph, 'before', 'true', 'wait', { version: 2 });
    const memory = { [event]: { after: { type: 'counter', value: 2 } } };
    const result = run(blueprint, { memory });
    assert.deepEqual(result.trace, ['event', 'before', 'wait']);
    assert.equal(result.memory[event].before.value, 1);
    assert.equal(result.memory[event].after.value, 2);
    assert.deepEqual({ ...result.decisions }, { before: true });
    assert.deepEqual(memory, { [event]: { after: { type: 'counter', value: 2 } } });
});

test('signal events use the same suspension rules and independent previews never consume a wait', () => {
    const key = 'signal:CloseLater', blueprint = delayBlueprint(3, key);
    const first = run(blueprint, {}, key), second = run(blueprint, {}, key);
    assert.deepEqual(second, first);
    assert.deepEqual(first.delay, { nodeId: 'wait', seconds: 3 });
    assert.deepEqual(first.actions.map(action => action.id), ['before']);
    assert.equal(validateBlueprint(JSON.parse(JSON.stringify(blueprint))).graphs[key].nodes[2].type, 'delay');
});

test('Delay rejects coercion, out of range values, extra fields and version one graphs', () => {
    const blueprint = delayBlueprint(), graph = blueprint.graphs[event], original = structuredClone(graph.nodes[2]);
    for (const patch of [{ seconds: 0 }, { seconds: .099 }, { seconds: -1 }, { seconds: 86400.001 },
        { seconds: true }, { seconds: '3' }, { seconds: NaN }, { seconds: Infinity }, { seconds: null }, { deadline: 3 }]) {
        graph.nodes[2] = { ...original, ...patch };
        assert.throws(() => validateBlueprint(blueprint), /control|node/);
    }
    graph.nodes[2] = structuredClone(original);
    delete graph.nodes[2].seconds;
    assert.throws(() => validateBlueprint(blueprint), /node/);
    graph.nodes[2] = structuredClone(original);
    for (const seconds of [.1, .1001, 86400]) validateBlueprint(delayBlueprint(seconds));
    validateBlueprint(blueprint);
    blueprint.version = 1;
    for (const edge of graph.edges) delete edge.kind;
    assert.throws(() => validateBlueprint(blueprint), /Unsupported/);
});

test('delay results and preceding actions never mutate frozen authored data or preview context', () => {
    function freeze(value) {
        if (value && typeof value === 'object') {
            Object.values(value).forEach(freeze);
            Object.freeze(value);
        }
        return value;
    }
    const blueprint = freeze(delayBlueprint()), context = freeze({ variables: { scene: {} }, now: 1000 });
    const before = structuredClone({ blueprint, context }), result = run(blueprint, context);
    result.actions[0].targetState = 'locked';
    result.delay.seconds = 99;
    assert.deepEqual({ blueprint, context }, before);
    assert.deepEqual(run(blueprint, context).delay, { nodeId: 'wait', seconds: 3 });
});
