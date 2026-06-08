from __future__ import annotations

from app.realtime.metrics import RealtimeMetrics


def test_realtime_metrics_tracks_counters_gauges_and_histograms():
    metrics = RealtimeMetrics()

    metrics.increment("chunk.batch.count", 2)
    metrics.gauge_add("ws.connections.active", 1)
    metrics.gauge_add("ws.connections.active", -1)
    metrics.observe("chunk.batch.p95_ms", 10)
    metrics.observe("chunk.batch.p95_ms", 30)

    snapshot = metrics.snapshot()

    assert snapshot["counters"]["chunk.batch.count"] == 2
    assert snapshot["gauges"]["ws.connections.active"] == 0
    assert snapshot["histograms"]["chunk.batch.p95_ms"] == {
        "count": 2,
        "total": 40,
        "min": 10,
        "max": 30,
        "p95": 30,
    }
