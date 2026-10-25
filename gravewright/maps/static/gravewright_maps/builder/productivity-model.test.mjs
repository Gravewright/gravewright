import test from 'node:test';
import assert from 'node:assert/strict';
import { newDocument } from './model.js';
import { organizeSelection, groupSelection, selectionBundle, placeBundle, objectBrushSamples, scatterObject } from './productivity-model.js';
import { playerWalls, areaEvents, playerDocument } from './player-test-model.js';

function fixture(){const document=newDocument();document.decorations=[1,4,8].map((x,index)=>({id:crypto.randomUUID(),layerId:document.layers[0].id,assetId:null,empty:true,lever:{state:'off'},name:'Object '+index,x,y:index+1,width:1,height:1,rotation:0}));return document;}
const refs=document=>document.decorations.map(item=>({kind:'decorations',id:item.id}));
test('align and distribute are atomic and respect locked selections',()=>{
    const doc=fixture(),before=structuredClone(doc);
    assert.deepEqual(organizeSelection(doc,refs(doc),'top').decorations.map(item=>item.y),[1,1,1]);
    assert.deepEqual(organizeSelection(doc,refs(doc),'distribute-x').decorations.map(item=>item.x),[1,4.5,8]);
    assert.deepEqual(doc,before);
    doc.layers[0].locked=true;assert.equal(organizeSelection(doc,refs(doc),'top'),null);
});
test('grouping moves selected objects while preserving identities and history input',()=>{
    const doc=fixture(),result=groupSelection(doc,refs(doc),'Danger room');
    assert.equal(result.document.layers.length,2);assert.equal(doc.layers.length,1);
    assert.deepEqual(result.document.decorations.map(item=>item.id),doc.decorations.map(item=>item.id));
    assert.ok(result.document.decorations.every(item=>item.layerId===result.layerId));
});
test('saved bundles preserve presence, remap internal targets and reject out of bounds atomically',()=>{
    const doc=fixture();doc.decorations[0].presenceRadius=2;
    doc.decorations[0].blueprint={graphs:{interact:{nodes:[{type:'reference',targetId:doc.decorations[1].id}]}}};
    const target=newDocument(),bundle=selectionBundle(doc,refs(doc));
    const placed=placeBundle(target,bundle,{x:3,y:3},target.layers[0].id);
    assert.equal(placed.document.decorations[0].presenceRadius,2);
    assert.notEqual(placed.document.decorations[0].id,doc.decorations[0].id);
    assert.equal(placed.document.decorations[0].blueprint.graphs.interact.nodes[0].targetId,placed.document.decorations[1].id);
    assert.equal(target.decorations.length,0);
    assert.equal(placeBundle(target,bundle,{x:39,y:29},target.layers[0].id),null);
});
test('object brush samples a whole path and clamps artwork size at source limits',()=>{
    const first=objectBrushSamples({x:0,y:0},{x:2.5,y:0},1);
    assert.deepEqual(first.samples,[{x:1,y:0},{x:2,y:0}]);assert.equal(first.carry,.5);
    assert.deepEqual(objectBrushSamples({x:2.5,y:0},{x:4,y:0},1,first.carry).samples,[{x:3,y:0},{x:4,y:0}]);
    const doc=fixture();const item=scatterObject(doc,{x:10,y:10},{assetId:crypto.randomUUID(),layerId:doc.layers[0].id,width:2,height:2,scaleVariation:.5,rotationVariation:90},()=>1);
    assert.equal(item.width,3);assert.equal(item.rotation,90);
});
test('player walls leave door openings and honor pass channels and hidden layers',()=>{
    const doc=fixture(),layerId=doc.layers[0].id;
    doc.walls=[{id:crypto.randomUUID(),layerId,x1:5,y1:0,x2:5,y2:10,thickness:.2}];
    doc.doors=[{id:crypto.randomUUID(),layerId,x1:5,y1:3,x2:5,y2:4,state:'open',thickness:.2}];
    const walls=playerWalls(doc);assert.equal(walls.length,3);assert.equal(walls[2].door_state,'open');
    doc.layers[0].visible=false;assert.equal(playerWalls(doc).length,0);assert.equal(playerDocument(doc).decorations.length,0);
});
test('area rehearsal detects enter and exit during a crossing without editing the source',()=>{
    const doc=fixture();doc.decorations[0].presenceRadius=1;
    const before=structuredClone(doc),events=areaEvents(doc,{x:0,y:1.5},{x:5,y:1.5});
    assert.deepEqual(events.map(event=>event.event),['presence:enter','presence:exit']);assert.deepEqual(doc,before);
    doc.decorations[0].presenceRadius=.05;
    assert.deepEqual(areaEvents(doc,{x:0,y:1.5},{x:200,y:1.5}).map(event=>event.event),['presence:enter','presence:exit']);
    const actor=crypto.randomUUID();
    doc.decorations=[];doc.regions=[{id:crypto.randomUUID(),layerId:doc.layers[0].id,x:1,y:1,width:1,height:1,enabled:true,filters:{actorIds:[actor]}}];
    assert.equal(areaEvents(doc,{x:0,y:1.5},{x:4,y:1.5},{actorId:crypto.randomUUID()}).length,0);
    assert.equal(areaEvents(doc,{x:0,y:1.5},{x:4,y:1.5},{actorId:actor}).length,2);
});
