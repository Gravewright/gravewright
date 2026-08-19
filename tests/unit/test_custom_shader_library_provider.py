from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ADDON = ROOT / "data/packages/addons/my-custom-shader"


def test_bridge_is_capability_gated_and_core_owned() -> None:
    registry = json.loads((ROOT / "app/engine/sdk/capabilities.json").read_text(encoding="utf-8"))
    methods = registry["capabilities"]["scene.shaders.customLibrary"]["methods"]
    assert methods == [
        "scene.shaders.customLibrary.registerProvider",
        "scene.shaders.customLibrary.openEditor",
        "scene.shaders.customLibrary.preview",
        "scene.shaders.customLibrary.clearPreview",
        "scene.shaders.customLibrary.use",
    ]
    runtime = (ROOT / "static/js/sdk/gravewright-sdk.js").read_text(encoding="utf-8")
    assert all(f'requireCap("{method}")' in runtime for method in methods)
    assert "compile" not in " ".join(methods).lower()
    assert "rawApply" not in runtime


def test_consumer_uses_only_sdk_and_has_no_private_shader_access() -> None:
    source = (ADDON / "assets/my-custom-shader.js").read_text(encoding="utf-8")
    forbidden = ("/game/", "WebSocket", "PIXI", "GravewrightLighting", "GravewrightShaderEditor", "querySelector(\"[data-shader")
    assert not [token for token in forbidden if token in source]
    assert "sdk.scene.shaders.customLibrary.registerProvider" in source
    assert "sdk.scene.shaders.customLibrary.openEditor" in source
    assert "sdk.scene.shaders.customLibrary.use" in source


def test_library_storage_is_managed_global_and_gm_only_at_runtime() -> None:
    manifest = json.loads((ADDON / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["storage"]["sqlite"]["location"] == "gravewright-managed"
    assert manifest["storage"]["sqlite"]["scopes"] == ["global"]
    runtime = (ROOT / "app/engine/sdk/package_storage_runtime.py").read_text(encoding="utf-8")
    assert 'if scope == "global":\n        return ctx.is_gm' in runtime


def test_export_format_and_definition_are_versioned_and_bounded() -> None:
    source = (ADDON / "assets/my-custom-shader.js").read_text(encoding="utf-8")
    core = (ROOT / "static/js/lighting/shader-editor.js").read_text(encoding="utf-8")
    assert 'format:"gravewright-custom-shader-library-entry",version:1' in source
    assert 'const MAX_DEFINITION_BYTES = 40000' in core
    assert 'const CUSTOM_VERSION = 1' in core
    assert "CUSTOM_SHADER_INVALID" in core
    assert '["SELECT", "TEXTAREA"].includes(input.tagName)' in core
