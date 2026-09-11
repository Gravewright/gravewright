"""Actual light blending, wall/door occlusion and animated board pixels."""

from io import BytesIO

from migration_closure import main
from PIL import Image, ImageChops


def check(gm, player, data, output):
    for page in (gm, player):
        page.evaluate(
            "window.addEventListener('gravewright:map-layers',e=>window.lightPixels=e.detail)"
        )

    def command(area, action, values):
        gm.evaluate(
            "p=>gravewrightRealtime.mapCommand('objects',p)",
            {"mapId": data["map"], "area": area, "action": action, "data": values},
        )

    def picture(page):
        page.wait_for_timeout(300)
        return Image.open(
            BytesIO(page.locator(".game-board canvas").first.screenshot())
        ).convert("RGB")

    before = [picture(page) for page in (gm, player)]
    command(
        "lights",
        "create",
        {
            "x": 600,
            "y": 400,
            "bright_radius": 2,
            "dim_radius": 4,
            "intensity": 0.9,
            "color": "#ff3300",
            "animation": "none",
        },
    )
    for i, page in enumerate((gm, player)):
        page.wait_for_function("window.lightPixels?.lights.length===1")
        after = picture(page)
        for point in ((650, 430), (750, 430)):
            a, b = before[i].getpixel(point), after.getpixel(point)
            assert all(y >= x - 1 for x, y in zip(a, b)), (
                "Light must add to underlying colors",
                a,
                b,
            )
            assert b[0] > a[0] + 5, ("Light must brighten the map", a, b)
        after.save(output / f"light-additive-{i}.png")
    light_id = gm.evaluate("lightPixels.lights[0].id")
    command(
        "walls",
        "create",
        {
            "kind": "door",
            "x1": 700,
            "y1": 100,
            "x2": 700,
            "y2": 700,
            "door_state": "closed",
        },
    )
    for i, page in enumerate((gm, player)):
        page.wait_for_function("window.lightPixels?.walls.length===1")
        after = picture(page)
        assert (
            max(
                abs(a - b)
                for a, b in zip(
                    before[i].getpixel((750, 430)), after.getpixel((750, 430))
                )
            )
            < 3
        )
    wall_id = gm.evaluate("lightPixels.walls[0].id")
    command("walls", "door", {"wall_id": wall_id, "door_state": "open"})
    for i, page in enumerate((gm, player)):
        page.wait_for_function("window.lightPixels?.walls[0]?.door_state==='open'")
        assert (
            picture(page).getpixel((750, 430))[0]
            > before[i].getpixel((750, 430))[0] + 5
        )
    print("Additive lights and closed/open door pixels passed on GM/player", flush=True)
    for kind in ("torch", "pulse"):
        command("lights", "update", {"light_id": light_id, "animation": kind})
        for page in (gm, player):
            page.wait_for_function(
                "kind=>window.lightPixels?.lights[0]?.animation===kind", arg=kind
            )
            a = picture(page).crop((400, 200, 850, 650))
            page.wait_for_timeout(400)
            b = picture(page).crop((400, 200, 850, 650))
            assert ImageChops.difference(a, b).getbbox(), (
                f"{kind} must animate on the board"
            )
        print("Board animation:", kind, flush=True)


if __name__ == "__main__":
    main(check)
