"""Instrumented Runner server for tests/e2e/realtime_session.py.

Starts the same Daphne entry point as the Runner (scripts/managed_server.py) and
adds measurement only; no handler changes behavior:

- every realtime operation (not only slow ones) is written to ``server-ops.jsonl``
  with its start time, a short connection label, queue/handler/SQL times, and the
  time its synchronous calls waited for, ran on and used CPU of their thread;
- channel-layer events get an arrival time, so deliveries report their queue wait
  (0.3.5 always reports ``queue_ms=0`` for them), and so do peer samples;
- warnings go to ``server.log`` with timestamps, in the original slow-handler format;
- process CPU, thread count and per-thread CPU are sampled into ``cpu.jsonl``.

Logs never contain payloads; connection labels come from GW_MEASURE_LABELS.
"""

import contextvars
import itertools
import json
import logging
import os
import sys
import threading
import time
from contextlib import ExitStack, contextmanager
from functools import wraps
from pathlib import Path
from time import monotonic, thread_time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUTPUT = Path(os.environ["GW_MEASURE_DIR"])
LABELS = json.loads(os.environ.get("GW_MEASURE_LABELS", "{}"))
EPOCH_OFFSET = time.time() - monotonic()


def configure_logging():
    handler = logging.FileHandler(OUTPUT / "server.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.WARNING)


def sample_cpu(stop):
    """Process and per-thread CPU every two seconds (Linux /proc)."""
    ticks = os.sysconf("SC_CLK_TCK")
    previous, threads_before, system_before = None, {}, None

    def system():
        values = [int(v) for v in Path("/proc/stat").read_text().split("\n", 1)[0].split()[1:]]
        return sum(values), values[3] + values[4]  # total, idle + iowait
    with (OUTPUT / "cpu.jsonl").open("w", buffering=1) as out:
        while not stop.wait(2):
            try:
                fields = Path("/proc/self/stat").read_text().rsplit(")", 1)[1].split()
                cpu = (int(fields[11]) + int(fields[12])) / ticks
                threads = {}
                for task in Path("/proc/self/task").iterdir():
                    try:
                        stat = (task / "stat").read_text().rsplit(")", 1)[1].split()
                        threads[task.name] = (int(stat[11]) + int(stat[12])) / ticks
                    except OSError:
                        continue
            except OSError:
                continue
            now = time.time()
            machine = system()
            if previous is not None:
                elapsed = now - previous[0]
                busy = sorted(((value - threads_before.get(name, value)) / elapsed
                               for name, value in threads.items()), reverse=True)
                spent = machine[0] - system_before[0]
                out.write(json.dumps({
                    "t": now, "process_cpu": round((cpu - previous[1]) / elapsed, 3),
                    "threads": len(threads), "top_threads": [round(v, 3) for v in busy[:4]],
                    "machine_busy": round(1 - (machine[1] - system_before[1]) / spent, 3) if spent else None,
                }) + "\n")
            previous, threads_before, system_before = (now, cpu), threads, machine


def install(metrics):
    """Replace the measurement hooks before the consumers bind them."""
    from channels.db import database_sync_to_async as channels_adapter
    from django.conf import settings
    from django.db import connections

    connection_label = contextvars.ContextVar("gw_measure_connection", default=None)
    ops = (OUTPUT / "server-ops.jsonl").open("w", buffering=1, encoding="utf-8")

    @contextmanager
    def handler(kind, arrived_at=None, name=None):
        started = monotonic()
        measurement = metrics.Measurement(
            kind if kind in metrics._KINDS else "handler",
            queue_ms=max(0, (started - arrived_at) * 1000) if arrived_at is not None else 0)
        if name is not None:
            measurement.name = name
        measurement.sync_calls = 0
        measurement.sync_wait_ms = measurement.sync_ms = measurement.sync_cpu_ms = 0.0
        token = metrics._current.set(measurement)
        try:
            yield measurement
        finally:
            metrics._current.reset(token)
            measurement.handler_ms = (monotonic() - started) * 1000
            threshold = getattr(settings, "GRAVEWRIGHT_REALTIME_SLOW_MS", 500)
            if threshold and measurement.queue_ms + measurement.handler_ms >= threshold:
                metrics.logger.warning(
                    "Slow realtime handler kind=%s name=%s queue_ms=%.2f handler_ms=%.2f "
                    "sql_count=%d sql_ms=%.2f frames=%d bytes=%d lock_errors=%d",
                    measurement.kind, measurement.name, measurement.queue_ms,
                    measurement.handler_ms, measurement.sql_count, measurement.sql_ms,
                    measurement.frames, measurement.bytes, measurement.lock_errors)
            holder = connection_label.get()
            ops.write(json.dumps({
                "t": round(EPOCH_OFFSET + started, 4),
                "conn": holder["who"] if holder else "-",
                "kind": measurement.kind, "name": measurement.name,
                "queue_ms": round(measurement.queue_ms, 2),
                "handler_ms": round(measurement.handler_ms, 2),
                "sql_count": measurement.sql_count, "sql_ms": round(measurement.sql_ms, 2),
                "sync_calls": measurement.sync_calls,
                "sync_wait_ms": round(measurement.sync_wait_ms, 2),
                "sync_ms": round(measurement.sync_ms, 2),
                "sync_cpu_ms": round(measurement.sync_cpu_ms, 2),
                "frames": measurement.frames, "bytes": measurement.bytes,
                "lock_errors": measurement.lock_errors,
            }) + "\n")

    def database_sync_to_async(func=None, **kwargs):
        if func is None:
            return lambda decorated: database_sync_to_async(decorated, **kwargs)

        def measured(submitted, *args, **call_kwargs):
            measurement = metrics._current.get()
            if measurement is None:
                return func(*args, **call_kwargs)
            started, cpu = monotonic(), thread_time()
            measurement.sync_wait_ms += (started - submitted) * 1000
            try:
                with ExitStack() as stack:
                    for connection in connections.all():
                        stack.enter_context(connection.execute_wrapper(measurement.execute))
                    return func(*args, **call_kwargs)
            finally:
                measurement.sync_calls += 1
                measurement.sync_ms += (monotonic() - started) * 1000
                measurement.sync_cpu_ms += (thread_time() - cpu) * 1000

        adapted = channels_adapter(measured, **kwargs)

        @wraps(func)
        async def call(*args, **call_kwargs):
            return await adapted(monotonic(), *args, **call_kwargs)

        return call

    metrics.handler = handler
    metrics.database_sync_to_async = database_sync_to_async
    return connection_label


def stamp_channel_events():
    from channels.layers import InMemoryChannelLayer

    original = InMemoryChannelLayer.receive

    async def receive(self, channel):
        message = await original(self, channel)
        # room.zone forwards its whole event to the browser; leave it untouched.
        if isinstance(message, dict) and message.get("type") != "room.zone":
            message = {**message, "_gw_arrived": monotonic()}
        return message

    InMemoryChannelLayer.receive = receive


def label_connections(connection_label, metrics):
    from django.db import OperationalError

    from gravewright.realtime import consumers, scene_stream
    from gravewright.realtime.errors import database_busy

    consumers.db = metrics.database_sync_to_async
    scene_stream.db = metrics.database_sync_to_async
    TableConsumer = consumers.TableConsumer
    counter = itertools.count(1)
    original_call, original_connect = TableConsumer.__call__, TableConsumer.connect
    original_lane, original_sample = TableConsumer.ephemeral_lane, TableConsumer.run_sample

    async def __call__(self, scope, receive, send):
        self._gw_holder = {"who": f"?#{next(counter)}"}
        connection_label.set(self._gw_holder)
        return await original_call(self, scope, receive, send)

    async def connect(self):
        await original_connect(self)
        if getattr(self, "user_id", None):
            number = self._gw_holder["who"].split("#", 1)[1]
            self._gw_holder["who"] = f"{LABELS.get(str(self.user_id), 'user')}#{number}"

    async def ephemeral_lane(self):
        connection_label.set(getattr(self, "_gw_holder", None))
        return await original_lane(self)

    async def run_sample(self, key, item):
        if key[0] == "own":
            return await original_sample(self, key, item)
        # Same as 0.3.5, plus the sample's channel arrival time as its queue start.
        with metrics.handler("ephemeral", item.get("_gw_arrived"), item["type"]):
            try:
                await super(TableConsumer, self).dispatch(item)
            except OperationalError as error:
                if not database_busy(error):
                    raise
                metrics.database_busy()

    TableConsumer.__call__ = __call__
    TableConsumer.connect = connect
    TableConsumer.ephemeral_lane = ephemeral_lane
    TableConsumer.run_sample = run_sample


def main():
    configure_logging()
    import django

    django.setup()
    from gravewright.realtime import metrics

    connection_label = install(metrics)
    stamp_channel_events()
    label_connections(connection_label, metrics)
    stop = threading.Event()
    threading.Thread(target=sample_cpu, args=(stop,), daemon=True, name="gw-cpu-sampler").start()
    from scripts.managed_server import main as serve

    try:
        serve()
    finally:
        stop.set()


if __name__ == "__main__":
    main()
