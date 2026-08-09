from __future__ import annotations

import time
import uuid

from sqlalchemy import insert

from app.business.handouts import HandoutService
from app.engine.assets.asset_read_service import AssetReadService
from app.engine.items.item_service import ItemService
from app.engine.journals.journal_service import JournalService
from app.persistence.database import engine_begin
from app.persistence.repositories.asset_repository import AssetRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.tables import items_core
from tests.conftest import seed_campaign, seed_member, seed_user


def _setup():
    gm_id = seed_user(name="GM")
    player_id = seed_user(name="Player")
    other_id = seed_user(name="Other")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, "player")
    seed_member(campaign_id, other_id, "player")
    item_id = uuid.uuid4().hex
    now = int(time.time())
    with engine_begin() as connection:
        connection.execute(insert(items_core).values(
            id=item_id, campaign_id=campaign_id, system_id="core", type="item",
            name="Secret Letter", folder_id=None, portrait_asset_id=None,
            permissions_json="{}", external_data_ref=None, status="active", version=1,
            created_by_user_id=gm_id, created_at=now, updated_at=now,
        ))
    return HandoutService(), gm_id, player_id, other_id, campaign_id, item_id


def test_targeted_user_grant_and_revoke_are_idempotent(db):
    service, gm_id, player_id, other_id, campaign_id, item_id = _setup()
    first = service.grant(
        campaign_id=campaign_id, user_id=gm_id, resource_type="item",
        resource_id=item_id, subject_type="user", subject_id=player_id,
    )
    second = service.grant(
        campaign_id=campaign_id, user_id=gm_id, resource_type="item",
        resource_id=item_id, subject_type="user", subject_id=player_id,
    )
    assert first.success and second.success and first.grant["id"] == second.grant["id"]
    assert service.can_view(campaign_id=campaign_id, user_id=player_id, resource_type="item", resource_id=item_id)
    assert not service.can_view(campaign_id=campaign_id, user_id=other_id, resource_type="item", resource_id=item_id)
    assert service.revoke(campaign_id=campaign_id, user_id=gm_id, grant_id=first.grant["id"]).success
    assert not service.can_view(campaign_id=campaign_id, user_id=player_id, resource_type="item", resource_id=item_id)


def test_everyone_and_role_grants_apply_only_inside_campaign(db):
    service, gm_id, player_id, _, campaign_id, item_id = _setup()
    role = service.grant(
        campaign_id=campaign_id, user_id=gm_id, resource_type="item",
        resource_id=item_id, subject_type="role", subject_id="player",
    )
    assert role.success
    assert service.can_view(campaign_id=campaign_id, user_id=player_id, resource_type="item", resource_id=item_id)
    outsider_id = seed_user(name="Outsider")
    assert not service.can_view(campaign_id=campaign_id, user_id=outsider_id, resource_type="item", resource_id=item_id)


def test_non_gm_and_cross_campaign_resource_are_denied(db):
    service, gm_id, player_id, _, campaign_id, item_id = _setup()
    other_campaign = seed_campaign(gm_id)
    denied = service.grant(
        campaign_id=campaign_id, user_id=player_id, resource_type="item",
        resource_id=item_id, subject_type="everyone",
    )
    crossed = service.grant(
        campaign_id=other_campaign, user_id=gm_id, resource_type="item",
        resource_id=item_id, subject_type="everyone",
    )
    assert denied.error_key == "handout.errors.denied"
    assert crossed.error_key == "handout.errors.not_found"


def test_legacy_grant_does_not_change_item_read_permission(db):
    service, gm_id, player_id, _, campaign_id, item_id = _setup()
    items = ItemService()
    assert items.get_item(item_id=item_id, user_id=player_id) is None
    assert service.grant(
        campaign_id=campaign_id, user_id=gm_id, resource_type="item",
        resource_id=item_id, subject_type="user", subject_id=player_id,
    ).success
    assert items.get_item(item_id=item_id, user_id=player_id) is None


def test_legacy_grant_does_not_change_private_journal_permission(db):
    service, gm_id, player_id, _, campaign_id, _ = _setup()
    journals = JournalService()
    created = journals.create_journal(
        campaign_id=campaign_id,
        user_id=gm_id,
        journal_type="diary",
        title="GM Notes",
        visibility="private",
        content_markdown="public text",
    )
    journal = journals.journals.get_by_id(created.journal_id)
    campaign = CampaignRepository().get_for_user(campaign_id=campaign_id, user_id=player_id)
    assert not journals.can_view_journal_directly(
        journal=dict(journal), campaign=dict(campaign), user_id=player_id
    )
    service.grant(
        campaign_id=campaign_id, user_id=gm_id, resource_type="journal",
        resource_id=created.journal_id, subject_type="user", subject_id=player_id,
    )
    assert not journals.can_view_journal_directly(
        journal=dict(journal), campaign=dict(campaign), user_id=player_id
    )
    assert not journals.can_edit_journal(
        journal=dict(journal), campaign=dict(campaign), user_id=player_id
    )


def test_legacy_grant_does_not_change_asset_read_permission(db, tmp_path):
    service, gm_id, player_id, _, campaign_id, _ = _setup()
    (tmp_path / "handout.png").write_bytes(b"image")
    asset = AssetRepository().create(
        campaign_id=campaign_id,
        owner_user_id=gm_id,
        filename="handout.png",
        content_type="image/png",
        byte_size=5,
        storage_path="handout.png",
        hash="safe-hash",
    )
    reader = AssetReadService()
    assert not reader.get_asset(
        asset_id=asset["id"], user_id=player_id, project_root=tmp_path
    ).success
    service.grant(
        campaign_id=campaign_id, user_id=gm_id, resource_type="asset",
        resource_id=asset["id"], subject_type="user", subject_id=player_id,
    )
    assert not reader.get_asset(
        asset_id=asset["id"], user_id=player_id, project_root=tmp_path
    ).success
