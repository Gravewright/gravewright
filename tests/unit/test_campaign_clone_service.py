from __future__ import annotations

import pytest
from sqlalchemy import func, insert, select

from app.business.campaigns.campaign_clone_service import (
    CampaignCloneOptions,
    CampaignCloneService,
)
from app.persistence.database import engine_begin, engine_connect
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.item_repository import ItemRepository
from app.persistence.repositories.journal_repository import JournalRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.tables import actors_core, campaign_join_codes, campaign_members, campaigns
from app.persistence.tables import campaign_invitations, chat_messages, quest_board_entries
from app.persistence.tables import items_core, scenes
from tests.conftest import seed_campaign, seed_user


def _count(table, **filters) -> int:
    statement = select(func.count()).select_from(table)
    for key, value in filters.items():
        statement = statement.where(getattr(table.c, key) == value)
    with engine_connect() as connection:
        return int(connection.execute(statement).scalar_one())


def test_minimal_clone_creates_distinct_campaign_with_only_owner(db):
    gm_id = seed_user(name="GM")
    source_id = seed_campaign(gm_id, title="Source")
    result = CampaignCloneService().clone(
        source_campaign_id=source_id,
        user_id=gm_id,
        title="Source Copy",
        options=CampaignCloneOptions(
            packages=False,
            scenes=False,
            actors=False,
            items=False,
            journals=False,
            settings=False,
        ),
    )
    assert result.success and result.campaign_id != source_id
    assert _count(campaign_members, campaign_id=result.campaign_id) == 1
    assert _count(scenes, campaign_id=result.campaign_id) == 0


def test_selective_clone_remaps_content_and_journal_links(db):
    gm_id = seed_user(name="GM")
    source_id = seed_campaign(gm_id, title="Source")
    actor_id = ActorRepository().create(
        campaign_id=source_id,
        system_id="test",
        actor_type="npc",
        name="Clone Actor",
        created_by_user_id=gm_id,
    )
    item_id = ItemRepository().create(
        campaign_id=source_id,
        system_id="test",
        item_type="weapon",
        name="Clone Item",
        created_by_user_id=gm_id,
    )
    board_id = JournalRepository().create(
        campaign_id=source_id,
        created_by_user_id=gm_id,
        journal_type="quest_board",
        title="Clone Board",
    )
    quest_id = JournalRepository().create(
        campaign_id=source_id,
        created_by_user_id=gm_id,
        journal_type="quest",
        title="Clone Quest",
    )
    with engine_begin() as connection:
        connection.execute(
            insert(quest_board_entries).values(
                board_id=board_id,
                quest_id=quest_id,
                sort_order=0,
                pinned=0,
                visibility="public_card",
                created_at=1,
            )
        )
    SceneRepository().create(
        campaign_id=source_id,
        name="Clone Scene",
        width=1000,
        height=1000,
        tile_size=100,
        chunk_size=16,
    )

    result = CampaignCloneService().clone(
        source_campaign_id=source_id,
        user_id=gm_id,
        title="Complete Copy",
        options=CampaignCloneOptions(),
    )
    assert result.success and result.campaign_id
    assert result.summary["actors"] == 1
    assert result.summary["items"] == 1
    assert result.summary["journals"] == 2
    assert result.summary["scenes"] == 1
    with engine_connect() as connection:
        cloned_actor = (
            connection.execute(
                select(actors_core).where(actors_core.c.campaign_id == result.campaign_id)
            )
            .mappings()
            .one()
        )
        cloned_item = (
            connection.execute(
                select(items_core).where(items_core.c.campaign_id == result.campaign_id)
            )
            .mappings()
            .one()
        )
    assert cloned_actor["id"] != actor_id and cloned_actor["portrait_asset_id"] is None
    assert cloned_item["id"] != item_id and cloned_item["portrait_asset_id"] is None
    assert _count(quest_board_entries) == 2


def test_preview_is_read_only_and_declares_private_exclusions(db):
    gm_id = seed_user(name="GM")
    source_id = seed_campaign(gm_id, title="Source")
    before = _count(campaigns)
    result = CampaignCloneService().preview(
        source_campaign_id=source_id,
        user_id=gm_id,
        options=CampaignCloneOptions(),
    )
    assert result.success
    assert _count(campaigns) == before
    assert {"members", "invitations", "join_codes", "chat", "presence"} <= set(
        result.summary["excluded"]
    )


def test_clone_rolls_back_whole_campaign_on_intermediate_failure(db, monkeypatch):
    gm_id = seed_user(name="GM")
    source_id = seed_campaign(gm_id, title="Source")
    service = CampaignCloneService()

    def fail(*args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("simulated clone failure")

    monkeypatch.setattr(service, "_clone_journals", fail)
    before = _count(campaigns)
    with pytest.raises(RuntimeError, match="simulated"):
        service.clone(
            source_campaign_id=source_id,
            user_id=gm_id,
            title="Failed Copy",
            options=CampaignCloneOptions(),
        )
    assert _count(campaigns) == before


def test_non_gm_cannot_preview_or_clone(db):
    gm_id = seed_user(name="GM")
    outsider_id = seed_user(name="Outsider")
    source_id = seed_campaign(gm_id)
    service = CampaignCloneService()
    preview = service.preview(
        source_campaign_id=source_id,
        user_id=outsider_id,
        options=CampaignCloneOptions(),
    )
    clone = service.clone(
        source_campaign_id=source_id,
        user_id=outsider_id,
        title="Forbidden Copy",
        options=CampaignCloneOptions(),
    )
    assert not preview.success and not clone.success
    assert _count(campaign_invitations, campaign_id=source_id) == 0
    assert _count(campaign_join_codes, campaign_id=source_id) == 0
    assert _count(chat_messages, campaign_id=source_id) == 0
