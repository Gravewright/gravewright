"""Streamer Mode bearer link: generate / revoke / consume (guest member)."""

from __future__ import annotations

import time

from app.business.campaigns.streamer_link_service import StreamerLinkService
from app.business.permissions import PermissionService
from app.domain.permissions.permissions import TablePermission
from app.domain.roles import PlayerRole
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.streamer_link_repository import StreamerLinkRepository
from tests.conftest import seed_campaign
from tests.conftest import seed_member
from tests.conftest import seed_user


def test_gm_generates_active_link(db):
    gm_id = seed_user(email="sl-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    service = StreamerLinkService()

    result = service.generate(campaign_id=campaign_id, user_id=gm_id)

    assert result.success is True
    assert result.token
    assert result.expires_at > int(time.time())

    active = service.get_active(campaign_id=campaign_id, user_id=gm_id)
    assert active.token == result.token


def test_non_gm_cannot_generate_link(db):
    gm_id = seed_user(email="sl-gm2@test.com")
    player_id = seed_user(email="sl-player@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    service = StreamerLinkService()

    result = service.generate(campaign_id=campaign_id, user_id=player_id)

    assert result.success is False
    assert result.error_key == "game.streamer.errors.gm_required"


def test_consume_mints_readonly_streamer_member(db):
    gm_id = seed_user(email="sl-gm3@test.com")
    campaign_id = seed_campaign(gm_id)
    service = StreamerLinkService()
    token = service.generate(campaign_id=campaign_id, user_id=gm_id).token

    resolved = service.consume(token=token)

    assert resolved is not None
    assert resolved["campaign_id"] == campaign_id
    guest_id = resolved["guest_user_id"]

    role = CampaignRepository().get_member_role(campaign_id=campaign_id, user_id=guest_id)
    assert role == PlayerRole.STREAMER.value

                                                                      
    permissions = PermissionService()
    assert permissions.can(
        user_id=guest_id, campaign_id=campaign_id, permission=TablePermission.SCENE_VIEW
    ) is True
    assert permissions.can(
        user_id=guest_id, campaign_id=campaign_id, permission=TablePermission.TOKEN_MOVE
    ) is False
    assert permissions.can(
        user_id=guest_id, campaign_id=campaign_id, permission=TablePermission.CHAT_SEND
    ) is False


def test_consume_reuses_same_guest_principal(db):
    gm_id = seed_user(email="sl-gm4@test.com")
    campaign_id = seed_campaign(gm_id)
    service = StreamerLinkService()
    token = service.generate(campaign_id=campaign_id, user_id=gm_id).token

    first = service.consume(token=token)
    second = service.consume(token=token)

    assert first["guest_user_id"] == second["guest_user_id"]


def test_revoke_invalidates_link(db):
    gm_id = seed_user(email="sl-gm5@test.com")
    campaign_id = seed_campaign(gm_id)
    service = StreamerLinkService()
    token = service.generate(campaign_id=campaign_id, user_id=gm_id).token

    service.revoke(campaign_id=campaign_id, user_id=gm_id)

    assert service.consume(token=token) is None
    assert service.get_active(campaign_id=campaign_id, user_id=gm_id).token is None


def test_regenerate_revokes_previous_link(db):
    gm_id = seed_user(email="sl-gm6@test.com")
    campaign_id = seed_campaign(gm_id)
    service = StreamerLinkService()
    old_token = service.generate(campaign_id=campaign_id, user_id=gm_id).token

    new_token = service.generate(campaign_id=campaign_id, user_id=gm_id).token

    assert old_token != new_token
    assert service.consume(token=old_token) is None
    assert service.consume(token=new_token) is not None


def test_expired_link_is_not_consumable(db):
    gm_id = seed_user(email="sl-gm7@test.com")
    campaign_id = seed_campaign(gm_id)
    repo = StreamerLinkRepository()
    repo.create_active(
        campaign_id=campaign_id,
        token="expired-token",
        created_by_user_id=gm_id,
        expires_at=int(time.time()) - 1,
    )

    assert repo.get_active_for_campaign(campaign_id=campaign_id) is None
    assert repo.consume_token(token="expired-token") is None


def test_unknown_token_is_rejected(db):
    service = StreamerLinkService()
    assert service.consume(token="does-not-exist") is None
    assert service.consume(token="") is None
