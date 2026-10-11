import test from 'node:test';
import assert from 'node:assert/strict';
import {previewBoardImage} from './image-preview.js';

test('current board previews and cancels without rebuilding the scene', () => {
    const calls = [], image = {id: 'image', scale: 2};
    const board = {previewImage(value) {calls.push(value);}, update() {assert.fail('Scene rebuild');}};
    previewBoardImage(board, {}, image);
    previewBoardImage(board, {});
    assert.deepEqual(calls, [image, undefined]);
});

test('cached board supports resizing and restoring without changing the saved snapshot', () => {
    const image = {id: 'image', scale: 1}, other = {id: 'other', scale: 3};
    const state = {images: [image, other], walls: []}, calls = [];
    const board = {update(value) {calls.push(value.state);}};
    previewBoardImage(board, state, {...image, scale: 2});
    previewBoardImage(board, state);
    assert.equal(calls[0].images[0].scale, 2);
    assert.equal(calls[0].images[1], other);
    assert.equal(calls[0].walls, state.walls);
    assert.equal(calls[1], state);
    assert.equal(state.images[0].scale, 1);
});
