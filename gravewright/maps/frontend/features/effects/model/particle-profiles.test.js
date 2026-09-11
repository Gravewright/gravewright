import { test } from 'node:test';
import assert from 'node:assert/strict';
import { PARTICLE_DEFAULTS, particlesOf } from './particle-profiles.js';
import { shaderPresets } from '../../scene-layers/lib/shader-presets.js';
import { defaults, payload } from './effects.js';
test('all twelve legacy profiles produce distinct, finite motion and appearance', () => {
    const signatures = new Set();
    assert.equal(Object.keys(PARTICLE_DEFAULTS).length, 12);
    for (const [kind, settings] of Object.entries(PARTICLE_DEFAULTS)) {
        const emitter = { id: 'test', x: 100, y: 200, enabled: true, kind, ...settings };
        const particles = particlesOf(emitter, 1234, 70);
        assert.ok(particles.length > 0, kind);
        for (const p of particles)
            for (const field of ['x', 'y', 'size', 'alpha', 'rotation'])
                assert.ok(Number.isFinite(p[field]), `${kind}.${field}`);
        signatures.add(JSON.stringify(particles));
        assert.deepEqual(particlesOf({ ...emitter, density: 0 }, 1234, 70), []);
        assert.deepEqual(particlesOf({ ...emitter, enabled: false }, 1234, 70), []);
    }
    assert.equal(signatures.size, 12);
});
test('rotation turns legacy motion around the emitter origin', () => {
    const emitter = { id: 'rain', x: 100, y: 200, enabled: true, kind: 'rain', ...PARTICLE_DEFAULTS.rain };
    const a = particlesOf(emitter, 1234, 70)[0];
    const b = particlesOf({ ...emitter, rotation: 90 }, 1234, 70)[0];
    assert.ok(Math.abs(b.x - (100 - (a.y - 200))) < 1e-8);
    assert.ok(Math.abs(b.y - (200 + (a.x - 100))) < 1e-8);
});
test('shader placement preserves each preset source and parameters', () => {
    assert.equal(shaderPresets.length, 50);
    const sources = new Set();
    for (const preset of shaderPresets) {
        const data = payload('shader', { ...defaults(), ...preset, x: 100, y: 200 });
        assert.equal(data.source, preset.source);
        for (const key of ['color', 'scale', 'radius', 'speed', 'blend_mode'])
            assert.equal(data[key], preset[key]);
        sources.add(preset.source);
    }
    assert.equal(sources.size, 50);
});
