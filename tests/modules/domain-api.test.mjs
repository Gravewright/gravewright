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

test('clock collections and mutations preserve scope, revisions and retry identity', async () => {
  const calls = [], clock = { id: 'clock', sceneId: null, version: 3 };
  const api = createDomainApi(async (...args) => { calls.push(args); return { clocks: [clock] }; });
  const options = { requestId: 'logical-clock-operation' };
  const context = { sceneId: 'scene', mapId: 'scene' };
  assert.equal(await api.clocks.get('clock', context), clock);
  await assert.rejects(api.clocks.get('unavailable', context), { code: 'not_found' });
  const payload = { ...context, id: clock.id, version: clock.version, scopeSceneId: null, name: 'Campaign clock' };
  await api.clocks.update(payload, options);
  await api.clocks.advance({ ...context, id: clock.id, version: 4, delta: -1 }, options);
  assert.deepEqual(calls.at(-2), ['clocks', 'update', payload, options]);
  assert.deepEqual(calls.at(-1), ['clocks', 'advance', { ...context, id: 'clock', version: 4, delta: -1 }, options]);
  assert.equal(clock.version, 3);
});

test('clock events filter other scenes and campaigns and release their listener', async () => {
  const target = new EventTarget(), life = new Lifetime(), values = [];
  const events = createEvents(target, life, { tableId: 'table', sceneId: 'scene' });
  events.on('clocks.changed', payload => values.push(payload));
  const emit = payload => target.dispatchEvent(new CustomEvent('gravewright:api-event', { detail: { type: 'resources.state', payload } }));
  emit({ tableId: 'other', sceneId: 'scene', module: 'clocks' });
  emit({ tableId: 'table', sceneId: 'other', module: 'clocks' });
  emit({ tableId: 'table', sceneId: 'scene', module: 'combat' });
  const projection = { tableId: 'table', sceneId: 'scene', module: 'clocks', state: { clocks: [] } };
  emit(projection);
  assert.deepEqual(values, [projection]);
  await life.close();
  emit(projection);
  assert.equal(values.length, 1);
});

test('clue discovery methods retain revision and retry identity without changing the projected collection', async () => {
  const clue = { id: 'discovered', version: 5, discovered: true }, calls = [];
  const api = createDomainApi(async (...args) => { calls.push(args); return { clues: [clue] }; });
  const context = { sceneId: 'scene' }, options = { requestId: 'logical-discovery' };
  assert.deepEqual(await api.clues.list(context), [clue]);
  await assert.rejects(api.clues.get('undiscovered', context), { code: 'not_found' });
  for (const action of ['reveal', 'hide', 'reset']) {
    const payload = { ...context, id: clue.id, version: clue.version };
    await api.clues[action](payload, options);
    assert.deepEqual(calls.at(-1), ['clues', action, payload, options]);
  }
  assert.equal(clue.version, 5);
});

test('clue subscriptions read authorized state and never forward an invalidation as a discovery', async () => {
  const target = new EventTarget(), life = new Lifetime(), values = [], reads = [];
  const projection = { clues: [{ id: 'discovered', content: 'Public finding' }] };
  const events = createEvents(target, life, { tableId: 'table', sceneId: 'scene' }, async domain => {
    reads.push(domain); return projection;
  });
  events.on('clues.changed', value => values.push(value));
  await new Promise(resolve => setImmediate(resolve));
  const emit = payload => target.dispatchEvent(new CustomEvent('gravewright:api-event', {
    detail: { type: 'api.changed', payload },
  }));
  emit({ tableId: 'foreign', domain: 'clues' });
  emit({ tableId: 'table', domain: 'clocks' });
  emit({ tableId: 'table', domain: 'clues', state: { clues: [{ gmNotes: 'NEVER FORWARD' }] } });
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(reads, ['clues', 'clues']);
  assert.equal(values.length, 2);
  assert.deepEqual(values.at(-1), { module: 'clues', state: projection, tableId: 'table', sceneId: 'scene' });
  assert.equal(JSON.stringify(values).includes('NEVER FORWARD'), false);
  await life.close();
  emit({ tableId: 'table', domain: 'clues' });
  assert.equal(reads.length, 2);
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
