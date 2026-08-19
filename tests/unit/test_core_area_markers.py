from pathlib import Path

from app.business.campaigns.campaign_system_service import resolved_area_marker_presets
from app.persistence.repositories.scene_repository import _normalize_board_area_marker


ROOT = Path(__file__).resolve().parents[2]


def test_core_area_markers_fill_only_an_empty_system_palette():
    defaults = resolved_area_marker_presets([])
    assert [preset["shape"] for preset in defaults] == ["line", "circle", "square", "cone"]
    assert all(preset["id"].startswith("core.") and preset["style"] for preset in defaults)

    custom = [{"id": "system.burst", "shape": "circle", "label": "Burst"}]
    assert resolved_area_marker_presets(custom) == custom


def test_area_marker_rotation_is_normalized_and_persisted():
    marker = _normalize_board_area_marker({
        "id": "marker-1",
        "scene_id": "scene-1",
        "shape": "square",
        "start": {"worldX": 10, "worldY": 20},
        "end": {"worldX": 80, "worldY": 90},
        "rotation": 450,
        "anchor_mode": "vertex",
    })
    assert marker["rotation"] == 90.0
    assert marker["anchor_mode"] == "vertex"


def test_core_marker_labels_and_removed_vertical_layers_ui_are_wired():
    template = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")
    toolbar = (ROOT / "static/js/tools/tools-toolbar.js").read_text(encoding="utf-8")

    for shape in ("line", "circle", "square", "cone"):
        assert f'data-area-marker-label-{shape}=' in template
    assert "markerPresetLabel" in toolbar
    assert 'data-tool-sub-panel="layers"' not in template
    assert "data-layers-toggle" not in template
    assert "toggleLayersPanel" not in toolbar


def test_markers_and_measurement_units_are_rendered_by_pixi_not_css_svg():
    adapter = (ROOT / "static/js/map/measures/map-measure-renderer.js").read_text(encoding="utf-8")
    pixi = (ROOT / "static/js/board/pixi/pixi-measure-layer.js").read_text(encoding="utf-8")
    layers = (ROOT / "static/js/board/pixi/pixi-board-layers.js").read_text(encoding="utf-8")
    css = (ROOT / "static/css/game.css").read_text(encoding="utf-8")

    assert "createElementNS" not in adapter and "boardRenderer.setMeasurements" in adapter
    assert "_renderMeasurements(board)" in pixi
    assert "new PIXI.Text" in pixi and "new PIXI.Graphics" in layers
    assert "board.measureLayer" in layers
    assert ".board-measure-overlay" not in css
    assert ".board-measure-label" not in css
