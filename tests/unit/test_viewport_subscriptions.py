from __future__ import annotations

import pytest

from app.domain.roles import PlayerRole
from app.domain.scenes import SceneChunkEncoding
from app.domain.scenes import SceneLayerKind
from app.domain.scenes import SceneLayerVisibility
from app.engine.scenes.scene_chunk_service import SceneChunkService
from app.infrastructure.storage.local_chunk_storage import LocalChunkStorage
from app.persistence.repositories.scene_layer_repository import SceneLayerRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.realtime.viewport_subscriptions import ViewportSubscriptionService
from tests.conftest import seed_campaign
from tests.conftest import seed_member
from tests.conftest import seed_user


def create_scene_stack(db):
    gm_id = seed_user(name="GM", email="viewport-gm@test.com")
    player_id = seed_user(name="Player", email="viewport-player@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    scene = SceneRepository().create(
        campaign_id=campaign_id,
        name="Warehouse",
        width=1400,
        height=1400,
        tile_size=70,
        chunk_size=16,
    )
    layer = SceneLayerRepository().create(
        scene_id=scene["id"],
        name="Ground",
        kind=SceneLayerKind.RASTER_TILE_REFS,
        visibility=SceneLayerVisibility.VISIBLE,
        display_order=0,
        encoding=SceneChunkEncoding.UINT32_TILE_REFS_V1,
    )

    return campaign_id, gm_id, player_id, scene, layer


def make_services(tmp_path):
    storage = LocalChunkStorage(root=tmp_path / "scenes")
    chunk_service = SceneChunkService(storage=storage)
    return chunk_service, ViewportSubscriptionService(chunk_service=chunk_service)


@pytest.mark.asyncio
async def test_viewport_subscription_returns_missing_and_stale_chunks(db, tmp_path):
    _campaign_id, gm_id, player_id, scene, layer = create_scene_stack(db)
    chunk_service, subscriptions = make_services(tmp_path)

    first = await chunk_service.write_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        data=b"current",
        user_id=gm_id,
    )
    second = await chunk_service.write_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=1,
        cy=0,
        data=b"new",
        user_id=gm_id,
    )

    result = subscriptions.resolve_viewport_chunks(
        user_id=player_id,
        scene_id=scene["id"],
        viewport_id="main",
        viewport_generation=3,
        cx0=0,
        cy0=0,
        cx1=1,
        cy1=0,
        layer_ids=(layer["id"],),
        known_chunks={
            subscriptions.chunk_key(layer_id=layer["id"], cx=0, cy=0): first.chunk["version"],
            subscriptions.chunk_key(layer_id=layer["id"], cx=1, cy=0): second.chunk["version"] - 1,
        },
    )

    assert result.success
    assert result.scene_epoch == scene["scene_epoch"]
    assert result.missing_count == 0
    assert result.stale_count == 1
    assert [(chunk.cx, chunk.cy, chunk.data) for chunk in result.chunks] == [(1, 0, b"new")]


@pytest.mark.asyncio
async def test_viewport_subscription_skips_current_known_chunks(db, tmp_path):
    _campaign_id, gm_id, player_id, scene, layer = create_scene_stack(db)
    chunk_service, subscriptions = make_services(tmp_path)

    written = await chunk_service.write_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        data=b"current",
        user_id=gm_id,
    )

    result = subscriptions.resolve_viewport_chunks(
        user_id=player_id,
        scene_id=scene["id"],
        viewport_id="main",
        viewport_generation=3,
        cx0=0,
        cy0=0,
        cx1=0,
        cy1=0,
        known_chunks={
            subscriptions.chunk_key(layer_id=layer["id"], cx=0, cy=0): written.chunk["version"],
        },
    )

    assert result.success
    assert result.chunks == ()
    assert result.missing_count == 0
    assert result.stale_count == 0


@pytest.mark.asyncio
async def test_viewport_candidates_are_ordered_from_focus_outward(db, tmp_path):
    _campaign_id, gm_id, player_id, scene, layer = create_scene_stack(db)
    chunk_service, subscriptions = make_services(tmp_path)

    for cx in range(5):
        await chunk_service.write_chunk(
            scene_id=scene["id"],
            layer_id=layer["id"],
            cx=cx,
            cy=0,
            data=f"chunk-{cx}".encode(),
            user_id=gm_id,
        )

    result = subscriptions.resolve_viewport_chunk_candidates(
        user_id=player_id,
        scene_id=scene["id"],
        viewport_id="main",
        viewport_generation=3,
        cx0=0,
        cy0=0,
        cx1=4,
        cy1=0,
        layer_ids=(layer["id"],),
        focus_cx=2.2,
        focus_cy=0,
    )

    assert result.success
    assert [chunk.cx for chunk in result.chunks] == [2, 3, 1, 4, 0]


@pytest.mark.asyncio
async def test_viewport_subscription_does_not_return_hidden_layer_to_player(db, tmp_path):
    _campaign_id, gm_id, player_id, scene, layer = create_scene_stack(db)
    chunk_service, subscriptions = make_services(tmp_path)

    await chunk_service.write_chunk(
        scene_id=scene["id"],
        layer_id=layer["id"],
        cx=0,
        cy=0,
        data=b"secret",
        user_id=gm_id,
    )
    SceneLayerRepository().update_metadata(
        layer_id=layer["id"],
        name=layer["name"],
        visibility=SceneLayerVisibility.HIDDEN,
        display_order=layer["display_order"],
        tile_table_version=layer["tile_table_version"],
    )

    result = subscriptions.resolve_viewport_chunks(
        user_id=player_id,
        scene_id=scene["id"],
        viewport_id="main",
        viewport_generation=3,
        cx0=0,
        cy0=0,
        cx1=0,
        cy1=0,
    )

    assert result.success
    assert result.chunks == ()
