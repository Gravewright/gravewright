from __future__ import annotations

from typing import Protocol


class ChunkStorageContract(Protocol):
    def read_chunk(
        self,
        *,
        scene_id: str,
        layer_id: str,
        cx: int,
        cy: int,
    ) -> bytes | None: ...

    def read_chunks(
        self,
        *,
        scene_id: str,
        layer_id: str,
        coords: tuple[tuple[int, int], ...],
    ) -> dict[tuple[int, int], bytes]: ...

    def write_chunk(
        self,
        *,
        scene_id: str,
        layer_id: str,
        cx: int,
        cy: int,
        data: bytes,
    ) -> str: ...

    def delete_chunk(
        self,
        *,
        scene_id: str,
        layer_id: str,
        cx: int,
        cy: int,
    ) -> None: ...
