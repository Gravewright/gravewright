import test from 'node:test';
import assert from 'node:assert/strict';
import { sceneNetwork, networkPage } from './network-model.js';

const node = (id, type, fields = {}) => ({ id, type, x: 10, y: 20, ...fields });
const execution = (from, to, output = 'next') => ({ from, to, output, kind: 'execution' });
const data = (from, to, output = 'door', input = 'target') => ({ from, to, output, input, kind: 'data' });
const owner = (id, graphs = {}, extra = {}) => ({ id, kind: 'door', name: `Owner ${id}`, blueprint: { graphs }, ...extra });
const graph = (nodes, edges = []) => ({ nodes: [node('event', 'event'), ...nodes], edges });
const relationship = (network, from, to, kind) => {
    const target = network.nodes.find(row => row.id === to || row.resourceId === to)?.id || to;
    return network.edges.find(edge => edge.from === from && edge.to === target && edge.kind === kind);
};

test('overview derives only existing owners and references used by executable paths', () => {
    const blueprintGraph = graph([node('ref', 'reference', { targetId: 'target' }), node('action', 'state'),
        node('unused', 'reference', { targetId: 'unreachable' }), node('never', 'light', { targetId: 'unreached-light' })],
    [execution('event', 'action'), data('ref', 'action')]);
    const catalog = { elements: [owner('owner', { 'signal:FixtureInteractClosed': blueprintGraph }), owner('target'), { id: 'ordinary', kind: 'image' }],
        lights: [{ id: 'unreached-light' }], sounds: [{ id: 'unused-sound' }] }, original = structuredClone(catalog);
    const result = sceneNetwork(catalog);
    assert.deepEqual(result.nodes.map(row => row.id), ['owner', 'target']);
    assert.ok(relationship(result, 'owner', 'target', 'reference'));
    assert.equal(result.nodes.some(row => row.id === 'unreachable'), false);
    assert.deepEqual(catalog, original);
});

test('typed connected targets hide inactive light and sound fallbacks and retain ordered groups', () => {
    const result = sceneNetwork({ elements: [owner('owner', { active: graph([
        node('lights', 'elementGroup', { memberType: 'light', targetIds: ['light-two', 'light-one'] }),
        node('sounds', 'soundReference', { trackId: 'sound-two' }), node('on', 'light', { targetId: 'inactive-light' }),
        node('play', 'sound', { trackId: 'inactive-sound' })], [execution('event', 'on'), execution('on', 'play'),
        data('lights', 'on', 'targets'), data('sounds', 'play', 'sound')]) })],
        lights: [{ id: 'light-one' }, { id: 'light-two' }, { id: 'inactive-light' }], sounds: [{ id: 'sound-two' }, { id: 'inactive-sound' }] });
    assert.deepEqual(result.edges.filter(row => row.kind === 'group').map(row => row.to), ['light:light-two', 'light:light-one']);
    assert.ok(relationship(result, 'owner', 'sound-two', 'sound'));
    assert.equal(result.nodes.some(row => ['inactive-light', 'inactive-sound'].includes(row.id)), false);
});

test('missing bindings remain visible inert targets with their owning behavior highlighted', () => {
    const result = sceneNetwork({ elements: [owner('owner', { active: graph([node('ref', 'reference', { targetId: 'deleted' }), node('act', 'state')],
        [execution('event', 'act'), data('ref', 'act')]) }), owner('unrelated')] });
    const missing = result.nodes.find(row => row.id === 'deleted');
    assert.equal(missing.missing, true); assert.equal(missing.editable, false);
    const page = networkPage(result, { problems: true });
    assert.deepEqual(page.nodes.map(row => row.id), ['owner', 'deleted']);
    assert.equal(page.edges.length, 1);
});

test('named scene signals only connect reachable senders to existing matching receivers', () => {
    const sender = owner('sender', { active: graph([node('emit', 'emitEvent', { scope: 'scene', name: 'Open' }),
        node('unused', 'emitEvent', { scope: 'scene', name: 'Unused' })], [execution('event', 'emit')]) });
    const result = sceneNetwork({ elements: [sender, owner('receiver', { 'signal:Open': graph([]) }), owner('other', { 'signal:Unused': graph([]) })] });
    assert.ok(relationship(result, 'sender', 'receiver', 'signal'));
    assert.equal(result.edges.some(row => row.kind === 'signal' && row.to === 'other'), false);
});

test('targeted signals preserve Self and explicit groups without creating unmatched receivers', () => {
    const result = sceneNetwork({ elements: [owner('self', {
        active: graph([node('selfEmit', 'emitEvent', { scope: 'element', name: 'Self' }),
            node('group', 'elementGroup', { memberType: 'element', targetIds: ['match', 'no-match'] }),
            node('others', 'emitEvent', { scope: 'element', name: 'Open' })],
        [execution('event', 'selfEmit'), execution('selfEmit', 'others'), data('group', 'others', 'targets')]),
        'signal:Self': graph([]),
    }), owner('match', { 'signal:Open': graph([]) }), owner('no-match')] });
    assert.ok(relationship(result, 'self', 'self', 'signal'));
    assert.ok(relationship(result, 'self', 'match', 'signal'));
    assert.equal(relationship(result, 'self', 'no-match', 'signal'), undefined);
    assert.ok(relationship(result, 'self', 'no-match', 'group'));
});

test('events merge on one relationship and data fanout does not duplicate the graph store', () => {
    const active = graph([node('ref', 'reference', { targetId: 'target' }), node('first', 'state'), node('second', 'reveal')],
        [execution('event', 'first'), execution('first', 'second'), data('ref', 'first'), data('ref', 'second')]);
    const catalog = { elements: [owner('source', { one: active, two: structuredClone(active) }), owner('target')] };
    const result = sceneNetwork(catalog), edge = relationship(result, 'source', 'target', 'reference');
    assert.deepEqual(edge.events, ['one', 'two']); assert.equal(result.edges.length, 1);
    assert.equal(catalog.elements[0].blueprint.graphs.one.nodes.length, 4);
});

test('presentation and appearance resources remain typed relationships', () => {
    const result = sceneNetwork({ elements: [owner('owner', { active: graph([
        node('teleport', 'teleport', { destinationId: 'region' }), node('handout', 'showHandout', { journalId: 'journal', audience: { scope: 'users', userIds: ['user'] } }),
        node('art', 'setAppearance', { assetId: 'asset' })], [execution('event', 'teleport'), execution('teleport', 'handout'), execution('handout', 'art')]) }),
        owner('region', {}, { kind: 'region' })], assets: [{ id: 'asset' }], handouts: [{ id: 'journal' }], users: [{ id: 'user' }] });
    for (const [target, kind] of [['region', 'teleport'], ['journal', 'handout'], ['asset', 'appearance'], ['user', 'audience']]) {
        assert.ok(relationship(result, 'owner', target, kind)); assert.equal(result.nodes.find(row => row.id === target || row.resourceId === target).missing, false);
    }
});

test('pagination bounds cards while preserving searchable off-page relationships', () => {
    const network = sceneNetwork({ elements: Array.from({ length: 95 }, (_, index) => owner(`owner-${index}`, index === 0 ? {
        'signal:AuthoredSecret': graph([node('ref', 'reference', { targetId: 'owner-94' }), node('act', 'state')], [execution('event', 'act'), data('ref', 'act')]),
    } : {})) });
    const first = networkPage(network), last = networkPage(network, { page: 999 });
    assert.equal(first.nodes.length, 40); assert.equal(first.pages, 3); assert.equal(first.page, 0);
    assert.equal(first.edges.length, 0); assert.equal(first.outgoing.length, 1);
    assert.equal(last.nodes.length, 15); assert.equal(last.page, 2);
    assert.equal(networkPage(network, { page: -2 }).page, 0);
    assert.equal(networkPage(network, { query: '  authoredsecret  ' }).nodes[0].id, 'owner-0');
    const empty = networkPage(network, { query: 'absent' }); assert.equal(empty.total, 0); assert.equal(empty.pages, 1);
});

test('resource namespaces cannot overwrite an editable owner with the same UUID', () => {
    const result = sceneNetwork({ elements: [owner('same', { active: graph([node('play', 'sound', { trackId: 'same' })],
        [execution('event', 'play')]) })], sounds: [{ id: 'same', name: 'Sound sharing a UUID with the owner' }] });
    assert.deepEqual(result.nodes.map(row => row.id), ['same', 'sound:same']);
    assert.equal(result.nodes[0].editable, true); assert.equal(result.nodes[0].resource, 'element');
    assert.equal(result.nodes[1].editable, false); assert.equal(result.nodes[1].resourceId, 'same');
    assert.ok(result.edges.some(edge => edge.from === 'same' && edge.to === 'sound:same' && edge.kind === 'sound'));
});

test('authored state images are visible relationships even without an action graph', () => {
    const element = owner('owner');
    element.blueprint.states = { closed: { appearance: 'asset', assetId: 'closed-image' }, open: { appearance: 'asset', assetId: 'missing-image' }, locked: { appearance: 'inherit' } };
    const result = sceneNetwork({ elements: [element], assets: [{ id: 'closed-image', name: 'Closed state artwork' }] });
    assert.ok(relationship(result, 'owner', 'asset:closed-image', 'appearance'));
    const missing = result.nodes.find(row => row.id === 'asset:missing-image');
    assert.equal(missing.missing, true); assert.equal(missing.resource, 'asset');
    assert.deepEqual(networkPage(result, { problems: true }).nodes.map(row => row.id), ['owner', 'asset:missing-image']);
});

test('clock actions expose typed live and missing relationships without colliding with owners', () => {
    const source = owner('same', { interact: graph([
        node('advance', 'clockControl', { clockId: 'same', action: 'advance', amount: 1 }),
        node('reset', 'clockControl', { clockId: 'removed', action: 'reset', amount: 1 }),
        node('unused', 'clockControl', { clockId: 'unused', action: 'set', amount: 2 }),
    ], [execution('event', 'advance'), execution('advance', 'reset')]) });
    const result = sceneNetwork({ elements: [source], clocks: [{ id: 'same', name: 'Authored clock' }] });
    assert.ok(result.nodes.find(row => row.id === 'same').editable);
    assert.equal(result.nodes.find(row => row.id === 'clock:same').name, 'Authored clock');
    assert.ok(relationship(result, 'same', 'clock:same', 'clock'));
    assert.equal(result.nodes.find(row => row.id === 'clock:removed').missing, true);
    assert.equal(result.nodes.some(row => row.id === 'clock:unused'), false);
    assert.deepEqual(networkPage(result, { problems: true }).nodes.map(row => row.id), ['same', 'clock:removed']);
});
