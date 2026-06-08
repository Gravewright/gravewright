from __future__ import annotations

from app.domain.fog import FogCircleGeom
from app.domain.fog import FogInitialState
from app.domain.fog import FogMode
from app.domain.fog import FogOp
from app.domain.fog import FogPolygonGeom
from app.domain.fog import FogShape
from app.domain.fog import FogSquareGeom
from app.domain.roles import PlayerRole
from app.engine.scenes.fog_service import FogService
from tests.conftest import seed_campaign
from tests.conftest import seed_member
from tests.conftest import seed_scene
from tests.conftest import seed_user


def test_enable_sets_baseline_and_clears_ops(db):
    gm_id = seed_user(name="GM", email="gm-fog-enable@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)

    service = FogService()
    result = service.enable(
        scene_id=scene["id"],
        user_id=gm_id,
        initial=FogInitialState.HIDE_ALL,
    )

    assert result.success
    assert result.enabled is True
    assert result.baseline == FogInitialState.HIDE_ALL.value
    assert result.ops == []
    assert result.version == 1


def test_enable_reveal_all(db):
    gm_id = seed_user(name="GM", email="gm-fog-reveal@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)

    service = FogService()
    result = service.enable(
        scene_id=scene["id"],
        user_id=gm_id,
        initial=FogInitialState.REVEAL_ALL,
    )

    assert result.success
    assert result.baseline == FogInitialState.REVEAL_ALL.value


def test_paint_appends_circle_op(db):
    gm_id = seed_user(name="GM", email="gm-fog-circle@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)

    service = FogService()
    service.enable(scene_id=scene["id"], user_id=gm_id, initial=FogInitialState.HIDE_ALL)

    result = service.paint(
        scene_id=scene["id"],
        user_id=gm_id,
        ops=[
            FogOp(
                mode=FogMode.REVEAL,
                shape=FogShape.CIRCLE,
                geom=FogCircleGeom(center_x_cells=5.0, center_y_cells=5.0, radius_cells=2.0),
            )
        ],
        expected_version=1,
    )

    assert result.success
    assert result.version == 2
    assert len(result.ops) == 1
    assert len(result.new_ops) == 1
    op = result.ops[0]
    assert op["mode"] == "reveal"
    assert op["shape"] == "circle"
    assert op["geom"] == {
        "center_x_cells": 5.0,
        "center_y_cells": 5.0,
        "radius_cells": 2.0,
    }


def test_paint_accumulates_ops_in_order(db):
    gm_id = seed_user(name="GM", email="gm-fog-accumulate@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)

    service = FogService()
    service.enable(scene_id=scene["id"], user_id=gm_id, initial=FogInitialState.HIDE_ALL)
    service.paint(
        scene_id=scene["id"],
        user_id=gm_id,
        ops=[FogOp(FogMode.REVEAL, FogShape.CIRCLE, FogCircleGeom(1.0, 1.0, 1.0))],
        expected_version=1,
    )
    result = service.paint(
        scene_id=scene["id"],
        user_id=gm_id,
        ops=[FogOp(FogMode.HIDE, FogShape.SQUARE, FogSquareGeom(2.0, 2.0, 2.0))],
        expected_version=2,
    )

    assert result.success
    assert len(result.ops) == 2
    assert len(result.new_ops) == 1
    assert result.ops[0]["shape"] == "circle"
    assert result.ops[1]["shape"] == "square"


def test_paint_polygon_geom_roundtrip(db):
    gm_id = seed_user(name="GM", email="gm-fog-poly@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)

    service = FogService()
    service.enable(scene_id=scene["id"], user_id=gm_id, initial=FogInitialState.HIDE_ALL)

    result = service.paint(
        scene_id=scene["id"],
        user_id=gm_id,
        ops=[
            FogOp(
                mode=FogMode.REVEAL,
                shape=FogShape.POLYGON,
                geom=FogPolygonGeom(points_cells=((5.0, 5.0), (10.0, 5.0), (7.5, 10.0))),
            )
        ],
        expected_version=1,
    )

    assert result.success
    geom = result.ops[0]["geom"]
    assert geom["points_cells"] == [[5.0, 5.0], [10.0, 5.0], [7.5, 10.0]]


def test_paint_requires_fog_enabled(db):
    gm_id = seed_user(name="GM", email="gm-fog-disabled@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)

    service = FogService()
    result = service.paint(
        scene_id=scene["id"],
        user_id=gm_id,
        ops=[FogOp(FogMode.REVEAL, FogShape.CIRCLE, FogCircleGeom(1.0, 1.0, 1.0))],
        expected_version=0,
    )

    assert not result.success
    assert result.error_key == "game.fog.errors.disabled"


def test_paint_detects_version_conflict(db):
    gm_id = seed_user(name="GM", email="gm-fog-version@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)

    service = FogService()
    service.enable(scene_id=scene["id"], user_id=gm_id, initial=FogInitialState.HIDE_ALL)

    result = service.paint(
        scene_id=scene["id"],
        user_id=gm_id,
        ops=[FogOp(FogMode.REVEAL, FogShape.CIRCLE, FogCircleGeom(5.0, 5.0, 1.0))],
        expected_version=999,
    )

    assert not result.success
    assert result.error_key == "game.fog.errors.version_conflict"


def test_reset_clears_ops_and_sets_baseline(db):
    gm_id = seed_user(name="GM", email="gm-fog-reset@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)

    service = FogService()
    service.enable(scene_id=scene["id"], user_id=gm_id, initial=FogInitialState.REVEAL_ALL)
    service.paint(
        scene_id=scene["id"],
        user_id=gm_id,
        ops=[FogOp(FogMode.HIDE, FogShape.CIRCLE, FogCircleGeom(5.0, 5.0, 2.0))],
        expected_version=1,
    )

    result = service.reset(scene_id=scene["id"], user_id=gm_id, to=FogInitialState.HIDE_ALL)

    assert result.success
    assert result.baseline == FogInitialState.HIDE_ALL.value
    assert result.ops == []


def test_disable_clears_state(db):
    gm_id = seed_user(name="GM", email="gm-fog-disable@test.com")
    campaign_id = seed_campaign(gm_id)
    scene = seed_scene(campaign_id)

    service = FogService()
    service.enable(scene_id=scene["id"], user_id=gm_id, initial=FogInitialState.HIDE_ALL)
    result = service.disable(scene_id=scene["id"], user_id=gm_id)

    assert result.success
    assert result.enabled is False

    state = service.get_state(scene["id"])
    assert state.success
    assert state.enabled is False
    assert state.ops == []


def test_player_cannot_paint(db):
    gm_id = seed_user(name="GM", email="gm-fog-perm-gm@test.com")
    player_id = seed_user(name="Player", email="player-fog-perm@test.com")
    campaign_id = seed_campaign(gm_id)
    seed_member(campaign_id, player_id, PlayerRole.PLAYER.value)
    scene = seed_scene(campaign_id)

    service = FogService()
    service.enable(scene_id=scene["id"], user_id=gm_id, initial=FogInitialState.HIDE_ALL)

    result = service.paint(
        scene_id=scene["id"],
        user_id=player_id,
        ops=[FogOp(FogMode.REVEAL, FogShape.CIRCLE, FogCircleGeom(5.0, 5.0, 1.0))],
        expected_version=1,
    )

    assert not result.success
    assert result.error_key == "permissions.errors.denied"
