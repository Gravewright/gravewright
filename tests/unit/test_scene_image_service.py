from __future__ import annotations

from app.engine.scenes.scene_image_service import SceneImageService
from app.persistence.repositories.asset_repository import AssetRepository
from app.persistence.repositories.scene_image_repository import SceneImageRepository
from app.security.scene_image_permissions import can_upload_scene_image
from tests.conftest import seed_campaign
from tests.conftest import seed_member
from tests.conftest import seed_scene
from tests.conftest import seed_user


def _placement(campaign_id: str, scene_id: str, owner_user_id: str, *, layer: str = "game") -> dict:
    return SceneImageRepository().create(
        campaign_id=campaign_id,
        scene_id=scene_id,
        asset_id="asset-1",
        owner_user_id=owner_user_id,
        x=10.0,
        y=20.0,
        natural_width=640,
        natural_height=480,
        layer=layer,
    )


def _library_asset(campaign_id: str, owner_user_id: str) -> dict:
    return AssetRepository().create(
        campaign_id=campaign_id,
        owner_user_id=owner_user_id,
        filename="card.png",
        content_type="image/png",
        byte_size=42,
        storage_path="x/card.png",
        hash="hash",
        width=300,
        height=420,
    )


def test_upload_permission_allows_players_not_streamers():
    assert can_upload_scene_image(actor_role="gm") is True
    assert can_upload_scene_image(actor_role="assistant_gm") is True
    assert can_upload_scene_image(actor_role="player") is True
    assert can_upload_scene_image(actor_role="streamer") is False
    assert can_upload_scene_image(actor_role=None) is False


def test_get_state_returns_placements_with_src(db):
    gm_id = seed_user(name="GM", email="scimg-state@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)
    _placement(campaign_id, scene["id"], gm_id)

    result = SceneImageService().get_state(campaign_id=campaign_id, user_id=gm_id)

    assert result.success, result.error_key
    placements = result.payload["placements"]
    assert len(placements) == 1
    assert placements[0]["src"] == "/game/assets/file/asset-1"
    assert placements[0]["natural_width"] == 640


def test_non_member_cannot_read_state(db):
    gm_id = seed_user(name="GM", email="scimg-nonmember-gm@test.com")
    outsider = seed_user(name="Outsider", email="scimg-outsider@test.com")
    campaign_id = seed_campaign(gm_id)

    result = SceneImageService().get_state(campaign_id=campaign_id, user_id=outsider)

    assert not result.success
    assert result.error_key == "game.scene_images.errors.not_found"


def test_owner_and_gm_can_move_third_party_cannot(db):
    gm_id = seed_user(name="GM", email="scimg-move-gm@test.com")
    owner_id = seed_user(name="Owner", email="scimg-move-owner@test.com")
    other_id = seed_user(name="Other", email="scimg-move-other@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, owner_id, "player")
    seed_member(campaign_id, other_id, "player")
    scene = seed_scene(campaign_id)
    placement = _placement(campaign_id, scene["id"], owner_id)
    service = SceneImageService()

    owner_move = service.update_placement(
        campaign_id=campaign_id, user_id=owner_id, placement_id=placement["id"], x=99.0, y=99.0
    )
    assert owner_move.success, owner_move.error_key
    assert owner_move.payload["placement"]["x"] == 99.0

    gm_move = service.update_placement(
        campaign_id=campaign_id, user_id=gm_id, placement_id=placement["id"], x=5.0
    )
    assert gm_move.success, gm_move.error_key

    other_move = service.update_placement(
        campaign_id=campaign_id, user_id=other_id, placement_id=placement["id"], x=0.0
    )
    assert not other_move.success
    assert other_move.error_key == "permissions.errors.denied"


def test_place_asset_uses_existing_asset_dimensions(db):
    gm_id = seed_user(name="GM", email="scimg-placeasset@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)
    asset = _library_asset(campaign_id, gm_id)

    result = SceneImageService().place_asset(
        campaign_id=campaign_id, user_id=gm_id, scene_id=scene["id"], asset_id=asset["id"], x=5.0, y=6.0
    )

    assert result.success, result.error_key
    placement = result.payload["placement"]
    assert placement["natural_width"] == 300
    assert placement["natural_height"] == 420
    assert placement["scale"] == 180 / 420
    assert placement["owner_user_id"] == gm_id
    assert placement["src"] == f"/game/assets/file/{asset['id']}"


def test_place_asset_accepts_rotation_and_scale(db):
    gm_id = seed_user(name="GM", email="scimg-placeasset-transform@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)
    asset = _library_asset(campaign_id, gm_id)

    result = SceneImageService().place_asset(
        campaign_id=campaign_id,
        user_id=gm_id,
        scene_id=scene["id"],
        asset_id=asset["id"],
        x=5.0,
        y=6.0,
        rotation=30.0,
        scale=0.5,
    )

    assert result.success, result.error_key
    placement = result.payload["placement"]
    assert placement["rotation"] == 30.0
    assert placement["scale"] == 0.5


def test_place_asset_rejects_foreign_asset(db):
    gm_id = seed_user(name="GM", email="scimg-foreign@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)

    result = SceneImageService().place_asset(
        campaign_id=campaign_id, user_id=gm_id, scene_id=scene["id"], asset_id="does-not-exist", x=0.0, y=0.0
    )

    assert not result.success
    assert result.error_key == "game.scene_images.errors.invalid_image"


def test_gm_only_placement_hidden_from_players_visible_to_gm_and_streamer(db):
    gm_id = seed_user(name="GM", email="scimg-gmlayer-gm@test.com")
    player_id = seed_user(name="Player", email="scimg-gmlayer-player@test.com")
    streamer_id = seed_user(name="Streamer", email="scimg-gmlayer-streamer@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, "player")
    seed_member(campaign_id, streamer_id, "streamer")
    scene = seed_scene(campaign_id)
    _placement(campaign_id, scene["id"], gm_id)
    _placement(campaign_id, scene["id"], gm_id, layer="gm")
    _placement(campaign_id, scene["id"], gm_id, layer="composition")

    service = SceneImageService()
    gm_view = service.get_state(campaign_id=campaign_id, user_id=gm_id)
    player_view = service.get_state(campaign_id=campaign_id, user_id=player_id)
    streamer_view = service.get_state(campaign_id=campaign_id, user_id=streamer_id)

    # Composition + game are visible to everyone; only the gm layer is hidden from players.
    assert len(gm_view.payload["placements"]) == 3
    assert len(streamer_view.payload["placements"]) == 3
    assert len(player_view.payload["placements"]) == 2
    assert all(p["layer"] != "gm" for p in player_view.payload["placements"])


def test_only_gm_can_send_to_gm_layer(db):
    gm_id = seed_user(name="GM", email="scimg-setgm-gm@test.com")
    owner_id = seed_user(name="Owner", email="scimg-setgm-owner@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, owner_id, "player")
    scene = seed_scene(campaign_id)
    placement = _placement(campaign_id, scene["id"], owner_id)
    service = SceneImageService()

    denied = service.update_placement(
        campaign_id=campaign_id, user_id=owner_id, placement_id=placement["id"], layer="gm"
    )
    assert not denied.success
    assert denied.error_key == "permissions.errors.denied"

    allowed = service.update_placement(
        campaign_id=campaign_id, user_id=gm_id, placement_id=placement["id"], layer="gm"
    )
    assert allowed.success, allowed.error_key
    assert allowed.payload["placement"]["layer"] == "gm"
    assert allowed.payload["placement"]["gm_only"] is True


def test_composition_layer_requires_gm_to_place(db):
    gm_id = seed_user(name="GM", email="scimg-comp-gm@test.com")
    player_id = seed_user(name="Player", email="scimg-comp-player@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, "player")
    scene = seed_scene(campaign_id)
    asset = _library_asset(campaign_id, gm_id)
    service = SceneImageService()

    denied = service.place_asset(
        campaign_id=campaign_id, user_id=player_id, scene_id=scene["id"],
        asset_id=asset["id"], x=1.0, y=2.0, layer="composition",
    )
    assert not denied.success
    assert denied.error_key == "permissions.errors.denied"

    allowed = service.place_asset(
        campaign_id=campaign_id, user_id=gm_id, scene_id=scene["id"],
        asset_id=asset["id"], x=1.0, y=2.0, layer="composition",
    )
    assert allowed.success, allowed.error_key
    assert allowed.payload["placement"]["layer"] == "composition"
    assert allowed.payload["placement"]["gm_only"] is False


def test_delete_by_owner_removes_placement(db):
    gm_id = seed_user(name="GM", email="scimg-del-gm@test.com")
    owner_id = seed_user(name="Owner", email="scimg-del-owner@test.com")
    other_id = seed_user(name="Other", email="scimg-del-other@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, owner_id, "player")
    seed_member(campaign_id, other_id, "player")
    scene = seed_scene(campaign_id)
    placement = _placement(campaign_id, scene["id"], owner_id)
    service = SceneImageService()

    denied = service.delete_placement(
        campaign_id=campaign_id, user_id=other_id, placement_id=placement["id"]
    )
    assert not denied.success
    assert denied.error_key == "permissions.errors.denied"

    removed = service.delete_placement(
        campaign_id=campaign_id, user_id=owner_id, placement_id=placement["id"]
    )
    assert removed.success, removed.error_key
    assert SceneImageRepository().get(placement["id"]) is None
