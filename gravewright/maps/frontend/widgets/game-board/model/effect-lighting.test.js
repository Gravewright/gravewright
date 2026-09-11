import { test } from 'node:test';
import assert from 'node:assert/strict';
import { effectLights } from './effect-lighting.js';
import { effectQuality } from '../../../shared/rendering/effect-quality.js';
test('emission follows enabled sources without adding persistent light identities', () => {
    const state = { lights: [], particles: [{ id: 'spark', x: 10, y: 20, scale: 2, color: '#ffaa00', enabled: true, light_emission: .5 }, { id: 'off', enabled: false, light_emission: 1 }], shaders: [] };
    const before = JSON.stringify(state), lights = effectLights(state, 70, 1400, 900);
    assert.equal(lights.length, 1);
    assert.equal(lights[0].id, 'emission:spark');
    assert.equal(lights[0].x, 10);
    assert.equal(lights[0].dim_radius, 2);
    assert.equal(lights[0].intensity, .5);
    assert.equal(JSON.stringify(state), before);
});
test('local profiles bound visual work without hiding source data', () => {
    for (const name of ['performance', 'balanced', 'quality']) {
        assert.ok(effectQuality(name).fps > 0, `${name} must animate scene content`);
        assert.ok(effectQuality(name).particles > 0, `${name} must display particles`);
        assert.equal(effectQuality(name).shaders, true, `${name} must render GLSL`);
    }
    assert.ok(effectQuality('performance').fps < effectQuality('balanced').fps);
    assert.ok(effectQuality('performance').particleLimit < effectQuality('balanced').particleLimit);
    assert.ok(effectQuality('balanced').particleLimit < effectQuality('quality').particleLimit);
    assert.ok(effectQuality('balanced').lightMap < effectQuality('quality').lightMap);
    assert.equal(effectQuality('quality').shaderDetail, 5);
});
