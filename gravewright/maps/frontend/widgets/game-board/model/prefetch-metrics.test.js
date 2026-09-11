import { test } from 'node:test';
import assert from 'node:assert/strict';
import { observed, metrics, prefetchSnapshot } from './prefetch-metrics.js';
import { TileBlobCache } from './tile-blob-cache.js';
import { warmTiles } from '../lib/warm-tiles.js';
import { tileBlobCache } from './tile-blob-cache.js';
test('actual tile bytes distinguish useful, expired and evicted speculation', () => {
    let now = 0;
    const cache = new TileBlobCache(5, () => now);
    const hint = observed({ region: { mapId: 'metrics', lod: 0, firstColumn: 0, firstRow: 0, lastColumn: 1, lastRow: 0 }, expires_at_ms: Date.now() + 10000, policy: 'utility_per_byte', score: .8, dwell_ms: 2000 });
    cache.put('a', new Blob(['abc']), 10, hint, 12);
    cache.take('a');
    assert.equal(hint.state, 'promoted');
    assert.equal(hint.usedBytes, 3);
    assert.equal(metrics.gm_hint_bytes_used, 3);
    assert.equal(metrics.gm_hint_latency_saved_ms, 12);
    cache.put('b', new Blob(['abcd']), 10, hint);
    now = 10;
    assert.equal(cache.has('b'), false);
    assert.equal(metrics.gm_hint_bytes_expired, 4);
    cache.put('c', new Blob(['abc']), 30, hint);
    cache.put('d', new Blob(['def']), 30, hint);
    assert.equal(metrics.gm_hint_bytes_evicted, 3);
    assert.ok(Object.keys(prefetchSnapshot().gmHintBuckets).length);
    cache.clear();
});
test('warming honors byte-utility order from the server', async () => {
    const fetch = globalThis.fetch, calls = [];
    globalThis.fetch = async (url) => { calls.push(String(url)); return new Response('tile'); };
    const manifest = { mapId: 'm', tileUrlTemplate: '/metric-tiles/{lod}/{x}/{y}', levels: [{ lod: 0, columns: 3, rows: 1 }] };
    const hint = observed({ region: { mapId: 'm', lod: 0, firstColumn: 0, firstRow: 0, lastColumn: 2, lastRow: 0 }, tiles: [{ x: 2, y: 0 }, { x: 0, y: 0 }, { x: 1, y: 0 }], expires_at_ms: Date.now() + 10000, policy: 'utility_per_byte' });
    try {
        await warmTiles(manifest, hint.region, hint.expires_at_ms, new Set(), hint).done;
        assert.deepEqual(calls, ['/metric-tiles/0/2/0.webp', '/metric-tiles/0/0/0.webp', '/metric-tiles/0/1/0.webp']);
        assert.equal(hint.state, 'warm');
        assert.equal(hint.bytes, 12);
    }
    finally {
        globalThis.fetch = fetch;
        tileBlobCache.clear();
    }
});
