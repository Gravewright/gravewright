"""Bound expensive recipient reads without holding permits for socket sends."""

import asyncio
import logging
import weakref

from django.conf import settings


logger = logging.getLogger(__name__)
DENIED = object()
# Values are weak too: a contended semaphore retains its loop, so a strong value
# here would keep the weak key alive across successive ASGI/test event loops.
_gates = weakref.WeakKeyDictionary()


def abandoned(job):
    """Observe failures from reads whose recipient disconnected while waiting."""
    if not job.cancelled() and (error := job.exception()) is not None:
        logger.error("Projection read failed after its recipient stopped waiting", exc_info=error)


class ProjectionGate:
    def __init__(self, limit):
        self.limit = limit
        self.slots = asyncio.Semaphore(limit)
        self.jobs = set()

    async def finish_read(self, work):
        try:
            return await work()
        finally:
            self.slots.release()

    async def read(self, work, authorized):
        await self.slots.acquire()
        transferred = False
        try:
            # A session, role or scene grant may change while this read queues.
            # Domain services still resolve live membership and resource access.
            if not await authorized():
                return DENIED
            job = asyncio.create_task(self.finish_read(work))
            transferred = True
            self.jobs.add(job)
            job.add_done_callback(self.jobs.discard)
            try:
                # Cancelling sync_to_async's future cannot stop a running thread.
                # Keep the permit until that read really finishes, while allowing
                # disconnect cleanup to abandon its wait immediately.
                # wait() leaves the child running on cancellation and lets our
                # callback report an abandoned failure exactly once.
                await asyncio.wait((job,))
                return job.result()
            except asyncio.CancelledError:
                job.add_done_callback(abandoned)
                raise
        finally:
            if not transferred:
                self.slots.release()


def gate_for_loop(limit):
    loop = asyncio.get_running_loop()
    reference = _gates.get(loop)
    gate = reference() if reference else None
    if gate is None or gate.limit != limit:
        gate = ProjectionGate(limit)
        _gates[loop] = weakref.ref(gate)
    return gate


async def read(work, authorized):
    """Authorize after admission; inherit the caller's DB thread and metrics."""
    limit = settings.GRAVEWRIGHT_REALTIME_PROJECTION_CONCURRENCY
    if limit == 0:
        return await work() if await authorized() else DENIED
    return await gate_for_loop(limit).read(work, authorized)
