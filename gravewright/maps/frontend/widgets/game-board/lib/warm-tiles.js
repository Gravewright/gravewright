import { increment, metrics } from "../model/prefetch-metrics.js";
import { regionTileUrls, tileUrl } from "../model/board-view.js";
import { tileBlobCache } from "../model/tile-blob-cache.js";
/** Low-priority authenticated HTTP, at most 24 tiles and two concurrent fetches. */
export function warmTiles(manifest, region, expires = Date.now() + 60_000, loaded = new Set(), hint) {
    const controller = new AbortController();
    const level = manifest.levels.find(l => l.lod === region.lod);
    const candidates = hint?.tiles && level ? hint.tiles.map(t => tileUrl(manifest, level, t.x, t.y)) : regionTileUrls(manifest, region, 24, url => !loaded.has(url) && !tileBlobCache.has(url));
    const urls = candidates.filter(url => { const cached = tileBlobCache.has(url); if (cached)
        increment('cache_hit'); return !loaded.has(url) && !cached; }).slice(0, 24);
    if (hint) {
        hint.state = 'prefetching';
        metrics.gm_hint_score_at_prefetch = hint.score || 0;
        metrics.gm_hint_dwell_at_prefetch_ms = hint.dwell_ms || 0;
        metrics.gm_hint_momentum_at_prefetch = hint.momentum || 0;
        increment('scheduler_debt_ms', Date.now() - hint.observedAt);
    }
    let finished = false;
    const timer = setTimeout(() => controller.abort(), Math.max(0, expires - Date.now()));
    async function worker() {
        while (urls.length && !controller.signal.aborted && Date.now() < expires) {
            const url = urls.shift();
            try {
                const started = performance.now();
                increment('cache_miss');
                increment('prefetch_requested');
                increment('prefetch_started');
                const response = await fetch(url, { signal: controller.signal, credentials: "same-origin", priority: "low" });
                if (!response.ok)
                    continue;
                const blob = await response.blob();
                increment('bytes_downloaded', blob.size);
                if (!controller.signal.aborted) {
                    tileBlobCache.put(url, blob, expires, hint, performance.now() - started);
                    increment('bytes_prefetched', blob.size);
                    increment('prefetch_completed');
                    if (hint)
                        hint.bytes += blob.size;
                }
                else
                    increment('bytes_wasted', blob.size);
            }
            catch { /* Speculation is never retried. */ }
        }
    }
    const done = Promise.all([worker(), worker()]).then(() => undefined).finally(() => { finished = true; clearTimeout(timer); if (hint && hint.state === 'prefetching')
        hint.state = controller.signal.aborted ? 'cancelled' : 'warm'; });
    return { cancel: () => { if (!finished && !controller.signal.aborted)
            increment('cancelled'); controller.abort(); clearTimeout(timer); }, done };
}
