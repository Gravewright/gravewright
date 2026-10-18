import test from 'node:test';
import assert from 'node:assert/strict';
import { blueprintContract, controlNodeTypes, defaultBlueprint, upgradeBlueprint, eventGraph, connectNodes,
    dataInputs, dataOutputs, isPureNode, nodeOutputs, validateBlueprint, validateBlueprintMemory,
    reconcileBlueprintMemory, simulateGraph } from './blueprint-model.js';

const event = 'signal:FixtureInteractClosed';
const plain = value => JSON.parse(JSON.stringify(value));
function controlBlueprint(type, params = {}, key = event) {
    const blueprint = upgradeBlueprint(defaultBlueprint()), graph = eventGraph(key);
    blueprint.graphs[key] = graph;
    graph.nodes.push({ id: 'gate', type, ...params, x: 300, y: 60 },
        { id: 'accepted', type: 'state', targetState: 'open', x: 600, y: 0 },
        { id: 'rejected', type: 'state', targetState: 'closed', x: 600, y: 300 });
    connectNodes(graph, 'event', 'next', 'gate', { version: 2 });
    connectNodes(graph, 'gate', 'true', 'accepted', { version: 2 });
    connectNodes(graph, 'gate', 'false', 'rejected', { version: 2 });
    return blueprint;
}
const run = (blueprint, context = {}, key = event) => simulateGraph(blueprint, key, 'closed', 'closed', {}, context);
function freeze(value) {
    if (value && typeof value === 'object') {
        Object.values(value).forEach(freeze);
        Object.freeze(value);
    }
    return value;
}

test('stateful controls expose only ordered execution branches and keep the contract immutable', () => {
    assert.deepEqual(controlNodeTypes, ['counter', 'once', 'cooldown']);
    for (const [type, params, labels] of [
        ['counter', { target: 3 }, ['Reached', 'Below target']],
        ['once', {}, ['First time', 'Already used']],
        ['cooldown', { seconds: 5 }, ['Ready', 'Cooling down']],
    ]) {
        const blueprint = controlBlueprint(type, params), node = blueprint.graphs[event].nodes[1];
        assert.equal(validateBlueprint(blueprint), blueprint);
        assert.equal(blueprintContract.nodes[type].category, 'control');
        assert.deepEqual(blueprintContract.nodes[type].inputs.map(port => port.kind), ['execution']);
        assert.deepEqual(blueprintContract.nodes[type].outputs.map(port => port.label), labels);
        assert.deepEqual(nodeOutputs(node), ['true', 'false']);
        assert.deepEqual(dataInputs(node), []);
        assert.deepEqual(dataOutputs(node), []);
        assert.equal(isPureNode(node), false);
        assert.throws(() => { blueprintContract.nodes[type].outputs[0].label = 'Changed'; }, TypeError);
        const before = structuredClone(blueprint.graphs[event]);
        assert.throws(() => connectNodes(blueprint.graphs[event], 'gate', 'value', 'accepted', { version: 2, input: 'target' }), /connection/);
        assert.deepEqual(blueprint.graphs[event], before);
    }
});

test('Counter increments across previews, branches after increment and saturates at the shared number limit', () => {
    const blueprint = controlBlueprint('counter', { target: 3 });
    let memory;
    for (const count of [1, 2, 3, 4]) {
        const result = run(blueprint, { memory });
        assert.equal(result.memory[event].gate.value, count);
        assert.equal(result.decisions.gate, count >= 3);
        assert.deepEqual(result.actions.map(action => action.id), [count >= 3 ? 'accepted' : 'rejected']);
        assert.deepEqual(result.trace, ['event', 'gate', count >= 3 ? 'accepted' : 'rejected']);
        assert.deepEqual(result.values, {});
        memory = result.memory;
    }
    blueprint.graphs[event].nodes[1].target = 1000000;
    const almost = { [event]: { gate: { type: 'counter', value: 999999 } } };
    const reached = run(blueprint, { memory: almost });
    assert.equal(reached.decisions.gate, true);
    assert.equal(reached.memory[event].gate.value, 1000000);
    assert.equal(run(blueprint, { memory: reached.memory }).memory[event].gate.value, 1000000);
    assert.equal(run(controlBlueprint('counter', { target: 1 })).decisions.gate, true);
});

test('Once accepts its first execution and preserves the used flag for later events', () => {
    const blueprint = controlBlueprint('once');
    const first = run(blueprint), second = run(blueprint, { memory: first.memory });
    assert.deepEqual(first.actions.map(action => action.id), ['accepted']);
    assert.deepEqual(second.actions.map(action => action.id), ['rejected']);
    assert.equal(first.decisions.gate, true);
    assert.equal(second.decisions.gate, false);
    assert.deepEqual(plain(second.memory), { [event]: { gate: { type: 'once', value: true } } });
});

test('Cooldown accepts at the exact deadline and blocked attempts do not extend it', () => {
    const blueprint = controlBlueprint('cooldown', { seconds: 5 });
    const first = run(blueprint, { now: 1000 });
    assert.equal(first.memory[event].gate.value, 6000);
    assert.equal(first.decisions.gate, true);
    for (const now of [1000, 5999]) {
        const blocked = run(blueprint, { memory: first.memory, now });
        assert.equal(blocked.decisions.gate, false);
        assert.equal(blocked.memory[event].gate.value, 6000);
        assert.deepEqual(blocked.actions.map(action => action.id), ['rejected']);
    }
    const ready = run(blueprint, { memory: first.memory, now: 6000 });
    assert.equal(ready.decisions.gate, true);
    assert.equal(ready.memory[event].gate.value, 11000);
    blueprint.graphs[event].nodes[1].seconds = .1001;
    assert.equal(run(blueprint).memory[event].gate.value, 101, 'fractional milliseconds round up');
});

test('parameter edits keep progress and a new cooldown duration applies after the old deadline', () => {
    const counter = controlBlueprint('counter', { target: 3 });
    const progress = run(counter).memory;
    counter.graphs[event].nodes[1].target = 2;
    const counted = run(counter, { memory: progress });
    assert.equal(counted.memory[event].gate.value, 2);
    assert.equal(counted.decisions.gate, true);
    const cooldown = controlBlueprint('cooldown', { seconds: 1 });
    const cooling = run(cooldown).memory;
    cooldown.graphs[event].nodes[1].seconds = 10;
    const blocked = run(cooldown, { memory: cooling, now: 500 });
    assert.equal(blocked.decisions.gate, false);
    assert.equal(blocked.memory[event].gate.value, 1000);
    assert.equal(run(cooldown, { memory: cooling, now: 1000 }).memory[event].gate.value, 11000);
});

test('control memory is isolated by event and named signals use the same execution rules', () => {
    const blueprint = controlBlueprint('once'), signal = 'signal:Again';
    blueprint.graphs[signal] = controlBlueprint('once', {}, signal).graphs[signal];
    const first = run(blueprint), signaled = run(blueprint, { memory: first.memory }, signal);
    assert.equal(signaled.decisions.gate, true, 'an identical node ID in another event has independent progress');
    assert.equal(run(blueprint, { memory: signaled.memory }).decisions.gate, false);
    assert.equal(run(blueprint, { memory: signaled.memory }, signal).decisions.gate, false);
    assert.deepEqual(Object.keys(signaled.memory).sort(), [event, signal].sort());
});

test('reconvergent branches execute a shared control once and unreachable controls keep no progress', () => {
    const blueprint = controlBlueprint('counter', { target: 2 }), graph = blueprint.graphs[event];
    graph.nodes.push({ id: 'order', type: 'sequence', x: 100, y: 100 });
    graph.edges = graph.edges.filter(edge => edge.from !== 'event');
    connectNodes(graph, 'event', 'next', 'order', { version: 2 });
    connectNodes(graph, 'order', 'then1', 'gate', { version: 2 });
    connectNodes(graph, 'order', 'then2', 'gate', { version: 2 });
    validateBlueprint(blueprint);
    const result = run(blueprint);
    assert.equal(result.memory[event].gate.value, 1);
    assert.equal(result.trace.filter(id => id === 'gate').length, 1);
    assert.deepEqual(result.actions.map(action => action.id), ['rejected']);
    graph.edges = graph.edges.filter(edge => edge.to !== 'gate');
    const unreachable = run(blueprint);
    assert.deepEqual(unreachable.trace, ['event', 'order']);
    assert.deepEqual(plain(unreachable.memory), {});
    assert.deepEqual(plain(unreachable.decisions), {});
});

test('previews clone progress and never mutate frozen input, authored graphs or other events', () => {
    const blueprint = freeze(controlBlueprint('counter', { target: 3 }));
    const context = freeze({ memory: { [event]: { gate: { type: 'counter', value: 1 } } }, now: 1234 });
    const before = structuredClone({ blueprint, context }), result = run(blueprint, context);
    assert.equal(result.memory[event].gate.value, 2);
    assert.notEqual(result.memory, context.memory);
    assert.notEqual(result.memory[event].gate, context.memory[event].gate);
    result.memory[event].gate.value = 45;
    assert.deepEqual({ blueprint, context }, before);
});

test('reconciliation removes deleted controls, deleted events and changed types while preserving layout and wires', () => {
    const blueprint = controlBlueprint('counter', { target: 3 }), memory = run(blueprint).memory;
    const graph = blueprint.graphs[event];
    graph.nodes[1].x = 2000;
    graph.nodes[1].y = 3000;
    graph.nodes[1].target = 7;
    graph.edges.reverse();
    assert.deepEqual(plain(reconcileBlueprintMemory(blueprint, memory)), plain(memory));
    const copied = reconcileBlueprintMemory(blueprint, memory);
    copied[event].gate.value = 11;
    assert.equal(memory[event].gate.value, 1);
    graph.nodes[1] = { id: 'gate', type: 'once', x: 2000, y: 3000 };
    assert.deepEqual(plain(reconcileBlueprintMemory(blueprint, memory)), {});
    assert.equal(run(blueprint, { memory }).decisions.gate, true);
    graph.nodes = graph.nodes.filter(node => node.id !== 'gate');
    assert.deepEqual(plain(reconcileBlueprintMemory(blueprint, memory)), {});
    delete blueprint.graphs[event];
    assert.deepEqual(plain(reconcileBlueprintMemory(blueprint, memory)), {});
});

test('control schema rejects legacy nodes, coercion, unsupported fields and out-of-range parameters', () => {
    for (const [type, valid, invalid] of [
        ['counter', { target: 3 }, [{ target: 0 }, { target: -1 }, { target: 1.5 }, { target: 1000001 }, { target: true }, { target: '3' }, { target: NaN }]],
        ['once', {}, [{ used: false }, { value: true }]],
        ['cooldown', { seconds: 5 }, [{ seconds: 0 }, { seconds: .099 }, { seconds: 86401 }, { seconds: NaN }, { seconds: Infinity }, { seconds: true }, { seconds: '5' }]],
    ]) {
        for (const patch of invalid) {
            const blueprint = controlBlueprint(type, { ...valid, ...patch });
            assert.throws(() => validateBlueprint(blueprint), /control|node/);
        }
        const legacy = controlBlueprint(type, valid);
        legacy.version = 1;
        assert.throws(() => validateBlueprint(legacy), /Unsupported/);
        const extra = controlBlueprint(type, { ...valid, surprise: true });
        assert.throws(() => validateBlueprint(extra), /node/);
    }
    validateBlueprint(controlBlueprint('counter', { target: 1000000 }));
    validateBlueprint(controlBlueprint('cooldown', { seconds: .1 }));
    validateBlueprint(controlBlueprint('cooldown', { seconds: 86400 }));
});

test('private control memory validates scalar types, names, exact fields and bounded row counts', () => {
    for (const memory of [null, [], { 'bad event': {} }, { 'signal:9bad': {} }, { [event]: null }, { [event]: [] },
        { [event]: { 'bad id': { type: 'once', value: true } } },
        ...[null, {}, { type: 'once', value: false }, { type: 'once', value: 1 }, { type: 'once', value: true, extra: true },
            { type: 'counter', value: true }, { type: 'counter', value: -1 }, { type: 'counter', value: 1.2 }, { type: 'counter', value: 1000001 },
            { type: 'cooldown', value: -1 }, { type: 'cooldown', value: Infinity }, { type: 'cooldown', value: Number.MAX_SAFE_INTEGER + 1 },
            { type: 'unknown', value: 1 }].map(row => ({ [event]: { gate: row } })),
    ]) assert.throws(() => validateBlueprintMemory(memory), /memory/);
    const memory = { [event]: Object.fromEntries(Array.from({ length: 128 }, (_, index) => [`gate${index}`, { type: 'counter', value: 0 }])) };
    assert.equal(validateBlueprintMemory(memory), memory);
    memory[event].overflow = { type: 'once', value: true };
    assert.throws(() => validateBlueprintMemory(memory), /memory/);
    const emptyEvents = Object.fromEntries(Array.from({ length: 128 }, (_, index) => [`signal:Event${index}`, {}]));
    validateBlueprintMemory(emptyEvents);
    emptyEvents['signal:Overflow'] = {};
    assert.throws(() => validateBlueprintMemory(emptyEvents), /memory/);
    assert.deepEqual(plain(reconcileBlueprintMemory(controlBlueprint('once'), { [event]: {} })), {});
});

test('memory reads own properties and supports safe authored IDs such as constructor', () => {
    const blueprint = controlBlueprint('once'), graph = blueprint.graphs[event];
    graph.nodes[1].id = 'constructor';
    for (const edge of graph.edges) {
        if (edge.to === 'gate') edge.to = 'constructor';
        if (edge.from === 'gate') edge.from = 'constructor';
    }
    validateBlueprint(blueprint);
    const rows = Object.create({ constructor: { type: 'once', value: true } });
    const first = run(blueprint, { memory: { [event]: rows } });
    assert.equal(first.decisions.constructor, true);
    assert.equal(Object.getPrototypeOf(first.memory), null);
    assert.equal(Object.getPrototypeOf(first.memory[event]), null);
    assert.equal(Object.hasOwn(first.memory[event], 'constructor'), true);
    Object.defineProperty(rows, 'constructor', { enumerable: true, value: { type: 'once', value: true } });
    assert.equal(run(blueprint, { memory: { [event]: rows } }).decisions.constructor, false);
    const inheritedEvent = Object.create({ [event]: rows });
    assert.equal(run(blueprint, { memory: inheritedEvent }).decisions.constructor, true);
});

test('simulation time is deterministic, bounded integer milliseconds with safe maximum deadlines', () => {
    const blueprint = controlBlueprint('cooldown', { seconds: 86400 });
    assert.equal(run(blueprint).memory[event].gate.value, 86400000);
    assert.equal(run(blueprint, { now: Number.MAX_SAFE_INTEGER - 86400000 }).memory[event].gate.value, Number.MAX_SAFE_INTEGER);
    for (const now of [-1, .5, true, null, '1000', NaN, Infinity, Number.MAX_SAFE_INTEGER - 86400000 + 1]) {
        assert.throws(() => run(blueprint, { now }), /time/);
    }
    const first = run(controlBlueprint('cooldown', { seconds: .1 }));
    assert.equal(run(controlBlueprint('cooldown', { seconds: .1 }), { memory: first.memory }).decisions.gate, false);
});

test('legacy simulations keep their previous result shape unless explicit memory is supplied', () => {
    const blueprint = defaultBlueprint();
    blueprint.graphs[event] = eventGraph(event);
    assert.deepEqual(run(blueprint), { trace: ['event'], actions: [], values: {} });
    assert.deepEqual(plain(run(blueprint, { memory: {} })), { trace: ['event'], actions: [], values: {}, memory: {} });
    delete blueprint.graphs[event];
    assert.deepEqual(run(blueprint), { trace: [], actions: [] });
    assert.deepEqual(plain(run(blueprint, { memory: {} })), { trace: [], actions: [], memory: {} });
});
