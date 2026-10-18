import { test } from 'node:test';
import assert from 'node:assert/strict';
import { projectTestDocument } from './playtest-model.js';
import { torchComponentState } from './torch-model.js';

test('door rehearsal keeps anchored open artwork while honoring an explicit hidden sprite', () => {
    const source = { cellSize: 70, doors: [{ id: 'hinged', assetId: 'wood', state: 'closed', rotationAnchor: 'end' }],
        decorations: [], regions: [], floors: [], walls: [], lights: [] };
    const opened = { changes: { elements: [{ id: 'native', sourceId: 'hinged', after: { data: { door_state: 'open' } } }] } };
    assert.equal(projectTestDocument(source, opened).doors[0].testAppearance.visible, true);
    opened.changes.elements[0].after.data.sprite = { appearance: 'hidden' };
    assert.equal(projectTestDocument(source, opened).doors[0].testAppearance.visible, false);
    assert.equal(source.doors[0].state, 'closed');
});

test('native rehearsal projects visual changes while preserving authored data and graphs', () => {
    const source = { cellSize: 100, doors: [{ id: 'door', state: 'closed', assetId: 'original', blueprint: { graphs: { 'signal:FixtureInteractClosed': { nodes: [] } } } }],
        floors: [{ id: 'floor', assetId: 'stone' }], lights: [{ id: 'lamp', x: 2, y: 2, enabled: false, brightRadius: 1, dimRadius: 2 }], decorations: [], regions: [], walls: [] };
    const before = structuredClone(source);
    const result = { sourceIds: { native: 'lamp' }, changes: { elements: [
        { id: 'd', sourceId: 'door', after: { data: { door_state: 'open', sprite: { appearance: 'hidden' } } } },
        { id: 'f', sourceId: 'floor', before: { data: { x: 200, y: 200, scale: 1, rotation: 0 } }, after: { data: { x: 300, y: 400, scale: 2, rotation: 90, surface: { materialId: 'wood' } } } },
        { id: 'native', after: { data: { x: 500, y: 600, enabled: true, bright_radius: 3, dim_radius: 4 } } },
    ] } };
    const projected = projectTestDocument(source, result);
    assert.deepEqual(source, before);
    assert.equal(projected.doors[0].state, 'open'); assert.equal(projected.doors[0].testAppearance.visible, false);
    assert.deepEqual(projected.doors[0].blueprint, source.doors[0].blueprint);
    assert.equal(projected.floors[0].assetId, 'wood');
    assert.equal(projected.floors[0].testTransform, 'translate(3 4) rotate(90) scale(2) translate(-2 -2)');
    assert.equal(projected.lights[0].enabled, true); assert.equal(projected.lights[0].x, 5); assert.equal(projected.lights[0].dimRadius, 4);
    assert.deepEqual(projectTestDocument(source, null), source);
});

test('hidden and rotated native torch projects its image without a double rotation', () => {
    const source = { cellSize: 100, decorations: [{ id: 'torch', x: 0, y: 0, width: 1, height: 1, rotation: 0, torch: { state: 'off', lit: true } }] };
    const projected = projectTestDocument(source, { changes: { elements: [{ sourceId: 'torch', after: { data: {
        x: 300, y: 400, natural_width: 100, natural_height: 200, scale: 1, rotation: 135,
        torch: { state: 'on', lit: false }, asset_id: 'new', layer: 'gm',
    } } }] } });
    assert.equal(projected.decorations[0].rotation, 45);
    assert.deepEqual(projected.decorations[0].torch, { state: 'on', lit: false });
    assert.equal(projected.decorations[0].testAppearance.visible, false);
    assert.equal(projected.decorations[0].x, 2.5); assert.equal(projected.decorations[0].y, 3);
});

test('a native child already rotated by the engine is not rotated again in the test preview', () => {
    const document = { decorations: [{ id: 'torch', x: 2, y: 2, width: 1, height: 1,
        torch: { state: 'on', lit: true, lightId: 'light' } }],
    lights: [{ id: 'light', x: 3, y: 4, enabled: false, rotation: 90, testNative: true }] };
    assert.deepEqual(torchComponentState(document, 'lights', document.lights[0]), document.lights[0]);
    const result = projectTestDocument({ cellSize: 100, doors: [{ id: 'door', state: 'closed' }] }, {
        changes: { elements: [{ sourceId: 'door', after: { data: { door_state: 'open' } } }] },
    });
    assert.equal(result.doors[0].testAppearance.visible, false);
});

test('moved and rotated regions project their native rectangle in cells without changing the authored region', () => {
    const source = { cellSize: 100, regions: [{ id: 'trigger', x: 1, y: 2, width: 3, height: 1, enabled: true }] };
    const result = projectTestDocument(source, { changes: { elements: [{ sourceId: 'trigger', after: { data: {
        enabled: false, geometry: { shape: 'rect', x: 300, y: 100, width: 100, height: 300 },
    } } }] } });
    assert.deepEqual(source.regions[0], { id: 'trigger', x: 1, y: 2, width: 3, height: 1, enabled: true });
    assert.deepEqual(result.regions[0], { id: 'trigger', x: 3, y: 1, width: 1, height: 3, enabled: false, testHidden: false, testRegion: true });
});

test('destroy rehearsal removes the native owner and its authoritative component deletions from a private visual copy', () => {
    const source = { cellSize: 100, decorations: [{ id: 'torch', torch: { state: 'on', lit: true, lightId: 'flame' } }, { id: 'other' }],
        lights: [{ id: 'flame', x: 1, y: 2 }, { id: 'room', x: 5, y: 5 }], particles: [{ id: 'sparks' }], shaders: [] };
    const before = structuredClone(source), result = { sourceIds: { nativeTorch: 'torch', nativeLight: 'flame', nativeEffect: 'sparks' }, changes: { elements: [
        { id: 'nativeTorch', sourceId: 'torch', before: { data: {} }, after: null },
        { id: 'nativeLight', before: { data: {} }, after: null },
        { id: 'nativeEffect', before: { data: {} }, after: null },
    ] } };
    const projected = projectTestDocument(source, result);
    assert.deepEqual(projected.decorations.map(item => item.id), ['other']);
    assert.deepEqual(projected.lights, source.lights.slice(1)); assert.deepEqual(projected.particles, []);
    assert.deepEqual(source, before, 'closing or resetting the test restores the untouched source document');
    assert.deepEqual(projectTestDocument(source, null), source);
});

test('deleting an area preview does not remove unrelated geometry or infer cascades absent from the engine result', () => {
    const source = { cellSize: 100, regions: [{ id: 'area', x: 1, y: 2, width: 3, height: 4 }],
        doors: [{ id: 'door', state: 'closed' }], decorations: [{ id: 'object' }], lights: [{ id: 'lamp', x: 1, y: 2 }] };
    const result = projectTestDocument(source, { changes: { elements: [{ sourceId: 'area', after: null }] } });
    assert.deepEqual(result.regions, []);
    assert.deepEqual(result.doors, source.doors); assert.deepEqual(result.decorations, source.decorations);
    assert.deepEqual(result.lights, source.lights);
});
