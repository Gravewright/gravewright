import test from 'node:test';
import assert from 'node:assert/strict';
import { sceneControlPage, sceneControlKind, sceneControlActions, sceneControlRows, sceneNativeItem, sceneNativePayload } from './scene-controls.js';

test('scene controls bound cards while searching all authored names and event names', () => {
    const elements = Array.from({ length: 101 }, (_, index) => ({ id: String(index), kind: 'door', name: `Door ${index}` }));
    elements[100].name = 'Alavanca de saída 雪'; elements[100].blueprint = { graphs: { 'signal:abrir': {} } };
    const before = structuredClone(elements);
    assert.equal(sceneControlPage({ elements }).rows.length, 40);
    assert.deepEqual(sceneControlPage({ elements }, { page: 99 }).rows.map(row => row.id), elements.slice(80).map(row => row.id));
    assert.equal(sceneControlPage({ elements }, { query: 'SAÍDA 雪' }).rows[0].id, '100');
    assert.equal(sceneControlPage({ elements }, { query: 'signal:abrir' }).total, 1);
    assert.deepEqual(elements, before);
});

test('dynamic floors and walls have their own filter without changing native owner identity', () => {
    const elements = [{ id: 'floor', kind: 'image', surfaceKind: 'floor' }, { id: 'wall', kind: 'image', surfaceKind: 'wall' }, { id: 'plain', kind: 'image' }];
    assert.equal(sceneControlKind(elements[0]), 'floor');
    assert.deepEqual(sceneControlPage({ elements }, { type: 'image' }).rows.map(row => row.id), ['plain']);
    assert.deepEqual(sceneControlPage({ elements }, { type: 'wall' }).rows.map(row => row.id), ['wall']);
    assert.equal(sceneControlPage({ elements }, { query: 'absent' }).pages, 1);
});

test('Empty Objects have a separate scene filter while keeping their native mechanism identity and authored name', () => {
    const owner = { id: 'controller', empty: true, kind: 'lever', name: 'Invisible encounter controller',
        state: 'off', assetId: null, blueprint: { version: 2, graphs: {} } };
    const catalog = { elements: [owner, { id: 'lever', kind: 'lever', name: 'Visible lever' }] };
    assert.equal(sceneControlKind(owner), 'empty');
    assert.deepEqual(sceneControlPage(catalog, { type: 'empty' }).rows, [owner]);
    assert.equal(sceneControlPage(catalog, { type: 'lever' }).rows[0].id, 'lever');
    assert.equal(sceneControlPage(catalog, { query: 'encounter' }).rows[0].name, owner.name);
    assert.deepEqual(sceneControlActions(owner), [{ action: 'interact', label: 'Run interaction', disabled: true }]);
});

test('native actions reflect current state and never offer flame controls on a plain image', () => {
    const door = sceneControlActions({ kind: 'door', state: 'closed', blueprint: { graphs: {} } });
    assert.equal(door.find(row => row.value === 'closed').disabled, true);
    assert.equal(door.find(row => row.action === 'interact').disabled, true);
    const smartDoor = sceneControlActions({ kind: 'door', state: 'locked', blueprint: { graphs: { 'interact:locked': {} } } });
    assert.equal(smartDoor.find(row => row.action === 'interact').disabled, true);
    const torch = sceneControlActions({ kind: 'torch', state: 'off', lit: true, visible: false });
    assert.equal(torch.find(row => row.action === 'flame').value, false);
    assert.equal(torch.find(row => row.action === 'visibility').value, true);
    assert.deepEqual(sceneControlActions({ kind: 'image', lit: true }), []);
});

test('generic interaction controls enable only wired handlers and describe a gesture independently of its actions', () => {
    const graph = { nodes: [{ id: 'event', type: 'event', event: 'interact' }, { id: 'action', type: 'showMessage' }], edges: [] };
    const owner = { kind: 'door', state: 'locked', blueprint: { version: 2, graphs: { interact: graph } } };
    assert.equal(sceneControlActions(owner).find(row => row.action === 'interact').disabled, true);
    graph.edges.push({ from: 'event', output: 'next', to: 'action', kind: 'execution' });
    assert.equal(sceneControlActions(owner).find(row => row.action === 'interact').disabled, false);
    assert.equal(sceneControlActions({ ...owner, kind: 'torch', state: 'off' }).find(row => row.action === 'interact').label, 'Run interaction');
    assert.equal(sceneControlActions({ ...owner, kind: 'lever', state: 'on' }).find(row => row.action === 'interact').label, 'Run interaction');
    assert.equal(sceneControlActions({ ...owner, blueprint: { ...owner.blueprint, version: 1 } }).find(row => row.action === 'interact').disabled, true);
    const empty = sceneControlActions({ kind: 'lever', state: 'off', blueprint: { version: 2, graphs: {} } });
    assert.deepEqual(empty.find(row => row.action === 'interact'), { action: 'interact', label: 'Run interaction', disabled: true });
});

test('native lights and effects join the paged catalog without becoming behavior owners', () => {
    const catalog = { elements: [{ id: 'door', kind: 'door' }],
        lights: [{ id: 'light', nativeKind: 'lights', x: 5, y: 6, nativeData: { enabled: false } }],
        effects: [{ id: 'particle', nativeKind: 'particles', nativeData: { enabled: true, kind: 'smoke' } },
            { id: 'shader', nativeKind: 'shaders', nativeData: { enabled: false } }] };
    const before = structuredClone(catalog), rows = sceneControlRows(catalog);
    assert.deepEqual(rows.map(row => row.kind), ['door', 'light', 'particle', 'shader']);
    assert.deepEqual(rows[1].point, { x: 5, y: 6 });
    assert.equal(rows[1].enabled, false); assert.equal(rows[2].editable, false);
    assert.equal(sceneControlPage(catalog, { type: 'shader' }).rows[0].id, 'shader');
    assert.deepEqual(catalog, before);
});

test('native editor adapter preserves geometry and maps light radii with its own CAS contract', () => {
    const owner = { id: 'light', version: 7, nativeKind: 'lights', nativeData: { x: 40, y: 80, bright_radius: 2, dim_radius: 4, enabled: true, elevation: 9 } };
    const original = structuredClone(owner), item = sceneNativeItem(owner);
    item.brightRadius = 3; item.dimRadius = 6; item.enabled = false;
    assert.deepEqual(sceneNativePayload(owner, item), { x: 40, y: 80, bright_radius: 3, dim_radius: 6, enabled: false, elevation: 9, light_id: 'light', version: 7 });
    assert.deepEqual(owner, original);
    const particle = { id: 'particle', version: 3, nativeKind: 'particles', nativeData: { x: 5, y: 6, kind: 'smoke', enabled: false } };
    const payload = sceneNativePayload(particle, sceneNativeItem(particle));
    assert.equal(payload.kind, 'smoke'); assert.equal(payload.emitter_id, 'particle'); assert.equal(payload.expected_version, 3);
    assert.equal(payload.version, undefined);
});

test('shader editor preset references resolve to native source before authorized update', () => {
    const owner = { id: 'shader', version: 2, nativeKind: 'shaders', nativeData: { name: 'Authored', source: 'gravewright-preset://orb-1/v1', x: 1, y: 2 } };
    const payload = sceneNativePayload(owner, sceneNativeItem(owner), [{ id: 'orb-1', source: 'void main() {}' }]);
    assert.equal(payload.source, 'void main() {}'); assert.equal(payload.shader_id, owner.id); assert.equal(payload.expected_version, 2);
    assert.throws(() => sceneNativePayload(owner, sceneNativeItem(owner)), /Unknown shader preset/);
    assert.equal(owner.nativeData.source, 'gravewright-preset://orb-1/v1');
});
