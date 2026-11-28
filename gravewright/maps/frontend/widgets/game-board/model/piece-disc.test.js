import assert from 'node:assert/strict';
import test from 'node:test';
import { DISC_SEGMENTS, pieceDisc } from './piece-disc.js';

const area = ({ positions, indices }) => {
    let total = 0;
    for (let i = 0; i < indices.length; i += 3) {
        const [a, b, c] = [indices[i], indices[i + 1], indices[i + 2]].map(index => [positions[index * 2], positions[index * 2 + 1]]);
        total += ((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2;
    }
    return total;
};
const vertices = disc => disc.positions.length / 2;
// Map a local point through the former sprite transform: rotate into art space, then normalize.
const spriteUv = (x, y, width, height, degrees) => {
    const t = degrees * Math.PI / 180;
    return [(x * Math.cos(t) + y * Math.sin(t)) / width + .5, (-x * Math.sin(t) + y * Math.cos(t)) / height + .5];
};

test('square art fills the whole disc and stays within the batching limit', () => {
    const disc = pieceDisc(35, 35, 70, 70);
    assert.equal(vertices(disc), DISC_SEGMENTS);
    assert.ok(vertices(disc) <= 100);
    const polygon = DISC_SEGMENTS / 2 * 35 * 35 * Math.sin(2 * Math.PI / DISC_SEGMENTS);
    assert.ok(Math.abs(area(disc) - polygon) < 1e-3, 'counter-clockwise fan covering the ellipse polygon');
    for (let i = 0; i < disc.uvs.length; i++) assert.ok(disc.uvs[i] >= -1e-6 && disc.uvs[i] <= 1 + 1e-6);
});

test('UVs reproduce the rotated sprite and portrait art is clipped like the mask did', () => {
    for (const degrees of [0, 30, 90, 211]) {
        const disc = pieceDisc(40, 25, 40, 80, degrees);
        assert.ok(vertices(disc) <= 100);
        for (let i = 0; i < vertices(disc); i++) {
            const x = disc.positions[i * 2], y = disc.positions[i * 2 + 1];
            const [u, v] = spriteUv(x, y, 40, 80, degrees);
            assert.ok(Math.abs(disc.uvs[i * 2] - u) < 1e-5 && Math.abs(disc.uvs[i * 2 + 1] - v) < 1e-5);
            assert.ok(u >= -1e-5 && u <= 1 + 1e-5 && v >= -1e-5 && v <= 1 + 1e-5, 'never samples outside the art');
            assert.ok((x / 40) ** 2 + (y / 25) ** 2 <= 1 + 1e-5, 'never draws outside the token ellipse');
        }
    }
    const upright = pieceDisc(40, 40, 40, 80);
    assert.ok(Math.abs(area(upright) - area(pieceDisc(40, 40, 80, 80))) > 100, 'the narrow art leaves the sides empty');
});

test('degenerate sizes produce no geometry', () => {
    for (const disc of [pieceDisc(0, 10, 10, 10), pieceDisc(10, 10, 0, 10), pieceDisc(10, 10, 10, Number.NaN)])
        assert.deepEqual([disc.positions.length, disc.uvs.length, disc.indices.length], [0, 0, 0]);
});
