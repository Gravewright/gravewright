import test from 'node:test';
import assert from 'node:assert/strict';
import { imageComponentKeys, imageComponentTransform } from './image-components.js';

test('component ownership expands only recognized native component references', () => {
    const image = { torch: { state: 'on', lit: true, components: {
        lights: { id: 'light-1' }, particles: { id: 'particle-1' }, shaders: { id: 'shader-1' },
        unknown: { id: 'private' },
    } } };
    assert.deepEqual(imageComponentKeys(image), ['light:light-1', 'particle:particle-1', 'shader:shader-1']);
    assert.deepEqual(imageComponentKeys({ torch: { state: 'on', lit: true } }), []);
    assert.deepEqual(imageComponentKeys({ lever: { state: 'on' } }), []);
});

test('component roots follow owner translation, rotation and scale around its center', () => {
    const original = { x: 100, y: 200, scale: 1, rotation: 30 };
    const next = { x: 300, y: 400, scale: 2, rotation: 120 };
    const base = { x: 120, y: 210, angle: 10, scaleX: 3, scaleY: 4 };
    const transformed = imageComponentTransform(original, next, base, { x: 120, y: 210 });
    assert.deepEqual(transformed, { x: 280, y: 440, angle: 100, scaleX: 3, scaleY: 4 });
    assert.deepEqual(base, { x: 120, y: 210, angle: 10, scaleX: 3, scaleY: 4 });
    assert.deepEqual(imageComponentTransform(original, original, base), base);
    assert.equal(imageComponentTransform({ ...original, scale: 0 }, next, base), undefined);
});

test('absolute particle and light geometry at a zero-origin root transforms as one group', () => {
    const original = { x: 100, y: 200, scale: 2, rotation: 0 };
    const next = { x: 150, y: 250, scale: 4, rotation: 90 };
    const local = { x: 100, y: 180 };
    const matrix = imageComponentTransform(original, next, { x: 0, y: 0, angle: 0 }, local);
    const radians = matrix.angle * Math.PI / 180;
    const world = { x: matrix.x + (local.x * Math.cos(radians) - local.y * Math.sin(radians)) * matrix.scaleX,
        y: matrix.y + (local.x * Math.sin(radians) + local.y * Math.cos(radians)) * matrix.scaleY };
    assert.ok(Math.abs(world.x - 190) < 1e-9);
    assert.ok(Math.abs(world.y - 250) < 1e-9);
    assert.equal(matrix.scaleX, 1, 'native component appearance is independent of artwork size');
});
