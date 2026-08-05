from __future__ import annotations


def build_journal_folder_tree(
    folders_flat: list[dict],
    journals_by_folder: dict[str, list],
) -> list[dict]:
    folder_map: dict[str, dict] = {}
    for folder in folders_flat:
        folder_map[folder["id"]] = {
            "id": folder["id"],
            "name": folder["name"],
            "color": folder.get("color"),
            "parent_id": folder.get("parent_id"),
            "journals": journals_by_folder.get(folder["id"], []),
            "children": [],
            "all_count": 0,
        }

    roots: list[dict] = []
    for folder in folder_map.values():
        parent_id = folder["parent_id"]
        if parent_id and parent_id in folder_map:
            folder_map[parent_id]["children"].append(folder)
        else:
            roots.append(folder)

    def _annotate(folders: list[dict]) -> None:
        for folder in folders:
            _annotate(folder["children"])
            folder["all_count"] = len(folder["journals"]) + sum(
                child["all_count"] for child in folder["children"]
            )

    _annotate(roots)
    return roots

