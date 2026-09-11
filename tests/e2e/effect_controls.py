"""Complete effect editor controls, draft isolation and destructive UI actions."""

import re

from migration_closure import main
from playwright.sync_api import expect


def check(gm, player, data, output):
    def state(page=gm):
        return page.evaluate(
            "async id => (await fetch('/api/maps/'+id+'/state')).json()", data["map"]
        )

    def saved(area, values):
        for page in (gm, player):
            page.wait_for_function(
                "([area,values]) => window.auditEffects?.[area]?.some(row => Object.entries(values).every(([k,v]) => row[k]===v))",
                arg=[area, values],
            )

    for page in (gm, player):
        page.evaluate(
            "window.addEventListener('gravewright:map-layers', e => window.auditEffects=e.detail)"
        )
    gm.get_by_role("group", name="Layers", exact=True).get_by_role(
        "button", name="Effects", exact=True
    ).click()
    gm.get_by_role("button", name="Shaders", exact=True).click()
    gm.locator('[data-shader-preset="orb-1"]').click()
    gm.mouse.click(850, 400)
    gm.locator('[data-effect-kind="shader"]').first.dblclick()
    editor = gm.locator(".effect-editor")
    library = editor.locator(".effect-editor__library")
    library.locator("summary").click()
    library.locator('input[type="search"]').fill("Frost Mist")
    expect(library).to_have_attribute("open", "")
    expect(
        library.locator(".effect-editor__presets").get_by_role("option")
    ).to_have_count(1)
    library.locator(".effect-editor__presets").get_by_role("option").click()
    library.locator(".effect-editor__choice button").click()
    expect(library).to_have_attribute("open", "")
    library.locator("summary").click()
    values = {
        "opacity": 0.35,
        "intensity": 0.45,
        "scale": 2.5,
        "speed": 1.7,
        "rotation": 123,
        "radius": 12,
        "light_response": 0.65,
        "light_emission": 0.4,
        "color": "#44aabb",
        "blend_mode": "multiply",
        "enabled": False,
    }
    for label, key in [
        ("Opacity", "opacity"),
        ("Intensity", "intensity"),
        ("Scale", "scale"),
        ("Speed", "speed"),
        ("Rotation", "rotation"),
        ("Range", "radius"),
        ("Receive lighting", "light_response"),
        ("Emit light", "light_emission"),
    ]:
        editor.get_by_role("slider", name=re.compile("^" + label)).fill(
            str(values[key])
        )
    editor.locator('input[type="color"]').fill(values["color"])
    editor.get_by_role("combobox", name=re.compile("^Blend mode")).select_option(
        "multiply"
    )
    editor.get_by_role("checkbox", name="Active", exact=True).uncheck()
    editor.get_by_role("button", name="Save", exact=True).click()
    saved("shaders", values)
    print(
        "Shader preset application and all controls persisted to both peers", flush=True
    )
    editor.get_by_role("slider", name=re.compile("^Opacity")).fill("0.9")
    gm.wait_for_timeout(400)
    assert state()["shaders"][0]["opacity"] == 0.35
    assert state(player)["shaders"][0]["opacity"] == 0.35
    editor.get_by_role("button", name="Close", exact=True).click()
    gm.locator('[data-effect-kind="shader"]').first.dblclick()
    expect(editor.get_by_role("slider", name=re.compile("^Opacity"))).to_have_value(
        "0.35"
    )
    editor.get_by_role("button", name="Remove shader", exact=True).click()
    expect(editor).to_have_count(0)
    gm.wait_for_function("window.auditEffects?.shaders.length===0")
    player.wait_for_function("window.auditEffects?.shaders.length===0")
    gm.get_by_role("button", name="Particles", exact=True).click()
    gm.locator(".effect-picker__particles button").first.click()
    gm.mouse.click(650, 400)
    gm.locator('[data-effect-kind="particle"]').first.dblclick()
    for label, value in [
        ("Size", 4),
        ("Quantity", 0.35),
        ("Receive lighting", 0.6),
        ("Emit light", 0.5),
    ]:
        editor.get_by_role("slider", name=re.compile("^" + label)).fill(str(value))
    editor.locator('input[type="color"]').fill("#ff8844")
    # Closing immediately flushes the debounced particle save.
    editor.get_by_role("button", name="Close", exact=True).click()
    saved(
        "particles",
        {
            "scale": 4,
            "density": 0.35,
            "light_response": 0.6,
            "light_emission": 0.5,
            "color": "#ff8844",
        },
    )
    gm.get_by_role("button", name="Clear all scene effects", exact=True).click()
    confirm = gm.locator(".scene-sources__confirm")
    expect(confirm).to_be_visible()
    print("Clear buttons:", confirm.inner_text(), flush=True)
    confirm.get_by_role("button", name="Cancel", exact=True).click()
    assert len(state()["particles"]) == 1
    gm.get_by_role("button", name="Clear all scene effects", exact=True).click()
    confirm.get_by_role("button").last.click()
    for page in (gm, player):
        page.wait_for_function(
            "window.auditEffects?.particles.length===0 && window.auditEffects?.shaders.length===0"
        )
    gm.reload()
    gm.wait_for_function("window.gravewrightMaps?.board?.viewport()")
    assert state()["particles"] == [] and state()["shaders"] == []
    print(
        "Draft isolation, particle save on close, remove, cancel/confirm clear and reload passed",
        flush=True,
    )


if __name__ == "__main__":
    main(check)
