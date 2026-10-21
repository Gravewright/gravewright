import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultBlueprint, eventGraph, connectNodes, validateBlueprint, simulateGraph, blueprintAppearance,
    blueprintContract, doorInstanceNode, elementInstanceNode, blueprintStatesFor, blueprintAllStates, upgradeBlueprint,
    dataInputs, dataOutputs, blueprintEventsFor, isBlueprintSignalEvent, typedDefault, validateVariableSnapshot } from './blueprint-model.js';

test('Empty Object events run ordinary logic and state actions without acquiring artwork', () => {
    const element = { id: 'empty', empty: true, assetId: null, lever: { state: 'off' } }, blueprint = defaultBlueprint('lever');
    const graph = blueprint.graphs.interact = eventGraph('interact');
    graph.nodes.push({ id: 'check', type: 'condition', state: 'off', x: 300, y: 100 },
        { id: 'activate', type: 'state', targetState: 'on', x: 600, y: 100 });
    connectNodes(graph, 'event', 'next', 'check'); connectNodes(graph, 'check', 'true', 'activate');
    assert.equal(validateBlueprint(blueprint, { element }), blueprint);
    assert.deepEqual(simulateGraph(blueprint, 'interact', 'off').actions.map(row => row.type), ['state']);
    for (const appearance of ['inherit', 'hidden', 'asset']) {
        const displayed = { ...element, blueprint: { ...blueprint, states: { off: { appearance, assetId: 'any-image' } } } };
        assert.deepEqual(blueprintAppearance(displayed), { visible: false, assetId: null });
    }
    for (const appearance of ['hidden', 'asset']) {
        const candidate = structuredClone(blueprint); candidate.states.off = { appearance, ...(appearance === 'asset' ? { assetId: 'image' } : {}) };
        assert.throws(() => validateBlueprint(candidate, { element, assets: [{ id: 'image' }] }), /cannot receive images/);
    }
    graph.nodes.push({ id: 'image', type: 'sprite', appearance: 'hidden', x: 300, y: 400 });
    assert.equal(validateBlueprint(blueprint, { element }), blueprint);
});

test('Empty Object image actions allow drafts and mixed target groups without granting owner artwork', () => {
    const ownerId = '00000000-0000-4000-8000-000000000011', otherId = '00000000-0000-4000-8000-000000000012';
    const imageId = '00000000-0000-4000-8000-000000000013', element = { id: ownerId, empty: true };
    const blueprint = defaultBlueprint('lever'), graph = blueprint.graphs.interact = eventGraph('interact');
    graph.nodes.push({ id: 'image', type: 'setAppearance', assetId: imageId, x: 300, y: 100 });
    connectNodes(graph, 'event', 'next', 'image');
    const resources = { element, assets: [{ id: imageId }] };
    assert.equal(validateBlueprint(blueprint, resources), blueprint);
    graph.nodes.push({ id: 'target', type: 'reference', targetId: ownerId, x: 300, y: 400 });
    connectNodes(graph, 'target', 'door', 'image', { input: 'target' });
    assert.equal(validateBlueprint(blueprint, resources), blueprint);
    graph.nodes.at(-1).targetId = otherId;
    assert.equal(validateBlueprint(blueprint, resources), blueprint);
    graph.nodes[2] = { id: 'target', type: 'elementGroup', name: 'Linked objects', memberType: 'element', targetIds: [otherId, ownerId], x: 300, y: 400 };
    graph.edges.at(-1).output = 'targets';
    assert.equal(validateBlueprint(blueprint, resources), blueprint);
    graph.nodes[2].targetIds = [otherId];
    assert.equal(validateBlueprint(blueprint, resources), blueprint);
    assert.deepEqual(blueprintAppearance({ ...element, blueprint, lever: { state: 'off' } }), { visible: false, assetId: null });
});

test('simulation follows the selected condition branch without changing the draft', () => {
    const blueprint = defaultBlueprint(), graph = eventGraph('signal:FixtureInteractClosed');
    blueprint.graphs['signal:FixtureInteractClosed'] = graph;
    graph.nodes.push(
        { id: 'condition', type: 'condition', state: 'closed', x: 300, y: 60 },
        { id: 'open', type: 'state', targetState: 'open', x: 600, y: 60 },
        { id: 'light', type: 'light', targetId: 'torch', enabled: true, x: 900, y: 60 },
        { id: 'sound', type: 'sound', trackId: 'locked', volume: .4, x: 600, y: 300 },
    );
    connectNodes(graph, 'event', 'next', 'condition');
    connectNodes(graph, 'condition', 'true', 'open');
    connectNodes(graph, 'open', 'next', 'light');
    connectNodes(graph, 'condition', 'false', 'sound');
    const before = structuredClone(blueprint);
    const result = simulateGraph(blueprint, 'signal:FixtureInteractClosed', 'closed');
    assert.deepEqual(result.trace, ['event', 'condition', 'open', 'light']);
    assert.deepEqual(result.actions.map(action => action.type), ['state', 'light']);
    assert.deepEqual(simulateGraph(blueprint, 'signal:FixtureInteractClosed', 'locked').trace, ['event', 'condition', 'sound']);
    result.actions[1].enabled = false;
    assert.deepEqual(blueprint, before);
});

test('invalid connections preserve the existing output and reject cycles', () => {
    const graph = eventGraph('signal:FixtureEnterOpen');
    graph.nodes.push(...['first', 'second'].map((id, index) => ({ id, type: 'state', targetState: 'open', x: 300 + index * 300, y: 60 })));
    connectNodes(graph, 'event', 'next', 'first');
    connectNodes(graph, 'first', 'next', 'second');
    const before = structuredClone(graph);
    assert.throws(() => connectNodes(graph, 'second', 'next', 'first'), /cycle/);
    assert.deepEqual(graph, before);
    assert.throws(() => connectNodes(graph, 'event', 'next', 'event'), /Invalid/);
    assert.deepEqual(graph, before);
    connectNodes(graph, 'event', 'next', 'second');
    assert.deepEqual(graph.edges.filter(edge => edge.from === 'event'), [
        { from: 'event', output: 'next', to: 'first', kind: 'execution' },
        { from: 'event', output: 'next', to: 'second', kind: 'execution' },
    ]);
});

test('validation checks state images and action references against the current resources', () => {
    const blueprint = defaultBlueprint(), graph = eventGraph('signal:FixtureEnterOpen');
    blueprint.states.open = { appearance: 'asset', assetId: 'open-image' };
    graph.nodes.push({ id: 'light', type: 'light', targetId: 'torch', enabled: true, x: 300, y: 60 },
        { id: 'sound', type: 'sound', trackId: 'creak', volume: .5, x: 600, y: 60 });
    blueprint.graphs['signal:FixtureEnterOpen'] = graph;
    const resources = { assets: [{ id: 'open-image' }], lights: [{ id: 'torch' }], sounds: [{ id: 'creak' }] };
    assert.equal(validateBlueprint(blueprint, resources), blueprint);
    assert.throws(() => validateBlueprint(blueprint, { ...resources, assets: [] }), /image/);
    assert.throws(() => validateBlueprint(blueprint, { ...resources, lights: [] }), /light/);
    assert.throws(() => validateBlueprint(blueprint, { ...resources, sounds: [] }), /sound/);
    graph.nodes[2].volume = 2;
    assert.throws(() => validateBlueprint(blueprint, resources), /sound/);
});

test('appearance preserves native door states and supports an explicit open image', () => {
    const door = { state: 'closed', assetId: 'base-image' };
    assert.deepEqual(blueprintAppearance(door), { visible: true, assetId: 'base-image' });
    door.state = 'open';
    assert.deepEqual(blueprintAppearance(door), { visible: false, assetId: 'base-image' });
    door.blueprint = defaultBlueprint();
    door.blueprint.states.open = { appearance: 'asset', assetId: 'open-image' };
    assert.deepEqual(blueprintAppearance(door), { visible: true, assetId: 'open-image' });
    door.blueprint.states.open = { appearance: 'hidden' };
    assert.deepEqual(blueprintAppearance(door), { visible: false, assetId: null });
});

test('door instance ports expose verbs and native state without adding object data to the blueprint', () => {
    const door = { id: 'door_north', name: 'North door', state: 'locked', blueprint: defaultBlueprint() };
    const before = structuredClone(door), instance = doorInstanceNode(door);
    assert.deepEqual(instance.outputs.map(({ id, event, color, kind }) => ({ id, event, color, kind })), [
        { id: 'interact', event: 'interact', color: 'green', kind: 'execution' },
        { id: 'destroy', event: 'destroy', color: 'red', kind: 'execution' },
    ]);
    assert.equal(instance.id, 'object:door_north');
    assert.equal(instance.sourceId, door.id);
    assert.equal(instance.name, door.name);
    assert.equal(instance.state, 'locked');
    instance.outputs[0].label = 'Edited label';
    door.state = 'open';
    assert.equal(doorInstanceNode(door).state, 'open', 'the view reads the real current state');
    assert.equal(doorInstanceNode(door).outputs[0].label, 'On interaction');
    door.state = 'locked';
    assert.deepEqual(door, before);
    assert.equal(blueprintContract.portKinds.execution.implemented, true);
    assert.equal(blueprintContract.portKinds.reference.implemented, false);
    assert.equal(blueprintContract.portKinds.value.implemented, true);
    assert.deepEqual(Object.keys(blueprintContract.nodes),
        ['door', 'lever', 'torch', 'region', 'event', 'light', 'sound', 'state', 'interact', 'flame', 'sprite', 'condition', 'sequence', 'property', 'compare', 'all', 'any', 'reference', 'reveal', 'barrier', 'soundControl',
            'getVariable', 'setVariable', 'compareValue', 'emitEvent', 'counter', 'once', 'cooldown', 'delay', 'timer', 'switch', 'random',
            'elementGroup', 'lightReference', 'soundReference', 'eventContext', 'move', 'rotate', 'setInteraction', 'setRegion',
            'showMessage', 'showHandout', 'requestRoll', 'setQuestStatus', 'cameraFocus', 'teleport', 'setVisibility', 'setAppearance']);
    assert.throws(() => { blueprintContract.nodes.door.outputs[0].color = 'red'; }, TypeError);
    assert.throws(() => doorInstanceNode({ id: 'another', state: 'fake' }), /Invalid/);
});

test('normalizing an older container keeps only supported graphs and does not mutate its source', () => {
    const blueprint = { ...defaultBlueprint(), version: 1 };
    for (const event of ['signal:FixtureEnterOpen', 'signal:FixtureExitClosed', 'signal:FixtureInteractLocked']) {
        const graph = eventGraph(event);
        graph.nodes.push({ id: 'action', type: 'state', targetState: 'closed', x: 817, y: 392 });
        connectNodes(graph, 'event', 'next', 'action');
        for (const edge of graph.edges) delete edge.kind;
        blueprint.graphs[event] = graph;
    }
    blueprint.graphs['enter:open'] = { nodes: [], edges: [] };
    blueprint.graphs.change = null;
    const originalJSON = JSON.stringify(blueprint), upgraded = upgradeBlueprint(blueprint);
    assert.equal(upgraded.version, 2);
    assert.equal(JSON.stringify(blueprint), originalJSON, 'view conversion never rewrites the original');
    assert.deepEqual(Object.keys(upgraded), ['version', 'kind', 'states', 'graphs']);
    assert.deepEqual(upgraded.states, blueprint.states);
    assert.deepEqual(Object.keys(upgraded.graphs), ['signal:FixtureEnterOpen', 'signal:FixtureExitClosed', 'signal:FixtureInteractLocked']);
    for (const event of Object.keys(upgraded.graphs)) {
        assert.deepEqual(upgraded.graphs[event].nodes, blueprint.graphs[event].nodes);
        assert.deepEqual(upgraded.graphs[event].edges, [{ from: 'event', output: 'next', to: 'action', kind: 'execution' }]);
        assert.deepEqual(simulateGraph(upgraded, event, 'locked').actions.map(action => action.targetState), ['closed']);
    }
    assert.equal(validateBlueprint(upgraded), upgraded);
    assert.deepEqual(upgradeBlueprint(upgraded), upgraded);
    upgraded.states.open.appearance = 'hidden';
    upgraded.graphs['signal:FixtureEnterOpen'].nodes[1].x = 123;
    assert.equal(JSON.stringify(blueprint), originalJSON);
});

function branchingBlueprint() {
    const blueprint = upgradeBlueprint(defaultBlueprint()), graph = eventGraph('interact');
    blueprint.graphs['interact'] = graph;
    graph.nodes.push(
        { id: 'first', type: 'state', targetState: 'open', x: 300, y: 0 },
        { id: 'second', type: 'light', targetId: 'torch', enabled: true, x: 300, y: 250 },
        { id: 'shared', type: 'sound', trackId: 'creak', volume: .4, x: 600, y: 0 },
    );
    for (const [from, to] of [['event', 'first'], ['event', 'second'], ['first', 'shared'], ['second', 'shared']]) {
        connectNodes(graph, from, 'next', to, { version: 2 });
    }
    return blueprint;
}

test('version two fanout follows persisted branch order and executes reconvergent actions once', () => {
    const blueprint = branchingBlueprint(), before = structuredClone(blueprint);
    const result = simulateGraph(blueprint, 'interact', 'closed');
    assert.deepEqual(result.trace, ['event', 'first', 'shared', 'second']);
    assert.deepEqual(result.actions.map(node => node.type), ['state', 'sound', 'light']);
    result.actions[1].volume = 1;
    assert.deepEqual(blueprint, before);
    assert.equal(validateBlueprint(blueprint, { lights: [{ id: 'torch' }], sounds: [{ id: 'creak' }] }), blueprint);
    blueprint.graphs['interact'].edges.reverse();
    assert.deepEqual(simulateGraph(blueprint, 'interact', 'closed').trace, ['event', 'second', 'shared', 'first']);
});

test('version two conditions select a branch using the event initial state', () => {
    const blueprint = branchingBlueprint(), graph = blueprint.graphs['interact'];
    graph.nodes.push({ id: 'condition', type: 'condition', state: 'closed', x: 600, y: 250 });
    graph.edges = [];
    for (const [from, output, to] of [['event', 'next', 'first'], ['first', 'next', 'condition'],
        ['condition', 'true', 'second'], ['condition', 'true', 'shared'], ['condition', 'false', 'shared']]) {
        connectNodes(graph, from, output, to, { version: 2 });
    }
    assert.deepEqual(simulateGraph(blueprint, 'interact', 'closed').trace, ['event', 'first', 'condition', 'second', 'shared']);
    assert.deepEqual(simulateGraph(blueprint, 'interact', 'locked').trace, ['event', 'first', 'condition', 'shared']);
});

test('version two duplicate and cycle attempts preserve every existing branch', () => {
    const blueprint = branchingBlueprint(), graph = blueprint.graphs['interact'];
    const before = structuredClone(graph);
    assert.throws(() => connectNodes(graph, 'event', 'next', 'first', { version: 2 }), /Duplicate/);
    assert.deepEqual(graph, before);
    assert.throws(() => connectNodes(graph, 'shared', 'next', 'first', { version: 2 }), /cycle/);
    assert.deepEqual(graph, before);
    const typed = graph.edges[0];
    delete typed.kind;
    assert.throws(() => validateBlueprint(blueprint), /connection/);
    typed.kind = 'reference';
    assert.throws(() => validateBlueprint(blueprint), /connection/);
    assert.throws(() => upgradeBlueprint(blueprint), /connection/);
});

test('old containers require normalization before validation and unsupported object nodes stay invalid', () => {
    const blueprint = branchingBlueprint();
    blueprint.version = 1;
    assert.throws(() => validateBlueprint(blueprint), /Unsupported/);
    for (const edge of blueprint.graphs['interact'].edges) delete edge.kind;
    assert.throws(() => validateBlueprint(blueprint), /Unsupported/);
    assert.equal(blueprint.version, 1);
    assert.throws(() => validateBlueprint({ ...defaultBlueprint(), sourceId: 'door_north' }), /state/);
    const graph = eventGraph('signal:FixtureEnterOpen');
    graph.nodes.push({ id: 'object:door_north', type: 'door', x: 300, y: 0 });
    const invalid = { ...defaultBlueprint(), graphs: { 'signal:FixtureEnterOpen': graph } };
    assert.throws(() => validateBlueprint(invalid), /node/);
});

function dataBlueprint() {
    const blueprint = { ...defaultBlueprint(), version: 2 }, graph = eventGraph('interact');
    blueprint.graphs['interact'] = graph;
    graph.nodes.push(
        { id: 'previous', type: 'property', property: 'previous', x: 300, y: 260 },
        { id: 'compare', type: 'compare', state: 'locked', x: 560, y: 260 },
        { id: 'check', type: 'condition', state: 'open', x: 300, y: 60 },
        { id: 'unlocked', type: 'state', targetState: 'open', x: 600, y: 0 },
        { id: 'relock', type: 'state', targetState: 'locked', x: 600, y: 120 },
    );
    connectNodes(graph, 'event', 'next', 'check', { version: 2 });
    connectNodes(graph, 'check', 'true', 'unlocked', { version: 2 });
    connectNodes(graph, 'check', 'false', 'relock', { version: 2 });
    connectNodes(graph, 'previous', 'value', 'compare', { version: 2, input: 'value' });
    connectNodes(graph, 'compare', 'result', 'check', { version: 2, input: 'test' });
    return blueprint;
}

test('typed data edges feed a condition from the previous state like the server', () => {
    const blueprint = dataBlueprint(), graph = blueprint.graphs['interact'];
    validateBlueprint(blueprint);
    assert.deepEqual(graph.edges.at(-1), { from: 'compare', output: 'result', to: 'check', input: 'test', kind: 'data' });
    const unlocked = simulateGraph(blueprint, 'interact', 'closed', 'locked');
    assert.deepEqual(unlocked.trace, ['event', 'check', 'previous', 'compare', 'unlocked']);
    assert.deepEqual(unlocked.values, { previous: 'locked', compare: true });
    assert.deepEqual(simulateGraph(blueprint, 'interact', 'closed', 'open').trace, ['event', 'check', 'previous', 'compare', 'relock']);
    assert.deepEqual(simulateGraph(blueprint, 'interact', 'closed').actions.map(action => action.id), ['relock']);
    const before = structuredClone(graph);
    assert.throws(() => connectNodes(graph, 'previous', 'value', 'check', { version: 2, input: 'test' }), /connection/, 'state into boolean');
    assert.throws(() => connectNodes(graph, 'previous', 'value', 'compare', { version: 2, input: 'value' }), /one connection/);
    assert.throws(() => connectNodes(graph, 'event', 'next', 'previous', { version: 2 }), /connection/, 'pure nodes have no execution input');
    assert.throws(() => connectNodes(graph, 'previous', 'value', 'compare', { version: 1, input: 'value' }), /Unsupported/);
    assert.deepEqual(graph, before);
    const untyped = structuredClone(blueprint);
    delete untyped.graphs['interact'].edges.at(-1).input;
    assert.throws(() => validateBlueprint(untyped), /connection/);
});

test('sequence runs numbered outputs in order and change sprite needs an available image', () => {
    const blueprint = { ...defaultBlueprint(), version: 2 }, graph = eventGraph('signal:FixtureInteractOpen');
    blueprint.graphs['signal:FixtureInteractOpen'] = graph;
    graph.nodes.push(
        { id: 'sequence', type: 'sequence', x: 300, y: 0 },
        { id: 'art', type: 'sprite', appearance: 'asset', assetId: 'oak', x: 600, y: 0 },
        { id: 'close', type: 'state', targetState: 'closed', x: 600, y: 200 },
    );
    connectNodes(graph, 'event', 'next', 'sequence', { version: 2 });
    connectNodes(graph, 'sequence', 'then2', 'close', { version: 2 });
    connectNodes(graph, 'sequence', 'then1', 'art', { version: 2 });
    assert.throws(() => validateBlueprint(blueprint), /Change sprite/);
    validateBlueprint(blueprint, { assets: [{ id: 'oak' }] });
    assert.deepEqual(simulateGraph(blueprint, 'signal:FixtureInteractOpen', 'open').actions.map(action => action.id), ['art', 'close']);
    graph.nodes[2] = { ...graph.nodes[2], appearance: 'hidden' };
    assert.throws(() => validateBlueprint(blueprint, { assets: [{ id: 'oak' }] }), /node/, 'only image sprites keep an asset');
    delete graph.nodes[2].assetId;
    validateBlueprint(blueprint);
    const legacy = { ...structuredClone(blueprint), version: 1 };
    for (const edge of legacy.graphs['signal:FixtureInteractOpen'].edges) delete edge.kind;
    assert.throws(() => validateBlueprint(legacy), /Unsupported/, 'older formats must be normalized before use');
});

test('element references target other doors and read their state without changing Self', () => {
    const other = 'b8f1c5e2-0c4d-4a52-9d0f-6f3a3c9b1e21', blueprint = { ...defaultBlueprint(), version: 2 };
    const graph = eventGraph('signal:FixtureEnterOpen');
    blueprint.graphs['signal:FixtureEnterOpen'] = graph;
    graph.nodes.push(
        { id: 'ref', type: 'reference', targetId: other, x: 300, y: 260 },
        { id: 'prop', type: 'property', property: 'state', x: 560, y: 260 },
        { id: 'cmp', type: 'compare', state: 'locked', x: 820, y: 260 },
        { id: 'check', type: 'condition', state: 'open', x: 300, y: 0 },
        { id: 'act', type: 'state', targetState: 'open', x: 600, y: 0 },
        { id: 'show', type: 'reveal', x: 600, y: 120 },
    );
    connectNodes(graph, 'event', 'next', 'check', { version: 2 });
    connectNodes(graph, 'check', 'true', 'act', { version: 2 });
    connectNodes(graph, 'check', 'false', 'show', { version: 2 });
    for (const [from, output, to, input] of [['ref', 'door', 'prop', 'target'], ['prop', 'value', 'cmp', 'value'],
        ['cmp', 'result', 'check', 'test'], ['ref', 'door', 'act', 'target']]) connectNodes(graph, from, output, to, { version: 2, input });
    validateBlueprint(blueprint);
    const locked = simulateGraph(blueprint, 'signal:FixtureEnterOpen', 'open', 'closed', { [other]: 'locked' });
    assert.deepEqual(locked.actions.map(action => [action.id, action.target]), [['act', other]]);
    const missing = simulateGraph(blueprint, 'signal:FixtureEnterOpen', 'open', 'closed', {});
    assert.equal(missing.values.prop, null);
    assert.deepEqual(missing.actions.map(action => [action.id, action.target]), [['show', undefined]]);
    assert.throws(() => connectNodes(graph, 'ref', 'door', 'check', { version: 2, input: 'test' }), /connection/);
    const invalid = structuredClone(blueprint);
    invalid.graphs['signal:FixtureEnterOpen'].nodes[1].targetId = 'door-b';
    assert.throws(() => validateBlueprint(invalid), /node/);
});

test('authorized state changes, barriers and sound controls validate like the server', () => {
    const blueprint = { ...defaultBlueprint(), version: 2 }, graph = eventGraph('signal:FixtureEnterOpen');
    blueprint.graphs['signal:FixtureEnterOpen'] = graph;
    graph.nodes.push(
        { id: 'act', type: 'state', targetState: 'open', players: true, x: 300, y: 0 },
        { id: 'wall', type: 'barrier', channel: 'sound', mode: 'attenuate', x: 600, y: 0 },
        { id: 'hush', type: 'soundControl', trackId: 'bell', action: 'volume', volume: .2, x: 900, y: 0 },
    );
    connectNodes(graph, 'event', 'next', 'act', { version: 2 });
    connectNodes(graph, 'act', 'next', 'wall', { version: 2 });
    connectNodes(graph, 'wall', 'next', 'hush', { version: 2 });
    validateBlueprint(blueprint, { sounds: [{ id: 'bell' }] });
    assert.deepEqual(simulateGraph(blueprint, 'signal:FixtureEnterOpen', 'open').actions.map(action => action.id), ['act', 'wall', 'hush']);
    assert.throws(() => validateBlueprint(blueprint), /sound/);
    for (const change of [{ index: 1, players: false }, { index: 2, channel: 'vision' }, { index: 3, action: 'pause' }]) {
        const invalid = structuredClone(blueprint), { index, ...fields } = change;
        Object.assign(invalid.graphs['signal:FixtureEnterOpen'].nodes[index], fields);
        assert.throws(() => validateBlueprint(invalid, { sounds: [{ id: 'bell' }] }), /node/, JSON.stringify(change));
    }
});

test('lever documents own off/on values while event entry points stay independent of state', () => {
    const lever = defaultBlueprint('lever');
    assert.equal(lever.version, 2);
    assert.deepEqual(blueprintStatesFor('lever'), ['off', 'on']);
    assert.deepEqual(blueprintStatesFor(), ['closed', 'open', 'locked']);
    assert.deepEqual(blueprintAllStates, ['closed', 'open', 'locked', 'off', 'on', 'empty', 'occupied']);
    assert.equal(defaultBlueprint().version, 2);
    assert.equal(validateBlueprint(lever), lever);
    const upgraded = upgradeBlueprint(lever);
    upgraded.states.on.appearance = 'hidden';
    assert.equal(lever.states.on.appearance, 'inherit');
    for (const event of blueprintEventsFor('lever')) for (const state of ['off', 'on']) {
        lever.graphs[event] = eventGraph(event);
        assert.deepEqual(simulateGraph(lever, event, state).trace, ['event']);
    }
    assert.equal(validateBlueprint(lever), lever);
    assert.throws(() => validateBlueprint({ ...lever, version: 1 }), /Unsupported/);
    assert.throws(() => validateBlueprint({ ...lever, states: { ...lever.states, open: { appearance: 'inherit' } } }), /state/);
    assert.equal(validateBlueprint({ ...lever, graphs: { 'presence:enter': eventGraph('presence:enter') } }).kind, 'lever');
    assert.throws(() => simulateGraph(lever, 'enter:open', 'off'), /event/);
    assert.throws(() => simulateGraph(lever, 'interact', 'open'), /state/);
    assert.throws(() => defaultBlueprint('unknown'), /Unsupported/);
    assert.throws(() => { blueprintStatesFor('lever')[0] = 'open'; }, TypeError);
});

test('lever instance reads the real decoration and inherited artwork stays visible in both states', () => {
    const lever = { id: 'lever_north', name: 'North lever', assetId: 'handle', lever: { state: 'off' }, blueprint: defaultBlueprint('lever') };
    const before = structuredClone(lever), instance = elementInstanceNode(lever);
    assert.deepEqual(instance, { id: 'object:lever_north', type: 'lever', sourceId: 'lever_north', name: 'North lever', state: 'off', outputs: [
        { id: 'interact', event: 'interact', label: 'On interaction', code: 'onInteract', color: 'green', kind: 'execution' },
        { id: 'presence:enter', event: 'presence:enter', label: 'On area enter', code: 'onAreaEnter', color: 'green', kind: 'execution' },
        { id: 'presence:exit', event: 'presence:exit', label: 'On area exit', code: 'onAreaExited', color: 'red', kind: 'execution' },
        { id: 'destroy', event: 'destroy', label: 'On destroy', code: 'onDestroy', color: 'red', kind: 'execution' },
    ] });
    instance.outputs[0].label = 'Edited';
    assert.deepEqual(lever, before);
    assert.equal(elementInstanceNode({ id: 'flat', state: 'on' }, 'lever').state, 'on');
    assert.equal(elementInstanceNode({ ...lever, name: '' }).name, 'Lever');
    for (const state of ['off', 'on']) {
        lever.lever.state = state;
        assert.equal(elementInstanceNode(lever).state, state);
        assert.deepEqual(blueprintAppearance(lever), { visible: true, assetId: 'handle' });
    }
    lever.blueprint.states.on = { appearance: 'hidden' };
    assert.deepEqual(blueprintAppearance(lever), { visible: false, assetId: null });
    lever.blueprint.states.on = { appearance: 'asset', assetId: 'raised' };
    assert.deepEqual(blueprintAppearance(lever), { visible: true, assetId: 'raised' });
    assert.throws(() => elementInstanceNode({ ...lever, lever: { state: 'locked' } }), /Invalid/);
    assert.throws(() => { blueprintContract.adapters.lever.outputs[0].color = 'red'; }, TypeError);
});

test('typed references connect doors and levers using the stable saved door output ID', () => {
    const target = 'b8f1c5e2-0c4d-4a52-9d0f-6f3a3c9b1e21';
    for (const [kind, event, current, state] of [['lever', 'signal:FixtureEnterOn', 'on', 'locked'], ['door', 'signal:FixtureEnterOpen', 'open', 'on']]) {
        const blueprint = upgradeBlueprint(defaultBlueprint(kind)), graph = eventGraph(event);
        blueprint.graphs[event] = graph;
        graph.nodes.push(
            { id: 'ref', type: 'reference', targetId: target, x: 300, y: 300 },
            { id: 'prop', type: 'property', property: 'state', x: 600, y: 300 },
            { id: 'cmp', type: 'compare', state, x: 900, y: 300 },
            { id: 'check', type: 'condition', state, x: 300, y: 0 },
            { id: 'act', type: 'state', targetState: state, x: 600, y: 0 },
        );
        connectNodes(graph, 'event', 'next', 'check', { version: 2 });
        connectNodes(graph, 'check', 'true', 'act', { version: 2 });
        for (const [from, output, to, input] of [['ref', 'door', 'prop', 'target'], ['prop', 'value', 'cmp', 'value'],
            ['cmp', 'result', 'check', 'test'], ['ref', 'door', 'act', 'target']]) connectNodes(graph, from, output, to, { version: 2, input });
        assert.equal(validateBlueprint(blueprint), blueprint);
        const before = structuredClone(blueprint), result = simulateGraph(blueprint, event, current, current, { [target]: state });
        assert.deepEqual(result.actions.map(action => [action.id, action.targetState, action.target]), [['act', state, target]]);
        assert.deepEqual(result.values, { ref: target, prop: state, cmp: true });
        assert.deepEqual(blueprint, before);
        assert.equal(simulateGraph(blueprint, event, current).actions.length, 0);
    }
    assert.deepEqual(blueprintContract.nodes.reference.outputs, [{ id: 'door', kind: 'value', type: 'element', label: 'Element' }]);
    assert.equal(blueprintContract.nodes.state.inputs.find(port => port.id === 'target').type, 'element');
});

const puzzleTorches = [
    '10000000-0000-4000-8000-000000000001',
    '10000000-0000-4000-8000-000000000002',
    '10000000-0000-4000-8000-000000000003',
    '10000000-0000-4000-8000-000000000004',
];
const puzzleDoor = '20000000-0000-4000-8000-000000000001';

function puzzleBlueprint(type = 'all', ports = ['a', 'b', 'c']) {
    const blueprint = defaultBlueprint('torch'), graph = eventGraph('signal:FixtureEnterOn');
    blueprint.graphs['signal:FixtureEnterOn'] = graph;
    graph.nodes.push(
        { id: 'gate', type, x: 900, y: 600 },
        { id: 'check', type: 'condition', state: 'off', x: 1200, y: 0 },
        { id: 'open', type: 'state', targetState: 'open', x: 1500, y: 0 },
        { id: 'close', type: 'state', targetState: 'closed', x: 1500, y: 250 },
        { id: 'door', type: 'reference', targetId: puzzleDoor, x: 1200, y: 600 },
    );
    connectNodes(graph, 'event', 'next', 'check', { version: 2 });
    connectNodes(graph, 'check', 'true', 'open', { version: 2 });
    connectNodes(graph, 'check', 'false', 'close', { version: 2 });
    connectNodes(graph, 'gate', 'result', 'check', { version: 2, input: 'test' });
    for (const id of ['open', 'close']) connectNodes(graph, 'door', 'door', id, { version: 2, input: 'target' });
    ports.forEach((port, index) => {
        graph.nodes.push(
            { id: `ref${index}`, type: 'reference', targetId: puzzleTorches[index], x: 0, y: 300 + 200 * index },
            { id: `prop${index}`, type: 'property', property: 'state', x: 300, y: 300 + 200 * index },
            { id: `cmp${index}`, type: 'compare', state: 'on', x: 600, y: 300 + 200 * index },
        );
        connectNodes(graph, `ref${index}`, 'door', `prop${index}`, { version: 2, input: 'target' });
        connectNodes(graph, `prop${index}`, 'value', `cmp${index}`, { version: 2, input: 'value' });
        connectNodes(graph, `cmp${index}`, 'result', 'gate', { version: 2, input: port });
    });
    return blueprint;
}

test('all and any recompute three distinct torch states for every truth combination', () => {
    for (const type of ['all', 'any']) {
        const blueprint = puzzleBlueprint(type), before = structuredClone(blueprint);
        validateBlueprint(blueprint);
        for (let mask = 0; mask < 8; mask += 1) {
            const states = Object.fromEntries(puzzleTorches.slice(0, 3).map((id, index) => [id, mask & (1 << index) ? 'on' : 'off']));
            const result = simulateGraph(blueprint, 'signal:FixtureEnterOn', 'on', 'off', states);
            const expected = type === 'all' ? mask === 7 : mask !== 0;
            assert.equal(result.values.gate, expected, `${type} / ${mask}`);
            assert.deepEqual(result.actions.map(action => [action.targetState, action.target]), [[expected ? 'open' : 'closed', puzzleDoor]]);
        }
        assert.deepEqual(blueprint, before, 'simulations never change the authored graph');
    }
});

test('logic evaluates every connected input in port order without short circuiting', () => {
    for (const type of ['all', 'any']) {
        const blueprint = puzzleBlueprint(type), graph = blueprint.graphs['signal:FixtureEnterOn'];
        graph.edges.reverse();
        const states = Object.fromEntries(puzzleTorches.map(id => [id, type === 'all' ? 'off' : 'on']));
        const result = simulateGraph(blueprint, 'signal:FixtureEnterOn', 'on', 'off', states);
        assert.deepEqual(result.trace.filter(id => /^(ref|prop|cmp)\d$/.test(id)),
            ['ref0', 'prop0', 'cmp0', 'ref1', 'prop1', 'cmp1', 'ref2', 'prop2', 'cmp2']);
        assert.equal(result.values.gate, type === 'any');
        for (const index of [0, 1, 2]) assert.equal(typeof result.values[`cmp${index}`], 'boolean');
    }
});

test('incomplete logic drafts remain false and preserve sparse connected ports on serialization', () => {
    for (const type of ['all', 'any']) {
        for (const ports of [[], ['d']]) {
            const blueprint = puzzleBlueprint(type, ports);
            assert.equal(validateBlueprint(blueprint), blueprint);
            const reopened = JSON.parse(JSON.stringify(blueprint));
            assert.deepEqual(reopened, blueprint);
            const result = simulateGraph(reopened, 'signal:FixtureEnterOn', 'on', 'off', { [puzzleTorches[0]]: 'on' });
            assert.equal(result.values.gate, false);
            assert.deepEqual(result.actions.map(action => action.id), ['close']);
        }
        const sparse = puzzleBlueprint(type, ['a', 'd']);
        assert.equal(simulateGraph(sparse, 'signal:FixtureEnterOn', 'on', 'off', {
            [puzzleTorches[0]]: 'on', [puzzleTorches[1]]: 'on',
        }).values.gate, true);
    }
});

test('nested logic gates accept boolean fanout without evaluating a shared source twice', () => {
    const blueprint = puzzleBlueprint('all', ['a', 'b', 'c', 'd']), graph = blueprint.graphs['signal:FixtureEnterOn'];
    graph.nodes.push({ id: 'either', type: 'any', x: 900, y: 1000 });
    graph.edges = graph.edges.filter(edge => !(edge.to === 'gate' && ['c', 'd'].includes(edge.input)));
    connectNodes(graph, 'cmp2', 'result', 'either', { version: 2, input: 'a' });
    connectNodes(graph, 'cmp3', 'result', 'either', { version: 2, input: 'b' });
    connectNodes(graph, 'either', 'result', 'gate', { version: 2, input: 'c' });
    connectNodes(graph, 'either', 'result', 'gate', { version: 2, input: 'd' });
    validateBlueprint(blueprint);
    const states = Object.fromEntries(puzzleTorches.map((id, index) => [id, index === 2 ? 'off' : 'on']));
    const result = simulateGraph(blueprint, 'signal:FixtureEnterOn', 'on', 'off', states);
    assert.equal(result.values.gate, true);
    assert.equal(result.values.either, true);
    assert.equal(result.trace.filter(id => id === 'either').length, 1);
    assert.equal(result.trace.filter(id => id === 'cmp3').length, 1);
    states[puzzleTorches[3]] = 'off';
    assert.equal(simulateGraph(blueprint, 'signal:FixtureEnterOn', 'on', 'off', states).values.gate, false);
});

test('logic handles missing element references as false comparisons', () => {
    for (const type of ['all', 'any']) {
        const blueprint = puzzleBlueprint(type, ['a', 'b']);
        const result = simulateGraph(blueprint, 'signal:FixtureEnterOn', 'on', 'off', { [puzzleTorches[0]]: 'on' });
        assert.equal(result.values.prop1, null);
        assert.equal(result.values.cmp1, false);
        assert.equal(result.values.gate, type === 'any');
        assert.equal(simulateGraph(blueprint, 'signal:FixtureEnterOn', 'on').values.gate, false);
    }
});

test('logic enforces boolean port types, exact fields, legacy vocabulary and cycle safety', () => {
    const blueprint = puzzleBlueprint('all', ['a', 'b']), graph = blueprint.graphs['signal:FixtureEnterOn'];
    graph.nodes.push({ id: 'other', type: 'any', x: 900, y: 1000 });
    const before = structuredClone(graph);
    for (const [from, output, to, options] of [
        ['prop0', 'value', 'gate', { version: 2, input: 'c' }],
        ['ref0', 'door', 'gate', { version: 2, input: 'c' }],
        ['event', 'next', 'gate', { version: 2 }],
        ['cmp0', 'result', 'gate', { version: 2, input: 'a' }],
    ]) assert.throws(() => connectNodes(graph, from, output, to, options), /connection/);
    assert.deepEqual(graph, before);
    connectNodes(graph, 'gate', 'result', 'other', { version: 2, input: 'a' });
    const connected = structuredClone(graph);
    assert.throws(() => connectNodes(graph, 'other', 'result', 'gate', { version: 2, input: 'c' }), /cycle/);
    assert.deepEqual(graph, connected);
    for (const type of ['all', 'any']) {
        const legacy = { ...defaultBlueprint(), version: 1 }, legacyGraph = eventGraph('signal:FixtureEnterOpen');
        legacy.graphs['signal:FixtureEnterOpen'] = legacyGraph;
        legacyGraph.nodes.push({ id: 'gate', type, x: 0, y: 0 });
        assert.throws(() => validateBlueprint(legacy), /Unsupported/);
        legacy.version = 2;
        validateBlueprint(legacy);
        legacyGraph.nodes[1].state = 'on';
        assert.throws(() => validateBlueprint(legacy), /node/);
    }
});

function variableBlueprint(valueType = 'boolean', expected = true, event = 'signal:FixtureInteractClosed') {
    const blueprint = upgradeBlueprint(defaultBlueprint()), graph = eventGraph(event);
    blueprint.graphs[event] = graph;
    graph.nodes.push(
        { id: 'remember', type: 'getVariable', scope: 'element', name: 'progress', valueType, default: typedDefault(valueType), x: 300, y: 400 },
        { id: 'compare', type: 'compareValue', valueType, operator: 'eq', expected, x: 600, y: 400 },
        { id: 'condition', type: 'condition', state: 'closed', x: 900, y: 100 },
        { id: 'open', type: 'state', targetState: 'open', x: 1200, y: 100 },
        { id: 'close', type: 'state', targetState: 'closed', x: 1200, y: 400 },
    );
    connectNodes(graph, 'event', 'next', 'condition', { version: 2 });
    connectNodes(graph, 'remember', 'value', 'compare', { version: 2, input: 'value' });
    connectNodes(graph, 'compare', 'result', 'condition', { version: 2, input: 'test' });
    connectNodes(graph, 'condition', 'true', 'open', { version: 2 });
    connectNodes(graph, 'condition', 'false', 'close', { version: 2 });
    return blueprint;
}

test('variables preserve false, zero and empty text in typed snapshot comparisons', () => {
    for (const [valueType, value, opposite] of [['boolean', false, true], ['number', 0, 12], ['text', '', 'ready']]) {
        const blueprint = variableBlueprint(valueType, value), getter = blueprint.graphs['signal:FixtureInteractClosed'].nodes[1];
        getter.default = opposite;
        const context = { variables: { element: { progress: { type: valueType, value } } } };
        const before = structuredClone({ blueprint, context });
        validateBlueprint(blueprint);
        const result = simulateGraph(blueprint, 'signal:FixtureInteractClosed', 'closed', 'closed', {}, context);
        assert.equal(result.values.remember, value);
        assert.equal(result.values.compare, true);
        assert.deepEqual(result.actions.map(action => action.id), ['open']);
        assert.deepEqual({ blueprint, context }, before);
        assert.deepEqual(simulateGraph(blueprint, 'signal:FixtureInteractClosed', 'closed').actions.map(action => action.id), ['close']);
    }
});

test('variables isolate element and scene scope and reject incompatible stored values', () => {
    const blueprint = variableBlueprint('number', 3), getter = blueprint.graphs['signal:FixtureInteractClosed'].nodes[1];
    const context = { variables: { element: { progress: { type: 'number', value: 3 } }, scene: { progress: { type: 'number', value: 8 } } } };
    assert.equal(simulateGraph(blueprint, 'signal:FixtureInteractClosed', 'closed', 'closed', {}, context).values.remember, 3);
    getter.scope = 'scene';
    assert.equal(simulateGraph(blueprint, 'signal:FixtureInteractClosed', 'closed', 'closed', {}, context).values.remember, 8);
    context.variables.scene.progress = { type: 'text', value: '8' };
    assert.throws(() => simulateGraph(blueprint, 'signal:FixtureInteractClosed', 'closed', 'closed', {}, context), /same type/);
    for (const row of [{ type: 'number', value: Infinity }, { type: 'number', value: true }, null]) {
        context.variables.scene.progress = row;
        assert.throws(() => simulateGraph(blueprint, 'signal:FixtureInteractClosed', 'closed', 'closed', {}, context), /snapshot/);
    }
});

test('queued variable assignments never change reads within the initial event snapshot', () => {
    const blueprint = variableBlueprint('number', 2), graph = blueprint.graphs['signal:FixtureInteractClosed'];
    graph.nodes.push({ id: 'assign', type: 'setVariable', scope: 'element', name: 'progress', valueType: 'number', value: 99, x: 300, y: 100 });
    graph.edges = graph.edges.filter(edge => edge.from !== 'event');
    connectNodes(graph, 'event', 'next', 'assign', { version: 2 });
    connectNodes(graph, 'assign', 'next', 'condition', { version: 2 });
    const context = { variables: { element: { progress: { type: 'number', value: 2 } } } };
    const before = structuredClone(context);
    const result = simulateGraph(blueprint, 'signal:FixtureInteractClosed', 'closed', 'closed', {}, context);
    assert.deepEqual(result.actions.map(action => [action.id, action.value]), [['assign', 99], ['open', undefined]]);
    assert.equal(result.values.remember, 2);
    assert.deepEqual(context, before);
    result.actions[0].value = -5;
    assert.equal(graph.nodes.find(node => node.id === 'assign').value, 99);
});

test('typed variable inputs use connected falsy values and reject incompatible connections atomically', () => {
    for (const valueType of ['boolean', 'number', 'text']) {
        const value = typedDefault(valueType), blueprint = variableBlueprint(valueType, value), graph = blueprint.graphs['signal:FixtureInteractClosed'];
        const literal = valueType === 'boolean' ? true : valueType === 'number' ? 1 : 'fallback';
        graph.nodes.push({ id: 'assign', type: 'setVariable', scope: 'scene', name: 'saved', valueType, value: literal, x: 200, y: 100 });
        connectNodes(graph, 'event', 'next', 'assign', { version: 2 });
        connectNodes(graph, 'remember', 'value', 'assign', { version: 2, input: 'value' });
        assert.equal(dataOutputs(graph.nodes[1])[0].type, valueType);
        assert.equal(dataInputs(graph.nodes.at(-1))[0].type, valueType);
        validateBlueprint(blueprint);
        assert.equal(simulateGraph(blueprint, 'signal:FixtureInteractClosed', 'closed').actions.find(action => action.id === 'assign').value, value);
        const before = structuredClone(graph);
        if (valueType !== 'boolean') {
            assert.throws(() => connectNodes(graph, 'compare', 'result', 'assign', { version: 2, input: 'value' }), /connection/);
            assert.deepEqual(graph, before);
        }
    }
});

test('numeric comparisons support all ordered operators and compare text without coercion', () => {
    const blueprint = variableBlueprint('number', 2), graph = blueprint.graphs['signal:FixtureInteractClosed'], comparison = graph.nodes[2];
    const context = { variables: { element: { progress: { type: 'number', value: 3 } } } };
    for (const [operator, expected] of [['eq', false], ['ne', true], ['lt', false], ['lte', false], ['gt', true], ['gte', true]]) {
        comparison.operator = operator;
        assert.equal(simulateGraph(blueprint, 'signal:FixtureInteractClosed', 'closed', 'closed', {}, context).values.compare, expected);
    }
    const text = variableBlueprint('text', '003');
    assert.equal(simulateGraph(text, 'signal:FixtureInteractClosed', 'closed', 'closed', {}, {
        variables: { element: { progress: { type: 'text', value: '3' } } },
    }).values.compare, false);
});

test('an unconnected typed comparison has a predictable empty draft value', () => {
    for (const valueType of ['boolean', 'number', 'text']) {
        const blueprint = variableBlueprint(valueType, typedDefault(valueType)), graph = blueprint.graphs['signal:FixtureInteractClosed'];
        graph.edges = graph.edges.filter(edge => !(edge.to === 'compare' && edge.input === 'value'));
        validateBlueprint(blueprint);
        assert.equal(simulateGraph(blueprint, 'signal:FixtureInteractClosed', 'closed').values.compare, true);
    }
});

test('variable and signal fields are bounded and reject ambiguous coercion or legacy use', () => {
    const blueprint = variableBlueprint('number', 3), graph = blueprint.graphs['signal:FixtureInteractClosed'], original = structuredClone(graph.nodes[1]);
    for (const patch of [{ name: '' }, { name: 'two words' }, { name: 'a'.repeat(65) }, { name: '9counter' },
        { scope: 'campaign' }, { valueType: 'state' }, { default: true }, { default: 1000001 }, { default: NaN },
        { default: Infinity }, { default: '3' }, { surprise: true }]) {
        graph.nodes[1] = { ...original, ...patch };
        assert.throws(() => validateBlueprint(blueprint), /variable|node/);
    }
    graph.nodes[1] = original;
    graph.nodes[2].operator = 'eval';
    assert.throws(() => validateBlueprint(blueprint), /comparison/);
    graph.nodes[2].operator = 'eq';
    blueprint.version = 1;
    assert.throws(() => validateBlueprint(blueprint), /Unsupported/);
    for (const valueType of ['boolean', 'text']) {
        const typed = variableBlueprint(valueType, typedDefault(valueType));
        typed.graphs['signal:FixtureInteractClosed'].nodes[2].operator = 'gt';
        assert.throws(() => validateBlueprint(typed), /comparison/);
    }
    const text = variableBlueprint('text', ''), getter = text.graphs['signal:FixtureInteractClosed'].nodes[1];
    getter.default = '🗝'.repeat(256);
    validateBlueprint(text);
    getter.default += '🗝';
    assert.throws(() => validateBlueprint(text), /variable/);
});

test('private simulation snapshots reject malformed memory and never read inherited variable names', () => {
    const blueprint = variableBlueprint('number', 3), getter = blueprint.graphs['signal:FixtureInteractClosed'].nodes[1];
    getter.name = 'constructor';
    const inherited = Object.create({ constructor: { type: 'number', value: 3 } });
    const context = { variables: { element: inherited } };
    assert.equal(simulateGraph(blueprint, 'signal:FixtureInteractClosed', 'closed', 'closed', {}, context).values.remember, 0);
    Object.defineProperty(inherited, 'constructor', { enumerable: true, value: { type: 'number', value: 3 } });
    assert.equal(simulateGraph(blueprint, 'signal:FixtureInteractClosed', 'closed', 'closed', {}, context).values.remember, 3);
    for (const snapshot of [null, [], { campaign: {} }, { element: [] }, { scene: null },
        { element: { 'bad name': { type: 'number', value: 3 } } },
        { scene: { score: { type: 'number', value: 3, extra: true } } },
        { scene: { score: { type: 'boolean', value: 0 } } },
        { scene: { score: { type: 'number', value: -1000001 } } },
        { scene: { score: { type: 'text', value: 'x'.repeat(257) } } }]) {
        assert.throws(() => validateVariableSnapshot(snapshot), /snapshot/);
    }
    const many = { element: Object.fromEntries(Array.from({ length: 64 }, (_, index) => [`v${index}`, { type: 'boolean', value: false }])) };
    validateVariableSnapshot(many);
    many.element.overflow = { type: 'boolean', value: false };
    assert.throws(() => validateVariableSnapshot(many), /snapshot/);
});

test('one variable keeps its type across authored events and stored assignments', () => {
    const blueprint = variableBlueprint('number', 0), other = eventGraph('signal:reset');
    blueprint.graphs['signal:reset'] = other;
    other.nodes.push({ id: 'assign', type: 'setVariable', scope: 'element', name: 'progress', valueType: 'text', value: '', x: 300, y: 100 });
    connectNodes(other, 'event', 'next', 'assign', { version: 2 });
    assert.throws(() => validateBlueprint(blueprint), /same type/);
    other.nodes[1].scope = 'scene';
    validateBlueprint(blueprint);
    assert.throws(() => simulateGraph(blueprint, 'signal:reset', 'closed', 'closed', {}, {
        variables: { scene: { progress: { type: 'number', value: 0 } } },
    }), /same type/);
});

test('named signal graphs are version two events and remain stable through serialization', () => {
    const blueprint = variableBlueprint('boolean', true, 'signal:puzzle.ready');
    validateBlueprint(blueprint);
    const reopened = JSON.parse(JSON.stringify(blueprint));
    assert.deepEqual(reopened, blueprint);
    assert.equal(isBlueprintSignalEvent('signal:puzzle.ready'), true);
    assert.equal(blueprintEventsFor('door').includes('signal:puzzle.ready'), false);
    assert.equal(blueprintEventsFor('door', reopened).includes('signal:puzzle.ready'), true);
    assert.deepEqual(simulateGraph(reopened, 'signal:puzzle.ready', 'closed').actions.map(action => action.id), ['close']);
    blueprint.version = 1;
    assert.throws(() => validateBlueprint(blueprint), /Unsupported/);
    for (const event of ['signal:', 'signal:bad name', 'signal:9bad', `signal:${'a'.repeat(65)}`, 'Signal:ready']) {
        assert.equal(isBlueprintSignalEvent(event), false);
        const invalid = upgradeBlueprint(defaultBlueprint());
        assert.throws(() => eventGraph(event), /event/);
        invalid.graphs[event] = { nodes: [{ id: 'event', type: 'event', event, x: 40, y: 60 }], edges: [] };
        assert.throws(() => validateBlueprint(invalid), /event/);
    }
    const many = upgradeBlueprint(defaultBlueprint());
    for (let index = 0; index < 16; index++) many.graphs[`signal:event${index}`] = eventGraph(`signal:event${index}`);
    validateBlueprint(many);
    many.graphs['signal:overflow'] = eventGraph('signal:overflow');
    assert.throws(() => validateBlueprint(many), /signals/);
});

test('signal simulation records scoped and targeted emissions without pretending to execute receivers', () => {
    const targetId = 'a2019d9e-c875-4f1f-a9ad-fb721c4addcd', blueprint = upgradeBlueprint(defaultBlueprint());
    const graph = eventGraph('signal:FixtureInteractClosed');
    blueprint.graphs['signal:FixtureInteractClosed'] = graph;
    graph.nodes.push(
        { id: 'send', type: 'emitEvent', scope: 'element', name: 'puzzle.ready', x: 300, y: 60 },
        { id: 'target', type: 'reference', targetId, x: 100, y: 400 },
        { id: 'broadcast', type: 'emitEvent', scope: 'scene', name: 'puzzle.ready', x: 600, y: 60 },
    );
    connectNodes(graph, 'event', 'next', 'send', { version: 2 });
    connectNodes(graph, 'target', 'door', 'send', { version: 2, input: 'target' });
    connectNodes(graph, 'send', 'next', 'broadcast', { version: 2 });
    const receiver = eventGraph('signal:puzzle.ready');
    receiver.nodes.push({ id: 'open_receiver', type: 'state', targetState: 'open', x: 300, y: 60 });
    connectNodes(receiver, 'event', 'next', 'open_receiver', { version: 2 });
    blueprint.graphs['signal:puzzle.ready'] = receiver;
    validateBlueprint(blueprint);
    const result = simulateGraph(blueprint, 'signal:FixtureInteractClosed', 'closed');
    assert.deepEqual(result.trace, ['event', 'send', 'target', 'broadcast']);
    assert.deepEqual(result.actions.map(action => [action.type, action.scope, action.name, action.target]), [
        ['emitEvent', 'element', 'puzzle.ready', targetId], ['emitEvent', 'scene', 'puzzle.ready', undefined],
    ]);
    assert.deepEqual(simulateGraph(blueprint, 'signal:puzzle.ready', 'closed').actions.map(action => action.id), ['open_receiver']);
});
