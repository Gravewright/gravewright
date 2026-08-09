from __future__ import annotations

import time
import uuid

from sqlalchemy import insert

from app.business.search import GlobalSearchService
from app.persistence.database import engine_begin
from app.persistence.tables import actors_core
from tests.conftest import seed_campaign, seed_user


def test_global_search_five_thousand_resources_reference_latency(db):
    gm_id = seed_user(name="GM")
    campaign_id = seed_campaign(gm_id)
    now = int(time.time())
    rows = [
        {
            "id": uuid.uuid4().hex,
            "campaign_id": campaign_id,
            "system_id": "test",
            "type": "npc",
            "name": f"Benchmark Guard {index:04d}",
            "folder_id": None,
            "permissions_json": "{}",
            "status": "active",
            "version": 1,
            "created_by_user_id": gm_id,
            "created_at": now,
            "updated_at": now,
        }
        for index in range(5_000)
    ]
    with engine_begin() as connection:
        connection.execute(insert(actors_core), rows)

    started = time.perf_counter()
    result = GlobalSearchService().search(
        campaign_id=campaign_id,
        user_id=gm_id,
        query="benchmark guard",
    )
    elapsed_ms = (time.perf_counter() - started) * 1_000
    assert result.success and len(result.results) == 20
    assert elapsed_ms < 150, f"reference search took {elapsed_ms:.1f} ms"
