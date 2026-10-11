"""Exercise image resizing through the full table UI against ownership_server.py."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
SEED = json.loads((ROOT / 'data/permissions-review-seed.json').read_text())
BASE = 'http://127.0.0.1:30002'

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    context.add_cookies([{**SEED['sessions'][0], 'url': BASE}])
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(f'{BASE}/game/{SEED["campaign"]}', wait_until='domcontentloaded')
    page.wait_for_function("Boolean(document.querySelector('canvas') && window.gravewrightRealtime?.mapCommand)")
    placement = page.evaluate("""async ({campaign, scene}) => {
        const canvas = document.createElement('canvas'); canvas.width = 200; canvas.height = 100;
        const ctx = canvas.getContext('2d'); ctx.fillStyle = '#c19549'; ctx.fillRect(0, 0, 200, 100);
        const blob = await new Promise(resolve => canvas.toBlob(resolve));
        const form = new FormData(); form.append('file', blob, 'resize-test.png');
        const csrf = await (await fetch('/__gravewright/csrf')).json();
        const response = await fetch(`/api/containers/${campaign}/library/upload`, {
            method: 'POST', headers: {[csrf.header || 'X-CSRF-Token']: csrf.token}, body: form,
        });
        const asset = await response.json(); if (!response.ok) throw Error(JSON.stringify(asset));
        await gravewrightRealtime.mapCommand('objects', {mapId: scene, area: 'images', action: 'create',
            data: {asset_id: asset.id || asset.asset_id, x: 400, y: 300, scale: 1}});
        const state = await (await fetch(`/api/maps/${scene}/state`)).json();
        return state.images.find(i => i.asset_id === (asset.id || asset.asset_id));
    }""", {'campaign': SEED['campaign'], 'scene': SEED['scene']})
    page.locator('.game-menubar__layer').nth(2).click()
    image = page.locator('.image-workspace__image').last
    expect(image).to_be_visible()
    image.click()
    handles = page.locator('.image-workspace__resize')
    expect(handles).to_have_count(4)
    old_width = float(image.get_attribute('width'))
    box = handles.nth(2).bounding_box()
    x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 60, y + 30, steps=8)
    page.mouse.up()
    page.wait_for_function("""({scene, width, id}) => fetch(`/api/maps/${scene}/state`).then(r => r.json())
        .then(state => state.images.some(i => i.id === id && i.natural_width * i.scale > width + 10))""",
        arg={'scene': SEED['scene'], 'width': old_width, 'id': placement['id']})
    page.reload(wait_until='domcontentloaded')
    page.locator('.game-menubar__layer').nth(2).click()
    expect(image).to_be_visible()
    assert float(image.get_attribute('width')) > old_width + 10
    # The normal Game selection also exposes resize handles, without switching layers.
    box = image.bounding_box()
    center = (box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    page.locator('.game-menubar__layer').nth(0).click()
    page.mouse.click(*center)
    handles = page.locator('[data-image-resize]')
    expect(handles).to_have_count(4)
    page.screenshot(path=str(ROOT / 'data/permissions-review-image-resize.png'))
    box = handles.nth(2).bounding_box()
    x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    current = page.evaluate("""async scene => (await (await fetch(`/api/maps/${scene}/state`)).json()).images.at(-1)""", SEED['scene'])
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 40, y + 20, steps=8)
    page.keyboard.press('Escape')
    page.mouse.up()
    expect(handles).to_have_count(0)
    after_cancel = page.evaluate("""async scene => (await (await fetch(`/api/maps/${scene}/state`)).json()).images.at(-1)""", SEED['scene'])
    assert after_cancel == current
    # Select by the known screen position again, then commit a resize.
    page.mouse.click(*center)
    expect(handles).to_have_count(4)
    box = handles.nth(2).bounding_box()
    x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    page.mouse.move(x, y); page.mouse.down()
    page.mouse.move(x + 40, y + 20, steps=8); page.mouse.up()
    page.wait_for_function("""({scene, scale, id}) => fetch(`/api/maps/${scene}/state`).then(r => r.json())
        .then(state => state.images.some(i => i.id === id && i.scale > scale))""",
        arg={'scene': SEED['scene'], 'scale': current['scale'], 'id': placement['id']})
    # Keyboard resize belongs to the handle, rather than the scene move shortcuts.
    page.wait_for_function("document.querySelector('.selection-workspace__error').hidden")
    handles.nth(2).focus()
    with page.expect_response(lambda response: response.url.endswith(f'/api/maps/{SEED["scene"]}/state')):
        page.keyboard.press('ArrowRight')
    page.reload(wait_until='domcontentloaded')
    page.locator('.game-menubar__layer').nth(2).click()
    expect(image).to_be_visible()
    assert float(image.get_attribute('width')) > current['natural_width'] * current['scale']
    assert not errors, errors
    browser.close()
    print('Full table image resize and persistence checks passed.')
