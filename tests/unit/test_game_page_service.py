from __future__ import annotations

import json

from app.business.game_page_service import GamePageService
from app.domain.roles import PlayerRole
from app.engine.journals.journal_service import JournalService
from tests.conftest import grant_actor_access
from tests.conftest import seed_actor
from tests.conftest import seed_campaign
from tests.conftest import seed_member
from tests.conftest import seed_system
from tests.conftest import seed_user


def test_member_list_excludes_gm(db):
    gm_id = seed_user(name="GM", email="gm@test.com")
    player_id = seed_user(name="Player", email="player@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    seed_system(campaign_id, gm_id)

    context = GamePageService().build_context(user_id=gm_id)
    room = context.rooms[0]
    members = json.loads(room["members_json"])

    assert members == [{"id": player_id, "name": "Player"}]


def test_active_system_resolves_to_manifest(db):
    gm_id = seed_user(name="GM", email="gm-active-system@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_system(campaign_id, gm_id)                                      

    context = GamePageService().build_context(user_id=gm_id)
    room = context.rooms[0]

    assert room["active_system"]["id"] == "dnd5e"
    assert room["active_system"]["name"] == "Dungeons & Dragons 5e"
    assert any(s["id"] == "dnd5e" for s in context.available_systems)


def test_room_lists_actors_the_user_can_view(db):
    gm_id = seed_user(name="GM", email="gm-actors-page@test.com")
    player_id = seed_user(name="Player", email="player-actors-page@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    seed_system(campaign_id, gm_id)

    visible = seed_actor(campaign_id, gm_id, name="Shared")
    grant_actor_access(visible, player_id, view=True)
    seed_actor(campaign_id, gm_id, name="Hidden")                      

    gm_room = GamePageService().build_context(user_id=gm_id).rooms[0]
    player_room = GamePageService().build_context(user_id=player_id).rooms[0]

    assert {a["name"] for a in gm_room["actors"]} == {"Shared", "Hidden"}
    assert [a["id"] for a in player_room["actors"]] == [visible]


def test_player_only_sees_owned_journals(db):
    gm_id = seed_user(name="GM", email="gm-journal-page@test.com")
    player_id = seed_user(name="Player", email="player-journal-page@test.com")
    other_player_id = seed_user(name="Other", email="other-journal-page@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    seed_member(campaign_id, other_player_id, PlayerRole.PLAYER.value)

    visible = JournalService().create_journal(
        campaign_id=campaign_id,
        user_id=player_id,
        journal_type="diary",
        title="Mine",
    )
    hidden = JournalService().create_journal(
        campaign_id=campaign_id,
        user_id=other_player_id,
        journal_type="diary",
        title="Hidden",
    )
    assert visible.success
    assert hidden.success

    context = GamePageService().build_context(user_id=player_id)
    room = context.rooms[0]

    assert [journal["id"] for journal in room["journals"]] == [visible.journal_id]


def test_player_sees_own_empty_journal_folder(db):
    gm_id = seed_user(name="GM", email="gm-journal-folder-page@test.com")
    player_id = seed_user(name="Player", email="player-journal-folder-page@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    folder = JournalService().create_folder(
        campaign_id=campaign_id,
        user_id=player_id,
        name="My Notes",
    )
    assert folder.success

    context = GamePageService().build_context(user_id=player_id)
    room = context.rooms[0]

    assert [item["id"] for item in room["journal_folder_tree"]] == [folder.folder_id]
