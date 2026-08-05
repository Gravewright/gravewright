from __future__ import annotations

"""Observability & operational security (Maintenance Plan - Etapa 10).

Correlation ids propagate into diagnostics (including offloaded work), audit
events carry actor/result/context, and sensitive fields are redacted before they
reach the ring buffer or the logs.
"""

import logging

import pytest
from litestar.testing import TestClient

from app.observability.audit import emit_audit
from app.observability.diagnostics import diagnostics_recorder, emit_diagnostic
from app.observability.request_context import get_request_id, set_request_id


@pytest.fixture(autouse=True)
def _clean_diagnostics():
    diagnostics_recorder.clear()
    set_request_id(None)
    yield
    diagnostics_recorder.clear()
    set_request_id(None)


def _last_event() -> dict:
    return diagnostics_recorder.recent(limit=1)[-1]


def test_sensitive_fields_are_redacted():
    emit_diagnostic(
        "test.redaction",
        user_id="u1",
        token="super-secret-token",
        password="hunter2",
        cookie="sid=abc",
        session_secret="xyz",
        authorization="Bearer abc",
        email="a@b.test",
    )
    event = _last_event()
    assert event["user_id"] == "u1"
    for key in ("token", "password", "cookie", "session_secret", "authorization", "email"):
        assert event[key] == "[redacted]", f"{key} should be redacted"


def test_benign_code_fields_are_not_redacted():
    # WebSocket close codes / error codes are useful, non-sensitive diagnostics.
    emit_diagnostic("test.codes", code=1008, error_code="rate_limited", user_id="u1")
    event = _last_event()
    assert event["code"] == 1008
    assert event["error_code"] == "rate_limited"


def test_nested_sensitive_fields_are_redacted():
    emit_diagnostic("test.nested", context={"api_key": "k", "ok": 1}, items=[{"token": "t"}])
    event = _last_event()
    assert event["context"]["api_key"] == "[redacted]"
    assert event["context"]["ok"] == 1
    assert event["items"][0]["token"] == "[redacted]"


def test_request_id_is_attached_to_diagnostics():
    set_request_id("rid-abc123")
    emit_diagnostic("test.correlated", user_id="u1")
    assert _last_event()["request_id"] == "rid-abc123"


def test_redacted_value_absent_from_log_line(caplog):
    with caplog.at_level(logging.INFO, logger="gravewright.diagnostics"):
        emit_diagnostic("test.log", token="THE-SECRET-VALUE")
    combined = "\n".join(record.getMessage() for record in caplog.records)
    assert "THE-SECRET-VALUE" not in combined
    assert "[redacted]" in combined


def test_emit_audit_event_shape():
    emit_audit("membership.created", actor_id="u1", campaign_id="c1", via="invitation")
    event = _last_event()
    assert event["event"] == "audit.membership.created"
    assert event["actor_id"] == "u1"
    assert event["result"] == "ok"
    assert event["campaign_id"] == "c1"


def test_ban_audit_records_actor_target_campaign_and_request(db):
    from app.business.campaigns.campaign_service import CampaignService
    from tests.conftest import seed_campaign, seed_member, seed_user

    gm_id = seed_user(name="GM")
    player_id = seed_user(name="Player")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, "player")
    set_request_id("rid-ban")

    result = CampaignService().ban_member(
        campaign_id=campaign_id,
        requester_user_id=gm_id,
        target_user_id=player_id,
    )

    assert result.success is True
    event = _last_event()
    assert event["event"] == "audit.membership.banned"
    assert event["actor_id"] == gm_id
    assert event["target_user_id"] == player_id
    assert event["campaign_id"] == campaign_id
    assert event["request_id"] == "rid-ban"
    assert event["result"] == "success"


@pytest.mark.asyncio
async def test_request_id_propagates_into_offloaded_work():
    from app.helpers.async_blocking import run_blocking

    set_request_id("rid-offload")
    got = await run_blocking(get_request_id)
    assert got == "rid-offload"


def test_response_carries_request_id_header(db):
    from main import app

    with TestClient(app=app) as client:
        resp = client.get("/login")
    assert resp.headers.get("x-request-id")
