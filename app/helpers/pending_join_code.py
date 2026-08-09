from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any


PENDING_JOIN_CODE_KEY = "pending_campaign_join_code"
PENDING_JOIN_CODE_CREATED_AT_KEY = "pending_campaign_join_code_created_at"
PENDING_JOIN_CODE_TTL_SECONDS = 15 * 60


def store_pending_join_code(session: Mapping[str, Any], code: str) -> dict[str, Any]:
    updated = dict(session)
    updated[PENDING_JOIN_CODE_KEY] = code.strip()
    updated[PENDING_JOIN_CODE_CREATED_AT_KEY] = int(time.time())
    return updated


def get_pending_join_code(session: Mapping[str, Any], *, now: int | None = None) -> str | None:
    code = session.get(PENDING_JOIN_CODE_KEY)
    created_at = session.get(PENDING_JOIN_CODE_CREATED_AT_KEY)
    if not isinstance(code, str) or not code.strip() or not isinstance(created_at, int):
        return None
    current = int(time.time()) if now is None else now
    if created_at > current or current - created_at > PENDING_JOIN_CODE_TTL_SECONDS:
        return None
    return code.strip()


def clear_pending_join_code(session: Mapping[str, Any]) -> dict[str, Any]:
    updated = dict(session)
    updated.pop(PENDING_JOIN_CODE_KEY, None)
    updated.pop(PENDING_JOIN_CODE_CREATED_AT_KEY, None)
    return updated
