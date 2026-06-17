"""Backup/export path semantics for SDK packages (Phase 7B).

Two operations with different data boundaries:

* **export/publish** — ships only the package directory; managed storage (a
  campaign's private data) is excluded by default.
* **backup** — includes both the package directory and its managed storage.

These helpers return the directories each operation should include so the CLI
(``grave package export|backup``) and any tooling agree on the boundary.
"""

from __future__ import annotations

from pathlib import Path

from app.engine.sdk import package_registry


def export_includes(kind: str, package_id: str) -> list[Path]:
    """Directories an export/publish should include (no managed storage)."""
    package_dir = package_registry.package_dir_for(kind, package_id)
    return [package_dir] if package_dir is not None else []


def backup_includes(kind: str, package_id: str) -> list[Path]:
    """Directories a package backup should include (package + storage)."""
    paths: list[Path] = []
    package_dir = package_registry.package_dir_for(kind, package_id)
    storage_dir = package_registry.storage_dir_for(kind, package_id)
    if package_dir is not None:
        paths.append(package_dir)
    if storage_dir is not None:
        paths.append(storage_dir)
    return paths
