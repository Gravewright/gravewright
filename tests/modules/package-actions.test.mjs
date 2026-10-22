import test from 'node:test';
import assert from 'node:assert/strict';
import { packageAction, waitForRestartPoll } from '../../gravewright/modules/static/gravewright_modules/package-actions.js';

test('restart polling rejects an already aborted signal without scheduling a timer', async t => {
  const controller = new AbortController(), reason = new Error('Package view disposed');
  controller.abort(reason);
  const schedule = t.mock.method(globalThis, 'setTimeout');
  await assert.rejects(waitForRestartPoll(controller.signal), error => error === reason);
  assert.equal(schedule.mock.callCount(), 0);
});

test('aborting a pending restart poll clears its timer and removes its listener', async t => {
  t.mock.timers.enable({apis: ['setTimeout']});
  const controller = new AbortController(), reason = new Error('Package view disposed');
  const schedule = t.mock.method(globalThis, 'setTimeout');
  const clear = t.mock.method(globalThis, 'clearTimeout');
  const remove = t.mock.method(controller.signal, 'removeEventListener');
  const waiting = waitForRestartPoll(controller.signal);
  const rejected = assert.rejects(waiting, error => error === reason);
  assert.equal(schedule.mock.callCount(), 1);
  assert.equal(schedule.mock.calls[0].arguments[1], 2000);
  controller.abort(reason);
  await rejected;
  assert.equal(clear.mock.callCount(), 1);
  assert.equal(clear.mock.calls[0].arguments[0], schedule.mock.calls[0].result);
  assert.equal(remove.mock.callCount(), 1);
  assert.equal(remove.mock.calls[0].arguments[0], 'abort');
  t.mock.timers.tick(2000);
});

test('a completed restart pause lasts two seconds and stops listening for aborts', async t => {
  t.mock.timers.enable({apis: ['setTimeout']});
  const controller = new AbortController();
  const remove = t.mock.method(controller.signal, 'removeEventListener');
  const clear = t.mock.method(globalThis, 'clearTimeout');
  let completed = false;
  const waiting = waitForRestartPoll(controller.signal).then(() => { completed = true; });
  t.mock.timers.tick(1999);
  await Promise.resolve();
  assert.equal(completed, false);
  t.mock.timers.tick(1);
  await waiting;
  assert.equal(completed, true);
  assert.equal(remove.mock.callCount(), 1);
  controller.abort();
  assert.equal(clear.mock.callCount(), 0);
});

test('restart pauses also work for callers without a scope signal', async t => {
  t.mock.timers.enable({apis: ['setTimeout']});
  const waiting = waitForRestartPoll();
  t.mock.timers.tick(2000);
  await waiting;
});

test('an update stops after abort during a failed restart status request', async t => {
  t.mock.timers.enable({apis: ['setTimeout']});
  const controller = new AbortController(), reason = new Error('Package view disposed');
  const posts = [], gets = [];
  const http = {
    scopeSignal: () => controller.signal,
    async post(...args) {
      posts.push(args);
      return {restartRequired: true};
    },
    async get(path) {
      gets.push(path);
      controller.abort(reason);
      throw new Error('Server unavailable during restart');
    },
  };
  const action = packageAction(http, {id: 'review.tools', version: '1.0.0'}, 'update');
  const rejected = assert.rejects(action, error => error === reason);
  await Promise.resolve();
  t.mock.timers.tick(2000);
  await rejected;
  t.mock.timers.tick(2000);
  assert.deepEqual(gets, ['/api/admin/status']);
  assert.deepEqual(posts, [['/api/module-packages/update',
    {id: 'review.tools', version: '1.0.0'}, {timeoutMs: null}]]);
});
