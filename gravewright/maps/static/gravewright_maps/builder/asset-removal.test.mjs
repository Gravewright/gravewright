import test from 'node:test';
import assert from 'node:assert/strict';
import { detachDocumentAsset, sameDocument } from './asset-removal.js';
import { newDocument, clone } from './model.js';
import { defaultBlueprint } from './blueprint-model.js';

function lever(base = 'removed') {
    const blueprint = defaultBlueprint('lever');
    blueprint.states.on = { appearance: 'asset', assetId: 'alternate' };
    return { id: 'handle', layerId: 'base', assetId: base, x: 3, y: 4, width: 2, height: 1,
        rotation: 45, lever: { state: 'off' }, blueprint };
}

test('deleting an image preserves geometry, authored text and unrelated library metadata', () => {
    const source = newDocument('removed');
    source.assets = [{ assetId: 'removed', role: 'wall', collection: 'Workshop', family: 'Stone' },
        { assetId: 'keep', role: 'floor', name: 'removed', collection: 'Workshop' }];
    for (const kind of ['floors', 'walls', 'doors', 'decorations'])
        source[kind].push({ id: kind, assetId: 'removed', x: 2, y: 3, width: 4, height: 5 });
    source.lights.push({ id: 'light', x: 1, y: 2, enabled: true });
    const before = clone(source), result = detachDocumentAsset(source, 'removed', ['keep']);
    assert.deepEqual(source, before);
    assert.equal(result.name, 'removed');
    assert.deepEqual(result.assets, [source.assets[1]]);
    for (const kind of ['floors', 'walls', 'doors', 'decorations'])
        assert.deepEqual(result[kind][0], { ...source[kind][0], assetId: null });
    assert.deepEqual(result.lights, source.lights);
    result.lights[0].enabled = false;
    assert.equal(source.lights[0].enabled, true);
});

test('deleting a ready-map image detaches only the background and preserves Empty behavior', () => {
    const source = newDocument(), blueprint = defaultBlueprint('lever');
    source.backgroundImage = { assetId: 'removed' };
    source.decorations.push({ id: 'logic', empty: true, assetId: null, lever: { state: 'off' }, blueprint });
    const before = clone(source), result = detachDocumentAsset(source, 'removed');
    assert.equal(Object.hasOwn(result, 'backgroundImage'), false);
    assert.deepEqual(result.decorations, source.decorations);
    assert.deepEqual(source, before);
    source.backgroundImage.assetId = 'unrelated';
    assert.deepEqual(detachDocumentAsset(source, 'removed').backgroundImage, { assetId: 'unrelated' });
});

test('state and Change sprite images become inherited while execution and other targets remain intact', () => {
    const source = newDocument(), blueprint = defaultBlueprint();
    blueprint.version = 2;
    blueprint.states.open = { appearance: 'asset', assetId: 'removed' };
    blueprint.states.locked = { appearance: 'asset', assetId: 'keep' };
    blueprint.graphs['signal:FixtureEnterOpen'] = {
        nodes: [{ id: 'event', type: 'event', event: 'signal:FixtureEnterOpen', x: 0, y: 0 },
            { id: 'sprite', type: 'sprite', appearance: 'asset', assetId: 'removed', x: 2, y: 3 },
            { id: 'sound', type: 'sound', trackId: 'removed', volume: .4, x: 4, y: 3 }],
        edges: [{ from: 'event', to: 'sprite', output: 'next', kind: 'execution' },
            { from: 'sprite', to: 'sound', output: 'next', kind: 'execution' }],
    };
    source.doors.push({ id: 'door', assetId: 'base', state: 'closed', blueprint });
    const before = clone(source), result = detachDocumentAsset(source, 'removed', ['base', 'keep']);
    const cleaned = result.doors[0].blueprint;
    assert.deepEqual(source, before);
    assert.deepEqual(cleaned.states.open, { appearance: 'inherit' });
    assert.deepEqual(cleaned.states.locked, blueprint.states.locked);
    assert.deepEqual(cleaned.graphs['signal:FixtureEnterOpen'].nodes[1], { id: 'sprite', type: 'sprite', appearance: 'inherit', x: 2, y: 3 });
    assert.deepEqual(cleaned.graphs['signal:FixtureEnterOpen'].nodes[2], blueprint.graphs['signal:FixtureEnterOpen'].nodes[2]);
    assert.deepEqual(cleaned.graphs['signal:FixtureEnterOpen'].edges, blueprint.graphs['signal:FixtureEnterOpen'].edges);
});

test('a removed lever base promotes the first available state image and retains its identity and behavior', () => {
    const source = newDocument(), item = lever();
    item.blueprint.states.off = { appearance: 'asset', assetId: 'missing' };
    source.decorations.push(item);
    const result = detachDocumentAsset(source, 'removed', new Set(['alternate']));
    assert.deepEqual(result.decorations[0], { ...item, assetId: 'alternate' });
    assert.equal(source.decorations[0].assetId, 'removed');
});

test('a lever without a surviving state image keeps its geometry as an empty decoration', () => {
    const source = newDocument(), item = lever();
    source.decorations.push(item);
    const result = detachDocumentAsset(source, 'removed', []), { lever: ignoredLever, blueprint: ignoredBlueprint, ...geometry } = item;
    assert.deepEqual(result.decorations[0], { ...geometry, assetId: null });
    assert.ok(source.decorations[0].lever);
    assert.ok(source.decorations[0].blueprint);
});

test('removing only a lever state image keeps the base and returns that state to its native appearance', () => {
    const source = newDocument();
    source.decorations.push(lever('base'));
    const result = detachDocumentAsset(source, 'alternate', ['base']);
    assert.equal(result.decorations[0].assetId, 'base');
    assert.deepEqual(result.decorations[0].lever, { state: 'off' });
    assert.deepEqual(result.decorations[0].blueprint.states.on, { appearance: 'inherit' });
    assert.deepEqual(detachDocumentAsset(result, 'alternate', ['base']), result);
});

test('semantic comparison ignores object key order but detects authoring and array order changes', () => {
    const source = { document: { name: 'Room', cells: [{ x: 1, y: 2 }, { x: 3, y: 4 }] }, folderId: null };
    const reordered = { folderId: null, document: { cells: [{ y: 2, x: 1 }, { y: 4, x: 3 }], name: 'Room' } };
    assert.equal(sameDocument(source, reordered), true);
    reordered.document.cells.reverse();
    assert.equal(sameDocument(source, reordered), false);
    assert.equal(sameDocument({ name: 'Room' }, { name: 'Other room' }), false);
    assert.equal(sameDocument({ value: null }, {}), false);
    assert.equal(sameDocument([], {}), false);
    assert.equal(sameDocument({ x: 1 }, { x: '1' }), false);
});

test('deleted Set appearance actions bridge execution only and preserve typed references and authored text', () => {
    const source = newDocument(), blueprint = defaultBlueprint();
    blueprint.version = 2;
    const execution = (from, to, output = 'next') => ({ from, to, output, kind: 'execution' });
    const data = (from, to, output, input) => ({ from, to, output, input, kind: 'data' });
    const node = (id, type, fields = {}) => ({ id, type, x: 10, y: 20, ...fields });
    const group = node('group', 'elementGroup', { name: 'removed', memberType: 'element', targetIds: ['removed', 'other'] });
    const variable = node('text', 'getVariable', { scope: 'element', name: 'Identity', valueType: 'text', default: 'removed' });
    blueprint.graphs['signal:FixtureInteractClosed'] = {
        nodes: [node('event', 'event', { event: 'signal:FixtureInteractClosed' }), node('condition', 'condition', { state: 'closed' }),
            node('first', 'setAppearance', { assetId: 'removed' }), node('second', 'setAppearance', { assetId: 'removed' }),
            node('keep', 'setAppearance', { assetId: 'keep' }), node('finish', 'state', { targetState: 'open' }),
            group, variable, node('ref', 'reference', { targetId: 'removed' }), node('all', 'all'), node('compare', 'compare', { state: 'closed' })],
        edges: [execution('event', 'condition'), execution('condition', 'first', 'true'), execution('condition', 'finish', 'true'),
            execution('condition', 'keep', 'false'), execution('first', 'second'), execution('second', 'finish'),
            execution('second', 'keep'), data('group', 'first', 'targets', 'target'), data('ref', 'second', 'door', 'target'),
            data('compare', 'all', 'result', 'a'), data('compare', 'all', 'result', 'b')],
    };
    source.doors.push({ id: 'owner', assetId: 'base', state: 'closed', blueprint });
    const before = clone(source), result = detachDocumentAsset(source, 'removed', ['base', 'keep']);
    const graph = result.doors[0].blueprint.graphs['signal:FixtureInteractClosed'];
    assert.deepEqual(source, before);
    assert.equal(graph.nodes.some(node => ['first', 'second'].includes(node.id)), false);
    assert.deepEqual(graph.nodes.find(node => node.id === 'group'), group);
    assert.deepEqual(graph.nodes.find(node => node.id === 'text'), variable);
    assert.deepEqual(graph.edges, [execution('event', 'condition'), execution('condition', 'finish', 'true'),
        execution('condition', 'keep', 'true'), execution('condition', 'keep', 'false'),
        data('compare', 'all', 'result', 'a'), data('compare', 'all', 'result', 'b')]);
    assert.equal(graph.edges.some(edge => edge.from === 'group' || edge.from === 'ref'), false);
    assert.deepEqual(detachDocumentAsset(result, 'removed', ['base', 'keep']), result);
});
