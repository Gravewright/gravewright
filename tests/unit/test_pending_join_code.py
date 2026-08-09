from __future__ import annotations

from app.helpers.pending_join_code import (
    PENDING_JOIN_CODE_CREATED_AT_KEY,
    PENDING_JOIN_CODE_KEY,
    PENDING_JOIN_CODE_TTL_SECONDS,
    clear_pending_join_code,
    get_pending_join_code,
    store_pending_join_code,
)


def test_pending_join_code_has_short_ttl(monkeypatch):
    monkeypatch.setattr("app.helpers.pending_join_code.time.time", lambda: 1_000)
    session = store_pending_join_code({"user_id": "user-1"}, " abcd-efgh-jk23 ")
    assert session[PENDING_JOIN_CODE_KEY] == "abcd-efgh-jk23"
    assert get_pending_join_code(session, now=1_000 + PENDING_JOIN_CODE_TTL_SECONDS) == (
        "abcd-efgh-jk23"
    )
    assert get_pending_join_code(session, now=1_001 + PENDING_JOIN_CODE_TTL_SECONDS) is None


def test_clearing_pending_code_preserves_other_session_data():
    session = {
        "user_id": "user-1",
        PENDING_JOIN_CODE_KEY: "ABCD-EFGH-JK23",
        PENDING_JOIN_CODE_CREATED_AT_KEY: 1_000,
    }
    assert clear_pending_join_code(session) == {"user_id": "user-1"}
