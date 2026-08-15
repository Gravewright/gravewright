from app.engine.items.item_service import ItemService
from tests.conftest import seed_campaign, seed_user


def _setup_tree():
    gm_id = seed_user(name="GM", email="item-folder-delete@test.com")
    campaign_id = seed_campaign(gm_id)
    service = ItemService()
    parent = service.create_folder(campaign_id=campaign_id, user_id=gm_id, name="Package")
    child = service.create_folder(
        campaign_id=campaign_id, user_id=gm_id, name="Skills", parent_id=parent.folder_id
    )
    nested = service.create_folder(
        campaign_id=campaign_id, user_id=gm_id, name="Novice", parent_id=child.folder_id
    )
    direct_item = service.items.create(
        campaign_id=campaign_id,
        system_id="test-system",
        item_type="skill",
        name="Direct",
        created_by_user_id=gm_id,
        folder_id=child.folder_id,
    )
    nested_item = service.items.create(
        campaign_id=campaign_id,
        system_id="test-system",
        item_type="skill",
        name="Nested",
        created_by_user_id=gm_id,
        folder_id=nested.folder_id,
    )
    return service, gm_id, parent.folder_id, child.folder_id, nested.folder_id, direct_item, nested_item


def test_delete_only_folder_moves_contents_up_one_level(db):
    service, gm_id, parent_id, child_id, nested_id, direct_item, nested_item = _setup_tree()

    result = service.delete_folder(folder_id=child_id, user_id=gm_id, delete_contents=False)

    assert result.success
    assert service.folders.get_by_id(folder_id=child_id) is None
    assert service.items.get(direct_item)["folder_id"] == parent_id
    assert service.folders.get_by_id(folder_id=nested_id)["parent_id"] == parent_id
    assert service.items.get(nested_item)["status"] == "active"


def test_delete_folder_with_contents_removes_entire_subtree(db):
    service, gm_id, _parent_id, child_id, nested_id, direct_item, nested_item = _setup_tree()

    result = service.delete_folder(folder_id=child_id, user_id=gm_id, delete_contents=True)

    assert result.success
    assert service.folders.get_by_id(folder_id=child_id) is None
    assert service.folders.get_by_id(folder_id=nested_id) is None
    assert service.items.get(direct_item)["status"] == "deleted"
    assert service.items.get(nested_item)["status"] == "deleted"
