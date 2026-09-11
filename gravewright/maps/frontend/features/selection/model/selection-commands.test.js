import assert from 'node:assert/strict';
import {applySelection,transformMeasures} from './selection-commands.js';
const calls=[];
const api={command:async(_c,_b,area,action,data)=>{calls.push({area,action,data});if(data.placement_id==='stale')throw Error('conflict');}};
const tokens={move:async(_c,id,data)=>{calls.push({area:'tokens',action:'move',data});return {version:8};},command:async(_c,_m,action,data)=>calls.push({area:'tokens',action,data})};
const rows=[{key:'token:t',id:'t',kind:'token',x:115,y:225,data:{cells:1,version:7,rotation:0}},
 {key:'image:i',id:'i',kind:'image',x:115,y:225,data:{rotation:0,version:1}},
 {key:'image:stale',id:'stale',kind:'image',x:0,y:0,data:{rotation:0,version:1}},
 {key:'wall:w',id:'w',kind:'wall',x:0,y:0,data:{x1:0,y1:0,x2:10,y2:0}},
 {key:'zone:z',id:'z',kind:'zone',x:0,y:0,data:{version:1,geometry:{shape:'rect',x:0,y:0,width:10,height:20}}}];
const result=await applySelection(api,tokens,'c','b','m',70,{},rows,'transform',{x:0,y:0},70,70,90,{x:10,y:15});
assert.deepEqual(result.failed,['image:stale']);assert.equal(result.done.length,4);
const moved=calls.find(c=>c.area==='tokens'&&c.action==='move').data;
assert.ok(Math.abs(moved.gridX-((-225+70-10)/70-.5))<1e-9);
assert.equal(calls.find(c=>c.area==='tokens'&&c.action==='configure').data.expectedVersion,8);
assert.deepEqual(calls.find(c=>c.area==='walls').data,{wall_id:'w',x1:70,y1:70,x2:70,y2:80});
assert.equal(calls.find(c=>c.area==='zones').data.patch.geometry.shape,'polygon');
assert.equal(transformMeasures([{id:'m',origin:{x:1,y:2},direction:0}],['m'],'delete',{x:0,y:0},0,0,0).length,0);
console.log('Mixed transforms preserve grid origin, revisions and partial failures');
