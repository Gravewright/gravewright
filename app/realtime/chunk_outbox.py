from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass


DEFAULT_MAX_BATCH_BYTES = 64 * 1024
DEFAULT_MAX_INFLIGHT_BATCHES = 2
DEFAULT_MAX_QUEUE_BYTES = 512 * 1024


@dataclass(frozen=True)
class OutboundChunkBatch:
    batch_id: str
    frame: bytes
    priority: int = 1

    @property
    def byte_size(self) -> int:
        return len(self.frame)


@dataclass(frozen=True)
class ReadyChunkBatch:
    batch_id: str
    frame: bytes


@dataclass(frozen=True)
class ChunkOutboxStats:
    queued_batches: int
    queued_bytes: int
    inflight_batches: int
    dropped_batches: int
    rejected_batches: int


class ChunkOutbox:
    def __init__(
        self,
        *,
        max_batch_bytes: int = DEFAULT_MAX_BATCH_BYTES,
        max_inflight_batches: int = DEFAULT_MAX_INFLIGHT_BATCHES,
        max_queue_bytes: int = DEFAULT_MAX_QUEUE_BYTES,
    ) -> None:
        if max_batch_bytes <= 0:
            raise ValueError("max_batch_bytes must be positive")
        if max_inflight_batches <= 0:
            raise ValueError("max_inflight_batches must be positive")
        if max_queue_bytes <= 0:
            raise ValueError("max_queue_bytes must be positive")

        self.max_batch_bytes = max_batch_bytes
        self.max_inflight_batches = max_inflight_batches
        self.max_queue_bytes = max_queue_bytes
        self._queued: OrderedDict[str, OutboundChunkBatch] = OrderedDict()
        self._inflight: dict[str, OutboundChunkBatch] = {}
        self._queued_bytes = 0
        self._dropped_batches = 0
        self._rejected_batches = 0

    def enqueue(self, batch: OutboundChunkBatch) -> bool:
        if not batch.batch_id:
            raise ValueError("batch_id is required")

        if batch.byte_size > self.max_batch_bytes:
            self._rejected_batches += 1
            return False

        existing = self._queued.pop(batch.batch_id, None)
        if existing is not None:
            self._queued_bytes -= existing.byte_size

        while self._queued and self._queued_bytes + batch.byte_size > self.max_queue_bytes:
            _batch_id, dropped = self._queued.popitem(last=False)
            self._queued_bytes -= dropped.byte_size
            self._dropped_batches += 1

        if self._queued_bytes + batch.byte_size > self.max_queue_bytes:
            self._rejected_batches += 1
            return False

        self._queued[batch.batch_id] = batch
        self._queued_bytes += batch.byte_size
        self._sort_queue()
        return True

    def ready_to_send(self) -> tuple[ReadyChunkBatch, ...]:
        ready: list[ReadyChunkBatch] = []

        while self._queued and len(self._inflight) < self.max_inflight_batches:
            batch_id, batch = self._queued.popitem(last=False)
            self._queued_bytes -= batch.byte_size
            self._inflight[batch_id] = batch
            ready.append(ReadyChunkBatch(batch_id=batch_id, frame=batch.frame))

        return tuple(ready)

    def ack(self, batch_id: str) -> bool:
        return self._inflight.pop(batch_id, None) is not None

    def nack(self, batch_id: str) -> bool:
        batch = self._inflight.pop(batch_id, None)
        if batch is None:
            return False
        return self.enqueue(batch)

    def stats(self) -> ChunkOutboxStats:
        return ChunkOutboxStats(
            queued_batches=len(self._queued),
            queued_bytes=self._queued_bytes,
            inflight_batches=len(self._inflight),
            dropped_batches=self._dropped_batches,
            rejected_batches=self._rejected_batches,
        )

    def _sort_queue(self) -> None:
        sorted_items = sorted(
            self._queued.items(),
            key=lambda item: item[1].priority,
        )
        self._queued = OrderedDict(sorted_items)
