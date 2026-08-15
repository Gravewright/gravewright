from app.engine.folder_tree import build_folder_tree


def test_folder_tree_sorts_and_annotates_nested_entries() -> None:
    folders = [
        {"id": "b", "name": "Zombies", "parent_id": None},
        {"id": "c", "name": "Archive", "parent_id": "a"},
        {"id": "a", "name": "Actors", "parent_id": None},
    ]
    entries = {
        "a": [{"name": "Zed"}, {"name": "alice"}],
        "c": [{"name": "Memo"}],
    }

    tree = build_folder_tree(folders, entries, entry_key="actors")

    assert [folder["name"] for folder in tree] == ["Actors", "Zombies"]
    assert [entry["name"] for entry in tree[0]["actors"]] == ["alice", "Zed"]
    assert tree[0]["direct_count"] == 2
    assert tree[0]["all_count"] == 3
    assert tree[0]["path"] == ["a"]
    assert tree[0]["children"][0]["depth"] == 1
    assert tree[0]["children"][0]["path"] == ["a", "c"]


def test_folder_tree_promotes_orphans_and_cycles_to_roots() -> None:
    folders = [
        {"id": "orphan", "name": "Orphan", "parent_id": "missing"},
        {"id": "one", "name": "One", "parent_id": "two"},
        {"id": "two", "name": "Two", "parent_id": "one"},
    ]

    tree = build_folder_tree(folders, {}, entry_key="entries")

    assert {folder["id"] for folder in tree} == {"orphan", "one", "two"}
    assert all(folder["parent_id"] is None for folder in tree)
