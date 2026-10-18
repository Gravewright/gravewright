import test from 'node:test';
import assert from 'node:assert/strict';
import { blueprintContract, controlNodeTypes, timerActions, defaultBlueprint, upgradeBlueprint, eventGraph,
    connectNodes, dataInputs, dataOutputs, nodeOutputs, isPureNode, validateBlueprint, simulateGraph } from './blueprint-model.js';

const event = 'signal:FixtureInteractClosed';
function timerBlueprint(action = 'start', seconds = 3) {
    const blueprint = upgradeBlueprint(defaultBlueprint()), graph = eventGraph(event);
    blueprint.graphs[event] = graph;
    graph.nodes.push({ id: 'countdown', type: 'timer', name: 'CloseLater', action,
        ...(action !== 'stop' ? { seconds } : {}), x: 300, y: 60 },
    { id: 'immediate', type: 'state', targetState: 'open', x: 600, y: 60 });
    connectNodes(graph, 'event', 'next', 'countdown', { version: 2 });
    connectNodes(graph, 'countdown', 'next', 'immediate', { version: 2 });
    return blueprint;
}
const run = (blueprint, context = {}, key = event) => simulateGraph(blueprint, key, 'closed', 'closed', {}, context);

test('Timer exposes only execution ports and never belongs to per-node gate memory', () => {
    const blueprint = timerBlueprint(), node = blueprint.graphs[event].nodes[1];
    validateBlueprint(blueprint);
    assert.deepEqual(timerActions, ['start', 'stop', 'restart']);
    assert.equal(blueprintContract.nodes.timer.category, 'control');
    assert.deepEqual(blueprintContract.nodes.timer.inputs.map(port => port.kind), ['execution']);
    assert.deepEqual(nodeOutputs(node), ['next']);
    assert.deepEqual(dataInputs(node), []);
    assert.deepEqual(dataOutputs(node), []);
    assert.equal(isPureNode(node), false);
    assert.equal(controlNodeTypes.includes('timer'), false);
    assert.equal(Object.hasOwn(run(blueprint), 'memory'), false);
    assert.equal(Object.hasOwn(run(blueprint), 'delay'), false);
    assert.throws(() => { timerActions.push('pause'); }, TypeError);
    assert.throws(() => { blueprintContract.nodes.timer.outputs[0].label = 'Changed'; }, TypeError);
});

test('starting, restarting and stopping a named countdown queue ordinary actions and continue immediately', () => {
    for (const action of timerActions) {
        const blueprint = timerBlueprint(action), result = run(blueprint);
        validateBlueprint(blueprint);
        assert.deepEqual(result.trace, ['event', 'countdown', 'immediate']);
        assert.deepEqual(result.actions.map(node => [node.type, node.name, node.action]),
            [['timer', 'CloseLater', action], ['state', undefined, undefined]]);
        assert.equal(Object.hasOwn(result.actions[0], 'seconds'), action !== 'stop');
        assert.deepEqual(run(blueprint, { now: 100000 }), result, 'preview clocks do not consume countdowns');
    }
});

test('timer names are local to an element and can be used by several distinct authored operations', () => {
    const blueprint = timerBlueprint(), graph = blueprint.graphs[event];
    graph.nodes.push({ id: 'replace', type: 'timer', name: 'CloseLater', action: 'restart', seconds: 9, x: 900, y: 60 },
        { id: 'cancel', type: 'timer', name: 'CloseLater', action: 'stop', x: 1200, y: 60 });
    connectNodes(graph, 'immediate', 'next', 'replace', { version: 2 });
    connectNodes(graph, 'replace', 'next', 'cancel', { version: 2 });
    validateBlueprint(blueprint);
    assert.deepEqual(run(blueprint).actions.filter(node => node.type === 'timer').map(node => node.action), ['start', 'restart', 'stop']);
    assert.equal(validateBlueprint(JSON.parse(JSON.stringify(blueprint))).graphs[event].nodes[3].name, 'CloseLater');
});

test('timer expiry listeners are separate fresh events that a local timer preview never executes', () => {
    const blueprint = timerBlueprint(), key = 'signal:CloseLater', graph = eventGraph(key);
    blueprint.graphs[key] = graph;
    graph.nodes.push({ id: 'expired', type: 'state', targetState: 'locked', x: 300, y: 60 });
    connectNodes(graph, 'event', 'next', 'expired', { version: 2 });
    validateBlueprint(blueprint);
    assert.deepEqual(run(blueprint).actions.map(node => node.id), ['countdown', 'immediate']);
    assert.deepEqual(run(blueprint, {}, key).actions.map(node => node.id), ['expired']);
    delete blueprint.graphs[key];
    validateBlueprint(blueprint);
    assert.deepEqual(run(blueprint).actions.map(node => node.id), ['countdown', 'immediate'], 'an unmatched signal name is a valid draft');
});

test('timer operations preceding a Delay remain queued while later operations await the server continuation', () => {
    const blueprint = timerBlueprint(), graph = blueprint.graphs[event];
    graph.nodes[2] = { id: 'immediate', type: 'delay', seconds: 2, x: 600, y: 60 };
    graph.nodes.push({ id: 'cancel', type: 'timer', name: 'CloseLater', action: 'stop', x: 900, y: 60 });
    connectNodes(graph, 'immediate', 'next', 'cancel', { version: 2 });
    const result = run(blueprint);
    assert.deepEqual(result.trace, ['event', 'countdown', 'immediate']);
    assert.deepEqual(result.actions.map(node => node.id), ['countdown']);
    assert.deepEqual(result.delay, { nodeId: 'immediate', seconds: 2 });
    graph.nodes[1] = { id: 'countdown', type: 'delay', seconds: 1, x: 300, y: 60 };
    assert.deepEqual(run(blueprint).actions, []);
});

test('a branch that does not reach a Timer never queues it or changes its ordinary state action', () => {
    const blueprint = timerBlueprint(), graph = blueprint.graphs[event];
    graph.nodes.push({ id: 'check', type: 'condition', state: 'open', x: 100, y: 60 });
    graph.edges = graph.edges.filter(edge => edge.from !== 'event');
    connectNodes(graph, 'event', 'next', 'check', { version: 2 });
    connectNodes(graph, 'check', 'true', 'countdown', { version: 2 });
    connectNodes(graph, 'check', 'false', 'immediate', { version: 2 });
    assert.deepEqual(run(blueprint).trace, ['event', 'check', 'immediate']);
    assert.deepEqual(run(blueprint).actions.map(node => node.id), ['immediate']);
});

test('a convergent Timer queues once per event even when several Sequence branches reach it', () => {
    const blueprint = timerBlueprint(), graph = blueprint.graphs[event];
    graph.nodes.push({ id: 'order', type: 'sequence', x: 100, y: 60 });
    graph.edges = graph.edges.filter(edge => edge.from !== 'event');
    connectNodes(graph, 'event', 'next', 'order', { version: 2 });
    connectNodes(graph, 'order', 'then1', 'countdown', { version: 2 });
    connectNodes(graph, 'order', 'then2', 'countdown', { version: 2 });
    assert.deepEqual(run(blueprint).trace, ['event', 'order', 'countdown', 'immediate']);
    assert.equal(run(blueprint).actions.filter(node => node.type === 'timer').length, 1);
});

test('timer duration and action validation rejects coercion, out of range values and unrelated fields', () => {
    const blueprint = timerBlueprint(), graph = blueprint.graphs[event], original = structuredClone(graph.nodes[1]);
    for (const patch of [{ seconds: 0 }, { seconds: .099 }, { seconds: 86400.001 }, { seconds: -1 }, { seconds: NaN },
        { seconds: Infinity }, { seconds: '3' }, { seconds: true }, { seconds: null }, { action: 'pause' },
        { action: 'START' }, { action: null }, { targetId: 'another-element' }, { scope: 'scene' }, { deadline: 3 }]) {
        graph.nodes[1] = { ...original, ...patch };
        assert.throws(() => validateBlueprint(blueprint), /timer|node/);
    }
    graph.nodes[1] = { ...original, action: 'stop' };
    assert.throws(() => validateBlueprint(blueprint), /node/, 'stop must omit seconds');
    for (const action of ['start', 'restart']) {
        graph.nodes[1] = { ...original, action };
        delete graph.nodes[1].seconds;
        assert.throws(() => validateBlueprint(blueprint), /node/, 'starting requires seconds');
        for (const seconds of [.1, .1001, 86400]) validateBlueprint(timerBlueprint(action, seconds));
    }
});

test('timer names have the same strict ASCII identity as signals, including final line break rejection', () => {
    const blueprint = timerBlueprint(), node = blueprint.graphs[event].nodes[1];
    for (const name of ['', '1timer', '_timer', 'timer name', 'timer:name', 't'.repeat(65), 'timer\n', 'timer\r', 'timer\u2028', 'relógio', null, 4]) {
        node.name = name;
        assert.throws(() => validateBlueprint(blueprint), /timer/);
    }
    for (const name of ['T', 'Timer.ready-1_next', 't'.repeat(64), 'constructor']) {
        node.name = name;
        validateBlueprint(blueprint);
    }
});

test('Timer stays version two and cannot accept data or targeted execution ports', () => {
    const blueprint = timerBlueprint(), graph = blueprint.graphs[event];
    graph.nodes.push({ id: 'read', type: 'getVariable', scope: 'element', name: 'Duration', valueType: 'number', default: 3, x: 100, y: 500 });
    assert.throws(() => connectNodes(graph, 'read', 'value', 'countdown', { version: 2, input: 'seconds' }), /connection/);
    assert.throws(() => connectNodes(graph, 'countdown', 'expired', 'immediate', { version: 2 }), /connection/);
    blueprint.version = 1;
    graph.nodes.pop();
    for (const edge of graph.edges) delete edge.kind;
    assert.throws(() => validateBlueprint(blueprint), /Unsupported/);
});

test('queued timer actions never mutate authored definitions, private context or prior preview results', () => {
    function freeze(value) {
        if (value && typeof value === 'object') {
            Object.values(value).forEach(freeze);
            Object.freeze(value);
        }
        return value;
    }
    const blueprint = freeze(timerBlueprint()), context = freeze({ variables: { scene: {} }, now: 1000 });
    const before = structuredClone({ blueprint, context }), result = run(blueprint, context);
    result.actions[0].name = 'Changed';
    result.actions[0].seconds = 99;
    assert.deepEqual({ blueprint, context }, before);
    assert.equal(run(blueprint, context).actions[0].seconds, 3);
    assert.equal(run(blueprint, context).actions[0].name, 'CloseLater');
});
