from __future__ import annotations

"""Standard JSON envelope + HTTP client contract (Maintenance Plan - Etapa 7).

Backend: the invitation endpoints answer JSON callers with the
``{"ok": ..., "message_key"|"error_key": ...}`` envelope, and an unauthenticated
JSON request is a clean 401 (session expired), not an ambiguous failure.

Frontend (source guards, since the repo has no JS test runner): the central HTTP
client maps status codes to canonical error keys, and the invitation form uses it
and no longer mis-reports transport failures as "invalid email".
"""

import types
from pathlib import Path

from litestar.middleware.csrf import generate_csrf_token
from litestar.testing import TestClient

from app.config import config
from app.helpers.http_responses import json_error, json_ok, wants_json
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_user

STATIC_JS = Path(__file__).resolve().parents[2] / "static" / "js"


# --- backend helper unit tests -------------------------------------------------

def test_wants_json_detects_accept_and_xhr():
    assert wants_json(types.SimpleNamespace(headers={"accept": "application/json"}))
    assert wants_json(types.SimpleNamespace(headers={"x-requested-with": "XMLHttpRequest"}))
    assert not wants_json(types.SimpleNamespace(headers={"accept": "text/html"}))


def test_json_ok_and_error_envelope_shapes():
    ok = json_ok(message_key="a.b")
    assert ok.status_code == 200 and ok.content == {"ok": True, "message_key": "a.b"}
    err = json_error(error_key="x.y", status_code=409)
    assert err.status_code == 409 and err.content == {"ok": False, "error_key": "x.y"}


# --- backend endpoint envelope tests ------------------------------------------

def _arm_csrf_only(client) -> None:
    token = generate_csrf_token(config.session_secret)
    client.cookies.set("csrftoken", token)
    client.headers["x-csrftoken"] = token


def test_invite_invalid_email_returns_error_envelope(db):
    from main import app

    gm_id = seed_user(name="GM", email="env-gm@test.com")
    campaign_id = seed_campaign(gm_id)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        resp = client.post(
            "/campaigns/invitations",
            data={"campaign_id": campaign_id, "email": "not-an-email", "role": "player"},
            headers={"Accept": "application/json"},
        )
    assert resp.status_code == 400
    body = resp.json()
    assert body["ok"] is False
    assert body["error_key"] == "game.invite.errors.invalid_email"


def test_invite_success_returns_ok_envelope(db):
    from main import app

    gm_id = seed_user(name="GM", email="env-gm2@test.com")
    seed_user(name="Target", email="target@test.com")
    campaign_id = seed_campaign(gm_id)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm_id)
        resp = client.post(
            "/campaigns/invitations",
            data={"campaign_id": campaign_id, "email": "target@test.com", "role": "player"},
            headers={"Accept": "application/json"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["message_key"] == "game.invite.success"


def test_accept_without_session_returns_session_expired(db):
    from main import app

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        _arm_csrf_only(client)  # pass CSRF, but no authenticated session
        resp = client.post(
            "/campaigns/invitations/accept",
            data={"invitation_id": "does-not-matter"},
            headers={"Accept": "application/json"},
        )
    assert resp.status_code == 401
    body = resp.json()
    assert body["ok"] is False
    assert body["error_key"] == "auth.errors.session_expired"


# --- frontend source guards ----------------------------------------------------

def test_http_client_maps_status_codes_to_error_keys():
    source = (STATIC_JS / "core" / "http.js").read_text(encoding="utf-8")
    assert "errorKeyForStatus" in source
    for token in [
        "auth.errors.session_expired",  # 401
        "http.errors.forbidden",  # 403
        "http.errors.conflict",  # 409
        "http.errors.rate_limited",  # 429
        "http.errors.server",  # 5xx
        "http.errors.network",  # status 0
    ]:
        assert token in source, f"missing status mapping: {token}"


def test_invitations_js_uses_central_client_and_fixes_the_bug():
    source = (STATIC_JS / "ui" / "invitations.js").read_text(encoding="utf-8")
    # Uses the central client instead of a raw fetch.
    assert "http.postForm" in source
    assert "fetch(" not in source
    # The old bug: any failure fell back to the invalid_email message. Now the
    # form-validation key only appears in the message lookup table, never as a
    # transport-failure fallback.
    assert 'getMessageForKey("game.invite.errors.invalid_email")' not in source
    assert 'getMessageForKey("http.errors.network")' in source or "result.errorKey" in source
