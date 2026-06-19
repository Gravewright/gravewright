"""Helpers for isolating blocking work from async request/WebSocket handlers.

The backend intentionally uses SQLAlchemy Core with synchronous DBAPI drivers.
When sync repository/service code is called directly from an ``async`` handler it
can block the event loop. ``run_blocking`` keeps the public API async while
moving those sync sections onto Python's default thread pool.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import ParamSpec, TypeVar

from app.config import config
from app.observability.diagnostics import emit_diagnostic
from app.observability.diagnostics import sanitize_metric_name
from app.realtime.metrics import realtime_metrics

P = ParamSpec("P")
R = TypeVar("R")

_SLOW_BLOCKING_MS = 250.0

# Dedicated pool for blocking DB work. ``asyncio.to_thread`` uses the loop's
# default executor (~min(32, cpu+4) threads), which throttles the realtime hot
# path: a single command fans into several DB round-trips, so under load worker
# threads queue and even trivial reads measure tens of ms of wait. Sizing this
# pool explicitly (and wider than the default) keeps reads from queuing behind
# the serialized writers.
_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        with _executor_lock:
            if _executor is None:
                _executor = ThreadPoolExecutor(
                    max_workers=max(8, config.realtime_blocking_workers),
                    thread_name_prefix="blocking",
                )
    return _executor


def _callable_name(func: Callable[..., object]) -> str:
    owner = getattr(func, "__self__", None)
    cls_name = owner.__class__.__name__ if owner is not None else ""
    name = getattr(func, "__name__", func.__class__.__name__)
    return f"{cls_name}.{name}" if cls_name else str(name)


async def run_blocking(func: Callable[P, R], /, *args: P.args, **kwargs: P.kwargs) -> R:
    """Run a synchronous callable in a worker thread and return its result.

    The helper also records coarse latency metrics. Slow calls emit a scrubbed
    diagnostic log line with only the callable name and duration.
    """
    name = _callable_name(func)
    metric_name = sanitize_metric_name(name)
    started = time.perf_counter()
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_get_executor(), partial(func, *args, **kwargs))
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        realtime_metrics.observe("blocking.call.duration_ms", elapsed_ms)
        realtime_metrics.observe(f"blocking.call.{metric_name}.duration_ms", elapsed_ms)
        if elapsed_ms >= _SLOW_BLOCKING_MS:
            realtime_metrics.increment("blocking.call.slow")
            emit_diagnostic(
                "blocking.call.slow",
                callable=name,
                duration_ms=round(elapsed_ms, 3),
            )
