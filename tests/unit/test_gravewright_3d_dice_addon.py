from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.engine.sdk.package_doctor_service import PackageDoctorService
from app.engine.sdk.package_asset_service import _CONTENT_TYPES
from app.engine.sdk.package_loader import load_package
from app.engine.sdk.package_manifest_validator import validate_manifest


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "data/packages/addons/gravewright-3d-dice"
CORE = PACKAGE / "scripts/dice-core.js"
RENDERER = PACKAGE / "src/dice-renderer.js"


def _node(expression: str):
    script = f"const core=require({json.dumps(str(CORE))});console.log(JSON.stringify({expression}));"
    completed = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
    return json.loads(completed.stdout)


def test_manifest_is_sdk1_addon_with_least_privilege():
    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    assert validate_manifest(manifest).ok
    assert manifest["id"] == "gravewright-3d-dice"
    assert manifest["kind"] == "addon"
    assert set(manifest["capabilities"]) == {
        "assets.scripts", "assets.styles", "events.subscribe", "chat.read",
        "ui.slots", "settings",
    }
    assert {setting["key"] for setting in manifest["settings"]} == {"dice_color", "font_color"}
    loaded = load_package(PACKAGE, expected_id="gravewright-3d-dice", expected_kind_root="addons")
    assert PackageDoctorService()._audit_capabilities("gravewright-3d-dice", loaded) == []


def test_renderer_and_styles_are_module_owned_lazy_assets() -> None:
    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    main = (PACKAGE / "scripts/main.js").read_text(encoding="utf-8")
    game = manifest["entrypoints"]["game"]

    assert game["scripts"] == ["scripts/dice-core.js", "scripts/main.js"]
    assert game["styles"] == []
    assert "scripts/dice-renderer.js" not in game["scripts"]
    assert 'packageAsset("scripts/dice-renderer.js")' in main
    assert 'packageAsset("styles/gravewright-3d-dice.css")' in main
    assert "async function ensureRenderer()" in main
    assert "new loadedRenderer.DiceRenderer(overlayHost)" in main


def test_structured_roll_groups_create_only_physical_dice():
    result = _node("core.visualDice([{faces:20,results:[17],subtotal:17},{faces:8,results:[3,6],subtotal:9},{faces:6,results:[4],subtotal:4}])")
    assert result == [
        {"faces": 20, "result": 17, "percentile": None},
        {"faces": 8, "result": 3, "percentile": None},
        {"faces": 8, "result": 6, "percentile": None},
        {"faces": 6, "result": 4, "percentile": None},
    ]


def test_supported_dice_and_authoritative_final_orientation_are_deterministic():
    result = _node("[4,6,8,10,12,20].map(f=>({f,d:core.visualDice([{faces:f,results:[f],subtotal:f}])[0],a:core.finalOrientation(f,f),b:core.finalOrientation(f,f)}))")
    assert [item["f"] for item in result] == [4, 6, 8, 10, 12, 20]
    assert all(item["d"]["result"] == item["f"] for item in result)
    assert all(item["a"] == item["b"] for item in result)


def test_every_die_uses_the_correct_polyhedron_topology():
    source = RENDERER.read_text(encoding="utf-8")
    assert 'import {DICE_MODELS, DICE_SHAPE} from "./upstream/DiceModels.js"' in source
    assert "new THREE.BufferGeometryLoader().parse" in source
    assert "upstreamCannonShape" in source


def test_tray_uses_a_top_down_camera_and_matching_octagonal_physics():
    source = RENDERER.read_text(encoding="utf-8")
    styles = (PACKAGE / "styles/gravewright-3d-dice.css").read_text(encoding="utf-8")
    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    assert "THREE.OrthographicCamera" in source
    assert "this.camera.position.set(0, 14, 0)" in source
    assert "TRAY_CORNER_CUT_X = 1.08" in source
    assert "object.collisionRadius * 1.03" in source
    assert "dice-tray-top-down.png" in styles
    assert manifest["provides"]["assets"]["images"][0]["path"] == "assets/dice-tray-top-down.png"


def test_results_are_mapped_without_a_corrective_final_spin():
    source = RENDERER.read_text(encoding="utf-8")
    assert "targetQuaternion" not in source
    assert "prepareFaceSwaps" in source
    assert "object.mesh.quaternion.multiply(object.faceSwap)" in source
    assert "material.map =" not in source
    assert "DICE_MODELS" in source
    assert "const animationStart = performance.now()" in source
    assert "start: animationStart" in source
    assert "anchor.shapeVertexIndices.forEach" in source
    assert "object.d4Vertices[object.targetIndex]" in source
    assert "vertexIndex + 1" in source
    assert "const world = new CANNON.World" in source
    assert "step % 20 === 19" in source


def test_dice_use_upstream_resin_pbr_map_and_high_resolution_numerals():
    source = RENDERER.read_text(encoding="utf-8")
    styles = (PACKAGE / "styles/gravewright-3d-dice.css").read_text(encoding="utf-8")
    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    assert "roughnessMap_resin.webp" in source
    assert "canvas.width = 1024" in source
    assert "THREE.LinearMipmapLinearFilter" in source
    assert "restD4OnFloor" in source
    assert "const numeralTextures = new Map()" in source
    assert "2.05 / Math.sqrt" in source
    assert 'label === "6" || label === "9"' in source
    assert "let fontSize = (label.length > 1 ? 600 : 720) * shapeScale" in source
    assert "DSN_FONT_SCALE = {4: 1, 6: 1.3, 8: 1.1, 10: 1, 12: 1.1, 20: 1}" in source
    assert "context.measureText(label).width" in source
    assert "context.font = `900 ${fontSize}px Inter, sans-serif`" in source
    assert "document.fonts.load" in source
    assert "InterVariable.woff2" in styles
    assert (PACKAGE / "assets/fonts/InterVariable.woff2").is_file()
    assert "SIL OPEN FONT LICENSE" in (PACKAGE / "assets/fonts/Inter-LICENSE.txt").read_text(encoding="utf-8")
    assert manifest["provides"]["assets"]["fonts"][0]["path"] == "assets/fonts/InterVariable.woff2"
    assert _CONTENT_TYPES[".woff2"] == "font/woff2"
    assert any(asset["path"] == "assets/roughnessMap_resin.webp" for asset in manifest["provides"]["assets"]["images"])


def test_percentile_is_structurally_split_into_tens_and_ones():
    assert _node("core.visualDice([{faces:100,results:[73,100],subtotal:173}])") == [
        {"faces": 10, "result": 70, "percentile": "tens"},
        {"faces": 10, "result": 3, "percentile": "ones"},
        {"faces": 10, "result": 0, "percentile": "tens"},
        {"faces": 10, "result": 0, "percentile": "ones"},
    ]


def test_visual_batch_is_bounded_to_fifty_dice():
    assert _node("core.visualDice([{faces:6,results:Array(100).fill(4),subtotal:400}]).length") == 50


def test_numeral_color_meets_contrast_threshold_across_palette():
    palette = ["#08090c", "#f8fafc", "#ef4444", "#22c55e", "#3b82f6", "#fde047", "#8b5cf6", "#808080"]
    result = _node(f"{json.dumps(palette)}.map(base=>({{base,numeral:core.numeralColor(base),ratio:core.contrastRatio(base,core.numeralColor(base))}}))")
    assert all(item["ratio"] >= 4.5 for item in result), result
    assert len({item["numeral"] for item in result}) > 1


def test_invalid_color_uses_documented_neutral_fallback():
    assert _node("[core.normalizeColor('not-a-color'),core.normalizeColor('#8B5CF6')]") == ["#6d7280", "#8b5cf6"]


def test_addon_uses_only_documented_sdk_and_its_owned_dom_surface():
    sources = "\n".join(path.read_text(encoding="utf-8") for path in (PACKAGE / "scripts").glob("*.js"))
    forbidden = [
        "app.", "engine.", "internal/", "private/", 'fetch("/api/internal',
        "WebSocket(", "querySelector(", "GravewrightCore", "app.renderer",
    ]
    assert [token for token in forbidden if token in sources] == []
    assert "sdk.chat.get" in sources
    assert "sdk.settings.get" in sources
    assert "sdk.settings.set" in sources
    assert 'sdk.events.on("chat.created"' in sources
    assert 'sdk.ui.slots.register("board.overlay"' in sources
    assert 'sdk.ui.slots.register("settings.modules"' in sources


def test_configured_body_and_font_colors_are_forwarded_to_the_renderer():
    main = (PACKAGE / "scripts/main.js").read_text(encoding="utf-8")
    renderer = RENDERER.read_text(encoding="utf-8")
    assert 'sdk.settings.get("dice_color"' in main
    assert 'sdk.settings.get("font_color"' in main
    assert "dice, color, fontColor" in main
    assert "sequence.fontColor || Core.numeralColor(sequence.color)" in renderer


def test_lifecycle_has_bounded_queue_dedup_and_complete_cleanup():
    main = (PACKAGE / "scripts/main.js").read_text(encoding="utf-8")
    renderer = RENDERER.read_text(encoding="utf-8")
    assert "seenOrder.length > 500" in main
    assert "this.queue.length >= 32" in renderer
    assert "this.active.length < 8" in renderer
    assert "cancelAnimationFrame(this.frame)" in renderer
    assert "clearTimeout(this.wakeTimer)" in renderer
    assert "object.physicsReleased = true" in renderer
    assert "this.queue.length = 0" in renderer
    assert "this.active.length = 0" in renderer
    assert "this.reducedMotion ? 3500 : 3300" in renderer
    assert "allBatchesDismissed" in renderer
    assert "batch.motion * 0.76 + batch.hold" in renderer
    assert ".gravewright-3d-dice-tray[hidden]" in (PACKAGE / "styles/gravewright-3d-dice.css").read_text(encoding="utf-8")
    assert "this.resizeObserver.disconnect()" in renderer
    assert "runtime?.destroy()" in main
