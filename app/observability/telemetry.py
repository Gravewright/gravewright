"""Opt-in local diagnostics capture for operators.

The capture is deliberately local-only: structured, redacted diagnostics and
periodic metric snapshots are written to a bounded rotating JSONL file. Nothing
is uploaded or transmitted to a third party.
"""

from __future__ import annotations

import atexit
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import threading
import time


_LOGGER_NAME = "gravewright.diagnostics"
_MAX_BYTES = 10 * 1024 * 1024
_BACKUP_COUNT = 5
_runtime: "LocalDiagnosticsRuntime | None" = None
_PRIVACY_MARKER = "share-safe-v1"
_PRIVATE_KEYS = {"path", "url", "origin", "host", "hostname", "ip", "address"}


class ShareSafeJsonFormatter(logging.Formatter):
    """Make every capture line safe to attach while preserving correlations."""

    def __init__(self, salt: bytes) -> None:
        super().__init__()
        self._salt = salt

    def _alias(self, key: str, value: object) -> str:
        kind = key.removesuffix("_id").removesuffix("_ids") or "id"
        digest = hashlib.blake2b(
            str(value).encode("utf-8", errors="replace"),
            key=self._salt,
            digest_size=8,
        ).hexdigest()
        return f"{kind}_{digest}"

    def _scrub(self, value: object, *, key: str = "") -> object:
        lowered = key.lower()
        if lowered in _PRIVATE_KEYS or lowered.endswith("_path") or lowered.endswith("_url"):
            return "[redacted]"
        if lowered == "id" or lowered.endswith("_id"):
            return self._alias(lowered, value)
        if lowered.endswith("_ids") and isinstance(value, (list, tuple)):
            return [self._alias(lowered, item) for item in value]
        if isinstance(value, dict):
            return {str(item_key): self._scrub(item, key=str(item_key)) for item_key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._scrub(item, key=key) for item in value]
        return value

    def format(self, record: logging.LogRecord) -> str:
        try:
            payload = json.loads(record.getMessage())
        except (TypeError, json.JSONDecodeError):
            payload = {"ts": int(time.time()), "event": "diagnostics.unstructured"}
        safe = self._scrub(payload)
        if not isinstance(safe, dict):
            safe = {"ts": int(time.time()), "event": "diagnostics.unstructured"}
        safe["privacy"] = _PRIVACY_MARKER
        return json.dumps(safe, sort_keys=True, separators=(",", ":"), default=str)


class LocalDiagnosticsRuntime:
    def __init__(self, path: Path, *, interval_seconds: int = 30) -> None:
        self.path = path
        self.interval_seconds = max(5, interval_seconds)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._handler: RotatingFileHandler | None = None
        self._previous_level: int | None = None
        self._previous_propagate: bool | None = None
        self._formatter = ShareSafeJsonFormatter(os.urandom(32))

    def start(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._preserve_unsafe_existing_file()
        handler = RotatingFileHandler(
            self.path,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(self._formatter)
        handler.setLevel(logging.INFO)
        logger = logging.getLogger(_LOGGER_NAME)
        self._previous_level = logger.level
        self._previous_propagate = logger.propagate
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        # Capture mode keeps the high-volume structured stream out of the
        # interactive terminal; the rotating file is its explicit destination.
        logger.propagate = False
        self._handler = handler
        self._write("diagnostics.capture.started", pid=os.getpid(), path=str(self.path))
        self._thread = threading.Thread(
            target=self._snapshot_loop,
            name="gravewright-local-diagnostics",
            daemon=True,
        )
        self._thread.start()

    def _preserve_unsafe_existing_file(self) -> None:
        if not self.path.is_file() or self.path.stat().st_size == 0:
            return
        suffix = "private"
        try:
            payloads = []
            with self.path.open("r", encoding="utf-8") as source:
                for line in source:
                    if line.strip():
                        payloads.append(json.loads(line))
        except (OSError, UnicodeError, json.JSONDecodeError):
            suffix = "invalid"
        else:
            if all(
                isinstance(payload, dict) and payload.get("privacy") == _PRIVACY_MARKER
                for payload in payloads
            ):
                return
        stamp = time.strftime("%Y%m%d-%H%M%S")
        quarantine = self.path.with_name(f"{self.path.name}.{suffix}-{stamp}")
        counter = 1
        while quarantine.exists():
            quarantine = self.path.with_name(
                f"{self.path.name}.{suffix}-{stamp}-{counter}"
            )
            counter += 1
        self.path.replace(quarantine)

    def _write(self, event: str, **fields: object) -> None:
        logging.getLogger(_LOGGER_NAME).info(
            json.dumps(
                {"ts": int(time.time()), "event": event, **fields},
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
        )

    def _snapshot_loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.snapshot()

    def snapshot(self) -> None:
        from app.realtime.metrics import realtime_metrics

        self._write("diagnostics.metrics", metrics=realtime_metrics.snapshot())

    def close(self) -> None:
        if self._stop.is_set():
            return
        self._stop.set()
        self.snapshot()
        self._write("diagnostics.capture.stopped", pid=os.getpid())
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=1)
        logger = logging.getLogger(_LOGGER_NAME)
        if self._handler is not None:
            logger.removeHandler(self._handler)
            self._handler.close()
            self._handler = None
        if self._previous_level is not None:
            logger.setLevel(self._previous_level)
        if self._previous_propagate is not None:
            logger.propagate = self._previous_propagate


def configure_local_diagnostics(path: str | Path, *, interval_seconds: int = 30) -> LocalDiagnosticsRuntime:
    global _runtime
    if _runtime is not None:
        return _runtime
    runtime = LocalDiagnosticsRuntime(Path(path).expanduser().resolve(), interval_seconds=interval_seconds)
    runtime.start()
    atexit.register(runtime.close)
    _runtime = runtime
    return runtime


def configure_local_diagnostics_from_environment() -> LocalDiagnosticsRuntime | None:
    if os.environ.get("GRAVEWRIGHT_DIAGNOSTICS_CAPTURE", "").strip().lower() not in {
        "1", "true", "yes", "on"
    }:
        return None
    path = os.environ.get("GRAVEWRIGHT_DIAGNOSTICS_FILE", "").strip()
    if not path:
        return None
    try:
        interval = int(os.environ.get("GRAVEWRIGHT_DIAGNOSTICS_INTERVAL", "30"))
    except ValueError:
        interval = 30
    return configure_local_diagnostics(path, interval_seconds=interval)
