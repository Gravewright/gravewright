from __future__ import annotations

import time

import pytest
from sqlalchemy import select

from app.persistence.database import engine_connect
from app.persistence.repositories.campaign_join_code_repository import (
    CampaignJoinCodeRepository,
)
from app.persistence.tables import campaign_join_code_redemptions, campaign_members
from tests.conftest import seed_campaign, seed_member, seed_user


def _setup():
    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    return CampaignJoinCodeRepository(), gm_id, campaign_id


def test_rotate_status_and_revoke_never_return_digest(db):
    repository, gm_id, campaign_id = _setup()
    now = int(time.time())
    first = repository.rotate_active_code(
        campaign_id=campaign_id,
        created_by_user_id=gm_id,
        code_hash="a" * 64,
        expires_at=now + 3600,
        max_uses=3,
        now=now,
    )
    assert first["use_count"] == 0
    assert "code_hash" not in first
    assert "code_hash" not in repository.get_status_for_campaign(campaign_id=campaign_id)

    second = repository.rotate_active_code(
        campaign_id=campaign_id,
        created_by_user_id=gm_id,
        code_hash="b" * 64,
        expires_at=now + 7200,
        max_uses=None,
        now=now + 1,
    )
    assert second["id"] != first["id"]
    assert repository.get_status_for_campaign(campaign_id=campaign_id)["id"] == second["id"]

    revoked = repository.revoke_active_code(campaign_id=campaign_id, now=now + 2)
    assert revoked is not None and revoked["revoked_at"] == now + 2
    assert "code_hash" not in revoked
    assert repository.revoke_active_code(campaign_id=campaign_id, now=now + 3) is None


def test_redeem_creates_player_membership_and_receipt_once(db):
    repository, gm_id, campaign_id = _setup()
    player_id = seed_user(name="Player")
    now = int(time.time())
    repository.rotate_active_code(
        campaign_id=campaign_id,
        created_by_user_id=gm_id,
        code_hash="c" * 64,
        expires_at=now + 3600,
        max_uses=2,
        now=now,
    )

    first = repository.redeem_for_user(code_hash="c" * 64, user_id=player_id, now=now + 1)
    second = repository.redeem_for_user(code_hash="c" * 64, user_id=player_id, now=now + 2)
    status = repository.get_status_for_campaign(campaign_id=campaign_id)

    assert first.status == "redeemed" and first.membership_created is True
    assert second.status == "already_member" and second.membership_created is False
    assert status["use_count"] == 1
    assert status["last_used_at"] == now + 1


def test_existing_member_is_idempotent_without_consuming_use(db):
    repository, gm_id, campaign_id = _setup()
    player_id = seed_user(name="Player")
    seed_member(campaign_id, player_id, "player")
    now = int(time.time())
    repository.rotate_active_code(
        campaign_id=campaign_id,
        created_by_user_id=gm_id,
        code_hash="d" * 64,
        expires_at=now + 3600,
        max_uses=1,
        now=now,
    )
    outcome = repository.redeem_for_user(code_hash="d" * 64, user_id=player_id, now=now + 1)
    assert outcome.status == "already_member"
    assert repository.get_status_for_campaign(campaign_id=campaign_id)["use_count"] == 0


def test_redeem_reports_internal_state_without_mutation(db):
    repository, gm_id, campaign_id = _setup()
    player_id = seed_user(name="Player")
    now = int(time.time())
    assert repository.redeem_for_user(code_hash="e" * 64, user_id=player_id).status == "not_found"

    repository.rotate_active_code(
        campaign_id=campaign_id,
        created_by_user_id=gm_id,
        code_hash="e" * 64,
        expires_at=now,
        max_uses=1,
        now=now - 10,
    )
    assert (
        repository.redeem_for_user(code_hash="e" * 64, user_id=player_id, now=now).status
        == "expired"
    )
    repository.revoke_active_code(campaign_id=campaign_id, now=now + 1)
    assert (
        repository.redeem_for_user(code_hash="e" * 64, user_id=player_id, now=now + 2).status
        == "revoked"
    )


def test_failure_before_commit_rolls_back_membership_and_counter(db, monkeypatch):
    repository, gm_id, campaign_id = _setup()
    player_id = seed_user(name="Player")
    now = int(time.time())
    repository.rotate_active_code(
        campaign_id=campaign_id,
        created_by_user_id=gm_id,
        code_hash="f" * 64,
        expires_at=now + 3600,
        max_uses=1,
        now=now,
    )

    def fail_before_receipt(*args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("simulated redemption persistence failure")

    monkeypatch.setattr(repository, "_insert_redemption", fail_before_receipt)
    with pytest.raises(RuntimeError, match="simulated"):
        repository.redeem_for_user(code_hash="f" * 64, user_id=player_id, now=now + 1)

    with engine_connect() as connection:
        assert (
            connection.execute(
                select(campaign_members.c.id).where(campaign_members.c.user_id == player_id)
            ).first()
            is None
        )
        assert connection.execute(select(campaign_join_code_redemptions.c.id)).first() is None
    assert repository.get_status_for_campaign(campaign_id=campaign_id)["use_count"] == 0
