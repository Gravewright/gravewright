from __future__ import annotations

import asyncio

from app.actions.game import manage_handouts
from tests.conftest import seed_campaign, seed_member, seed_user


class _Transport:
    def __init__(self, deliveries: list[dict]) -> None:
        self.deliveries = deliveries

    async def to_player(self, *, player_id, event, payload) -> None:
        self.deliveries.append({"player_id": player_id, "event": event.value, "payload": payload})


def test_present_targets_only_selected_user_without_room_log(db, monkeypatch):
    gm_id = seed_user(name="GM")
    selected_id = seed_user(name="Selected")
    other_id = seed_user(name="Other")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, selected_id, "player")
    seed_member(campaign_id, other_id, "player")
    deliveries = []
    monkeypatch.setattr(manage_handouts, "RealtimeTransport", lambda: _Transport(deliveries))
    asyncio.run(manage_handouts._present({
        "campaign_id": campaign_id, "resource_type": "journal", "resource_id": "journal-1",
        "subject_type": "user", "subject_id": selected_id, "created_by_user_id": gm_id,
    }))
    assert len(deliveries) == 1
    assert deliveries[0]["player_id"] == selected_id
    assert deliveries[0]["event"] == "handout.presented"
    assert deliveries[0]["payload"]["resource_type"] == "journal"
    assert deliveries[0]["payload"]["ticket"]
    assert other_id != deliveries[0]["player_id"]


def test_present_role_targets_only_that_campaign_role(db, monkeypatch):
    gm_id = seed_user(name="GM")
    player_id = seed_user(name="Player")
    assistant_id = seed_user(name="Assistant")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, "player")
    seed_member(campaign_id, assistant_id, "assistant_gm")
    deliveries = []
    monkeypatch.setattr(manage_handouts, "RealtimeTransport", lambda: _Transport(deliveries))
    asyncio.run(manage_handouts._present({
        "campaign_id": campaign_id, "resource_type": "item", "resource_id": "item-1",
        "subject_type": "role", "subject_id": "player", "created_by_user_id": gm_id,
    }))
    assert [delivery["player_id"] for delivery in deliveries] == [player_id]
    assert assistant_id not in [delivery["player_id"] for delivery in deliveries]
