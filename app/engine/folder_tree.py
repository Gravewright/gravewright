from __future__ import annotations

from collections.abc import Callable
from typing import Any


def _label(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or value.get("title") or "")
    return str(getattr(value, "name", None) or getattr(value, "title", None) or "")


def build_folder_tree(
    folders_flat: list[dict],
    entries_by_folder: dict[str, list],
    *,
    entry_key: str,
    entry_label: Callable[[Any], str] = _label,
) -> list[dict]:
    """Build a safe, deterministic directory tree shared by all document panels."""
    folder_map: dict[str, dict] = {}
    for source in folders_flat:
        folder_id = str(source["id"])
        entries = list(entries_by_folder.get(source["id"], entries_by_folder.get(folder_id, [])))
        entries.sort(key=lambda value: (entry_label(value).casefold(), entry_label(value)))
        folder_map[folder_id] = {
            "id": folder_id,
            "name": source["name"],
            "color": source.get("color"),
            "parent_id": str(source["parent_id"]) if source.get("parent_id") else None,
            entry_key: entries,
            "children": [],
            "direct_count": len(entries),
            "all_count": 0,
            "depth": 0,
            "path": [],
        }

    def has_cycle(folder_id: str, parent_id: str) -> bool:
        seen = {folder_id}
        cursor: str | None = parent_id
        while cursor and cursor in folder_map:
            if cursor in seen:
                return True
            seen.add(cursor)
            cursor = folder_map[cursor].get("parent_id")
        return False

    invalid_parent_ids = {
        folder["id"]
        for folder in folder_map.values()
        if folder.get("parent_id")
        and (
            folder["parent_id"] not in folder_map
            or has_cycle(folder["id"], folder["parent_id"])
        )
    }
    roots: list[dict] = []
    for folder in folder_map.values():
        parent_id = folder.get("parent_id")
        if parent_id and folder["id"] not in invalid_parent_ids:
            folder_map[parent_id]["children"].append(folder)
        else:
            folder["parent_id"] = None
            roots.append(folder)

    sort_key = lambda folder: (str(folder["name"]).casefold(), str(folder["name"]), folder["id"])

    def annotate(folders: list[dict], *, depth: int = 0, path: tuple[str, ...] = ()) -> None:
        folders.sort(key=sort_key)
        for folder in folders:
            folder["depth"] = depth
            folder["path"] = [*path, folder["id"]]
            annotate(folder["children"], depth=depth + 1, path=(*path, folder["id"]))
            folder["all_count"] = folder["direct_count"] + sum(
                child["all_count"] for child in folder["children"]
            )

    annotate(roots)
    return roots
