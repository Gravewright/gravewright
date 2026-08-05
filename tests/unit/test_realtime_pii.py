from __future__ import annotations

"""Realtime PII minimization contract (Maintenance Plan - Etapa 4).

Presence/membership snapshots and events must not carry email or other PII. The
frontend roster only needs ``user_id``, ``name``, ``role`` and ``is_online``.
These tests fail if a sensitive key or an email value leaks into those payloads.
"""

import json


from app.actions.game.websocket import _members_by_campaign
from app.business.game_page_service import GamePageService
from app.realtime.payloads import MemberPlayerData, PresencePlayerData
from tests.conftest import seed_campaign, seed_user

_FORBIDDEN_KEYS = {"email", "password", "password_hash", "token", "session_secret", "code"}
_ALLOWED_MEMBER_KEYS = {"user_id", "name", "role", "is_online"}


def _assert_no_pii(payload, *, email: str) -> None:
    """No forbidden key anywhere, and the raw email value must be absent."""

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                assert key not in _FORBIDDEN_KEYS, f"forbidden key '{key}' in payload"
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    assert email not in json.dumps(payload), "email value leaked into payload JSON"
    assert "@" not in json.dumps(payload), "an email-looking value leaked into payload JSON"


def test_member_player_data_contract_has_no_pii():
    assert "email" not in MemberPlayerData.__annotations__
    assert set(MemberPlayerData.__annotations__) == _ALLOWED_MEMBER_KEYS
    assert "email" not in PresencePlayerData.__annotations__


def test_websocket_member_snapshot_drops_email_even_if_source_has_it():
    # The source row still *could* carry email (from a wider query); the snapshot
    # builder must not propagate it into the client-facing payload.
    leaky_member = {
        "campaign_id": "c1",
        "user_id": "u1",
        "name": "Alice",
        "role": "gm",
        "email": "alice@example.test",
    }
    grouped = _members_by_campaign(
        members=[leaky_member],
        online_user_ids_by_room={"c1": {"u1"}},
    )
    player = grouped["c1"][0]
    assert set(player) == _ALLOWED_MEMBER_KEYS
    assert player["is_online"] is True
    _assert_no_pii(grouped, email="alice@example.test")


def test_game_page_context_members_have_no_email(db):
    email = "gm-pii@example.test"
    gm_id = seed_user(name="Roster GM", email=email)
    seed_campaign(gm_id, title="PII Campaign")

    context = GamePageService().build_context(user_id=gm_id)
    rooms = context.rooms

    all_members = [member for room in rooms for member in room["members"]]
    assert all_members, "expected at least the GM as a member"
    for member in all_members:
        assert set(member) == _ALLOWED_MEMBER_KEYS
    _assert_no_pii([room["members"] for room in rooms], email=email)
