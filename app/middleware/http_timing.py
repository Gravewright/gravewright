"""Server-side HTTP request timing.

Records how long the app actually spends handling each HTTP request, so HTTP
latency (e.g. ``POST /game/chat``) can be read from real server metrics instead
of being inferred from a load client whose own event loop may be the bottleneck.

Emits into ``realtime_metrics``:
    http.request.duration_ms              — every request
    http.request.<sanitized-path>.duration_ms  — per route (ids collapsed)
"""
from __future__ import annotations

import re
import time
from collections.abc import Awaitable, Callable
from typing import Any

from app.observability.diagnostics import sanitize_metric_name
from app.realtime.metrics import realtime_metrics

ASGIApp = Callable[
    [dict[str, Any], Callable[..., Awaitable[Any]], Callable[..., Awaitable[Any]]],
    Awaitable[Any],
]

# Collapse high-cardinality path segments (uuids, long hex, numeric ids) so the
# per-route metric name stays bounded.
_ID_SEGMENT = re.compile(r"^(?:[0-9a-fA-F]{12,}|\d+)$")


def _route_label(path: str) -> str:
    parts = [seg for seg in path.split("/") if seg]
    if not parts:
        return "root"
    collapsed = ["id" if _ID_SEGMENT.match(seg) else seg for seg in parts]
    return ".".join(collapsed)


class HttpTimingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[..., Awaitable[Any]],
        send: Callable[..., Awaitable[Any]],
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        label = sanitize_metric_name(_route_label(scope.get("path", "")))
        started = time.perf_counter()
        try:
            await self.app(scope, receive, send)
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            realtime_metrics.observe("http.request.duration_ms", elapsed_ms)
            realtime_metrics.observe(f"http.request.{label}.duration_ms", elapsed_ms)
