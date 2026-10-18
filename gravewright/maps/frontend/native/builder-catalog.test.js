import test from 'node:test';
import assert from 'node:assert/strict';
import { lightPresets, particlePresets, shaderPresets, createLight, createParticle, createShader } from './builder-catalog.js';
import { payload } from '../features/effects/model/effects.js';

test('builder native factories retain table preset values and omit catalog metadata from saved rows', () => {
    assert.equal(lightPresets.length, 3); assert.equal(particlePresets.length, 12); assert.equal(shaderPresets.length, 50);
    for (const preset of lightPresets) {
        const row = createLight(preset.id, 2, 3);
        assert.equal(row.animation, preset.id); assert.equal(row.color, preset.color);
        assert.equal(row.brightRadius, preset.bright_radius); assert.equal(row.dimRadius, preset.dim_radius);
        assert.equal(row.x, 2); assert.equal(row.y, 3); assert.equal(Object.hasOwn(row, 'id'), false);
        assert.equal(Object.hasOwn(row, 'name'), false);
    }
    for (const preset of particlePresets) {
        const row = createParticle(preset.id, 4, 5);
        assert.equal(row.kind, preset.id); assert.equal(row.color, preset.color); assert.equal(row.scale, preset.scale);
        assert.deepEqual(payload('particle', row), row); assert.equal(Object.hasOwn(row, 'id'), false);
    }
    for (const preset of shaderPresets) {
        const row = createShader(preset.id, 6, 7);
        assert.equal(row.source, `gravewright-preset://${preset.id}/v1`); assert.equal(row.radius, preset.radius);
        assert.equal(row.name, preset.name); assert.equal(row.color, preset.color);
        assert.deepEqual(payload('shader', row), row); assert.equal(Object.hasOwn(row, 'id'), false);
        assert.equal(Object.hasOwn(row, 'category'), false); assert.equal(Object.hasOwn(row, 'description'), false);
    }
    assert.throws(() => createLight('unknown'), /Unknown/);
    assert.throws(() => createParticle('unknown'), /Unknown/);
    assert.throws(() => createShader('unknown'), /Unknown/);
});
