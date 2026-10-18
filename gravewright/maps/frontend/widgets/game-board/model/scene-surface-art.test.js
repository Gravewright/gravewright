import test from 'node:test';
import assert from 'node:assert/strict';
import { loadSurfaceArt, surfaceArtRows } from './scene-surface-art.js';
import { SceneImageArt } from './scene-image-art.js';

const placement = (extra = {}) => ({ id: 'paint', src: '/paint', x: 50, y: 50,
    natural_width: 40, natural_height: 40, scale: 1, rotation: 0, layer: 'game', z_index: 0,
    surface: { kind: 'floor', materialId: 'material', maskId: 'mask', cellSize: 40,
        left: 30, top: 30, rotation: 0 }, ...extra });
const grouped = (extra = {}) => placement({ surfacePlane: { group: 'floor', operation: 'paint', order: 0 }, ...extra });
const art = images => surfaceArtRows(images, 300, 300);
const deferred = () => {
    let resolve;
    const promise = new Promise(done => { resolve = done; });
    return { promise, resolve };
};
const settle = () => new Promise(resolve => setImmediate(resolve));

function fixture(responses = {}) {
    const originals = Object.fromEntries(['document', 'DOMMatrix', 'fetch', 'createImageBitmap']
        .map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
    const requests = [], decodes = [], bitmaps = [], canvases = [];
    class Canvas {
        width = 0;
        height = 0;
        calls = [];
        getContext() {
            return { save() {}, restore() {}, translate() {}, rotate() {}, scale() {}, fillRect() {},
                drawImage: (...args) => this.calls.push(args),
                createPattern: () => ({ setTransform() {} }) };
        }
    }
    globalThis.document = { createElement(name) {
        assert.equal(name, 'canvas');
        const canvas = new Canvas(); canvases.push(canvas); return canvas;
    } };
    globalThis.DOMMatrix = class { translate() { return this; } };
    globalThis.fetch = async (url, options) => {
        requests.push({ url, options });
        const response = responses[url] ?? {};
        return { ok: response.status === undefined || response.status < 400,
            status: response.status ?? 200, blob: async () => ({ url }) };
    };
    globalThis.createImageBitmap = async ({ url }) => {
        decodes.push(url);
        const response = responses[url] ?? {};
        if (response.decode) await response.decode.promise;
        const bitmap = { width: 40, height: 40, url, closes: 0, close() { this.closes++; } };
        bitmaps.push(bitmap);
        return bitmap;
    };
    return { requests, decodes, bitmaps, canvases, restore() {
        for (const [key, descriptor] of Object.entries(originals)) {
            if (descriptor) Object.defineProperty(globalThis, key, descriptor);
            else delete globalThis[key];
        }
    } };
}

test('surface finish changes retain identity while invalidating composed artwork', () => {
    for (const row of [placement(), grouped()]) {
        const [original] = art([row]);
        const [changed] = art([{ ...row, surface: { ...row.surface, materialId: 'new-material' } }]);
        assert.equal(changed.id, original.id, 'the previous finish can remain visible until its replacement loads');
        assert.notEqual(changed.src, original.src);
        const [source] = art([{ ...row, src: '/new-source' }]);
        assert.equal(source.id, original.id);
        assert.notEqual(source.src, original.src);
    }
});

test('coverage, stacking and private layer changes revoke the previous surface identity', () => {
    for (const row of [placement(), grouped()]) {
        const [original] = art([row]);
        const variants = [
            { ...row, x: 70 }, { ...row, y: 70 }, { ...row, rotation: 90 }, { ...row, scale: 2 },
            { ...row, natural_width: 60 }, { ...row, natural_height: 60 }, { ...row, z_index: 1 },
            { ...row, layer: 'gm-image-layer' },
            { ...row, surface: { ...row.surface, maskId: 'new-mask' } },
        ];
        if (row.surfacePlane) variants.push(
            { ...row, surfacePlane: { ...row.surfacePlane, order: 1 } },
            { ...row, surfacePlane: { ...row.surfacePlane, operation: 'erase' } });
        for (const variant of variants) {
            const [changed] = art([variant]);
            assert.notEqual(changed.id, original.id, 'obsolete coverage cannot be used as replacement fallback');
            if (row.surfacePlane || variant.surface.maskId !== row.surface.maskId) {
                assert.notEqual(changed.src, original.src, 'composite coverage and masks require new pixels');
            } else {
                assert.equal(changed.src, original.src, 'a standalone transform reuses its decoded surface pixels');
            }
        }
    }
});

test('group membership and clipping bounds form part of its surface identity', () => {
    const row = grouped(), eraser = grouped({ id: 'eraser', x: 65,
        surfacePlane: { group: 'floor', operation: 'erase', order: 1 } });
    const [single] = art([row]), [multiple] = art([row, eraser]);
    assert.notEqual(single.id, multiple.id, 'removing an eraser never retains its previous composite');
    assert.notEqual(multiple.id, art([row, { ...eraser, id: 'replacement' }])[0].id);
    const clipped = surfaceArtRows([row], 60, 60)[0];
    assert.notEqual(clipped.id, single.id);
    assert.deepEqual(art([{ ...row, empty: true }, placement({ id: 'ordinary', surface: undefined })]), []);
});

test('a successful composed surface closes its decoded inputs and owns a separate canvas', async () => {
    const f = fixture();
    try {
        const [row] = art([grouped(), grouped({ id: 'second', x: 100 })]);
        const signal = new AbortController().signal;
        const resource = await loadSurfaceArt(row.src, signal);
        assert.equal(f.requests.length, 2, 'shared material and mask decode once per composition');
        assert.ok(f.requests.every(request => request.options.signal === signal
            && request.options.credentials === 'same-origin'));
        assert.equal(f.bitmaps.length, 2);
        assert.ok(f.bitmaps.every(bitmap => bitmap.closes === 1));
        assert.equal(resource.bytes, resource.canvas.width * resource.canvas.height * 4);
        assert.equal(resource.canvas.calls.length, 2, 'both paint rows are composed into the final canvas');
        assert.ok(f.canvases.includes(resource.canvas));
    } finally { f.restore(); }
});

test('a failed material waits for and closes a delayed sibling mask decoder', async () => {
    const mask = deferred();
    const f = fixture({ '/game/map-assets/material': { status: 503 },
        '/game/map-assets/mask': { decode: mask } });
    try {
        let completed = false;
        const pending = loadSurfaceArt(art([placement()])[0].src, new AbortController().signal);
        const rejected = assert.rejects(pending, /Unable to load surface artwork \(503\)/);
        pending.then(() => { completed = true; }, () => { completed = true; });
        await settle();
        assert.deepEqual(f.decodes, ['/game/map-assets/mask']);
        assert.equal(completed, false, 'cleanup waits for the sibling that may still return a bitmap');
        mask.resolve();
        await rejected;
        assert.equal(f.bitmaps.length, 1);
        assert.equal(f.bitmaps[0].closes, 1);
        assert.equal(f.canvases.length, 0, 'failed inputs never publish a partial surface');
    } finally { mask.resolve(); f.restore(); }
});

test('a failed group input rejects the entire composite and closes all successful inputs', async () => {
    const f = fixture({ '/broken': { status: 404 } });
    try {
        const rows = [grouped({ surface: undefined }), grouped({ id: 'broken', src: '/broken', surface: undefined })];
        await assert.rejects(loadSurfaceArt(art(rows)[0].src, new AbortController().signal), /404/);
        assert.equal(f.bitmaps.length, 1);
        assert.equal(f.bitmaps[0].closes, 1);
        assert.equal(f.canvases.length, 0);
    } finally { f.restore(); }
});

test('aborting during decoding closes the late bitmap without allocating a canvas', async () => {
    const decode = deferred(), controller = new AbortController();
    const f = fixture({ '/paint': { decode } });
    try {
        const source = art([placement({ surface: { kind: 'floor' } })])[0].src;
        const rejected = assert.rejects(loadSurfaceArt(source, controller.signal), /cancelled/);
        await settle();
        assert.deepEqual(f.decodes, ['/paint']);
        controller.abort();
        decode.resolve();
        await rejected;
        assert.equal(f.bitmaps[0].closes, 1);
        assert.equal(f.canvases.length, 0);
    } finally { decode.resolve(); f.restore(); }
});

test('superseded surface decoding cannot replace newer art and closes every bitmap', async () => {
    const decode = deferred(), f = fixture({ '/paint': { decode } }), applied = [];
    const cache = new SceneImageArt({ load: loadSurfaceArt,
        apply: (_id, resource) => applied.push(resource.canvas), remove() {}, release() {} });
    try {
        const [original] = art([placement({ surface: { kind: 'floor' } })]);
        const [next] = art([placement({ src: '/replacement', surface: { kind: 'floor' } })]);
        cache.sync([original]);
        await settle();
        cache.sync([next]);
        await settle();
        assert.equal(f.requests[0].options.signal.aborted, true);
        assert.equal(applied.length, 1);
        assert.equal(applied[0].calls[0][0].url, '/replacement');
        decode.resolve();
        await settle();
        assert.equal(applied.length, 1);
        assert.equal(f.bitmaps.length, 2);
        assert.ok(f.bitmaps.every(bitmap => bitmap.closes === 1));
    } finally { cache.reset(); decode.resolve(); f.restore(); }
});
