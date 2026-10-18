"""Run durable Blueprint continuations inside the active ASGI server lifecycle."""

import asyncio
import logging
import os
import sys
from pathlib import Path

from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import close_old_connections, connections


logger = logging.getLogger(__name__)


def process_pending():
    """Keep database connections local to a short synchronous worker pass."""
    managed_state = os.environ.get('GRAVEWRIGHT_MANAGED_STATE')
    if managed_state and (Path(managed_state) / 'maintenance').exists():
        return
    from .blueprint_delays import process_due_delays

    close_old_connections()
    try:
        return process_due_delays(limit=20)
    finally:
        connections.close_all()


class DelayWorker:
    """One loop task per server process; the database arbitrates other workers."""

    def __init__(self, process=None, interval=.25):
        self.process = process or process_pending
        self.interval = interval
        self.task = None
        self.stopping = None

    def start(self):
        if not getattr(settings, 'GRAVEWRIGHT_AUTOMATION_WORKER_ENABLED', True):
            return
        if self.task is not None and not self.task.done():
            return
        self.stopping = asyncio.Event()
        self.task = asyncio.create_task(self.run(), name='blueprint-delays')

    async def run(self):
        while not self.stopping.is_set():
            interval = self.interval
            try:
                # The bridge also returns post-commit Channels notifications to
                # this event loop, including the local in-memory channel layer.
                await sync_to_async(self.process, thread_sensitive=True)()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception('Could not process pending Blueprint delays.')
                interval = max(interval, 2)
            try:
                await asyncio.wait_for(self.stopping.wait(), timeout=interval)
            except TimeoutError:
                pass

    async def stop(self):
        if self.task is None:
            return
        self.stopping.set()
        # Finish the current transaction before the host closes its loop.
        await self.task
        self.task = None


class DelayWorkerMiddleware:
    """Support ASGI lifespan and Daphne's existing reactor startup/shutdown."""

    def __init__(self, application, worker=None):
        self.application = application
        self.worker = worker or DelayWorker()
        self.reactor = None
        self.bind_daphne()

    def bind_daphne(self):
        # Never install a reactor while importing Django or running a command.
        # Daphne installs its asyncio reactor before loading the ASGI app.
        reactor = sys.modules.get('twisted.internet.reactor')
        if reactor is None or reactor is self.reactor:
            return
        loop = getattr(reactor, '_asyncioEventloop', None)
        if loop is None or loop.is_closed():
            return
        from twisted.internet.defer import Deferred

        self.reactor = reactor
        reactor.callWhenRunning(lambda: loop.call_soon(self.worker.start))
        reactor.addSystemEventTrigger('before', 'shutdown',
            lambda: Deferred.fromFuture(loop.create_task(self.worker.stop())))

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'lifespan':
            self.bind_daphne()
            return await self.application(scope, receive, send)
        try:
            while True:
                message = await receive()
                if message['type'] == 'lifespan.startup':
                    self.worker.start()
                    await send({'type': 'lifespan.startup.complete'})
                elif message['type'] == 'lifespan.shutdown':
                    await self.worker.stop()
                    await send({'type': 'lifespan.shutdown.complete'})
                    return
        finally:
            await self.worker.stop()
