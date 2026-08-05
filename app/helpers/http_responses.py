"""Shared HTTP/JSON response helpers (maintenance plan, Etapa 7).

Centralizes the ``wants_json`` content-negotiation check and the standard JSON
envelope so action handlers stop re-implementing them. The envelope is:

    { "ok": bool, "message_key"?: str, "error_key"?: str, ...data }

so the frontend HTTP client can map outcomes consistently.
"""

from __future__ import annotations

from typing import Any

from litestar import Request
from litestar.response import Response


def wants_json(request: Request) -> bool:
    """True when the caller expects JSON (Accept header or an XHR request)."""
    accept = request.headers.get("accept", "")
    requested_with = request.headers.get("x-requested-with", "")
    return "application/json" in accept or requested_with == "XMLHttpRequest"


def json_ok(
    *,
    message_key: str | None = None,
    status_code: int = 200,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Response:
    """A success envelope: ``{"ok": True, ...}``."""
    payload: dict[str, Any] = {"ok": True}
    if message_key is not None:
        payload["message_key"] = message_key
    if data:
        payload.update(data)
    return Response(content=payload, status_code=status_code, headers=headers)


def json_error(*, error_key: str, status_code: int = 400) -> Response:
    """An error envelope: ``{"ok": False, "error_key": ...}``."""
    return Response(content={"ok": False, "error_key": error_key}, status_code=status_code)
