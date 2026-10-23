import test from 'node:test';
import assert from 'node:assert/strict';
import { createGlobalApi } from '../../gravewright/modules/static/gravewright_modules/global-api.js';
import { Lifetime } from '../../gravewright/modules/static/gravewright_modules/lifetime.js';
import { managementTransport } from '../../gravewright/web/static/gravewright_web/campaign-manager/transport.js';
import { lineDiff } from '../../gravewright/web/static/gravewright_web/campaign-manager/line-diff.js';

test('preparation adapters escape identifiers and send one request UUID per command', async () => {
  const calls = [];
  const http = {
    get: async (path, options) => { calls.push({ method: 'GET', path, options }); return {}; },
    post: async (path, body, options) => { calls.push({ method: 'POST', path, body, options }); return {}; },
  };
  const api = createGlobalApi(http, new Lifetime());
  await api.campaigns.preparation('a/b');
  await api.campaigns.prepare('a/b', 'session-create', { title: 'Session' }, 'request-1');
  await api.campaigns.references('a/b', 'journal', 'x&y=1');
  await api.campaigns.viewAs('a/b', 'user/1');
  await api.campaigns.journalHistory('a/b', 'j/1');
  await api.campaigns.journalRevision('a/b', 'r/1');
  await api.campaigns.journalTrash('a/b');
  assert.deepEqual(calls.map(call => call.path), [
    '/api/containers/a%2Fb/preparation',
    '/api/containers/a%2Fb/preparation',
    '/api/containers/a%2Fb/references?type=journal&id=x%26y%3D1',
    '/api/containers/a%2Fb/view-as/user%2F1',
    '/api/containers/a%2Fb/journal-history/j%2F1',
    '/api/containers/a%2Fb/journal-revisions/r%2F1',
    '/api/containers/a%2Fb/journal-trash',
  ]);
  assert.deepEqual(calls[1].body, { action: 'session-create', payload: { title: 'Session' }, request_id: 'request-1' });
});

test('manager search uses the authorized HTTP API instead of a table socket', async t => {
  const searches = [];
  let authorized = 0;
  const transport = managementTransport({
    api: { table: { search: async (query, options) => { searches.push({ query, options }); return [{ type: 'journal', id: '1', title: 'Synthetic' }]; } } },
    execute: async () => ({}), publish: () => {}, revoked: () => {},
    authorize: async () => { authorized++; return { memberRole: 'gm' }; },
  });
  t.after(() => transport.close());
  assert.deepEqual(await transport.search('Synth'), [{ type: 'journal', id: '1', title: 'Synthetic' }]);
  assert.equal(authorized, 1);
  assert.equal(searches[0].query, 'Synth');
  assert.equal(searches[0].options.signal, transport.signal);
  assert.equal(typeof transport.tableTool, 'undefined');
});

test('line comparison marks removed, added and unchanged lines in order', () => {
  assert.deepEqual(lineDiff(['# Title', 'Old', 'Same'], ['# Title', 'Same', 'New']), [
    [' ', '# Title'], ['-', 'Old'], [' ', 'Same'], ['+', 'New'],
  ]);
  assert.deepEqual(lineDiff([], ['Only new']), [['+', 'Only new']]);
  assert.deepEqual(lineDiff(['Only old'], []), [['-', 'Only old']]);
  assert.equal(lineDiff(Array(2500).fill('x'), []).length, 2000);
});
