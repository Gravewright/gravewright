"""Lightweight structured diagnostics for runtime/game operations.

This module intentionally uses only the standard library. Events are emitted as
JSON log lines and kept in a small in-memory ring buffer so the instance owner
can inspect recent activity without needing a metrics stack during development.
Payloads must stay scrubbed: never pass raw command payloads, cookies, tokens or
passwords here.

Process model: the ring buffer is per-process state guarded by a threading
lock. It is whole only under the V1 single-worker deployment (``WEB_WORKERS=1``,
enforced in ``app/config.py``). Running multiple workers would fragment the
buffer into N independent copies and ``/inside/diagnostics`` would report a
single worker's slice — see STABILIZATION_V1 P0.4. A multi-worker future needs a
shared substrate (Prometheus export or broker aggregation), not this buffer.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Any

_LOGGER = logging.getLogger("gravewright.diagnostics")
_METRIC_SAFE_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


@dataclass(frozen=True)
class DiagnosticEvent:
    ts: int
    event: str
    fields: dict[str, Any]


class DiagnosticsRecorder:
    def __init__(self, *, max_events: int = 500) -> None:
        self._events: deque[DiagnosticEvent] = deque(maxlen=max_events)
        self._lock = Lock()

    def record(self, event: str, **fields: Any) -> DiagnosticEvent:
        item = DiagnosticEvent(ts=int(time.time()), event=event, fields=dict(fields))
        with self._lock:
            self._events.append(item)
        return item

    def recent(self, *, limit: int = 100) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), self._events.maxlen or 500))
        with self._lock:
            events = list(self._events)[-safe_limit:]
        return [{"ts": item.ts, "event": item.event, **item.fields} for item in events]

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


def sanitize_metric_name(value: str | None) -> str:
    """Return a safe metric-name component for commands/events."""
    raw = (value or "unknown").strip().lower()
    raw = raw.replace(":", ".")
    raw = _METRIC_SAFE_RE.sub("_", raw)
    raw = raw.strip("._-")
    return raw or "unknown"


def emit_diagnostic(event: str, /, *, level: str = "info", **fields: Any) -> None:
    """Record and log one structured diagnostic event.

    ``fields`` are JSON-serialized with ``default=str`` so enums/paths don't
    crash diagnostics. Values should be low-cardinality and non-sensitive.
    """
    item = diagnostics_recorder.record(event, **fields)
    payload = {"ts": item.ts, "event": event, **item.fields}
    line = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    log_method = getattr(_LOGGER, level, _LOGGER.info)
    log_method(line)


diagnostics_recorder = DiagnosticsRecorder()
