import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {randomUUID} from 'node:crypto';
import {test} from 'node:test';
import {runInNewContext} from 'node:vm';

const source = readFileSync(new URL('../../gravewright/table/static/gravewright_table/realtime.js', import.meta.url), 'utf8')
  .replace(/^import .* from .*;$/m, '');

function table() {
  const signals = {}, sockets = [];
  class Socket {
    static OPEN = 1;
    readyState = 1;
    handlers = {};
    sent = [];
    constructor() { sockets.push(this); }
    addEventListener(type, handler) { this.handlers[type] = handler; }
    send(data) { this.sent.push(JSON.parse(data)); }
    receive(type, payload = {}) { this.handlers.message({data: JSON.stringify({type, payload})}); }
  }
  const root = {dataset: {tableId: 'table', role: 'gm'}, querySelector: () => null};
  const window = {addEventListener() {}, dispatchEvent() {}};
  runInNewContext(source, {
    window,
    document: {getElementById: id => id === 'table-workspace' ? root : null, querySelector: () => null, addEventListener() {}},
    location: {protocol: 'http:', host: 'localhost'},
    WebSocket: Socket, crypto: {randomUUID}, Event,
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options?.detail; } },
    mergePatch: patch => Object.assign(signals, patch), getPath: key => signals[key],
    setInterval() {}, clearInterval() {}, setTimeout() {}, clearTimeout() {},
  });
  const socket = sockets[0];
  socket.receive('table.joined');
  return {api: window.gravewrightRealtime, socket};
}

for (const chatMapId of [null, randomUUID()]) {
  test(`scene commands keep their target with chat scope ${chatMapId}`, async () => {
    const {api, socket} = table();
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
    const replay = socket.sent.filter(message => message.type === 'maps.command').at(-1);
    assert.deepEqual(replay, command);
    socket.receive('maps.ack', {requestId: command.payload.requestId, result: {mapId: target}});
    assert.equal((await activation).mapId, target);
    assert.deepEqual(data, {mapId: target});
  });
}
