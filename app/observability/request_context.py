"""Per-request correlation id, propagated via a context variable.

Set by ``RequestIdMiddleware`` at the edge and read by ``emit_diagnostic`` so
every structured log line and audit event can be correlated to one request
without carrying any sensitive data (maintenance plan, Etapa 10).
"""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar, Token

_request_id: ContextVar[str | None] = ContextVar("gravewright_request_id", default=None)

_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9._-]{1,64}$")


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def sanitize_request_id(value: str | None) -> str | None:
    """Constrain an inbound id to safe characters and length (avoid log injection)."""
    if not value:
        return None
    return value if _SAFE_ID_RE.fullmatch(value) else None


def set_request_id(value: str | None) -> Token[str | None]:
    """Set the correlation id and return the token needed to restore context."""
    return _request_id.set(value)


def reset_request_id(token: Token[str | None]) -> None:
    """Restore the exact context that existed before :func:`set_request_id`."""
    _request_id.reset(token)


def get_request_id() -> str | None:
    return _request_id.get()
