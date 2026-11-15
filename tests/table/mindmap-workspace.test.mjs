import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import {runInNewContext} from 'node:vm';

const source = readFileSync(new URL('../../gravewright/table/static/gravewright_table/mindmap-workspace.js', import.meta.url), 'utf8')
  .replace(/^import .* from .*;$/gm, '');

// Mounts the workspace with a virtual clock and counts mind map reads.
function workspace() {
  const listeners = new Map(), timers = new Map();
  let now = 0, next = 0, reads = 0;
  const node = () => ({dataset: {}, hidden: false, addEventListener() {}, setAttribute() {}, append() {}});
  const toggle = node();
  const root = {...node(), dataset: {tableId: 'table-1', management: 'false'}, querySelector: () => toggle};
  const window = {
    addEventListener(type, handler) { listeners.set(type, [...(listeners.get(type) || []), handler]); },
    gravewrightRealtime: {subscribeModule() {}},
  };
  const context = {
    window, crypto: {randomUUID: () => 'id'},
    document: {querySelector: selector => selector === '#table-workspace' ? root : null, createElement: node},
    AbortController, Promise, Set, Array,
    setTimeout: (fn, ms) => { timers.set(++next, {fn, at: now + ms}); return next; },
    clearTimeout: handle => timers.delete(handle),
    gravewright: {forTable: () => ({mindmaps: {state: async () => { reads++; return {mindmaps: [], canManage: true}; }}})},
    createTranslator: () => ({t: key => key, onChange: () => () => {}}),
    afterContentReady() {}, mountModal() {},
    mountMindmaps: () => ({update() {}, open() {}, destroy() {}}),
  };
  runInNewContext(source, context);
  return {
    frame(type) { for (const handler of listeners.get('gravewright:api-event') || []) handler({detail: {type, payload: {}}}); },
    async advance(ms) {
      now += ms;
      for (const [handle, timer] of [...timers]) if (timer.at <= now) { timers.delete(handle); timer.fn(); }
      await new Promise(resolve => setImmediate(resolve));
    },
    get reads() { return reads; },
  };
}

test('pointer, drag, camera and liveness frames do not reload mind maps', async () => {
  const table = workspace();
  for (const type of ['maps.cursor', 'token.drag', 'scene.viewport.ready', 'scene.gm_prefetch.hint',
    'session.ping', 'table.presence', 'maps.ping']) {
    table.frame(type);
    await table.advance(200);
  }
  assert.equal(table.reads, 0);
});

test('frames that carry table state still reload mind maps once per burst', async () => {
  const table = workspace();
  table.frame('maps.cursor');
  table.frame('api.changed');
  table.frame('maps.cursor');
  table.frame('tokens.state');
  await table.advance(200);
  assert.equal(table.reads, 1);
  table.frame('actors.state');
  await table.advance(200);
  assert.equal(table.reads, 2);
});
