import test from 'node:test';
import assert from 'node:assert/strict';
import { isGMImage, imageInWorkspace, imageMarkerVisible, canMoveImageToGame } from './image-layer.js';
import { createInteractiveImageHitTest } from './lever-interaction.js';

const image = { id: 'art', layer: 'map', x: 100, y: 100, scale: 1, rotation: 0,
    natural_width: 70, natural_height: 70, z_index: 1, lever: { state: 'off' } };

test('moving ordinary images to GM and back keeps them selectable in their workspace', () => {
    for (const kind of [{}, { lever: { state: 'off' } }, { torch: { state: 'off', lit: true } }, { surface: { kind: 'floor' } }]) {
        const publicImage = { ...image, ...kind };
        for (const layer of ['gm', 'gm-image-layer']) {
            const privateImage = { ...publicImage, layer };
            assert.equal(isGMImage(privateImage), true);
            assert.equal(imageInWorkspace(privateImage, 'game'), false);
            assert.equal(imageInWorkspace(privateImage, 'composition'), false);
            assert.equal(imageInWorkspace(privateImage, 'gm'), true);
            assert.equal(canMoveImageToGame(privateImage), true);
            const restored = { ...privateImage, layer: 'map' };
            assert.equal(imageInWorkspace(restored, 'game'), true);
            assert.equal(imageInWorkspace(restored, 'composition'), true);
            assert.equal(imageInWorkspace(restored, 'gm'), false);
        }
    }
});

test('legacy Empty Objects remain private, with a faint GM marker across workspaces', () => {
    for (const layer of [undefined, 'map', 'game', 'gm', 'gm-image-layer']) {
        const empty = { ...image, empty: true, layer };
        assert.equal(isGMImage(empty), true);
        assert.equal(canMoveImageToGame(empty), false);
        for (const workspace of ['game', 'composition', 'effects', 'lighting', 'walls', 'audio', 'gm']) {
            assert.equal(imageInWorkspace(empty, workspace), workspace === 'gm');
            assert.equal(imageMarkerVisible(empty, workspace, true), true);
            assert.equal(imageMarkerVisible(empty, workspace, false), false);
        }
    }
});

test('private ordinary art stays visible only to the GM in every workspace', () => {
    for (const layer of ['gm', 'gm-image-layer']) for (const workspace of ['game', 'composition', 'gm']) {
        assert.equal(imageMarkerVisible({ ...image, layer }, workspace, true), true);
        assert.equal(imageMarkerVisible({ ...image, layer }, workspace, false), false);
        assert.equal(imageMarkerVisible(image, workspace, false), true);
    }
});

test('GM workspace hit tests cannot let private controllers cover public interactions in Game', () => {
    const privateImage = { ...image, id: 'private', layer: 'gm-image-layer', z_index: 10 };
    const empty = { ...image, id: 'empty', empty: true, z_index: 20 };
    const point = { x: 100, y: 100 };
    assert.equal(createInteractiveImageHitTest([image, privateImage, empty], true, 'game')(point), image);
    assert.equal(createInteractiveImageHitTest([image, privateImage], true, 'gm')(point), privateImage);
    assert.equal(createInteractiveImageHitTest([image, empty], true, 'gm')(point), empty);
    assert.equal(createInteractiveImageHitTest([image, privateImage, empty], false, 'game')(point), image);
    assert.equal(createInteractiveImageHitTest([empty], false, 'gm')(point), undefined);
});
