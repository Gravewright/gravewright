import test from 'node:test';
import assert from 'node:assert/strict';
import { objectInSelectionWorkspace as allowed } from './selection-scope.js';
const layers = ['game','gm','composition','walls','lighting','effects','audio'];
test('authoring workspaces exclude unrelated objects even when overlapping', () => {
    const owners = {wall:'walls', light:'lighting', particle:'effects', shader:'effects', sound:'audio', card:'game', zone:'gm'};
    for (const [kind, owner] of Object.entries(owners)) for (const layer of layers)
        assert.equal(allowed({kind,data:{},x:100,y:100},layer),layer===owner,`${kind} in ${layer}`);
    for (const kind of ['drawing','measure','unknown']) assert.equal(allowed({kind,data:{}},'game'),false);
});
test('Game and GM selection keep token and image audiences separate', () => {
    for (const layer of layers) {
        assert.equal(allowed({kind:'token',data:{}},layer),layer==='game');
        assert.equal(allowed({kind:'token',data:{hidden:true}},layer),layer==='gm');
        assert.equal(allowed({kind:'token',data:{layer:'game',hidden:true}},layer),layer==='game');
        assert.equal(allowed({kind:'image',data:{layer:'map'}},layer),layer==='composition');
        assert.equal(allowed({kind:'image',data:{layer:'gm-image-layer'}},layer),layer==='gm');
        assert.equal(allowed({kind:'image',data:{layer:'map',empty:true}},layer),layer==='gm');
    }
});
