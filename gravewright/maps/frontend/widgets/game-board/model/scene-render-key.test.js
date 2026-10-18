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

const images = {...state, images: [{id:'art',src:'/art.png',x:10,y:20,scale:1,rotation:0,layer:'game',z_index:0}]};
assert.equal(key(images), key({...images, images:[{...images.images[0],x:100,scale:2,rotation:90,layer:'gm',z_index:3}]}));
assert.equal(key(images), key({...images, images:[{...images.images[0],src:'/other.png'}]}));
assert.notEqual(key(images), key({...images, images:[]}));

const empty = { ...images, images: [{ ...images.images[0], src: '', empty: true, natural_width: 70, natural_height: 140 }] };
assert.notEqual(key(empty), key({ ...empty, images: [{ ...empty.images[0], empty: false }] }));
assert.notEqual(key(empty), key({ ...empty, images: [{ ...empty.images[0], natural_width: 140 }] }));
assert.notEqual(key(empty), key({ ...empty, images: [{ ...empty.images[0], natural_height: 70 }] }));
assert.equal(key(empty), key({ ...empty, images: [{ ...empty.images[0], x: 100, scale: 2, rotation: 90 }] }));

const surface = { ...images, images: [{ ...images.images[0], surface: { kind: 'floor', maskId: 'mask' },
    surfacePlane: { group: 'floor-layer', order: 0, operation: 'paint' } }] };
assert.notEqual(key(surface), key({ ...surface, images: [{ ...surface.images[0], layer: 'gm-image-layer' }] }));
assert.notEqual(key(surface), key({ ...surface, images: [{ ...surface.images[0], x: 100 }] }));
for (const dimension of ['natural_width', 'natural_height']) {
    assert.notEqual(key(surface), key({ ...surface, images: [{ ...surface.images[0], [dimension]: 200 }] }),
        'grouped surface dimensions invalidate their composite coverage');
}
assert.notEqual(key(surface), key({ ...surface, images: [{ ...surface.images[0],
    surface: { ...surface.images[0].surface, materialId: 'replacement' } }] }));

const region = { id: 'region', enabled: true, audience: 'gm',
    geometry: { shape: 'rect', x: 0, y: 0, width: 100, height: 100 },
    region: { name: 'Pressure plate', state: 'empty', count: 0 } };
const regions = { ...surface, zones: [region] };
assert.equal(key(surface), key(regions), 'adding a zone leaves floor and effects intact');
assert.notEqual(keys.zones(surface), keys.zones(regions));
assert.equal(keys.zones(regions), keys.zones(structuredClone(regions)));
for (const next of [
    { ...region, region: { ...region.region, state: 'occupied', count: 1 } },
    { ...region, region: { ...region.region, count: 2 } },
    { ...region, geometry: { ...region.geometry, width: 200 } },
    { ...region, audience: 'all' },
    { ...region, enabled: false },
]) {
    const changed = { ...regions, zones: [next] };
    assert.equal(key(regions), key(changed), 'zone changes leave floor and effects intact');
    assert.notEqual(keys.zones(regions), keys.zones(changed), 'the zone layer receives its own update');
}
for (const kind of ['lights', 'particles', 'shaders']) {
    const changed = { ...regions, [kind]: [{ id: 'effect', enabled: true }] };
    assert.notEqual(key(regions), key(changed), `${kind} still invalidates its scene resources`);
    assert.equal(keys.zones(regions), keys.zones(changed), `${kind} does not invalidate zone art`);
}
