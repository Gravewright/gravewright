from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from app.persistence.repositories.campaign_join_code_repository import (
    CampaignJoinCodeRepository,
)
from tests.conftest import seed_campaign, seed_user


def test_concurrent_rotations_leave_exactly_one_active_code(db):
    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    now = int(time.time())
    hash_prefix = uuid.uuid4().hex

    def rotate(suffix: str):
        return CampaignJoinCodeRepository().rotate_active_code(
            campaign_id=campaign_id,
            created_by_user_id=gm_id,
            code_hash=(hash_prefix + suffix * 64)[:64],
            expires_at=now + 3600,
            max_uses=None,
            now=now,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(rotate, ["a", "b"]))

    status = CampaignJoinCodeRepository().get_status_for_campaign(campaign_id=campaign_id)
    assert status is not None
    assert status["id"] in {outcome["id"] for outcome in outcomes}
    assert "code_hash" not in status


def test_concurrent_redeems_do_not_exceed_max_uses(db):
    gm_id = seed_user(name="GM")
    first_player = seed_user(name="First")
    second_player = seed_user(name="Second")
    campaign_id = seed_campaign(gm_id)
    now = int(time.time())
    code_hash = (uuid.uuid4().hex * 2)[:64]
    CampaignJoinCodeRepository().rotate_active_code(
        campaign_id=campaign_id,
        created_by_user_id=gm_id,
        code_hash=code_hash,
        expires_at=now + 3600,
        max_uses=1,
        now=now,
    )

    def redeem(user_id: str):
        return CampaignJoinCodeRepository().redeem_for_user(
            code_hash=code_hash, user_id=user_id, now=now + 1
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(redeem, [first_player, second_player]))

    assert sorted(outcome.status for outcome in outcomes) == ["exhausted", "redeemed"]
    assert sum(outcome.membership_created for outcome in outcomes) == 1
    assert (
        CampaignJoinCodeRepository().get_status_for_campaign(campaign_id=campaign_id)["use_count"]
        == 1
    )


def test_ten_concurrent_same_user_redeems_are_idempotent(db):
    gm_id = seed_user(name="GM")
    player_id = seed_user(name="Player")
    campaign_id = seed_campaign(gm_id)
    now = int(time.time())
    code_hash = (uuid.uuid4().hex * 2)[:64]
    CampaignJoinCodeRepository().rotate_active_code(
        campaign_id=campaign_id,
        created_by_user_id=gm_id,
        code_hash=code_hash,
        expires_at=now + 3600,
        max_uses=2,
        now=now,
    )

    def redeem(_):
        return CampaignJoinCodeRepository().redeem_for_user(
            code_hash=code_hash, user_id=player_id, now=now + 1
        )

    with ThreadPoolExecutor(max_workers=10) as executor:
        outcomes = list(executor.map(redeem, range(10)))

    assert [outcome.status for outcome in outcomes].count("redeemed") == 1
    assert [outcome.status for outcome in outcomes].count("already_member") == 9
    assert sum(outcome.membership_created for outcome in outcomes) == 1
    assert (
        CampaignJoinCodeRepository().get_status_for_campaign(campaign_id=campaign_id)["use_count"]
        == 1
    )
