"""Custom GLSL and actual range/wall/door clipping in both browser renderers."""

from io import BytesIO

from migration_closure import main
from PIL import Image


def check(gm, player, data, output):
    for page in (gm, player):
        page.evaluate(
            "window.addEventListener('gravewright:map-layers', e => window.geometryState=e.detail)"
        )

    def command(area, action, values):
        return gm.evaluate(
            "p=>gravewrightRealtime.mapCommand('objects',p)",
            {"mapId": data["map"], "area": area, "action": action, "data": values},
        )

    gm.get_by_role("group", name="Layers", exact=True).get_by_role(
        "button", name="Effects", exact=True
    ).click()
    gm.get_by_role("button", name="Shaders", exact=True).click()
    gm.locator(".effect-picker__custom").click()
    gm.mouse.click(850, 400)
    gm.locator('[data-effect-kind="shader"]').first.dblclick()
    editor = gm.locator(".effect-editor")
    editor.locator("#effect-shader-source").fill(
        "void main(){finalColor=vec4(1.0,0.0,0.0,1.0);}"
    )
    editor.get_by_role("button", name="Save", exact=True).click()
    gm.wait_for_function(
        "geometryState?.shaders[0]?.source.includes('1.0,0.0,0.0,1.0')"
    )
    editor.get_by_role("button", name="Close", exact=True).click()
    shader = gm.evaluate("geometryState.shaders[0].id")
    command(
        "shaders",
        "update",
        {
            "shader_id": shader,
            "x": 400,
            "y": 400,
            "radius": 3,
            "opacity": 1,
            "light_response": 0,
            "light_emission": 0,
            "blend_mode": "normal",
        },
    )
    for page in (gm, player):
        page.wait_for_function(
            "geometryState?.shaders[0]?.x===400 && geometryState.shaders[0].radius===3"
        )

    def pixels(label, beyond_wall):
        for role, page in (("gm", gm), ("player", player)):
            page.wait_for_timeout(400)
            canvas = page.locator(".game-board canvas").first
            picture = Image.open(BytesIO(canvas.screenshot())).convert("RGB")
            view = page.evaluate("gravewrightMaps.board.viewport()")

            def red(x, y, picture=picture, view=view):
                r, g, b = picture.getpixel(
                    (
                        round(x * view["scale"] + view["x"]),
                        round(y * view["scale"] + view["y"]),
                    )
                )
                return r > 220 and g < 30 and b < 30

            assert red(430, 430), (label, role, "source side must render")
            assert red(530, 430) == beyond_wall, (label, role, "wall clipping")
            assert not red(800, 430), (label, role, "range clipping")
            picture.save(output / f"effect-geometry-{label}-{role}.png")

    pixels("range", True)
    command(
        "walls",
        "create",
        {
            "kind": "door",
            "x1": 480,
            "y1": 200,
            "x2": 480,
            "y2": 650,
            "door_state": "closed",
        },
    )
    for page in (gm, player):
        page.wait_for_function("geometryState?.walls.length===1")
    pixels("closed-door", False)
    wall = gm.evaluate("geometryState.walls[0].id")
    command("walls", "door", {"wall_id": wall, "door_state": "open"})
    for page in (gm, player):
        page.wait_for_function("geometryState?.walls[0]?.door_state==='open'")
    pixels("open-door", True)
    print(
        "Custom GLSL, range clipping and closed/open door pixels passed for GM and player",
        flush=True,
    )


if __name__ == "__main__":
    main(check)
