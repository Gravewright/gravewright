from app.engine.tokens.token_instance_sheet_service import get_path, patch_embedded_item


def test_unlinked_token_item_patch_updates_its_private_snapshot():
    data = {
        "skills": [
            {"id": "skill-1", "name": "Lutar", "data": {"die": {"sides": 8}}}
        ]
    }

    list_path = patch_embedded_item(data, "skill-1", {"data.key": "fighting"})

    assert list_path == "skills"
    assert get_path(data, list_path)[0]["data"]["key"] == "fighting"


def test_unlinked_token_item_patch_does_not_touch_an_unknown_item():
    data = {"skills": [{"id": "skill-1", "data": {}}]}

    assert patch_embedded_item(data, "missing", {"data.key": "fighting"}) is None
    assert data["skills"][0]["data"] == {}
