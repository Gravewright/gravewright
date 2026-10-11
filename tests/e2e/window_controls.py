"""Detached and minimized windows against ownership_server.py's isolated fixture."""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
SEED = json.loads((ROOT / 'data/permissions-review-seed.json').read_text())
BASE = 'http://127.0.0.1:30002'


def drag(page, panel, x, y):
    box = panel.locator(':scope > header').bounding_box()
    page.mouse.move(box['x'] + 90, box['y'] + 15)
    page.mouse.down()
    page.mouse.move(x, y, steps=5)
    page.mouse.up()


def native_window(context, page):
    session = context.new_cdp_session(page)
    try:
        return session.send('Browser.getWindowForTarget')['windowId']
    finally:
        session.detach()


with sync_playwright() as playwright:
    headed = '--headed' in sys.argv
    browser = playwright.chromium.launch(headless=not headed)
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    context.add_cookies([{**SEED['sessions'][0], 'url': BASE}])
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(f'{BASE}/game/{SEED["campaign"]}')
    page.wait_for_function('Boolean(window.gravewrightMaps?.current && window.gravewrightActors && window.gravewrightJournals)')
    page.wait_for_timeout(1200)
    main_window = native_window(context, page)
    # A previously named ordinary tab must never capture a detached panel.
    with page.expect_popup() as ordinary:
        page.evaluate("window.open('about:blank', 'maps-directory')")
    ordinary_tab = ordinary.value
    if headed:
        assert native_window(context, ordinary_tab) == main_window
    page.bring_to_front()
    for name, hook, panel_id in [
        ('scenes', 'data-map-panel', 'maps-panel'),
        ('actors', 'data-actor-panel', 'actors-panel'),
        ('journals', 'data-journal-directory', 'journals-panel'),
    ]:
        dock = page.locator(f'button[data-panel={name}]')
        dock.click()
        panel = page.locator(f'#{panel_id}')
        expect(panel).to_be_visible()
        drag(page, panel, 250, 80)
        expanded = panel.bounding_box()
        panel.locator(f'[{hook}=minimize]').click()
        assert panel.bounding_box()['height'] < 100
        # Moving a minimized header must preserve the expanded window's height.
        drag(page, panel, 340, 110)
        dock.click()
        expect(panel).to_be_visible()
        assert abs(panel.bounding_box()['height'] - expanded['height']) < 2
        before = panel.bounding_box()
        # Saved positions belong to the table, not the detached viewport.
        for _ in range(2):
            with page.expect_popup() as opened:
                panel.locator(f'[{hook}=detach]').click()
            popup = opened.value
            assert native_window(context, popup) != main_window
            expect(ordinary_tab.locator(f'#{panel_id}')).to_have_count(0)
            expect(page.locator(f'#{panel_id}')).to_have_count(0)
            popup.on('pageerror', lambda error: errors.append(str(error)))
            detached = popup.locator(f'#{panel_id}')
            expect(detached).to_be_visible()
            popup.wait_for_function('Boolean(document.styleSheets.length)')
            expect(detached).to_have_css('position', 'static')
            box = detached.bounding_box()
            assert box['x'] == 0 and box['y'] == 0, box
            assert abs(box['width'] - popup.evaluate('innerWidth')) < 2, box
            assert abs(box['height'] - popup.evaluate('innerHeight')) < 2, box
            expect(detached.locator(f'[{hook}=minimize]')).to_be_hidden()
            popup.close()
            page.bring_to_front()
            expect(panel).to_be_visible()
            returned = panel.bounding_box()
            for dimension in ['x', 'y', 'width', 'height']:
                assert abs(before[dimension] - returned[dimension]) < 2, (before, returned)
        # Returned panels must retain working drag and minimize listeners.
        drag(page, panel, 420, 130)
        panel.locator(f'[{hook}=minimize]').click()
        assert panel.bounding_box()['height'] < 100
        dock.click()
        assert panel.bounding_box()['height'] > 200
        with page.expect_popup() as opened:
            panel.locator(f'[{hook}=detach]').click()
        popup = opened.value
        with popup.expect_event('close'):
            popup.locator(f'[{hook}=close]').click()
        expect(panel).to_be_hidden()
    ordinary_tab.close()
    for name in ['items', 'content']:
        dock = page.locator(f'button[data-panel={name}]')
        dock.click()
        panel = page.locator('[data-native-directory=' + ('compendiums' if name == 'content' else name) + ']')
        panel.locator('[data-window-action=minimize]').click()
        assert panel.bounding_box()['height'] < 100
        dock.click()
        expect(panel).to_be_visible()
        assert panel.bounding_box()['height'] > 200
        expect(panel.locator('[data-window-action=minimize]')).to_have_attribute('aria-label', 'Minimize')
        panel.locator('[data-close]').click()
    page.evaluate('(id) => window.gravewrightJournals.open(id)', SEED['journal'])
    journal = page.locator('.journal-window')
    expect(journal).to_be_visible()
    # The title input is not a drag handle; use the empty titlebar area.
    journal.evaluate('(el) => {el.style.left="150px";el.style.top="80px";el.style.height="600px";el.style.width="900px"}')
    journal.locator('[data-action=minimize]').click()
    assert journal.bounding_box()['height'] < 100
    handle = journal.locator(':scope > header').bounding_box()
    page.mouse.move(handle['x'] + 5, handle['y'] + 10)
    page.mouse.down()
    page.mouse.move(210, 120, steps=5)
    page.mouse.up()
    journal.locator('[data-action=minimize]').click()
    assert abs(journal.bounding_box()['height'] - 600) < 2
    before = journal.bounding_box()
    with page.expect_popup() as opened:
        journal.locator('[data-action=detach]').click()
    popup = opened.value
    detached = popup.locator('.journal-window')
    expect(detached).to_have_css('position', 'static')
    assert detached.bounding_box()['x'] == 0
    popup.close()
    expect(journal).to_be_visible()
    assert abs(journal.bounding_box()['height'] - before['height']) < 2
    journal.locator('[data-action=close]').click()
    expect(journal).to_have_count(0)
    page.evaluate('(id) => window.gravewrightActors.open(id)', SEED['actor'])
    sheet = page.locator('.actor-directory__sheet')
    expect(sheet).to_be_visible()
    with page.expect_popup() as opened:
        sheet.locator('[data-window=detach]').click()
    popup = opened.value
    assert native_window(context, popup) != main_window
    detached = popup.locator('.actor-directory__sheet')
    expect(detached).to_have_css('position', 'static')
    expect(page.locator('.actor-directory__sheet')).to_have_count(0)
    popup.close()
    expect(sheet).to_be_visible()
    # A blocked popup leaves the sheet usable and tells the user what happened.
    page.evaluate('window.savedOpenForTest = window.open; window.open = () => null')
    sheet.locator('[data-window=detach]').click()
    expect(sheet.locator('[data-window-error]')).to_be_visible()
    expect(sheet).to_be_visible()
    page.evaluate('window.open = window.savedOpenForTest; delete window.savedOpenForTest')
    with page.expect_popup() as opened:
        sheet.locator('[data-window=detach]').click()
    popup = opened.value
    expect(popup.locator('[data-window-error]')).to_have_count(0)
    with popup.expect_event('close'):
        popup.locator('[data-window=close]').click()
    expect(sheet).to_have_count(0)
    page.evaluate('window.gravewrightDice.toggle()')
    tray = page.locator('#dice-tray')
    expect(tray).to_be_visible()
    with page.expect_popup() as opened:
        tray.locator('[data-dice-action=detach]').click()
    popup = opened.value
    assert native_window(context, popup) != main_window
    expect(page.locator('#dice-tray')).to_have_count(0)
    expect(popup.locator('#dice-tray')).to_have_css('position', 'static')
    popup.close()
    expect(tray).to_be_visible()
    page.evaluate('window.gravewrightDice.close()')
    page.evaluate('window.gravewrightRealtime.toggleChat()')
    with page.expect_popup() as opened:
        page.evaluate('window.gravewrightRealtime.detach()')
    popup = opened.value
    assert native_window(context, popup) != main_window
    expect(popup.locator('#chat-panel')).to_be_visible()
    popup.close()
    expect(page.locator('#chat-panel')).to_be_visible()
    assert not errors, errors
    browser.close()
    print('Window controls passed: minimized drag, dock restore, repeated detach, geometry, close and reattach.')
