from __future__ import annotations

import time
import uuid

from sqlalchemy import insert

from app.business.search import GlobalSearchService
from app.persistence.database import engine_begin
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.item_repository import ItemRepository
from app.persistence.repositories.journal_repository import JournalRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.tables import campaign_members
from tests.conftest import seed_campaign, seed_user


def _add_player(campaign_id: str, user_id: str) -> None:
    now = int(time.time())
    with engine_begin() as connection:
        connection.execute(
            insert(campaign_members).values(
                id=uuid.uuid4().hex,
                campaign_id=campaign_id,
                user_id=user_id,
                role="player",
                created_at=now,
                updated_at=now,
            )
        )


def test_search_normalizes_all_core_resource_types_for_gm(db):
    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    ActorRepository().create(
        campaign_id=campaign_id,
        system_id="test",
        actor_type="npc",
        name="Moon Actor",
        created_by_user_id=gm_id,
    )
    ItemRepository().create(
        campaign_id=campaign_id,
        system_id="test",
        item_type="weapon",
        name="Moon Blade",
        created_by_user_id=gm_id,
    )
    JournalRepository().create(
        campaign_id=campaign_id,
        created_by_user_id=gm_id,
        journal_type="note",
        title="Moon Journal",
        content_markdown="A hidden moon clue for the party.",
    )
    SceneRepository().create(
        campaign_id=campaign_id,
        name="Moon Keep",
        width=1000,
        height=1000,
        tile_size=100,
        chunk_size=16,
    )

    result = GlobalSearchService().search(campaign_id=campaign_id, user_id=gm_id, query="moon")
    assert result.success
    assert {entry["type"] for entry in result.results} == {
        "actor",
        "item",
        "journal",
        "scene",
    }
    assert all(
        {"id", "type", "title", "subtitle", "icon", "snippet", "target"} <= entry.keys()
        for entry in result.results
    )


def test_search_filters_private_resources_for_player(db):
    gm_id = seed_user(name="GM")
    player_id = seed_user(name="Player")
    campaign_id = seed_campaign(gm_id)
    _add_player(campaign_id, player_id)
    visible_actor = ActorRepository().create(
        campaign_id=campaign_id,
        system_id="test",
        actor_type="pc",
        name="Secret Hero",
        created_by_user_id=gm_id,
        owner_user_ids=[player_id],
    )
    hidden_actor = ActorRepository().create(
        campaign_id=campaign_id,
        system_id="test",
        actor_type="npc",
        name="Secret Villain",
        created_by_user_id=gm_id,
    )
    visible_item = ItemRepository().create(
        campaign_id=campaign_id,
        system_id="test",
        item_type="weapon",
        name="Secret Sword",
        created_by_user_id=gm_id,
        owner_user_ids=[player_id],
    )
    hidden_item = ItemRepository().create(
        campaign_id=campaign_id,
        system_id="test",
        item_type="weapon",
        name="Secret Staff",
        created_by_user_id=gm_id,
    )
    visible_journal = JournalRepository().create(
        campaign_id=campaign_id,
        created_by_user_id=gm_id,
        journal_type="note",
        title="Secret Shared",
        visibility="shared",
    )
    hidden_journal = JournalRepository().create(
        campaign_id=campaign_id,
        created_by_user_id=gm_id,
        journal_type="note",
        title="Secret GM Note",
        visibility="private",
    )

    result = GlobalSearchService().search(
        campaign_id=campaign_id, user_id=player_id, query="secret"
    )
    ids = {entry["id"] for entry in result.results}
    assert {visible_actor, visible_item, visible_journal} <= ids
    assert hidden_actor not in ids
    assert hidden_item not in ids
    assert hidden_journal not in ids


def test_search_never_crosses_campaign_or_membership_boundary(db):
    first_gm = seed_user(name="First GM")
    second_gm = seed_user(name="Second GM")
    first_campaign = seed_campaign(first_gm)
    second_campaign = seed_campaign(second_gm)
    ActorRepository().create(
        campaign_id=second_campaign,
        system_id="test",
        actor_type="npc",
        name="Boundary Target",
        created_by_user_id=second_gm,
    )
    service = GlobalSearchService()
    own = service.search(campaign_id=first_campaign, user_id=first_gm, query="boundary")
    denied = service.search(campaign_id=second_campaign, user_id=first_gm, query="boundary")
    assert own.success and own.results == []
    assert not denied.success
    assert denied.error_key == "search.errors.denied"


def test_search_limits_and_short_queries(db):
    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    for index in range(30):
        ActorRepository().create(
            campaign_id=campaign_id,
            system_id="test",
            actor_type="npc",
            name=f"Guard {index:02d}",
            created_by_user_id=gm_id,
        )
    service = GlobalSearchService()
    assert service.search(campaign_id=campaign_id, user_id=gm_id, query="g").results == []
    assert len(service.search(campaign_id=campaign_id, user_id=gm_id, query="guard").results) == 20
