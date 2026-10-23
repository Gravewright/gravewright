import test from 'node:test';
import assert from 'node:assert/strict';
import { setImmediate as nextTurn } from 'node:timers/promises';
import { managementTransport } from '../../gravewright/web/static/gravewright_web/campaign-manager/transport.js';

const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};

async function until(predicate) {
  for (let attempt = 0; attempt < 20; attempt++) {
    if (predicate()) return;
    await nextTurn();
  }
  assert.ok(predicate(), 'the expected asynchronous boundary was reached');
}

function fixture(t, overrides = {}) {
  const calls = { state: [], execute: [], authorize: [], publish: [], revoked: [], report: [], roll: [], navigation: [] };
  const state = overrides.state || (async domain => ({ domain, version: 1 }));
  const api = Object.fromEntries(['journals', 'actors', 'maps', 'items', 'cards', 'audio', 'combat'].map(domain => [domain, {
    state: async (payload, options) => {
      calls.state.push({ domain, payload, options });
      return state(domain, payload, options);
    },
  }]));
  for (const method of ['navigate', 'activate']) api.maps[method] = async (...args) => calls.navigation.push({ method, args });
  api.dice = { roll: async (...args) => { calls.roll.push(args); return { id: 'native-chat-roll' }; } };
  const transport = managementTransport({
    api,
    authorize: async signal => {
      calls.authorize.push(signal);
      return overrides.authorize ? overrides.authorize(signal) : { memberRole: 'gm' };
    },
    execute: async (...args) => {
      calls.execute.push(args);
      return overrides.execute ? overrides.execute(...args) : { id: 'saved', version: 2 };
    },
    publish: (...args) => calls.publish.push(args),
    revoked: error => calls.revoked.push(error),
    report: error => calls.report.push(error),
  });
  t.after(() => transport.close());
  return { transport, calls, api };
}

test('revoked GM authorization clears cached state and blocks mutations and dice', async t => {
  for (const properties of [{ status: 401 }, { status: 403 }, { status: 404 }, { code: 'permission_denied' }]) {
    await t.test(JSON.stringify(properties), async st => {
      const denied = Object.assign(new Error('Current GM membership required.'), properties);
      const { transport, calls } = fixture(st, { authorize: async () => { throw denied; } });
      await transport.read('journals');
      assert.equal(transport.states.size, 1);
      await assert.rejects(transport.journalCommand('save', { id: 'secret', version: 1 }), error => error === denied);
      assert.equal(transport.signal.aborted, true);
      assert.equal(transport.states.size, 0);
      assert.deepEqual(calls.revoked, [denied]);
      assert.equal(calls.execute.length, 0);
      await assert.rejects(transport.roll({ expression: '1d6' }), { name: 'AbortError' });
      assert.equal(calls.roll.length, 0);
      assert.equal(calls.authorize.length, 1);
    });
  }
});

test('concurrent commands share authorization and retain their explicit retry options', async t => {
  const authorization = deferred();
  const { transport, calls, api } = fixture(t, { authorize: () => authorization.promise });
  const one = transport.journalCommand('save', { id: 'journal', version: 4 }, { requestId: 'journal-retry' });
  const two = transport.resourceCommand('actors', 'update', { id: 'actor', version: 9 }, { requestId: 'actor-retry' });
  await until(() => calls.authorize.length === 1);
  assert.equal(calls.execute.length, 0);
  authorization.resolve({ memberRole: 'gm' });
  assert.deepEqual(await Promise.all([one, two]), [{ id: 'saved', version: 2 }, { id: 'saved', version: 2 }]);
  assert.equal(calls.authorize.length, 1);
  assert.deepEqual(calls.execute.map(args => args.slice(1, 4)), [
    ['journals', 'save', { id: 'journal', version: 4 }], ['actors', 'update', { id: 'actor', version: 9 }],
  ]);
  assert.ok(calls.execute.every(args => args[0] === api && args[4].signal === transport.signal));
  assert.deepEqual(calls.execute.map(args => args[4].requestId), ['journal-retry', 'actor-retry']);
  assert.equal(calls.state.length, 2);
});

test('closing during authorization prevents the queued command from executing', async t => {
  const authorization = deferred();
  const { transport, calls } = fixture(t, { authorize: () => authorization.promise });
  const operation = transport.journalCommand('delete', { id: 'journal', version: 1 });
  const rejected = assert.rejects(operation, { name: 'AbortError' });
  await until(() => calls.authorize.length === 1);
  transport.close();
  authorization.resolve({ memberRole: 'gm' });
  await rejected;
  assert.equal(calls.execute.length, 0);
  assert.equal(calls.state.length, 0);
  assert.equal(calls.publish.length, 0);
});

test('closing while a mutation finishes prevents its follow-up read and notifications', async t => {
  const mutation = deferred();
  const { transport, calls } = fixture(t, { execute: () => mutation.promise });
  const operation = transport.resourceCommand('items', 'update', { id: 'item', version: 3 });
  const rejected = assert.rejects(operation, { name: 'AbortError' });
  await until(() => calls.execute.length === 1);
  transport.close();
  mutation.resolve({ id: 'item', version: 4 });
  await rejected;
  assert.equal(calls.state.length, 0);
  assert.equal(calls.publish.length, 0);
  assert.equal(calls.report.length, 0);
  assert.equal(transport.states.size, 0);
});

test('domain reads coalesce and unchanged state does not emit duplicate updates', async t => {
  const response = deferred();
  const { transport, calls } = fixture(t, { state: () => response.promise });
  const first = transport.read('actors'), second = transport.read('actors');
  assert.equal(first, second);
  assert.equal(calls.state.length, 1);
  const value = { actors: [{ id: 'hero', version: 7 }] };
  response.resolve(value);
  assert.equal(await first, value);
  assert.equal(await second, value);
  assert.equal(transport.states.get('actors'), value);
  assert.equal(calls.publish.length, 1);
  await transport.read('actors');
  assert.equal(calls.state.length, 2);
  assert.equal(calls.publish.length, 1);
});

test('a mutation invalidates an older in-flight read before publishing or returning state', async t => {
  const oldRead = deferred(), freshRead = deferred(), mutation = deferred();
  let reads = 0;
  const { transport, calls } = fixture(t, {
    state: () => ++reads === 1 ? oldRead.promise : freshRead.promise,
    execute: () => mutation.promise,
  });
  const subscription = transport.journalsSubscribe();
  const operation = transport.journalCommand('save', { id: 'journal', version: 1 });
  await until(() => calls.execute.length === 1);
  mutation.resolve({ id: 'journal', version: 2 });
  await nextTurn();
  oldRead.resolve({ journals: [{ id: 'journal', version: 1 }] });
  await until(() => reads === 2);
  assert.equal(calls.publish.length, 0, 'the response from before the save must not reach editors');
  assert.equal(transport.states.has('journals'), false);
  const fresh = { journals: [{ id: 'journal', version: 2 }] };
  freshRead.resolve(fresh);
  await Promise.all([subscription, operation]);
  assert.deepEqual(calls.publish, [['journals', fresh, { sceneId: null }]]);
  assert.equal(transport.states.get('journals'), fresh);
  assert.equal(calls.execute.length, 1);
});

test('changing scene subscriptions refreshes locally without navigating or activating the table', async t => {
  const oldRead = deferred(), newRead = deferred();
  const { transport, calls } = fixture(t, {
    state: (_domain, payload) => payload.sceneId === 'scene-a' ? oldRead.promise : newRead.promise,
  });
  const first = transport.subscribeModule('maps', 'scene-a');
  const second = transport.subscribeModule('maps', 'scene-b', 'preview-token');
  assert.equal(calls.state.length, 1);
  oldRead.resolve({ sceneId: 'scene-a' });
  await until(() => calls.state.length === 2);
  assert.equal(calls.publish.length, 0);
  assert.deepEqual(calls.state.map(call => call.payload), [
    { sceneId: 'scene-a' }, { sceneId: 'scene-b', previewTokenId: 'preview-token' },
  ]);
  const value = { sceneId: 'scene-b' };
  newRead.resolve(value);
  await Promise.all([first, second]);
  assert.deepEqual(calls.publish, [['maps', value, { sceneId: 'scene-b', previewTokenId: 'preview-token' }]]);
  assert.deepEqual(calls.navigation, []);
  assert.equal(calls.execute.length, 0);
  assert.ok(calls.state.every(call => call.options.signal === transport.signal));
});

test('an identical native cards payload still publishes when its scene or preview context changes', async t => {
  const value = { decks: [{ id: 'deck', name: 'Synthetic deck', version: 1 }], hand: [], cards: [], isGM: true };
  const { transport, calls } = fixture(t, { state: async () => structuredClone(value) });
  await transport.subscribeModule('cards', 'scene-a');
  await transport.subscribeModule('cards', 'scene-b');
  await transport.subscribeModule('cards', 'scene-b', 'preview-token');
  await transport.subscribeModule('cards', 'scene-b', 'preview-token');
  assert.deepEqual(calls.publish, [
    ['cards', value, { sceneId: 'scene-a' }],
    ['cards', value, { sceneId: 'scene-b' }],
    ['cards', value, { sceneId: 'scene-b', previewTokenId: 'preview-token' }],
  ]);
  assert.equal(calls.state.length, 4);
  assert.deepEqual(calls.navigation, []);
  assert.equal(calls.execute.length, 0);
});

test('closing a pending subscription aborts it without publishing state or reporting an error', async t => {
  const response = deferred();
  const { transport, calls } = fixture(t, { state: () => response.promise });
  const subscription = transport.actorsSubscribe();
  transport.close();
  transport.close();
  response.resolve({ actors: [{ id: 'late-secret' }] });
  await subscription;
  assert.equal(calls.state[0].options.signal.aborted, true);
  assert.deepEqual(calls.publish, []);
  assert.deepEqual(calls.report, []);
  assert.equal(transport.states.size, 0);
});

test('refresh reports temporary domain failures without revoking access and rechecks authorization', async t => {
  let fail = false, revoked = false;
  const networkError = Object.assign(new Error('Temporary request failure.'), { status: 503 });
  const permissionError = Object.assign(new Error('No longer a GM.'), { status: 403 });
  const { transport, calls } = fixture(t, {
    state: async () => { if (fail) throw networkError; return { journals: [] }; },
    authorize: async () => { if (revoked) throw permissionError; return { memberRole: 'gm' }; },
  });
  await transport.journalsSubscribe();
  fail = true;
  await transport.refresh();
  assert.deepEqual(calls.report, [networkError]);
  assert.equal(transport.signal.aborted, false);
  assert.equal(calls.publish.length, 1);
  revoked = true;
  await assert.rejects(transport.refresh(), error => error === permissionError);
  assert.deepEqual(calls.revoked, [permissionError]);
  assert.equal(calls.authorize.length, 2);
  assert.equal(calls.state.length, 2);
  assert.equal(transport.states.size, 0);
});

test('native rolls keep the supplied request UUID and scene context after checking GM access', async t => {
  const { transport, calls } = fixture(t);
  const payload = { expression: '2d6 + 3', visibility: 'gm', label: 'Authored label' };
  const result = await transport.roll(payload, { requestId: 'same-logical-roll', mapId: 'encounter-scene' });
  assert.deepEqual(result, { id: 'native-chat-roll' });
  assert.equal(calls.authorize.length, 1);
  assert.deepEqual(calls.roll, [[payload.expression, { ...payload, sceneId: 'encounter-scene' },
    { requestId: 'same-logical-roll', signal: transport.signal }]]);
  assert.equal(calls.execute.length, 0);
  assert.equal(calls.state.length, 0);
});
