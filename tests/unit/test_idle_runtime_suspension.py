from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_map_render_loop_emits_view_changes_for_event_driven_consumers() -> None:
    render_loop = (ROOT / "static/js/map/render-loop/map-render-loop.js").read_text(encoding="utf-8")

    assert 'new CustomEvent("vtt:map-view-changed"' in render_loop
    assert 'sceneChanged: flags.has("scene")' in render_loop


def test_scene_images_have_no_permanent_poll_or_animation_loop() -> None:
    images = (ROOT / "static/js/scene-images/scene-image-layer.js").read_text(encoding="utf-8")

    assert "startCompositionFollow" not in images
    assert "startTicker" not in images
    assert 'document.addEventListener("vtt:map-view-changed"' in images


def test_sdk_scene_objects_follow_map_events_instead_of_fifty_ms_timer() -> None:
    sdk = (ROOT / "static/js/sdk/gravewright-sdk.js").read_text(encoding="utf-8")

    assert "setInterval(position, 50)" not in sdk
    assert 'document.addEventListener("vtt:map-view-changed", onMapViewChanged)' in sdk
    assert 'window.setTimeout(render, hasLiveClock ? 1000 : 60000)' in sdk
    assert "setInterval(render,1000)" not in sdk
