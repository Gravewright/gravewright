import test from 'node:test';
import assert from 'node:assert/strict';
import { builderNativeDraft, builderNativeItem } from './builder-editor-model.js';
import { createLight, createParticle, createShader, shaderPresets } from './builder-catalog.js';

const identify = item => ({ id: 'source-id', layerId: 'custom-layer', ...item, authored: { reference: 'preserved' } });

test('private native drafts leave source objects unchanged and no-op saves preserve absent legacy fields', () => {
    for (const [kind, item] of [['lights', createLight()], ['particles', createParticle()], ['shaders', createShader()]]) {
        const source = identify(item), before = structuredClone(source), draft = builderNativeDraft(kind, source);
        assert.deepEqual(builderNativeItem(kind, source, draft), source);
        draft.authored.reference = 'draft-only';
        draft.color = '#112233';
        const next = builderNativeItem(kind, source, draft);
        assert.equal(next.color, '#112233');
        assert.deepEqual(next.authored, before.authored);
        assert.deepEqual(source, before);
    }
    const oldLight = identify({ ...createLight(), elevation: -12.5 });
    delete oldLight.rotation; delete oldLight.angle; delete oldLight.animation;
    assert.deepEqual(builderNativeItem('lights', oldLight, builderNativeDraft('lights', oldLight)), oldLight);
});

test('native light radii stay in cells and preserve unlimited falloff, position and custom-layer identity', () => {
    const source = identify({ ...createLight('torch', 3.125, 8.75), elevation: 12 });
    const draft = builderNativeDraft('lights', source);
    assert.equal(draft.bright_radius, source.brightRadius);
    draft.bright_radius = 9.5; draft.dim_radius = 2;
    draft.id = 'forbidden'; draft.layerId = 'forbidden'; draft.x = 500; draft.elevation = -99;
    const next = builderNativeItem('lights', source, draft);
    assert.equal(next.brightRadius, 9.5); assert.equal(next.dimRadius, 9.5);
    for (const key of ['id', 'layerId', 'x', 'y', 'elevation']) assert.equal(next[key], source[key]);
    assert.equal(Object.hasOwn(next, 'bright_radius'), false);
    draft.dim_radius = 0;
    assert.equal(builderNativeItem('lights', source, draft).dimRadius, 0);
});

test('shader editing resolves the reviewed preset and preserves its URI when only settings change', () => {
    const source = identify(createShader('orb-1', 4.5, 6.25));
    const draft = builderNativeDraft('shaders', source);
    assert.equal(draft.source, shaderPresets.find(preset => preset.id === 'orb-1').source);
    draft.opacity = .35;
    assert.equal(builderNativeItem('shaders', source, draft).source, source.source);
    draft.source = 'void main() { finalColor = vec4(1.0); }';
    assert.equal(builderNativeItem('shaders', source, draft).source, draft.source);
    Object.assign(draft, shaderPresets.find(preset => preset.id === 'orb-2'));
    const next = builderNativeItem('shaders', source, draft);
    assert.equal(next.source, 'gravewright-preset://orb-2/v1');
    assert.equal(next.id, source.id);
    assert.equal(Object.hasOwn(next, 'category'), false);
    assert.equal(Object.hasOwn(next, 'description'), false);
});

test('native draft validation rejects invalid values without mutating the source', () => {
    const cases = [
        ['lights', createLight(), { bright_radius: 201 }],
        ['lights', createLight(), { angle: 4 }],
        ['lights', createLight(), { enabled: 1 }],
        ['particles', createParticle(), { kind: '__proto__' }],
        ['particles', createParticle(), { scale: NaN }],
        ['particles', createParticle(), { light_emission: 2.01 }],
        ['shaders', createShader(), { source: 'bad\0source' }],
        ['shaders', createShader(), { name: '   ' }],
        ['shaders', createShader(), { blend_mode: 'forbidden' }],
    ];
    for (const [kind, fields, changes] of cases) {
        const source = identify(fields), before = structuredClone(source), draft = { ...builderNativeDraft(kind, source), ...changes };
        assert.throws(() => builderNativeItem(kind, source, draft));
        assert.deepEqual(source, before);
    }
    assert.throws(() => builderNativeDraft('shaders', { source: 'gravewright-preset://missing/v1' }), /Unknown shader preset/);
});
