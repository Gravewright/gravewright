from __future__ import annotations

from app.observability.diagnostics import diagnostics_recorder
from app.observability.diagnostics import emit_diagnostic
from app.observability.diagnostics import sanitize_metric_name
from app.realtime.metrics import realtime_metrics


def test_diagnostics_recorder_keeps_recent_structured_events():
    diagnostics_recorder.clear()

    emit_diagnostic("test.event", user_id="user-1", success=True)

    recent = diagnostics_recorder.recent(limit=1)
    assert recent[0]["event"] == "test.event"
    assert recent[0]["user_id"] == "user-1"
    assert recent[0]["success"] is True


def test_metric_name_sanitizer_is_stable_for_commands():
    assert sanitize_metric_name("token.move") == "token.move"
    assert sanitize_metric_name("Scene Activate Request!") == "scene_activate_request"
    assert sanitize_metric_name("") == "unknown"


def test_realtime_metrics_snapshot_exposes_histograms():
    realtime_metrics.reset()

    realtime_metrics.increment("ws.command.count")
    realtime_metrics.observe("ws.command.duration_ms", 10.0)
    realtime_metrics.observe("ws.command.duration_ms", 30.0)

    snapshot = realtime_metrics.snapshot()
    assert snapshot["counters"]["ws.command.count"] == 1
    assert snapshot["histograms"]["ws.command.duration_ms"]["count"] == 2
    assert snapshot["histograms"]["ws.command.duration_ms"]["p95"] == 30.0
