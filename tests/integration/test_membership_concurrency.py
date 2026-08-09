from __future__ import annotations

"""Membership concurrency & idempotency (Maintenance Plan - Etapa 5).

N concurrent accepts of the same invitation for the same user must produce
exactly one membership and exactly one "created" outcome, with no IntegrityError
escaping. Verified on SQLite here (the default suite backend); PostgreSQL is
covered by the opt-in backend matrix.
"""

from concurrent.futures import ThreadPoolExecutor
import uuid

import pytest

from app.business.campaigns.campaign_invitation_service import CampaignInvitationService
from app.domain.roles import PlayerRole
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.campaign_invitation_repository import (
    CampaignInvitationRepository,
)
from tests.conftest import seed_campaign, seed_user


def _pending_invitation_id(user_id: str, campaign_id: str) -> str:
    pending = CampaignInvitationRepository().list_pending_for_user(user_id)
    match = [row for row in pending if row["campaign_id"] == campaign_id]
    assert match, "expected a pending invitation"
    return match[0]["id"]


def _setup_pending_invitation(*, campaign_title: str) -> tuple[str, str, str]:
    suffix = uuid.uuid4().hex[:12]
    gm_id = seed_user(name="GM", email=f"gm-conc-{suffix}@test.com")
    player_email = f"player-conc-{suffix}@test.com"
    player_id = seed_user(name="Player", email=player_email)
    campaign_id = seed_campaign(gm_id, title=campaign_title)
    CampaignInvitationService().create_invitation(
        campaign_id=campaign_id,
        invited_by_user_id=gm_id,
        invited_email=player_email,
        role=PlayerRole.PLAYER.value,
    )
    return campaign_id, player_id, _pending_invitation_id(player_id, campaign_id)


@pytest.mark.parametrize("concurrency", [2, 10])
def test_concurrent_accepts_create_single_membership(db, concurrency):
    campaign_id, player_id, invitation_id = _setup_pending_invitation(
        campaign_title=f"Race {concurrency}"
    )

    def accept():
        # Each thread uses its own service instance, like separate requests.
        return CampaignInvitationService().accept_invitation(
            invitation_id=invitation_id, user_id=player_id
        )

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(lambda _: accept(), range(concurrency)))

    # No request errored out (no unhandled IntegrityError / 500).
    assert all(r.success for r in results), [r.error_key for r in results]

    # Exactly one request reports it created the membership.
    created_count = sum(1 for r in results if r.payload.get("membership_created"))
    assert created_count == 1, f"expected exactly one creation, got {created_count}"

    # Exactly one membership row for this (campaign, user).
    members = CampaignRepository().list_members(campaign_id=campaign_id)
    player_rows = [m for m in members if m["user_id"] == player_id]
    assert len(player_rows) == 1


def test_already_member_accept_is_idempotent_success(db):
    campaign_id, player_id, invitation_id = _setup_pending_invitation(campaign_title="Idempotent")

    first = CampaignInvitationService().accept_invitation(
        invitation_id=invitation_id, user_id=player_id
    )
    second = CampaignInvitationService().accept_invitation(
        invitation_id=invitation_id, user_id=player_id
    )

    assert first.payload["membership_created"] is True
    assert second.success is True
    assert second.payload["membership_created"] is False

    members = CampaignRepository().list_members(campaign_id=campaign_id)
    assert len([m for m in members if m["user_id"] == player_id]) == 1
