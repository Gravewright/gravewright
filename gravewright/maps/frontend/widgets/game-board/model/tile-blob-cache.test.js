import { test } from 'node:test';
import assert from 'node:assert/strict';
import { TileBlobCache } from './tile-blob-cache.js';
import { warmTiles } from '../lib/warm-tiles.js';
import { tileBlobCache } from './tile-blob-cache.js';
test('speculative blobs expire, obey byte budget and are consumed only once', () => {
    let now = 0;
    const cache = new TileBlobCache(5, () => now);
    cache.put('a', new Blob(['aaa']), 10);
    cache.put('b', new Blob(['bbb']), 10);
    assert.equal(cache.take('a'), undefined);
    assert.equal(cache.take('b')?.size, 3);
    assert.equal(cache.take('b'), undefined);
    cache.put('c', new Blob(['cc']), 10);
    now = 10;
    assert.equal(cache.take('c'), undefined);
    cache.put('large', new Blob(['123456']), 30);
    assert.equal(cache.has('large'), false);
    cache.put('d', new Blob(['d']), 30);
    cache.clear();
    assert.equal(cache.has('d'), false);
});
test('warming bounds concurrent requests and reuses no-store bytes without a second request', async () => {
    const original = globalThis.fetch;
    let active = 0, maximum = 0, calls = 0;
    globalThis.fetch = async (_url, options) => {
        assert.equal(options?.priority, 'low');
        active++;
        calls++;
        maximum = Math.max(maximum, active);
        await new Promise(resolve => setTimeout(resolve, 1));
        active--;
        return new Response('tile', { headers: { 'Cache-Control': 'private, no-store' } });
    };
    const manifest = { mapId: 'm', tileUrlTemplate: '/tiles/{lod}/{x}/{y}.webp', levels: [{ lod: 0, columns: 10, rows: 10 }] };
    const region = { mapId: 'm', lod: 0, firstColumn: 0, firstRow: 0, lastColumn: 9, lastRow: 9 };
    try {
        await warmTiles(manifest, region).done;
        assert.equal(calls, 24);
        assert.equal(maximum, 2);
        assert.equal(await tileBlobCache.take('/tiles/0/0/0.webp')?.text(), 'tile');
        assert.equal(calls, 24);
        const warming = warmTiles(manifest, region);
        warming.cancel();
        await warming.done;
        assert.equal(tileBlobCache.has('/tiles/0/0/0.webp'), false);
    }
    finally {
        globalThis.fetch = original;
        tileBlobCache.clear();
    }
});
