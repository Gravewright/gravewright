import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Texture } from 'pixi.js';
import { AnimatedLight, LightTexturePool } from '../lib/animated-light.js';
import { SceneLightMap } from '../lib/scene-light-map.js';
import { paintAnimatedLight } from '../../../features/lighting/model/light-profiles.js';

function recorder() {
    let state = { x: 0, y: 0, rotation: 0, alpha: 1 };
    const stack = [], draws = [];
    return {
        draws, reads: 0,
        save() { stack.push({ ...state }); },
        restore() { state = stack.pop(); },
        translate(x, y) {
            state.x += Math.cos(state.rotation) * x - Math.sin(state.rotation) * y;
            state.y += Math.sin(state.rotation) * x + Math.cos(state.rotation) * y;
        },
        rotate(value) { state.rotation += value; },
        get globalAlpha() { return state.alpha; },
        set globalAlpha(value) { state.alpha = value; },
        drawImage(source, x, y, width) { draws.push({ ...state, radius: width / 2 }); },
        beginPath() {}, moveTo() {}, lineTo() {}, closePath() {}, arc() {}, clip() {},
        setTransform() {}, clearRect() {}, scale() {}, putImageData() {},
        createImageData(w, h) { return { data: new Uint8ClampedArray(w * h * 4) }; },
        getImageData(x, y, w, h) {
            this.reads++;
            const data = new Uint8ClampedArray(w * h * 4);
            for (let i = 0; i < data.length; i += 4) data.set([128, 64, 0, 255], i);
            return { data };
        },
    };
}
const canvases = [];
globalThis.document = {
    createElement(tag) {
        assert.equal(tag, 'canvas');
        const canvas = { width: 0, height: 0, contexts: 0, context: recorder(), getContext() { this.contexts++; return this.context; } };
        canvases.push(canvas);
        return canvas;
    },
};
const textures = { get() { return Texture.EMPTY; } };
const base = { id: 'torch-42', x: 80, y: 60, color: '#ff9a3c', intensity: .9, bright_radius: 2, dim_radius: 5, angle: 360 };
function close(actual, expected, name) { assert.ok(Math.abs(actual - expected) < 1e-8, `${name}: ${actual} != ${expected}`); }

test('GPU flame, pulse and steady layers preserve the canvas profile over time and radii', () => {
    for (const animation of ['torch', 'candle', 'fire', 'pulse', 'none', '', 'unknown']) {
        for (const [id, bright_radius, dim_radius, radius] of [
            ['torch-42', 2, 5, 500], ['other-phase', 0, 4, 28], ['unicode-\u706b\ud83d\udd25', 3, 0, 7211],
        ]) {
            const light = { ...base, animation, id, bright_radius, dim_radius };
            const gpu = new AnimatedLight(light, radius, textures);
            assert.equal(gpu.node.x, light.x);
            assert.equal(gpu.node.y, light.y);
            for (const now of [0, 17, 620, 1300, 2800, 12345, 900000]) {
                const cpu = recorder();
                paintAnimatedLight(cpu, light, 0, 0, radius, now);
                gpu.update(now);
                assert.equal(gpu.node.children.length, cpu.draws.length);
                cpu.draws.forEach((draw, index) => {
                    const sprite = gpu.node.children[index];
                    close(sprite.x, draw.x, 'x');
                    close(sprite.y, draw.y, 'y');
                    close(sprite.width / 2, draw.radius, 'radius');
                    close(Math.sin(sprite.rotation), Math.sin(draw.rotation), 'rotation');
                    close(Math.cos(sprite.rotation), Math.cos(draw.rotation), 'rotation');
                    close(sprite.alpha, draw.alpha, 'alpha');
                    assert.equal(sprite.blendMode, 'add');
                });
            }
            gpu.node.destroy({ children: true });
        }
    }
});

test('animating existing GPU lights reuses sprites and never paints or updates a texture', () => {
    let requested = 0, updated = 0;
    const gpu = new AnimatedLight({ ...base, animation: 'torch' }, 500, { get() { requested++; return Texture.EMPTY; } });
    const sprites = [...gpu.node.children], created = canvases.length;
    const onUpdate = () => updated++;
    Texture.EMPTY.source.on('update', onUpdate);
    try {
        for (let frame = 0; frame < 600; frame++) gpu.update(frame * 1000 / 30);
        assert.deepEqual(gpu.node.children, sprites);
        assert.equal(requested, 3);
        assert.equal(updated, 0);
        assert.equal(canvases.length, created);
    }
    finally {
        Texture.EMPTY.source.off('update', onUpdate);
        gpu.node.destroy({ children: true });
    }
});

test('matching lights share textures within one board while different boards dispose independently', () => {
    const previous = Texture.from, created = [];
    Texture.from = (canvas, skipCache) => {
        assert.equal(skipCache, true);
        const texture = { canvas, destroyed: false, destroy(source) { assert.equal(source, true); this.destroyed = true; } };
        created.push(texture);
        return texture;
    };
    try {
        const first = new LightTexturePool(), second = new LightTexturePool();
        const texture = first.get(base.color, true);
        assert.equal(first.get(base.color, true), texture);
        const other = second.get(base.color, true);
        assert.notEqual(other, texture);
        assert.equal(created.length, 2);
        first.dispose();
        assert.equal(texture.destroyed, true);
        assert.equal(other.destroyed, false);
        second.dispose();
        assert.equal(other.destroyed, true);
    }
    finally { Texture.from = previous; }
});

function stamps(count = 1) {
    return Array.from({ length: count }, (_, index) => ({
        light: { ...base, id: `torch-${index}`, animation: 'torch' }, x: base.x, y: base.y, radius: 500,
        polygon: [{ x: 0, y: 0 }, { x: 1000, y: 0 }, { x: 1000, y: 1000 }, { x: 0, y: 1000 }],
    }));
}

test('shader light atlas reuses GPU nodes and has no Canvas work or texture uploads per frame', () => {
    const renders = [];
    const map = new SceneLightMap(7000, 5000, 512, .2, { textures, renderToTexture: (scene, target) => renders.push({ scene, target, nodes: [...scene.children] }) });
    const lights = stamps(30), canvas = map.canvas;
    let uploads = 0;
    map.texture.source.on('update', () => uploads++);
    for (let i = 0; i < 12; i++) map.update(lights, false, i * 1000 / 30);
    assert.equal(renders.length, 12);
    assert.equal(renders[0].nodes.length, 30);
    assert.deepEqual(renders.at(-1).nodes, renders[0].nodes);
    assert.equal(renders[0].target, map.texture);
    close(renders[0].scene.scale.x, 512 / 7000, 'atlas scale');
    assert.equal(canvas.width, 512);
    assert.equal(canvas.height, 366);
    assert.equal(canvas.contexts, 0);
    assert.equal(uploads, 0);
    map.dispose();
    assert.equal(renders[0].scene.destroyed, true);
    assert.equal(map.texture.destroyed, true);
    assert.equal(canvas.width, 1);
});

test('responsive particles sample separately at most eight times per second with existing tint semantics', () => {
    let renders = 0;
    const map = new SceneLightMap(1000, 1000, 32, .2, { textures, renderToTexture: () => renders++ });
    const lights = stamps();
    for (const now of [0, 33, 66, 99, 124, 125]) map.update(lights, true, now);
    assert.equal(renders, 6);
    assert.equal(map.canvas.context.reads, 2);
    assert.equal(map.canvas.context.draws.length, 6);
    assert.equal(map.tint('#ffffff', 20, 30, 0), 0xffffff);
    const expected = [128, 64, 0].reduce((value, channel, index) => value | Math.round(Math.pow(.2 + channel / 255, 1 / 2.2) * 255) << (16 - index * 8), 0);
    assert.equal(map.tint('#ffffff', 20, 30, 1), expected);
    assert.equal(map.tint('#ffffff', -100, 9000, 1), expected);
    map.update(lights, false, 130);
    assert.equal(map.tint('#ffffff', 20, 30, 1), 0xffffff);
    assert.equal(map.canvas.context.reads, 2);
    map.dispose();
});

test('scenes without shaders allocate no GPU atlas and sample only when particles request it', () => {
    let renders = 0, requested = 0, destroyed = 0;
    const previous = Texture.EMPTY.destroy;
    Texture.EMPTY.destroy = () => destroyed++;
    try {
        const map = new SceneLightMap(7000, 5000, 512, .2, {
            sampleOnly: true,
            renderToTexture() { renders++; },
            textures: { get() { requested++; return Texture.EMPTY; } },
        });
        const lights = stamps(30);
        map.update(lights, false, 0);
        assert.equal(map.texture, Texture.EMPTY);
        assert.equal(map.canvas.contexts, 0);
        assert.equal(renders, 0);
        assert.equal(requested, 0);
        map.update(lights, true, 1);
        map.update(lights, true, 100);
        assert.equal(map.canvas.context.reads, 1);
        assert.equal(renders, 0);
        assert.equal(requested, 0);
        map.dispose();
        assert.equal(destroyed, 0);
    }
    finally { Texture.EMPTY.destroy = previous; }
});

test('non-GPU boards paint directly into one bounded fallback atlas', () => {
    const previous = Texture.from;
    let uploads = 0, destroyed = false;
    const fallback = { source: { update() { uploads++; } }, destroy() { destroyed = true; } };
    Texture.from = () => fallback;
    try {
        const map = new SceneLightMap(7000, 5000, 256, .2);
        const lights = stamps(3);
        map.update(lights, false, 0);
        map.update(lights, true, 130);
        assert.equal(uploads, 2);
        assert.equal(map.canvas.context.draws.length, 18);
        assert.equal(map.canvas.context.reads, 1);
        assert.equal(map.canvas.width, 256);
        map.dispose();
        assert.equal(destroyed, true);
    }
    finally { Texture.from = previous; }
});
