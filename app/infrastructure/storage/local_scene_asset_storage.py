from __future__ import annotations

import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path

from PIL import Image

from app.helpers.env import PROJECT_ROOT


SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
SAFE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


class LocalSceneAssetStorage:
    def __init__(
        self,
        *,
        root: Path | None = None,
    ) -> None:
        self.root = root or PROJECT_ROOT / "storage" / "scenes"

    def write_original(
        self,
        *,
        scene_id: str,
        filename: str,
        data: bytes,
    ) -> str:
        self._validate_id(scene_id, "scene_id")
        extension = self._safe_extension(filename)
        path = self.root / scene_id / "assets" / "original" / f"original{extension}"
        self._atomic_write(path, data)
        return self._storage_path(path)

    def read_asset(self, storage_path: str) -> bytes:
        path = PROJECT_ROOT / storage_path
        self._assert_inside_root(path)
        return path.resolve().read_bytes()

    def delete_layer_tiles(self, *, scene_id: str, layer_id: str) -> None:
        import shutil
        self._validate_id(scene_id, "scene_id")
        self._validate_id(layer_id, "layer_id")
        path = self.root / scene_id / "assets" / "tiles" / layer_id
        self._assert_inside_root(path)
        if path.exists():
            shutil.rmtree(path)

    def delete_scene(self, *, scene_id: str) -> None:
        """Remove the entire on-disk tree for a scene (originals, tiles and
        chunks all live under ``<root>/<scene_id>/``)."""
        import shutil
        self._validate_id(scene_id, "scene_id")
        path = self.root / scene_id
        self._assert_inside_root(path)
        if path.exists():
            shutil.rmtree(path)

    def write_tile_png(
        self,
        *,
        scene_id: str,
        layer_id: str,
        tx: int,
        ty: int,
        image: Image.Image,
    ) -> tuple[str, bytes]:
        self._validate_id(scene_id, "scene_id")
        self._validate_id(layer_id, "layer_id")
        self._validate_coord(tx, "tx")
        self._validate_coord(ty, "ty")

        path = self.root / scene_id / "assets" / "tiles" / layer_id / f"{tx}_{ty}.png"

        with tempfile.SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b") as buffer:
            image.save(buffer, format="PNG", optimize=True)
            buffer.seek(0)
            data = buffer.read()

        self._atomic_write(path, data)

        return self._storage_path(path), data

    def write_tile_bytes(
        self,
        *,
        scene_id: str,
        layer_id: str,
        tx: int,
        ty: int,
        data: bytes,
    ) -> str:
        """Write pre-encoded PNG bytes for a tile (used by staged retile)."""
        self._validate_id(scene_id, "scene_id")
        self._validate_id(layer_id, "layer_id")
        self._validate_coord(tx, "tx")
        self._validate_coord(ty, "ty")

        path = self.root / scene_id / "assets" / "tiles" / layer_id / f"{tx}_{ty}.png"
        self._atomic_write(path, data)
        return self._storage_path(path)

    def create_layer_tiles_staging(self, *, scene_id: str, layer_id: str) -> Path:
        """Create a private staging directory for a future layer-tile swap."""
        self._validate_id(scene_id, "scene_id")
        self._validate_id(layer_id, "layer_id")
        path = (
            self.root
            / scene_id
            / "assets"
            / "tiles"
            / ".staging"
            / f"{layer_id}-{uuid.uuid4().hex}"
        )
        self._assert_inside_root(path)
        path.mkdir(parents=True, exist_ok=False)
        return path

    def final_tile_storage_path(self, *, scene_id: str, layer_id: str, tx: int, ty: int) -> str:
        self._validate_id(scene_id, "scene_id")
        self._validate_id(layer_id, "layer_id")
        self._validate_coord(tx, "tx")
        self._validate_coord(ty, "ty")
        path = self.root / scene_id / "assets" / "tiles" / layer_id / f"{tx}_{ty}.png"
        self._assert_inside_root(path)
        return self._storage_path(path)

    def write_staged_tile_bytes(self, *, staging_dir: Path, tx: int, ty: int, data: bytes) -> None:
        self._assert_inside_root(staging_dir)
        self._validate_coord(tx, "tx")
        self._validate_coord(ty, "ty")
        path = staging_dir / f"{tx}_{ty}.png"
        self._assert_inside_root(path)
        self._atomic_write(path, data)

    def promote_layer_tiles_staging(
        self,
        *,
        scene_id: str,
        layer_id: str,
        staging_dir: Path,
    ) -> Path | None:
        """Replace the final layer tile directory with a staged one.

        Returns a backup path for the previous final directory. The caller must
        delete that backup after associated database metadata commits, or restore
        it if the commit fails.
        """
        self._validate_id(scene_id, "scene_id")
        self._validate_id(layer_id, "layer_id")
        self._assert_inside_root(staging_dir)
        if not staging_dir.exists() or not staging_dir.is_dir():
            raise FileNotFoundError("tile staging directory is missing")

        final = self.root / scene_id / "assets" / "tiles" / layer_id
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

    def restore_layer_tiles_backup(
        self,
        *,
        scene_id: str,
        layer_id: str,
        backup_dir: Path | None,
    ) -> None:
        self._validate_id(scene_id, "scene_id")
        self._validate_id(layer_id, "layer_id")
        final = self.root / scene_id / "assets" / "tiles" / layer_id
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

    def _atomic_write(self, path: Path, data: bytes) -> None:
        self._assert_inside_root(path)
        path.parent.mkdir(parents=True, exist_ok=True)
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

    def _assert_inside_root(self, path: Path) -> None:
        resolved_root = self.root.resolve()
        resolved_path = path.resolve()

        if resolved_root not in resolved_path.parents:
            raise ValueError("asset path escapes storage root")

    def _safe_extension(self, filename: str) -> str:
        extension = Path(filename).suffix.lower()

        if extension not in SAFE_EXTENSIONS:
            raise ValueError("filename extension is invalid")

        return extension

    def _storage_path(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(PROJECT_ROOT))
        except ValueError:
            return str(path.resolve())

    def _validate_id(self, value: str, field_name: str) -> None:
        if not value or not SAFE_ID_RE.fullmatch(value):
            raise ValueError(f"{field_name} is invalid")

    def _validate_coord(self, value: int, field_name: str) -> None:
        if value < 0:
            raise ValueError(f"{field_name} must be zero or positive")
