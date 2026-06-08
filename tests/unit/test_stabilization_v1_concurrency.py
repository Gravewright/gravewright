"""Acceptance tests for the STABILIZATION_V1 P0 concurrency fixes.

- P0.2: optimistic concurrency (CAS) on token override/visibility/link mutations.
- P0.3: race-free ``room_event_log.seq`` allocation via DB autoincrement.

The SQLite test engine runs in WAL mode with ``busy_timeout=5000`` (see
``app/persistence/engine.py``), so the threaded cases below contend on a real
writer lock instead of failing fast — close enough to exercise the invariant.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from app.persistence.repositories.token_repository import TokenRepository
from app.realtime.event_log import RoomEventLog
from app.realtime.events import TransportEvent
from tests.conftest import seed_actor
from tests.conftest import seed_campaign
from tests.conftest import seed_scene
from tests.conftest import seed_user


def _make_token(repo: TokenRepository, db) -> dict:
    gm_id = seed_user(email="stab-cas-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)
    actor_id = seed_actor(campaign_id, gm_id, name="CAS Subject")
    return repo.create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)


                                                                             
                               
                                                                             

def test_update_overrides_cas_rejects_stale_version(db):
    repo = TokenRepository()
    token = _make_token(repo, db)
    assert token["version"] == 1

    first = repo.update_overrides(
        token_id=token["id"], overrides={"hp": 10}, expected_version=1
    )
    assert first is not None
    assert first["version"] == 2

                                                                                
    second = repo.update_overrides(
        token_id=token["id"], overrides={"hp": 99}, expected_version=1
    )
    assert second is None

    current = repo.get_by_id(token["id"])
    assert current["overrides"] == {"hp": 10}
    assert current["version"] == 2


def test_set_hidden_cas_rejects_stale_version(db):
    repo = TokenRepository()
    token = _make_token(repo, db)

    first = repo.set_hidden(token_id=token["id"], hidden=True, expected_version=1)
    assert first is not None
    assert first["version"] == 2
    assert first["hidden"] == 1

    second = repo.set_hidden(token_id=token["id"], hidden=False, expected_version=1)
    assert second is None

    current = repo.get_by_id(token["id"])
    assert current["hidden"] == 1
    assert current["version"] == 2


def test_update_link_mode_and_overrides_cas_rejects_stale_version(db):
    from app.domain.tokens import TokenActorLinkMode

    repo = TokenRepository()
    token = _make_token(repo, db)

    first = repo.update_link_mode_and_overrides(
        token_id=token["id"],
        actor_link_mode=TokenActorLinkMode.UNLINKED,
        overrides={"hp": 5},
        expected_version=1,
    )
    assert first is not None
    assert first["version"] == 2

    second = repo.update_link_mode_and_overrides(
        token_id=token["id"],
        actor_link_mode=TokenActorLinkMode.UNLINKED,
        overrides={"hp": 7},
        expected_version=1,
    )
    assert second is None


def test_update_overrides_without_expected_version_is_unconditional(db):
    """The CAS guard is opt-in: callers that omit expected_version still win."""
    repo = TokenRepository()
    token = _make_token(repo, db)

    a = repo.update_overrides(token_id=token["id"], overrides={"hp": 1})
    b = repo.update_overrides(token_id=token["id"], overrides={"hp": 2})
    assert a["version"] == 2
    assert b["version"] == 3


def test_concurrent_update_overrides_yields_exactly_one_conflict(db):
    repo = TokenRepository()
    token = _make_token(repo, db)
    expected = token["version"]

    def write(value: int):
        return repo.update_overrides(
            token_id=token["id"], overrides={"hp": value}, expected_version=expected
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, [10, 20]))

    successes = [r for r in results if r is not None]
    conflicts = [r for r in results if r is None]
    assert len(successes) == 1
    assert len(conflicts) == 1
    assert successes[0]["version"] == expected + 1


                                                                             
                                                
                                                                             

def test_concurrent_appends_produce_unique_contiguous_seq(db):
    gm_id = seed_user(email="stab-seq-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    event_log = RoomEventLog()

    n = 25

    def append(i: int) -> int:
        return event_log.append(
            room_id=campaign_id,
            event=TransportEvent.SCENE_UPDATED,
            payload={"room_id": campaign_id, "scene_id": f"scene-{i}"},
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        seqs = list(pool.map(append, range(n)))

    assert all(s is not None for s in seqs)
    assert len(set(seqs)) == n          
    assert sorted(seqs) == list(range(min(seqs), min(seqs) + n))              
