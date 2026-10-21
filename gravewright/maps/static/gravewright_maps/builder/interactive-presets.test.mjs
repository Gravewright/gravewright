import test from 'node:test';
import assert from 'node:assert/strict';
import { validateBlueprint, simulateGraph, blueprintAppearance } from './blueprint-model.js';
import { interactiveObjectPresets, interactiveObjectBehaviorOptions, createInteractiveObjectPreset } from './interactive-presets.js';

const doorId = '00000000-0000-4000-8000-000000000001';
const journalId = '00000000-0000-4000-8000-000000000002';
const userId = '00000000-0000-4000-8000-000000000003';
const trackId = '00000000-0000-4000-8000-000000000004';
const assetId = '00000000-0000-4000-8000-000000000005';
const run = (blueprint, state = 'off', context = {}, event = 'interact') => simulateGraph(blueprint, event, state, state, {}, context);

test('every catalog object produces a valid, independent generic mechanism with an executable interaction', () => {
    assert.equal(interactiveObjectPresets.length, 14);
    assert.equal(new Set(interactiveObjectPresets.map(row => row.id)).size, 14);
    assert.deepEqual(interactiveObjectBehaviorOptions.map(row => row.value), interactiveObjectPresets.map(row => `preset:${row.id}`));
    for (const preset of interactiveObjectPresets) {
        const first = createInteractiveObjectPreset(preset.id, { doorId: preset.door ? doorId : '', journalId });
        const second = createInteractiveObjectPreset(preset.id, { doorId: preset.door ? doorId : '', journalId });
        assert.equal(first.blueprint.version, 2); assert.equal(first.blueprint.kind, 'lever');
        assert.equal(validateBlueprint(first.blueprint), first.blueprint);
        assert.ok(run(first.blueprint, first.initialState).actions.length, preset.id);
        assert.equal(first.name, preset.name);
        first.blueprint.graphs.interact.nodes[0].x = 900;
        assert.equal(second.blueprint.graphs.interact.nodes[0].x, 40);
    }
});

test('optional sounds execute on the successful effect branch while active images follow object state', () => {
    for (const preset of interactiveObjectPresets) {
        const options = { doorId: preset.door ? doorId : '', journalId, includeSound: true, trackId, volume: .35, includeImage: true, assetId };
        const { blueprint, initialState } = createInteractiveObjectPreset(preset.id, options);
        assert.equal(validateBlueprint(blueprint, { assets: [{ id: assetId }], sounds: [{ id: trackId }] }), blueprint);
        const event = preset.id === 'trap' ? 'presence:enter' : 'interact';
        const actions = run(blueprint, initialState, {}, event).actions;
        const played = actions.filter(action => action.type === 'sound');
        assert.equal(played.length, 1, preset.id); assert.equal(played[0].trackId, trackId); assert.equal(played[0].volume, .35);
        assert.deepEqual(blueprint.states.off, { appearance: 'inherit' });
        assert.deepEqual(blueprint.states.on, { appearance: 'asset', assetId });
        assert.deepEqual(blueprintAppearance({ blueprint, lever: { state: 'off' } }), { visible: true, assetId: undefined });
        assert.deepEqual(blueprintAppearance({ blueprint, lever: { state: 'on' } }), { visible: true, assetId });
        const omitted = createInteractiveObjectPreset(preset.id, { ...options, includeSound: false, includeImage: false }).blueprint;
        assert.ok(Object.values(omitted.graphs).every(graph => graph.nodes.every(node => node.type !== 'sound')), preset.id);
        assert.deepEqual(omitted.states.on, { appearance: 'inherit' });
    }
    assert.throws(() => createInteractiveObjectPreset('chest', { includeSound: true }), /Choose a sound/);
    assert.throws(() => createInteractiveObjectPreset('chest', { includeSound: true, trackId, volume: 1.01 }), /Choose a sound/);
    assert.throws(() => createInteractiveObjectPreset('chest', { includeImage: true }), /Choose an image/);
    const { blueprint } = createInteractiveObjectPreset('chest', { includeSound: true, trackId });
    const first = run(blueprint), closed = run(blueprint, 'on', { memory: first.memory });
    assert.equal(run(blueprint, 'off', { memory: closed.memory }).actions.some(action => action.type === 'sound'), false);
    const trap = createInteractiveObjectPreset('trap', { includeSound: true, trackId }).blueprint;
    assert.equal(run(trap, 'off', {}, 'presence:enter').actions.length, 0);
});

test('a dice challenge asks a selected player for the authored roll and respects its cooldown', () => {
    const audience = { scope: 'users', userIds: [userId] };
    const { blueprint } = createInteractiveObjectPreset('dice-request', { expression: '2d6+1', label: 'Synthetic challenge', visibility: 'gm', audience });
    const first = run(blueprint, 'off', { now: 1000 });
    const roll = first.actions.find(action => action.type === 'requestRoll');
    assert.equal(roll.expression, '2d6+1'); assert.equal(roll.label, 'Synthetic challenge'); assert.equal(roll.visibility, 'gm');
    assert.deepEqual(roll.audience, audience);
    assert.deepEqual(run(blueprint, 'on', { now: 1100, memory: first.memory }).actions, []);
    assert.throws(() => createInteractiveObjectPreset('dice-request', { expression: '' }), /dice request/);
    assert.throws(() => createInteractiveObjectPreset('dice-request', { visibility: 'secret' }), /dice request/);
});

test('quest templates change the chosen quest and present its entry without changing the audience', () => {
    for (const [id, status] of [['quest-start', 'active'], ['quest-complete', 'completed']]) {
        const { blueprint } = createInteractiveObjectPreset(id, { journalId, audience: { scope: 'players' } });
        const actions = run(blueprint).actions;
        assert.deepEqual(actions.map(action => action.type), ['setQuestStatus', 'showHandout', 'state']);
        assert.equal(actions[0].status, status); assert.equal(actions[0].journalId, journalId);
        assert.equal(actions[1].journalId, journalId); assert.deepEqual(actions[1].audience, { scope: 'players' });
        assert.throws(() => createInteractiveObjectPreset(id), /quest first/);
    }
});

test('a pressure plate opens a linked door on entry and closes it on exit', () => {
    const { blueprint } = createInteractiveObjectPreset('pressure-plate', { doorId });
    for (const event of ['interact', 'presence:enter'])
        assert.deepEqual(run(blueprint, 'off', {}, event).actions.map(action => [action.targetState, action.target]), [['on', undefined], ['open', doorId]]);
    assert.deepEqual(run(blueprint, 'on', {}, 'presence:exit').actions.map(action => [action.targetState, action.target]), [['off', undefined], ['closed', doorId]]);
    assert.deepEqual(run(blueprint, 'on', { eventContext: { count: 1 } }, 'presence:exit').actions, []);
    const button = createInteractiveObjectPreset('door-button', { doorId }).blueprint;
    assert.deepEqual(run(button, 'on').actions.map(action => action.targetState), ['on', 'open']);
});

test('entrance signs announce once on entry but can always be read by interaction', () => {
    const { blueprint } = createInteractiveObjectPreset('entrance-sign', { text: 'Synthetic welcome.' });
    const first = run(blueprint, 'off', {}, 'presence:enter');
    assert.equal(first.actions.find(action => action.type === 'showMessage').text, 'Synthetic welcome.');
    assert.deepEqual(run(blueprint, 'on', { memory: first.memory }, 'presence:enter').actions, []);
    assert.equal(run(blueprint, 'on', { memory: first.memory }).actions.find(action => action.type === 'showMessage').text, 'Synthetic welcome.');
});

test('timed switches do not restart while active and retain a connected reset after the requested delay', () => {
    const { blueprint } = createInteractiveObjectPreset('timed-switch', { doorId, seconds: 12 });
    const first = run(blueprint);
    assert.deepEqual(first.actions.map(action => action.targetState), ['on', 'open']);
    assert.deepEqual(first.delay, { nodeId: 'resetDelay', seconds: 12 });
    assert.deepEqual(run(blueprint, 'on').actions, []);
    assert.ok(blueprint.graphs.interact.edges.some(edge => edge.from === 'resetDelay' && edge.to === 'deactivate'));
    assert.ok(blueprint.graphs.interact.edges.some(edge => edge.from === 'deactivate' && edge.to === 'close'));
    assert.throws(() => createInteractiveObjectPreset('timed-switch', { seconds: 0 }), /control/);
});

test('switch and passage toggle themselves and their linked door in both directions', () => {
    for (const preset of ['switch', 'secret-passage']) {
        const { blueprint } = createInteractiveObjectPreset(preset, { doorId });
        assert.deepEqual(run(blueprint).actions.map(row => [row.targetState, row.target]), [['on', undefined], ['open', doorId]]);
        assert.deepEqual(run(blueprint, 'on').actions.map(row => [row.targetState, row.target]), [['off', undefined], ['closed', doorId]]);
        assert.ok(run(blueprint).actions.every(row => !Object.hasOwn(row, 'players')), 'the preset does not grant lock permissions');
    }
    const standalone = createInteractiveObjectPreset('switch').blueprint;
    assert.deepEqual(run(standalone).actions.map(row => row.targetState), ['on']);
    assert.throws(() => createInteractiveObjectPreset('secret-passage'), /controlled door/);
    assert.throws(() => createInteractiveObjectPreset('switch', { doorId: 'missing' }), /controlled door/);
});

test('a chest opens and closes repeatedly while its contents message is shown once', () => {
    const { blueprint } = createInteractiveObjectPreset('chest', { text: 'A synthetic key.', audience: { scope: 'players' } });
    const first = run(blueprint);
    assert.deepEqual(first.actions.map(row => row.type), ['state', 'showMessage']);
    assert.equal(first.actions[1].text, 'A synthetic key.'); assert.deepEqual(first.actions[1].audience, { scope: 'players' });
    const closed = run(blueprint, 'on', { memory: first.memory });
    assert.deepEqual(closed.actions.map(row => row.targetState), ['off']);
    const reopened = run(blueprint, 'off', { memory: closed.memory });
    assert.deepEqual(reopened.actions.map(row => row.type), ['state']); assert.equal(reopened.actions[0].targetState, 'on');
});

test('a readable book delivers the chosen journal to one player and can be read again', () => {
    const audience = { scope: 'users', userIds: [userId] };
    const { blueprint } = createInteractiveObjectPreset('book', { journalId, audience });
    audience.userIds.length = 0;
    for (const state of ['off', 'on']) {
        const actions = run(blueprint, state).actions;
        assert.equal(actions[0].type, 'showHandout'); assert.equal(actions[0].journalId, journalId);
        assert.deepEqual(actions[0].audience, { scope: 'users', userIds: [userId] });
        assert.equal(actions[1].targetState, 'on');
    }
    assert.throws(() => createInteractiveObjectPreset('book'), /journal handout/);
});

test('an altar throttles interaction messages without extending the cooldown', () => {
    const { blueprint } = createInteractiveObjectPreset('altar');
    const first = run(blueprint, 'off', { now: 1000 });
    assert.deepEqual(first.actions.map(row => row.type), ['state', 'showMessage']);
    const blocked = run(blueprint, 'on', { now: 5999, memory: first.memory });
    assert.deepEqual(blocked.actions, []);
    assert.equal(blocked.memory.interact.cooldown.value, 6000);
    const ready = run(blueprint, 'on', { now: 6000, memory: blocked.memory });
    assert.deepEqual(ready.actions.map(row => row.type), ['state', 'showMessage']);
});

test('a trap warns on area entry only while armed, with bounded repeated warnings', () => {
    const { blueprint, initialState } = createInteractiveObjectPreset('trap', { audience: { scope: 'players' } });
    assert.equal(initialState, 'on');
    const first = run(blueprint, 'on', { now: 1000 }, 'presence:enter');
    assert.deepEqual(first.actions.map(row => row.type), ['showMessage']);
    assert.deepEqual(first.actions[0].audience, { scope: 'players' });
    assert.deepEqual(run(blueprint, 'on', { now: 1001, memory: first.memory }, 'presence:enter').actions, []);
    assert.deepEqual(run(blueprint, 'off', {}, 'presence:enter').actions, []);
    assert.equal(run(blueprint, 'on').actions[0].targetState, 'off');
    assert.equal(run(blueprint, 'off').actions[0].targetState, 'on');
});

test('presets validate messages and audiences and localize only their authored starter text', () => {
    for (const options of [{ text: '' }, { text: 'x'.repeat(2001) }, { audience: { scope: 'users', userIds: [] } }, { audience: { scope: 'everyone' } }])
        assert.throws(() => createInteractiveObjectPreset('chest', options), /presentation|audience/);
    assert.throws(() => createInteractiveObjectPreset('unknown'), /interactive object/);
    const translated = createInteractiveObjectPreset('chest', { t: text => `translated:${text}` });
    assert.equal(translated.name, 'translated:Chest');
    assert.equal(run(translated.blueprint).actions[1].text, 'translated:The chest is open.');
    const authored = createInteractiveObjectPreset('chest', { text: 'Keep my text.', t: text => `translated:${text}` });
    assert.equal(run(authored.blueprint).actions[1].text, 'Keep my text.');
});
