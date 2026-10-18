import test from 'node:test';
import assert from 'node:assert/strict';
import { newDocument, defaultLayers } from './model.js';
import { nativeEffectState, hasNativeEffects } from './native-effects-model.js';
import { effectLights } from '../../../frontend/widgets/game-board/model/effect-lighting.js';

test('native projection scales only positions and geometry while retaining cell-based native ranges', () => {
    const doc = newDocument(); doc.layers = defaultLayers();
    const layerId = doc.layers[0].id;
    doc.lights.push({ id: 'torch', layerId, x: 2.5, y: 3.5, brightRadius: 2, dimRadius: 5, animation: 'torch',
        rotation: 35, angle: 120, color: '#ff9900', intensity: .9, enabled: true });
    doc.particles.push({ id: 'smoke', layerId, x: 5, y: 6, scale: 3, density: .6, kind: 'smoke', enabled: true });
    doc.shaders.push({ id: 'orb', layerId, x: 7, y: 8, radius: 6, opacity: .7, intensity: .8,
        source: 'gravewright-preset://orb-1/v1', enabled: true });
    const before = structuredClone(doc), projected = nativeEffectState(doc);
    assert.equal(projected.cell, 70); assert.equal(projected.width, 2800); assert.equal(projected.height, 2100);
    assert.deepEqual([projected.state.lights[0].x, projected.state.lights[0].y], [175, 245]);
    assert.equal(projected.state.lights[0].bright_radius, 2); assert.equal(projected.state.lights[0].dim_radius, 5);
    assert.deepEqual([projected.state.particles[0].x, projected.state.particles[0].scale], [350, 3]);
    assert.deepEqual([projected.state.shaders[0].x, projected.state.shaders[0].radius], [490, 6]);
    assert.equal(hasNativeEffects(projected), true);
    assert.deepEqual(doc, before);
});

test('native preview occlusion cuts walls at doors and preserves open/closed native door semantics', () => {
    const doc = newDocument();
    doc.walls.push({ id: 'wall', x1: 2, y1: 3, x2: 10, y2: 3 });
    doc.doors.push({ id: 'door', x1: 5, y1: 3, x2: 7, y2: 3, state: 'open' });
    const { state } = nativeEffectState(doc);
    assert.deepEqual(state.walls.map(wall => [wall.x1, wall.y1, wall.x2, wall.y2, wall.kind, wall.door_state]),
        [[140, 210, 350, 210, 'wall', undefined], [490, 210, 700, 210, 'wall', undefined], [350, 210, 490, 210, 'door', 'open']]);
    assert.equal(state.walls.every(wall => wall.blocks_light === 1 && wall.light_behavior === 'block'), true);
    doc.doors[0].state = 'closed';
    assert.equal(nativeEffectState(doc).state.walls.at(-1).door_state, 'closed');
});

test('native preview retains independent wall and door barrier rules and elevation after splitting', () => {
    const doc = newDocument();
    doc.walls.push({ id: 'window', x1: 2, y1: 3, x2: 10, y2: 3, presentation: 'window',
        behavior: { movement: 'block', vision: 'pass', light: 'pass', sound: 'attenuate' },
        vertical: { bottom: -1.25, top: 4.5 }, discovered: true });
    doc.doors.push({ id: 'secret', x1: 5, y1: 3, x2: 7, y2: 3, state: 'open', presentation: 'secret',
        behavior: { movement: 'pass', vision: 'block', light: 'block', sound: 'pass' },
        vertical: { bottom: null, top: null }, discovered: false });
    const before = structuredClone(doc), { state } = nativeEffectState(doc);
    assert.equal(state.walls.length, 3);
    for (const wall of state.walls.slice(0, 2)) {
        assert.deepEqual([wall.presentation, wall.movement_behavior, wall.vision_behavior, wall.light_behavior,
            wall.sound_behavior, wall.blocks_light, wall.blocks_sight, wall.vertical_bottom, wall.vertical_top, wall.discovered],
        ['window', 'block', 'pass', 'pass', 'attenuate', 0, 0, -1.25, 4.5, true]);
    }
    const door = state.walls.at(-1);
    assert.deepEqual([door.presentation, door.movement_behavior, door.light_behavior, door.blocks_light,
        door.vertical_bottom, door.vertical_top, door.discovered, door.door_state],
    ['secret', 'pass', 'block', 1, null, null, false, 'open']);
    assert.deepEqual(doc, before);
});

test('hidden layers and invisible effects consume no animation, while invisible emission remains native light', () => {
    const doc = newDocument();
    doc.layers.push({ id: 'hidden', visible: false });
    doc.lights.push({ id: 'hidden', layerId: 'hidden', x: 2, y: 2, enabled: true, intensity: 1 });
    doc.particles.push({ id: 'zero', x: 3, y: 4, enabled: true, density: 0, light_emission: 0 });
    doc.shaders.push({ id: 'zero', x: 5, y: 6, radius: 3, enabled: true, opacity: 0, intensity: 1, light_emission: 0 });
    assert.equal(hasNativeEffects(nativeEffectState(doc)), false);
    doc.shaders[0].light_emission = .25;
    const { state } = nativeEffectState(doc);
    assert.equal(state.shaders.length, 0); assert.equal(state.particles.length, 0); assert.equal(state.lights.length, 1);
    assert.deepEqual(state.lights[0], { id: 'emission:zero', x: 350, y: 420, color: undefined, intensity: .25,
        bright_radius: .44999999999999996, dim_radius: 3, enabled: true, animation: 'none', angle: 360, rotation: 0 });
});

test('invisible particle and shader emission exactly uses the native tabletop calculation', () => {
    const doc = newDocument(); doc.cellSize = 73;
    doc.particles.push({ id: 'particle', x: 2.3, y: 4.7, kind: 'smoke', scale: 3.3, density: 0,
        color: '#aabbcc', enabled: true, light_emission: .37 });
    doc.shaders.push({ id: 'bounded', x: 9.1, y: 2.2, radius: 7.7, opacity: 0, intensity: 1,
        color: '#ddbbcc', enabled: true, light_emission: .31 },
    { id: 'whole', x: 8.2, y: 7.3, radius: 0, opacity: 0, intensity: 0,
        color: '#aaddcc', enabled: true, light_emission: .29 });
    const projected = nativeEffectState(doc);
    const at = row => ({ ...row, x: row.x * doc.cellSize, y: row.y * doc.cellSize });
    assert.deepEqual(projected.state.lights, effectLights({ lights: [], particles: doc.particles.map(at),
        shaders: doc.shaders.map(at) }, doc.cellSize, projected.width, projected.height));
    assert.deepEqual(projected.state.particles, []); assert.deepEqual(projected.state.shaders, []);
});

test('zero intensity retains custom shaders because their code may ignore that uniform', () => {
    const doc = newDocument();
    const source = 'void main() { finalColor = vec4(0.2, 0.4, 0.6, 1.0); }';
    doc.shaders.push({ id: 'constant', x: 4, y: 3, radius: 2, opacity: 1, intensity: 0,
        enabled: true, light_emission: 0, source });
    const projected = nativeEffectState(doc);
    assert.equal(projected.state.shaders.length, 1);
    assert.equal(projected.state.shaders[0].source, source);
    assert.equal(projected.state.shaders[0].intensity, 0);
    assert.equal(hasNativeEffects(projected), true);
});
