from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


ASGIApp = Callable[
    [dict[str, Any], Callable[..., Awaitable[Any]], Callable[..., Awaitable[Any]]],
    Awaitable[Any],
]


class SecurityHeadersMiddleware:
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

        async def send_wrapper(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])

                security_headers = {
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"DENY",
                    b"referrer-policy": b"strict-origin-when-cross-origin",
                    b"permissions-policy": b"camera=(), microphone=(), geolocation=()",
                    b"cross-origin-opener-policy": b"same-origin",
                    b"content-security-policy": (
                        b"default-src 'self'; "
                        b"script-src 'self' 'unsafe-eval' 'wasm-unsafe-eval' https://cdn.jsdelivr.net https://esm.sh; "
                        b"style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                        b"img-src 'self' data: blob:; "
                        b"font-src 'self' data: https://cdn.jsdelivr.net; "
                                                                                
                                                                              
                        b"connect-src 'self' data: blob: ws: wss: https://esm.sh https://cdn.jsdelivr.net; "
                        b"worker-src 'self' blob:; "
                        b"object-src 'none'; "
                        b"base-uri 'self'; "
                        b"frame-ancestors 'none'; "
                        b"form-action 'self'"
                    ),
                }

                existing = {key.lower() for key, _ in headers}

                for key, value in security_headers.items():
                    if key.lower() not in existing:
                        headers.append((key, value))

            await send(message)

        await self.app(scope, receive, send_wrapper)
