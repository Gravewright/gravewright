from __future__ import annotations

import pytest

from app.domain.scenes import UINT32_MAX
from app.engine.scenes.chunk_codec import decode_uint32_tile_refs
from app.engine.scenes.chunk_codec import encode_uint32_tile_refs
from app.engine.scenes.chunk_codec import expected_uint32_chunk_bytes
from app.engine.scenes.chunk_codec import validate_uint32_chunk_payload


def test_encode_and_decode_uint32_tile_refs():
    data = encode_uint32_tile_refs([0, 1, 2, UINT32_MAX])

    assert decode_uint32_tile_refs(data) == [0, 1, 2, UINT32_MAX]


def test_encode_rejects_out_of_range_refs():
    with pytest.raises(ValueError, match="uint32"):
        encode_uint32_tile_refs([-1])

    with pytest.raises(ValueError, match="uint32"):
        encode_uint32_tile_refs([UINT32_MAX + 1])


def test_decode_rejects_invalid_length():
    with pytest.raises(ValueError, match="invalid length"):
        decode_uint32_tile_refs(b"\x00")


def test_validate_uint32_chunk_payload_checks_expected_size():
    data = encode_uint32_tile_refs([1, 2, 3, 4])

    validate_uint32_chunk_payload(data=data, chunk_size=2)
    assert expected_uint32_chunk_bytes(2) == 16

    with pytest.raises(ValueError, match="invalid size"):
        validate_uint32_chunk_payload(data=data, chunk_size=3)
