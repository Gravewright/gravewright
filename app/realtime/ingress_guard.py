from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from typing import Callable
from urllib.parse import urlsplit

from app.config import config
from app.realtime.commands import ClientCommand
from app.realtime.envelopes import error_envelope

                                                                              
                                                                              
                                                                    
                                                                                
MAX_MESSAGE_BYTES = config.ws_max_message_bytes

                                                                               
                                                
EXPENSIVE_COMMANDS = frozenset(
    {
        ClientCommand.VIEWPORT_SUBSCRIBE.value,
        ClientCommand.SESSION_RESUME.value,
        ClientCommand.SCENE_ACTIVATE_REQUEST.value,
        ClientCommand.TOKEN_CREATE_MANY_FROM_ACTORS.value,
        ClientCommand.FOG_ENABLE.value,
        ClientCommand.FOG_DISABLE.value,
        ClientCommand.FOG_RESET.value,
    }
)


@dataclass
class _TokenBucket:
    """Classic token bucket. ``allow`` is O(1) and clock-injectable for tests."""

    capacity: float
    refill_per_sec: float
    tokens: float
    updated_at: float

    def allow(self, *, now: float, cost: float = 1.0) -> bool:
        elapsed = max(0.0, now - self.updated_at)
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_sec)
        self.updated_at = now
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False


@dataclass(frozen=True)
class _BucketSpec:
    capacity: float
    refill_per_sec: float


                                                                
                                                                               
                                                                          
_GLOBAL_SPEC = _BucketSpec(
    capacity=float(config.ws_burst_commands),
    refill_per_sec=float(config.ws_commands_per_second),
)
_DEFAULT_COMMAND_SPEC = _BucketSpec(capacity=40.0, refill_per_sec=20.0)
_EXPENSIVE_COMMAND_SPEC = _BucketSpec(capacity=8.0, refill_per_sec=2.0)
_PER_COMMAND_SPECS: dict[str, _BucketSpec] = {
                                                                          
    ClientCommand.VIEWPORT_UPDATE.value: _BucketSpec(capacity=40.0, refill_per_sec=25.0),
    ClientCommand.FOG_PAINT.value: _BucketSpec(capacity=30.0, refill_per_sec=15.0),
    ClientCommand.TOKEN_MOVE.value: _BucketSpec(capacity=40.0, refill_per_sec=20.0),
    ClientCommand.CHUNK_ACK.value: _BucketSpec(capacity=120.0, refill_per_sec=80.0),
    ClientCommand.CHUNK_NACK.value: _BucketSpec(capacity=120.0, refill_per_sec=80.0),
}


@dataclass(frozen=True)
class IngressDecision:
    """Outcome of inspecting a single raw client frame.

    Exactly one of these terminal states applies:
    - ``close_code`` set  → close the socket with that code (oversized / policy).
    - ``error`` set       → send the error envelope and keep the connection open.
    - ``message`` set      → forward the parsed JSON message to the dispatchers.
    """

    close_code: int | None = None
    close_reason: str | None = None
    error: dict[str, Any] | None = None
    message: dict[str, Any] | None = None

    @property
    def should_close(self) -> bool:
        return self.close_code is not None


def is_origin_allowed(origin: str | None, allowed_origins: tuple[str, ...]) -> bool:
    """Validate the handshake ``Origin`` against an allowlist.

    An empty allowlist means "not configured" and is treated as allow-all so
    local development keeps working; production should set ``WS_ALLOWED_ORIGINS``
    (or ``ALLOWED_HOSTS``, from which origins are derived).
    """
    if not allowed_origins:
        return True
    if not origin:
                                                                             
                                                                               
        return False
    normalized_origin = origin.rstrip("/")
    origin_parts = urlsplit(normalized_origin)
    if not origin_parts.scheme or not origin_parts.hostname:
        return False

    for allowed in allowed_origins:
        normalized_allowed = allowed.rstrip("/")
        allowed_parts = urlsplit(normalized_allowed)
        if not allowed_parts.scheme or not allowed_parts.hostname:
            if normalized_origin == normalized_allowed:
                return True
            continue
        if origin_parts.scheme != allowed_parts.scheme:
            continue
        if allowed_parts.port is not None and origin_parts.port != allowed_parts.port:
            continue
        if allowed_parts.port is None and origin_parts.port is not None:
            continue
        allowed_host = allowed_parts.hostname.lower()
        origin_host = origin_parts.hostname.lower()
        if allowed_host.startswith("*."):
            suffix = allowed_host[1:]
            if origin_host.endswith(suffix) and origin_host != allowed_host[2:]:
                return True
            continue
        if origin_host == allowed_host:
            return True
    return False


class WebSocketIngressGuard:
    """Per-connection guard run before every command is dispatched.

    Responsibilities: bound raw frame size, parse JSON safely, and rate-limit
    globally / per-command / for expensive commands. It never raises; callers
    act on the returned :class:`IngressDecision`.
    """

    def __init__(
        self,
        *,
        max_message_bytes: int = MAX_MESSAGE_BYTES,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_message_bytes = max_message_bytes
        self._clock = clock
        now = clock()
        self._global = _bucket(_GLOBAL_SPEC, now)
        self._expensive = _bucket(_EXPENSIVE_COMMAND_SPEC, now)
        self._by_command: dict[str, _TokenBucket] = {}

    def inspect(self, raw: str | bytes) -> IngressDecision:
        size = len(raw.encode("utf-8")) if isinstance(raw, str) else len(raw)
        if size > self._max_message_bytes:
            return IngressDecision(
                close_code=1009,
                close_reason="Message too large.",
            )

        try:
            message = json.loads(raw)
        except (ValueError, TypeError):
            return IngressDecision(
                error=error_envelope(
                    command_id=None,
                    code="invalid_payload",
                    message="Message must be valid JSON.",
                )
            )

        if not isinstance(message, dict):
            return IngressDecision(
                error=error_envelope(
                    command_id=None,
                    code="invalid_payload",
                    message="Command envelope must be an object.",
                )
            )

        command_id = message.get("id") if isinstance(message.get("id"), str) else None
        command = message.get("command")
        command = command if isinstance(command, str) else None

        rate_error = self._check_rate(command=command, command_id=command_id)
        if rate_error is not None:
            return IngressDecision(error=rate_error)

        return IngressDecision(message=message)

    def _check_rate(
        self,
        *,
        command: str | None,
        command_id: str | None,
    ) -> dict[str, Any] | None:
        now = self._clock()

        if not self._global.allow(now=now):
            return self._rate_limited(command_id, "connection")

        if command is None:
            return None

        if command in EXPENSIVE_COMMANDS and not self._expensive.allow(now=now):
            return self._rate_limited(command_id, "expensive")

        bucket = self._by_command.get(command)
        if bucket is None:
            spec = _PER_COMMAND_SPECS.get(command, _DEFAULT_COMMAND_SPEC)
            bucket = _bucket(spec, now)
            self._by_command[command] = bucket

        if not bucket.allow(now=now):
            return self._rate_limited(command_id, "command")

        return None

    @staticmethod
    def _rate_limited(command_id: str | None, scope: str) -> dict[str, Any]:
        return error_envelope(
            command_id=command_id,
            code="rate_limited",
            message=f"Too many requests ({scope}). Slow down.",
        )


def _bucket(spec: _BucketSpec, now: float) -> _TokenBucket:
    return _TokenBucket(
        capacity=spec.capacity,
        refill_per_sec=spec.refill_per_sec,
        tokens=spec.capacity,
        updated_at=now,
    )
