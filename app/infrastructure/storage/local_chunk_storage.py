from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path

from app.helpers.env import PROJECT_ROOT


SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class LocalChunkStorage:
    def __init__(
        self,
        *,
        root: Path | None = None,
    ) -> None:
        self.root = root or PROJECT_ROOT / "storage" / "scenes"

    def read_chunk(
        self,
        *,
        scene_id: str,
        layer_id: str,
        cx: int,
        cy: int,
    ) -> bytes | None:
        path = self._chunk_path(
            scene_id=scene_id,
            layer_id=layer_id,
            cx=cx,
            cy=cy,
        )

        if not path.exists():
            return None

        return path.read_bytes()

    def read_chunks(
        self,
        *,
        scene_id: str,
        layer_id: str,
        coords: tuple[tuple[int, int], ...],
    ) -> dict[tuple[int, int], bytes]:
        data_by_coord: dict[tuple[int, int], bytes] = {}
        for cx, cy in coords:
            data = self.read_chunk(
                scene_id=scene_id,
                layer_id=layer_id,
                cx=cx,
                cy=cy,
            )
            if data is not None:
                data_by_coord[(cx, cy)] = data
        return data_by_coord

    def write_chunk(
        self,
        *,
        scene_id: str,
        layer_id: str,
        cx: int,
        cy: int,
        data: bytes,
    ) -> str:
        path = self._chunk_path(
            scene_id=scene_id,
            layer_id=layer_id,
            cx=cx,
            cy=cy,
        )
        path.parent.mkdir(parents=True, exist_ok=True)

        digest = hashlib.sha256(data).hexdigest()
        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=path.parent,
                prefix=f".{path.name}.",
                delete=False,
            ) as temp_file:
                temp_file.write(data)
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_path = Path(temp_file.name)

            os.replace(temp_path, path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

        return digest

    def create_layer_chunks_staging(self, *, scene_id: str, layer_id: str) -> Path:
        self._validate_id(scene_id, "scene_id")
        self._validate_id(layer_id, "layer_id")
        path = self.root / scene_id / "chunks" / ".staging" / f"{layer_id}-{uuid.uuid4().hex}"
        self._assert_inside_root(path)
        path.mkdir(parents=True, exist_ok=False)
        return path

    def write_staged_chunk(self, *, staging_dir: Path, cx: int, cy: int, data: bytes) -> str:
        self._assert_inside_root(staging_dir)
        self._validate_coord(cx, "cx")
        self._validate_coord(cy, "cy")
        path = staging_dir / f"{cx}_{cy}.bin"
        self._assert_inside_root(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(data).hexdigest()
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=path.parent,
                prefix=f".{path.name}.",
                delete=False,
            ) as temp_file:
                temp_file.write(data)
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_path = Path(temp_file.name)
            os.replace(temp_path, path)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
        return digest

    def promote_layer_chunks_staging(
        self,
        *,
        scene_id: str,
        layer_id: str,
        staging_dir: Path,
    ) -> Path | None:
        self._validate_id(scene_id, "scene_id")
        self._validate_id(layer_id, "layer_id")
        self._assert_inside_root(staging_dir)
        if not staging_dir.exists() or not staging_dir.is_dir():
            raise FileNotFoundError("chunk staging directory is missing")

        final = self.root / scene_id / "chunks" / layer_id
        backup = final.parent / f".{layer_id}.backup.{uuid.uuid4().hex}"
        self._assert_inside_root(final)
        self._assert_inside_root(backup)
        final.parent.mkdir(parents=True, exist_ok=True)

        backup_path: Path | None = None
        try:
            if final.exists():
                os.replace(final, backup)
                backup_path = backup
            os.replace(staging_dir, final)
            return backup_path
        except Exception:
            if final.exists() and backup_path is not None:
                shutil.rmtree(final, ignore_errors=True)
            if backup_path is not None and backup_path.exists() and not final.exists():
                os.replace(backup_path, final)
            raise

    def restore_layer_chunks_backup(
        self,
        *,
        scene_id: str,
        layer_id: str,
        backup_dir: Path | None,
    ) -> None:
        self._validate_id(scene_id, "scene_id")
        self._validate_id(layer_id, "layer_id")
        final = self.root / scene_id / "chunks" / layer_id
        self._assert_inside_root(final)
        if final.exists():
            shutil.rmtree(final)
        if backup_dir is not None and backup_dir.exists():
            self._assert_inside_root(backup_dir)
            os.replace(backup_dir, final)

    def discard_path(self, path: Path | None) -> None:
        if path is None:
            return
        self._assert_inside_root(path)
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

    def _assert_inside_root(self, path: Path) -> None:
        resolved_root = self.root.resolve()
        resolved_path = path.resolve()
        if resolved_root not in resolved_path.parents:
            raise ValueError("chunk path escapes storage root")

    def delete_layer_chunks(self, *, scene_id: str, layer_id: str) -> None:
        import shutil
        self._validate_id(scene_id, "scene_id")
        self._validate_id(layer_id, "layer_id")
        path = self.root / scene_id / "chunks" / layer_id
        resolved_root = self.root.resolve()
        resolved_path = path.resolve()
        if resolved_root not in resolved_path.parents:
            raise ValueError("chunk path escapes storage root")
        if path.exists():
            shutil.rmtree(path)

    def delete_chunk(
        self,
        *,
        scene_id: str,
        layer_id: str,
        cx: int,
        cy: int,
    ) -> None:
        path = self._chunk_path(
            scene_id=scene_id,
            layer_id=layer_id,
            cx=cx,
            cy=cy,
        )

        try:
            path.unlink()
        except FileNotFoundError:
            return

    def _chunk_path(
        self,
        *,
        scene_id: str,
        layer_id: str,
        cx: int,
        cy: int,
    ) -> Path:
        self._validate_id(scene_id, "scene_id")
        self._validate_id(layer_id, "layer_id")
        self._validate_coord(cx, "cx")
        self._validate_coord(cy, "cy")

        path = self.root / scene_id / "chunks" / layer_id / f"{cx}_{cy}.bin"
        resolved_root = self.root.resolve()
        resolved_path = path.resolve()

        if resolved_root not in resolved_path.parents:
            raise ValueError("chunk path escapes storage root")

        return path

    def _validate_id(self, value: str, field_name: str) -> None:
        if not value or not SAFE_ID_RE.fullmatch(value):
            raise ValueError(f"{field_name} is invalid")

    def _validate_coord(self, value: int, field_name: str) -> None:
        if value < 0:
            raise ValueError(f"{field_name} must be zero or positive")
