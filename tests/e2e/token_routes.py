"""Real Ctrl gestures, A* wall detours, route action and game tools."""

from migration_closure import main
from playwright.sync_api import expect


def check(gm, player, data, output):
    actor = gm.evaluate(
        "()=>gravewrightRealtime.resourceCommand('actors','actor.create',{name:'Route hero'})"
    )
    gm.evaluate(
        "p=>gravewrightRealtime.resourceCommand('actors','actor.permissions',{id:p.id,permissions:{[p.player]:'owner'}})",
        {"id": actor["id"], "player": data["player_id"]},
    )
    gm.evaluate(
        "p=>gravewrightRealtime.resourceCommand('tokens','place',p)",
        {"mapId": data["map"], "actorId": actor["id"], "gridX": 3, "gridY": 3},
    )
    gm.evaluate(
        "p=>gravewrightRealtime.mapCommand('objects',p)",
        {
            "mapId": data["map"],
            "area": "walls",
            "action": "create",
            "data": {
                "kind": "door",
                "x1": 385,
                "y1": 70,
                "x2": 385,
                "y2": 350,
                "door_state": "closed",
            },
        },
    )
    hero = player.get_by_role("button", name="Token: Route hero", exact=True)
    expect(hero).to_be_visible(timeout=15000)
    hero.click()
    player.keyboard.down("Control")
    for x, y in [(245, 455), (525, 455), (525, 245)]:
        player.mouse.click(x, y)
    route = player.locator(".token-workspace__route")
    expect(route.locator("circle")).to_have_count(3)
    expect(route.get_by_text("Your route:", exact=False)).to_be_visible()
    expect(route.get_by_text("Suggested:", exact=False)).to_be_visible()
    expect(
        route.get_by_role("button", name="Use suggested route", exact=True)
    ).to_be_visible()
    player.screenshot(path=str(output / "ctrl-route-suggestion.png"))
    before = hero.bounding_box()
    # Planning never moves the token; choosing the suggestion still waits for Ctrl release.
    assert abs(before["x"] - 210) < 2
    route.get_by_role("button", name="Use suggested route", exact=True).click()
    expect(
        route.get_by_role("button", name="Use suggested route", exact=True)
    ).to_have_count(0)
    points = route.locator("polyline").first.get_attribute("points")
    assert len(points.split()) > 2, "Closed door requires a detour"
    player.keyboard.up("Control")
    player.wait_for_function(
        "async p=>{const s=await(await fetch('/api/containers/'+p.campaign+'/maps/'+p.map+'/tokens')).json();return s.tokens[0]?.gridX===7 && s.tokens[0]?.gridY===3}",
        arg=data,
    )
    expect(route).to_have_count(0)
    expect(
        gm.get_by_role("button", name="Token: Route hero", exact=True)
    ).to_have_attribute("x", "490")
    print(
        "Multiple Ctrl points, wall-aware A*, CTA, player movement and GM delivery passed",
        flush=True,
    )
    hero.click()
    player.keyboard.down("Control")
    player.mouse.click(665, 245)
    player.mouse.click(665, 385)
    expect(route.locator("circle")).to_have_count(2)
    player.keyboard.press("Escape")
    player.keyboard.up("Control")
    expect(route).to_have_count(0)
    assert abs(hero.bounding_box()["x"] - 490) < 2
    # A blocked straight route still offers a safe, longer detour.
    hero.click()
    player.keyboard.down("Control")
    player.mouse.click(245, 245)
    expect(route.locator("circle")).to_have_count(1)
    expect(route.get_by_text("Route avoids walls", exact=True)).to_be_visible()
    wall_id = gm.evaluate(
        "async id=>(await(await fetch('/api/maps/'+id+'/state')).json()).walls[0].id",
        data["map"],
    )

    def door(value):
        gm.evaluate(
            "p=>gravewrightRealtime.mapCommand('objects',p)",
            {
                "mapId": data["map"],
                "area": "walls",
                "action": "door",
                "data": {"wall_id": wall_id, "door_state": value},
            },
        )

    door("open")
    expect(route.locator("circle")).to_have_count(1)
    expect(
        route.get_by_role("button", name="Use suggested route", exact=True)
    ).to_have_count(0)
    door("closed")
    expect(
        route.get_by_role("button", name="Use suggested route", exact=True)
    ).to_be_visible()
    player.keyboard.press("Escape")
    player.keyboard.up("Control")
    print("Longer safe detour and live door changes passed", flush=True)
    # The routing surface must relinquish input to the actual game tools.
    gm.get_by_role("button", name="Measure", exact=True).first.click()
    expect(gm.locator(".measure-panel")).to_be_visible()
    gm.mouse.move(700, 400)
    gm.mouse.down()
    gm.mouse.move(910, 400, steps=5)
    gm.mouse.up()
    expect(gm.locator(".measurement-workspace text")).to_have_count(1)
    gm.get_by_role("button", name="Close measurement", exact=True).click()
    gm.get_by_role("button", name="Draw", exact=True).first.click()
    gm.mouse.move(700, 500)
    gm.mouse.down()
    gm.mouse.move(910, 550, steps=5)
    gm.mouse.up()
    gm.wait_for_function(
        "async id=>(await(await fetch('/api/maps/'+id+'/state')).json()).drawings.rows.length===1",
        arg=data["map"],
    )
    for index, (name, kind) in enumerate((("Rectangle", "rect"), ("Ellipse", "ellipse")), 2):
        gm.locator(".drawing-paint").get_by_role("button", name=name, exact=True).click()
        gm.mouse.move(700, 350)
        gm.mouse.down()
        gm.mouse.move(840, 490, steps=3)
        gm.mouse.up()
        gm.wait_for_function(
            "async p=>{const s=await(await fetch('/api/maps/'+p.map+'/state')).json();return s.drawings.rows.length===p.count&&s.drawings.rows.at(-1)?.kind===p.kind}",
            arg={"map": data["map"], "count": index, "kind": kind},
        )
    gm.get_by_role("button", name="Close drawing", exact=True).click()
    for page in (gm, player):
        expect(page.locator('[data-dock-tool="templates"]')).to_have_count(0)
        expect(page.get_by_role("button", name="Shapes", exact=True)).to_have_count(0)
        page.get_by_role("button", name="Select", exact=True).first.click()
        page.keyboard.press("t")
        expect(page.locator(".measure-panel")).to_have_count(0)
        expect(page.locator(".drawing-paint")).to_have_count(0)
        expect(
            page.locator('.game-dock__group:visible [data-dock-tool="select"]')
        ).to_have_attribute("aria-pressed", "true")
    gm.get_by_role("group", name="Layers", exact=True).get_by_role(
        "button", name="GM", exact=True
    ).click()
    expect(gm.locator('[data-dock-tool="templates"]')).to_have_count(0)
    gm.keyboard.press("t")
    expect(gm.locator(".measure-panel")).to_have_count(0)
    gm.get_by_role("button", name="Draw", exact=True).first.click()
    expect(gm.locator(".drawing-paint")).to_be_visible()
    expect(gm.locator(".drawing-paint").get_by_role("button", name="Rectangle", exact=True)).to_be_visible()
    expect(gm.locator(".drawing-paint").get_by_role("button", name="Ellipse", exact=True)).to_be_visible()
    gm.screenshot(path=str(output / "minipaint-shapes-without-standalone-tool.png"))
    gm.get_by_role("button", name="Close drawing", exact=True).click()
    print("Escape, local measurement, MiniPaint shapes and removed Shapes shortcut passed", flush=True)


if __name__ == "__main__":
    main(check)
