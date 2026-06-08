from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from typing import Any


CHUNK_BATCH_MAGIC = b"GWCB"
CHUNK_BATCH_VERSION = 1
CHUNK_BATCH_FRAME_TYPE = 1
CHUNK_BATCH_HEADER = struct.Struct("<4sBBHI")
MAX_HEADER_BYTES = 1024 * 1024


@dataclass(frozen=True)
class ChunkBatchItem:
    layer_id: str
    cx: int
    cy: int
    version: int
    hash: str
    encoding: str
    data: bytes

    @property
    def byte_size(self) -> int:
        return len(self.data)


@dataclass(frozen=True)
class DecodedChunkBatchItem:
    layer_id: str
    cx: int
    cy: int
    version: int
    hash: str
    encoding: str
    byte_size: int
    data: bytes


@dataclass(frozen=True)
class ChunkBatchFrame:
    batch_id: str
    scene_id: str
    scene_epoch: int
    viewport_id: str
    viewport_generation: int
    chunks: tuple[ChunkBatchItem, ...]


@dataclass(frozen=True)
class DecodedChunkBatchFrame:
    batch_id: str
    scene_id: str
    scene_epoch: int
    viewport_id: str
    viewport_generation: int
    chunks: tuple[DecodedChunkBatchItem, ...]


def encode_chunk_batch_frame(frame: ChunkBatchFrame) -> bytes:
    _validate_common_header(
        batch_id=frame.batch_id,
        scene_id=frame.scene_id,
        scene_epoch=frame.scene_epoch,
        viewport_id=frame.viewport_id,
        viewport_generation=frame.viewport_generation,
    )

    offset = 0
    payload_parts = []
    chunk_headers = []

    for chunk in frame.chunks:
        _validate_chunk_fields(
            layer_id=chunk.layer_id,
            cx=chunk.cx,
            cy=chunk.cy,
            version=chunk.version,
            hash=chunk.hash,
            encoding=chunk.encoding,
            byte_size=chunk.byte_size,
        )
        payload_parts.append(chunk.data)
        chunk_headers.append(
            {
                "layer_id": chunk.layer_id,
                "cx": chunk.cx,
                "cy": chunk.cy,
                "version": chunk.version,
                "hash": chunk.hash,
                "encoding": chunk.encoding,
                "byte_size": chunk.byte_size,
                "offset": offset,
                "length": chunk.byte_size,
            }
        )
        offset += chunk.byte_size

    header = {
        "batch_id": frame.batch_id,
        "scene_id": frame.scene_id,
        "scene_epoch": frame.scene_epoch,
        "viewport_id": frame.viewport_id,
        "viewport_generation": frame.viewport_generation,
        "chunks": chunk_headers,
    }
    header_bytes = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")

    if len(header_bytes) > MAX_HEADER_BYTES:
        raise ValueError("chunk batch header is too large")

    prefix = CHUNK_BATCH_HEADER.pack(
        CHUNK_BATCH_MAGIC,
        CHUNK_BATCH_VERSION,
        CHUNK_BATCH_FRAME_TYPE,
        0,
        len(header_bytes),
    )

    return prefix + header_bytes + b"".join(payload_parts)


def decode_chunk_batch_frame(data: bytes) -> DecodedChunkBatchFrame:
    if len(data) < CHUNK_BATCH_HEADER.size:
        raise ValueError("chunk batch frame is too short")

    magic, version, frame_type, _flags, header_len = CHUNK_BATCH_HEADER.unpack_from(data)

    if magic != CHUNK_BATCH_MAGIC:
        raise ValueError("chunk batch frame has invalid magic")

    if version != CHUNK_BATCH_VERSION:
        raise ValueError("chunk batch frame has unsupported version")

    if frame_type != CHUNK_BATCH_FRAME_TYPE:
        raise ValueError("chunk batch frame has unsupported type")

    if header_len > MAX_HEADER_BYTES:
        raise ValueError("chunk batch header is too large")

    header_start = CHUNK_BATCH_HEADER.size
    header_end = header_start + header_len

    if header_end > len(data):
        raise ValueError("chunk batch frame has truncated header")

    try:
        header = json.loads(data[header_start:header_end].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("chunk batch header is invalid") from exc

    if not isinstance(header, dict):
        raise ValueError("chunk batch header must be an object")

    batch_id = _required_str(header, "batch_id")
    scene_id = _required_str(header, "scene_id")
    scene_epoch = _required_positive_int(header, "scene_epoch")
    viewport_id = _required_str(header, "viewport_id")
    viewport_generation = _required_non_negative_int(header, "viewport_generation")
    chunks_header = header.get("chunks")

    if not isinstance(chunks_header, list):
        raise ValueError("chunk batch chunks must be a list")

    payload = data[header_end:]
    decoded_chunks = []

    for chunk_header in chunks_header:
        if not isinstance(chunk_header, dict):
            raise ValueError("chunk batch chunk metadata must be an object")

        layer_id = _required_str(chunk_header, "layer_id")
        cx = _required_non_negative_int(chunk_header, "cx")
        cy = _required_non_negative_int(chunk_header, "cy")
        version = _required_positive_int(chunk_header, "version")
        chunk_hash = _required_str(chunk_header, "hash")
        encoding = _required_str(chunk_header, "encoding")
        byte_size = _required_non_negative_int(chunk_header, "byte_size")
        offset = _required_non_negative_int(chunk_header, "offset")
        length = _required_non_negative_int(chunk_header, "length")

        if byte_size != length:
            raise ValueError("chunk batch chunk byte_size must match length")

        end = offset + length
        if end > len(payload):
            raise ValueError("chunk batch payload is truncated")

        chunk_data = payload[offset:end]
        _validate_chunk_fields(
            layer_id=layer_id,
            cx=cx,
            cy=cy,
            version=version,
            hash=chunk_hash,
            encoding=encoding,
            byte_size=byte_size,
        )
        decoded_chunks.append(
            DecodedChunkBatchItem(
                layer_id=layer_id,
                cx=cx,
                cy=cy,
                version=version,
                hash=chunk_hash,
                encoding=encoding,
                byte_size=byte_size,
                data=chunk_data,
            )
        )

    return DecodedChunkBatchFrame(
        batch_id=batch_id,
        scene_id=scene_id,
        scene_epoch=scene_epoch,
        viewport_id=viewport_id,
        viewport_generation=viewport_generation,
        chunks=tuple(decoded_chunks),
    )


def _validate_common_header(
    *,
    batch_id: str,
    scene_id: str,
    scene_epoch: int,
    viewport_id: str,
    viewport_generation: int,
) -> None:
    if not batch_id:
        raise ValueError("batch_id is required")
    if not scene_id:
        raise ValueError("scene_id is required")
    if scene_epoch < 1:
        raise ValueError("scene_epoch must be positive")
    if not viewport_id:
        raise ValueError("viewport_id is required")
    if viewport_generation < 0:
        raise ValueError("viewport_generation must be zero or positive")


def _validate_chunk_fields(
    *,
    layer_id: str,
    cx: int,
    cy: int,
    version: int,
    hash: str,
    encoding: str,
    byte_size: int,
) -> None:
    if not layer_id:
        raise ValueError("layer_id is required")
    if cx < 0 or cy < 0:
        raise ValueError("chunk coordinates must be zero or positive")
    if version < 1:
        raise ValueError("chunk version must be positive")
    if not hash:
        raise ValueError("chunk hash is required")
    if not encoding:
        raise ValueError("chunk encoding is required")
    if byte_size < 0:
        raise ValueError("chunk byte_size must be zero or positive")


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"chunk batch {key} is required")
    return value


def _required_non_negative_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"chunk batch {key} must be zero or positive")
    return value


def _required_positive_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or value < 1:
        raise ValueError(f"chunk batch {key} must be positive")
    return value
