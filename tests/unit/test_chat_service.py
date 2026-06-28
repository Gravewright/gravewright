from __future__ import annotations

import pytest

from app.domain.chat import ChatVisibility
from app.domain.roles import PlayerRole
from app.engine.chat.chat_service import ChatService
from app.persistence.repositories.chat_message_repository import ChatMessageRepository
from app.realtime.events import TransportEvent
from tests.conftest import seed_campaign, seed_member, seed_user


class MockTransport:
    def __init__(self) -> None:
        self.room_messages: list[dict] = []
        self.gm_messages: list[dict] = []
        self.room_events: list[dict] = []
        self.whispers: list[dict] = []

    async def chat_to_room(self, room_id, message):
        self.room_messages.append({"room_id": room_id, "visibility": "public", **message})

    async def chat_to_gm(self, room_id, message):
        self.gm_messages.append({"room_id": room_id, "visibility": "gm_only", **message})

    async def chat_whisper(self, room_id, sender_player_id, target_player_ids, message):
        self.whispers.append(
            {
                "room_id": room_id,
                "sender": sender_player_id,
                "targets": list(target_player_ids),
                **message,
            }
        )

    async def chat_system(self, room_id, message, target_player_ids=None):
        pass

    async def to_player(self, player_id, event, payload):
        pass

    async def to_players(self, player_ids, event, payload):
        pass

    async def to_room(self, room_id, event, payload):
        self.room_events.append({"room_id": room_id, "event": event, "payload": payload})

    async def to_room_except(self, room_id, excluded_player_ids, event, payload):
        pass

    async def to_role(self, room_id, role, event, payload):
        pass

    async def to_gm(self, room_id, event, payload):
        pass

    async def to_players_in_room(self, room_id, event, payload):
        pass

    async def to_streamers(self, room_id, event, payload):
        pass

    async def is_player_connected(self, player_id):
        return False


@pytest.fixture
def transport():
    return MockTransport()


async def test_public_message_saved_and_emitted(db, transport):
    gm_id = seed_user(name="GM", email="gm@test.com")
    campaign_id = seed_campaign(gm_id)

    result = await ChatService().send_message(
        campaign_id=campaign_id,
        sender_user_id=gm_id,
        sender_name="GM",
        content="Hello world",
        transport=transport,
    )

    assert result.success
    assert len(transport.room_messages) == 1
    assert transport.room_messages[0]["content"] == "Hello world"
    assert transport.room_messages[0]["visibility"] == ChatVisibility.PUBLIC


async def test_system_message_saved_and_emitted(db, transport):
    gm_id = seed_user(name="GM", email="sys@test.com")
    campaign_id = seed_campaign(gm_id)

    result = await ChatService().send_system_message(
        campaign_id=campaign_id,
        content="🩸 Aria sofreu 4 de dano de fogo (HP 16).",
        transport=transport,
    )

    assert result.success
    assert len(transport.room_messages) == 1
    msg = transport.room_messages[0]
    assert msg["kind"] == "system"
    assert msg["author"] == "Sistema"
    assert "Aria sofreu 4" in msg["content"]
                                                                        
    assert ChatMessageRepository().list_for_campaign(campaign_id=campaign_id) == []


async def test_system_message_rejects_empty(db, transport):
    gm_id = seed_user(name="GM", email="sys2@test.com")
    campaign_id = seed_campaign(gm_id)
    result = await ChatService().send_system_message(
        campaign_id=campaign_id, content="   ", transport=transport
    )
    assert not result.success
    assert len(transport.room_messages) == 0


async def test_card_message_saved_with_card_metadata_and_emitted(db, transport):
    gm_id = seed_user(name="GM", email="card-chat@test.com")
    campaign_id = seed_campaign(gm_id)

    result = await ChatService().send_card_message(
        campaign_id=campaign_id,
        sender_user_id=gm_id,
        sender_name="GM",
        content="GM revealed 1 card: Ace",
        cards=[{"id": "card-1", "name": "Ace", "front_asset_id": "front"}],
        card_event={"id": "event-1", "event_type": "card.drawn"},
        transport=transport,
    )

    assert result.success
    assert len(transport.room_messages) == 1
    assert transport.room_messages[0]["metadata"]["type"] == "cards.revealed"
    messages = ChatMessageRepository().list_for_campaign(campaign_id=campaign_id)
    assert len(messages) == 1
    assert messages[0]["kind"] == "system"
    assert messages[0]["metadata"]["cards"][0]["front_asset_id"] == "front"


async def test_gm_message_only_goes_to_gm(db, transport):
    gm_id = seed_user(name="GM", email="gm@test.com")
    campaign_id = seed_campaign(gm_id)

    result = await ChatService().send_message(
        campaign_id=campaign_id,
        sender_user_id=gm_id,
        sender_name="GM",
        content="/gm secret note",
        transport=transport,
    )

    assert result.success
    assert len(transport.room_messages) == 0
    assert len(transport.gm_messages) == 1
    assert transport.gm_messages[0]["content"] == "secret note"
    assert transport.gm_messages[0]["visibility"] == ChatVisibility.GM_ONLY


async def test_emote_message_sent_to_room(db, transport):
    gm_id = seed_user(name="GM", email="gm@test.com")
    campaign_id = seed_campaign(gm_id)

    result = await ChatService().send_message(
        campaign_id=campaign_id,
        sender_user_id=gm_id,
        sender_name="GM",
        content="/me waves",
        transport=transport,
    )

    assert result.success
    assert len(transport.room_messages) == 1
    assert transport.room_messages[0]["kind"] == "emote"
    assert transport.room_messages[0]["content"] == "waves"


async def test_roll_message_sent_to_room(db, transport):
    gm_id = seed_user(name="GM", email="gm@test.com")
    campaign_id = seed_campaign(gm_id)

    result = await ChatService().send_message(
        campaign_id=campaign_id,
        sender_user_id=gm_id,
        sender_name="GM",
        content="/roll 1d6",
        transport=transport,
    )

    assert result.success
    assert len(transport.room_messages) == 1
    assert transport.room_messages[0]["kind"] == "roll"
    assert "total" in transport.room_messages[0]


async def test_r_alias_rolls_like_roll(db, transport):
    gm_id = seed_user(name="GM", email="gm-r-alias@test.com")
    campaign_id = seed_campaign(gm_id)

    result = await ChatService().send_message(
        campaign_id=campaign_id,
        sender_user_id=gm_id,
        sender_name="GM",
        content="/r 1d6",
        transport=transport,
    )

    assert result.success
    assert len(transport.room_messages) == 1
    assert transport.room_messages[0]["kind"] == "roll"
    assert "total" in transport.room_messages[0]


async def test_gmroll_is_secret_and_not_persisted(db, transport):
    gm_id = seed_user(name="GM", email="gm-gmroll@test.com")
    player_id = seed_user(name="Player", email="player-gmroll@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    result = await ChatService().send_message(
        campaign_id=campaign_id,
        sender_user_id=player_id,
        sender_name="Player",
        content="/gmroll 1d20",
        transport=transport,
    )

    assert result.success
    assert len(transport.room_messages) == 0
    assert len(transport.gm_messages) == 0
    assert len(transport.whispers) == 1
    whisper = transport.whispers[0]
    assert whisper["sender"] == player_id
    assert gm_id in whisper["targets"]
    assert whisper["kind"] == "roll"
    assert whisper["secret"] is True
                                               
    assert ChatMessageRepository().list_for_campaign(campaign_id=campaign_id) == []


async def test_whisper_delivered_to_named_target(db, transport):
    gm_id = seed_user(name="GM", email="gm-whisper@test.com")
    bob_id = seed_user(name="Bob", email="bob-whisper@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, bob_id, PlayerRole.PLAYER.value)

    result = await ChatService().send_message(
        campaign_id=campaign_id,
        sender_user_id=gm_id,
        sender_name="GM",
        content="/w Bob hello there",
        transport=transport,
    )

    assert result.success
    assert len(transport.whispers) == 1
    whisper = transport.whispers[0]
    assert whisper["sender"] == gm_id
    assert whisper["targets"] == [bob_id]
    assert whisper["content"] == "hello there"
    assert whisper["target_names"] == ["Bob"]
    assert ChatMessageRepository().list_for_campaign(campaign_id=campaign_id) == []


async def test_whisper_to_name_with_spaces(db, transport):
    gm_id = seed_user(name="GM", email="gm-whisper-space@test.com")
    target_id = seed_user(name="Mary Jane", email="mj-whisper@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, target_id, PlayerRole.PLAYER.value)

    result = await ChatService().send_message(
        campaign_id=campaign_id,
        sender_user_id=gm_id,
        sender_name="GM",
        content="/w Mary Jane watch out",
        transport=transport,
    )

    assert result.success
    assert transport.whispers[0]["targets"] == [target_id]
    assert transport.whispers[0]["content"] == "watch out"


async def test_whisper_unknown_target_rejected(db, transport):
    gm_id = seed_user(name="GM", email="gm-whisper-bad@test.com")
    campaign_id = seed_campaign(gm_id)

    result = await ChatService().send_message(
        campaign_id=campaign_id,
        sender_user_id=gm_id,
        sender_name="GM",
        content="/w Nobody hello",
        transport=transport,
    )

    assert not result.success
    assert result.error_key == "game.chat.errors.invalid_whisper_target"
    assert len(transport.whispers) == 0


async def test_whisper_without_message_rejected(db, transport):
    gm_id = seed_user(name="GM", email="gm-whisper-empty@test.com")
    bob_id = seed_user(name="Bob", email="bob-whisper-empty@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, bob_id, PlayerRole.PLAYER.value)

    result = await ChatService().send_message(
        campaign_id=campaign_id,
        sender_user_id=gm_id,
        sender_name="GM",
        content="/w Bob",
        transport=transport,
    )

    assert not result.success
    assert result.error_key == "game.chat.errors.empty_message"


async def test_non_member_cannot_send_message(db, transport):
    gm_id = seed_user(name="GM", email="gm@test.com")
    outsider_id = seed_user(name="Outsider", email="out@test.com")
    campaign_id = seed_campaign(gm_id)

    result = await ChatService().send_message(
        campaign_id=campaign_id,
        sender_user_id=outsider_id,
        sender_name="Outsider",
        content="Hello",
        transport=transport,
    )

    assert not result.success
    assert result.error_key == "game.chat.errors.not_a_member"
    assert len(transport.room_messages) == 0


async def test_empty_message_rejected(db, transport):
    gm_id = seed_user(name="GM", email="gm@test.com")
    campaign_id = seed_campaign(gm_id)

    result = await ChatService().send_message(
        campaign_id=campaign_id,
        sender_user_id=gm_id,
        sender_name="GM",
        content="   ",
        transport=transport,
    )

    assert not result.success
    assert result.error_key == "game.chat.errors.empty_message"


async def test_chat_visibility_consistent(db, transport):
    gm_id = seed_user(name="GM", email="gm@test.com")
    campaign_id = seed_campaign(gm_id)

    await ChatService().send_message(
        campaign_id=campaign_id,
        sender_user_id=gm_id,
        sender_name="GM",
        content="Public",
        transport=transport,
    )

    messages = ChatMessageRepository().list_for_campaign(campaign_id=campaign_id)
    assert messages[0]["visibility"] == ChatVisibility.PUBLIC


async def test_author_can_delete_own_message(db, transport):
    gm_id = seed_user(name="GM", email="gm-delete-own@test.com")
    player_id = seed_user(name="Player", email="player-delete-own@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    await ChatService().send_message(
        campaign_id=campaign_id,
        sender_user_id=player_id,
        sender_name="Player",
        content="remove me",
        transport=transport,
    )
    message_id = ChatMessageRepository().list_for_campaign(campaign_id=campaign_id)[0]["id"]

    result = await ChatService().delete_message(
        campaign_id=campaign_id,
        user_id=player_id,
        message_id=message_id,
        transport=transport,
    )

    assert result.success
    assert ChatMessageRepository().list_for_campaign(campaign_id=campaign_id) == []
    assert transport.room_events[-1]["event"] == TransportEvent.CHAT_MESSAGE_DELETED
    assert transport.room_events[-1]["payload"]["message_id"] == message_id


async def test_player_cannot_delete_other_user_message(db, transport):
    gm_id = seed_user(name="GM", email="gm-delete-other@test.com")
    author_id = seed_user(name="Author", email="author-delete-other@test.com")
    other_id = seed_user(name="Other", email="other-delete-other@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, author_id, PlayerRole.PLAYER.value)
    seed_member(campaign_id, other_id, PlayerRole.PLAYER.value)

    await ChatService().send_message(
        campaign_id=campaign_id,
        sender_user_id=author_id,
        sender_name="Author",
        content="keep me",
        transport=transport,
    )
    message_id = ChatMessageRepository().list_for_campaign(campaign_id=campaign_id)[0]["id"]

    result = await ChatService().delete_message(
        campaign_id=campaign_id,
        user_id=other_id,
        message_id=message_id,
        transport=transport,
    )

    assert not result.success
    assert result.error_key == "permissions.errors.denied"
    assert len(ChatMessageRepository().list_for_campaign(campaign_id=campaign_id)) == 1


async def test_gm_can_clear_all_messages(db, transport):
    gm_id = seed_user(name="GM", email="gm-clear-chat@test.com")
    campaign_id = seed_campaign(gm_id)

    service = ChatService()
    await service.send_message(
        campaign_id=campaign_id,
        sender_user_id=gm_id,
        sender_name="GM",
        content="one",
        transport=transport,
    )
    await service.send_message(
        campaign_id=campaign_id,
        sender_user_id=gm_id,
        sender_name="GM",
        content="two",
        transport=transport,
    )

    result = await ChatService().clear_messages(
        campaign_id=campaign_id,
        user_id=gm_id,
        transport=transport,
    )

    assert result.success
    assert ChatMessageRepository().list_for_campaign(campaign_id=campaign_id) == []
    assert transport.room_events[-1]["event"] == TransportEvent.CHAT_MESSAGES_CLEARED
    assert transport.room_events[-1]["payload"]["room_id"] == campaign_id
