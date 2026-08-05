from __future__ import annotations

from app.domain.scenes import RenderPriority
from app.domain.scenes import RenderPriorityAgingPolicy
from app.engine.scenes.render_scheduler import RenderPriorityScheduler
from app.engine.scenes.render_scheduler import SchedulerBudget


def test_scheduler_dequeues_highest_priority_first():
    scheduler = RenderPriorityScheduler()

    scheduler.enqueue(key="low", payload={"id": "low"}, priority=RenderPriority.LOW, now_ms=0)
    scheduler.enqueue(key="high", payload={"id": "high"}, priority=RenderPriority.HIGH, now_ms=0)
    scheduler.enqueue(
        key="normal",
        payload={"id": "normal"},
        priority=RenderPriority.NORMAL,
        now_ms=0,
    )

    assert scheduler.dequeue(now_ms=0).key == "high"
    assert scheduler.dequeue(now_ms=0).key == "normal"
    assert scheduler.dequeue(now_ms=0).key == "low"


def test_scheduler_uses_fifo_with_same_effective_priority():
    scheduler = RenderPriorityScheduler()

    scheduler.enqueue(key="first", payload=None, priority=RenderPriority.NORMAL, now_ms=0)
    scheduler.enqueue(key="second", payload=None, priority=RenderPriority.NORMAL, now_ms=1)

    assert scheduler.dequeue(now_ms=1).key == "first"
    assert scheduler.dequeue(now_ms=1).key == "second"


def test_scheduler_aging_promotes_waiting_items():
    scheduler = RenderPriorityScheduler(
        aging_policy=RenderPriorityAgingPolicy(
            promote_after_ms=100,
            max_aged_priority=RenderPriority.HIGH,
        )
    )

    scheduler.enqueue(key="waiting", payload=None, priority=RenderPriority.BACKGROUND, now_ms=0)
    scheduler.enqueue(key="fresh", payload=None, priority=RenderPriority.NORMAL, now_ms=299)

    assert scheduler.dequeue(now_ms=300).key == "waiting"


def test_scheduler_replaces_existing_key_without_losing_original_order():
    scheduler = RenderPriorityScheduler()

    scheduler.enqueue(key="same", payload=1, priority=RenderPriority.LOW, now_ms=0)
    scheduler.enqueue(key="other", payload=2, priority=RenderPriority.LOW, now_ms=1)
    scheduler.enqueue(key="same", payload=3, priority=RenderPriority.LOW, now_ms=2)

    item = scheduler.dequeue(now_ms=2)

    assert item.key == "same"
    assert item.payload == 3


def test_drain_returns_items_in_priority_order():
    scheduler = RenderPriorityScheduler()
    scheduler.enqueue(key="bg", payload=None, priority=RenderPriority.BACKGROUND, now_ms=0)
    scheduler.enqueue(key="hi", payload=None, priority=RenderPriority.HIGH, now_ms=0)
    scheduler.enqueue(key="no", payload=None, priority=RenderPriority.NORMAL, now_ms=0)

    drained = scheduler.drain(now_ms=0, budget=SchedulerBudget(max_items=10))

    assert [item.key for item in drained] == ["hi", "no", "bg"]
    assert len(scheduler) == 0


def test_drain_orders_by_order_field_within_priority_tier():
    scheduler = RenderPriorityScheduler()
                                                                          
                                                                        
    scheduler.enqueue(key="far", payload=None, priority=RenderPriority.NORMAL, now_ms=0, order=3)
    scheduler.enqueue(key="near", payload=None, priority=RenderPriority.NORMAL, now_ms=0, order=0)
    scheduler.enqueue(key="mid", payload=None, priority=RenderPriority.NORMAL, now_ms=0, order=1)

    drained = scheduler.drain(now_ms=0, budget=SchedulerBudget(max_items=10))

    assert [item.key for item in drained] == ["near", "mid", "far"]


def test_priority_tier_beats_order():
    scheduler = RenderPriorityScheduler()
                                                                             
    scheduler.enqueue(key="far_high", payload=None, priority=RenderPriority.HIGH, now_ms=0, order=9)
    scheduler.enqueue(key="near_low", payload=None, priority=RenderPriority.NORMAL, now_ms=0, order=0)

    drained = scheduler.drain(now_ms=0, budget=SchedulerBudget(max_items=10))

    assert [item.key for item in drained] == ["far_high", "near_low"]


def test_drain_respects_max_items():
    scheduler = RenderPriorityScheduler()
    for index in range(5):
        scheduler.enqueue(
            key=f"k{index}",
            payload=None,
            priority=RenderPriority.NORMAL,
            now_ms=index,
        )

    drained = scheduler.drain(now_ms=10, budget=SchedulerBudget(max_items=2))

    assert len(drained) == 2
    assert len(scheduler) == 3


def test_drain_respects_max_payload_bytes():
    scheduler = RenderPriorityScheduler()
    scheduler.enqueue(
        key="a", payload=None, priority=RenderPriority.HIGH, now_ms=0, byte_size=400
    )
    scheduler.enqueue(
        key="b", payload=None, priority=RenderPriority.HIGH, now_ms=1, byte_size=400
    )

    drained = scheduler.drain(
        now_ms=0, budget=SchedulerBudget(max_items=10, max_payload_bytes=500)
    )

    assert [item.key for item in drained] == ["a"]
    assert len(scheduler) == 1


def test_drain_respects_max_cost():
    scheduler = RenderPriorityScheduler()
    scheduler.enqueue(key="a", payload=None, priority=RenderPriority.HIGH, now_ms=0, cost=3)
    scheduler.enqueue(key="b", payload=None, priority=RenderPriority.HIGH, now_ms=1, cost=3)

    drained = scheduler.drain(now_ms=0, budget=SchedulerBudget(max_items=10, max_cost=4))

    assert [item.key for item in drained] == ["a"]


def test_drain_allows_single_item_larger_than_budget():
    scheduler = RenderPriorityScheduler()
    scheduler.enqueue(
        key="huge", payload=None, priority=RenderPriority.HIGH, now_ms=0, byte_size=10_000
    )

    drained = scheduler.drain(
        now_ms=0, budget=SchedulerBudget(max_items=10, max_payload_bytes=500)
    )

    assert [item.key for item in drained] == ["huge"]


def test_replacing_item_preserves_first_queued_age_for_aging():
    scheduler = RenderPriorityScheduler(
        aging_policy=RenderPriorityAgingPolicy(
            promote_after_ms=100,
            max_aged_priority=RenderPriority.HIGH,
        )
    )

    scheduler.enqueue(key="a", payload=1, priority=RenderPriority.BACKGROUND, now_ms=0)
    scheduler.enqueue(key="a", payload=2, priority=RenderPriority.BACKGROUND, now_ms=250)
    scheduler.enqueue(key="b", payload=3, priority=RenderPriority.NORMAL, now_ms=250)

    item = scheduler.dequeue(now_ms=300)
    assert item.key == "a"
    assert item.payload == 2


def test_cancel_removes_item_by_key():
    scheduler = RenderPriorityScheduler()
    scheduler.enqueue(key="a", payload=None, priority=RenderPriority.NORMAL, now_ms=0)

    assert scheduler.cancel("a") is True
    assert scheduler.cancel("a") is False
    assert len(scheduler) == 0


def test_cancel_where_removes_by_predicate():
    scheduler = RenderPriorityScheduler()
    scheduler.enqueue(key="a", payload=None, priority=RenderPriority.NORMAL, now_ms=0, cost=1)
    scheduler.enqueue(key="b", payload=None, priority=RenderPriority.NORMAL, now_ms=0, cost=5)

    removed = scheduler.cancel_where(lambda item: item.cost > 2)

    assert removed == 1
    assert len(scheduler) == 1


def test_cancel_scope_removes_older_viewport_generation():
    scheduler = RenderPriorityScheduler()
    scheduler.enqueue(
        key="old",
        payload=None,
        priority=RenderPriority.NORMAL,
        now_ms=0,
        scene_id="s1",
        viewport_id="main",
        viewport_generation=1,
    )
    scheduler.enqueue(
        key="new",
        payload=None,
        priority=RenderPriority.NORMAL,
        now_ms=0,
        scene_id="s1",
        viewport_id="main",
        viewport_generation=2,
    )

    removed = scheduler.cancel_scope(
        scene_id="s1",
        viewport_id="main",
        older_than_viewport_generation=2,
    )

    assert removed == 1
    assert scheduler.dequeue(now_ms=0).key == "new"


def test_cancel_scope_removes_mismatched_scene_epoch():
    scheduler = RenderPriorityScheduler()
    scheduler.enqueue(
        key="stale", payload=None, priority=RenderPriority.NORMAL, now_ms=0,
        scene_id="s1", scene_epoch=3,
    )
    scheduler.enqueue(
        key="fresh", payload=None, priority=RenderPriority.NORMAL, now_ms=0,
        scene_id="s1", scene_epoch=4,
    )

    removed = scheduler.cancel_scope(scene_id="s1", scene_epoch_not=4)

    assert removed == 1
    assert scheduler.dequeue(now_ms=0).key == "fresh"


def test_expired_items_are_discarded():
    scheduler = RenderPriorityScheduler()
    scheduler.enqueue(
        key="a", payload=None, priority=RenderPriority.HIGH, now_ms=0, expires_at_ms=100
    )

    assert scheduler.dequeue(now_ms=150) is None
    assert len(scheduler) == 0
    assert scheduler.snapshot(now_ms=150).expired_total == 1


def test_snapshot_reports_counters_and_distribution():
    scheduler = RenderPriorityScheduler()
    scheduler.enqueue(
        key="a", payload=None, priority=RenderPriority.HIGH, now_ms=0, byte_size=100, cost=2
    )
    scheduler.enqueue(
        key="b", payload=None, priority=RenderPriority.NORMAL, now_ms=0, byte_size=50
    )

    snapshot = scheduler.snapshot(now_ms=0)

    assert snapshot.queued_items == 2
    assert snapshot.queued_bytes == 150
    assert snapshot.queued_cost == 3
    assert snapshot.by_base_priority == {"high": 1, "normal": 1}
    assert snapshot.enqueued_total == 2


def test_clear_removes_everything():
    scheduler = RenderPriorityScheduler()
    scheduler.enqueue(key="a", payload=None, priority=RenderPriority.NORMAL, now_ms=0)
    scheduler.enqueue(key="b", payload=None, priority=RenderPriority.NORMAL, now_ms=0)

    scheduler.clear()

    assert len(scheduler) == 0


def test_dequeue_on_empty_returns_none():
    scheduler = RenderPriorityScheduler()
    assert scheduler.dequeue(now_ms=0) is None
