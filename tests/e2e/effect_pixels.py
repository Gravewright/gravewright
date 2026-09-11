"""Visible preview pixels and animation in the default profile (not just GLSL compilation)."""

from io import BytesIO

from migration_closure import main
from PIL import Image, ImageChops
from playwright.sync_api import expect


def assert_preview_pixels(gm, label, output=None, *, animated=False):
    surface = gm.locator(".effect-preview__surface")
    canvas = surface.locator("canvas")
    gm.wait_for_timeout(200)
    assert canvas.evaluate(
        "el => el.width === Math.round(el.parentElement.clientWidth * Math.min(devicePixelRatio, 2)) && el.height === Math.round(el.parentElement.clientHeight * Math.min(devicePixelRatio, 2))"
    ), f"{label}: canvas dimensions were reset by a DOM update"
    before = Image.open(BytesIO(surface.screenshot())).convert("RGB")
    if animated:
        gm.wait_for_timeout(300)
        after = Image.open(BytesIO(surface.screenshot())).convert("RGB")
    canvas.evaluate("el => el.style.visibility='hidden'")
    empty = Image.open(BytesIO(surface.screenshot())).convert("RGB")
    canvas.evaluate("el => el.style.visibility=''")
    if output:
        before.save(output / ("preview-" + label + ".png"))
    assert ImageChops.difference(before, empty).getbbox(), (
        f"{label}: preview canvas is blank"
    )
    if animated:
        assert ImageChops.difference(before, after).getbbox(), (
            f"{label}: preview is frozen"
        )
    print("Visible preview pixels:", label, flush=True)


def check(gm, player, data, output):
    for page in (gm, player):
        page.evaluate(
            "window.addEventListener('gravewright:map-layers', e => window.effectPixelsState = e.detail)"
        )
    expect(gm.locator("html")).to_have_attribute("data-render-profile", "performance")
    gm.get_by_role("group", name="Layers", exact=True).get_by_role(
        "button", name="Effects", exact=True
    ).click()

    gm.get_by_role("button", name="Shaders", exact=True).click()
    picker = gm.locator(".effect-picker")
    for preset in ("orb-1", "fog-3", "liquid-3"):
        picker.locator(f'[data-shader-preset="{preset}"]').hover()
        assert_preview_pixels(gm, preset, output, animated=True)
    picker.locator('[data-shader-preset="liquid-3"]').click()
    gm.mouse.click(650, 400)
    gm.wait_for_function(
        "async id => (await (await fetch('/api/maps/'+id+'/state')).json()).shaders.length===1",
        arg=data["map"],
    )
    # The newly placed shader must animate without first changing preferences.
    for page in (gm, player):
        page.wait_for_timeout(500)
        board = page.locator(".game-board canvas").first
        before = Image.open(BytesIO(board.screenshot())).convert("RGB")
        page.wait_for_timeout(400)
        after = Image.open(BytesIO(board.screenshot())).convert("RGB")
        assert ImageChops.difference(before, after).getbbox(), (
            "Default scene renderer is static"
        )
    gm.get_by_role("button", name="Particles", exact=True).click()
    for index in (1, 4):
        picker.locator(".effect-picker__particles button").nth(index).hover()
        assert_preview_pixels(gm, "particle-" + str(index), output, animated=True)
    picker.locator(".effect-picker__particles button").nth(1).click()
    gm.mouse.click(420, 350)
    gm.wait_for_function(
        "async id => (await (await fetch('/api/maps/'+id+'/state')).json()).particles.length===1",
        arg=data["map"],
    )
    gm.evaluate(
        """async mapId => {
        const state=await (await fetch('/api/maps/'+mapId+'/state')).json();
        await gravewrightRealtime.mapCommand('objects', {mapId,area:'shaders',action:'update',data:{shader_id:state.shaders[0].id,enabled:false}});
    }""",
        data["map"],
    )
    for page in (gm, player):
        page.wait_for_function(
            "effectPixelsState?.shaders[0]?.enabled===false && effectPixelsState?.particles.length===1"
        )
        page.wait_for_timeout(300)
        board = page.locator(".game-board canvas").first
        before = Image.open(BytesIO(board.screenshot())).convert("RGB")
        page.wait_for_timeout(400)
        after = Image.open(BytesIO(board.screenshot())).convert("RGB")
        assert ImageChops.difference(before, after).getbbox(), (
            "Default particle renderer is static"
        )
    print(
        "Default profile: visible animated shader/particle previews and independent GM/player shader and particle rendering passed.",
        flush=True,
    )


if __name__ == "__main__":
    main(check)
