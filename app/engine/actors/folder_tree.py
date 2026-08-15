from __future__ import annotations

from app.engine.folder_tree import build_folder_tree


def build_actor_folder_tree(
    folders_flat: list[dict],
    actors_by_folder: dict[str, list],
) -> list[dict]:
    return build_folder_tree(folders_flat, actors_by_folder, entry_key="actors")
