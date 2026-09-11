"""Effects integration with real WebGL, GM/player sockets and an isolated database."""

import re
import sys
from io import BytesIO

from effect_pixels import assert_preview_pixels
from migration_closure import main
from PIL import Image, ImageChops
from playwright.sync_api import expect


def check(gm, player, data, output):
    for page in (gm, player):
        page.evaluate(
            "window.addEventListener('gravewright:map-layers', e => window.effectState = e.detail)"
        )

    def state():
        return gm.evaluate(
            "async id => (await fetch('/api/maps/'+id+'/state')).json()", data["map"]
        )

    def wait(expression):
        print("Waiting:", expression, flush=True)
        gm.wait_for_function(
            "async ([id,expression]) => {const s=await (await fetch('/api/maps/'+id+'/state')).json();return new Function('s','return '+expression)(s)}",
            arg=[data["map"], expression],
            timeout=15000,
        )

    def profile(page, name):
        page.locator(".game-menubar__logo").click()
        page.get_by_role("button", name="Preferences", exact=True).click()
        page.locator(f'[data-render-choice="{name}"]').click()
        expect(page.locator("html")).to_have_attribute("data-render-profile", name)
        page.keyboard.press("Escape")
        expect(page.locator(".house-menu-scrim")).to_be_hidden()

    # Original defaults, followed by an actual UI selection on each device.
    expect(gm.locator("html")).to_have_attribute("data-render-profile", "performance")
    profile(gm, "quality")
    expect(player.locator("html")).to_have_attribute(
        "data-render-profile", "performance"
    )
    profile(player, "balanced")
    profile(gm, "performance")
    gm.get_by_role("group", name="Layers", exact=True).get_by_role(
        "button", name="Effects", exact=True
    ).click()
    gm.get_by_role("button", name="Particles", exact=True).click()
    picker = gm.locator(".effect-picker")
    expect(picker).to_be_visible()
    expect(gm.get_by_role("button", name="Particles", exact=True)).to_have_attribute(
        "aria-pressed", "true"
    )
    # A non-Escape key must not close the picker (native modifier regression).
    picker.locator(".effect-picker__particles button").first.focus()
    gm.keyboard.press("ArrowRight")
    expect(picker).to_be_visible()
    expect(picker.locator(".effect-picker__particles button")).to_have_count(12)
    particle_preview_count = 0 if "--skip-particle-previews" in sys.argv else 12
    for index in range(particle_preview_count):
        button = picker.locator(".effect-picker__particles button").nth(index)
        button.hover()
        expect(picker.locator(".effect-preview__label")).not_to_have_text(
            "Preview unavailable"
        )
        assert_preview_pixels(gm, f"particle-{index}")
    picker.locator(".effect-picker__particles button").nth(1).click()
    gm.mouse.click(450, 330)
    wait("s.particles.length===1 && s.particles[0].kind==='ember'")
    gm.locator('[data-effect-kind="particle"]').first.dblclick()
    editor = gm.locator(".effect-editor")
    expect(editor).to_be_visible()
    editor.locator("select").select_option("rain")
    wait("s.particles[0].kind==='rain'")
    editor.locator("input[type=range]").nth(2).fill("8")
    wait("s.particles[0].scale===8")
    editor.locator("input[type=checkbox]").uncheck()
    wait("s.particles[0].enabled===false")
    editor.locator("input[type=checkbox]").check()
    wait("s.particles[0].enabled===true")
    editor.locator(".effect-editor__header button").click()

    profile(gm, "performance")
    gm.get_by_role("button", name="Shaders", exact=True).click()
    expect(picker).to_be_visible()
    presets = picker.locator("[data-shader-preset]")
    expect(presets).to_have_count(50)
    print("Shader picker", flush=True)
    preview_count = 1 if "--controls-only" in sys.argv else 50
    preview_start = int(sys.argv[sys.argv.index("--shader-start") + 1]) if "--shader-start" in sys.argv else 0
    assert 0 <= preview_start < preview_count
    for index in range(preview_start, preview_count):
        print("Preset:", index, flush=True)
        name = presets.nth(index).locator("strong").inner_text()
        presets.nth(index).hover()
        expect(picker.locator(".effect-preview__label")).to_have_text(name)
        assert_preview_pixels(
            gm, presets.nth(index).get_attribute("data-shader-preset")
        )
    if "--previews-only" in sys.argv:
        print(
            f"Shader previews {preview_start}–{preview_count - 1} contain visible pixels in Performance.",
            flush=True,
        )
        return
    presets.first.click()
    gm.mouse.click(750, 400)
    wait("s.shaders.length===1")
    gm.locator('[data-effect-kind="shader"]').first.dblclick()
    expect(gm.locator(".effect-editor--shader")).to_be_visible()
    editor.get_by_role("checkbox", name="Entire scene", exact=True).check()
    editor.locator(".effect-editor__actions button").last.click()
    wait("s.shaders[0].radius===0")
    editor.get_by_role("checkbox", name="Entire scene", exact=True).uncheck()
    editor.get_by_role("slider", name=re.compile("^Opacity")).fill("0.5")
    editor.get_by_role("slider", name=re.compile("^Receive lighting")).fill("0.5")
    editor.locator(".effect-editor__actions button").last.click()
    wait(
        "s.shaders[0].radius===8 && s.shaders[0].opacity===0.5 && s.shaders[0].light_response===0.5"
    )
    source = gm.locator("#effect-shader-source")
    original = source.input_value()
    source.fill("this is invalid GLSL")
    editor.locator(".effect-editor__actions button").last.click()
    expect(editor.locator("[role=status]")).not_to_be_empty()
    assert state()["shaders"][0]["source"] == original
    # Valid text above the former, incompatible 16K server limit.
    source.fill(original + "\n/*" + "x" * 17000 + "*/")
    editor.locator(".effect-editor__actions button").last.click()
    wait("s.shaders[0].source.length>17000")
    editor.locator(".effect-editor__header button").click()

    # Mixed selection, clipboard, rotation and deletion use the original gestures.
    gm.locator('[data-effect-kind="particle"]').first.click(modifiers=["Shift"])
    gm.keyboard.press("Control+c")
    gm.mouse.move(1000, 600)
    gm.keyboard.press("Control+v")
    wait("s.particles.length===2 && s.shaders.length===2")
    gm.keyboard.down("Shift")
    gm.mouse.wheel(0, 100)
    gm.keyboard.up("Shift")
    wait("s.particles.some(p=>p.rotation===15) && s.shaders.some(p=>p.rotation===15)")
    gm.keyboard.press("Delete")
    wait("s.particles.length===1 && s.shaders.length===1")

    profile(gm, "quality")
    # Verify each renderer independently, on both peers, through real socket updates.
    rows = state()

    def enabled(area, value):
        identity = "emitter_id" if area == "particles" else "shader_id"
        gm.evaluate(
            """p => gravewrightRealtime.mapCommand('objects', p)""",
            {
                "mapId": data["map"],
                "area": area,
                "action": "update",
                "data": {identity: rows[area][0]["id"], "enabled": value},
            },
        )

    for active in ("shaders", "particles"):
        enabled("particles", active == "particles")
        enabled("shaders", active == "shaders")
        for page in (gm, player):
            page.wait_for_function(
                "active => window.effectState?.particles[0]?.enabled === (active==='particles') && window.effectState?.shaders[0]?.enabled === (active==='shaders')",
                arg=active,
            )
            page.wait_for_timeout(300)
            canvas = page.locator(".game-board canvas").first
            a = Image.open(BytesIO(canvas.screenshot())).convert("RGB")
            page.wait_for_timeout(300)
            b = Image.open(BytesIO(canvas.screenshot())).convert("RGB")
            assert ImageChops.difference(a, b).getbbox(), (
                f"{active} did not animate on the board"
            )
    enabled("shaders", True)
    profile(gm, "balanced")
    gm.reload()
    gm.wait_for_function("window.gravewrightMaps?.board?.viewport()")
    expect(gm.locator("html")).to_have_attribute("data-render-profile", "balanced")
    assert len(state()["particles"]) == len(state()["shaders"]) == 1
    gm.screenshot(path=str(output / "effects.png"))
    print(
        f"Effects passed: {particle_preview_count} particle previews, {preview_count - preview_start} shader previews (indices {preview_start}–{preview_count - 1}), editing, GLSL validation, GM/player animation and persistent local quality.",
        flush=True,
    )


if __name__ == "__main__":
    main(check)
