from __future__ import annotations

import io

from litestar.testing import TestClient
from PIL import Image

import app.actions.game.manage_actors as manage_actors
from app.domain.roles import PlayerRole
from app.engine.actors.actor_asset_service import ActorAssetService
from app.engine.actors.actor_service import ActorService
from app.engine.sheets.actor_sheet_service import ActorSheetService
from app.engine.tokens.actor_token_projector import ActorTokenProjector
from app.engine.systems.system_install_service import SystemInstallService
from app.infrastructure.storage.local_actor_asset_storage import LocalActorAssetStorage
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.token_repository import TokenRepository
from tests.conftest import TEST_SESSION_CONFIG, login, seed_campaign, seed_member, seed_scene, seed_user


def _png_bytes(size: int = 8) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (size, size), (120, 60, 30)).save(buf, "PNG")
    return buf.getvalue()


def _setup(prefix: str) -> tuple[str, str, str]:
    gm_id = seed_user(name="GM", email=f"gm-aimg-{prefix}@test.com")
    campaign_id = seed_campaign(gm_id)
    systems = SystemInstallService()
    assert systems.install(package_id="dnd5e", user_id=gm_id).success
    assert systems.enable(package_id="dnd5e").success
    actor = ActorService().create_actor(
        campaign_id=campaign_id,
        user_id=gm_id,
        system_id="dnd5e",
        actor_type="character",
        name="Fiona",
    )
    assert actor.success
    return gm_id, campaign_id, actor.actor_id


def _service(tmp_path) -> ActorAssetService:
    return ActorAssetService(storage=LocalActorAssetStorage(root=tmp_path / "actor-assets"))


def _write_route_asset(tmp_path, *, campaign_id: str, actor_id: str, kind: str) -> str:
    storage_path = f"storage/actor-assets/{campaign_id}/{actor_id}/{kind}.png"
    path = tmp_path / storage_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_png_bytes())
    ActorRepository().set_asset(actor_id=actor_id, kind=kind, storage_path=storage_path)
    return storage_path


def test_upload_sets_column_and_writes_file(db, tmp_path):
    gm_id, _, actor_id = _setup("ok")
    result = _service(tmp_path).upload_image(
        actor_id=actor_id,
        user_id=gm_id,
        kind="portrait",
        filename="face.png",
        content_type="image/png",
        data=_png_bytes(),
    )
    assert result.success
    assert result.url == f"/game/actor/{actor_id}/image/portrait?v=" + result.url.split("?v=")[1]
    actor = ActorRepository().get(actor_id)
    stored = actor["portrait_asset_id"]
    assert stored and "portrait.png" in stored


def test_invalid_type_rejected(db, tmp_path):
    gm_id, _, actor_id = _setup("bad-type")
    result = _service(tmp_path).upload_image(
        actor_id=actor_id,
        user_id=gm_id,
        kind="portrait",
        filename="face.gif",
        content_type="image/gif",
        data=b"GIF89a",
    )
    assert not result.success
    assert result.error_key == "game.actors.image.errors.unsupported_type"


def test_invalid_kind_rejected(db, tmp_path):
    gm_id, _, actor_id = _setup("bad-kind")
    result = _service(tmp_path).upload_image(
        actor_id=actor_id,
        user_id=gm_id,
        kind="banner",
        filename="x.png",
        content_type="image/png",
        data=_png_bytes(),
    )
    assert not result.success
    assert result.error_key == "game.actors.image.errors.invalid_kind"


def test_player_without_edit_cannot_upload(db, tmp_path):
    gm_id, campaign_id, actor_id = _setup("perm")
    player_id = seed_user(name="P", email="p-aimg-perm@test.com")
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    result = _service(tmp_path).upload_image(
        actor_id=actor_id,
        user_id=player_id,
        kind="portrait",
        filename="x.png",
        content_type="image/png",
        data=_png_bytes(),
    )
    assert not result.success
    assert result.error_key == "game.actors.errors.not_allowed"


def test_bundle_exposes_image_urls_and_summary(db, tmp_path):
    gm_id, _, actor_id = _setup("bundle")
    _service(tmp_path).upload_image(
        actor_id=actor_id,
        user_id=gm_id,
        kind="portrait",
        filename="p.png",
        content_type="image/png",
        data=_png_bytes(),
    )
    bundle = ActorSheetService().to_dict(
        ActorSheetService().build_bundle(actor_id=actor_id, user_id=gm_id)
    )
    assert bundle["portrait_url"] and "/image/portrait" in bundle["portrait_url"]
    assert bundle["token_url"] is None                
                                                                            
    assert bundle["summary"].get("name") == "Fiona"


def test_token_projection_uses_uploaded_token_image(db, tmp_path):
    gm_id, _, actor_id = _setup("proj")
    _service(tmp_path).upload_image(
        actor_id=actor_id,
        user_id=gm_id,
        kind="token",
        filename="t.png",
        content_type="image/png",
        data=_png_bytes(),
    )
    actor = ActorRepository().get(actor_id)
    view = ActorTokenProjector().project(actor)
    assert (
        view.get("token_asset_url") == f"/game/actor/{actor_id}/image/token?v={actor['updated_at']}"
    )


def test_player_can_load_visible_token_image_without_actor_access(db, tmp_path, monkeypatch):
    from main import app

    gm_id, campaign_id, actor_id = _setup("serve-token")
    player_id = seed_user(name="P", email="p-aimg-serve-token@test.com")
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    scene = seed_scene(campaign_id)
    TokenRepository().create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)
    _write_route_asset(tmp_path, campaign_id=campaign_id, actor_id=actor_id, kind="token")
    monkeypatch.setattr(manage_actors, "PROJECT_ROOT", tmp_path)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, player_id)
        response = client.get(f"/game/actor/{actor_id}/image/token")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")


def test_player_can_load_visible_token_portrait_fallback_without_actor_access(db, tmp_path, monkeypatch):
    from main import app

    gm_id, campaign_id, actor_id = _setup("serve-portrait")
    player_id = seed_user(name="P", email="p-aimg-serve-portrait@test.com")
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    scene = seed_scene(campaign_id)
    TokenRepository().create(scene_id=scene["id"], actor_id=actor_id, grid_x=0, grid_y=0)
    _write_route_asset(tmp_path, campaign_id=campaign_id, actor_id=actor_id, kind="portrait")
    monkeypatch.setattr(manage_actors, "PROJECT_ROOT", tmp_path)

    with TestClient(app=app, session_config=TEST_SESSION_CONFIG) as client:
        login(client, player_id)
        response = client.get(f"/game/actor/{actor_id}/image/portrait")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
