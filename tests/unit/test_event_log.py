from __future__ import annotations

import time

import pytest

from app.realtime.event_log import RoomEventLog
from app.realtime.events import TransportEvent
from app.realtime.transport import RealtimeTransport
from tests.conftest import seed_campaign
from tests.conftest import seed_user


def test_room_event_log_replays_events_after_sequence(db):
    gm_id = seed_user(name="GM", email="event-log-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    event_log = RoomEventLog()
    first_seq = event_log.append(
        room_id=campaign_id,
        event=TransportEvent.SCENE_ACTIVATED,
        payload={"room_id": campaign_id, "scene_id": "scene-1"},
    )
    second_seq = event_log.append(
        room_id=campaign_id,
        event=TransportEvent.SCENE_CHUNK_UPDATED,
        payload={
            "room_id": campaign_id,
            "scene_id": "scene-1",
            "layer_id": "layer-1",
            "cx": 0,
            "cy": 0,
            "version": 2,
        },
    )

    replay = event_log.replay_since(room_id=campaign_id, after_seq=first_seq)

    assert replay.expired is False
    assert replay.latest_seq == second_seq
    assert [event["event"] for event in replay.events] == [
        TransportEvent.SCENE_CHUNK_UPDATED.value
    ]
    assert replay.events[0]["event_seq"] == second_seq
    assert replay.events[0]["payload"]["version"] == 2


def test_room_event_log_skips_non_replayable_events(db):
    gm_id = seed_user(name="GM", email="event-log-presence@test.com")
    campaign_id = seed_campaign(gm_id)
    event_log = RoomEventLog()

    seq = event_log.append(
        room_id=campaign_id,
        event=TransportEvent.PRESENCE_UPDATED,
        payload={"room_id": campaign_id, "user_id": gm_id},
    )

    assert seq is None
    assert event_log.latest_seq(campaign_id) is None


def test_room_event_log_skips_token_events_to_avoid_private_replay(db):
    gm_id = seed_user(name="GM", email="event-log-token@test.com")
    campaign_id = seed_campaign(gm_id)
    event_log = RoomEventLog()

    seq = event_log.append(
        room_id=campaign_id,
        event=TransportEvent.TOKENS_MOVED,
        payload={
            "room_id": campaign_id,
            "scene_id": "scene-1",
            "tokens": [{"token_id": "private-token"}],
        },
    )

    assert seq is None
    assert event_log.latest_seq(campaign_id) is None


def test_replay_since_flags_gap_when_events_expired(db):
    """STABILIZATION_V1 P1.4 — reconnect after a retention gap must signal resync.

    A client that reconnects with an ``after_seq`` older than the oldest retained
    event has missed events that already aged out; ``replay_since`` must report
    ``expired=True`` so the client knows to do a full resync instead of silently
    skipping the gap.
    """
    gm_id = seed_user(name="GM", email="event-log-gap@test.com")
    campaign_id = seed_campaign(gm_id)
    event_log = RoomEventLog()

                                                                                
                                                                             
    seq1 = event_log.append(
        room_id=campaign_id,
        event=TransportEvent.SCENE_UPDATED,
        payload={"room_id": campaign_id, "scene_id": "scene-1"},
        ttl_seconds=-100,
    )
    event_log.append(
        room_id=campaign_id,
        event=TransportEvent.SCENE_UPDATED,
        payload={"room_id": campaign_id, "scene_id": "scene-2"},
        ttl_seconds=-100,
    )
    live_seq = event_log.append(
        room_id=campaign_id,
        event=TransportEvent.SCENE_CHUNK_UPDATED,
        payload={"room_id": campaign_id, "scene_id": "scene-3"},
    )

    replay = event_log.replay_since(room_id=campaign_id, after_seq=seq1)

    assert replay.expired is True
    assert replay.latest_seq == live_seq
    assert [event["event_seq"] for event in replay.events] == [live_seq]


def test_room_event_log_prunes_expired_events(db):
    gm_id = seed_user(name="GM", email="event-log-expired@test.com")
    campaign_id = seed_campaign(gm_id)
    event_log = RoomEventLog()
    event_log.append(
        room_id=campaign_id,
        event=TransportEvent.SCENE_UPDATED,
        payload={"room_id": campaign_id, "scene_id": "scene-1"},
        ttl_seconds=1,
    )

    deleted = event_log.prune_expired(now=int(time.time()) + 2)

    assert deleted == 1
    assert event_log.latest_seq(campaign_id) is None


@pytest.mark.asyncio
async def test_realtime_transport_records_replayable_room_events(db):
    gm_id = seed_user(name="GM", email="event-log-transport@test.com")
    campaign_id = seed_campaign(gm_id)
    event_log = RoomEventLog()
    transport = RealtimeTransport(event_log=event_log)

    await transport._deliver(
        user_ids=[gm_id],
        room_id=campaign_id,
        event=TransportEvent.SCENE_UPDATED,
        payload={"room_id": campaign_id, "scene_id": "scene-1"},
    )

    replay = event_log.replay_since(room_id=campaign_id, after_seq=0)

    assert replay.latest_seq == 1
