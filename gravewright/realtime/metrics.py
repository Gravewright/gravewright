"""Payload-free measurements spanning asynchronous realtime handler work."""

from contextlib import ExitStack, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
import logging
from time import monotonic

from channels.db import database_sync_to_async as channels_database_sync_to_async
from django.conf import settings
from django.db import connections


logger = logging.getLogger(__name__)
_current = ContextVar('realtime_metrics', default=None)
_KINDS = frozenset({'command', 'delivery', 'ephemeral', 'presence', 'heartbeat',
                    'connect', 'disconnect'})


@dataclass
class Measurement:
    kind: str
    name: str = '-'
    queue_ms: float = 0
    handler_ms: float = 0
    sql_count: int = 0
    sql_ms: float = 0
    frames: int = 0
    bytes: int = 0
    lock_errors: int = 0

    def execute(self, execute, sql, params, many, context):
        started = monotonic()
        try:
            return execute(sql, params, many, context)
        finally:
            self.sql_count += 1
            self.sql_ms += (monotonic() - started) * 1000


@contextmanager
def handler(kind, arrived_at=None, name=None):
    """Measure one lane operation, including time spent waiting in its queue.

    ``name`` must come from the caller's allowlist of message types; client-supplied
    strings are never logged directly.
    """
    started = monotonic()
    measurement = Measurement(kind if kind in _KINDS else 'handler',
                              queue_ms=max(0, (started - arrived_at) * 1000)
                              if arrived_at is not None else 0)
    if name is not None:
        measurement.name = name
    token = _current.set(measurement)
    try:
        yield measurement
    finally:
        _current.reset(token)
        measurement.handler_ms = (monotonic() - started) * 1000
        threshold = getattr(settings, 'GRAVEWRIGHT_REALTIME_SLOW_MS', 500)
        if threshold and measurement.queue_ms + measurement.handler_ms >= threshold:
            logger.warning(
                'Slow realtime handler kind=%s name=%s queue_ms=%.2f handler_ms=%.2f '
                'sql_count=%d sql_ms=%.2f frames=%d bytes=%d lock_errors=%d',
                measurement.kind, measurement.name, measurement.queue_ms,
                measurement.handler_ms, measurement.sql_count, measurement.sql_ms,
                measurement.frames, measurement.bytes, measurement.lock_errors)


def label(name):
    """Name the current measurement after its message type (callers pass allowlisted names)."""
    measurement = _current.get()
    if measurement is not None:
        measurement.name = name


def frame(encoded):
    """Count an emitted wire frame without retaining or logging its content."""
    measurement = _current.get()
    if measurement is not None:
        measurement.frames += 1
        measurement.bytes += len(encoded.encode('utf-8') if isinstance(encoded, str) else encoded)


def database_busy():
    """Report a recognized lock error without SQL, parameters or exception text."""
    measurement = _current.get()
    if measurement is not None:
        measurement.lock_errors += 1
    logger.warning('Realtime database busy kind=%s name=%s',
                   measurement.kind if measurement else 'handler',
                   measurement.name if measurement else '-')


def database_sync_to_async(func=None, **kwargs):
    """Drop-in Channels adapter that measures queries on their owning thread."""
    if func is None:
        return lambda decorated: database_sync_to_async(decorated, **kwargs)

    @wraps(func)
    def measured(*args, **call_kwargs):
        measurement = _current.get()
        if measurement is None:
            return func(*args, **call_kwargs)
        with ExitStack() as stack:
            for connection in connections.all():
                stack.enter_context(connection.execute_wrapper(measurement.execute))
            return func(*args, **call_kwargs)

    return channels_database_sync_to_async(measured, **kwargs)
