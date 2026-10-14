import test from 'node:test';
import assert from 'node:assert/strict';
import {BrowserBridge} from '../../gravewright/modules/static/gravewright_modules/browser-bridge.js';
import {Lifetime} from '../../gravewright/modules/static/gravewright_modules/lifetime.js';
import {OPERATION_TRANSPORTS} from '../../gravewright/modules/static/gravewright_modules/generated.js';

test('an idle mount renews its lease before calls and closes once', async () => {
 const bridge = new BrowserBridge('table'),life = new Lifetime(),calls=[];
 bridge.http={post:async(path,payload)=>{calls.push(payload.action);return {};}};
 const identity={moduleId:'example.test',tableId:'table',mountId:'mount',moduleSetRevision:'revision'};
 await bridge.ensure(identity,life);
 await bridge.ensure(identity,life);
 assert.deepEqual(calls,['open']);
 bridge.leaseTimes.set(life,Date.now()-31*60*1000);
 await bridge.ensure(identity,life);
 assert.deepEqual(calls,['open','open']);
 await life.close();
 assert.deepEqual(calls,['open','open','close']);
 assert.throws(()=>bridge.ensure(identity,life),e=>e.code==='stale_context');
});

test('lifecycle context exposes multipart card uploads with its bound lease', async t => {
 const previousWindow = globalThis.window;
 const previousFetch = globalThis.fetch;
 globalThis.window = new EventTarget();
 t.after(() => { globalThis.window = previousWindow; globalThis.fetch = previousFetch; });
 const bridge = new BrowserBridge('table'), life = new Lifetime(), leases = [], requests = [];
 bridge.http = {
  post: async (path, payload) => { leases.push({path, payload}); return {}; },
  get: async () => ({header:'X-CSRFToken', token:'test-csrf'}),
 };
 globalThis.fetch = async (url, options) => {
  requests.push({url, options});
  return new Response(JSON.stringify({value:{assetId:'native-asset'}}), {status:200});
 };
 const identity = {moduleId:'example.test',tableId:'table',mountId:'customize',moduleSetRevision:'revision'};
 const context = bridge.context({id:'example.test'},identity,life);
 const file = new File(['pixels'],'front.png',{type:'image/png'}), progress = [];
 assert.equal(OPERATION_TRANSPORTS['card.asset.upload'],'multipart');
 assert.deepEqual(await context.host.call('card.asset.upload',{file,purpose:'card_front'},{onProgress:value=>progress.push(value)}),{assetId:'native-asset'});
 assert.deepEqual(leases.map(call=>call.payload.action),['open']);
 const {url, options} = requests[0];
 assert.equal(url,'/api/tables/table/modules/example.test/call');
 assert.equal(options.credentials,'same-origin');
 assert.equal(options.headers['X-CSRFToken'],'test-csrf');
 assert.equal(options.signal,life.signal);
 assert.equal(options.body.get('file').name,'front.png');
 assert.deepEqual(JSON.parse(options.body.get('metadata')),{
  name:'card.asset.upload',payload:{purpose:'card_front'},moduleSetRevision:'revision',mountId:'customize',
 });
 assert.deepEqual(progress,[{loaded:file.size,total:file.size}]);
 await life.close();
 assert.deepEqual(leases.map(call=>call.payload.action),['open','close']);
 await assert.rejects(context.host.call('card.asset.upload',{file,purpose:'card_back'}),{code:'stale_context'});
 assert.equal(requests.length,1);
});

test('card uploads retain public permission errors and caller cancellation', async t => {
 const previousFetch = globalThis.fetch;
 t.after(() => { globalThis.fetch = previousFetch; });
 const bridge = new BrowserBridge('table'), life = new Lifetime();
 bridge.http = {post:async()=>({}),get:async()=>({header:'X-CSRFToken',token:'test-csrf'})};
 const host = bridge.host({moduleId:'example.test',mountId:'customize',moduleSetRevision:'revision'},life);
 const payload = {file:new File(['pixels'],'front.png',{type:'image/png'}),purpose:'card_front'};
 globalThis.fetch = async () => new Response(JSON.stringify({error:'permission_denied'}),{status:403});
 await assert.rejects(host.call('card.asset.upload',payload),{code:'permission_denied'});
 const cancellation = new AbortController();
 cancellation.abort();
 await assert.rejects(host.call('card.asset.upload',payload,{signal:cancellation.signal}),{code:'cancelled'});
 await life.close();
});
