from __future__ import annotations

from app.business.game_page_service import GamePageService
from app.domain.roles import PlayerRole
from app.engine.actors.actor_permissions import can_edit_actor, can_view_actor
from app.engine.actors.actor_service import ActorService
from app.persistence.repositories.actor_repository import ActorRepository
from tests.conftest import seed_actor, seed_campaign, seed_member, seed_system, seed_user


def _setup(db):
    gm_id = seed_user(name="GM", email=f"gm-{id(db)}@perm.com")
    player_id = seed_user(name="Player", email=f"pl-{id(db)}@perm.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    seed_system(campaign_id, gm_id)
    return gm_id, player_id, campaign_id


def _campaign(role: str) -> dict:
    return {"member_role": role}


                                                                              

def test_gm_always_views_and_edits(db):
    gm_id, _player_id, campaign_id = _setup(db)
    actor_id = seed_actor(campaign_id, gm_id)
    actor = ActorRepository().get(actor_id)
    assert can_view_actor(actor=actor, campaign=_campaign("gm"), user_id=gm_id)
    assert can_edit_actor(actor=actor, campaign=_campaign("gm"), user_id=gm_id)


def test_player_no_access_by_default(db):
    gm_id, player_id, campaign_id = _setup(db)
    actor = ActorRepository().get(seed_actor(campaign_id, gm_id))
    assert not can_view_actor(actor=actor, campaign=_campaign("player"), user_id=player_id)
    assert not can_edit_actor(actor=actor, campaign=_campaign("player"), user_id=player_id)


def test_set_member_access_read_grants_view_only(db):
    gm_id, player_id, campaign_id = _setup(db)
    actor_id = seed_actor(campaign_id, gm_id)
    res = ActorService().set_member_access(
        actor_id=actor_id, target_user_id=player_id, access_level="read", requester_user_id=gm_id
    )
    assert res.success
    actor = ActorRepository().get(actor_id)
    assert can_view_actor(actor=actor, campaign=_campaign("player"), user_id=player_id)
    assert not can_edit_actor(actor=actor, campaign=_campaign("player"), user_id=player_id)


def test_set_member_access_owner_grants_edit(db):
    gm_id, player_id, campaign_id = _setup(db)
    actor_id = seed_actor(campaign_id, gm_id)
    ActorService().set_member_access(
        actor_id=actor_id, target_user_id=player_id, access_level="owner", requester_user_id=gm_id
    )
    actor = ActorRepository().get(actor_id)
    assert can_edit_actor(actor=actor, campaign=_campaign("player"), user_id=player_id)
    assert ActorRepository().has_owner(actor_id=actor_id, user_id=player_id)


def test_set_member_access_none_revokes(db):
    gm_id, player_id, campaign_id = _setup(db)
    actor_id = seed_actor(campaign_id, gm_id, owner_user_ids=[player_id])
    ActorService().set_member_access(
        actor_id=actor_id, target_user_id=player_id, access_level="none", requester_user_id=gm_id
    )
    actor = ActorRepository().get(actor_id)
    assert not can_view_actor(actor=actor, campaign=_campaign("player"), user_id=player_id)
    assert not ActorRepository().has_owner(actor_id=actor_id, user_id=player_id)


def test_toggle_owner_round_trip(db):
    gm_id, player_id, campaign_id = _setup(db)
    actor_id = seed_actor(campaign_id, gm_id)
    svc = ActorService()
    first = svc.toggle_owner(actor_id=actor_id, user_id_to_toggle=player_id, requester_user_id=gm_id)
    assert first.success and first.is_owner is True
    assert ActorRepository().has_owner(actor_id=actor_id, user_id=player_id)
    second = svc.toggle_owner(actor_id=actor_id, user_id_to_toggle=player_id, requester_user_id=gm_id)
    assert second.is_owner is False
    assert not ActorRepository().has_owner(actor_id=actor_id, user_id=player_id)


def test_player_cannot_set_access(db):
    gm_id, player_id, campaign_id = _setup(db)
    actor_id = seed_actor(campaign_id, gm_id)
    res = ActorService().set_member_access(
        actor_id=actor_id, target_user_id=player_id, access_level="owner", requester_user_id=player_id
    )
    assert not res.success
    assert res.error_key == "game.actors.errors.gm_required"


                                                                            

def test_create_and_move_actor_into_folder(db):
    gm_id, _player_id, campaign_id = _setup(db)
    actor_id = seed_actor(campaign_id, gm_id)
    folder = ActorService().create_folder(campaign_id=campaign_id, user_id=gm_id, name="NPCs")
    assert folder.success
    moved = ActorService().move_actor(
        actor_id=actor_id, target_folder_id=folder.folder_id, user_id=gm_id
    )
    assert moved.success and moved.folder_id == folder.folder_id
    assert ActorRepository().get(actor_id)["folder_id"] == folder.folder_id


def test_delete_folder_unfiles_actors(db):
    gm_id, _player_id, campaign_id = _setup(db)
    folder = ActorService().create_folder(campaign_id=campaign_id, user_id=gm_id, name="Temp")
    actor_id = seed_actor(campaign_id, gm_id)
    ActorService().move_actor(actor_id=actor_id, target_folder_id=folder.folder_id, user_id=gm_id)
    ActorService().delete_folder(folder_id=folder.folder_id, user_id=gm_id)
    assert ActorRepository().get(actor_id)["folder_id"] is None


def test_move_folder_into_own_descendant_is_rejected(db):
    gm_id, _player_id, campaign_id = _setup(db)
    parent = ActorService().create_folder(campaign_id=campaign_id, user_id=gm_id, name="Parent")
    child = ActorService().create_folder(
        campaign_id=campaign_id, user_id=gm_id, name="Child", parent_id=parent.folder_id
    )
    res = ActorService().move_folder(
        folder_id=parent.folder_id, target_parent_id=child.folder_id, user_id=gm_id
    )
    assert not res.success


def test_player_only_sees_folder_with_accessible_actor(db):
    gm_id, player_id, campaign_id = _setup(db)
    private_folder = ActorService().create_folder(campaign_id=campaign_id, user_id=gm_id, name="Hidden")
    shared_folder = ActorService().create_folder(campaign_id=campaign_id, user_id=gm_id, name="Party")
    hidden_actor = seed_actor(campaign_id, gm_id, name="Boss")
    shared_actor = seed_actor(campaign_id, gm_id, name="Ally", owner_user_ids=[player_id])
    ActorService().move_actor(actor_id=hidden_actor, target_folder_id=private_folder.folder_id, user_id=gm_id)
    ActorService().move_actor(actor_id=shared_actor, target_folder_id=shared_folder.folder_id, user_id=gm_id)

    room = next(
        r for r in GamePageService().build_context(user_id=player_id).rooms if r["id"] == campaign_id
    )
    assert [f["id"] for f in room["actor_folder_tree"]] == [shared_folder.folder_id]
    assert {a["name"] for a in room["actors"]} == {"Ally"}
