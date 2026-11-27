import test from 'node:test';
import assert from 'node:assert/strict';
import {createDomainApi,executeNative} from '../../gravewright/modules/static/gravewright_modules/domain-api.js';

test('initiative batches expose one explicit mutation preserving sources, UUID and abort signal',async()=>{
  const calls=[],api=createDomainApi(async(...args)=>{calls.push(args);return {version:8,batch:{replayed:false}};});
  const payload={sceneId:'scene',version:7,selectFirst:true,label:'Initiative',entries:[
    {tokenId:'token',expression:'2d20kh1+3',visibility:'gm',source:{actorVersion:4,sheetVersion:2,tokenVersion:6}}]};
  const options={requestId:'same-logical-operation',signal:new AbortController().signal};
  assert.equal((await api.combat.rollInitiativeBatch(payload,options)).version,8);
  assert.deepEqual(calls,[['combat','rollInitiativeBatch',payload,options]]);
  assert.equal(calls[0][3],options);
  assert.equal(api.capabilities().domains.combat.rollInitiativeBatch,'roll-initiative-batch');
  await executeNative(api,'combat','roll-initiative-batch',payload,options);
  assert.deepEqual(calls[1],calls[0]);
});
