import test from 'node:test';
import assert from 'node:assert/strict';
import { Container, Texture, TextureSource } from 'pixi.js';
import { SceneLayers } from '../lib/scene-layers.js';

const settle = () => new Promise(resolve => setImmediate(resolve));
const placement = { id: 'surface', src: '/surface', x: 30, y: 40, scale: 1, rotation: 0,
    z_index: 0, layer: 'game', surface: { materialId: 'material', maskId: 'mask' } };
const state = { containerId: 'table', blockId: 'block', sceneId: 'scene', images: [placement],
    walls: [], lights: [], particles: [], shaders: [], cards: [], zones: [], drawings: { rows: [] },
    spatialSounds: [], lighting: { mode: 'manual', darkness: 0 }, fog: { enabled: false }, vision: [] };

function fixture() {
    const originals = Object.fromEntries(['document', 'HTMLCanvasElement', 'requestAnimationFrame',
        'cancelAnimationFrame'].map(key => [key, globalThis[key]]));
    class Canvas {
        width = 64;
        height = 64;
        getContext() { return { createRadialGradient: () => ({ addColorStop() {} }), fillRect() {} }; }
    }
    globalThis.HTMLCanvasElement = Canvas;
    globalThis.document = { createElement: () => new Canvas(), hidden: false };
    globalThis.requestAnimationFrame = () => 1;
    globalThis.cancelAnimationFrame = () => {};
    const containers = [];
    const layers = new SceneLayers({
        invalidate() {},
        createLayer(id) {
            const container = new Container();
            containers.push({ id, container });
            return { native: () => ({ container }), dispose: () => container.destroy({ children: true }) };
        },
    });
    const loads = [];
    layers.surfaceArt = () => new Promise(resolve => loads.push(resolve));
    const resource = () => ({ texture: new Texture({ source: new TextureSource({ width: 64, height: 64 }) }),
        canvas: new Canvas(), bytes: 64 * 64 * 4 });
    return { layers, loads, containers, resource, restore() {
        layers.dispose();
        for (const [key, value] of Object.entries(originals)) {
            if (value === undefined) delete globalThis[key];
            else globalThis[key] = value;
        }
    } };
}

test('a stale decoded surface cannot replace current scene art after a rebuild', async () => {
    const f = fixture();
    try {
        f.layers.render(state, 70, 300, 300, true);
        await settle();
        f.layers.render({ ...state, images: [{ ...placement, src: '/new-surface' }],
            lighting: { ...state.lighting, darkness: .5 } }, 70, 300, 300, true);
        await settle();
        const current = f.containers.filter(row => row.id === 'native:images').at(-1).container;
        f.loads[1](f.resource());
        await settle();
        const sprite = current.children[0];
        assert.ok(sprite);
        f.loads[0](f.resource());
        await settle();
        f.layers.previewImage({ ...placement, x: 100 });
        assert.equal(sprite.x, 100, 'the live sprite remains registered after old decode completion');
        assert.equal(current.children.length, 1);
    } finally { f.restore(); }
});

test('a surface decoded during an image drag keeps the active preview position', async () => {
    const f = fixture();
    try {
        f.layers.render(state, 70, 300, 300, true);
        await settle();
        f.layers.previewImage({ ...placement, x: 100, y: 120, rotation: 30 });
        f.loads[0](f.resource());
        await settle();
        const current = f.containers.find(row => row.id === 'native:images').container;
        const sprite = current.children[0];
        assert.equal(sprite.x, 100);
        assert.equal(sprite.y, 120);
        assert.ok(Math.abs(sprite.angle - 30) < .000001);
        f.layers.previewImage(undefined);
        assert.equal(sprite.x, placement.x);
        assert.equal(sprite.y, placement.y);
    } finally { f.restore(); }
});

test('token previews retain image art and transforms until an image snapshot changes', async () => {
    const f = fixture();
    try {
        f.layers.render(state, 70, 300, 300, true);
        await settle();
        f.loads[0](f.resource());
        await settle();
        const imageLayer = f.containers.find(row => row.id === 'native:images').container;
        const sprite = imageLayer.children[0];
        let synced = 0;
        const sync = f.layers.syncImages;
        f.layers.syncImages = function (...args) { synced++; return sync.apply(this, args); };
        for (let x = 0; x < 20; x++)
            f.layers.render({ ...state, vision: [{ x, y: 10, radius: 50 }] }, 70, 300, 300, true);
        assert.equal(synced, 0, 'moving a token does not reconcile every image again');
        assert.equal(imageLayer.children[0], sprite, 'the mounted floor remains intact');
        f.layers.render({ ...state, images: [{ ...placement, x: 125 }] }, 70, 300, 300, true);
        assert.equal(synced, 1, 'an actual image snapshot still updates its transform');
        assert.equal(sprite.x, 125);
        assert.equal(imageLayer.children.length, 1);
    } finally { f.restore(); }
});
