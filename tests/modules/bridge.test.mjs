import test from 'node:test';
import assert from 'node:assert/strict';
import {BrowserBridge} from '../../gravewright/modules/static/gravewright_modules/browser-bridge.js';
import {Lifetime} from '../../gravewright/modules/static/gravewright_modules/lifetime.js';

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
