import test from 'node:test';
import assert from 'node:assert/strict';
import { sceneObjects, hit } from './objects.js';

test('a composed image is one mixed selection object while unrelated native effects remain selectable', () => {
    const state = { cards: [], walls: [], lights: [{ id: 'owned', x: 10, y: 20 }, { id: 'free', x: 50, y: 60 }],
        particles: [{ id: 'fire', x: 10, y: 20 }], shaders: [{ id: 'aura', x: 10, y: 20 }], spatialSounds: [], zones: [],
        images: [{ id: 'torch', x: 10, y: 20, scale: 1, rotation: 0, natural_width: 20, natural_height: 30,
            torch: { state: 'off', lit: true, components: { lights: { id: 'owned' },
                particles: { id: 'fire' }, shaders: { id: 'aura' } } } }] };
    assert.deepEqual(sceneObjects(state, [], 70, true, []).map(row => row.key), ['image:torch', 'light:free']);
    const detached = { ...state, images: [] };
    assert.deepEqual(sceneObjects(detached, [], 70, true, []).map(row => row.key),
        ['light:owned', 'light:free', 'particle:fire', 'shader:aura']);
    assert.deepEqual(sceneObjects(state, [], 70, false, []), []);
});

test('generated paint and erase operators stay internal while promoted surfaces remain selectable', () => {
    const state = { cards: [], walls: [], lights: [], particles: [], shaders: [], spatialSounds: [], zones: [],
        images: [{ id: 'static', surfacePlane: { group: 'a', order: 0, operation: 'paint' } },
            { id: 'erase', surfacePlane: { group: 'a', order: 1, operation: 'erase' } },
            { id: 'dynamic', surfacePlane: { group: 'a', order: 2, operation: 'paint' }, surface: { kind: 'floor' },
                x: 10, y: 10, rotation: 0, scale: 1, natural_width: 10, natural_height: 10 }] };
    assert.deepEqual(sceneObjects(state, [], 70, true, []).map(row => row.id), ['dynamic']);
});

test('the GM can select an Empty Object by its authored box while players retain no editing object', () => {
    const image = { id: 'controller', empty: true, src: '', asset_id: null, x: 100, y: 150,
        scale: 2, rotation: 90, natural_width: 40, natural_height: 20, lever: { state: 'off' } };
    const state = { cards: [], walls: [], lights: [], particles: [], shaders: [], spatialSounds: [], zones: [], images: [image] };
    const selected = sceneObjects(state, [], 70, true, []);
    assert.equal(selected.length, 1);
    assert.equal(selected[0].label, 'Empty Object');
    assert.equal(selected[0].key, 'image:controller');
    assert.equal(hit(selected[0], { x: 110, y: 180 }, 0), true);
    assert.equal(hit(selected[0], { x: 130, y: 150 }, 0), false);
    assert.deepEqual(sceneObjects(state, [], 70, false, []), []);
});
