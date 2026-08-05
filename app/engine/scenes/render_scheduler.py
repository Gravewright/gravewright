from __future__ import annotations

import heapq
import time
from collections.abc import Callable
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from app.domain.scenes import RenderPriority
from app.domain.scenes import RenderPriorityAgingPolicy


@dataclass(frozen=True)
class SchedulerBudget:
    max_items: int
    max_payload_bytes: int | None = None
    max_cost: int | None = None
    max_elapsed_ms: float | None = None

    def __post_init__(self) -> None:
        if self.max_items <= 0:
            raise ValueError("max_items must be positive")
        if self.max_payload_bytes is not None and self.max_payload_bytes <= 0:
            raise ValueError("max_payload_bytes must be positive")
        if self.max_cost is not None and self.max_cost <= 0:
            raise ValueError("max_cost must be positive")
        if self.max_elapsed_ms is not None and self.max_elapsed_ms <= 0:
            raise ValueError("max_elapsed_ms must be positive")


@dataclass(frozen=True)
class RenderQueueItem:
    key: str
    payload: Any
    base_priority: RenderPriority
    first_queued_at_ms: int
    updated_at_ms: int
    sequence: int
    kind: str = "generic"
    scene_id: str | None = None
    scene_epoch: int | None = None
    viewport_id: str | None = None
    viewport_generation: int | None = None
    byte_size: int = 0
    cost: int = 1
                                                                            
                                                                        
    order: int = 0
    expires_at_ms: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def age_ms(self, now_ms: int) -> int:
        return max(0, now_ms - self.first_queued_at_ms)

    def is_expired(self, now_ms: int) -> bool:
        return self.expires_at_ms is not None and now_ms >= self.expires_at_ms


@dataclass(frozen=True)
class SchedulerSnapshot:
    queued_items: int
    queued_bytes: int
    queued_cost: int
    by_base_priority: dict[str, int]
    by_effective_priority: dict[str, int]
    oldest_item_age_ms: int | None
    enqueued_total: int
    replaced_total: int
    dequeued_total: int
    canceled_total: int
    expired_total: int
    aged_total: int


class RenderPriorityScheduler:
    """Priority queue for viewport-driven map streaming work.

    Deduplicates jobs by logical key (keeping the most recent payload while
    preserving the original queue age for aging), promotes starving work via the
    aging policy, and drains items under a byte/cost/time budget. The heap is
    rebuilt once per ``drain`` so dynamic aging stays correct without a stale
    persistent heap.
    """

    def __init__(
        self,
        *,
        aging_policy: RenderPriorityAgingPolicy | None = None,
    ) -> None:
        self.aging_policy = aging_policy or RenderPriorityAgingPolicy()
        self._items: dict[str, RenderQueueItem] = {}
        self._sequence_by_key: dict[str, int] = {}
        self._next_sequence = 0

        self._enqueued_total = 0
        self._replaced_total = 0
        self._dequeued_total = 0
        self._canceled_total = 0
        self._expired_total = 0
        self._aged_total = 0

    def enqueue(
        self,
        *,
        key: str,
        payload: Any,
        priority: RenderPriority,
        now_ms: int,
        kind: str = "generic",
        scene_id: str | None = None,
        scene_epoch: int | None = None,
        viewport_id: str | None = None,
        viewport_generation: int | None = None,
        byte_size: int = 0,
        cost: int = 1,
        order: int = 0,
        expires_at_ms: int | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> RenderQueueItem:
        if not key:
            raise ValueError("key is required")
        if byte_size < 0:
            raise ValueError("byte_size must be zero or positive")
        if cost <= 0:
            raise ValueError("cost must be positive")
        if not kind:
            raise ValueError("kind is required")

        existing = self._items.get(key)

        if key not in self._sequence_by_key:
            self._sequence_by_key[key] = self._next_sequence
            self._next_sequence += 1

        first_queued_at_ms = existing.first_queued_at_ms if existing else now_ms

        item = RenderQueueItem(
            key=key,
            payload=payload,
            base_priority=priority,
            first_queued_at_ms=first_queued_at_ms,
            updated_at_ms=now_ms,
            sequence=self._sequence_by_key[key],
            kind=kind,
            scene_id=scene_id,
            scene_epoch=scene_epoch,
            viewport_id=viewport_id,
            viewport_generation=viewport_generation,
            byte_size=byte_size,
            cost=cost,
            order=order,
            expires_at_ms=expires_at_ms,
            metadata=metadata or {},
        )

        self._items[key] = item
        self._enqueued_total += 1
        if existing is not None:
            self._replaced_total += 1

        return item

    def dequeue(self, *, now_ms: int) -> RenderQueueItem | None:
        drained = self.drain(now_ms=now_ms, budget=SchedulerBudget(max_items=1))
        return drained[0] if drained else None

    def drain(
        self,
        *,
        now_ms: int,
        budget: SchedulerBudget,
    ) -> tuple[RenderQueueItem, ...]:
        self._purge_expired(now_ms=now_ms)
        if not self._items:
            return ()

        started = time.perf_counter()
        heap = self._ranked_heap(now_ms=now_ms)
        drained: list[RenderQueueItem] = []
        used_bytes = 0
        used_cost = 0

        while heap and len(drained) < budget.max_items:
            if budget.max_elapsed_ms is not None and drained:
                elapsed_ms = (time.perf_counter() - started) * 1000
                if elapsed_ms >= budget.max_elapsed_ms:
                    break

            effective_int, _order, _sequence, key = heapq.heappop(heap)
            item = self._items.get(key)
            if item is None:
                continue

            next_bytes = used_bytes + item.byte_size
            if (
                budget.max_payload_bytes is not None
                and next_bytes > budget.max_payload_bytes
                and drained
            ):
                                                                           
                                                                              
                break

            next_cost = used_cost + item.cost
            if budget.max_cost is not None and next_cost > budget.max_cost and drained:
                break

            self._items.pop(key, None)
            drained.append(item)
            used_bytes = next_bytes
            used_cost = next_cost
            self._dequeued_total += 1
            if effective_int < int(item.base_priority):
                self._aged_total += 1

        return tuple(drained)

    def cancel(self, key: str) -> bool:
        removed = self._items.pop(key, None) is not None
        if removed:
            self._canceled_total += 1
        return removed

    def cancel_where(self, predicate: Callable[[RenderQueueItem], bool]) -> int:
        keys = [key for key, item in self._items.items() if predicate(item)]
        for key in keys:
            self._items.pop(key, None)
        self._canceled_total += len(keys)
        return len(keys)

    def cancel_scope(
        self,
        *,
        scene_id: str | None = None,
        scene_epoch_not: int | None = None,
        viewport_id: str | None = None,
        older_than_viewport_generation: int | None = None,
        kind: str | None = None,
    ) -> int:
        def matches(item: RenderQueueItem) -> bool:
            if scene_id is not None and item.scene_id != scene_id:
                return False
            if scene_epoch_not is not None and item.scene_epoch == scene_epoch_not:
                return False
            if viewport_id is not None and item.viewport_id != viewport_id:
                return False
            if kind is not None and item.kind != kind:
                return False
            if older_than_viewport_generation is not None:
                if item.viewport_generation is None:
                    return False
                return item.viewport_generation < older_than_viewport_generation
            return True

        return self.cancel_where(matches)

    def snapshot(self, *, now_ms: int) -> SchedulerSnapshot:
        self._purge_expired(now_ms=now_ms)
        by_base: dict[str, int] = {}
        by_effective: dict[str, int] = {}
        queued_bytes = 0
        queued_cost = 0
        oldest_age: int | None = None

        for item in self._items.values():
            queued_bytes += item.byte_size
            queued_cost += item.cost

            base_name = item.base_priority.name.lower()
            by_base[base_name] = by_base.get(base_name, 0) + 1

            effective = self._effective_priority(item=item, now_ms=now_ms)
            effective_name = effective.name.lower()
            by_effective[effective_name] = by_effective.get(effective_name, 0) + 1

            age = item.age_ms(now_ms)
            oldest_age = age if oldest_age is None else max(oldest_age, age)

        return SchedulerSnapshot(
            queued_items=len(self._items),
            queued_bytes=queued_bytes,
            queued_cost=queued_cost,
            by_base_priority=by_base,
            by_effective_priority=by_effective,
            oldest_item_age_ms=oldest_age,
            enqueued_total=self._enqueued_total,
            replaced_total=self._replaced_total,
            dequeued_total=self._dequeued_total,
            canceled_total=self._canceled_total,
            expired_total=self._expired_total,
            aged_total=self._aged_total,
        )

    def clear(self) -> None:
        self._canceled_total += len(self._items)
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)

    def _ranked_heap(self, *, now_ms: int) -> list[tuple[int, int, int, str]]:
        heap: list[tuple[int, int, int, str]] = []
        for item in self._items.values():
            priority = self._effective_priority(item=item, now_ms=now_ms)
                                                                                   
                                                                                      
            heapq.heappush(heap, (int(priority), item.order, item.sequence, item.key))
        return heap

    def _effective_priority(
        self,
        *,
        item: RenderQueueItem,
        now_ms: int,
    ) -> RenderPriority:
        return self.aging_policy.effective_priority(
            base_priority=item.base_priority,
            waited_ms=item.age_ms(now_ms),
        )

    def _purge_expired(self, *, now_ms: int) -> None:
        expired = [key for key, item in self._items.items() if item.is_expired(now_ms)]
        for key in expired:
            self._items.pop(key, None)
        self._expired_total += len(expired)
