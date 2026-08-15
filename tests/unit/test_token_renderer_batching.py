from pathlib import Path


SOURCE = (Path(__file__).resolve().parents[2] / "static/js/board/pixi/pixi-token-layer.js").read_text(encoding="utf-8")


def test_token_geometry_is_dirty_only_and_position_uses_transform() -> None:
    assert "node.container.position.set(wx, wy)" in SOURCE
    assert "if (node.visualKey !== visualKey)" in SOURCE
    assert SOURCE.index("if (node.visualKey !== visualKey)") < SOURCE.index("g.clear();", SOURCE.index("if (node.visualKey !== visualKey)"))


def test_removed_token_nodes_are_destroyed_not_retained_forever() -> None:
    assert "if (!existing.has(id))" in SOURCE
    assert "node.container.destroy({ children: true })" in SOURCE
    assert "board.tokenNodes.delete(id)" in SOURCE


def test_transparent_plain_tokens_use_contiguous_sprite_fast_path() -> None:
    layers = (Path(__file__).resolve().parents[2] / "static/js/board/pixi/pixi-board-layers.js").read_text(encoding="utf-8")
    assert "board.tokenSpriteLayer" in layers
    assert 'token.asset_render_mode === "transparent"' in SOURCE
    assert "this._renderFastToken" in SOURCE
    assert "board.fastTokenSprites" in SOURCE


def test_lighting_submits_only_viewport_relevant_sources() -> None:
    lighting = (Path(__file__).resolve().parents[2] / "static/js/board/pixi/pixi-lighting-layer.js").read_text(encoding="utf-8")
    assert "const visibleLights = (lighting.lights || []).filter" in lighting
    assert "litAreas.map(flatten), visibleLights" in lighting
    assert "if (!classic) visibleLights.forEach" in lighting
