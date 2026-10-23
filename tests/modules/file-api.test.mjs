import test from 'node:test';
import assert from 'node:assert/strict';
import { createFileCaller, domainTiming } from '../../gravewright/modules/static/gravewright_modules/file-api.js';
import { createDomainApi, executeNative } from '../../gravewright/modules/static/gravewright_modules/domain-api.js';
import { BrowserBridge } from '../../gravewright/modules/static/gravewright_modules/browser-bridge.js';
import { HttpClient } from '../../gravewright/modules/static/gravewright_modules/http-client.js';
import { Lifetime } from '../../gravewright/modules/static/gravewright_modules/lifetime.js';

const REQUEST = 'df1ddc36-3b22-4e86-b66b-e38cc8313601';
const BYTES = new Uint8Array([0, 255, 7, 13, 10, 128, 25]);
const csrf = { header: 'X-Test-CSRF', token: 'synthetic-csrf' };
const json = value => new Response(JSON.stringify({ value }), { status: 200, headers: { 'content-type': 'application/json' } });
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};

function browser(t, metadata = {}) {
  const previous = { document: globalThis.document, window: globalThis.window, fetch: globalThis.fetch };
  globalThis.window = new EventTarget();
  globalThis.document = {
    getElementById: () => null,
    querySelector: selector => {
      const key = selector.match(/^meta\[name="(.+)"\]$/)?.[1];
      return metadata[key] ? { content: metadata[key] } : null;
    },
  };
  t.after(() => Object.assign(globalThis, previous));
}

function fixture(t, metadata = {}) {
  browser(t, metadata);
  const life = new Lifetime();
  t.after(() => life.close());
  const calls = [];
  const http = { get: async (path, options) => { calls.push({ path, options }); return csrf; } };
  const fileCall = createFileCaller({ http, life, path: '/api/tables/table/files', identity: { tableId: 'table' } });
  return { life, http, calls, fileCall };
}

test('file uploads preserve bytes, multipart metadata, CSRF and configured API paths', async t => {
  const { fileCall, calls } = fixture(t, { 'gravewright-csrf-url': '/csrf-local', 'gravewright-backend-api': '/proxy-api' });
  const requests = [], progress = [];
  globalThis.fetch = async (url, options) => { requests.push({ url, options }); return json({ id: 'asset' }); };
  const file = new File([BYTES], 'ficha ação.pdf', { type: 'application/pdf' });
  const result = await fileCall('actors', 'uploadAsset', { file, folderId: 'folder' }, { requestId: REQUEST, onProgress: value => progress.push(value) });
  assert.deepEqual(result, { id: 'asset' });
  assert.equal(calls[0].path, '/csrf-local');
  const { url, options } = requests[0];
  assert.equal(url, '/proxy-api/tables/table/files');
  assert.equal(options.method, 'POST');
  assert.equal(options.credentials, 'same-origin');
  assert.equal(options.headers[csrf.header], csrf.token);
  assert.equal(options.headers['content-type'], undefined, 'the browser must supply the multipart boundary');
  assert.ok(options.body instanceof FormData);
  const uploaded = options.body.get('file');
  assert.equal(uploaded.name, file.name);
  assert.equal(uploaded.type, file.type);
  assert.deepEqual(new Uint8Array(await uploaded.arrayBuffer()), BYTES);
  assert.deepEqual(JSON.parse(options.body.get('metadata')), {
    domain: 'actors', method: 'uploadAsset', payload: { folderId: 'folder' }, requestId: REQUEST,
  });
  assert.deepEqual(progress, [{ loaded: file.size, total: file.size }]);
});

test('Universal VTT uploads retain retry UUIDs and generate a UUID only for a new operation', async t => {
  const { fileCall } = fixture(t), envelopes = [];
  globalThis.fetch = async (_url, options) => { envelopes.push(JSON.parse(options.body.get('metadata'))); return json({ sceneId: 'scene' }); };
  const payload = { file: new File(['{"format":0.3}'], 'room.dd2vtt', { type: 'application/json' }), folderId: 'folder' };
  await fileCall('maps', 'importUniversalVtt', payload, { requestId: REQUEST });
  await fileCall('maps', 'importUniversalVtt', payload, { requestId: REQUEST });
  await fileCall('maps', 'importUniversalVtt', payload);
  assert.equal(envelopes[0].requestId, REQUEST);
  assert.equal(envelopes[1].requestId, REQUEST);
  assert.match(envelopes[2].requestId, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  assert.notEqual(envelopes[2].requestId, REQUEST);
  assert.deepEqual(envelopes[0].payload, { folderId: 'folder' });
});

test('downloads return real bytes and UTF-8 filenames without JSON decoding', async t => {
  const { fileCall } = fixture(t), requests = [], progress = [];
  globalThis.fetch = async (_url, options) => {
    requests.push(options);
    return new Response(BYTES, { headers: { 'content-type': 'application/pdf', 'content-disposition': 'attachment; filename="fallback.pdf"; filename*=UTF-8\'\'ficha%20a%C3%A7%C3%A3o.pdf' } });
  };
  const result = await fileCall('actors', 'downloadAsset', { id: 'asset' }, { requestId: REQUEST, onProgress: value => progress.push(value) });
  assert.equal(result.name, 'ficha ação.pdf');
  assert.equal(result.contentType, 'application/pdf');
  assert.equal(result.size, BYTES.length);
  assert.deepEqual(new Uint8Array(await result.blob.arrayBuffer()), BYTES);
  assert.equal(requests[0].headers['content-type'], 'application/json');
  assert.deepEqual(JSON.parse(requests[0].body), { domain: 'actors', method: 'downloadAsset', payload: { id: 'asset' }, requestId: REQUEST });
  assert.deepEqual(progress, [{ loaded: BYTES.length, total: BYTES.length }]);
});

test('malformed filename encoding falls back to the plain filename', async t => {
  const { fileCall } = fixture(t);
  globalThis.fetch = async () => new Response(BYTES, { headers: { 'content-disposition': 'attachment; filename="safe.bin"; filename*=utf-8\'\'%E0%A4%A' } });
  assert.equal((await fileCall('library', 'download', { id: 'asset' })).name, 'safe.bin');
  globalThis.fetch = async () => new Response(BYTES);
  assert.equal((await fileCall('library', 'download', { id: 'asset' })).name, 'download.bin');
});

test('all binary domain wrappers use the file transport and retain caller options', async () => {
  const calls = [], jsonCalls = [];
  const api = createDomainApi(async (...args) => { jsonCalls.push(args); }, { files: async (...args) => { calls.push(args); return { ok: true }; } });
  const entries = [
    ['maps', 'upload'], ['maps', 'importUniversalVtt'], ['library', 'upload'], ['library', 'download'],
    ['actors', 'uploadAsset'], ['actors', 'uploadImage'], ['actors', 'downloadAsset'], ['audio', 'upload'],
    ['cards', 'uploadAsset'], ['journals', 'uploadAsset'], ['journals', 'downloadAsset'],
  ];
  const file = new File([BYTES], 'test.bin'), payload = { file, id: 'asset' }, options = { requestId: REQUEST, signal: new AbortController().signal };
  for (const [domain, method] of entries) await api[domain][method](payload, options);
  assert.deepEqual(calls.map(call => call.slice(0, 2)), entries);
  assert.ok(calls.every(call => call[2] === payload && call[3] === options));
  assert.equal(jsonCalls.length, 0);
  await assert.rejects(api.maps.upload(null), { code: 'invalid_data' });
  assert.equal(api.maps.executeSql, undefined);
  await assert.rejects(executeNative(api, 'maps', 'not-a-method', {}), { code: 'unavailable' });
  assert.equal(calls.length, entries.length);
});

test('binary methods without a file adapter fail instead of falling back to JSON', async () => {
  let jsonCalls = 0;
  const api = createDomainApi(async () => { jsonCalls++; });
  await assert.rejects(api.library.upload({ file: new File([BYTES], 'test.bin') }), { code: 'unavailable' });
  await assert.rejects(api.actors.downloadAsset({ id: 'asset' }), { code: 'unavailable' });
  assert.equal(jsonCalls, 0);
});

test('unknown operations and non-file uploads make no binary request', async t => {
  const { fileCall } = fixture(t);
  let fetches = 0;
  globalThis.fetch = async () => { fetches++; return json({}); };
  await assert.rejects(fileCall('maps', 'unknown', {}), { code: 'invalid_data' });
  await assert.rejects(fileCall('maps', 'upload', { file: BYTES }), { code: 'invalid_data' });
  await assert.rejects(fileCall('maps', 'upload', []), { code: 'invalid_data' });
  assert.equal(fetches, 0);
});

test('file errors retain public codes and a failed request is never retried through JSON', async t => {
  const { fileCall } = fixture(t);
  let fetches = 0;
  for (const [status, body, expected] of [[403, { error: 'permission_denied' }, 'permission_denied'],
    [409, { error: 'conflict' }, 'conflict'], [404, {}, 'not_found'], [500, { error: 'private_backend_detail' }, 'unavailable']]) {
    globalThis.fetch = async () => { fetches++; return new Response(JSON.stringify(body), { status }); };
    await assert.rejects(fileCall('library', 'download', { id: 'asset' }), { code: expected });
  }
  assert.equal(fetches, 4);
});

test('CSRF transport failures retain the public unavailable error without sending a file', async t => {
  browser(t);
  const life = new Lifetime();
  t.after(() => life.close());
  let fetches = 0;
  globalThis.fetch = async () => { fetches++; return json({}); };
  const fileCall = createFileCaller({ life, path: '/api/files', http: { get: async () => { throw new Error('Synthetic network failure'); } } });
  await assert.rejects(fileCall('library', 'download', { id: 'asset' }), { code: 'unavailable' });
  assert.equal(fetches, 0);
});

test('late body decoding cannot emit progress after its owning lifetime closes', async t => {
  const { fileCall, life } = fixture(t), decoding = deferred(), body = deferred(), progress = [];
  globalThis.fetch = async () => ({ ok: true, headers: new Headers(), blob: async () => { decoding.resolve(); return body.promise; } });
  const pending = fileCall('library', 'download', { id: 'asset' }, { onProgress: value => progress.push(value) });
  await decoding.promise;
  await life.close();
  await assert.rejects(pending, { code: 'stale_context' });
  body.resolve(new Blob([BYTES]));
  await Promise.resolve(); await Promise.resolve(); await Promise.resolve();
  assert.deepEqual(progress, []);
});

test('caller cancellation aborts pending file work while disposal makes its handle stale', async t => {
  const { fileCall, life } = fixture(t), started = deferred();
  let transportSignal;
  globalThis.fetch = async (_url, options) => {
    transportSignal = options.signal; started.resolve();
    return new Promise((_resolve, reject) => options.signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true }));
  };
  const cancellation = new AbortController();
  const pending = fileCall('library', 'download', { id: 'asset' }, { signal: cancellation.signal });
  await started.promise; cancellation.abort();
  await assert.rejects(pending, { code: 'cancelled' });
  assert.equal(transportSignal.aborted, true);
  const next = deferred();
  globalThis.fetch = async (_url, options) => { transportSignal = options.signal; next.resolve(); return new Promise(() => {}); };
  const stale = fileCall('library', 'download', { id: 'asset' });
  await next.promise; await life.close();
  await assert.rejects(stale, { code: 'stale_context' });
  assert.equal(transportSignal.aborted, true);
  await assert.rejects(fileCall('library', 'download', { id: 'asset' }), { code: 'stale_context' });
});

test('pre-cancelled calls do not open leases or acquire CSRF tokens', async t => {
  browser(t);
  const life = new Lifetime(), cancellation = new AbortController();
  let work = 0;
  const fileCall = createFileCaller({ life, http: { get: async () => { work++; return csrf; } },
    path: '/api/files', ensure: async () => { work++; } });
  cancellation.abort();
  await assert.rejects(fileCall('library', 'download', { id: 'asset' }, { signal: cancellation.signal }), { code: 'cancelled' });
  assert.equal(work, 0);
  await life.close();
});

test('file transfers have no default timeout and an explicit deadline aborts transport', async t => {
  const { fileCall } = fixture(t);
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const started = deferred(), reply = deferred();
  let signal;
  globalThis.fetch = async (_url, options) => { signal = options.signal; started.resolve(); return reply.promise; };
  const pending = fileCall('library', 'download', { id: 'asset' });
  await started.promise; t.mock.timers.tick(60_000);
  assert.equal(signal.aborted, false);
  reply.resolve(new Response(BYTES)); await pending;
  const timed = deferred();
  globalThis.fetch = async (_url, options) => {
    signal = options.signal; timed.resolve();
    return new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('Timeout', 'AbortError')), { once: true }));
  };
  const deadline = fileCall('library', 'download', { id: 'asset' }, { timeoutMs: 20 });
  await timed.promise; t.mock.timers.tick(20);
  assert.equal(signal.aborted, true);
  await assert.rejects(deadline, { code: 'unavailable' });
});

test('module binary calls renew their own lease and retain scene and mount identity', async t => {
  browser(t);
  const bridge = new BrowserBridge('table'), life = new Lifetime(), leases = [], requests = [];
  bridge.http = { post: async (path, payload) => { leases.push({ path, payload }); return {}; }, get: async () => csrf };
  globalThis.fetch = async (url, options) => { requests.push({ url, metadata: JSON.parse(options.body.get('metadata')) }); return json({ id: 'asset' }); };
  const identity = { tableId: 'table', moduleId: 'fixture.files', mountId: 'mount', moduleSetRevision: 'revision', sceneId: 'bound-scene' };
  const api = bridge.api(identity, life);
  const payload = { file: new File([BYTES], 'test.png'), sceneId: 'bound-scene' };
  await api.library.upload(payload, { requestId: REQUEST });
  bridge.leaseTimes.set(life, Date.now() - 11 * 60_000);
  await api.library.upload(payload, { requestId: REQUEST });
  assert.deepEqual(leases.map(call => call.payload.action), ['open', 'open']);
  assert.equal(requests[0].url, '/api/tables/table/modules/fixture.files/files');
  assert.deepEqual(requests[0].metadata, { domain: 'library', method: 'upload', payload: { sceneId: 'bound-scene' }, requestId: REQUEST,
    mountId: 'mount', moduleSetRevision: 'revision', sceneId: 'bound-scene' });
  await assert.rejects(api.library.upload({ ...payload, sceneId: 'other' }), { code: 'stale_context' });
  assert.equal(requests.length, 2);
  await life.close();
  assert.deepEqual(leases.map(call => call.payload.action), ['open', 'open', 'close']);
  await assert.rejects(api.library.upload(payload), { code: 'stale_context' });
  assert.equal(requests.length, 2);
});

test('heavy JSON operations opt out of the normal timeout while explicit options remain authoritative', async t => {
  browser(t);
  const bridge = new BrowserBridge('table'), life = new Lifetime(), calls = [];
  bridge.ensure = async () => {};
  bridge.http = { post: async (path, payload, options) => { calls.push({ path, payload, options }); return { value: {} }; } };
  const api = bridge.api({ moduleId: 'fixture.files', tableId: 'table', mountId: 'mount', moduleSetRevision: 'revision' }, life);
  await api.mapBuilder.generate({ projectId: 'project', expectedVersion: 1 });
  await api.maps.exportUniversalVtt({ sceneId: 'scene' });
  await api.blueprints.testDraft({ document: {}, elementId: 'element', event: 'interact' });
  await api.actors.state();
  await api.mapBuilder.generate({ projectId: 'project', expectedVersion: 1 }, { timeoutMs: 1234 });
  assert.deepEqual(calls.slice(0, 3).map(call => call.options.timeoutMs), [null, null, null]);
  assert.equal(Object.hasOwn(calls[3].options, 'timeoutMs'), false);
  assert.equal(calls[4].options.timeoutMs, 1234);
  assert.deepEqual(domainTiming('actors', 'state', { timeoutMs: null }), { timeoutMs: null });
  await life.close();
});

test('HttpClient.download uses the injected byte transport with caller signal and Unicode headers', async t => {
  browser(t, { 'gravewright-backend-api': '/local-api' });
  const calls = [], cancellation = new AbortController(), progress = [];
  const client = new HttpClient({ request: async (url, options) => {
    calls.push({ url, options });
    return new Response(BYTES, { headers: { 'content-type': 'application/pdf', 'content-disposition': "attachment; filename*=UTF-8''a%C3%A7%C3%A3o.pdf" } });
  } });
  globalThis.fetch = async () => { throw new Error('The injected transport must be used'); };
  const result = await client.download('/api/assets/asset', { signal: cancellation.signal, onProgress: value => progress.push(value) });
  assert.equal(calls[0].url, '/local-api/assets/asset');
  assert.equal(calls[0].options.signal, cancellation.signal);
  assert.equal(calls[0].options.credentials, 'same-origin');
  assert.equal(calls[0].options.cache, 'no-store');
  assert.equal(result.name, 'ação.pdf');
  assert.deepEqual(new Uint8Array(await result.blob.arrayBuffer()), BYTES);
  assert.deepEqual(progress, [{ loaded: BYTES.length, total: BYTES.length }]);
  cancellation.abort();
  await assert.rejects(client.download('/api/assets/asset', { signal: cancellation.signal }), { name: 'AbortError' });
  assert.equal(calls.length, 1);
});

test('HttpClient.upload fourth options bind CSRF and upload to the requested signal and deadline', async t => {
  browser(t);
  const requests = [], scope = new AbortController(), caller = new AbortController();
  const client = new HttpClient({ send: async request => {
    requests.push(request);
    return { ok: true, status: 200, text: JSON.stringify(request.method === 'GET' ? csrf : { id: 'uploaded' }) };
  } }, () => scope.signal);
  const form = new FormData(); form.append('file', new File([BYTES], 'image.png'));
  assert.deepEqual(await client.upload('/api/upload', form, undefined, { signal: caller.signal, timeoutMs: 4321 }), { id: 'uploaded' });
  assert.ok(requests.every(request => request.signal === caller.signal));
  assert.equal(requests[1].body, form);
  assert.equal(requests[1].headers[csrf.header], csrf.token);
  assert.equal(requests[1].timeoutMs, 4321);
  await client.upload('/api/upload', form);
  assert.equal(requests[3].signal, scope.signal);
  assert.equal(Object.hasOwn(requests[3], 'timeoutMs'), false);
});

test('HTTP errors retain stable codes and the server display message for JSON and file reads', async t => {
  browser(t);
  const message = 'This deleted document uses files that are missing. Restore the files before trying again.';
  const payload = JSON.stringify({ error: 'invalid_data', message });
  const client = new HttpClient({
    send: async () => ({ ok: false, status: 400, text: payload }),
    request: async () => new Response(payload, { status: 400 }),
  });
  for (const read of [() => client.get('/api/resource'), () => client.download('/api/resource')])
    await assert.rejects(read(), { name: 'ApiError', code: 'invalid_data', status: 400, message });
  const legacy = new HttpClient({ send: async () => ({ ok: false, status: 409, text: '{"error":"conflict"}' }) });
  await assert.rejects(legacy.get('/api/resource'), { code: 'conflict', message: 'conflict' });
  const malformed = new HttpClient({ send: async () => ({ ok: false, status: 500, text: '<html>Failed</html>' }) });
  await assert.rejects(malformed.get('/api/resource'), { code: 'request_failed', message: 'request_failed' });
});
