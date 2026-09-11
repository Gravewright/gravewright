import assert from 'node:assert/strict';
import { SceneRenderKey } from './scene-render-key.js';
const state = { containerId: 'a', blockId: 'b', sceneId: 'c', walls: [], lights: [], particles: [], shaders: [], images: [], cards: [], zones: [], spatialSounds: [], lighting: { mode: 'dynamic', darkness: 1 }, fog: { enabled: false }, vision: [] };
const keys = new SceneRenderKey();
const key = (s) => keys.static(s, 70, 1400, 900, true, 'quality');
assert.equal(key(state), key(structuredClone(state)));
const moved = { ...state, previewTokenVision: true, vision: [{ x: 100, y: 100, radius: 70 }] };
assert.equal(key(state), key(moved));
assert.notEqual(keys.vision(state), keys.vision(moved));
assert.notEqual(key(state), key({ ...state, lighting: { ...state.lighting, lights_out: false } }));
assert.notEqual(key(state), key({ ...state, walls: [{ id: 'wall', x1: 1, y1: 1, x2: 10, y2: 10, kind: 'wall' }] }));
assert.notEqual(key(state), key({ ...state, blockId: 'another' }));
assert.notEqual(key(state), keys.static(state, 70, 1400, 900, true, 'performance'));
assert.equal(key(state), key({ ...state, fog: { ...state.fog, gmOpacity: .3 } }));

assert.equal(key(state), key({ ...state, fog: { enabled: true, ops: [{ mode: "reveal" }] } }));
