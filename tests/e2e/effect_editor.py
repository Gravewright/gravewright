"""Effect editor geometry and movable behavior in the real table stylesheet cascade."""

from migration_closure import main
from playwright.sync_api import expect


def check(gm, player, data, output):
    gm.get_by_role("group", name="Layers", exact=True).get_by_role(
        "button", name="Effects", exact=True
    ).click()
    gm.get_by_role("button", name="Shaders", exact=True).click()
    gm.locator('[data-shader-preset="orb-1"]').click()
    gm.mouse.click(650, 400)
    gm.locator('[data-effect-kind="shader"]').first.dblclick()
    editor = gm.locator(".effect-editor")
    expect(editor).to_be_visible()
    gm.wait_for_timeout(300)
    assert editor.evaluate("el => getComputedStyle(el).width") == "760px"
    assert editor.locator("textarea").first.bounding_box()["width"] > 300
    assert editor.evaluate("el => getComputedStyle(el).position") == "fixed"
    editor.get_by_role("checkbox", name="Entire scene", exact=True).check()
    gm.wait_for_timeout(200)
    assert editor.evaluate("el => getComputedStyle(el).resize") == "both"
    header = editor.locator(".effect-editor__header").bounding_box()
    before = editor.bounding_box()
    gm.mouse.move(header["x"] + 100, header["y"] + 15)
    gm.mouse.down()
    gm.mouse.move(header["x"] + 150, header["y"] + 45, steps=5)
    gm.mouse.up()
    after = editor.bounding_box()
    assert abs(after["width"] - before["width"]) < 1
    assert abs(after["x"] - before["x"] - 50) < 2
    gm.screenshot(path=str(output / "effect-editor-desktop.png"))
    # Resize through the native browser grip; the two columns must stack when narrow.
    gm.mouse.move(after["x"] + after["width"] - 3, after["y"] + after["height"] - 3)
    gm.mouse.down()
    gm.mouse.move(after["x"] + 480, after["y"] + after["height"] - 3, steps=8)
    gm.mouse.up()
    assert editor.bounding_box()["width"] < 600
    columns = editor.locator(".effect-editor__columns")
    assert (
        columns.evaluate(
            "el => getComputedStyle(el).gridTemplateColumns.split(' ').length"
        )
        == 1
    )
    editor.get_by_role("button", name="Close", exact=True).click()
    gm.set_viewport_size({"width": 390, "height": 740})
    # Dispatch on the existing scene origin, which can be outside the narrow camera viewport.
    origin = gm.locator('[data-effect-kind="shader"]').first
    bounds = origin.bounding_box()
    origin.dispatch_event(
        "dblclick",
        {
            "clientX": bounds["x"] + bounds["width"] / 2,
            "clientY": bounds["y"] + bounds["height"] / 2,
        },
    )
    expect(editor).to_be_visible()
    box = editor.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= 390
    save = editor.locator(".effect-editor__actions button").last.bounding_box()
    assert save["y"] + save["height"] <= 740
    gm.screenshot(path=str(output / "effect-editor-mobile.png"))
    print(
        "Shader editor: original width, editable controls, drag, native resize and narrow viewport passed.",
        flush=True,
    )


if __name__ == "__main__":
    main(check)
