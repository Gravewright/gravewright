from __future__ import annotations

from app.engine.tokens.token_view_service import TokenViewService


def _token(**kwargs) -> dict:
    base = {
        "id": "tok_1",
        "scene_id": "scene_1",
        "actor_id": "actor_1",
        "grid_x": 5,
        "grid_y": 3,
        "width_cells": 1,
        "height_cells": 1,
        "name": None,
        "token_asset_url": None,
        "disposition": "neutral",
        "hidden": 0,
        "locked": 0,
        "controlled_by_role": "gm",
        "controlled_by_user_ids": [],
        "version": 1,
        "overrides": {},
    }
    base.update(kwargs)
    return base


def _projection(**kwargs) -> dict:
    """A manifest-mapped TokenView (as produced by ActorTokenProjector)."""
    base = {"name": "Monstro Modelo", "bars": {"bar_1": {"value": 10, "max": 10}}}
    base.update(kwargs)
    return base


def test_name_falls_back_to_projection():
    view = TokenViewService().build_view(
        token=_token(), projection=_projection(name="Monstro Modelo")
    )
    assert view["name"] == "Monstro Modelo"


def test_name_falls_back_to_actor():
    view = TokenViewService().build_view(token=_token(), projection={}, actor={"name": "Aragorn"})
    assert view["name"] == "Aragorn"


def test_token_name_overrides_projection():
    view = TokenViewService().build_view(
        token=_token(name="Monstro Modelo Guard"), projection=_projection(name="Monstro Modelo")
    )
    assert view["name"] == "Monstro Modelo Guard"


def test_overrides_dict_name_overrides_projection():
    view = TokenViewService().build_view(
        token=_token(overrides={"name": "Monstro Modelo Captain"}),
        projection=_projection(name="Monstro Modelo"),
    )
    assert view["name"] == "Monstro Modelo Captain"


def test_token_name_beats_overrides_dict():
    view = TokenViewService().build_view(
        token=_token(name="Direct Name", overrides={"name": "Override Name"}),
        projection=_projection(),
    )
    assert view["name"] == "Direct Name"


def test_unlinked_override_name_beats_initial_token_name():
    view = TokenViewService().build_view(
        token=_token(
            actor_link_mode="unlinked",
            name="Monstro Modelo",
            overrides={"name": "Monstro Modelo A"},
        ),
        projection=_projection(),
    )
    assert view["name"] == "Monstro Modelo A"


def test_empty_name_without_projection_or_actor():
    view = TokenViewService().build_view(token=_token(), projection={})
    assert view["name"] == ""


def test_asset_url_from_token_field():
    view = TokenViewService().build_view(
        token=_token(token_asset_url="/assets/template-monster.png"), projection=_projection()
    )
    assert view["asset_url"] == "/assets/template-monster.png"


def test_asset_url_from_overrides():
    view = TokenViewService().build_view(
        token=_token(overrides={"token_asset_url": "/assets/custom.png"}), projection=_projection()
    )
    assert view["asset_url"] == "/assets/custom.png"


def test_asset_url_falls_back_to_projection():
    view = TokenViewService().build_view(
        token=_token(), projection=_projection(token_asset_url="/assets/projected.png")
    )
    assert view["asset_url"] == "/assets/projected.png"


def test_asset_url_none_by_default():
    view = TokenViewService().build_view(token=_token(), projection=_projection())
    assert view["asset_url"] is None


def test_missing_actor_image_is_not_sent_to_the_texture_loader(monkeypatch):
    monkeypatch.setattr(
        "app.engine.tokens.token_view_service.actor_image_file_exists",
        lambda actor, kind: False,
    )
    view = TokenViewService().build_view(
        token=_token(token_asset_url="/game/actor/actor_1/image/portrait?v=7"),
        projection=_projection(),
        actor={"id": "actor_1", "campaign_id": "campaign_1", "name": "Missing"},
    )
    assert view["asset_url"] is None


def test_lower_bar_from_projection():
    view = TokenViewService().build_view(
        token=_token(), projection=_projection(bars={"bar_1": {"value": 7, "max": 10}})
    )
    assert view["bars"]["bar_1"]["value"] == 7
    assert view["bars"]["bar_1"]["max"] == 10
    assert view["bars"]["bar_1"]["visibility"] == "everyone"


def test_both_slots_render_independently():
    """The two bars are separate readings; one may be set and the other not."""
    view = TokenViewService().build_view(
        token=_token(),
        projection=_projection(
            bars={"bar_1": {"value": 7, "max": 10}, "bar_2": {"value": 2, "max": 4}}
        ),
    )
    assert view["bars"]["bar_1"]["value"] == 7
    assert view["bars"]["bar_2"]["value"] == 2


def test_only_the_upper_bar_is_fine():
    view = TokenViewService().build_view(
        token=_token(), projection=_projection(bars={"bar_2": {"value": 5, "max": 5}})
    )
    assert set(view["bars"]) == {"bar_2"}


def test_bar_colors_default_to_green_below_and_blue_above():
    view = TokenViewService().build_view(
        token=_token(),
        projection=_projection(
            bars={"bar_1": {"value": 1, "max": 1}, "bar_2": {"value": 1, "max": 1}}
        ),
    )
    assert view["bars"]["bar_1"]["color"] == "#4caf50"
    assert view["bars"]["bar_2"]["color"] == "#3b82f6"


def test_a_system_color_survives_into_the_view():
    view = TokenViewService().build_view(
        token=_token(),
        projection=_projection(bars={"bar_1": {"value": 1, "max": 1, "color": "#a020f0"}}),
    )
    assert view["bars"]["bar_1"]["color"] == "#a020f0"


def test_bar_max_defaults_to_value():
    view = TokenViewService().build_view(
        token=_token(), projection=_projection(bars={"bar_1": {"value": 7}})
    )
    assert view["bars"]["bar_1"]["value"] == 7
    assert view["bars"]["bar_1"]["max"] == 7


def test_bar_from_override_wins():
    view = TokenViewService().build_view(
        token=_token(overrides={"bar_1": {"value": 3, "max": 7}}),
        projection=_projection(bars={"bar_1": {"value": 10, "max": 10}}),
    )
    assert view["bars"]["bar_1"]["value"] == 3
    assert view["bars"]["bar_1"]["max"] == 7


def test_an_override_does_not_repaint_the_bar():
    """The copy carries its own numbers; what the bar *is* stays the system's."""
    view = TokenViewService().build_view(
        token=_token(overrides={"bar_1": {"value": 3, "max": 7}}),
        projection=_projection(bars={"bar_1": {"value": 10, "max": 10, "color": "#a020f0"}}),
    )
    assert view["bars"]["bar_1"]["color"] == "#a020f0"


def test_no_bars_when_projection_has_none():
    view = TokenViewService().build_view(token=_token(), projection={"name": "Monstro Modelo"})
    assert view["bars"] == {}


def test_bar_with_null_value_is_skipped():
    view = TokenViewService().build_view(
        token=_token(), projection=_projection(bars={"bar_1": {"value": None, "max": None}})
    )
    assert view["bars"] == {}


def test_empty_conditions_status_summary():
    view = TokenViewService().build_view(token=_token(), projection=_projection())
    assert view["status_summary"] == {"count": 0, "has_negative": False, "has_positive": False}


def test_status_summary_with_conditions():
    conditions = [
        {"kind": "negative", "condition_id": "poisoned"},
        {"kind": "positive", "condition_id": "bless"},
        {"kind": "neutral", "condition_id": "prone"},
    ]
    view = TokenViewService().build_view(
        token=_token(), projection=_projection(), conditions=conditions
    )
    assert view["status_summary"]["count"] == 3
    assert view["status_summary"]["has_negative"] is True
    assert view["status_summary"]["has_positive"] is True


def test_gm_sees_hidden_tokens():
    tokens = [_token(id="tok_1", hidden=0), _token(id="tok_2", hidden=1)]
    views = TokenViewService().build_views_for_scene(
        tokens=tokens,
        projections_by_actor_id={},
        actors_by_id={},
        conditions_by_token_id={},
        is_gm=True,
    )
    assert len(views) == 2


def test_player_does_not_see_hidden_tokens():
    tokens = [_token(id="tok_1", hidden=0), _token(id="tok_2", hidden=1)]
    views = TokenViewService().build_views_for_scene(
        tokens=tokens,
        projections_by_actor_id={},
        actors_by_id={},
        conditions_by_token_id={},
        is_gm=False,
    )
    assert len(views) == 1
    assert views[0]["token_id"] == "tok_1"


def test_build_views_resolves_projection_and_conditions():
    token = _token(id="tok_1", actor_id="actor_1", hidden=0)
    projection = _projection(name="Hero", bars={"bar_1": {"value": 20, "max": 20}})
    conditions = [{"kind": "negative", "condition_id": "prone"}]

    views = TokenViewService().build_views_for_scene(
        tokens=[token],
        projections_by_actor_id={"actor_1": projection},
        actors_by_id={"actor_1": {"name": "Hero"}},
        conditions_by_token_id={"tok_1": conditions},
        is_gm=False,
    )

    assert len(views) == 1
    assert views[0]["name"] == "Hero"
    assert views[0]["bars"]["bar_1"]["value"] == 20
    assert views[0]["status_summary"]["count"] == 1


def test_basic_view_fields_present():
    view = TokenViewService().build_view(
        token=_token(grid_x=4, grid_y=2, disposition="hostile"), projection=_projection()
    )
    assert view["token_id"] == "tok_1"
    assert view["scene_id"] == "scene_1"
    assert view["actor_id"] == "actor_1"
    assert view["grid_x"] == 4
    assert view["grid_y"] == 2
    assert view["disposition"] == "hostile"
    assert view["hidden"] is False
    assert view["locked"] is False
    assert view["version"] == 1
