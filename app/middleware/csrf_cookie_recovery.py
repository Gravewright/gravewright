from __future__ import annotations

import hashlib
import hmac
from http.cookies import SimpleCookie
from typing import TYPE_CHECKING

from litestar.enums import ScopeType

if TYPE_CHECKING:
    from litestar.types import ASGIApp, Receive, Scope, Send


_CSRF_COOKIE_NAME = "csrftoken"
_CSRF_SECRET_LENGTH = 64
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class CSRFCookieRecoveryMiddleware:
    """Discard CSRF cookies signed by another local installation.

    Windows source installs share ``localhost:8000`` while each installation
    owns a different session secret. Litestar otherwise keeps an old cookie on
    safe requests, making the next form submission fail with a 403.
    """

    def __init__(self, app: ASGIApp, *, secret: str) -> None:
        self.app = app
        self.secret = secret

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == ScopeType.HTTP and scope.get("method") in _SAFE_METHODS:
            self._remove_invalid_csrf_cookie(scope)
        await self.app(scope, receive, send)

    def _remove_invalid_csrf_cookie(self, scope: Scope) -> None:
        headers = list(scope.get("headers", ()))
        for index, (name, value) in enumerate(headers):
            if name.lower() != b"cookie":
                continue
            cookies = SimpleCookie()
            cookies.load(value.decode("latin-1"))
            morsel = cookies.get(_CSRF_COOKIE_NAME)
            if morsel is None or self._is_valid(morsel.value):
                return
            del cookies[_CSRF_COOKIE_NAME]
            replacement = "; ".join(f"{key}={item.value}" for key, item in cookies.items())
            if replacement:
                headers[index] = (name, replacement.encode("latin-1"))
            else:
                del headers[index]
            scope["headers"] = headers
            return

    def _is_valid(self, token: str) -> bool:
        if len(token) < (_CSRF_SECRET_LENGTH * 2) + 1:
            return False
        token_secret = token[:_CSRF_SECRET_LENGTH]
        supplied_hash = token[_CSRF_SECRET_LENGTH:]
        expected_hash = hmac.new(
            self.secret.encode(), token_secret.encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(supplied_hash, expected_hash)
