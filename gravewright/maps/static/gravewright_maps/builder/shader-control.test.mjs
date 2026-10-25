import test from 'node:test';
import assert from 'node:assert/strict';
import {shaderProperties,validateShaderValue} from './shader-control.js';
import {defaultBlueprint,eventGraph,connectNodes,validateBlueprint,simulateGraph} from './blueprint-model.js';
import {captureTemplate,resolveTemplate} from './blueprint-templates.js';

const id='00000000-0000-4000-8000-000000000017',replacement='00000000-0000-4000-8000-000000000018';
function fixture(property='opacity',value=.4){const blueprint=defaultBlueprint('lever'),graph=blueprint.graphs.interact=eventGraph('interact');
    graph.nodes.push({id:'shader',type:'shaderControl',targetId:id,property,value,x:300,y:60});connectNodes(graph,'event','next','shader');return {blueprint,graph};}
test('shader controls expose bounded native properties and keep GLSL out of the action',()=>{
    for(const[property,field]of Object.entries(shaderProperties))assert.equal(validateShaderValue(property,field.value),field.value);
    for(const[property,value]of [['source','void main(){}'],['enabled',1],['speed',9],['opacity',-1],['color','red'],['intensity',NaN]])assert.throws(()=>validateShaderValue(property,value));
    const {blueprint}=fixture();assert.equal(validateBlueprint(blueprint,{shaders:[{id}]}),blueprint);
    assert.throws(()=>validateBlueprint(blueprint,{shaders:[]}),/shader/);
});
test('shader value sockets read compatible variables and reject invalid evaluated values',()=>{
    const {blueprint,graph}=fixture('speed',1);
    graph.nodes.push({id:'speed',type:'getVariable',scope:'element',name:'Speed',valueType:'number',default:2,x:0,y:300});
    connectNodes(graph,'speed','value','shader',{input:'value'});
    assert.equal(simulateGraph(blueprint,'interact','off').actions[0].value,2);
    graph.nodes[2].default=9;
    assert.throws(()=>simulateGraph(blueprint,'interact','off'),/shader/);
});
test('behavior templates bind shader resources instead of keeping a previous map target',()=>{
    const {blueprint}=fixture();
    const definition=captureTemplate(blueprint,{catalog:{shaders:[{id,name:'Mist'}]}});
    const binding=definition.bindings.find(row=>row.type==='shader');assert.ok(binding);
    const placed=resolveTemplate(definition,{bindings:{[binding.id]:replacement},parameters:{},catalog:{shaders:[{id:replacement}]}});
    assert.equal(placed.graphs.interact.nodes[1].targetId,replacement);
});
