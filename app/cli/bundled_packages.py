"""Install immutable packages shipped with a frozen Gravewright Core build."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from app.config import config
from app.engine.sdk.package_manifest import KIND_TO_DIRECTORY

PACKAGE_KIND_DIRS = tuple(KIND_TO_DIRECTORY.values())


def install_bundled_packages(*, bundle_root: Path | None = None) -> list[Path]:
    """Seed missing packages without overwriting an operator's installed copy."""
    if bundle_root is None:
        if not getattr(sys, "frozen", False):
            return []
        bundle_root = Path(getattr(sys, "_MEIPASS", "")) / "bundled-packages"
    installed: list[Path] = []
    data_root = Path(config.data_dir)
    for kind in PACKAGE_KIND_DIRS:
        source_kind = bundle_root / kind
        if not source_kind.is_dir():
            continue
        for source in source_kind.iterdir():
            if not source.is_dir():
                continue
            target = data_root / "packages" / kind / source.name
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target)
            installed.append(target)
    return installed
