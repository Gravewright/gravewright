"""Window layout and custom modal checks against ownership_server.py on port 30002."""
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SEED = json.loads((ROOT / 'data/permissions-review-seed.json').read_text())
BASE = 'http://127.0.0.1:30002'
URL = f'{BASE}/game/{SEED["campaign"]}'


def context(browser, index=0):
    ctx = browser.new_context(viewport={'width': 1440, 'height': 1000})
    ctx.add_cookies([{**SEED['sessions'][index], 'url': BASE}])
    return ctx


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    gm = context(browser)
    page = gm.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(URL)
    page.wait_for_function('Boolean(window.gravewrightItems?.open && window.gravewrightMaps?.current)')
    page.wait_for_timeout(1200)
    page.locator('button[data-panel=items]').click()
    panel = page.locator('[data-native-directory=items]')
    expect(panel).to_be_visible()
    expect(panel.locator('[data-window-action=reset]')).to_be_visible()
    header = panel.locator('header').bounding_box()
    page.mouse.move(header['x'] + 90, header['y'] + 15)
    page.mouse.down()
    page.mouse.move(260, 70, steps=5)
    page.mouse.up()
    box = panel.bounding_box()
    storage_key = f'gravewright.windows.v1.{SEED["users"][0]}.{SEED["campaign"]}'
    page.wait_for_function('(key) => Boolean(localStorage.getItem(key))', arg=storage_key)
    # Resize through the browser handle; saving must include both dimensions.
    page.mouse.move(box['x'] + box['width'] - 3, box['y'] + box['height'] - 3)
    page.mouse.down()
    page.mouse.move(box['x'] + box['width'] + 55, box['y'] + box['height'] - 83, steps=5)
    page.mouse.up()
    page.wait_for_timeout(200)
    saved = panel.bounding_box()
    assert saved['width'] > box['width'] + 20, (box, saved)
    panel.locator('[data-window-action=minimize]').click()
    assert panel.bounding_box()['height'] < 100
    panel.locator('[data-window-action=minimize]').click()
    assert abs(panel.bounding_box()['height'] - saved['height']) < 2
    page.reload()
    page.wait_for_timeout(1200)
    page.locator('button[data-panel=items]').click()
    expect(panel).to_be_visible()
    restored = panel.bounding_box()
    for key in ['x', 'y', 'width', 'height']:
        assert abs(restored[key] - saved[key]) < 2, (saved, restored)
    # Another user starts without the GM's saved layout.
    player = context(browser, 1)
    player_page = player.new_page()
    player_page.goto(URL)
    assert player_page.evaluate('(key) => localStorage.getItem(key)', storage_key) is None
    # Existing items use accessible custom modals and keep edits after saving.
    page.evaluate('(id) => window.gravewrightItems.open(id)', SEED['item'])
    modal = page.locator('.table-form-modal[role=dialog]')
    expect(modal).to_be_visible()
    assert modal.evaluate('(el) => el.tagName') == 'SECTION'
    expect(page.locator('dialog')).to_have_count(0)
    assert page.locator('#table-workspace').evaluate('(el) => Boolean(el.closest("[inert]"))')
    modal.locator('[type=submit]').focus()
    page.keyboard.press('Tab')
    expect(modal.locator('[data-close]')).to_be_focused()
    modal.locator('[name=name]').fill('Window layout item')
    modal.locator('[type=submit]').click()
    expect(modal).to_have_count(0)
    expect(panel.get_by_role('button', name='Window layout item', exact=True)).to_be_visible()
    assert not page.locator('#table-workspace').evaluate('(el) => Boolean(el.closest("[inert]"))')
    page.evaluate('(id) => window.gravewrightItems.open(id)', SEED['item'])
    modal.get_by_role('button', name='Cancel', exact=True).click()
    expect(modal).to_have_count(0)
    # Scene settings expose the same window frame and keyboard-operable tabs.
    page.locator('button[data-panel=scenes]').click()
    scene_name = page.evaluate('window.gravewrightMaps.current.name')
    page.locator('#maps-panel strong').get_by_text(scene_name, exact=True).click(button='right')
    page.locator('.directory-context-menu').get_by_role('menuitem', name='Edit', exact=True).click()
    scene = page.locator('.game-scene-settings[role=dialog]')
    expect(scene).to_be_visible()
    expect(scene.get_by_role('tab')).to_have_count(3)
    screenshot_dir = ROOT / 'data/window-layout-review'
    screenshot_dir.mkdir(exist_ok=True)
    page.screenshot(path=str(screenshot_dir / 'scene-settings.png'))
    scene.get_by_role('tab', name='General', exact=True).focus()
    page.keyboard.press('ArrowRight')
    expect(scene.get_by_role('tab', name='Grid and scale', exact=True)).to_have_attribute('aria-selected', 'true')
    scene.locator('[name=measureValue]').fill('')
    scene.get_by_role('tab', name='General', exact=True).click()
    scene.locator('[name=name]').fill('')
    scene.locator('[type=submit]').click()
    expect(scene.get_by_role('tab', name='General', exact=True)).to_have_attribute('aria-selected', 'true')
    expect(scene.locator('[name=name]')).to_be_focused()
    scene.locator('[name=name]').fill(scene_name)
    scene.locator('[type=submit]').click()
    expect(scene.get_by_role('tab', name='Grid and scale', exact=True)).to_have_attribute('aria-selected', 'true')
    scene.locator('[name=measureValue]').fill('1')
    scene.locator('[data-calibrate]').click()
    expect(scene).to_be_hidden()
    assert not page.locator('#table-workspace').evaluate('(el) => Boolean(el.closest("[inert]"))')
    page.keyboard.press('Escape')
    expect(scene).to_be_visible()
    assert page.locator('#table-workspace').evaluate('(el) => Boolean(el.closest("[inert]"))')
    scene.get_by_role('tab', name='Initial view', exact=True).click()
    scene.locator('[data-current-view]').click()
    expect(scene.locator('[data-view-status]')).to_be_visible()
    scene.get_by_role('tab', name='General', exact=True).click()
    scene.locator('[name=name]').fill('Window layout scene')
    scene.locator('[type=submit]').click()
    expect(scene).to_have_count(0)
    expect(page.locator('#maps-panel strong').get_by_text('Window layout scene', exact=True)).to_be_visible()
    # Pending writes keep the modal open; failures restore the controls.
    page.evaluate('''async () => {
      const {openFormModal} = await import('/static/gravewright_table/form-modal.js');
      openFormModal('Pending test', [], () => new Promise((resolve,reject) => {window.rejectModalTest=reject}));
    }''')
    modal.locator('[type=submit]').click()
    page.keyboard.press('Escape')
    expect(modal).to_be_visible()
    expect(modal.locator('[data-close]')).to_be_disabled()
    page.evaluate('window.rejectModalTest(Error("Test save failed"))')
    expect(modal.locator('[role=alert]')).to_have_text('Test save failed')
    expect(modal.locator('[data-close]')).to_be_enabled()
    page.keyboard.press('Escape')
    expect(modal).to_have_count(0)
    page.locator('button[data-panel=content]').click()
    compendiums = page.locator('[data-native-directory=compendiums]')
    expect(compendiums).to_be_visible()
    expect(compendiums.locator('[data-window-action=reset]')).to_be_visible()
    compendiums.locator('[data-window-action=minimize]').click()
    assert compendiums.bounding_box()['height'] < 100
    compendiums.locator('[data-window-action=minimize]').click()
    compendiums.locator('[data-close]').click()
    player_page.wait_for_function('Boolean(window.gravewrightItems?.open)')
    player_page.evaluate('(id) => window.gravewrightItems.open(id)', SEED['item'])
    player_modal = player_page.locator('.table-form-modal[role=dialog]')
    expect(player_modal.locator('[name=name]')).to_have_attribute('readonly', '')
    expect(player_modal.locator('[type=submit]')).to_be_hidden()
    player_page.keyboard.press('Escape')
    # Layout reset removes the preference and viewport changes keep panels reachable.
    if not panel.is_visible():
        page.locator('button[data-panel=items]').click()
    panel.locator('[data-window-action=reset]').click()
    entries = page.evaluate('(key) => JSON.parse(localStorage.getItem(key))', storage_key)
    assert not any(key == panel.get_attribute('id') for key, _ in entries)
    page.set_viewport_size({'width': 600, 'height': 700})
    box = panel.bounding_box()
    assert box['x'] >= 0 and box['y'] >= 0 and box['x'] + box['width'] <= 601, box
    assert not errors, errors
    browser.close()
    print('Window layout, item modal, scene tabs, keyboard focus and viewport checks passed.')
