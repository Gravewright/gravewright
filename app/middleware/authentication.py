from __future__ import annotations

import time
from collections import OrderedDict
from app.persistence.rows import Row

from litestar.connection import ASGIConnection
from litestar.middleware import AbstractAuthenticationMiddleware, AuthenticationResult

from app.persistence.repositories.user_repository import UserRepository


def _as_row(mapping: dict) -> dict:
    """Materialise repository mappings as plain dicts at the auth boundary."""
    return dict(mapping)

                                                                               
                                                                                
                                                                                  
                                                                                 
                                                                      
_USER_CACHE: OrderedDict[str, tuple[Row, float]] = OrderedDict()
_USER_CACHE_TTL = 30.0
_USER_CACHE_MAX = 10_000


def _cached_user(user_id: str) -> Row | None:
    now = time.monotonic()
    entry = _USER_CACHE.get(user_id)
    if entry is not None and entry[1] > now:
        return entry[0]

    loaded = UserRepository().get_by_id(user_id)
    user = _as_row(loaded) if loaded is not None else None
    if user is not None:
        if len(_USER_CACHE) >= _USER_CACHE_MAX:
            _USER_CACHE.popitem(last=False)
        _USER_CACHE[user_id] = (user, now + _USER_CACHE_TTL)
    return user


class AuthenticationMiddleware(AbstractAuthenticationMiddleware):
    """Resolves the current user from the server-side session once per request.

    The session middleware (ServerSideSessionConfig) runs first and populates
    ``scope["session"]`` with the session dict; we read ``user_id`` from it and
    expose the loaded user as ``connection.user`` (a row mapping or ``None``) and the
    session dict as ``connection.auth``. Route protection is enforced by the
    ``require_user`` guard, not here.
    """

    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:
        session: dict = connection.scope.get("session") or {}
        user_id = session.get("user_id")
        user: Row | None = _cached_user(user_id) if user_id else None
        return AuthenticationResult(user=user, auth=session)
