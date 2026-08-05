"""Assigns a correlation id to every HTTP request.

Reads an inbound ``X-Request-ID`` (sanitized) or generates one, stores it in a
context variable for the duration of the request, and echoes it back on the
response so a client/log can be correlated to server-side diagnostics.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from app.observability.request_context import (
    new_request_id,
    reset_request_id,
    sanitize_request_id,
    set_request_id,
)

ASGIApp = Callable[
    [dict[str, Any], Callable[..., Awaitable[Any]], Callable[..., Awaitable[Any]]],
    Awaitable[Any],
]


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[..., Awaitable[Any]],
        send: Callable[..., Awaitable[Any]],
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        inbound = headers.get(b"x-request-id")
        request_id = (
            sanitize_request_id(inbound.decode("latin-1")) if inbound else None
        ) or new_request_id()
        token = set_request_id(request_id)

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                response_headers = [
                    (name, value)
                    for name, value in (message.get("headers") or [])
                    if name.lower() != b"x-request-id"
                ]
                response_headers.append((b"x-request-id", request_id.encode("latin-1")))
                message["headers"] = response_headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            reset_request_id(token)
