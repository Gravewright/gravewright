from __future__ import annotations

from app.domain.roles import PlayerRole
from app.engine.content.content_import_service import ContentImportService
from app.engine.items.item_service import ItemService
from app.engine.sheets.item_sheet_data_service import ItemSheetDataService
from app.engine.sheets.item_sheet_service import ItemSheetService
from tests.conftest import install_system, seed_campaign, seed_member, seed_system, seed_user


def _setup(prefix: str) -> tuple[str, str]:
    gm_id = seed_user(name="GM", email=f"gm-{prefix}@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_system(campaign_id, gm_id, package_id="dnd5e")
    return gm_id, campaign_id


def _player(campaign_id: str, prefix: str) -> str:
    player_id = seed_user(name="Player", email=f"player-{prefix}@test.com")
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    return player_id


def test_create_item_gm(db):
    gm_id, campaign_id = _setup("create")
    result = ItemService().create_item(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        item_type="weapon",
        name="Espada Longa (modelo)",
    )
    assert result.success
    items = ItemService().list_for_campaign(campaign_id=campaign_id, user_id=gm_id)
    assert [i["name"] for i in items] == ["Espada Longa (modelo)"]


def test_create_item_requires_campaign_active_system(db):
    gm_id = seed_user(name="GM", email="gm-item-active-required@test.com")
    campaign_id = seed_campaign(gm_id)
    install_system(gm_id, package_id="dnd5e")

    result = ItemService().create_item(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        item_type="weapon",
        name="Wrong System Sword",
    )

    assert not result.success
    assert result.error_key == "game.items.errors.system_not_assigned"


def test_create_item_invalid_type_rejected(db):
    gm_id, campaign_id = _setup("badtype")
    result = ItemService().create_item(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        item_type="dragon",
        name="Nope",
    )
    assert not result.success
    assert result.error_key == "game.items.errors.invalid_type"


def test_create_item_requires_gm(db):
    gm_id, campaign_id = _setup("nogm")
    player_id = _player(campaign_id, "nogm")
    result = ItemService().create_item(
        campaign_id=campaign_id,
        user_id=player_id,
        system_id="dnd5e",
        item_type="weapon",
        name="Sneaky",
    )
    assert not result.success
    assert result.error_key == "game.items.errors.gm_required"


def test_sheet_data_patch_bumps_version(db):
    gm_id, campaign_id = _setup("patch")
    item = ItemService().create_item(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        item_type="weapon",
        name="Axe",
    )
    svc = ItemSheetDataService()
    result = svc.patch_data(item_id=item.item_id, user_id=gm_id, patch={"damage": "1d12"})
    assert result.success
    assert result.version == 2
    again = svc.get_data(item_id=item.item_id, user_id=gm_id)
    assert again.data["damage"] == "1d12"


def test_sheet_bundle_uses_item_layout(db):
    gm_id, campaign_id = _setup("bundle")
    item = ItemService().create_item(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        item_type="weapon",
        name="Mace",
    )
    bundle = ItemSheetService().build_bundle(item_id=item.item_id, user_id=gm_id)
    assert bundle is not None
    assert bundle.layout is not None
    assert bundle.can_edit is True


def test_player_visibility_follows_access(db):
    gm_id, campaign_id = _setup("vis")
    player_id = _player(campaign_id, "vis")
    item = ItemService().create_item(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        item_type="weapon",
        name="Secret Blade",
    )
    svc = ItemService()
                                        
    assert svc.list_for_campaign(campaign_id=campaign_id, user_id=player_id) == []
                 
    assert svc.set_member_access(
        item_id=item.item_id,
        target_user_id=player_id,
        access_level="read",
        requester_user_id=gm_id,
    ).success
    visible = svc.list_for_campaign(campaign_id=campaign_id, user_id=player_id)
    assert [i["id"] for i in visible] == [item.item_id]
                                                
    patched = ItemSheetDataService().patch_data(
        item_id=item.item_id, user_id=player_id, patch={"damage": "1d4"}
    )
    assert not patched.success
             
    assert svc.set_member_access(
        item_id=item.item_id,
        target_user_id=player_id,
        access_level="none",
        requester_user_id=gm_id,
    ).success
    assert svc.list_for_campaign(campaign_id=campaign_id, user_id=player_id) == []


def test_owner_can_edit(db):
    gm_id, campaign_id = _setup("owner")
    player_id = _player(campaign_id, "owner")
    item = ItemService().create_item(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        item_type="weapon",
        name="Owned",
    )
    svc = ItemService()
    toggled = svc.toggle_owner(
        item_id=item.item_id, user_id_to_toggle=player_id, requester_user_id=gm_id
    )
    assert toggled.success and toggled.is_owner is True
    patched = ItemSheetDataService().patch_data(
        item_id=item.item_id, user_id=player_id, patch={"damage": "2d6"}
    )
    assert patched.success


def test_folder_create_move_and_cycle_guard(db):
    gm_id, campaign_id = _setup("folder")
    svc = ItemService()
    parent = svc.create_folder(campaign_id=campaign_id, user_id=gm_id, name="Weapons")
    child = svc.create_folder(campaign_id=campaign_id, user_id=gm_id, name="Swords")
    assert parent.success and child.success
                              
    assert svc.move_folder(
        folder_id=child.folder_id, target_parent_id=parent.folder_id, user_id=gm_id
    ).success
                                                                
    cycle = svc.move_folder(
        folder_id=parent.folder_id, target_parent_id=child.folder_id, user_id=gm_id
    )
    assert not cycle.success
                       
    item = svc.create_item(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        item_type="weapon",
        name="Rapier",
    )
    moved = svc.move_item(item_id=item.item_id, target_folder_id=parent.folder_id, user_id=gm_id)
    assert moved.success and moved.folder_id == parent.folder_id


def test_delete_folder_unfolders_items(db):
    gm_id, campaign_id = _setup("delfolder")
    svc = ItemService()
    folder = svc.create_folder(campaign_id=campaign_id, user_id=gm_id, name="Trash")
    item = svc.create_item(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        item_type="weapon",
        name="Dagger",
        folder_id=folder.folder_id,
    )
    assert svc.delete_folder(folder_id=folder.folder_id, user_id=gm_id).success
    reloaded = svc.get_item(item_id=item.item_id, user_id=gm_id)
    assert reloaded["folder_id"] is None


def test_import_item_pack_creates_seeded_item(db):
    gm_id, campaign_id = _setup("import")
    result = ContentImportService().import_item_entry(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        pack_id="dnd5e-weapons",
        entry_id="template-longsword",
    )
    assert result.success
    item = ItemService().get_item(item_id=result.item_id, user_id=gm_id)
    assert item["name"] == "Espada Longa (modelo)"
    assert item["type"] == "weapon"
    data = ItemSheetDataService().get_data(item_id=result.item_id, user_id=gm_id).data
    assert data["damage"] == "1d8"


def test_import_actor_pack_via_item_rejected(db):
    gm_id, campaign_id = _setup("import-bad")
    result = ContentImportService().import_item_entry(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        pack_id="dnd5e-monsters",
        entry_id="template-monster",
    )
    assert not result.success
    assert result.error_key == "game.content.errors.not_importable"
