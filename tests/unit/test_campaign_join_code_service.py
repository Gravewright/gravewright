from __future__ import annotations

import logging
import time

import pytest

from app.business.campaigns.campaign_join_code_service import (
    PUBLIC_UNAVAILABLE_ERROR,
    RATE_LIMIT_ERROR,
    CampaignJoinCodeService,
)
from app.helpers.codes import hash_join_code
from app.observability.diagnostics import diagnostics_recorder
from app.persistence.repositories.campaign_join_code_repository import (
    CampaignJoinCodeRepository,
)
from tests.conftest import seed_campaign, seed_member, seed_user


def _setup():
    gm_id = seed_user(name="GM")
    player_id = seed_user(name="Player")
    campaign_id = seed_campaign(gm_id)
    return CampaignJoinCodeService(), gm_id, player_id, campaign_id


def test_management_is_gm_only(db):
    service, gm_id, player_id, campaign_id = _setup()
    denied = service.generate_or_rotate(campaign_id=campaign_id, user_id=player_id)
    assert denied.success is False
    assert denied.error_key == "campaign.join_code.errors.permission_denied"
    assert service.revoke(campaign_id=campaign_id, user_id=player_id).success is False
    assert service.status(campaign_id=campaign_id, user_id=player_id).success is False

    allowed = service.generate_or_rotate(campaign_id=campaign_id, user_id=gm_id)
    assert allowed.success is True
    assert allowed.code


@pytest.mark.parametrize("role", ["assistant_gm", "player", "streamer"])
def test_non_gm_campaign_members_cannot_manage_join_codes(db, role):
    service, _, _, campaign_id = _setup()
    member_id = seed_user(name=role)
    seed_member(campaign_id, member_id, role)

    assert service.status(campaign_id=campaign_id, user_id=member_id).success is False


@pytest.mark.parametrize(
    "kwargs,error_key",
    [
        ({"role": "assistant_gm"}, "campaign.join_code.errors.invalid_role"),
        ({"expires_in_hours": 0}, "campaign.join_code.errors.invalid_expiration"),
        ({"expires_in_hours": 721}, "campaign.join_code.errors.invalid_expiration"),
        ({"max_uses": 0}, "campaign.join_code.errors.invalid_max_uses"),
        ({"max_uses": 1001}, "campaign.join_code.errors.invalid_max_uses"),
    ],
)
def test_generation_validates_server_side_limits_and_player_role(db, kwargs, error_key):
    service, gm_id, _, campaign_id = _setup()
    result = service.generate_or_rotate(campaign_id=campaign_id, user_id=gm_id, **kwargs)
    assert result.success is False
    assert result.error_key == error_key


def test_generate_rotate_status_and_revoke_are_sanitized(db):
    service, gm_id, _, campaign_id = _setup()
    generated = service.generate_or_rotate(
        campaign_id=campaign_id,
        user_id=gm_id,
        expires_in_hours=24,
        max_uses=5,
    )
    assert generated.success and generated.code
    assert generated.payload["role"] == "player"
    assert generated.payload["masked_code"] == "****-****-****"
    assert "code_hash" not in generated.payload

    rotated = service.generate_or_rotate(campaign_id=campaign_id, user_id=gm_id)
    assert rotated.success and rotated.code != generated.code
    assert rotated.message_key == "campaign.join_code.rotated"
    status = service.status(campaign_id=campaign_id, user_id=gm_id)
    assert status.success
    assert "code_hash" not in status.payload["join_code"]
    assert generated.code not in str(status.payload)
    assert service.revoke(campaign_id=campaign_id, user_id=gm_id).success
    assert service.revoke(campaign_id=campaign_id, user_id=gm_id).success


def test_successful_redeem_returns_campaign_member_and_is_idempotent(db):
    service, gm_id, player_id, campaign_id = _setup()
    generated = service.generate_or_rotate(campaign_id=campaign_id, user_id=gm_id)
    first = service.redeem(code=generated.code, user_id=player_id, client_ip="192.0.2.1")
    second = service.redeem(code=generated.code, user_id=player_id, client_ip="192.0.2.1")
    assert first.success and first.payload["membership_created"] is True
    assert first.payload["campaign"]["id"] == campaign_id
    assert first.payload["member"]["role"] == "player"
    assert second.success and second.payload["membership_created"] is False


def test_different_internal_failures_have_one_public_error(db):
    service, gm_id, player_id, campaign_id = _setup()
    now = int(time.time())
    repository = CampaignJoinCodeRepository()
    outcomes = [service.redeem(code="invalid", user_id=player_id, client_ip="198.51.100.1")]

    expired = "ABCD-EFGH-JKMP"
    repository.rotate_active_code(
        campaign_id=campaign_id,
        created_by_user_id=gm_id,
        code_hash=hash_join_code(expired),
        expires_at=now,
        max_uses=1,
        now=now - 1,
    )
    outcomes.append(service.redeem(code=expired, user_id=player_id, client_ip="198.51.100.2"))

    revoked = "ABCD-EFGH-JKMQ"
    repository.rotate_active_code(
        campaign_id=campaign_id,
        created_by_user_id=gm_id,
        code_hash=hash_join_code(revoked),
        expires_at=now + 3600,
        max_uses=1,
        now=now,
    )
    repository.revoke_active_code(campaign_id=campaign_id, now=now + 1)
    outcomes.append(service.redeem(code=revoked, user_id=player_id, client_ip="198.51.100.3"))

    exhausted = "ABCD-EFGH-JKMR"
    repository.rotate_active_code(
        campaign_id=campaign_id,
        created_by_user_id=gm_id,
        code_hash=hash_join_code(exhausted),
        expires_at=now + 3600,
        max_uses=1,
        now=now,
    )
    first_user = seed_user(name="First")
    assert service.redeem(code=exhausted, user_id=first_user, client_ip="198.51.100.4").success
    outcomes.append(service.redeem(code=exhausted, user_id=player_id, client_ip="198.51.100.5"))

    assert {outcome.error_key for outcome in outcomes} == {PUBLIC_UNAVAILABLE_ERROR}


def test_rate_limit_applies_independently_by_user_and_ip(db):
    service, _, _, _ = _setup()
    for index in range(10):
        result = service.redeem(
            code="invalid",
            user_id="same-user",
            client_ip=f"203.0.113.{index + 1}",
        )
        assert result.error_key == PUBLIC_UNAVAILABLE_ERROR
    blocked_user = service.redeem(code="invalid", user_id="same-user", client_ip="203.0.113.200")
    assert blocked_user.rate_limited and blocked_user.error_key == RATE_LIMIT_ERROR

    for index in range(10):
        result = service.redeem(
            code="invalid",
            user_id=f"ip-user-{index}",
            client_ip="192.0.2.200",
        )
        assert result.error_key == PUBLIC_UNAVAILABLE_ERROR
    blocked_ip = service.redeem(code="invalid", user_id="another-user", client_ip="192.0.2.200")
    assert blocked_ip.rate_limited and blocked_ip.error_key == RATE_LIMIT_ERROR


def test_success_clears_redeem_failures(db):
    service, gm_id, player_id, campaign_id = _setup()
    generated = service.generate_or_rotate(campaign_id=campaign_id, user_id=gm_id)
    for _ in range(9):
        assert not service.redeem(code="invalid", user_id=player_id, client_ip="192.0.2.55").success
    assert service.redeem(code=generated.code, user_id=player_id, client_ip="192.0.2.55").success
    after_clear = service.redeem(code="invalid", user_id=player_id, client_ip="192.0.2.55")
    assert after_clear.error_key == PUBLIC_UNAVAILABLE_ERROR
    assert after_clear.rate_limited is False


def test_logs_and_diagnostics_never_contain_plaintext_or_digest(db, caplog):
    diagnostics_recorder.clear()
    service, gm_id, player_id, campaign_id = _setup()
    generated = service.generate_or_rotate(campaign_id=campaign_id, user_id=gm_id)
    digest = hash_join_code(generated.code)
    with caplog.at_level(logging.INFO, logger="gravewright.diagnostics"):
        service.redeem(code=generated.code, user_id=player_id, client_ip="192.0.2.9")
    rendered = "\n".join(record.getMessage() for record in caplog.records)
    recent = str(diagnostics_recorder.recent(limit=20))
    assert generated.code not in rendered + recent
    assert generated.code.replace("-", "") not in rendered + recent
    assert digest not in rendered + recent
