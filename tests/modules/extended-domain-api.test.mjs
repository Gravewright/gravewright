import test from 'node:test';
import assert from 'node:assert/strict';
import { createDomainApi, executeNative } from '../../gravewright/modules/static/gravewright_modules/domain-api.js';

test('MapBuilder and blueprint calls retain payload revisions and retry options', async () => {
  const calls = [];
  const api = createDomainApi(async (...args) => { calls.push(args); return { ok: true }; });
  const options = { requestId: 'same-logical-operation', signal: new AbortController().signal, timeoutMs: null };
  const document = { name: 'Synthetic dungeon', version: 1 };
  const project = { projectId: 'project', expectedVersion: 4, document };
  const sync = { projectId: 'project', expectedVersion: 5, expectedSceneVersion: 8 };
  const network = { sceneId: 'scene', elementId: 'door', expectedVersion: 2, expectedProjectVersion: 5, blueprint: {} };
  const template = { templateId: 'reusable', expectedVersion: 3, name: 'Door', description: '', definition: {} };

  await api.mapBuilder.save(project, options);
  await api.mapBuilder.generate({ projectId: 'project', expectedVersion: 5 }, options);
  await api.mapBuilder.sync(sync, options);
  await api.mapBuilder.adopt({ sceneId: 'scene', expectedSceneVersion: 8 }, options);
  await api.blueprints.save(network, options);
  await api.blueprints.saveTemplate(template, options);
  await api.blueprints.testDraft({ document, elementId: 'door', event: 'interact' }, options);
  await api.blueprints.control({ sceneId: 'scene', elementId: 'door', expectedVersion: 2, action: 'open' }, options);

  assert.deepEqual(calls.map(([domain, method]) => [domain, method]), [
    ['mapBuilder', 'save'], ['mapBuilder', 'generate'], ['mapBuilder', 'sync'], ['mapBuilder', 'adopt'],
    ['blueprints', 'save'], ['blueprints', 'saveTemplate'], ['blueprints', 'testDraft'], ['blueprints', 'control'],
  ]);
  assert.equal(calls[0][2], project);
  assert.equal(calls[2][2], sync);
  assert.equal(calls[4][2], network);
  assert.equal(calls[5][2], template);
  assert.ok(calls.every(call => call[3] === options));
  assert.equal(Object.isFrozen(api.mapBuilder), true);
  assert.equal(api.mapBuilder.command, undefined);
});

test('library action compatibility and map navigation use their explicit methods', async () => {
  const calls = [];
  const api = createDomainApi(async (...args) => { calls.push(args); return {}; });
  const options = { requestId: 'library-operation' };
  await executeNative(api, 'library', 'folder-create', { name: 'Illustrations' }, options);
  await executeNative(api, 'library', 'folder-rename', { folderId: 'folder', name: 'Artwork' }, options);
  await executeNative(api, 'library', 'move', { assetId: 'asset', folderId: 'folder' }, options);
  await api.maps.navigate({ mapId: null }, options);
  await api.maps.exportUniversalVtt({ mapId: 'scene' }, options);
  assert.deepEqual(calls.map(call => call.slice(0, 3)), [
    ['library', 'createFolder', { name: 'Illustrations' }],
    ['library', 'updateFolder', { folderId: 'folder', name: 'Artwork' }],
    ['library', 'move', { assetId: 'asset', folderId: 'folder' }],
    ['maps', 'navigate', { mapId: null }],
    ['maps', 'exportUniversalVtt', { mapId: 'scene' }],
  ]);
  assert.ok(calls.every(call => call[3] === options));
  await assert.rejects(executeNative(api, 'library', 'executeSql', {}), { code: 'unavailable' });
  assert.equal(calls.length, 5);
});

test('system calls support named operations and native envelopes without changing identity', async () => {
  const calls = [];
  const context = { tableId: 'campaign', sceneId: 'scene', moduleId: 'example.integration' };
  const api = createDomainApi(async (...args) => { calls.push(args); return {}; }, { context });
  const options = { requestId: 'system-operation', timeoutMs: 30_000 };
  const data = { actorId: 'hero', source: 'template:generic' };
  await api.system.state({}, options);
  await api.system.call('example.read', data, options);
  await api.system.call({ operation: 'example.configure', data }, options);
  await api.system.call('example.list');
  assert.deepEqual(calls.map(call => call.slice(0, 3)), [
    ['system', 'state', {}],
    ['system', 'call', { operation: 'example.read', data }],
    ['system', 'call', { operation: 'example.configure', data }],
    ['system', 'call', { operation: 'example.list', data: {} }],
  ]);
  assert.ok(calls.slice(0, 3).every(call => call[3] === options));
  context.sceneId = 'another-scene';
  assert.equal(api.context.sceneId, 'scene');
  assert.equal(Object.isFrozen(api.system), true);
  await assert.rejects(api.system.call(null), { code: 'invalid_data' });
  await assert.rejects(api.blueprints.save([]), { code: 'invalid_data' });
  assert.equal(calls.length, 4);
});

test('capability catalog is local and caller mutations cannot change future calls', async () => {
  let remoteCalls = 0;
  const api = createDomainApi(async () => { remoteCalls++; return {}; });
  const capabilities = api.capabilities();
  assert.equal(capabilities.version, api.version);
  assert.equal(capabilities.domains.mapBuilder.sync, 'sync');
  assert.ok(capabilities.reads.actors.includes('sheet'));
  assert.ok(capabilities.services.dice.includes('roll'));
  capabilities.domains.mapBuilder.sync = 'run-unrestricted';
  capabilities.services.dice.push('setAdmin');
  assert.equal(api.capabilities().domains.mapBuilder.sync, 'sync');
  assert.deepEqual(api.capabilities().services.dice, ['roll']);
  assert.equal(remoteCalls, 0);
  assert.equal(api.mapBuilder.runUnrestricted, undefined);
});

test('ownership calls retain explicit document identity and caller revisions', async () => {
  const calls = [];
  const api = createDomainApi(async (...args) => { calls.push(args); return { version: 9 }; });
  const options = { requestId: 'permission-change' };
  const document = { kind: 'pages', id: 'journal:page' };
  const update = { ...document, version: 8, permissions: { default: 'inherit' } };
  await api.ownership.state(document, options);
  await api.ownership.read(document, options);
  await api.ownership.update(update, options);
  assert.deepEqual(calls.map(call => call.slice(0, 3)), [
    ['ownership', 'state', document], ['ownership', 'read', document], ['ownership', 'update', update],
  ]);
  assert.ok(calls.every(call => call[3] === options));
  assert.equal(update.version, 8);
  assert.equal(api.ownership.get, undefined);
  assert.ok(Object.isFrozen(api.ownership));
});
