from __future__ import annotations

from app.engine.assets.asset_library_service import AssetLibraryService
from app.persistence.repositories.asset_repository import AssetRepository
from app.security.asset_permissions import can_manage_assets
from app.security.asset_permissions import can_view_assets
from tests.conftest import seed_campaign
from tests.conftest import seed_member
from tests.conftest import seed_user


def _asset(campaign_id: str, owner_user_id: str) -> dict:
    return AssetRepository().create(
        campaign_id=campaign_id,
        owner_user_id=owner_user_id,
        filename="statue.png",
        content_type="image/png",
        byte_size=42,
        storage_path="x/statue.png",
        hash="hash",
        width=300,
        height=420,
    )


def test_manage_permission_allows_players_not_streamers():
    assert can_manage_assets(actor_role="gm") is True
    assert can_manage_assets(actor_role="assistant_gm") is True
    assert can_manage_assets(actor_role="player") is True
    assert can_manage_assets(actor_role="streamer") is False
    assert can_manage_assets(actor_role=None) is False
    assert can_view_assets(actor_role="streamer") is True
    assert can_view_assets(actor_role=None) is False


def test_non_member_cannot_read_state(db):
    gm_id = seed_user(name="GM", email="asset-nonmember-gm@test.com")
    outsider = seed_user(name="Outsider", email="asset-outsider@test.com")
    campaign_id = seed_campaign(gm_id)

    result = AssetLibraryService().get_state(campaign_id=campaign_id, user_id=outsider)

    assert not result.success
    assert result.error_key == "game.assets.errors.not_found"


def test_folders_and_move_present_with_src(db):
    gm_id = seed_user(name="GM", email="asset-library@test.com")
    campaign_id = seed_campaign(gm_id)
    service = AssetLibraryService()

    folder = service.create_folder(campaign_id=campaign_id, user_id=gm_id, name="Props")
    assert folder.success, folder.error_key
    folder_id = folder.payload["folder"]["id"]

    asset = _asset(campaign_id, gm_id)
    moved = service.move_asset(campaign_id=campaign_id, user_id=gm_id, asset_id=asset["id"], folder_id=folder_id)

    assert moved.success, moved.error_key
    assert moved.payload["asset"]["folder_id"] == folder_id
    assert moved.payload["asset"]["src"] == f"/game/assets/file/{asset['id']}"

    state = service.get_state(campaign_id=campaign_id, user_id=gm_id)
    assert state.success, state.error_key
    assert state.payload["folders"][0]["name"] == "Props"
    assert state.payload["assets"][0]["id"] == asset["id"]
    assert state.payload["assets"][0]["src"] == f"/game/assets/file/{asset['id']}"


def test_delete_asset_removes_from_library(db):
    gm_id = seed_user(name="GM", email="asset-delete-gm@test.com")
    campaign_id = seed_campaign(gm_id)
    service = AssetLibraryService()
    asset = _asset(campaign_id, gm_id)

    result = service.delete_asset(campaign_id=campaign_id, user_id=gm_id, asset_id=asset["id"])

    assert result.success, result.error_key
    assert AssetRepository().get_by_id(asset["id"]) is None
    state = service.get_state(campaign_id=campaign_id, user_id=gm_id)
    assert state.payload["assets"] == []


def test_move_rejects_foreign_folder(db):
    gm_id = seed_user(name="GM", email="asset-foreign-folder@test.com")
    campaign_id = seed_campaign(gm_id)
    other_campaign = seed_campaign(seed_user(name="Other", email="asset-other-gm@test.com"))
    service = AssetLibraryService()
    other_folder = service.create_folder(campaign_id=other_campaign, user_id=gm_id, name="Foreign")
    asset = _asset(campaign_id, gm_id)

    result = service.move_asset(
        campaign_id=campaign_id,
        user_id=gm_id,
        asset_id=asset["id"],
        folder_id=other_folder.payload["folder"]["id"] if other_folder.success else "missing",
    )

    assert not result.success


def test_player_cannot_manage_but_can_view(db):
    gm_id = seed_user(name="GM", email="asset-player-gm@test.com")
    spectator = seed_user(name="Spec", email="asset-spectator@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, spectator, "streamer")

    denied = AssetLibraryService().create_folder(campaign_id=campaign_id, user_id=spectator, name="Nope")
    assert not denied.success
    assert denied.error_key == "permissions.errors.denied"

    state = AssetLibraryService().get_state(campaign_id=campaign_id, user_id=spectator)
    assert state.success, state.error_key
