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
