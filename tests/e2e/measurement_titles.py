"""Edit optional measurement titles directly beside their dimensions on the map."""

from migration_closure import main
from playwright.sync_api import expect


def check(gm, player, data, output):
    gm.get_by_role('button', name='Measure', exact=True).first.click()
    panel = gm.locator('.measure-panel')
    checkbox = panel.get_by_label('Title', exact=True)
    expect(checkbox).not_to_be_checked()
    gm.mouse.move(400, 300)
    gm.mouse.down()
    gm.mouse.move(600, 420, steps=4)
    gm.mouse.up()
    expect(gm.get_by_role('textbox', name='Measurement title', exact=True)).to_have_count(0)
    checkbox.check()
    title = gm.get_by_role('textbox', name='Measurement title', exact=True)
    expect(title).to_be_visible()
    title.fill('Dangerous area <script>')
    expect(title).to_have_value('Dangerous area <script>')
    title.press('Enter')
    expect(gm.locator('.measure-panel')).to_be_visible()
    expect(gm.locator('.measurement-workspace text')).to_have_count(1)
    title_box = title.bounding_box()
    dimensions = gm.locator('.measurement-workspace text').bounding_box()
    # The SVG label's painted bounds include its 3px outline.
    assert abs(title_box['x'] - dimensions['x'] - 3) < 2
    assert 0 <= dimensions['y'] - title_box['y'] - title_box['height'] <= 10
    scale = gm.evaluate('gravewrightMaps.board.viewport().scale')
    gm.mouse.move(500, 400)
    gm.mouse.wheel(0, -300)
    gm.wait_for_function('scale => gravewrightMaps.board.viewport().scale !== scale', arg=scale)
    gm.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    gm.screenshot(path=str(output / 'measurement-title-zoom.png'))
    gm.wait_for_function('''() => {
        const a = document.querySelector('.measurement-title__input').getBoundingClientRect();
        const b = document.querySelector('.measurement-workspace text').getBoundingClientRect();
        return Math.abs(a.x - b.x) < 2 && a.bottom <= b.y;
    }''')
    handle = gm.locator('.measurement-workspace__handle').first.bounding_box()
    before = title.bounding_box()
    gm.mouse.move(handle['x'] + handle['width'] / 2, handle['y'] + handle['height'] / 2)
    gm.mouse.down()
    gm.mouse.move(handle['x'] + handle['width'] / 2 + 40, handle['y'] + handle['height'] / 2 + 30, steps=4)
    gm.mouse.up()
    after = title.bounding_box()
    assert abs(after['x'] - before['x'] - 40) < 2
    assert abs(after['y'] - before['y'] - 30) < 2
    expect(title).to_have_value('Dangerous area <script>')
    checkbox.uncheck()
    expect(title).to_have_count(0)
    checkbox.check()
    expect(title).to_have_value('Dangerous area <script>')
    panel.get_by_role('button', name='Close measurement', exact=True).click()
    expect(gm.locator('.measurement-title__text')).to_have_text('Dangerous area <script>')
    expect(player.locator('.measurement-title')).to_have_count(0)
    gm.get_by_role('button', name='Measure', exact=True).first.click()
    expect(title).to_have_value('Dangerous area <script>')
    # Selecting a new shape gives it an independent title.
    panel.get_by_role('button', name='Cube / rectangle', exact=True).click()
    gm.mouse.move(750, 300)
    gm.mouse.down()
    gm.mouse.move(950, 450, steps=4)
    gm.mouse.up()
    titles = gm.get_by_role('textbox', name='Measurement title', exact=True)
    expect(titles).to_have_count(2)
    expect(titles.nth(1)).to_have_value('')
    titles.nth(1).fill('Dangerous area')
    gm.screenshot(path=str(output / 'measurement-title-desktop.png'))
    gm.set_viewport_size({'width': 390, 'height': 844})
    expect(panel).to_be_visible()
    expect(checkbox).to_be_checked()
    panel.get_by_role('button', name='Circle', exact=True).click()
    gm.mouse.move(80, 180)
    gm.mouse.down()
    gm.mouse.move(200, 280, steps=4)
    gm.mouse.up()
    expect(titles.nth(2)).to_be_visible()
    titles.nth(2).fill('Dangerous area with a long descriptive title ' * 2)
    expect(titles.nth(2)).to_have_attribute('maxlength', '120')
    gm.screenshot(path=str(output / 'measurement-title-mobile.png'))
    panel.get_by_role('button', name='Delete', exact=True).click()
    expect(titles).to_have_count(2)
    panel.get_by_role('button', name='Clear', exact=True).click()
    panel.get_by_role('button', name='Confirm clearing', exact=True).click()
    expect(titles).to_have_count(0)
    print('Measurement titles: inline editing, toggle, safe text, independent shapes, close/reopen and cleanup passed', flush=True)


if __name__ == '__main__':
    main(check)
