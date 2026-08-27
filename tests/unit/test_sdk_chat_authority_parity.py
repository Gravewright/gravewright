from __future__ import annotations

import asyncio

from litestar.testing import TestClient

from app.engine.chat.chat_service import ChatService
from app.engine.chat.visibility_policy import ChatVisibilityPolicy
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_user
from tests.unit.test_chat_service import MockTransport
from tests.unit.test_sdk_runtime_expansion import _install_runtime_addon


def _read(client, *, campaign_id, package_id, message_id=None):
    params = {"campaign_id": campaign_id, "package_id": package_id}
    if message_id:
        params["entity_id"] = message_id
    return client.get("/sdk/runtime/read/chat", params=params)


def test_gmroll_event_get_list_and_native_policy_share_authority(db, tmp_path, monkeypatch):
    from app.persistence.repositories.chat_message_repository import ChatMessageRepository
    from main import app

    gm = seed_user(name="GM")
    sender = seed_user(name="Sender")
    unrelated = seed_user(name="Unrelated")
    outsider = seed_user(name="Outsider")
    campaign = seed_campaign(gm)
    seed_member(campaign, sender, "player")
    seed_member(campaign, unrelated, "player")
    other_campaign = seed_campaign(outsider)
    transport = MockTransport()
    result = asyncio.run(ChatService().send_message(
        campaign_id=campaign, sender_user_id=sender, sender_name="Sender",
        content="/gmroll 1d20", transport=transport,
    ))
    assert result.success
    assert len(transport.whispers) == 1
    event_audience = {sender, *transport.whispers[0]["targets"]}
    assert event_audience == {sender, gm}
    message = ChatMessageRepository().list_for_campaign(campaign_id=campaign)[0]
    message_id = message["id"]
    assert ChatVisibilityPolicy.can_view(message=message, user_id=gm, member_role="gm")
    assert ChatVisibilityPolicy.can_view(message=message, user_id=sender, member_role="player")
    assert not ChatVisibilityPolicy.can_view(message=message, user_id=unrelated, member_role="player")

    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, ["chat.read"])
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        for authorized in (gm, sender):
            login(client, authorized)
            assert _read(client, campaign_id=campaign, package_id="runtime-addon", message_id=message_id).status_code == 200
            listed = _read(client, campaign_id=campaign, package_id="runtime-addon").json()["messages"]
            assert message_id in {entry["id"] for entry in listed}
        login(client, unrelated)
        assert _read(client, campaign_id=campaign, package_id="runtime-addon", message_id=message_id).status_code == 404
        assert message_id not in {entry["id"] for entry in _read(client, campaign_id=campaign, package_id="runtime-addon").json()["messages"]}
        login(client, outsider)
        assert _read(client, campaign_id=campaign, package_id="runtime-addon", message_id=message_id).status_code == 403
        assert _read(client, campaign_id=other_campaign, package_id="runtime-addon", message_id=message_id).status_code == 403


def test_whisper_sender_recipient_and_unrelated_have_coherent_readback(db, tmp_path, monkeypatch):
    from app.persistence.repositories.chat_message_repository import ChatMessageRepository
    from main import app

    sender = seed_user(name="Sender")
    recipient = seed_user(name="Recipient")
    unrelated = seed_user(name="Unrelated")
    campaign = seed_campaign(sender)
    seed_member(campaign, recipient, "player")
    seed_member(campaign, unrelated, "player")
    transport = MockTransport()
    result = asyncio.run(ChatService().send_message(
        campaign_id=campaign, sender_user_id=sender, sender_name="Sender",
        content="/w Recipient secret words", transport=transport,
    ))
    assert result.success
    assert {sender, *transport.whispers[0]["targets"]} == {sender, recipient}
    message = ChatMessageRepository().list_for_campaign(campaign_id=campaign)[0]
    message_id = message["id"]
    assert "_audience_user_ids" not in message["metadata"]

    _install_runtime_addon(tmp_path, monkeypatch, sender, campaign, ["chat.read"])
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        for authorized in (sender, recipient):
            login(client, authorized)
            fetched = _read(client, campaign_id=campaign, package_id="runtime-addon", message_id=message_id)
            assert fetched.status_code == 200
            assert "_audience_user_ids" not in fetched.text
            assert message_id in {entry["id"] for entry in _read(client, campaign_id=campaign, package_id="runtime-addon").json()["messages"]}
        login(client, unrelated)
        assert _read(client, campaign_id=campaign, package_id="runtime-addon", message_id=message_id).status_code == 404
        assert message_id not in {entry["id"] for entry in _read(client, campaign_id=campaign, package_id="runtime-addon").json()["messages"]}


def test_visibility_policy_rejects_forged_deleted_unknown_and_cross_audience_shapes():
    base = {"author_user_id": "author", "visibility": "whisper", "_audience_user_ids": ["recipient"]}
    assert ChatVisibilityPolicy.can_view(message=base, user_id="author", member_role="player")
    assert ChatVisibilityPolicy.can_view(message=base, user_id="recipient", member_role="player")
    assert not ChatVisibilityPolicy.can_view(message=base, user_id="forged", member_role="player")
    assert not ChatVisibilityPolicy.can_view(message=base, user_id="recipient", member_role=None)
