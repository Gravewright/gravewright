import test from 'node:test';
import assert from 'node:assert/strict';
import { resizeImage } from './image-transform.js';

const image = { id: 'image', version: 3, x: 100, y: 200, natural_width: 400,
    natural_height: 200, scale: 0.5, rotation: 0 };
const near = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-8, `${actual} != ${expected}`);
function anchor(image, corner) {
    const angle = image.rotation * Math.PI / 180;
    const x = corner.x * image.natural_width * image.scale / 2;
    const y = corner.y * image.natural_height * image.scale / 2;
    return { x: image.x - x * Math.cos(angle) + y * Math.sin(angle),
        y: image.y - x * Math.sin(angle) - y * Math.cos(angle) };
}

test('dragging any corner keeps proportions and fixes the opposite corner, including rotation', () => {
    for (const rotation of [0, 30, 90, 235]) for (const x of [-1, 1]) for (const y of [-1, 1]) {
        const original = { ...image, rotation }, corner = { x, y };
        const angle = rotation * Math.PI / 180;
        const dx = x * 200, dy = y * 100;
        const start = { x: 60, y: 90 };
        const result = resizeImage(original, corner, start, {
            x: start.x + dx * Math.cos(angle) - dy * Math.sin(angle),
            y: start.y + dx * Math.sin(angle) + dy * Math.cos(angle),
        });
        near(result.scale, 1);
        near(anchor(result, corner).x, anchor(original, corner).x);
        near(anchor(result, corner).y, anchor(original, corner).y);
        assert.equal(result.version, 3);
        assert.equal(original.scale, 0.5);
    }
});

test('shrinking and crossing the fixed corner never flips the image or exceeds server limits', () => {
    const corner = { x: 1, y: 1 }, start = { x: 0, y: 0 };
    const smaller = resizeImage(image, corner, start, { x: -100, y: -50 });
    near(smaller.scale, 0.25);
    for (const [distance, expected] of [[-1e9, 0.001], [1e9, 100], [0, 0.5]]) {
        const result = resizeImage(image, corner, start, { x: distance, y: distance });
        near(result.scale, expected);
        near(anchor(result, corner).x, anchor(image, corner).x);
        near(anchor(result, corner).y, anchor(image, corner).y);
    }
});

test('tiny and large state images retain their exact lever box scale during native resizing', () => {
    const corner = { x: 1, y: 1 }, start = { x: 0, y: 0 };
    for (const [natural_width, natural_height, scale] of [[1, 1, 192], [32768, 32768, 64 / 32768 / 8], [16, 32, 2]]) {
        const lever = { ...image, natural_width, natural_height, scale,
            lever: { state: 'on', width: natural_width * scale, height: natural_height * scale * 2 } };
        const still = resizeImage(lever, corner, start, start);
        assert.equal(still.scale, scale, 'starting a resize must not jump to the ordinary image limit');
        const resized = resizeImage(lever, corner, start, { x: natural_width * scale, y: natural_height * scale });
        near(resized.scale, scale * 2);
        near(anchor(resized, corner).x, anchor(lever, corner).x);
        near(anchor(resized, corner).y, anchor(lever, corner).y);
        assert.deepEqual(resized.lever, lever.lever, 'the server owns changes to the authored box');
    }
});

test('lever resize limits constrain both authored dimensions, including space around state art', () => {
    const corner = { x: -1, y: 1 }, start = { x: 0, y: 0 };
    for (const [boxWidth, boxHeight] of [[192, 384], [400, 200], [.001, 1e6], [1e6, .001]]) {
        const lever = { ...image, natural_width: 1, natural_height: 1, scale: Math.min(boxWidth, boxHeight),
            lever: { state: 'on', width: boxWidth, height: boxHeight } };
        for (const distance of [-1e15, 1e15]) {
            const resized = resizeImage(lever, corner, start, { x: -distance, y: distance });
            const ratio = resized.scale / lever.scale;
            assert.ok(boxWidth * ratio >= .001 && boxHeight * ratio >= .001);
            assert.ok(boxWidth * ratio <= 1e6 && boxHeight * ratio <= 1e6);
            assert.ok(resized.scale >= 1e-12 && resized.scale <= 1e6);
            near(anchor(resized, corner).x, anchor(lever, corner).x);
            near(anchor(resized, corner).y, anchor(lever, corner).y);
        }
    }
});

test('torch artwork uses the composed authored box while preserving independent state and component references', () => {
    const original = { ...image, natural_width: 1, natural_height: 1, scale: 192,
        torch: { state: 'on', lit: false, width: 192, height: 384, components: { lights: { id: 'light' } } } };
    const corner = { x: 1, y: 1 }, start = { x: 0, y: 0 };
    assert.equal(resizeImage(original, corner, start, start).scale, 192);
    const resized = resizeImage(original, corner, start, { x: 192, y: 192 });
    near(resized.scale, 384);
    near(anchor(resized, corner).x, anchor(original, corner).x);
    near(anchor(resized, corner).y, anchor(original, corner).y);
    assert.deepEqual(resized.torch, original.torch);
});
