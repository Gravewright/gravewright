import test from 'node:test';
import assert from 'node:assert/strict';
import { createDomainApi, createEvents, executeNative } from '../../gravewright/modules/static/gravewright_modules/domain-api.js';
import { Lifetime } from '../../gravewright/modules/static/gravewright_modules/lifetime.js';
import { BrowserBridge } from '../../gravewright/modules/static/gravewright_modules/browser-bridge.js';

// BrowserBridge subscriptions need only an EventTarget, not a renderer.
globalThis.window = new EventTarget();

test('explicit domain methods share one transport and preserve request options', async () => {
  const calls = [];
  const api = createDomainApi(async (...args) => { calls.push(args); return { id:'created' }; });
  const options = { requestId:'retry-id', signal:new AbortController().signal };
  await api.cards.draw({ deck_instance_id:'deck', count:1 }, options);
  await api.chat.send({ text:'Hello' }, options);
  await api.dice.roll('2d6+3', { visibility:'gm' }, options);
  await executeNative(api, 'items', 'folder-create', {name:'Equipment'}, options);
  assert.deepEqual(calls.map(c => c.slice(0,3)), [
    ['cards','draw',{deck_instance_id:'deck',count:1}],
    ['chat','send',{text:'Hello'}], ['dice','roll',{visibility:'gm',expression:'2d6+3'}],
    ['items','createFolder',{name:'Equipment'}],
  ]);
  assert.ok(calls.every(c => c[3] === options));
  assert.ok(Object.isFrozen(api.actors));
  assert.equal(api.actors.command, undefined);
  await assert.rejects(executeNative(api,'items','executeSql',{}), {code:'unavailable'});
});

test('actor convenience update and combat turns retain optimistic versions', async () => {
  const calls = [];
  const api = createDomainApi(async (domain, method, payload) => {
    calls.push([domain,method,payload]);
    if (domain === 'actors' && method === 'state') return {actors:[{id:'hero',version:7}]};
    if (domain === 'combat' && method === 'state') return {version:11};
    return {};
  });
  await api.actors.update('hero',{name:'Renamed'});
  await api.combat.nextTurn();
  assert.deepEqual(calls[1],['actors','update',{id:'hero',name:'Renamed',version:7}]);
  assert.deepEqual(calls[3],['combat','nextTurn',{version:11}]);
  await assert.rejects(api.actors.get('private'),{code:'not_found'});
});

test('event subscriptions filter table, scene and resource and release on disposal', async () => {
  const target = new EventTarget(), life = new Lifetime(), values = [];
  const events = createEvents(target, life, {tableId:'table',sceneId:'scene'});
  const off = events.on('combat.changed', payload => values.push(payload));
  const emit = payload => target.dispatchEvent(new CustomEvent('gravewright:api-event', {detail:{type:'resources.state',payload}}));
  emit({tableId:'other',sceneId:'scene',module:'combat'});
  emit({tableId:'table',sceneId:'other',module:'combat'});
  emit({tableId:'table',sceneId:'scene',module:'cards'});
  emit({tableId:'table',sceneId:'scene',module:'combat'});
  assert.equal(values.length,1);
  off(); off();
  emit({tableId:'table',sceneId:'scene',module:'combat'});
  assert.equal(values.length,1);
  events.on('combat.changed', payload => values.push(payload));
  await life.close();
  emit({tableId:'table',sceneId:'scene',module:'combat'});
  assert.equal(values.length,1);
  assert.throws(() => events.on('actors.changed',()=>{}),{code:'stale_context'});
});

test('module API retains its own identity during interleaved calls and cancels stale mounts', async () => {
  const bridge = new BrowserBridge('table'), calls = [], first = new Lifetime(), second = new Lifetime();
  bridge.ensure = async () => {};
  bridge.request = async (path,payload,signal) => { calls.push({path,payload,signal}); return {id:payload.mountId}; };
  const a = bridge.api({moduleId:'one',tableId:'table',mountId:'a',moduleSetRevision:'1',sceneId:'scene-a'}, first);
  const b = bridge.api({moduleId:'two',tableId:'table',mountId:'b',moduleSetRevision:'1',sceneId:'scene-b'}, second);
  await Promise.all([a.chat.send({text:'one'}),b.chat.send({text:'two'})]);
  assert.equal(calls[0].payload.mountId,'a');
  assert.equal(calls[1].payload.mountId,'b');
  assert.equal(calls[0].payload.sceneId,'scene-a');
  assert.match(calls[1].path,/modules\/two\/api$/);
  await first.close();
  await assert.rejects(a.items.state(),{code:'stale_context'});
  await b.items.state();
  const controller = new AbortController(); controller.abort();
  await assert.rejects(b.items.state({}, {signal:controller.signal}),{code:'cancelled'});
  await second.close();
});
