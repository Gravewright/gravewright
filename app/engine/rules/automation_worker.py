"""Small lifecycle host for durable registered-action jobs."""

from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass

from app.engine.rules.automation_service import AutomationService
from app.helpers.async_blocking import run_blocking


@dataclass
class _Worker:
    task: asyncio.Task
    stop: asyncio.Event


# A process can host more than one ASGI lifespan loop in tests and embedding.
# asyncio primitives are loop-bound, so a single module-global task is unsafe.
_workers: dict[asyncio.AbstractEventLoop, _Worker] = {}


async def _loop(stop: asyncio.Event) -> None:
    worker_id = f"{os.getpid()}-{uuid.uuid4().hex}"
    while not stop.is_set():
        try:
            result = await run_blocking(AutomationService().run_one, worker_id=worker_id)
            delay = 0.05 if result.value else 0.5
        except Exception:
            delay = 1.0
        try:
            await asyncio.wait_for(stop.wait(), timeout=delay)
        except TimeoutError:
            pass


async def start_automation_worker() -> None:
    loop = asyncio.get_running_loop()
    existing = _workers.get(loop)
    if existing and not existing.task.done():
        return
    stop = asyncio.Event()
    task = asyncio.create_task(_loop(stop), name="gravewright-automation-worker")
    _workers[loop] = _Worker(task=task, stop=stop)


async def stop_automation_worker() -> None:
    loop = asyncio.get_running_loop()
    worker = _workers.pop(loop, None)
    if worker is None:
        return
    worker.stop.set()
    try:
        await asyncio.wait_for(worker.task, timeout=2)
    except (TimeoutError, asyncio.CancelledError):
        worker.task.cancel()
