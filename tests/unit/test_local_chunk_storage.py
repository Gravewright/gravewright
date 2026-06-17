from __future__ import annotations

import hashlib

import pytest

from app.infrastructure.storage.local_chunk_storage import LocalChunkStorage


def test_local_chunk_storage_write_and_read(tmp_path):
    storage = LocalChunkStorage(root=tmp_path / "scenes")
    data = b"\x00\x00\x00\x01"

    digest = storage.write_chunk(
        scene_id="scene_1",
        layer_id="layer_1",
        cx=0,
        cy=0,
        data=data,
    )

    assert digest == hashlib.sha256(data).hexdigest()
    assert storage.read_chunk(
        scene_id="scene_1",
        layer_id="layer_1",
        cx=0,
        cy=0,
    ) == data


def test_local_chunk_storage_reads_multiple_chunks(tmp_path):
    storage = LocalChunkStorage(root=tmp_path / "scenes")
    storage.write_chunk(
        scene_id="scene_1",
        layer_id="layer_1",
        cx=0,
        cy=0,
        data=b"zero",
    )
    storage.write_chunk(
        scene_id="scene_1",
        layer_id="layer_1",
        cx=1,
        cy=0,
        data=b"one",
    )

    assert storage.read_chunks(
        scene_id="scene_1",
        layer_id="layer_1",
        coords=((0, 0), (1, 0), (2, 0)),
    ) == {
        (0, 0): b"zero",
        (1, 0): b"one",
    }


def test_local_chunk_storage_overwrites_atomically(tmp_path):
    storage = LocalChunkStorage(root=tmp_path / "scenes")

    storage.write_chunk(
        scene_id="scene_1",
        layer_id="layer_1",
        cx=0,
        cy=0,
        data=b"first",
    )
    digest = storage.write_chunk(
        scene_id="scene_1",
        layer_id="layer_1",
        cx=0,
        cy=0,
        data=b"second",
    )

    assert digest == hashlib.sha256(b"second").hexdigest()
    assert storage.read_chunk(
        scene_id="scene_1",
        layer_id="layer_1",
        cx=0,
        cy=0,
    ) == b"second"


def test_local_chunk_storage_delete_is_idempotent(tmp_path):
    storage = LocalChunkStorage(root=tmp_path / "scenes")

    storage.write_chunk(
        scene_id="scene_1",
        layer_id="layer_1",
        cx=0,
        cy=0,
        data=b"data",
    )
    storage.delete_chunk(scene_id="scene_1", layer_id="layer_1", cx=0, cy=0)
    storage.delete_chunk(scene_id="scene_1", layer_id="layer_1", cx=0, cy=0)

    assert storage.read_chunk(scene_id="scene_1", layer_id="layer_1", cx=0, cy=0) is None


def test_local_chunk_storage_rejects_path_traversal(tmp_path):
    storage = LocalChunkStorage(root=tmp_path / "scenes")

    with pytest.raises(ValueError, match="scene_id"):
        storage.write_chunk(
            scene_id="../outside",
            layer_id="layer_1",
            cx=0,
            cy=0,
            data=b"data",
        )

    assert not (tmp_path / "outside").exists()


def test_local_chunk_storage_rejects_negative_coordinates(tmp_path):
    storage = LocalChunkStorage(root=tmp_path / "scenes")

    with pytest.raises(ValueError, match="cx"):
        storage.read_chunk(
            scene_id="scene_1",
            layer_id="layer_1",
            cx=-1,
            cy=0,
        )
