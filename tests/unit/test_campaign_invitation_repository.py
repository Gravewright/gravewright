from __future__ import annotations

"""Invitation accept semantics (post-maintenance plan, Etapa 1).

An accepted invitation is a receipt, not a key: it stays idempotent only while
the membership it created still exists. Once a GM removes or bans the member,
replaying the old invitation must not put them back in the table.
"""

import pytest
from sqlalchemy import select, update

from app.business.campaigns.campaign_invitation_service import CampaignInvitationService
from app.domain.campaigns import InvitationStatus
from app.domain.roles import PlayerRole
from app.persistence.database import engine_begin
from app.persistence.repositories.campaign_invitation_repository import (
    CampaignInvitationRepository,
)
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.tables import campaign_invitations
from tests.conftest import seed_campaign, seed_user


def _invite(campaign_id: str, gm_id: str, email: str) -> None:
    result = CampaignInvitationService().create_invitation(
        campaign_id=campaign_id,
        invited_by_user_id=gm_id,
        invited_email=email,
        role=PlayerRole.PLAYER.value,
    )
    assert result.success, result.error_key


def _pending_invitation_id(user_id: str, campaign_id: str) -> str:
    for row in CampaignInvitationRepository().list_pending_for_user(user_id):
        if row["campaign_id"] == campaign_id:
            return row["id"]
    raise AssertionError(f"no pending invitation for {user_id} in {campaign_id}")


def _invitation_status(invitation_id: str) -> str:
    with engine_begin() as conn:
        row = conn.execute(
            select(campaign_invitations.c.status).where(campaign_invitations.c.id == invitation_id)
        ).first()
    assert row is not None
    return row[0]


def _set_status(invitation_id: str, status: str) -> None:
    with engine_begin() as conn:
        conn.execute(
            update(campaign_invitations)
            .where(campaign_invitations.c.id == invitation_id)
            .values(status=status)
        )


def _membership_count(campaign_id: str, user_id: str) -> int:
    members = CampaignRepository().list_members(campaign_id=campaign_id)
    return len([m for m in members if m["user_id"] == user_id])


def _setup(email: str = "player-accept@test.com") -> tuple[str, str, str]:
    """GM + campaign + invited player; returns (campaign_id, player_id, invitation_id)."""
    gm_id = seed_user(name="GM", email="gm-accept@test.com")
    player_id = seed_user(name="Player", email=email)
    campaign_id = seed_campaign(gm_id, title="Accept Semantics")
    _invite(campaign_id, gm_id, email)
    return campaign_id, player_id, _pending_invitation_id(player_id, campaign_id)


# --- Teste A: aceite normal ----------------------------------------------------


def test_pending_accept_creates_membership_and_marks_invitation(db):
    campaign_id, player_id, invitation_id = _setup()

    outcome = CampaignInvitationRepository().accept_for_user(
        invitation_id=invitation_id, user_id=player_id
    )

    assert outcome.status == "accepted"
    assert outcome.membership_created is True
    assert _membership_count(campaign_id, player_id) == 1
    assert _invitation_status(invitation_id) == InvitationStatus.ACCEPTED.value


# --- Teste B: repetição idempotente --------------------------------------------


def test_repeated_accept_with_live_membership_is_idempotent(db):
    campaign_id, player_id, invitation_id = _setup()
    repo = CampaignInvitationRepository()

    repo.accept_for_user(invitation_id=invitation_id, user_id=player_id)
    second = repo.accept_for_user(invitation_id=invitation_id, user_id=player_id)

    assert second.status == "accepted"
    # No second membership and: crucially: no second join event.
    assert second.membership_created is False
    assert _membership_count(campaign_id, player_id) == 1


# --- Teste C: membro removido --------------------------------------------------


def test_accepted_invitation_does_not_restore_removed_membership(db):
    campaign_id, player_id, invitation_id = _setup()
    repo = CampaignInvitationRepository()
    repo.accept_for_user(invitation_id=invitation_id, user_id=player_id)

    CampaignRepository().remove_member(campaign_id=campaign_id, user_id=player_id)

    replay = repo.accept_for_user(invitation_id=invitation_id, user_id=player_id)

    assert replay.status == "membership_removed"
    assert replay.membership_created is False
    assert _membership_count(campaign_id, player_id) == 0


def test_service_reports_membership_removed_without_side_effects(db):
    campaign_id, player_id, invitation_id = _setup()
    service = CampaignInvitationService()
    service.accept_invitation(invitation_id=invitation_id, user_id=player_id)
    CampaignRepository().remove_member(campaign_id=campaign_id, user_id=player_id)

    result = service.accept_invitation(invitation_id=invitation_id, user_id=player_id)

    assert result.success is False
    assert result.error_key == "inside.invitations.errors.membership_removed"
    assert result.payload == {}
    assert _membership_count(campaign_id, player_id) == 0


# --- Teste D: membro banido ----------------------------------------------------


def test_ban_cannot_be_undone_by_replaying_the_invitation(db):
    from app.business.campaigns.campaign_service import CampaignService

    gm_id = seed_user(name="GM", email="gm-ban@test.com")
    player_id = seed_user(name="Player", email="player-ban@test.com")
    campaign_id = seed_campaign(gm_id, title="Ban Replay")
    _invite(campaign_id, gm_id, "player-ban@test.com")
    invitation_id = _pending_invitation_id(player_id, campaign_id)

    service = CampaignInvitationService()
    service.accept_invitation(invitation_id=invitation_id, user_id=player_id)

    banned = CampaignService().ban_member(
        campaign_id=campaign_id,
        requester_user_id=gm_id,
        target_user_id=player_id,
    )
    assert banned.success

    replay = service.accept_invitation(invitation_id=invitation_id, user_id=player_id)

    assert replay.success is False
    assert replay.error_key == "inside.invitations.errors.membership_removed"
    assert _membership_count(campaign_id, player_id) == 0


# --- convites pendentes são revogados na remoção -------------------------------


def test_removing_a_member_revokes_their_pending_invitations(db):
    """A second, still-pending invite must not survive the removal."""
    gm_id = seed_user(name="GM", email="gm-revoke@test.com")
    player_id = seed_user(name="Player", email="player-revoke@test.com")
    campaign_id = seed_campaign(gm_id, title="Revoke Pending")
    _invite(campaign_id, gm_id, "player-revoke@test.com")
    first_invitation = _pending_invitation_id(player_id, campaign_id)

    CampaignInvitationRepository().accept_for_user(
        invitation_id=first_invitation, user_id=player_id
    )

    # A stale pending invite issued before the accept (same user, same campaign).
    _set_status(first_invitation, InvitationStatus.PENDING.value)

    CampaignRepository().remove_member(campaign_id=campaign_id, user_id=player_id)

    assert _invitation_status(first_invitation) == InvitationStatus.REVOKED.value
    assert CampaignInvitationRepository().list_pending_for_user(player_id) == []

    replay = CampaignInvitationRepository().accept_for_user(
        invitation_id=first_invitation, user_id=player_id
    )
    assert replay.status == "not_pending"
    assert _membership_count(campaign_id, player_id) == 0


@pytest.mark.parametrize(
    "status", [InvitationStatus.DECLINED.value, InvitationStatus.REVOKED.value]
)
def test_closed_invitation_states_are_rejected(db, status):
    campaign_id, player_id, invitation_id = _setup()
    _set_status(invitation_id, status)

    outcome = CampaignInvitationRepository().accept_for_user(
        invitation_id=invitation_id, user_id=player_id
    )

    assert outcome.status == "not_pending"
    assert outcome.membership_created is False
    assert _membership_count(campaign_id, player_id) == 0
    assert _invitation_status(invitation_id) == status


def test_unknown_invitation_is_not_found(db):
    _, player_id, _ = _setup()

    outcome = CampaignInvitationRepository().accept_for_user(
        invitation_id="does-not-exist", user_id=player_id
    )

    assert outcome.status == "not_found"
