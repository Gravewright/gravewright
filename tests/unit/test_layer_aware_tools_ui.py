from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_tool_registry_declares_layer_compatibility():
    registry = (ROOT / "static/js/tools/tools-registry.js").read_text(encoding="utf-8")
    toolbar = (ROOT / "static/js/tools/tools-toolbar.js").read_text(encoding="utf-8")
    # A lista de camadas vive num lugar so: quando estava copiada em quatro
    # arquivos, acrescentar Efeitos e Paredes deixava metade do dock sem saber
    # que elas existiam.
    assert 'const LAYERS = ["game", "gm", "composition", "effects", "walls", "lighting"]' in registry
    assert "select: LAYERS" in registry
    for tool in ("ruler", "hp", "draw", "shape"):
        assert f'{tool}: ["game", "gm"]' in registry
    assert "syncToolsForLayer" in toolbar
    assert "if (!toolSupportsLayer(activeTool)) setActiveTool(DEFAULT_TOOL)" in toolbar
    template = (ROOT / "templates/pages/game/index.html").read_text(encoding="utf-8")
    assert template.count('data-active-layer="composition"') >= 2


def test_selection_is_scoped_to_the_active_layer():
    selection = (ROOT / "static/js/map/selection/map-selection.js").read_text(encoding="utf-8")
    images = (ROOT / "static/js/scene-images/scene-image-layer.js").read_text(encoding="utf-8")
    layer_mode = (ROOT / "static/js/map/layers/map-layer-mode.js").read_text(encoding="utf-8")
    assert 'if (layer === "composition") return false' in selection
    assert 'Boolean(token?.hidden) === (layer === "gm")' in selection
    assert "p.layer === activeLayer" in images
    assert "placement.layer !== activeLayer" in images
    assert 'activeDrawLayer !== "composition"' in layer_mode


def test_layer_preferences_visibility_and_lock_are_local_and_persistent():
    toolbar = (ROOT / "static/js/tools/tools-toolbar.js").read_text(encoding="utf-8")
    render_loop = (ROOT / "static/js/map/render-loop/map-render-loop.js").read_text(encoding="utf-8")
    measures = (ROOT / "static/js/map/measures/map-measure-renderer.js").read_text(encoding="utf-8")
    assert "gravewright.tools.layers.v1" not in toolbar  # key is composed from STORAGE_KEY
    assert '`${STORAGE_KEY}.layers.v1.${userId}.${roomId}`' in toolbar
    assert "isLayerVisible" in toolbar and "isLayerLocked" in toolbar
    assert "tool:layer-state" in toolbar
    assert "isLayerVisible" in render_loop
    assert "isLayerVisible" in measures


def test_scene_image_layer_actions_are_scoped_and_support_move_and_duplicate():
    images = (ROOT / "static/js/scene-images/scene-image-layer.js").read_text(encoding="utf-8")
    assert "selectedMovable()" in images
    assert "moveToLayer(placements, next)" in images
    assert "duplicateSelected()" in images
    assert 'layer: activeLayer' in images
    assert "isLayerLocked" in images
