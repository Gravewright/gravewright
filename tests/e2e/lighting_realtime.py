"""Light previews, editing and manual visibility while the pointer remains held."""

from io import BytesIO

from migration_closure import main
from PIL import Image, ImageChops
from playwright.sync_api import expect


def check(gm, player, data, output):
    for page in (gm, player):
        page.evaluate(
            "window.addEventListener('gravewright:map-layers', e => window.lightState=e.detail)"
        )
    gm.get_by_role("group", name="Layers", exact=True).get_by_role(
        "button", name="Lighting", exact=True
    ).click()
    print("Lighting layer", flush=True)
    gm.locator('[data-effect-tool="light"]').click()
    picker = gm.locator(".light-picker")
    for kind in ("torch", "pulse", "none"):
        picker.locator(f'[data-choice="{kind}"]').hover()
        gm.wait_for_timeout(250)
        surface = picker.locator("canvas")
        a = Image.open(BytesIO(surface.screenshot())).convert("RGB")
        gm.wait_for_timeout(400)
        b = Image.open(BytesIO(surface.screenshot())).convert("RGB")
        delta = ImageChops.difference(a, b).getbbox()
        assert bool(delta) == (kind != "none"), f"{kind}: incorrect preview animation"
        a.save(output / f"light-preview-{kind}.png")
        print("Preview:", kind, flush=True)
    picker.locator('[data-choice="none"]').click()
    gm.mouse.click(650, 420)
    gm.wait_for_function("window.lightState?.lights.length===1")
    gm.locator('[data-effect-kind="light"]').first.dblclick()
    editor = gm.locator(".light-editor")
    expect(editor).to_be_visible()
    editor.locator('[name="color"]').fill("#ff8844")
    editor.locator('[name="intensity"]').fill("0.6")
    editor.locator('[name="angle"]').fill("90")
    editor.locator('[name="rotation"]').fill("45")
    for page in (gm, player):
        page.wait_for_function(
            "window.lightState?.lights[0]?.color==='#ff8844' && lightState.lights[0].intensity===0.6 && lightState.lights[0].angle===90 && lightState.lights[0].rotation===45"
        )
    editor.get_by_role("button", name="Close", exact=True).click()
    gm.screenshot(path=str(output / "light-edited.png"))
    gm.locator("[data-map-visibility]:visible").click()
    panel = gm.locator(".game-panel--visibility")
    panel.locator('[data-mode="manual"]').click()
    panel.locator('[data-fog-action="enable"][data-value="hide_all"]').click()
    for page in (gm, player):
        page.wait_for_function(
            "window.lightState?.lighting.mode==='manual' && lightState.fog.enabled"
        )

    def pixel(page, x, y):
        picture = Image.open(
            BytesIO(page.locator(".game-board canvas").first.screenshot())
        ).convert("RGB")
        return picture.getpixel((x, y))

    assert max(pixel(player, 800, 450)) < 5
    gm.mouse.move(800, 450)
    gm.mouse.down()
    # Must reach the other browser before pointerup, not merely update a GM-only preview.
    player.wait_for_function("window.lightState?.fog.ops.length>0", timeout=5000)
    assert max(pixel(player, 800, 450)) > 20
    gm.mouse.move(1000, 450, steps=8)
    player.wait_for_function(
        "window.lightState?.fog.ops.some(op=>op.geom.center_x_cells>13)", timeout=5000
    )
    assert max(pixel(player, 990, 450)) > 20
    gm.mouse.up()
    print("Circle brush reached player during pointerdown/drag", flush=True)
    panel.locator('[data-brush="hide"]').click()
    panel.locator('[data-shape="square"]').click()
    gm.mouse.move(800, 450)
    gm.mouse.down()
    player.wait_for_function(
        "window.lightState?.fog.ops.some(op=>op.mode==='hide' && op.shape==='square')",
        timeout=5000,
    )
    assert max(pixel(player, 800, 450)) < 5
    gm.mouse.up()
    # GM opacity is local and cannot reveal the player map.
    panel.locator('[name="opacity"]').fill("0.1")
    assert max(pixel(player, 800, 450)) < 5
    panel.locator('[data-mode="dynamic"]').click()
    gm.wait_for_function("window.lightState?.lighting.mode==='dynamic'")
    # Input events alone (no change/pointerup) must publish darkness.
    panel.locator('[name="darkness"]').evaluate(
        "el=>{el.value='0.35';el.dispatchEvent(new Event('input',{bubbles:true}));}"
    )
    player.wait_for_function("window.lightState?.lighting.darkness===0.35", timeout=5000)
    gm.reload()
    gm.wait_for_function("gravewrightMaps?.board?.viewport()")
    persisted = gm.evaluate(
        "async id=>(await fetch('/api/maps/'+id+'/state')).json()", data["map"]
    )
    assert persisted["lighting"]["darkness"] == 0.35
    assert any(op["mode"] == "hide" for op in persisted["fog"]["ops"])
    print(
        "Light controls, live circle/square fog, local opacity, darkness input and reload passed",
        flush=True,
    )


if __name__ == "__main__":
    main(check)
