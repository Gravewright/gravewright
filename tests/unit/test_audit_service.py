from __future__ import annotations

import pytest

from app.business.audit import AuditService
from app.business.audit.catalog import safe_metadata
from tests.conftest import seed_campaign, seed_user


def test_catalog_rejects_unknown_events_and_strips_unallowed_metadata():
    with pytest.raises(ValueError):
        safe_metadata("unknown.event", {"anything": "value"})
    assert safe_metadata(
        "join_code.generated",
        {"expires_at": 123, "max_uses": 4, "code": "SECRET", "email": "x@y"},
    ) == {"expires_at": 123, "max_uses": 4}


def test_record_and_paginate_are_gm_only(db):
    gm_id = seed_user(name="GM")
    outsider_id = seed_user(name="Outsider")
    campaign_id = seed_campaign(gm_id)
    service = AuditService()
    service.record(
        campaign_id=campaign_id,
        actor_user_id=gm_id,
        event_type="join_code.generated",
        subject_type="join_code",
        subject_id="internal-id",
        action="generate",
        result="success",
        metadata={"expires_at": 123, "code_hash": "must-not-persist"},
    )

    allowed = service.list(campaign_id=campaign_id, user_id=gm_id)
    denied = service.list(campaign_id=campaign_id, user_id=outsider_id)
    assert allowed.success and allowed.total == 1
    assert allowed.events[0]["metadata"] == {"expires_at": 123}
    assert "must-not-persist" not in str(allowed.events)
    assert denied.error_key == "audit.errors.denied"


def test_pagination_and_event_filter_are_bounded(db):
    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    service = AuditService()
    for index in range(3):
        service.record(
            campaign_id=campaign_id,
            actor_user_id=gm_id,
            event_type="snapshot.created",
            subject_type="snapshot",
            subject_id=str(index),
            action="create",
            result="success",
            metadata={"kind": "manual", "format_version": 1},
            now=index + 1,
        )
    page = service.list(
        campaign_id=campaign_id,
        user_id=gm_id,
        event_type="snapshot.created",
        page=2,
        page_size=2,
    )
    assert page.total == 3
    assert len(page.events) == 1
    assert service.list(
        campaign_id=campaign_id, user_id=gm_id, event_type="not.valid"
    ).error_key == "audit.errors.invalid_filter"


def test_join_code_integration_persists_no_plaintext_or_hash(db):
    from app.business.campaigns.campaign_join_code_service import CampaignJoinCodeService

    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    generated = CampaignJoinCodeService().generate_or_rotate(
        campaign_id=campaign_id, user_id=gm_id
    )
    result = AuditService().export(campaign_id=campaign_id, user_id=gm_id)
    rendered = str(result.events)
    assert result.success and result.total == 1
    assert result.events[0]["event_type"] == "join_code.generated"
    assert generated.code not in rendered
    assert "code_hash" not in rendered


def test_retention_prunes_old_events_and_failed_action_is_safe(db):
    from app.business.campaigns.campaign_join_code_service import CampaignJoinCodeService

    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    service = AuditService()
    service.record(
        campaign_id=campaign_id,
        actor_user_id=gm_id,
        event_type="snapshot.created",
        action="create",
        result="success",
        now=1,
    )
    assert service.prune(now=200 * 86400) == 1

    CampaignJoinCodeService().generate_or_rotate(
        campaign_id=campaign_id, user_id=gm_id, role="forbidden-role"
    )
    result = service.list(campaign_id=campaign_id, user_id=gm_id)
    assert result.total == 1
    assert result.events[0]["result"] == "denied"
    assert "forbidden-role" not in str(result.events)
