from __future__ import annotations

import json
from types import SimpleNamespace

from app.cli import run as run_mod
from app.observability.diagnostics import emit_diagnostic
from app.observability.telemetry import LocalDiagnosticsRuntime
from app.realtime.metrics import realtime_metrics


def test_local_diagnostics_writes_redacted_events_and_metric_snapshots(tmp_path):
    target = tmp_path / "diagnostics.jsonl"
    runtime = LocalDiagnosticsRuntime(target, interval_seconds=3600)
    runtime.start()
    emit_diagnostic(
        "test.event",
        token="must-not-leak",
        operation="safe",
        user_id="real-user-id",
        room_id="real-room-id",
        path="C:/Users/person/private/project",
    )
    try:
        raise RuntimeError("diagnostic failure")
    except RuntimeError:
        emit_diagnostic("test.failure", level="exception", exception="RuntimeError")
    realtime_metrics.increment("test.diagnostics.count")
    runtime.snapshot()
    runtime.close()

    records = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
    event = next(record for record in records if record["event"] == "test.event")
    metric = next(record for record in records if record["event"] == "diagnostics.metrics")
    assert event["token"] == "[redacted]"
    assert event["operation"] == "safe"
    assert event["user_id"].startswith("user_") and "real-user-id" not in event["user_id"]
    assert event["room_id"].startswith("room_") and "real-room-id" not in event["room_id"]
    assert event["path"] == "[redacted]"
    assert event["privacy"] == "share-safe-v1"
    assert metric["metrics"]["counters"]["test.diagnostics.count"] >= 1
    assert records[0]["event"] == "diagnostics.capture.started"
    assert records[-1]["event"] == "diagnostics.capture.stopped"
    assert next(record for record in records if record["event"] == "test.failure")["exception"] == "RuntimeError"


def test_run_diagnostics_is_explicit_local_and_passed_only_to_child(tmp_path, monkeypatch, capsys):
    target = tmp_path / "capture.jsonl"
    captured = {}

    def fake_run(command, **kwargs):
        captured.update(command=command, **kwargs)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(run_mod.subprocess, "run", fake_run)
    result = run_mod.serve(
        host="127.0.0.1",
        port=8000,
        dev=False,
        open_browser=False,
        diagnostics=True,
        diagnostics_file=str(target),
    )

    assert result == 0
    assert captured["env"]["GRAVEWRIGHT_DIAGNOSTICS_CAPTURE"] == "1"
    assert captured["env"]["GRAVEWRIGHT_DIAGNOSTICS_FILE"] == str(target.resolve())
    output = capsys.readouterr().out
    assert "Local diagnostics: ON" in output
    assert "no network upload" in output


def test_invalid_existing_capture_is_preserved_and_replaced_with_clean_jsonl(tmp_path):
    target = tmp_path / "diagnostics.jsonl"
    target.write_text('{"event":"ok"}\nTraceback (most recent call last):\n', encoding="utf-8")
    runtime = LocalDiagnosticsRuntime(target, interval_seconds=3600)
    runtime.start()
    runtime.close()

    quarantined = list(tmp_path.glob("diagnostics.jsonl.invalid-*"))
    assert len(quarantined) == 1
    assert "Traceback" in quarantined[0].read_text(encoding="utf-8")
    assert all(json.loads(line) for line in target.read_text(encoding="utf-8").splitlines())


def test_valid_but_unsanitized_capture_is_preserved_as_private(tmp_path):
    target = tmp_path / "diagnostics.jsonl"
    target.write_text('{"event":"old","user_id":"real-user"}\n', encoding="utf-8")
    runtime = LocalDiagnosticsRuntime(target, interval_seconds=3600)
    runtime.start()
    runtime.close()

    private = list(tmp_path.glob("diagnostics.jsonl.private-*"))
    assert len(private) == 1
    fresh = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
    assert fresh and all(record["privacy"] == "share-safe-v1" for record in fresh)
