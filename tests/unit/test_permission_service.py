from __future__ import annotations

from app.business.permissions.permission_service import PermissionService
from app.domain.permissions.permissions import TablePermission, PermissionEffect, PermissionSubjectType
from app.domain.roles import PlayerRole
from app.persistence.repositories.campaign_permission_repository import CampaignPermissionRepository
from tests.conftest import seed_campaign, seed_member, seed_user


def test_gm_can_do_core_permissions(db):
    gm_id = seed_user(name="GM", email="gm@test.com")
    campaign_id = seed_campaign(gm_id)
    svc = PermissionService()
    assert svc.can(user_id=gm_id, campaign_id=campaign_id, permission=TablePermission.SETTINGS_VIEW)
    assert svc.can(user_id=gm_id, campaign_id=campaign_id, permission=TablePermission.CAMPAIGN_INVITE_MEMBERS)
    assert svc.can(user_id=gm_id, campaign_id=campaign_id, permission=TablePermission.SETTINGS_UPDATE_PERMISSIONS)


def test_player_denied_gm_only_permission(db):
    gm_id = seed_user(name="GM", email="gm@test.com")
    player_id = seed_user(name="Player", email="player@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    svc = PermissionService()
    assert not svc.can(user_id=player_id, campaign_id=campaign_id, permission=TablePermission.SETTINGS_UPDATE_PERMISSIONS)


def test_player_has_default_chat_permissions(db):
    gm_id = seed_user(name="GM", email="gm@test.com")
    player_id = seed_user(name="Player", email="player@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    svc = PermissionService()
    assert svc.can(user_id=player_id, campaign_id=campaign_id, permission=TablePermission.CHAT_SEND)
    assert svc.can(user_id=player_id, campaign_id=campaign_id, permission=TablePermission.CHAT_VIEW)


def test_scene_map_permissions_follow_default_roles(db):
    gm_id = seed_user(name="GM", email="gm@test.com")
    player_id = seed_user(name="Player", email="player@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    svc = PermissionService()

    assert svc.can(user_id=gm_id, campaign_id=campaign_id, permission=TablePermission.SCENE_CREATE)
    assert svc.can(user_id=gm_id, campaign_id=campaign_id, permission=TablePermission.MAP_UPLOAD)
    assert svc.can(user_id=player_id, campaign_id=campaign_id, permission=TablePermission.SCENE_VIEW)
    assert svc.can(user_id=player_id, campaign_id=campaign_id, permission=TablePermission.TOKEN_MOVE)
    assert not svc.can(user_id=player_id, campaign_id=campaign_id, permission=TablePermission.MAP_UPLOAD)
    assert not svc.can(user_id=player_id, campaign_id=campaign_id, permission=TablePermission.MAP_PAINT)


def test_non_member_denied(db):
    gm_id = seed_user(name="GM", email="gm@test.com")
    outsider_id = seed_user(name="Outsider", email="out@test.com")
    campaign_id = seed_campaign(gm_id)
    svc = PermissionService()
    assert not svc.can(user_id=outsider_id, campaign_id=campaign_id, permission=TablePermission.CHAT_SEND)


def test_override_allow_grants_extra_permission(db):
    gm_id = seed_user(name="GM", email="gm@test.com")
    player_id = seed_user(name="Player", email="player@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    perm_key = TablePermission.SETTINGS_VIEW.value
    CampaignPermissionRepository().replace_subject_effects(
        campaign_id=campaign_id,
        subject_type=PermissionSubjectType.USER,
        subject_id=player_id,
        effects={perm_key: PermissionEffect.ALLOW},
    )

    svc = PermissionService()
    assert svc.can(user_id=player_id, campaign_id=campaign_id, permission=TablePermission.SETTINGS_VIEW)


def test_override_deny_removes_default_permission(db):
    gm_id = seed_user(name="GM", email="gm@test.com")
    player_id = seed_user(name="Player", email="player@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

                                              
    perm_key = TablePermission.CHAT_SEND.value
    CampaignPermissionRepository().replace_subject_effects(
        campaign_id=campaign_id,
        subject_type=PermissionSubjectType.USER,
        subject_id=player_id,
        effects={perm_key: PermissionEffect.DENY},
    )

    svc = PermissionService()
    assert not svc.can(user_id=player_id, campaign_id=campaign_id, permission=TablePermission.CHAT_SEND)


def test_role_level_override_applies_to_all_role_members(db):
    gm_id = seed_user(name="GM", email="gm@test.com")
    player1_id = seed_user(name="P1", email="p1@test.com")
    player2_id = seed_user(name="P2", email="p2@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player1_id, PlayerRole.PLAYER.value)
    seed_member(campaign_id, player2_id, PlayerRole.PLAYER.value)

    perm_key = TablePermission.SETTINGS_VIEW.value
    CampaignPermissionRepository().replace_subject_effects(
        campaign_id=campaign_id,
        subject_type=PermissionSubjectType.ROLE,
        subject_id=PlayerRole.PLAYER.value,
        effects={perm_key: PermissionEffect.ALLOW},
    )

    svc = PermissionService()
    assert svc.can(user_id=player1_id, campaign_id=campaign_id, permission=TablePermission.SETTINGS_VIEW)
    assert svc.can(user_id=player2_id, campaign_id=campaign_id, permission=TablePermission.SETTINGS_VIEW)
