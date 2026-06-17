from __future__ import annotations

from app.domain.scenes import EMPTY_TILE_REF
from app.domain.scenes import UINT32_MAX


UINT32_REF_SIZE_BYTES = 4


def encode_uint32_tile_refs(tile_refs: list[int]) -> bytes:
    encoded = bytearray()

    for tile_ref in tile_refs:
        if tile_ref < EMPTY_TILE_REF or tile_ref > UINT32_MAX:
            raise ValueError("tile_ref must fit in uint32")

        encoded.extend(tile_ref.to_bytes(UINT32_REF_SIZE_BYTES, byteorder="little", signed=False))

    return bytes(encoded)


def decode_uint32_tile_refs(data: bytes) -> list[int]:
    if len(data) % UINT32_REF_SIZE_BYTES != 0:
        raise ValueError("uint32 tile ref data has invalid length")

    return [
        int.from_bytes(
            data[index:index + UINT32_REF_SIZE_BYTES],
            byteorder="little",
            signed=False,
        )
        for index in range(0, len(data), UINT32_REF_SIZE_BYTES)
    ]


def expected_uint32_chunk_bytes(chunk_size: int) -> int:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    return chunk_size * chunk_size * UINT32_REF_SIZE_BYTES


def validate_uint32_chunk_payload(
    *,
    data: bytes,
    chunk_size: int,
) -> None:
    expected_size = expected_uint32_chunk_bytes(chunk_size)

    if len(data) != expected_size:
        raise ValueError("uint32 chunk payload has invalid size")

    decode_uint32_tile_refs(data)
