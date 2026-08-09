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


def test_histogram_retains_exact_aggregates_but_bounded_samples():
    """Observations must not be retained one-float-per-call forever.

    ``observe`` is called on every WS command, blocking DB call and HTTP
    request, so unbounded retention is an out-of-memory bug on a long-lived
    process. count/total/min/max stay exact; only the percentile window is
    capped.
    """
    metrics = RealtimeMetrics(max_histogram_samples=16)

    for value in range(1000):
        metrics.observe("ws.command.duration_ms", float(value))

    histogram = metrics._histograms["ws.command.duration_ms"]
    assert len(histogram.samples) == 16

    snapshot = metrics.snapshot()["histograms"]["ws.command.duration_ms"]
    assert snapshot["count"] == 1000
    assert snapshot["total"] == sum(float(v) for v in range(1000))
    assert snapshot["min"] == 0
    assert snapshot["max"] == 999


def test_distinct_series_names_are_capped_and_truncation_is_reported():
    """Several call sites derive metric names from request data.

    A client that mints unique names must not be able to grow the process-global
    dicts without bound.
    """
    metrics = RealtimeMetrics(max_series=4)

    for index in range(100):
        metrics.increment(f"ws.command.garbage{index}.count")
        metrics.observe(f"ws.command.garbage{index}.duration_ms", 1.0)

    assert len(metrics._counters) == 4
    assert len(metrics._histograms) == 4
    assert metrics.snapshot()["counters"]["metrics.series.dropped"] == 192


def test_series_already_present_keep_recording_after_the_cap():
    metrics = RealtimeMetrics(max_series=1)

    metrics.increment("ws.command.count")
    metrics.increment("ws.command.count")
    metrics.increment("ws.command.rejected")

    counters = metrics.snapshot()["counters"]
    assert counters["ws.command.count"] == 2
    assert "ws.command.rejected" not in counters
