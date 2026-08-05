from __future__ import annotations

from app.persistence.rows import Row
from typing import Any

from litestar.connection import ASGIConnection, Request
from litestar.exceptions import NotAuthorizedException
from litestar.handlers.base import BaseRouteHandler
from litestar.response import Redirect, Response

SESSION_EXPIRED_KEY = "auth.errors.session_expired"


def provide_current_user(request: Request[Any, Any, Any]) -> Row | None:
    """DI provider: the authenticated user resolved by ``AuthenticationMiddleware``.

    Returns ``None`` for anonymous visitors. Use the ``require_user`` guard on a
    route to guarantee a non-null value.
    """
    return request.scope.get("user")


def provide_session(request: Request[Any, Any, Any]) -> Row | None:
    """DI provider: the current session row resolved by ``AuthenticationMiddleware``."""
    return request.scope.get("auth")


def require_user(connection: ASGIConnection, _: BaseRouteHandler) -> None:
    """Guard: reject the request unless an authenticated user is present.

    Raises ``NotAuthorizedException`` (handled by ``auth_exception_handler``, which
    redirects browser navigations to /login and returns a 401 JSON body to API calls).
    """
    if connection.scope.get("user") is None:
        raise NotAuthorizedException(detail=SESSION_EXPIRED_KEY)


def auth_exception_handler(request: Request[Any, Any, Any], exc: NotAuthorizedException) -> Response:
    """Render an auth failure as a login redirect for browsers, JSON 401 otherwise.

    The JSON body carries both ``ok: False`` and ``error_key`` so it is a superset of
    every shape the hand-rolled per-handler checks used to return.
    """
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return Redirect(path="/login")
    return Response({"ok": False, "error_key": SESSION_EXPIRED_KEY}, status_code=401)
