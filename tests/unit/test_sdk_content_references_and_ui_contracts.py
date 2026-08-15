from pathlib import Path

import pytest

from app.engine.sdk.content_reference_service import parse_content_reference
from app.engine.sdk.package_manifest import PackageSetting
from app.engine.sdk.package_settings_service import SettingValueError, coerce_setting_value


ROOT = Path(__file__).resolve().parents[2]


def test_grave_reference_round_trip_and_campaign_boundary():
    ref = parse_content_reference(
        "grave://campaign/campaign-1/scene/scene-1/token/token-1?page=3&anchor=target",
        campaign_id="campaign-1",
    )
    assert ref.kind == "token"
    assert ref.parent_kind == "scene"
    assert ref.parent_id == "scene-1"
    assert ref.page == 3
    assert ref.uri == "grave://campaign/campaign-1/scene/scene-1/token/token-1?page=3&anchor=target"
    with pytest.raises(PermissionError):
        parse_content_reference(ref.uri, campaign_id="campaign-2")


@pytest.mark.parametrize("value", [-1, 11])
def test_typed_setting_enforces_numeric_bounds(value):
    definition = PackageSetting(key="volume", scope="client", type="integer", minimum=0, maximum=10)
    with pytest.raises(SettingValueError):
        coerce_setting_value(definition, value)


def test_typed_setting_enforces_string_pattern():
    definition = PackageSetting(key="color", scope="user", type="string", pattern=r"#[0-9a-f]{6}")
    assert coerce_setting_value(definition, "#a0b1c2") == "#a0b1c2"
    with pytest.raises(SettingValueError):
        coerce_setting_value(definition, "red")


def test_renderer_and_partial_application_contracts_are_loaded():
    render_loop = (ROOT / "static/js/map/render-loop/map-render-loop.js").read_text(encoding="utf-8")
    game_page = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")
    partial = (ROOT / "static/js/ui/partial-applications.js").read_text(encoding="utf-8")
    assert "dirtyFlags" in render_loop and "invalidate: markDirty" in render_loop
    assert "partial-applications.js" in game_page
    assert "window.GravewrightApplications" in partial and "options.parts" in partial
