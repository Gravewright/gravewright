"""Fire-and-forget async work that must outlive the caller's coroutine.

Used for teardown side effects (e.g. presence leave) that should not block a
request/WebSocket handler from returning while they persist state and fan out
a broadcast.
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

from app.observability.diagnostics import emit_diagnostic

_background_tasks: set[asyncio.Task[Any]] = set()


def spawn_detached(coro: Coroutine[Any, Any, Any], *, name: str) -> asyncio.Task[Any]:
    """Schedule ``coro`` on the running loop, independent of the caller.

    A strong reference to the task is kept until it finishes so it isn't
    garbage-collected mid-flight, and any exception it raises is logged
    rather than propagated to an unrelated awaiter.
    """
    task = asyncio.create_task(coro, name=name)
    _background_tasks.add(task)
    task.add_done_callback(_on_task_done)
    return task


def _on_task_done(task: asyncio.Task[Any]) -> None:
    _background_tasks.discard(task)

    if task.cancelled():
        return

    exc = task.exception()
    if exc is not None:
        emit_diagnostic(
            "background_task.failed",
            level="exception",
            task_name=task.get_name(),
            exception=exc.__class__.__name__,
        )
