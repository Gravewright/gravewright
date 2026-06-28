from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path

from app.helpers.env import PROJECT_ROOT

SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
SAFE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class LocalAssetStorage:
    """Stores asset-library images under ``storage/library-assets/<campaign>/<asset>``."""

    def __init__(self, *, root: Path | None = None) -> None:
        self.root = root or PROJECT_ROOT / "storage" / "library-assets"

    def write_image(
        self,
        *,
        campaign_id: str,
        asset_id: str,
        filename: str,
        data: bytes,
    ) -> str:
        self._validate_id(campaign_id, "campaign_id")
        self._validate_id(asset_id, "asset_id")
        extension = self._safe_extension(filename)
        path = self.root / campaign_id / f"{asset_id}{extension}"
        self._atomic_write(path, data)
        return self._storage_path(path)

    def delete(self, storage_path: str) -> None:
        path = PROJECT_ROOT / storage_path
        self._assert_inside_root(path)
        if path.exists():
            path.unlink()

    def delete_campaign(self, *, campaign_id: str) -> None:
        self._validate_id(campaign_id, "campaign_id")
        path = self.root / campaign_id
        self._assert_inside_root(path)
        if path.exists():
            shutil.rmtree(path)

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
