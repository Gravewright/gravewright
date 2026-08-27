from __future__ import annotations

import uuid

from litestar.testing import TestClient

from app.engine.dice.roll_service import RollService
from app.engine.sdk.runtime_dto import chat_snapshot, roll_group_snapshot
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_user
from tests.unit.test_sdk_runtime_expansion import _install_runtime_addon


PUBLIC_KEYS = {"faces", "results", "subtotal"}


def test_roll_group_projector_allowlists_exact_public_keys():
    projected = roll_group_snapshot({
        "sides": 20,
        "results": [17],
        "subtotal": 17,
        "notation": "1d20",
        "dropped": [2],
        "other_internal_field": "secret",
    })
    assert projected == {"faces": 20, "results": [17], "subtotal": 17}
    assert set(projected) == PUBLIC_KEYS


def test_real_supported_rolls_project_faces_without_internal_fields():
    for faces in (4, 6, 8, 10, 12, 20):
        evaluated = RollService().evaluate(f"1d{faces}")
        projected = roll_group_snapshot(evaluated.groups[0])
        assert projected["faces"] == faces
        assert len(projected["results"]) == 1
        assert set(projected) == PUBLIC_KEYS


def test_multiple_mixed_dice_and_modifier_project_only_physical_groups():
    same = RollService().evaluate("2d6")
    mixed = RollService().evaluate("2d8+1d6+3")
    assert [roll_group_snapshot(group)["faces"] for group in same.groups] == [6]
    assert len(roll_group_snapshot(same.groups[0])["results"]) == 2
    assert [roll_group_snapshot(group)["faces"] for group in mixed.groups] == [8, 6]
    assert len(mixed.groups) == 2
    assert mixed.modifier == 3


def test_chat_snapshot_projects_adversarial_groups_instead_of_passing_them_through():
    internal = {
        "id": "message",
        "groups": [{"sides": 4, "results": [2], "subtotal": 2, "notation": "1d4", "dropped": [], "private": True}],
    }
    public = chat_snapshot(internal)
    assert public["groups"] == [{"faces": 4, "results": [2], "subtotal": 2}]
    assert set(public["groups"][0]) == PUBLIC_KEYS


def test_sdk_chat_get_and_list_have_identical_roll_group_shape(db, tmp_path, monkeypatch):
    from app.persistence.repositories.chat_message_repository import ChatMessageRepository
    from main import app

    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, ["chat.read"])
    evaluated = RollService().evaluate("2d8+1d6+3")
    message_id = uuid.uuid4().hex
    ChatMessageRepository().create(
        message_id=message_id,
        campaign_id=campaign,
        author_user_id=gm,
        author_name="GM",
        author_role="gm",
        kind="roll",
        content="",
        expression="2d8+1d6+3",
        groups=evaluated.groups,
        modifier=evaluated.modifier,
        total=evaluated.total,
        visibility="public",
        metadata={},
    )
    params = {"campaign_id": campaign, "package_id": "runtime-addon"}
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        fetched = client.get("/sdk/runtime/read/chat", params={**params, "entity_id": message_id})
        listed = client.get("/sdk/runtime/read/chat", params=params)
    assert fetched.status_code == listed.status_code == 200
    get_groups = fetched.json()["message"]["groups"]
    list_groups = next(message for message in listed.json()["messages"] if message["id"] == message_id)["groups"]
    assert get_groups == list_groups
    assert [group["faces"] for group in get_groups] == [8, 6]
    assert all(set(group) == PUBLIC_KEYS for group in get_groups)


def test_sdk_chat_get_allows_gm_to_reread_gm_only_roll(db, tmp_path, monkeypatch):
    from app.persistence.repositories.chat_message_repository import ChatMessageRepository
    from main import app

    gm = seed_user(name="GM")
    campaign = seed_campaign(gm)
    _install_runtime_addon(tmp_path, monkeypatch, gm, campaign, ["chat.read"])
    evaluated = RollService().evaluate("1d20")
    message_id = uuid.uuid4().hex
    ChatMessageRepository().create(
        message_id=message_id, campaign_id=campaign, author_user_id=gm,
        author_name="GM", author_role="gm", kind="roll", content="",
        expression="1d20", groups=evaluated.groups, modifier=evaluated.modifier,
        total=evaluated.total, visibility="gm_only", metadata={},
    )
    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, gm)
        fetched = client.get("/sdk/runtime/read/chat", params={
            "campaign_id": campaign, "package_id": "runtime-addon", "entity_id": message_id,
        })
    assert fetched.status_code == 200
    assert fetched.json()["message"]["groups"][0]["faces"] == 20
