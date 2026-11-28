import test from 'node:test';
import assert from 'node:assert/strict';
import { Container } from 'pixi.js';
import { SceneLayers } from '../lib/scene-layers.js';

const door = state => ({ id: 'door', x1: 220, y1: 100, x2: 220, y2: 300, door_state: state, kind: 'door' });
const stroke = (id, x) => ({ id, kind: 'pen', points: [{ x, y: 10 }, { x: x + 30, y: 40 }], color: '#ffffff',
    width: 3, opacity: 1, fill: 'none', audience: 'campaign' });
const base = { containerId: 'table', blockId: 'block', sceneId: 'scene', images: [], zones: [],
    walls: [door('closed'), { id: 'far', x1: 1500, y1: 900, x2: 1600, y2: 900 }],
    lights: [{ id: 'near', x: 150, y: 200, enabled: true, color: '#ffc36b', intensity: 1, bright_radius: 2,
        dim_radius: 4, angle: 360, rotation: 0, animation: 'torch' },
    { id: 'far', x: 1700, y: 300, enabled: true, color: '#88aaff', intensity: 1, bright_radius: 1,
        dim_radius: 2, angle: 360, rotation: 0, animation: 'none' }],
    particles: [{ id: 'embers', enabled: true, x: 400, y: 400, kind: 'ember', density: 1, scale: 1 }],
    shaders: [], cards: [{ id: 'card', x: 300, y: 300, rotation: 0, scale: 1, z_index: 0, card: {} }],
    drawings: { rows: [stroke('a', 20)] }, spatialSounds: [], lighting: { mode: 'dynamic', darkness: .6, lights_out: true },
    fog: { enabled: false }, vision: [] };

const context = () => new Proxy({}, { get(target, name) {
    if (name in target) return target[name];
    if (name === 'createImageData') return (w, h) => ({ data: new Uint8ClampedArray(w * h * 4) });
    if (name === 'getImageData') return (x, y, w, h) => ({ data: new Uint8ClampedArray(w * h * 4) });
    if (name === 'createRadialGradient') return () => ({ addColorStop() {} });
    return () => {};
} });
// One class for the whole file: light falloff canvases are cached across scenes.
class Canvas { width = 64; height = 64; #context = context(); getContext() { return this.#context; } }

function fixture() {
    const originals = Object.fromEntries(['document', 'HTMLCanvasElement', 'requestAnimationFrame',
        'cancelAnimationFrame'].map(key => [key, globalThis[key]]));
    globalThis.HTMLCanvasElement = Canvas;
    globalThis.document = { createElement: () => new Canvas(), hidden: false };
    globalThis.requestAnimationFrame = () => 1;
    globalThis.cancelAnimationFrame = () => {};
    const created = [];
    const layers = new SceneLayers({
        invalidate() {},
        createLayer(id) {
            const container = new Container();
            created.push({ id, container });
            return { native: () => ({ container }), dispose: () => container.destroy({ children: true }) };
        },
    });
    const layer = id => created.filter(row => row.id === `native:${id}`).at(-1).container;
    return { layers, created, layer, render: state => layers.render(state, 50, 2000, 1200, true), restore() {
        layers.dispose();
        for (const [key, value] of Object.entries(originals)) {
            if (value === undefined) delete globalThis[key];
            else globalThis[key] = value;
        }
    } };
}

test('drawings, cards and sounds refresh only their own layer', () => {
    const f = fixture();
    try {
        f.render(base);
        const layerCount = f.created.length;
        const lights = [...f.layer('lights').children], particles = [...f.layer('particles').children];
        assert.equal(lights.length, 2);
        const firstStroke = f.layer('drawings').children[0];
        f.render({ ...base, drawings: { rows: [stroke('a', 20), stroke('b', 90)] } });
        assert.equal(f.created.length, layerCount, 'a new stroke mounts no layer');
        assert.deepEqual(f.layer('lights').children, lights, 'lights are untouched');
        assert.deepEqual(f.layer('particles').children, particles, 'particles are untouched');
        assert.equal(f.layer('drawings').children.length, 2);
        assert.equal(f.layer('drawings').children[0], firstStroke, 'the existing stroke is retained');
        const card = f.layer('cards').children[0];
        const moved = { ...base, drawings: { rows: [stroke('a', 20), stroke('b', 90)] },
            cards: [{ ...base.cards[0], x: 420, rotation: 90 }] };
        f.render(moved);
        assert.equal(f.layer('cards').children[0], card, 'a moved card keeps its node');
        assert.equal(card.x, 420);
        assert.equal(card.angle, 90);
        f.render({ ...moved, spatialSounds: [{ id: 'rain', x: 10, y: 10, radius: 300 }] });
        assert.equal(f.created.length, layerCount);
        assert.deepEqual(f.layer('lights').children, lights, 'a spatial sound changes nothing visual');
        f.render({ ...moved, drawings: { rows: [stroke('b', 90)] } });
        assert.equal(firstStroke.destroyed, true, 'a removed stroke is released');
        assert.equal(f.layer('drawings').children.length, 1);
    } finally { f.restore(); }
});

test('a door rebuilds lights from cached polygons without remounting other layers', () => {
    const f = fixture();
    try {
        f.render(base);
        const layerCount = f.created.length;
        const stroke = f.layer('drawings').children[0], card = f.layer('cards').children[0];
        const particles = [...f.layer('particles').children];
        const reach = () => f.layer('lights').children.map(group => Math.round(group.children[0].bounds.maxX));
        const masks = reach();
        assert.ok(masks[0] < 300, `the closed door stops the near light (${masks[0]})`);
        f.render({ ...base, walls: [door('open'), base.walls[1]] });
        assert.equal(f.created.length, layerCount);
        assert.equal(f.layer('drawings').children[0], stroke);
        assert.equal(f.layer('cards').children[0], card);
        assert.deepEqual(f.layer('particles').children, particles);
        const after = reach();
        assert.equal(after[0], 350, 'the opened door lets the near light reach its full radius');
        assert.equal(after[1], masks[1], 'the distant light keeps its polygon');
    } finally { f.restore(); }
});

test('a different scene, role or size remounts every layer', () => {
    const f = fixture();
    try {
        f.render(base);
        const layerCount = f.created.length;
        f.render({ ...base, sceneId: 'other' });
        assert.equal(f.created.length, layerCount * 2);
        f.layers.render({ ...base, sceneId: 'other' }, 50, 2000, 1200, false);
        assert.equal(f.created.length, layerCount * 3);
    } finally { f.restore(); }
});
