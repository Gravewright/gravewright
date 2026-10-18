import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultBlueprint, upgradeBlueprint, eventGraph, connectNodes, validateBlueprint, simulateGraph, elementInstanceNode,
    blueprintVerbEventsFor, blueprintEventsFor, blueprintEventLabel, blueprintEventMetadata, isMeaningfulBlueprintGraph,
    hasBlueprintEventPath, canInteractWithBlueprintDoor } from './blueprint-model.js';

const wire = (graph, from, output, to, input) => connectNodes(graph, from, output, to, { version: 2, ...(input ? { input } : {}) });
function draft(kind, event) {
    const blueprint = upgradeBlueprint(defaultBlueprint(kind)), graph = eventGraph(event);
    blueprint.graphs[event] = graph;
    return { blueprint, graph };
}

test('new event ports name verbs while native state remains a separate property', () => {
    for (const kind of ['door', 'lever', 'torch', 'region']) {
        const state = kind === 'door' ? 'locked' : kind === 'region' ? 'empty' : 'off';
        const element = { id: 'source', kind, state, blueprint: defaultBlueprint(kind) }, before = structuredClone(element);
        const instance = elementInstanceNode(element, kind);
        assert.deepEqual(instance.outputs.map(port => port.event), blueprintVerbEventsFor(kind));
        assert.deepEqual(instance.outputs.map(port => port.code), kind === 'region' ? ['onAreaEnter', 'onAreaExited', 'onDestroy']
            : kind === 'door' ? ['onInteract', 'onDestroy'] : ['onInteract', 'onAreaEnter', 'onAreaExited', 'onDestroy']);
        assert.equal(instance.state, state);
        assert.deepEqual(element, before);
        instance.outputs[0].code = 'edited';
        assert.equal(elementInstanceNode(element, kind).outputs[0].code, kind === 'region' ? 'onAreaEnter' : 'onInteract');
    }
});

test('removed event graphs are rejected and loading discards only their behavior', () => {
    for (const [kind, state] of [['door', 'closed'], ['lever', 'off'], ['torch', 'on'], ['region', 'occupied']]) {
        const event = kind === 'region' ? 'presence:enter' : 'interact';
        const { blueprint, graph } = draft(kind, event);
        const element = { id: 'source', kind, state, blueprint };
        graph.nodes.push({ id: 'remember', type: 'setVariable', scope: 'element', name: 'Visited', valueType: 'boolean', value: true, x: 600, y: 60 });
        wire(graph, 'event', 'next', 'remember');
        for (const removed of ['change', 'enter:on', 'exit:closed', 'interact:off']) {
            assert.equal(blueprintEventsFor(kind, blueprint).includes(removed), false);
            assert.equal(blueprintEventMetadata(removed, kind), null);
            assert.throws(() => eventGraph(removed), /event/);
            blueprint.graphs[removed] = { nodes: [{ id: 'event', type: 'event', event: removed, x: 20, y: 40 }], edges: [] };
            assert.throws(() => validateBlueprint(blueprint), /event/);
            assert.throws(() => simulateGraph(blueprint, removed, state), /event/);
        }
        const before = structuredClone(element), loaded = upgradeBlueprint(blueprint);
        assert.deepEqual(Object.keys(loaded.graphs), [event]);
        assert.deepEqual(loaded.graphs[event], graph);
        assert.deepEqual(loaded.states, blueprint.states);
        assert.deepEqual(elementInstanceNode(element, kind).outputs.map(port => port.event), blueprintVerbEventsFor(kind));
        assert.deepEqual(simulateGraph(loaded, event, state).actions.map(action => action.name), ['Visited']);
        assert.deepEqual(element, before, 'loading changes only its detached result');
        assert.throws(() => upgradeBlueprint({ ...loaded, graphs: { misspelled: graph } }), /event/);
    }
});

test('interaction starts one complete sequence and conditions retain the initial event snapshot', () => {
    const { blueprint, graph } = draft('lever', 'interact');
    graph.nodes.push({ id: 'check', type: 'condition', state: 'off', x: 300, y: 60 },
        { id: 'turnOn', type: 'state', targetState: 'on', x: 600, y: 60 },
        { id: 'onImage', type: 'sprite', appearance: 'asset', assetId: 'active', x: 900, y: 60 },
        { id: 'turnOff', type: 'state', targetState: 'off', x: 600, y: 300 },
        { id: 'offImage', type: 'sprite', appearance: 'asset', assetId: 'inactive', x: 900, y: 300 },
        { id: 'verifyStart', type: 'condition', state: 'off', x: 1200, y: 60 },
        { id: 'rememberStart', type: 'setVariable', scope: 'element', name: 'WasOff', valueType: 'boolean', value: true, x: 1500, y: 60 });
    wire(graph, 'event', 'next', 'check'); wire(graph, 'check', 'true', 'turnOn'); wire(graph, 'check', 'false', 'turnOff');
    wire(graph, 'turnOn', 'next', 'onImage'); wire(graph, 'turnOff', 'next', 'offImage'); wire(graph, 'onImage', 'next', 'verifyStart');
    wire(graph, 'verifyStart', 'true', 'rememberStart');
    const before = structuredClone(blueprint);
    validateBlueprint(blueprint, { assets: [{ id: 'active' }, { id: 'inactive' }] });
    const activated = simulateGraph(blueprint, 'interact', 'off');
    assert.deepEqual(activated.actions.slice(0, 2).map(action => [action.type, action.targetState || action.assetId]), [['state', 'on'], ['sprite', 'active']]);
    assert.equal(activated.actions[2].name, 'WasOff', 'conditions after state actions still read the initial event snapshot');
    assert.deepEqual(simulateGraph(blueprint, 'interact', 'on').actions.map(action => [action.type, action.targetState || action.assetId]),
        [['state', 'off'], ['sprite', 'inactive']]);
    assert.deepEqual(Object.keys(blueprint.graphs), ['interact']);
    assert.deepEqual(blueprint, before);
    assert.deepEqual(eventGraph('interact').nodes, [{ id: 'event', type: 'event', event: 'interact', x: 40, y: 60 }]);
});

test('test and network labels name base events without translating authored signal names', () => {
    const calls = [], t = text => { assert.equal(typeof text, 'string'); calls.push(text); return `[${text}]`; };
    assert.equal(blueprintEventLabel('interact', t), '[On interaction]');
    assert.equal(blueprintEventLabel('presence:enter', t, 'region'), '[On area enter]');
    assert.equal(blueprintEventLabel('presence:exit', t, 'region'), '[On area exit]');
    assert.equal(blueprintEventLabel('destroy', t), '[On destroy]');
    assert.equal(blueprintEventLabel('signal:Puzzle.Ready', t), '[On signal] · Puzzle.Ready');
    assert.equal(calls.includes('Puzzle.Ready'), false);
});

test('game-style event metadata preserves area graph IDs and routes timer expiry through the existing named signal', () => {
    assert.deepEqual(blueprintEventMetadata('presence:enter', 'region'), { event: 'presence:enter', label: 'On area enter', code: 'onAreaEnter' });
    assert.deepEqual(blueprintEventMetadata('presence:exit', 'region'), { event: 'presence:exit', label: 'On area exit', code: 'onAreaExited' });
    assert.deepEqual(blueprintEventMetadata('destroy', 'torch'), { event: 'destroy', label: 'On destroy', code: 'onDestroy' });
    const signal = blueprintEventMetadata('signal:TimerFinished', 'lever');
    assert.deepEqual(signal, { event: 'signal:TimerFinished', label: 'On signal', code: 'onSignal', name: 'TimerFinished' });
    signal.label = 'Edited';
    assert.equal(blueprintEventMetadata('signal:TimerFinished').label, 'On signal');
    for (const event of ['timer:TimerFinished', 'onTimer', 'onDestroy', 'constructor', 'toString', 'signal:bad name'])
        assert.equal(blueprintEventMetadata(event), null);
});

test('destroy graphs evaluate event context and branches against each native kind without changing the source', () => {
    for (const [kind, state] of [['door', 'locked'], ['lever', 'on'], ['torch', 'off'], ['region', 'occupied']]) {
        const { blueprint, graph } = draft(kind, 'destroy');
        graph.nodes.push({ id: 'eventName', type: 'eventContext', property: 'event', x: 300, y: 300 },
            { id: 'compare', type: 'compareValue', valueType: 'text', operator: 'eq', expected: 'destroy', x: 600, y: 300 },
            { id: 'check', type: 'condition', state, x: 300, y: 60 },
            { id: 'remember', type: 'setVariable', scope: 'scene', name: 'Destroyed', valueType: 'boolean', value: true, x: 600, y: 60 });
        wire(graph, 'event', 'next', 'check'); wire(graph, 'eventName', 'value', 'compare', 'value');
        wire(graph, 'compare', 'result', 'check', 'test'); wire(graph, 'check', 'true', 'remember');
        validateBlueprint(blueprint);
        const before = structuredClone(blueprint), result = simulateGraph(blueprint, 'destroy', state);
        assert.equal(result.values.eventName, 'destroy');
        assert.deepEqual(result.actions.map(row => [row.type, row.name, row.value]), [['setVariable', 'Destroyed', true]]);
        assert.deepEqual(blueprint, before);
    }
});

test('new factories use the current version and lifecycle graphs survive serialization', () => {
    const blueprint = defaultBlueprint();
    assert.equal(blueprint.version, 2);
    blueprint.graphs.destroy = eventGraph('destroy');
    assert.equal(validateBlueprint(blueprint), blueprint);
    const reopened = JSON.parse(JSON.stringify(blueprint));
    assert.deepEqual(Object.keys(reopened.graphs), ['destroy']);
    assert.deepEqual(simulateGraph(reopened, 'destroy', 'closed').trace, ['event']);
});

test('destroy simulations keep per-event control memory private and independent from interaction', () => {
    const { blueprint, graph } = draft('torch', 'destroy');
    graph.nodes.push({ id: 'once', type: 'once', x: 300, y: 60 },
        { id: 'remember', type: 'setVariable', scope: 'scene', name: 'DestroyCounted', valueType: 'boolean', value: true, x: 600, y: 60 });
    wire(graph, 'event', 'next', 'once'); wire(graph, 'once', 'true', 'remember');
    blueprint.graphs.interact = structuredClone(graph); blueprint.graphs.interact.nodes[0].event = 'interact';
    validateBlueprint(blueprint);
    const before = structuredClone(blueprint), first = simulateGraph(blueprint, 'destroy', 'off');
    assert.equal(first.actions.length, 1);
    assert.deepEqual(simulateGraph(blueprint, 'destroy', 'off', 'off', {}, { memory: first.memory }).actions, []);
    assert.equal(simulateGraph(blueprint, 'interact', 'off', 'off', {}, { memory: first.memory }).actions.length, 1);
    assert.deepEqual(blueprint, before);
});

test('event roots carry no state checks, configurable filters or branch outputs', () => {
    const blueprint = defaultBlueprint('lever');
    for (const event of blueprintVerbEventsFor('lever')) {
        const graph = blueprint.graphs[event] = eventGraph(event);
        for (const field of ['state', 'previous', 'targetState', 'filter', 'expected']) {
            graph.nodes[0][field] = 'off';
            assert.throws(() => validateBlueprint(blueprint), /node/);
            delete graph.nodes[0][field];
        }
        graph.nodes.push({ id: 'move', type: 'state', targetState: 'on', x: 718, y: 418 });
        assert.throws(() => wire(graph, 'event', 'true', 'move'), /connection/);
        wire(graph, 'event', 'next', 'move');
    }
    const element = { id: 'lever', lever: { state: 'off' }, blueprint }, before = structuredClone(element);
    assert.deepEqual(elementInstanceNode(element).outputs.map(port => port.event), ['interact', 'presence:enter', 'presence:exit', 'destroy']);
    assert.deepEqual(element, before);
    assert.equal(validateBlueprint(blueprint), blueprint);
});

test('authored nodes and an execution path are distinguished without giving the event an implicit decision', () => {
    const { blueprint, graph } = draft('torch', 'interact');
    assert.equal(isMeaningfulBlueprintGraph(undefined), false);
    assert.equal(isMeaningfulBlueprintGraph(graph), false);
    assert.equal(hasBlueprintEventPath(blueprint, 'interact'), false);
    graph.nodes.push({ id: 'toggle', type: 'state', targetState: 'on', x: 400, y: 60 });
    assert.equal(isMeaningfulBlueprintGraph(graph), true, 'a disconnected authored card still remains visible');
    assert.equal(hasBlueprintEventPath(blueprint, 'interact'), false, 'a disconnected card has no execution path');
    wire(graph, 'event', 'next', 'toggle');
    assert.equal(hasBlueprintEventPath(blueprint, 'interact'), true);
    assert.equal(hasBlueprintEventPath(blueprint, 'change'), false);
});

test('native locked-door handles allow an authorized interaction without exposing the graph or bypassing its disabled flag', () => {
    const { blueprint, graph } = draft('door', 'interact');
    const door = { kind: 'door', door_state: 'locked', blueprint };
    assert.equal(canInteractWithBlueprintDoor(door), false);
    graph.nodes.push({ id: 'check', type: 'condition', state: 'locked', x: 300, y: 60 });
    wire(graph, 'event', 'next', 'check');
    assert.equal(canInteractWithBlueprintDoor(door), true);
    assert.equal(canInteractWithBlueprintDoor({ kind: 'door', door_state: 'locked', blueprintInteraction: true }), true,
        'the filtered player projection conveys only whether a handler exists');
    assert.equal(canInteractWithBlueprintDoor({ ...door, interactionEnabled: false }), false);
    assert.equal(canInteractWithBlueprintDoor({ ...door, interactionEnabled: false }, true), true, 'GMs retain manual control');
    assert.equal(canInteractWithBlueprintDoor({ kind: 'door', door_state: 'locked', blueprintInteraction: false }), false);
    assert.equal(canInteractWithBlueprintDoor({ kind: 'door', door_state: 'closed' }), true);
    assert.equal(canInteractWithBlueprintDoor({ kind: 'wall', door_state: 'closed' }), false);
    assert.equal(canInteractWithBlueprintDoor(null), false);
});

test('one interaction graph can toggle a mechanism by checking its current state', () => {
    const { blueprint, graph } = draft('torch', 'interact');
    graph.nodes.push({ id: 'check', type: 'condition', state: 'on', x: 300, y: 60 },
        { id: 'off', type: 'state', targetState: 'off', x: 600, y: 60 },
        { id: 'on', type: 'state', targetState: 'on', x: 600, y: 300 });
    wire(graph, 'event', 'next', 'check'); wire(graph, 'check', 'true', 'off'); wire(graph, 'check', 'false', 'on');
    validateBlueprint(blueprint);
    const before = structuredClone(blueprint);
    assert.deepEqual(simulateGraph(blueprint, 'interact', 'off').actions.map(row => row.targetState), ['on']);
    assert.deepEqual(simulateGraph(blueprint, 'interact', 'on').actions.map(row => row.targetState), ['off']);
    assert.deepEqual(blueprint, before);
});

test('an interaction exposes context values without changing the event snapshot', () => {
    const { blueprint, graph } = draft('torch', 'interact');
    graph.nodes.push({ id: 'check', type: 'condition', state: 'on', x: 300, y: 60 },
        { id: 'light', type: 'flame', enabled: true, x: 600, y: 60 },
        { id: 'dark', type: 'flame', enabled: false, x: 600, y: 300 },
        { id: 'previous', type: 'eventContext', property: 'previous', x: 300, y: 600 },
        { id: 'wasOff', type: 'compare', state: 'off', x: 600, y: 600 },
        { id: 'verify', type: 'condition', state: 'on', x: 900, y: 300 });
    wire(graph, 'event', 'next', 'check'); wire(graph, 'check', 'true', 'light'); wire(graph, 'check', 'false', 'dark');
    wire(graph, 'light', 'next', 'verify'); wire(graph, 'previous', 'value', 'wasOff', 'value'); wire(graph, 'wasOff', 'result', 'verify', 'test');
    validateBlueprint(blueprint);
    const result = simulateGraph(blueprint, 'interact', 'on', 'off', {}, { eventContext: { previous: 'on', state: 'off' } });
    assert.deepEqual(result.actions.map(row => [row.type, row.enabled]), [['flame', true]]);
    assert.equal(result.values.previous, 'off', 'trusted event snapshots take precedence over preview metadata');
    assert.equal(result.values.wasOff, true);
    assert.deepEqual(simulateGraph(blueprint, 'interact', 'off', 'on').actions.map(row => row.enabled), [false]);
});

test('loading an old container discards removed graphs and promotes its format without executing it', () => {
    const blueprint = { ...defaultBlueprint(), version: 1, graphs: { 'enter:closed': { nodes: [], edges: [] }, change: null } };
    const before = structuredClone(blueprint);
    assert.throws(() => validateBlueprint(blueprint), /Unsupported/);
    assert.throws(() => simulateGraph(blueprint, 'interact', 'closed'), /Unsupported/);
    const upgraded = upgradeBlueprint(blueprint);
    assert.deepEqual(upgraded.graphs, {});
    assert.equal(upgraded.version, 2);
    assert.equal(validateBlueprint(upgraded), upgraded);
    assert.deepEqual(blueprint, before);
});

test('interaction controls retain progress only in private simulation memory', () => {
    const { blueprint, graph } = draft('lever', 'interact');
    graph.nodes.push({ id: 'once', type: 'once', x: 300, y: 60 },
        { id: 'action', type: 'state', targetState: 'on', x: 600, y: 60 });
    wire(graph, 'event', 'next', 'once'); wire(graph, 'once', 'true', 'action');
    validateBlueprint(blueprint);
    const before = structuredClone(blueprint), first = simulateGraph(blueprint, 'interact', 'on', 'off');
    assert.equal(first.actions.length, 1);
    const memory = structuredClone(first.memory), beforeMemory = structuredClone(memory);
    const second = simulateGraph(blueprint, 'interact', 'off', 'on', {}, { memory });
    assert.deepEqual(second.actions, []);
    assert.deepEqual(memory, beforeMemory);
    assert.deepEqual(blueprint, before);
});

test('regions start per-token crossings without change or native interaction events', () => {
    const blueprint = defaultBlueprint('region');
    for (const event of blueprintVerbEventsFor('region')) blueprint.graphs[event] = eventGraph(event);
    validateBlueprint(blueprint);
    assert.deepEqual(simulateGraph(blueprint, 'presence:enter', 'occupied', 'occupied').trace, ['event']);
    assert.throws(() => validateBlueprint({ ...blueprint, graphs: { interact: eventGraph('interact') } }), /event/);
    assert.throws(() => simulateGraph(blueprint, 'interact', 'empty'), /event/);
});

test('ordinary and Empty Objects expose area entry points independently of off/on state', () => {
    for (const [kind, empty] of [['lever', false], ['torch', false], ['lever', true]]) {
        const blueprint = defaultBlueprint(kind), element = { id: 'object', kind, [kind]: { state: 'off' }, blueprint,
            ...(empty ? { empty: true, assetId: null } : { assetId: 'native-image' }) };
        assert.deepEqual(elementInstanceNode(element, kind).outputs.map(port => port.event),
            ['interact', 'presence:enter', 'presence:exit', 'destroy']);
        for (const event of ['presence:enter', 'presence:exit']) {
            blueprint.graphs[event] = eventGraph(event);
            assert.equal(validateBlueprint(blueprint, { element }), blueprint);
            const before = structuredClone(element);
            for (const state of ['off', 'on']) {
                const result = simulateGraph(blueprint, event, state);
                assert.deepEqual(result.trace, ['event']);
                assert.deepEqual(result.actions, [], 'entering or leaving never toggles the object implicitly');
            }
            assert.deepEqual(element, before);
        }
        assert.deepEqual(upgradeBlueprint(blueprint), blueprint, 'reopening preserves authored area graphs');
    }
    const door = defaultBlueprint('door');
    door.graphs['presence:enter'] = eventGraph('presence:enter');
    assert.throws(() => validateBlueprint(door), /event/);
});

test('area simulation supplies its transition and token metadata without replacing object state', () => {
    for (const kind of ['lever', 'torch']) for (const event of ['presence:enter', 'presence:exit']) {
        const { blueprint, graph } = draft(kind, event);
        for (const [index, property] of ['presence', 'tokenId', 'count'].entries()) {
            const valueType = property === 'count' ? 'number' : 'text';
            graph.nodes.push({ id: `read${index}`, type: 'eventContext', property, x: 350, y: index * 120 },
                { id: `remember${index}`, type: 'setVariable', scope: 'element', name: `Value${index}`, valueType,
                    value: valueType === 'number' ? 0 : '', x: 650, y: index * 120 });
            wire(graph, index ? `remember${index - 1}` : 'event', 'next', `remember${index}`);
            wire(graph, `read${index}`, 'value', `remember${index}`, 'value');
        }
        graph.nodes.push({ id: 'check', type: 'condition', state: 'off', x: 900, y: 120 },
            { id: 'activate', type: 'state', targetState: 'on', x: 1200, y: 120 });
        wire(graph, 'remember2', 'next', 'check'); wire(graph, 'check', 'true', 'activate');
        validateBlueprint(blueprint);
        const tokenId = '00000000-0000-4000-8000-000000000001';
        for (const state of ['off', 'on']) {
            const result = simulateGraph(blueprint, event, state, state, {}, { eventContext: { tokenId, count: 2 } });
            assert.equal(result.values.read0, event.slice(9));
            assert.equal(result.values.read1, tokenId);
            assert.equal(result.values.read2, 2);
            assert.equal(result.trace.includes('activate'), state === 'off', 'the explicit condition reads off/on, never occupied/empty');
            assert.deepEqual(result.actions.filter(action => action.type === 'state').map(action => action.targetState), state === 'off' ? ['on'] : []);
        }
    }
});
