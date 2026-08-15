from __future__ import annotations

from app.engine.folder_tree import build_folder_tree


def build_item_folder_tree(
    folders_flat: list[dict],
    items_by_folder: dict[str, list],
) -> list[dict]:
    return build_folder_tree(folders_flat, items_by_folder, entry_key="entries")
