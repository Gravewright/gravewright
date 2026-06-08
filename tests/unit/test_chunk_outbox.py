from __future__ import annotations

from app.realtime.chunk_outbox import ChunkOutbox
from app.realtime.chunk_outbox import OutboundChunkBatch


def batch(batch_id: str, size: int, *, priority: int = 1) -> OutboundChunkBatch:
    return OutboundChunkBatch(
        batch_id=batch_id,
        frame=bytes([1]) * size,
        priority=priority,
    )


def test_outbox_limits_inflight_until_ack():
    outbox = ChunkOutbox(max_batch_bytes=20, max_inflight_batches=1, max_queue_bytes=100)

    assert outbox.enqueue(batch("a", 10))
    assert outbox.enqueue(batch("b", 10))

    ready = outbox.ready_to_send()
    assert [item.batch_id for item in ready] == ["a"]
    assert outbox.stats().inflight_batches == 1

    assert outbox.ready_to_send() == ()
    assert outbox.ack("a")
    assert [item.batch_id for item in outbox.ready_to_send()] == ["b"]


def test_outbox_nack_requeues_batch():
    outbox = ChunkOutbox(max_batch_bytes=20, max_inflight_batches=1, max_queue_bytes=100)
    outbox.enqueue(batch("a", 10))

    assert [item.batch_id for item in outbox.ready_to_send()] == ["a"]
    assert outbox.nack("a")
    assert [item.batch_id for item in outbox.ready_to_send()] == ["a"]


def test_outbox_rejects_oversized_batch():
    outbox = ChunkOutbox(max_batch_bytes=10, max_inflight_batches=1, max_queue_bytes=100)

    assert not outbox.enqueue(batch("a", 11))
    assert outbox.stats().rejected_batches == 1
    assert outbox.ready_to_send() == ()


def test_outbox_drops_old_queued_batches_to_fit_queue():
    outbox = ChunkOutbox(max_batch_bytes=20, max_inflight_batches=1, max_queue_bytes=25)

    assert outbox.enqueue(batch("a", 10))
    assert outbox.enqueue(batch("b", 10))
    assert outbox.enqueue(batch("c", 10))

    assert outbox.stats().dropped_batches == 1
    assert [item.batch_id for item in outbox.ready_to_send()] == ["b"]


def test_outbox_sends_lower_priority_number_first():
    outbox = ChunkOutbox(max_batch_bytes=20, max_inflight_batches=2, max_queue_bytes=100)

    assert outbox.enqueue(batch("low", 10, priority=3))
    assert outbox.enqueue(batch("high", 10, priority=1))

    assert [item.batch_id for item in outbox.ready_to_send()] == ["high", "low"]
