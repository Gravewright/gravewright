from __future__ import annotations

"""Baseline smoke test (Maintenance Plan - Etapa 0).

Exercises the minimum persistence happy-path required by the baseline:
create a campaign, list it back, and add a member on a throwaway SQLite
database. It is intentionally dependency-light so it can act as a stable
reference point when comparing behaviour across later maintenance stages.
"""

from app.persistence.repositories.campaign_repository import CampaignRepository
from tests.conftest import seed_member
from tests.conftest import seed_user


def test_baseline_create_list_add_member(db):
    repo = CampaignRepository()

    gm_id = seed_user(name="Baseline GM")

    created = repo.create(owner_user_id=gm_id, title="Baseline Campaign", description="")
    assert created["title"] == "Baseline Campaign"
    campaign_id = created["id"]

    # The owner is listed as a GM member of their own campaign.
    listed = repo.list_for_user(gm_id)
    assert [row["id"] for row in listed] == [campaign_id]
    assert listed[0]["member_role"] == "gm"

    # Adding a second member surfaces through the roster query.
    player_id = seed_user(name="Baseline Player")
    seed_member(campaign_id, player_id, role="player")

    members = repo.list_members(campaign_id=campaign_id)
    names = sorted(member["name"] for member in members)
    assert names == ["Baseline GM", "Baseline Player"]
