/** Local diagnostics only. Contains no journal, chat or GM identity data. */
const counters = ['created', 'prefetch_requested', 'prefetch_completed', 'promoted_to_visible', 'expired_unused', 'bytes_downloaded', 'bytes_used', 'bytes_wasted', 'cache_hit', 'cache_miss', 'cancelled', 'lead_time_ms', 'latency_saved_ms', 'scheduler_debt_ms', 'candidates', 'prefetch_started', 'promoted', 'bytes_prefetched', 'bytes_promoted', 'bytes_expired', 'bytes_evicted', 'score_at_prefetch', 'score_at_promotion', 'dwell_at_prefetch_ms', 'momentum_at_prefetch'];
export const metrics = Object.fromEntries(counters.map(k => ['gm_hint_' + k, 0]));
const hints = new Map(), buckets = new Map();
export function increment(key, n = 1) { metrics['gm_hint_' + key] = (metrics['gm_hint_' + key] || 0) + n; }
export function observed(hint) {
    const region = hint.region;
    const id = `${region.mapId}:${region.lod}:${region.firstColumn}:${region.firstRow}:${region.lastColumn}:${region.lastRow}:${hint.expires_at_ms}`;
    if (hints.has(id))
        return hints.get(id);
    const record = { ...hint, id, state: 'candidate', observedAt: Date.now(), bytes: 0, usedBytes: 0 };
    hints.set(id, record);
    increment('created');
    increment('candidates');
    if (hints.size > 128)
        hints.delete(hints.keys().next().value);
    return record;
}
export function promoted(hint, bytes, downloadedAt, networkMs) {
    if (!hint)
        return;
    if (hint.state !== 'promoted') {
        increment('promoted');
        increment('promoted_to_visible');
    }
    hint.state = 'promoted';
    hint.usedBytes += bytes;
    increment('bytes_used', bytes);
    increment('bytes_promoted', bytes);
    metrics.gm_hint_score_at_promotion = hint.score || 0;
    increment('lead_time_ms', Math.max(0, Date.now() - downloadedAt));
    increment('latency_saved_ms', networkMs);
    const key = `${hint.policy}:${Math.max(0, Math.min(10, Math.floor(hint.distance_chunks || 0)))}:${Math.min(10, Math.floor((hint.dwell_ms || 0) / 1000))}`;
    const bucket = buckets.get(key) || { bytes: 0, promotions: 0 };
    bucket.bytes += bytes;
    bucket.promotions++;
    buckets.set(key, bucket);
}
export function discarded(hint, bytes, reason) {
    increment('bytes_wasted', bytes);
    increment(reason === 'expired' ? 'bytes_expired' : 'bytes_evicted', bytes);
    if (hint && hint.state !== 'promoted' && hint.state !== 'expired') {
        hint.state = 'expired';
        increment('expired_unused');
    }
}
export function prefetchSnapshot() {
    for (const hint of hints.values())
        if (hint.expires_at_ms <= Date.now() && !['promoted', 'expired'].includes(hint.state)) {
            hint.state = 'expired';
            increment('expired_unused');
        }
    return { metrics: { ...metrics, gm_hint_useful_byte_ratio: metrics.gm_hint_bytes_prefetched ? metrics.gm_hint_bytes_used / metrics.gm_hint_bytes_prefetched : 0 }, gmHintStates: [...hints.values()].map(h => ({ id: h.id, state: h.state, bytes: h.bytes, usedBytes: h.usedBytes, score: h.score, policy: h.policy })), gmHintBuckets: Object.fromEntries(buckets) };
}
