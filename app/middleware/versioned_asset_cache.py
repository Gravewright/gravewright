from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import parse_qs


ASGIApp = Callable[
    [dict[str, Any], Callable[..., Awaitable[Any]], Callable[..., Awaitable[Any]]],
    Awaitable[Any],
]


class VersionedAssetCacheMiddleware:
    """Cache immutable assets only when their URL carries an explicit version."""

    CACHE_CONTROL = b"public, max-age=31536000, immutable"
    PREFIXES = ("/static/", "/sdk/packages/")

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[..., Awaitable[Any]],
        send: Callable[..., Awaitable[Any]],
    ) -> None:
        if scope.get("type") != "http" or scope.get("method") not in {"GET", "HEAD"}:
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path") or "")
        query = parse_qs(bytes(scope.get("query_string") or b"").decode("latin-1"))
        versioned = path.startswith(self.PREFIXES) and bool(query.get("v", [""])[0])
        if not versioned:
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message.get("type") == "http.response.start" and int(message.get("status", 0)) < 400:
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"cache-control"
                ]
                headers.append((b"cache-control", self.CACHE_CONTROL))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
