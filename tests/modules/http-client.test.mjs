import test from 'node:test';
import assert from 'node:assert/strict';
import { HttpClient, ApiError } from '../../gravewright/modules/static/gravewright_modules/http-client.js';

const csrf = (token) => JSON.stringify({ header: 'X-Test-CSRF', token });

// A transport answering CSRF reads with a numbered token and state changes with `reply`.
function server(reply) {
  const requests = [];
  let issued = 0;
  const client = new HttpClient({ send: async (request) => {
    requests.push(request);
    if (request.method === 'GET') return { ok: true, status: 200, text: csrf(`token-${++issued}`) };
    return reply(request, requests.filter((r) => r.method !== 'GET').length);
  } });
  return { client, requests, gets: () => requests.filter((r) => r.method === 'GET').length };
}
const ok = { ok: true, status: 200, text: JSON.stringify({ value: 'done' }) };
const refused = (code) => ({ ok: false, status: 403, text: JSON.stringify({ error: code }) });

test('state changes of one client share a single CSRF read', async () => {
  const { client, requests, gets } = server(() => ok);
  await client.post('/api/one', { a: 1 });
  await client.patch('/api/two', { b: 2 });
  await client.delete('/api/three');
  assert.equal(gets(), 1);
  for (const request of requests.filter((r) => r.method !== 'GET')) assert.equal(request.headers['X-Test-CSRF'], 'token-1');
});

test('a refused CSRF token is read again and the request repeated once', async () => {
  const { client, requests, gets } = server((request, attempt) => attempt === 1 ? refused('invalid_csrf_token') : ok);
  assert.deepEqual(await client.post('/api/save', { a: 1 }), { value: 'done' });
  assert.equal(gets(), 2);
  assert.deepEqual(requests.filter((r) => r.method === 'POST').map((r) => r.headers['X-Test-CSRF']), ['token-1', 'token-2']);
  await client.post('/api/save', { a: 2 });
  assert.equal(gets(), 2, 'the renewed token is kept');
});

test('a token refused twice fails without a third attempt', async () => {
  const { client, requests } = server(() => refused('invalid_csrf_token'));
  await assert.rejects(client.post('/api/save', {}), (error) => error instanceof ApiError && error.code === 'invalid_csrf_token');
  assert.equal(requests.filter((r) => r.method === 'POST').length, 2);
});

test('other refusals are not repeated', async () => {
  const { client, requests, gets } = server(() => refused('permission_denied'));
  await assert.rejects(client.post('/api/save', {}), (error) => error.code === 'permission_denied');
  assert.equal(requests.filter((r) => r.method === 'POST').length, 1);
  assert.equal(gets(), 1);
});

test('a cancelled CSRF read is not kept for later requests', async () => {
  const cancel = new AbortController();
  const client = new HttpClient({ send: async (request) => {
    if (request.method === 'GET' && request.signal === cancel.signal) { cancel.abort(); throw new DOMException('aborted', 'AbortError'); }
    return request.method === 'GET' ? { ok: true, status: 200, text: csrf('fresh') } : ok;
  } });
  await assert.rejects(client.post('/api/save', {}, { signal: cancel.signal }), { name: 'AbortError' });
  assert.deepEqual(await client.post('/api/save', {}), { value: 'done' });
});
