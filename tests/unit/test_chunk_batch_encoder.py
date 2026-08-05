from __future__ import annotations

import struct

import pytest

from app.realtime.chunk_batch_encoder import CHUNK_BATCH_HEADER
from app.realtime.chunk_batch_encoder import CHUNK_BATCH_MAGIC
from app.realtime.chunk_batch_encoder import ChunkBatchFrame
from app.realtime.chunk_batch_encoder import ChunkBatchItem
from app.realtime.chunk_batch_encoder import decode_chunk_batch_frame
from app.realtime.chunk_batch_encoder import encode_chunk_batch_frame


def test_chunk_batch_binary_frame_roundtrip():
    frame = ChunkBatchFrame(
        batch_id="batch-1",
        scene_id="scene-1",
        scene_epoch=7,
        viewport_id="main",
        viewport_generation=42,
        chunks=(
            ChunkBatchItem(
                layer_id="ground",
                cx=1,
                cy=2,
                version=3,
                hash="hash-a",
                encoding="uint32_tile_refs_v1",
                data=b"abcd",
            ),
            ChunkBatchItem(
                layer_id="ground",
                cx=2,
                cy=2,
                version=4,
                hash="hash-b",
                encoding="uint32_tile_refs_v1",
                data=b"efghij",
            ),
        ),
    )

    encoded = encode_chunk_batch_frame(frame)
    decoded = decode_chunk_batch_frame(encoded)

    assert encoded[:4] == CHUNK_BATCH_MAGIC
    assert decoded.batch_id == "batch-1"
    assert decoded.scene_id == "scene-1"
    assert decoded.scene_epoch == 7
    assert decoded.viewport_id == "main"
    assert decoded.viewport_generation == 42
    assert [(chunk.cx, chunk.cy, chunk.version, chunk.data) for chunk in decoded.chunks] == [
        (1, 2, 3, b"abcd"),
        (2, 2, 4, b"efghij"),
    ]


def test_chunk_batch_rejects_invalid_magic():
    frame = ChunkBatchFrame(
        batch_id="batch-1",
        scene_id="scene-1",
        scene_epoch=1,
        viewport_id="main",
        viewport_generation=0,
        chunks=(),
    )
    encoded = bytearray(encode_chunk_batch_frame(frame))
    encoded[:4] = b"NOPE"

    with pytest.raises(ValueError, match="invalid magic"):
        decode_chunk_batch_frame(bytes(encoded))


def test_chunk_batch_rejects_truncated_header():
    encoded = CHUNK_BATCH_HEADER.pack(
        CHUNK_BATCH_MAGIC,
        1,
        1,
        0,
        10,
    ) + b"{}"

    with pytest.raises(ValueError, match="truncated header"):
        decode_chunk_batch_frame(encoded)


def test_chunk_batch_rejects_truncated_payload():
    frame = ChunkBatchFrame(
        batch_id="batch-1",
        scene_id="scene-1",
        scene_epoch=1,
        viewport_id="main",
        viewport_generation=0,
        chunks=(
            ChunkBatchItem(
                layer_id="ground",
                cx=0,
                cy=0,
                version=1,
                hash="hash",
                encoding="uint32_tile_refs_v1",
                data=b"abcd",
            ),
        ),
    )
    encoded = encode_chunk_batch_frame(frame)

    with pytest.raises(ValueError, match="payload is truncated"):
        decode_chunk_batch_frame(encoded[:-1])


def test_chunk_batch_rejects_unsupported_version():
    encoded = bytearray(
        CHUNK_BATCH_HEADER.pack(
            CHUNK_BATCH_MAGIC,
            99,
            1,
            0,
            2,
        ) + b"{}"
    )

    with pytest.raises(ValueError, match="unsupported version"):
        decode_chunk_batch_frame(bytes(encoded))


def test_chunk_batch_rejects_invalid_encode_values():
    with pytest.raises(ValueError, match="scene_epoch"):
        encode_chunk_batch_frame(
            ChunkBatchFrame(
                batch_id="batch-1",
                scene_id="scene-1",
                scene_epoch=0,
                viewport_id="main",
                viewport_generation=0,
                chunks=(),
            )
        )


def test_chunk_batch_header_layout_is_stable():
    assert CHUNK_BATCH_HEADER.size == 12
    assert struct.calcsize("<4sBBHI") == CHUNK_BATCH_HEADER.size
