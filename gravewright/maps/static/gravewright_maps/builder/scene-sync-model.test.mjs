import test from 'node:test';
import assert from 'node:assert/strict';
import { mergeSceneProject } from './scene-sync-model.js';

const project = () => ({ schemaVersion: 3, name: 'Câmara do Guardião', doors: [
    { id: 'door', name: 'Guardian door', state: 'closed', x1: 1, x2: 2, blueprint: { variables: { visits: 0 } } },
], decorations: [], lights: [{ id: 'torch', enabled: true, radius: 6 }], walls: [], layers: [] });
const frozen = value => {
    if (value && typeof value === 'object') {
        for (const entry of Object.values(value)) frozen(entry);
        Object.freeze(value);
    }
    return value;
};

test('imports in-game state while preserving unrelated unsaved authoring and all input documents', () => {
    const base = project(), local = structuredClone(base), remote = structuredClone(base);
    local.doors[0].name = 'Porta — saída / norte';
    local.doors[0].x2 = 3;
    remote.doors[0].state = 'open';
    remote.doors[0].blueprint.variables.visits = 2;
    remote.lights[0].enabled = false;
    const before = structuredClone({ base, local, remote });
    for (const document of [base, local, remote]) frozen(document);
    const result = mergeSceneProject(base, local, remote);
    assert.deepEqual(result.conflicts, []);
    assert.deepEqual(result.document.doors, [{ ...remote.doors[0], name: local.doors[0].name, x2: 3 }]);
    assert.deepEqual(result.document.lights, remote.lights);
    assert.deepEqual({ base, local, remote }, before);
    result.document.doors[0].blueprint.variables.visits = 100;
    result.document.lights[0].enabled = true;
    assert.equal(remote.doors[0].blueprint.variables.visits, 2);
    assert.equal(remote.lights[0].enabled, false);
});

test('reports only the divergent fields and preserves equal concurrent changes', () => {
    const base = project(), local = structuredClone(base), remote = structuredClone(base);
    local.doors[0].state = remote.doors[0].state = 'locked';
    local.doors[0].x1 = 4;
    remote.doors[0].x1 = 7;
    remote.doors[0].name = 'Game name';
    const result = mergeSceneProject(base, local, remote);
    assert.deepEqual(result.conflicts, ['/doors/door/x1']);
    assert.equal(result.document.doors[0].x1, 4);
    assert.equal(result.document.doors[0].state, 'locked');
    assert.equal(result.document.doors[0].name, 'Game name');
});

test('merges independent additions and deletions by row identity', () => {
    const base = { doors: [{ id: 'a', state: 'closed' }, { id: 'b', state: 'closed' }, { id: 'c', state: 'closed' }] };
    const local = { doors: [{ id: 'a', state: 'closed' }, { id: 'local', state: 'open' }, { id: 'b', state: 'closed' }] };
    const remote = { doors: [{ id: 'a', state: 'open' }, { id: 'remote', state: 'locked' }, { id: 'c', state: 'closed' }] };
    const result = mergeSceneProject(base, local, remote);
    assert.deepEqual(result.conflicts, []);
    assert.deepEqual(result.document.doors, [
        { id: 'a', state: 'open' }, { id: 'local', state: 'open' }, { id: 'remote', state: 'locked' },
    ]);
});

test('conflicting deletion versus edit keeps the preferred side and reports the whole row', () => {
    const base = project(), removed = structuredClone(base), edited = structuredClone(base);
    removed.doors = [];
    edited.doors[0].state = 'open';
    const localRemoval = mergeSceneProject(base, removed, edited);
    assert.deepEqual(localRemoval.conflicts, ['/doors/door']);
    assert.deepEqual(localRemoval.document.doors, []);
    const remoteRemoval = mergeSceneProject(base, edited, removed);
    assert.deepEqual(remoteRemoval.conflicts, ['/doors/door']);
    assert.deepEqual(remoteRemoval.document.doors, edited.doors);
    const acceptedEdit = mergeSceneProject(base, removed, edited, { preferRemote: true });
    assert.deepEqual(acceptedEdit.conflicts, ['/doors/door']);
    assert.deepEqual(acceptedEdit.document.doors, edited.doors);
    const acceptedRemoval = mergeSceneProject(base, edited, removed, { preferRemote: true });
    assert.deepEqual(acceptedRemoval.conflicts, ['/doors/door']);
    assert.deepEqual(acceptedRemoval.document.doors, []);
});

test('rebasing undo snapshots retains authoring history but cannot undo an accepted game delta', () => {
    const base = project(), historical = structuredClone(base), remote = structuredClone(base);
    historical.name = 'Previous local title';
    historical.doors[0].state = 'locked';
    historical.doors[0].x1 = 8;
    remote.doors[0].state = 'open';
    remote.lights = [];
    historical.lights[0].radius = 10;
    const result = mergeSceneProject(base, historical, remote, { preferRemote: true });
    assert.deepEqual(result.conflicts, ['/doors/door/state', '/lights/torch']);
    assert.equal(result.document.name, historical.name);
    assert.equal(result.document.doors[0].x1, 8);
    assert.equal(result.document.doors[0].state, 'open');
    assert.deepEqual(result.document.lights, []);
});

test('keeps concurrent row additions and nested keyed Blueprint edits', () => {
    const base = { doors: [], graphs: { interact: { nodes: [{ id: 'event', x: 0, type: 'event' }], edges: [] } } };
    const local = structuredClone(base), remote = structuredClone(base);
    local.doors.push({ id: 'new', name: 'Door' });
    remote.doors.push({ id: 'new', name: 'Door', state: 'open' });
    local.graphs.interact.nodes[0].x = 100;
    remote.graphs.interact.nodes.push({ id: 'state', type: 'state' });
    const result = mergeSceneProject(base, local, remote);
    assert.deepEqual(result.conflicts, []);
    assert.deepEqual(result.document.doors, remote.doors);
    assert.deepEqual(result.document.graphs.interact.nodes, [{ id: 'event', x: 100, type: 'event' }, { id: 'state', type: 'state' }]);
});

test('treats point, reference and duplicate-ID arrays as atomic', () => {
    const base = { points: [[0, 0], [1, 1]], targets: ['a'], rows: [{ id: 'same', x: 1 }, { id: 'same', x: 2 }] };
    const local = structuredClone(base), remote = structuredClone(base);
    local.points[0][0] = 2;
    remote.points[1][1] = 3;
    remote.targets.push('b');
    local.rows[0].x = 3;
    remote.rows[1].x = 4;
    const result = mergeSceneProject(base, local, remote);
    assert.deepEqual(result.conflicts, ['/points', '/rows']);
    assert.deepEqual(result.document.points, local.points);
    assert.deepEqual(result.document.rows, local.rows);
    assert.deepEqual(result.document.targets, ['a', 'b']);
});

test('merges independently imported classified assets by assetId', () => {
    const base = { assets: [{ assetId: 'stone', role: 'floor', name: 'Stone' }] };
    const local = { assets: [...base.assets, { assetId: 'wood', role: 'decoration', name: 'Imported locally' }] };
    const remote = { assets: [{ ...base.assets[0], name: 'Pedra — do salão' }, { assetId: 'iron', role: 'door' }] };
    const result = mergeSceneProject(base, local, remote);
    assert.deepEqual(result.conflicts, []);
    assert.deepEqual(result.document.assets, [remote.assets[0], local.assets[1], remote.assets[1]]);
    result.document.assets[0].name = 'Detached copy';
    assert.equal(remote.assets[0].name, 'Pedra — do salão');
});

test('reports divergent classifications of the same catalog asset', () => {
    const base = { assets: [{ assetId: 'image', role: 'decoration', name: 'Artwork' }] };
    const local = { assets: [{ ...base.assets[0], role: 'floor' }] };
    const remote = { assets: [{ ...base.assets[0], role: 'door', name: 'Game artwork' }] };
    const result = mergeSceneProject(base, local, remote);
    assert.deepEqual(result.conflicts, ['/assets/image/role']);
    assert.deepEqual(result.document.assets, [{ assetId: 'image', role: 'floor', name: 'Game artwork' }]);
    const preferred = mergeSceneProject(base, local, remote, { preferRemote: true });
    assert.deepEqual(preferred.conflicts, ['/assets/image/role']);
    assert.deepEqual(preferred.document.assets, remote.assets);
});

test('assetId does not change the identity contract of unrelated nested arrays', () => {
    const base = { settings: { assets: [{ assetId: 'image', value: 1 }] } };
    const local = { settings: { assets: [...base.settings.assets, { assetId: 'local', value: 2 }] } };
    const remote = { settings: { assets: [...base.settings.assets, { assetId: 'remote', value: 3 }] } };
    const result = mergeSceneProject(base, local, remote);
    assert.deepEqual(result.conflicts, ['/settings/assets']);
    assert.deepEqual(result.document, local);
});

test('merges a one-sided reorder with remote edits and insertions', () => {
    const base = { layers: [{ id: 'a', name: 'A' }, { id: 'b', name: 'B' }, { id: 'c', name: 'C' }] };
    const local = { layers: [base.layers[2], base.layers[0], base.layers[1]] };
    const remote = { layers: [{ id: 'a', name: 'Changed' }, { id: 'new', name: 'New' }, base.layers[1], base.layers[2]] };
    const result = mergeSceneProject(base, local, remote);
    assert.deepEqual(result.conflicts, []);
    assert.deepEqual(result.document.layers.map(row => row.id), ['c', 'a', 'new', 'b']);
    assert.equal(result.document.layers[1].name, 'Changed');
});

test('reports incompatible reorders instead of silently replacing local ordering', () => {
    const base = { layers: ['a', 'b', 'c'].map(id => ({ id })) };
    const local = { layers: [base.layers[1], base.layers[0], base.layers[2]] };
    const remote = { layers: [base.layers[0], base.layers[2], base.layers[1]] };
    const result = mergeSceneProject(base, local, remote);
    assert.deepEqual(result.conflicts, ['/layers/$order']);
    assert.deepEqual(result.document.layers, local.layers);
    const preferred = mergeSceneProject(base, local, remote, { preferRemote: true });
    assert.deepEqual(preferred.conflicts, ['/layers/$order']);
    assert.deepEqual(preferred.document.layers, remote.layers);
});

test('detects incompatible placement of the same added row while retaining independent additions', () => {
    const base = { layers: ['a', 'b'].map(id => ({ id })) };
    const local = { layers: [base.layers[0], { id: 'new' }, base.layers[1], { id: 'local' }] };
    const remote = { layers: [{ id: 'new' }, base.layers[0], { id: 'remote' }, base.layers[1]] };
    const result = mergeSceneProject(base, local, remote);
    assert.deepEqual(result.conflicts, ['/layers/$order']);
    assert.deepEqual(result.document.layers.map(row => row.id), ['a', 'new', 'remote', 'b', 'local']);
});

test('merges missing optional properties and distinguishes deletion from null', () => {
    const base = { setting: { value: 1 }, disabled: null }, local = {}, remote = { setting: { value: 2 }, disabled: null, optional: { value: null } };
    const result = mergeSceneProject(base, local, remote);
    assert.deepEqual(result.conflicts, ['/setting']);
    assert.equal(Object.hasOwn(result.document, 'setting'), false);
    assert.equal(Object.hasOwn(result.document, 'disabled'), false);
    assert.deepEqual(result.document.optional, { value: null });
});

test('copies prototype-like JSON keys safely and escapes conflict pointer segments', () => {
    const base = JSON.parse('{"__proto__":{"polluted":false},"constructor":{"prototype":{"safe":true}},"doors":[{"id":"a/b~c","state":"closed"}]}');
    const local = structuredClone(base), remote = structuredClone(base);
    local.__proto__.polluted = true;
    remote.constructor.prototype.safe = false;
    local.doors[0].state = 'locked';
    remote.doors[0].state = 'open';
    const result = mergeSceneProject(base, local, remote);
    assert.deepEqual(result.conflicts, ['/doors/a~1b~0c/state']);
    assert.equal(Object.getPrototypeOf(result.document), Object.prototype);
    assert.equal(Object.hasOwn(result.document, '__proto__'), true);
    assert.equal(result.document.__proto__.polluted, true);
    assert.equal(result.document.constructor.prototype.safe, false);
    assert.equal({}.polluted, undefined);
});
