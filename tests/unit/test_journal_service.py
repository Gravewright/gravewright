from __future__ import annotations

import json

from app.domain.roles import PlayerRole
from app.engine.journals.journal_service import JournalService
from app.persistence.repositories.journal_repository import JournalRepository
from tests.conftest import seed_campaign, seed_member, seed_user


def test_player_creates_owned_journal(db):
    gm_id = seed_user(name="GM", email="gm-journal@test.com")
    player_id = seed_user(name="Player", email="player-journal@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    result = JournalService().create_journal(
        campaign_id=campaign_id,
        user_id=player_id,
        journal_type="diary",
        title="Session Notes",
        content_markdown="hello",
    )

    assert result.success
    assert result.journal_id is not None
    assert JournalRepository().has_owner(journal_id=result.journal_id, user_id=player_id)


def test_unlinked_player_cannot_view_or_edit_journal(db):
    gm_id = seed_user(name="GM", email="gm-journal-2@test.com")
    player_id = seed_user(name="Player", email="player-journal-2@test.com")
    other_id = seed_user(name="Other", email="other-journal-2@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    seed_member(campaign_id, other_id, PlayerRole.PLAYER.value)

    created = JournalService().create_journal(
        campaign_id=campaign_id,
        user_id=player_id,
        journal_type="diary",
        title="Private",
    )
    assert created.success
    journal = JournalRepository().get_by_id(created.journal_id)

    can_view = JournalService().can_view_journal(
        journal=journal,
        campaign={"member_role": PlayerRole.PLAYER.value},
        user_id=other_id,
    )
    update = JournalService().update_journal(
        journal_id=created.journal_id,
        user_id=other_id,
        title="Nope",
    )

    assert can_view is False
    assert not update.success
    assert update.error_key == "game.journal.errors.not_owner"


def test_gm_can_view_and_edit_player_journal(db):
    gm_id = seed_user(name="GM", email="gm-journal-3@test.com")
    player_id = seed_user(name="Player", email="player-journal-3@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    created = JournalService().create_journal(
        campaign_id=campaign_id,
        user_id=player_id,
        journal_type="quest",
        title="Find the key",
        data={"status": "available"},
    )
    assert created.success
    journal = JournalRepository().get_by_id(created.journal_id)

    can_view = JournalService().can_view_journal(
        journal=journal,
        campaign={"member_role": "gm"},
        user_id=gm_id,
    )
    update = JournalService().update_journal(
        journal_id=created.journal_id,
        user_id=gm_id,
        title="Find the silver key",
        data={"status": "active"},
        owner_user_ids=[player_id],
    )
    updated = JournalRepository().get_by_id(created.journal_id)

    assert can_view is True
    assert update.success
    assert updated["title"] == "Find the silver key"
    assert json.loads(updated["data_json"])["status"] == "active"


def test_read_only_journal_permission_can_view_but_not_edit(db):
    gm_id = seed_user(name="GM", email="gm-journal-read@test.com")
    player_id = seed_user(name="Player", email="player-journal-read@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    created = JournalService().create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="diary",
        title="Shared",
    )
    assert created.success
    permission = JournalService().set_member_access(
        journal_id=created.journal_id,
        target_user_id=player_id,
        access_level="read",
        requester_user_id=gm_id,
    )
    journal = JournalRepository().get_by_id(created.journal_id)
    can_view = JournalService().can_view_journal(
        journal=journal,
        campaign={"member_role": PlayerRole.PLAYER.value},
        user_id=player_id,
    )
    can_edit = JournalService().can_edit_journal(
        journal=journal,
        campaign={"member_role": PlayerRole.PLAYER.value},
        user_id=player_id,
    )
    update = JournalService().update_journal(
        journal_id=created.journal_id,
        user_id=player_id,
        title="Nope",
    )

    assert permission.success
    assert can_view is True
    assert can_edit is False
    assert not update.success
    assert update.error_key == "game.journal.errors.not_owner"


def test_owner_journal_permission_can_edit(db):
    gm_id = seed_user(name="GM", email="gm-journal-owner@test.com")
    player_id = seed_user(name="Player", email="player-journal-owner@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    created = JournalService().create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="diary",
        title="Owned",
    )
    assert created.success
    permission = JournalService().set_member_access(
        journal_id=created.journal_id,
        target_user_id=player_id,
        access_level="owner",
        requester_user_id=gm_id,
    )
    update = JournalService().update_journal(
        journal_id=created.journal_id,
        user_id=player_id,
        title="Edited",
    )

    assert permission.success
    assert update.success


def test_gm_edit_does_not_clear_resource_permissions(db):
    gm_id = seed_user(name="GM", email="gm-journal-keep-owner@test.com")
    player_id = seed_user(name="Player", email="player-journal-keep-owner@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    created = JournalService().create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="diary",
        title="Shared",
    )
    assert created.success
    assert JournalService().set_member_access(
        journal_id=created.journal_id,
        target_user_id=player_id,
        access_level="owner",
        requester_user_id=gm_id,
    ).success

    update = JournalService().update_journal(
        journal_id=created.journal_id,
        user_id=gm_id,
        title="Shared updated",
    )

    assert update.success
    assert JournalRepository().has_owner(journal_id=created.journal_id, user_id=player_id)


def test_shared_visibility_lets_any_player_view(db):
    gm_id = seed_user(name="GM", email="gm-journal-shared@test.com")
    player_id = seed_user(name="Player", email="player-journal-shared@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    created = JournalService().create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="diary",
        title="Lore",
        visibility="shared",
        content_markdown="Public lore",
    )
    assert created.success
    journal = JournalRepository().get_by_id(created.journal_id)

    can_view = JournalService().can_view_journal(
        journal=journal,
        campaign={"member_role": PlayerRole.PLAYER.value},
        user_id=player_id,
    )
    can_edit = JournalService().can_edit_journal(
        journal=journal,
        campaign={"member_role": PlayerRole.PLAYER.value},
        user_id=player_id,
    )
    assert can_view is True
    assert can_edit is False


def test_quest_player_view_strips_gm_and_hidden_items(db):
    gm_id = seed_user(name="GM", email="gm-journal-view@test.com")
    player_id = seed_user(name="Player", email="player-journal-view@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    created = JournalService().create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="quest",
        title="The Crypt",
        visibility="shared",
        data={
            "status": "available",
            "public": {"summary": "Investigate the crypt"},
            "gm": {"secrets_markdown": "The baron is a lich"},
            "objectives": [
                {"text": "Find the entrance", "visibleToPlayers": True},
                {"text": "Find the hidden altar", "visibleToPlayers": False},
            ],
            "rewards": [
                {"text": "50 gold", "visibleToPlayers": True},
                {"text": "Cursed relic", "visibleToPlayers": False},
            ],
        },
    )
    assert created.success
    journal = JournalRepository().get_by_id(created.journal_id)

    player_view = JournalService().build_view(
        journal=dict(journal),
        campaign={"member_role": PlayerRole.PLAYER.value},
        user_id=player_id,
    )
    gm_view = JournalService().build_view(
        journal=dict(journal),
        campaign={"member_role": "gm"},
        user_id=gm_id,
    )

    assert player_view["is_gm_view"] is False
    assert "gm" not in player_view["quest"]
    assert [o["text"] for o in player_view["quest"]["objectives"]] == ["Find the entrance"]
    assert [r["text"] for r in player_view["quest"]["rewards"]] == ["50 gold"]

    assert gm_view["is_gm_view"] is True
    assert gm_view["quest"]["gm"]["secrets_markdown"] == "The baron is a lich"
    assert len(gm_view["quest"]["objectives"]) == 2


def test_toggle_objective_marks_completed(db):
    gm_id = seed_user(name="GM", email="gm-journal-obj@test.com")
    campaign_id = seed_campaign(gm_id)

    created = JournalService().create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="quest",
        title="Quest",
        data={
            "objectives": [
                {"id": "obj_1", "text": "Step one", "visibleToPlayers": True},
            ]
        },
    )
    assert created.success

    result = JournalService().toggle_objective(
        quest_id=created.journal_id,
        objective_id="obj_1",
        completed=True,
        requester_user_id=gm_id,
    )
    assert result.success
    data = json.loads(JournalRepository().get_by_id(created.journal_id)["data_json"])
    assert data["objectives"][0]["completed"] is True


def test_board_player_sees_public_card_not_draft(db):
    gm_id = seed_user(name="GM", email="gm-journal-board@test.com")
    player_id = seed_user(name="Player", email="player-journal-board@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    service = JournalService()
    board = service.create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="quest_board",
        title="Tavern Board",
        visibility="shared",
    )
    available = service.create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="quest",
        title="Available Quest",
        data={"status": "available", "public": {"summary": "Open contract"}},
    )
    draft = service.create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="quest",
        title="Draft Quest",
        data={"status": "draft"},
    )
    pinned = service.create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="quest",
        title="Pinned Quest",
        data={"status": "available", "public": {"summary": "Featured contract"}},
    )
    # ``available`` is added without pinning: players still see it (every added
    # quest is visible); pinning only floats a quest to the top.
    assert service.add_quest_to_board(
        board_id=board.journal_id, quest_id=available.journal_id, requester_user_id=gm_id,
    ).success
    assert service.add_quest_to_board(
        board_id=board.journal_id, quest_id=draft.journal_id, requester_user_id=gm_id,
    ).success
    assert service.add_quest_to_board(
        board_id=board.journal_id, quest_id=pinned.journal_id, requester_user_id=gm_id,
        pinned=True,
    ).success

    board_row = JournalRepository().get_by_id(board.journal_id)
    player_view = service.build_view(
        journal=dict(board_row),
        campaign={"member_role": PlayerRole.PLAYER.value},
        user_id=player_id,
    )
    gm_view = service.build_view(
        journal=dict(board_row),
        campaign={"member_role": "gm"},
        user_id=gm_id,
    )

    player_entries = player_view["board_entries"]
    player_quest_ids = {entry["quest_id"] for entry in player_entries}
    gm_quest_ids = {entry["quest_id"] for entry in gm_view["board_entries"]}

    assert available.journal_id in player_quest_ids
    assert pinned.journal_id in player_quest_ids
    assert draft.journal_id not in player_quest_ids
    # Pinned quests float to the top of the board.
    assert player_entries[0]["quest_id"] == pinned.journal_id
    assert gm_quest_ids == {available.journal_id, draft.journal_id, pinned.journal_id}


def test_player_folder_is_visible_even_when_empty(db):
    gm_id = seed_user(name="GM", email="gm-journal-4@test.com")
    player_id = seed_user(name="Player", email="player-journal-4@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    folder = JournalService().create_folder(
        campaign_id=campaign_id,
        user_id=player_id,
        name="Notes",
    )

    assert folder.success
    assert folder.folder_id is not None


def test_diary_doc_round_trip_and_player_gm_block_filter(db):
    gm_id = seed_user(name="GM", email="gm-journal-doc@test.com")
    player_id = seed_user(name="Player", email="player-journal-doc@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    created = JournalService().create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="diary",
        title="Lore",
        visibility="shared",
    )
    assert created.success

    doc = {
        "format": "gw-journal-doc-v1",
        "version": 1,
        "doc": {"type": "doc", "content": [
            {"type": "paragraph", "attrs": {"visibility": "public"},
             "content": [{"type": "text", "text": "Everyone sees this"}]},
            {"type": "gwCallout", "attrs": {"kind": "secret", "visibility": "gm", "title": "Secret"},
             "content": [{"type": "paragraph", "content": [{"type": "text", "text": "GM only"}]}]},
        ]},
    }
    updated = JournalService().update_journal(
        journal_id=created.journal_id,
        user_id=gm_id,
        title="Lore",
        visibility="shared",
        data={"content": doc},
    )
    assert updated.success

    journal = JournalRepository().get_by_id(created.journal_id)
    gm_view = JournalService().build_view(
        journal=journal, campaign={"member_role": PlayerRole.GM.value}, user_id=gm_id,
    )
    player_view = JournalService().build_view(
        journal=journal, campaign={"member_role": PlayerRole.PLAYER.value}, user_id=player_id,
    )

    gm_blocks = gm_view["content_doc"]["doc"]["content"]
    player_blocks = player_view["content_doc"]["doc"]["content"]
    assert [b["type"] for b in gm_blocks] == ["paragraph", "gwCallout"]
    assert [b["type"] for b in player_blocks] == ["paragraph"]
    assert player_view["content_markdown"] == ""


def test_quest_public_description_strips_gm_blocks_for_players(db):
    gm_id = seed_user(name="GM", email="gm-quest-desc@test.com")
    player_id = seed_user(name="Player", email="player-quest-desc@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    description = {
        "format": "gw-journal-doc-v1", "version": 1,
        "doc": {"type": "doc", "content": [
            {"type": "paragraph", "attrs": {"visibility": "public"},
             "content": [{"type": "text", "text": "Public clue"}]},
            {"type": "gwCallout", "attrs": {"kind": "secret", "visibility": "gm", "title": "S"},
             "content": [{"type": "paragraph", "content": [{"type": "text", "text": "GM clue"}]}]},
        ]},
    }
    created = JournalService().create_journal(
        campaign_id=campaign_id, user_id=gm_id, journal_type="quest", title="Crypt",
        visibility="shared",
        data={"status": "available", "public": {"summary": "s", "description": description}},
    )
    assert created.success
    journal = JournalRepository().get_by_id(created.journal_id)

    player_view = JournalService().build_view(
        journal=dict(journal), campaign={"member_role": PlayerRole.PLAYER.value}, user_id=player_id,
    )
    gm_view = JournalService().build_view(
        journal=dict(journal), campaign={"member_role": "gm"}, user_id=gm_id,
    )

    player_blocks = player_view["quest"]["public"]["description"]["doc"]["content"]
    gm_blocks = gm_view["quest"]["public"]["description"]["doc"]["content"]
    assert [b["type"] for b in player_blocks] == ["paragraph"]
    assert [b["type"] for b in gm_blocks] == ["paragraph", "gwCallout"]
    assert "gm" not in player_view["quest"]


def test_non_gm_owner_never_sees_gm_blocks_and_save_preserves_them(db):
    gm = seed_user(name="GM", email="gm-owner-gmblock@test.com")
    player = seed_user(name="Player", email="player-owner-gmblock@test.com")
    campaign_id = seed_campaign(gm)
    seed_member(campaign_id, player, PlayerRole.PLAYER.value)

    created = JournalService().create_journal(
        campaign_id=campaign_id, user_id=gm, journal_type="diary", title="Lore",
    )
    doc = {
        "format": "gw-journal-doc-v1", "version": 1,
        "doc": {"type": "doc", "content": [
            {"type": "paragraph", "attrs": {"visibility": "public"},
             "content": [{"type": "text", "text": "Public"}]},
            {"type": "gwCallout", "attrs": {"kind": "secret", "visibility": "gm", "title": "S"},
             "content": [{"type": "paragraph", "content": [{"type": "text", "text": "GM secret"}]}]},
        ]},
    }
    JournalService().update_journal(journal_id=created.journal_id, user_id=gm, title="Lore", data={"content": doc})
                                                                               
    JournalService().toggle_owner(
        journal_id=created.journal_id, user_id_to_toggle=player, requester_user_id=gm,
    )

    journal = JournalRepository().get_by_id(created.journal_id)
    owner_view = JournalService().build_view(
        journal=dict(journal), campaign={"member_role": PlayerRole.PLAYER.value}, user_id=player,
    )
    assert [b["type"] for b in owner_view["content_doc"]["doc"]["content"]] == ["paragraph"]

                                                                            
    edited = {
        "format": "gw-journal-doc-v1", "version": 1,
        "doc": {"type": "doc", "content": [
            {"type": "paragraph", "attrs": {"visibility": "public"},
             "content": [{"type": "text", "text": "Edited by owner"}]},
        ]},
    }
    saved = JournalService().update_journal(
        journal_id=created.journal_id, user_id=player, title="Lore", data={"content": edited},
    )
    assert saved.success

    journal2 = JournalRepository().get_by_id(created.journal_id)
    gm_view = JournalService().build_view(
        journal=dict(journal2), campaign={"member_role": "gm"}, user_id=gm,
    )
    types = [b["type"] for b in gm_view["content_doc"]["doc"]["content"]]
    assert "gwCallout" in types


def test_quest_is_viewable_via_shared_board(db):
    gm = seed_user(name="GM", email="gm-boardview@test.com")
    player = seed_user(name="Player", email="player-boardview@test.com")
    campaign_id = seed_campaign(gm)
    seed_member(campaign_id, player, PlayerRole.PLAYER.value)

    quest = JournalService().create_journal(
        campaign_id=campaign_id, user_id=gm, journal_type="quest", title="On Board",
        visibility="private", data={"status": "available", "public": {"summary": "s"}},
    )
    board = JournalService().create_journal(
        campaign_id=campaign_id, user_id=gm, journal_type="quest_board", title="Board",
        visibility="shared",
    )
    added = JournalService().add_quest_to_board(
        board_id=board.journal_id, quest_id=quest.journal_id, requester_user_id=gm,
    )
    assert added.success

    on_board = JournalRepository().get_by_id(quest.journal_id)
    assert JournalService().can_view_journal(
        journal=dict(on_board), campaign={"member_role": PlayerRole.PLAYER.value}, user_id=player,
    ) is True

                                                                            
    hidden = JournalService().create_journal(
        campaign_id=campaign_id, user_id=gm, journal_type="quest", title="Hidden",
        visibility="private",
    )
    hidden_row = JournalRepository().get_by_id(hidden.journal_id)
    assert JournalService().can_view_journal(
        journal=dict(hidden_row), campaign={"member_role": PlayerRole.PLAYER.value}, user_id=player,
    ) is False


def test_diary_gm_fields_are_gm_only_and_preserved(db):
    gm = seed_user(name="GM", email="gm-diary-gmfields@test.com")
    player = seed_user(name="Player", email="player-diary-gmfields@test.com")
    campaign_id = seed_campaign(gm)
    seed_member(campaign_id, player, PlayerRole.PLAYER.value)

    created = JournalService().create_journal(
        campaign_id=campaign_id, user_id=gm, journal_type="diary", title="Lore",
    )
    JournalService().toggle_owner(
        journal_id=created.journal_id, user_id_to_toggle=player, requester_user_id=gm,
    )

    def _doc(text):
        return {"format": "gw-journal-doc-v1", "version": 1,
                "doc": {"type": "doc", "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": text}]}]}}

    JournalService().update_journal(
        journal_id=created.journal_id, user_id=gm, title="Lore",
        data={"content": _doc("Public body"),
              "gm": {"notes": _doc("Secret plan"), "secrets": _doc("Hidden twist")}},
    )

    journal = JournalRepository().get_by_id(created.journal_id)
    gm_view = JournalService().build_view(
        journal=dict(journal), campaign={"member_role": "gm"}, user_id=gm)
    player_view = JournalService().build_view(
        journal=dict(journal), campaign={"member_role": PlayerRole.PLAYER.value}, user_id=player)

    assert gm_view["diary"]["gm"]["notes"]["doc"]["content"]
    assert "diary" not in player_view                                          

                                                                          
    JournalService().update_journal(
        journal_id=created.journal_id, user_id=player, title="Lore",
        data={"content": _doc("Edited body"), "gm": {"notes": _doc(""), "secrets": _doc("")}},
    )
    journal2 = JournalRepository().get_by_id(created.journal_id)
    gm_view2 = JournalService().build_view(
        journal=dict(journal2), campaign={"member_role": "gm"}, user_id=gm)
    notes_text = gm_view2["diary"]["gm"]["notes"]["doc"]["content"][0]["content"][0]["text"]
    assert notes_text == "Secret plan"


def test_owner_can_edit_journal_in_another_users_folder(db):
    gm = seed_user(name="GM", email="gm-folderedit@test.com")
    player = seed_user(name="Player", email="player-folderedit@test.com")
    campaign_id = seed_campaign(gm)
    seed_member(campaign_id, player, PlayerRole.PLAYER.value)

    folder = JournalService().create_folder(campaign_id=campaign_id, user_id=gm, name="GM Folder")
    created = JournalService().create_journal(
        campaign_id=campaign_id, user_id=gm, journal_type="diary", title="Lore",
        folder_id=folder.folder_id,
    )
    JournalService().toggle_owner(
        journal_id=created.journal_id, user_id_to_toggle=player, requester_user_id=gm,
    )

                                                                                 
                                                                                 
    result = JournalService().update_journal(
        journal_id=created.journal_id, user_id=player, title="Lore",
        folder_id=folder.folder_id,
        data={"content": {"format": "gw-journal-doc-v1", "version": 1,
                          "doc": {"type": "doc", "content": [
                              {"type": "paragraph", "content": [{"type": "text", "text": "Edited"}]}]}}},
    )
    assert result.success, result.error_key

    journal = JournalRepository().get_by_id(created.journal_id)
    assert journal["folder_id"] == folder.folder_id


def test_board_quest_opens_via_board_but_is_not_listed_in_sidebar(db):
    gm = seed_user(name="GM", email="gm-boardhub@test.com")
    player = seed_user(name="Player", email="player-boardhub@test.com")
    campaign_id = seed_campaign(gm)
    seed_member(campaign_id, player, PlayerRole.PLAYER.value)

    quest = JournalService().create_journal(
        campaign_id=campaign_id, user_id=gm, journal_type="quest", title="On Board",
        visibility="private", data={"status": "available", "public": {"summary": "s"}},
    )
    board = JournalService().create_journal(
        campaign_id=campaign_id, user_id=gm, journal_type="quest_board", title="Board",
        visibility="shared",
    )
    JournalService().add_quest_to_board(
        board_id=board.journal_id, quest_id=quest.journal_id, requester_user_id=gm,
    )

    svc = JournalService()
    quest_row = dict(JournalRepository().get_by_id(quest.journal_id))
    player_campaign = {"member_role": PlayerRole.PLAYER.value}

                                            
    assert svc.can_view_journal(journal=quest_row, campaign=player_campaign, user_id=player) is True
                                                                            
    assert svc.can_view_journal_directly(journal=quest_row, campaign=player_campaign, user_id=player) is False

                                                 
    board_row = dict(JournalRepository().get_by_id(board.journal_id))
    assert svc.can_view_journal_directly(journal=board_row, campaign=player_campaign, user_id=player) is True


def test_board_with_all_filters_off_still_shows_quests_to_players(db):
                                                                                 
                                                                                       
    gm = seed_user(name="GM", email="gm-boardfilters@test.com")
    player = seed_user(name="Player", email="player-boardfilters@test.com")
    campaign_id = seed_campaign(gm)
    seed_member(campaign_id, player, PlayerRole.PLAYER.value)

    quest = JournalService().create_journal(
        campaign_id=campaign_id, user_id=gm, journal_type="quest", title="Q",
        visibility="private", data={"status": "available", "public": {"summary": "s"}},
    )
    board = JournalService().create_journal(
        campaign_id=campaign_id, user_id=gm, journal_type="quest_board", title="Board",
        visibility="shared",
        data={"filters": {"showAvailable": False, "showActive": False,
                          "showCompleted": False, "showFailed": False}},
    )
    JournalService().add_quest_to_board(
        board_id=board.journal_id, quest_id=quest.journal_id, requester_user_id=gm,
    )

    journal = dict(JournalRepository().get_by_id(board.journal_id))
    player_view = JournalService().build_view(
        journal=journal, campaign={"member_role": PlayerRole.PLAYER.value}, user_id=player,
    )
    assert len(player_view["board_entries"]) == 1
    assert player_view["board_entries"][0]["quest_id"] == quest.journal_id
