import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {randomUUID} from 'node:crypto';
import {test} from 'node:test';
import {runInNewContext} from 'node:vm';

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8');
const contentSource = read('../../gravewright/table/static/gravewright_table/content-state.js').replace(/^export /gm, '');
const contentExports = 'contentStates, initialContent, contentReady, afterContentReady, clearContent';
const stateSource = read('../../gravewright/table/static/gravewright_table/realtime-state.js').replace(/^export /gm, '');
const stateExports = 'createCommandRecovery, createProjectionState';
const source = read('../../gravewright/table/static/gravewright_table/realtime.js').replace(/^import .* from .*;$/gm, '');

// A virtual clock: timers only run when a test advances time.
function clock() {
  let now = 0, next = 0;
  const timers = new Map();
  const add = (fn, ms = 0, every = null) => { timers.set(++next, {fn, at: now + ms, every}); return next; };
  return {
    now: () => now,
    setTimeout: (fn, ms) => add(fn, ms),
    setInterval: (fn, ms) => add(fn, ms, Math.max(ms || 0, 1)),
    clearTimeout: handle => timers.delete(handle),
    clearInterval: handle => timers.delete(handle),
    advance(ms) {
      const end = now + ms;
      for (;;) {
        const due = [...timers.entries()].filter(([, timer]) => timer.at <= end)
          .sort((a, b) => a[1].at - b[1].at || a[0] - b[0])[0];
        if (!due) break;
        const [handle, timer] = due;
        now = timer.at;
        if (timer.every === null) timers.delete(handle); else timer.at += timer.every;
        timer.fn();
      }
      now = end;
    },
  };
}

function element() {
  return {children: [], dataset: {}, scrollHeight: 0, scrollTop: 0, clientHeight: 0, content: {firstElementChild: null},
    querySelector: () => null, insertBefore() {}, replaceChildren() {}, append() {}, addEventListener() {}, setAttribute() {}};
}

function table() {
  const signals = {}, sockets = [], events = [], time = clock();
  class Socket {
    static OPEN = 1;
    readyState = 1;
    handlers = {};
    sent = [];
    closed = [];
    constructor() { sockets.push(this); }
    addEventListener(type, handler) { this.handlers[type] = handler; }
    send(data) { this.sent.push(JSON.parse(data)); }
    receive(type, payload = {}) { this.handlers.message({data: JSON.stringify({type, payload})}); }
    close(code = 1000) {
      if (this.readyState === 3) return;
      this.readyState = 3;
      this.closed.push(code);
      this.handlers.close?.({code});
    }
  }
  const root = {...element(), dataset: {tableId: 'table', role: 'gm'}};
  const log = element();
  const window = {addEventListener() {}, dispatchEvent: event => events.push(event)};
  runInNewContext(`const {${contentExports}} = (() => {\n${contentSource}\nreturn {${contentExports}};\n})();
const {${stateExports}} = (() => {\n${stateSource}\nreturn {${stateExports}};\n})();\n${source}`, {
    window,
    document: {getElementById: id => ({'table-workspace': root, 'chat-log': log})[id] || null,
      querySelector: () => null, addEventListener() {}, createElement: element},
    location: {protocol: 'http:', host: 'localhost'},
    WebSocket: Socket, crypto: {randomUUID}, Event, structuredClone,
    Date: {now: time.now},
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options?.detail; } },
    mergePatch: patch => Object.assign(signals, patch), getPath: key => signals[key],
    requestAnimationFrame() {},
    setInterval: time.setInterval, clearInterval: time.clearInterval,
    setTimeout: time.setTimeout, clearTimeout: time.clearTimeout,
  });
  sockets[0].receive('table.joined');
  return {api: window.gravewrightRealtime, sockets, latest: () => sockets.at(-1), clock: time, events, signals};
}

const sent = (socket, type) => socket.sent.filter(message => message.type === type);
// Values created inside the VM have another realm's prototypes; compare their data.
const plain = value => JSON.parse(JSON.stringify(value));
const idle = (socket, clock, ms) => { for (let at = 0; at < ms; at += 5000) { clock.advance(5000); socket.receive('session.ping'); } };

for (const chatMapId of [null, randomUUID()]) {
  test(`scene commands keep their target with chat scope ${chatMapId}`, async () => {
    const {api, latest} = table();
    const socket = latest();
    api.chatScope(chatMapId);
    const target = randomUUID();
    const data = {mapId: target};
    const activation = api.mapCommand('activate', data);
    const command = socket.sent.at(-1);
    assert.equal(command.type, 'maps.command');
    assert.equal(command.payload.data.mapId, target);
    // Rejoining must replay the original target, even if the chat scope changed.
    api.chatScope(randomUUID());
    socket.receive('table.joined');
    const replay = sent(socket, 'maps.command').at(-1);
    assert.deepEqual(replay, command);
    socket.receive('maps.ack', {requestId: command.payload.requestId, result: {mapId: target}});
    assert.equal((await activation).mapId, target);
    assert.deepEqual(data, {mapId: target});
  });
}

test('ping does not resend pending chat or rolls', () => {
  const {api, latest} = table();
  const socket = latest();
  api.say('hello');
  api.roll({expression: '1d20'}).catch(() => {});
  for (let index = 0; index < 3; index++) socket.receive('session.ping');
  assert.equal(sent(socket, 'chat.say').length, 1);
  assert.equal(sent(socket, 'dice.roll').length, 1);
  assert.equal(sent(socket, 'session.pong').length, 3);
});

test('rejoin resends pending chat and roll once with the same requestId', () => {
  const {api, latest, clock} = table();
  const first = latest();
  api.say('hello');
  api.roll({expression: '1d20'}).catch(() => {});
  const [say] = sent(first, 'chat.say'), [roll] = sent(first, 'dice.roll');
  first.close(1006);
  clock.advance(500);
  const second = latest();
  assert.notEqual(second, first);
  second.receive('table.joined');
  assert.deepEqual(sent(second, 'chat.say'), [say]);
  assert.deepEqual(sent(second, 'dice.roll'), [roll]);
});

test('roll_in_progress retries with backoff and stops on ack', async () => {
  const {api, latest, clock} = table();
  const socket = latest();
  const result = api.roll({expression: '1d20'});
  const requestId = sent(socket, 'dice.roll')[0].payload.requestId;
  socket.receive('dice.error', {requestId, code: 'roll_in_progress'});
  clock.advance(999);
  assert.equal(sent(socket, 'dice.roll').length, 1);
  clock.advance(1);
  assert.equal(sent(socket, 'dice.roll').length, 2);
  socket.receive('dice.error', {requestId, code: 'roll_in_progress'});
  clock.advance(1999);
  assert.equal(sent(socket, 'dice.roll').length, 2);
  clock.advance(1);
  assert.equal(sent(socket, 'dice.roll').length, 3);
  socket.receive('dice.ack', {requestId, message: {id: '7', tableId: 'table', html: ''}});
  clock.advance(10000);
  assert.equal(sent(socket, 'dice.roll').length, 3);
  assert.equal((await result).id, '7');
});

const commands = [
  ['resourceCommand', api => api.resourceCommand('tokens', 'move', {id: 'a'}), 'tokens'],
  ['mapCommand', api => api.mapCommand('activate', {mapId: 'm'}), 'maps'],
  ['journalCommand', api => api.journalCommand('update', {id: 'j'}), 'journals'],
  ['moduleCommand', api => api.moduleCommand('audio', 'play', {id: 't'}), 'resources'],
];
for (const [name, call, area] of commands) {
  test(`busy keeps ${name} pending and retries the same payload`, async () => {
    const {api, latest, clock} = table();
    const socket = latest();
    let settled = false;
    const promise = call(api).finally(() => { settled = true; });
    const command = socket.sent.at(-1);
    socket.receive(`${area}.error`, {requestId: command.payload.requestId, code: 'busy', message: 'The table is busy. Retrying.'});
    await Promise.resolve();
    assert.equal(settled, false);
    clock.advance(999);
    assert.equal(sent(socket, command.type).length, 1);
    clock.advance(1);
    const resent = sent(socket, command.type);
    assert.equal(resent.length, 2);
    assert.deepEqual(resent[1], command);
    socket.receive(`${area}.ack`, {requestId: command.payload.requestId, result: {ok: true}});
    assert.deepEqual(plain(await promise), {ok: true});
  });
}

test('non-busy errors still reject immediately', async () => {
  const {api, latest, clock} = table();
  const socket = latest();
  const promise = api.mapCommand('activate', {mapId: 'm'});
  const command = socket.sent.at(-1);
  socket.receive('maps.error', {requestId: command.payload.requestId, code: 'forbidden', message: 'Not allowed.'});
  await assert.rejects(promise, /Not allowed\./);
  idle(socket, clock, 60000);
  assert.equal(sent(socket, 'maps.command').length, 1);
  assert.deepEqual(socket.closed, []);
});

test('command deadline closes once and resubmits on rejoin', async () => {
  const {api, latest, clock} = table();
  const first = latest();
  const promise = api.resourceCommand('tokens', 'move', {id: 'a'});
  const command = first.sent.at(-1);
  for (let index = 0; index < 8; index++) { clock.advance(5000); first.receive('session.ping'); }
  clock.advance(4999);
  assert.deepEqual(first.closed, []);
  clock.advance(1);
  assert.deepEqual(first.closed, [4000]);
  clock.advance(500);
  const second = latest();
  assert.notEqual(second, first);
  second.receive('table.joined');
  assert.deepEqual(sent(second, 'tokens.command'), [command]);
  second.receive('tokens.ack', {requestId: command.payload.requestId, result: {tokens: []}});
  assert.deepEqual(plain(await promise), {tokens: []});
  assert.deepEqual(first.closed, [4000]);
});

test('acknowledged commands never trigger the deadline', async () => {
  const {api, latest, clock} = table();
  const socket = latest();
  const promise = api.mapCommand('activate', {mapId: 'm'});
  socket.receive('maps.ack', {requestId: socket.sent.at(-1).payload.requestId, result: {}});
  await promise;
  idle(socket, clock, 60000);
  assert.deepEqual(socket.closed, []);
});

test('replies that are not acknowledgements never start a deadline', () => {
  const {api, latest, clock} = table();
  const socket = latest();
  api.tableTool('table.search', {requestId: randomUUID(), query: 'door'});
  idle(socket, clock, 60000);
  assert.deepEqual(socket.closed, []);
});

test('access revoked still rejects every pending command and cancels retries', async () => {
  const {api, sockets, latest, clock} = table();
  const socket = latest();
  const map = api.mapCommand('activate', {mapId: 'm'});
  const roll = api.roll({expression: '1d20'});
  const command = sent(socket, 'maps.command')[0];
  socket.receive('maps.error', {requestId: command.payload.requestId, code: 'busy'});
  socket.close(4403);
  await assert.rejects(map);
  await assert.rejects(roll);
  clock.advance(60000);
  assert.equal(sent(socket, 'maps.command').length, 1);
  assert.equal(sockets.length, 1);
});

const detailOf = (events, type) => events.filter(event => event.type === type).map(event => plain(event.detail));

test('tokens.state deltas merge into the last state and dispatch the full payload', () => {
  const {latest, events} = table();
  const socket = latest();
  const rows = [{id: 'a', gridX: 1}, {id: 'b', gridX: 2}, {id: 'c', gridX: 3}];
  socket.receive('tokens.state', {mapId: 'm', tokens: rows});
  socket.receive('tokens.state', {mapId: 'm', delta: true, upserts: {tokens: [{id: 'b', gridX: 9}]},
    removes: {tokens: ['c']}, teleports: [{id: 'b', version: 2}]});
  const expected = {mapId: 'm', tokens: [{id: 'a', gridX: 1}, {id: 'b', gridX: 9}], teleports: [{id: 'b', version: 2}]};
  assert.deepEqual(detailOf(events, 'gravewright:tokens.state').at(-1), expected);
  const sdk = detailOf(events, 'gravewright:api-event').filter(detail => detail.type === 'tokens.state').at(-1);
  // Modules see the complete projection, never the transport delta.
  assert.deepEqual(sdk.payload, {...expected, tableId: 'table'});
  socket.receive('tokens.state', {mapId: 'm', delta: true, unset: ['teleports']});
  assert.equal('teleports' in detailOf(events, 'gravewright:tokens.state').at(-1), false);
});

test('maps.layers deltas apply the server order', () => {
  const {latest, events} = table();
  const socket = latest();
  socket.receive('maps.layers', {sceneId: 's', images: [{id: 'a'}, {id: 'b'}], walls: []});
  socket.receive('maps.layers', {sceneId: 's', delta: true, upserts: {images: [{id: 'c'}]},
    order: {images: ['c', 'b', 'a']}});
  assert.deepEqual(detailOf(events, 'gravewright:map-layers').at(-1).images.map(row => row.id), ['c', 'b', 'a']);
});

test('audio deltas dispatch full catalogs and current playback to native and SDK consumers', () => {
  const {latest, events} = table();
  const socket = latest();
  const initial = {sceneId: 's', tracks: [{id: 'a', name: 'First'}, {id: 'b', name: 'Second'}],
    playlists: [{id: 'p', tracks: [{soundId: 'a'}]}], spatialSounds: [],
    serverTime: 100, score: {state: 'stopped', serverTime: 100}, playback: {ambient: []}};
  socket.receive('resources.state', {module: 'audio', sceneId: 's', state: initial});
  socket.receive('resources.state', {module: 'audio', sceneId: 's', state: {
    sceneId: 's', delta: true, serverTime: 101, score: {state: 'stopped', serverTime: 101},
    upserts: {tracks: [{id: 'b', name: 'Renamed'}]}, removes: {tracks: ['a'], playlists: ['p']},
  }});
  const expected = {module: 'audio', sceneId: 's', state: {...initial, tracks: [{id: 'b', name: 'Renamed'}],
    playlists: [], serverTime: 101, score: {state: 'stopped', serverTime: 101}}};
  assert.deepEqual(detailOf(events, 'gravewright:resources').at(-1), expected);
  const sdk = detailOf(events, 'gravewright:api-event').filter(detail => detail.type === 'resources.state').at(-1);
  assert.deepEqual(sdk.payload, {...expected, tableId: 'table'});
});

test('audio deltas isolate catalogs by scene and from mutable event consumers', () => {
  const {createProjectionState} = runInNewContext(`${stateSource}\n({createProjectionState})`, {structuredClone});
  const state = createProjectionState();
  const input = {module: 'audio', sceneId: 'a', state: {sceneId: 'a', tracks: [{id: 'one', name: 'Original'}]}};
  const first = state.receive('resources.state', input);
  input.state.tracks[0].name = 'Mutated input';
  first.state.tracks.push({id: 'untrusted'});
  state.receive('resources.state', {module: 'items', sceneId: 'a', state: {tracks: [{id: 'wrong module'}]}});
  state.receive('resources.state', {module: 'audio', sceneId: 'b', state: {sceneId: 'b', tracks: [{id: 'two'}]}});
  const second = state.receive('resources.state', {module: 'audio', sceneId: 'a', state: {
    delta: true, sceneId: 'a', serverTime: 101,
  }});
  assert.deepEqual(plain(second.state.tracks), [{id: 'one', name: 'Original'}]);
  second.state.tracks[0].name = 'Mutated retained row';
  const third = state.receive('resources.state', {module: 'audio', sceneId: 'a', state: {
    delta: true, sceneId: 'a', serverTime: 102,
  }});
  assert.deepEqual(plain(third.state.tracks), [{id: 'one', name: 'Original'}]);
  state.receive('resources.state', {module: 'audio', sceneId: 'a', state: {}, unavailable: true});
  assert.equal(state.receive('resources.state', {module: 'audio', sceneId: 'a', state: {delta: true, sceneId: 'a'}}), null);
  state.clear();
  assert.equal(state.receive('resources.state', {module: 'audio', sceneId: 'b', state: {delta: true, sceneId: 'b'}}), null);
});

test('an audio delta without its base resubscribes with the selected preview listener', () => {
  const {api, latest, events} = table();
  api.subscribeModule('audio', 's', 'preview-token');
  const socket = latest();
  socket.receive('resources.state', {module: 'audio', sceneId: 's', state: {delta: true, sceneId: 's', serverTime: 101}});
  assert.deepEqual(plain(sent(socket, 'resources.sync').at(-1).payload), {
    tableId: 'table', module: 'audio', sceneId: 's', previewTokenId: 'preview-token',
  });
  assert.equal(detailOf(events, 'gravewright:resources').length, 0);
});

test('changing the audio scene or preview discards its old delta base', () => {
  const {api, latest, events} = table();
  const socket = latest();
  const full = sceneId => ({module: 'audio', sceneId, state: {sceneId, tracks: [{id: 'sound'}]}});
  const delta = sceneId => ({module: 'audio', sceneId, state: {sceneId, delta: true, serverTime: 101}});
  api.subscribeModule('audio', 'a', 'first');
  socket.receive('resources.state', full('a'));
  // Resubscribing an unchanged selection keeps its current base.
  api.subscribeModule('audio', 'a', 'first');
  socket.receive('resources.state', delta('a'));
  assert.equal(detailOf(events, 'gravewright:resources').length, 2);
  api.subscribeModule('audio', 'a', 'second');
  socket.receive('resources.state', delta('a'));
  assert.equal(detailOf(events, 'gravewright:resources').length, 2);
  assert.equal(sent(socket, 'resources.sync').at(-1).payload.previewTokenId, 'second');
  socket.receive('resources.state', full('a'));
  api.subscribeModule('audio', 'b', 'third');
  socket.receive('resources.state', delta('a'));
  assert.deepEqual(plain(sent(socket, 'resources.sync').at(-1).payload), {
    tableId: 'table', module: 'audio', sceneId: 'b', previewTokenId: 'third',
  });
  assert.equal(detailOf(events, 'gravewright:resources').length, 3);
  socket.receive('resources.state', full('b'));
  socket.receive('resources.state', delta('b'));
  assert.equal(detailOf(events, 'gravewright:resources').length, 5);
});

test('mutable projection inputs and delivered branches cannot corrupt later deltas', () => {
  const {createProjectionState} = runInNewContext(`${stateSource}\n({createProjectionState})`, {structuredClone});
  const state = createProjectionState();
  const initial = {sceneId: 's', images: [{id: 'a', art: {color: 'red'}}, {id: 'b', art: {color: 'blue'}}],
    walls: [{id: 'wall', channels: {movement: true}}], camera: {zoom: 1}};
  const first = state.receive('maps.layers', initial);
  initial.images[0].art.color = 'external input mutation';
  first.walls[0].channels.movement = false;
  first.walls.push({id: 'external wall'});
  const patch = {sceneId: 's', delta: true, upserts: {images: [{id: 'b', art: {color: 'green'}}]},
    marker: {name: 'server marker'}, unset: ['camera']};
  const second = state.receive('maps.layers', patch);
  assert.deepEqual(plain(second), {sceneId: 's',
    images: [{id: 'a', art: {color: 'red'}}, {id: 'b', art: {color: 'green'}}],
    walls: [{id: 'wall', channels: {movement: true}}], marker: {name: 'server marker'}});

  // All branches remain ordinary mutable data for native and SDK consumers.
  patch.upserts.images[0].art.color = 'mutated upsert';
  patch.marker.name = 'mutated metadata';
  second.images[0].art.color = 'mutated retained row';
  second.images.push({id: 'external image'});
  second.walls[0].channels.movement = false;
  second.walls.push({id: 'another external wall'});
  const third = state.receive('maps.layers', {sceneId: 's', delta: true,
    upserts: {images: [{id: 'c', art: {color: 'yellow'}}]}, removes: {images: ['a']},
    order: {images: ['c', 'b']}});
  assert.deepEqual(plain(third), {sceneId: 's',
    images: [{id: 'c', art: {color: 'yellow'}}, {id: 'b', art: {color: 'green'}}],
    walls: [{id: 'wall', channels: {movement: true}}], marker: {name: 'server marker'}});
});

test('applying a delta preserves previously delivered snapshots', () => {
  const {createProjectionState} = runInNewContext(`${stateSource}\n({createProjectionState})`, {structuredClone});
  const state = createProjectionState();
  const original = {mapId: 'm', tokens: [{id: 'a', gridX: 1}, {id: 'b', gridX: 2}],
    teleports: [{id: 'b', version: 2}]};
  const first = state.receive('tokens.state', structuredClone(original));
  const second = state.receive('tokens.state', {mapId: 'm', delta: true,
    upserts: {tokens: [{id: 'b', gridX: 8}]}, removes: {tokens: ['a']}, unset: ['teleports']});
  assert.deepEqual(plain(first), original);
  assert.deepEqual(plain(second), {mapId: 'm', tokens: [{id: 'b', gridX: 8}]});
  second.tokens[0].gridX = 99;
  assert.deepEqual(plain(state.receive('tokens.state', {mapId: 'm', delta: true})),
    {mapId: 'm', tokens: [{id: 'b', gridX: 8}]});
});

test('a delta without its base state requests a full projection', () => {
  const {latest, events} = table();
  const socket = latest();
  socket.receive('tokens.state', {mapId: 'm', delta: true, upserts: {tokens: [{id: 'a'}]}});
  socket.receive('maps.layers', {sceneId: 's', delta: true, upserts: {images: [{id: 'a'}]}});
  assert.deepEqual(plain(sent(socket, 'tokens.sync').at(-1).payload), {tableId: 'table', mapId: 'm'});
  assert.deepEqual(plain(sent(socket, 'maps.layers').at(-1).payload), {tableId: 'table', mapId: 's'});
  assert.equal(detailOf(events, 'gravewright:tokens.state').length, 0);
});

test('rejoining discards cached projections', () => {
  const {latest, clock} = table();
  const first = latest();
  first.receive('tokens.state', {mapId: 'm', tokens: [{id: 'a'}]});
  first.close(1006);
  clock.advance(500);
  const second = latest();
  second.receive('table.joined');
  second.receive('tokens.state', {mapId: 'm', delta: true, upserts: {tokens: [{id: 'b'}]}});
  assert.equal(sent(second, 'tokens.sync').at(-1).payload.mapId, 'm');
});
