import test from 'node:test';
import assert from 'node:assert/strict';
import { defaultBlueprint, upgradeBlueprint, eventGraph, connectNodes, validateBlueprint, simulateGraph, dataInputs,
    acceptsDataType, validateAudience, nodeOutputs } from './blueprint-model.js';

const id = number => `00000000-0000-4000-8000-${String(number).padStart(12, '0')}`;
const event = 'signal:FixtureInteractClosed', audience = { scope: 'users', userIds: [id(1), id(2)] };
const actions = [
    { id: 'message', type: 'showMessage', text: '  Authored text <b>plain</b>  ', audience },
    { id: 'handout', type: 'showHandout', journalId: id(3), audience: { scope: 'trigger' } },
    { id: 'camera', type: 'cameraFocus', focusX: 1.25, focusY: 9, audience: { scope: 'players' } },
    { id: 'teleport', type: 'teleport', destinationId: id(4) },
    { id: 'visibility', type: 'setVisibility', visible: false },
    { id: 'appearance', type: 'setAppearance', assetId: id(5) },
    { id: 'roll', type: 'requestRoll', expression: '2d6 + 3', label: 'Search the chest', visibility: 'gm', audience: { scope: 'players' } },
    { id: 'quest', type: 'setQuestStatus', journalId: id(6), status: 'completed' },
];
const resources = { assets: [{ id: id(5) }] };
function fixture(nodes = actions) {
    const blueprint = upgradeBlueprint(defaultBlueprint()), graph = eventGraph(event);
    blueprint.graphs[event] = graph;
    graph.nodes.push(...structuredClone(nodes).map((node, index) => ({ x: 300 + index * 300, y: 400, ...node })));
    for (let index = 1; index < graph.nodes.length; index++) connectNodes(graph, graph.nodes[index - 1].id, 'next', graph.nodes[index].id, { version: 2 });
    return { blueprint, graph };
}

test('presentation actions continue in order and preview produces independent queued data only', () => {
    const { blueprint } = fixture(), before = structuredClone(blueprint);
    validateBlueprint(blueprint, resources);
    const first = simulateGraph(blueprint, event, 'closed'), second = simulateGraph(blueprint, event, 'closed');
    assert.deepEqual(first.actions.map(row => row.type), actions.map(row => row.type));
    assert.equal(first.actions[0].text, actions[0].text);
    assert.equal(first.actions[2].x, 900); assert.equal(first.actions[2].focusX, 1.25);
    first.actions[0].audience.userIds.reverse(); first.actions[0].text = 'changed';
    assert.deepEqual(second.actions[0].audience, audience);
    assert.deepEqual(blueprint, before);
    assert.equal(Object.hasOwn(first, 'effects'), false);
});

test('audiences use exact discriminated fields and bounded distinct UUIDs', () => {
    for (const value of [{ scope: 'trigger' }, { scope: 'players' }, audience,
        { scope: 'users', userIds: Array.from({ length: 64 }, (_, index) => id(index + 1)) }]) assert.equal(validateAudience(value), value);
    for (const value of [null, {}, [], { scope: 'all' }, { scope: 'trigger', userIds: [] }, { scope: 'players', role: 'gm' },
        { scope: 'users' }, { scope: 'users', userIds: [] }, { scope: 'users', userIds: ['bad'] },
        { scope: 'users', userIds: [id(1), id(1).toUpperCase()] }, { scope: 'users', userIds: [id(1) + '\n'] },
        { scope: 'users', userIds: Array.from({ length: 65 }, (_, index) => id(index + 1)) }]) assert.throws(() => validateAudience(value), /audience/);
});

test('message, camera, handout and teleport schemas reject coercion and invalid ranges', () => {
    const invalid = [
        { ...actions[0], text: '' }, { ...actions[0], text: '   ' }, { ...actions[0], text: 'bad\0text' }, { ...actions[0], text: 'a'.repeat(2001) },
        { ...actions[0], text: false }, { ...actions[1], journalId: 'bad' }, { ...actions[1], journalId: id(1) + '\n' },
        { ...actions[2], focusX: -1 }, { ...actions[2], focusY: 1001 }, { ...actions[2], focusX: '1' }, { ...actions[2], focusY: true },
        { ...actions[3], destinationId: 'bad' }, { ...actions[3], tokenId: id(9) }, { ...actions[4], visible: 1 }, { ...actions[5], assetId: 'bad' },
    ];
    for (const node of invalid) assert.throws(() => validateBlueprint(fixture([node]).blueprint, resources), /blueprint|image/);
    validateBlueprint(fixture([{ ...actions[0], text: '🔥'.repeat(2000) }, { ...actions[2], focusX: 0, focusY: 1000 }]).blueprint);
});

test('appearance checks campaign assets and visual targets accept element groups only', () => {
    for (const type of ['setAppearance', 'setVisibility']) {
        const target = dataInputs({ type }).find(port => port.id === 'target');
        assert.equal(acceptsDataType(target, 'element'), true); assert.equal(acceptsDataType(target, 'elementset'), true);
        assert.equal(acceptsDataType(target, 'light'), false);
    }
    for (const action of actions) assert.deepEqual(nodeOutputs(action), ['next']);
    for (const action of actions.slice(0, 4)) assert.deepEqual(dataInputs(action), []);
    assert.throws(() => validateBlueprint(fixture([actions[5]]).blueprint), /image/);
    validateBlueprint(fixture([actions[5]]).blueprint, { assets: [], materials: resources.assets });
    const stateImage = fixture([actions[5]]).blueprint;
    stateImage.states.open = { appearance: 'asset', assetId: id(5) };
    assert.throws(() => validateBlueprint(stateImage, { assets: [], materials: resources.assets }), /image/);
});

test('Delay suspends later presentation actions and version one cannot silently acquire them', () => {
    const { blueprint } = fixture([actions[0], { id: 'wait', type: 'delay', seconds: .1 }, actions[1]]);
    const result = simulateGraph(blueprint, event, 'closed');
    assert.deepEqual(result.actions.map(row => row.type), ['showMessage']); assert.equal(result.delay.nodeId, 'wait');
    for (const action of actions) {
        const old = fixture([action]).blueprint; old.version = 1;
        old.graphs[event].edges = old.graphs[event].edges.map(({ kind, ...edge }) => edge);
        assert.throws(() => validateBlueprint(old, resources), /blueprint/);
    }
});

test('roll requests preserve selected recipients and authored expressions without rolling during preview', () => {
    const roll = { ...actions[6], audience: { scope: 'users', userIds: [id(1)] } };
    const { blueprint } = fixture([roll, actions[7]]);
    validateBlueprint(blueprint);
    const before = structuredClone(blueprint), result = simulateGraph(blueprint, event, 'closed');
    assert.equal(result.actions[0].expression, '2d6 + 3');
    assert.deepEqual(result.actions[0].audience.userIds, [id(1)]);
    assert.equal(result.actions[1].status, 'completed');
    assert.equal(Object.hasOwn(result.actions[0], 'total'), false);
    result.actions[0].audience.userIds.push(id(2));
    assert.deepEqual(blueprint, before);
    for (const node of [
        { ...roll, expression: '' }, { ...roll, expression: 'x'.repeat(513) }, { ...roll, expression: '1d20\0' },
        { ...roll, expression: 20 }, { ...roll, label: 'x'.repeat(49) }, { ...roll, visibility: 'secret' },
        { ...roll, audience: { scope: 'users', userIds: [] } },
        { ...actions[7], journalId: 'other' }, { ...actions[7], status: 'unknown' },
    ]) assert.throws(() => validateBlueprint(fixture([node]).blueprint), /blueprint/);
});
