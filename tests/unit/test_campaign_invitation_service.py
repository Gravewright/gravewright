from __future__ import annotations

from app.business.campaigns.campaign_invitation_service import CampaignInvitationService
from app.domain.roles import PlayerRole
from app.persistence.repositories.campaign_invitation_repository import CampaignInvitationRepository
from tests.conftest import seed_campaign, seed_member, seed_user


def _get_pending_invitation_id(user_id: str, campaign_id: str) -> str:
    """Fetch the pending invitation ID for a user + campaign from the DB."""
    invitations = CampaignInvitationRepository().list_pending_for_user(user_id)
    for inv in invitations:
        if inv["campaign_id"] == campaign_id:
            return inv["id"]
    raise AssertionError(f"No pending invitation found for user {user_id} in campaign {campaign_id}")


def test_gm_creates_invitation(db):
    gm_id = seed_user(name="GM", email="gm@test.com")
    seed_user(name="Player", email="player@test.com")
    campaign_id = seed_campaign(gm_id)

    result = CampaignInvitationService().create_invitation(
        campaign_id=campaign_id,
        invited_by_user_id=gm_id,
        invited_email="player@test.com",
        role=PlayerRole.PLAYER.value,
    )
    assert result.success


def test_player_cannot_create_invitation(db):
    gm_id = seed_user(name="GM", email="gm@test.com")
    player_id = seed_user(name="Player", email="player@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)

    result = CampaignInvitationService().create_invitation(
        campaign_id=campaign_id,
        invited_by_user_id=player_id,
        invited_email="other@test.com",
        role=PlayerRole.PLAYER.value,
    )
    assert not result.success
    assert result.error_key == "game.invite.errors.gm_required"


def test_user_accepts_valid_invitation(db):
    gm_id = seed_user(name="GM", email="gm@test.com")
    player_id = seed_user(name="Player", email="player@test.com")
    campaign_id = seed_campaign(gm_id)

    CampaignInvitationService().create_invitation(
        campaign_id=campaign_id,
        invited_by_user_id=gm_id,
        invited_email="player@test.com",
        role=PlayerRole.PLAYER.value,
    )
    invitation_id = _get_pending_invitation_id(player_id, campaign_id)

    result = CampaignInvitationService().accept_invitation(
        invitation_id=invitation_id,
        user_id=player_id,
    )
    assert result.success


def test_already_accepted_invitation_fails(db):
    gm_id = seed_user(name="GM", email="gm@test.com")
    player_id = seed_user(name="Player", email="player@test.com")
    campaign_id = seed_campaign(gm_id)

    CampaignInvitationService().create_invitation(
        campaign_id=campaign_id,
        invited_by_user_id=gm_id,
        invited_email="player@test.com",
        role=PlayerRole.PLAYER.value,
    )
    invitation_id = _get_pending_invitation_id(player_id, campaign_id)

    CampaignInvitationService().accept_invitation(invitation_id=invitation_id, user_id=player_id)
    result = CampaignInvitationService().accept_invitation(invitation_id=invitation_id, user_id=player_id)
    assert not result.success


def test_accepting_does_not_duplicate_membership(db):
    from app.persistence.repositories.campaign_repository import CampaignRepository

    gm_id = seed_user(name="GM", email="gm@test.com")
    player_id = seed_user(name="Player", email="player@test.com")
    campaign_id = seed_campaign(gm_id)

    CampaignInvitationService().create_invitation(
        campaign_id=campaign_id,
        invited_by_user_id=gm_id,
        invited_email="player@test.com",
        role=PlayerRole.PLAYER.value,
    )
    invitation_id = _get_pending_invitation_id(player_id, campaign_id)
    CampaignInvitationService().accept_invitation(invitation_id=invitation_id, user_id=player_id)

    members = CampaignRepository().list_members_for_user_campaigns(player_id)
    player_memberships = [m for m in members if m["user_id"] == player_id and m["campaign_id"] == campaign_id]
    assert len(player_memberships) == 1


def test_invitation_invalid_role_rejected(db):
    gm_id = seed_user(name="GM", email="gm@test.com")
    campaign_id = seed_campaign(gm_id)

    result = CampaignInvitationService().create_invitation(
        campaign_id=campaign_id,
        invited_by_user_id=gm_id,
        invited_email="player@test.com",
        role="gm",                         
    )
    assert not result.success
    assert result.error_key == "game.invite.errors.invalid_role"
