from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_hidden_grid_and_alt_disable_token_snap():
    drag = (ROOT / "static/js/map/drag/map-token-drag.js").read_text(encoding="utf-8")
    geometry = (ROOT / "static/js/map/drag/map-drag.js").read_text(encoding="utf-8")

    assert "scene.gridVisible !== false && !event.altKey" in drag
    assert "snap ? Math.round(gridX)" in geometry
    assert "Math.round(gridX * 10000) / 10000" in geometry


def test_grid_mapper_preserves_fractional_long_range_calibration():
    mapper = (ROOT / "static/js/ui/modals/scene-grid-mapper.js").read_text(encoding="utf-8")

    assert "longRangeSizes" in mapper
    assert ".toFixed(4)" in mapper
    assert "Math.round(scaledSize / imageScale)" not in mapper
    assert "window.GravewrightMap.startPan(canvas, event)" in mapper
    assert 'canvas.dispatchEvent(new WheelEvent("wheel"' in mapper
    assert "sample.x * state.zoom + state.offsetX" in mapper
    assert "requestAnimationFrame(followCamera)" in mapper
    assert "const spanX = end.x + end.width - origin.x" in mapper
    assert "size = Math.round(size)" in mapper
    assert "offsetX: stabilizeOffset(origin.x)" in mapper
    assert "renderPreview()" in mapper
    assert "samples.length !== 3" in mapper
