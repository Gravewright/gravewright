"""Test player presentations through real WebSocket sessions on the isolated fixture server."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
SEED = json.loads((ROOT / 'data/permissions-review-seed.json').read_text())
BASE = 'http://127.0.0.1:30002'
URL = f'{BASE}/game/{SEED["campaign"]}'

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    contexts, pages = [], []
    for index in range(3):
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        context.add_cookies([{**SEED['sessions'][index], 'url': BASE}])
        page = context.new_page()
        page.goto(URL)
        page.wait_for_function('Boolean(window.gravewrightJournals?.open)')
        contexts.append(context)
        pages.append(page)
    gm, alice, bruno = pages
    gm.evaluate("document.documentElement.lang='pt-BR'")
    gm.locator('button[data-panel=journals]').click()
    state_url = f'{BASE}/api/containers/{SEED["campaign"]}/journals'
    book = next(j for j in contexts[0].request.get(state_url).json()['journals'] if j['title'] == 'Presentation book')

    def open_modal(title):
        gm.locator('#journals-panel strong').get_by_text(title, exact=True).click(button='right')
        gm.locator('.gw-folder-menu').get_by_role('button', name='Exibir para os jogadores', exact=True).click()
        modal = gm.locator('.journal-presentation-modal')
        expect(modal).to_be_visible()
        expect(gm.locator('.journal-window')).to_have_count(0)
        return modal

    modal = open_modal('Presentation book')
    expect(modal.locator('[name=allPlayers]')).to_be_checked()
    expect(modal.locator('[name=ownership]')).to_have_value('unchanged')
    expect(modal.locator('[name=players]').first).to_be_disabled()
    modal.locator('[name=allPlayers]').uncheck()
    modal.locator('[type=submit]').click()
    expect(modal.locator('[role=alert]')).to_be_visible()
    expect(alice.locator('.journal-window')).to_have_count(0)
    modal.locator(f'[name=players][value="{SEED["users"][1]}"]').check()
    screenshots = ROOT / 'data/permissions-review-screenshots'
    screenshots.mkdir(exist_ok=True)
    gm.screenshot(path=str(screenshots / 'presentation-desktop.png'))
    modal.locator('[type=submit]').click()
    try:
        expect(modal).to_have_count(0, timeout=15000)
    except AssertionError:
        raise AssertionError(f'Presentation did not finish: {modal.locator("[role=alert]").inner_text()}') from None
    expect(alice.locator('.journal-window')).to_be_visible(timeout=15000)
    expect(alice.locator('[data-page-id=first]')).to_be_visible()
    expect(alice.locator('[data-page-id=second]')).to_be_visible()
    expect(alice.locator('.journal-window')).not_to_contain_text('GM secret page')
    expect(bruno.locator('.journal-window')).to_have_count(0)
    assert not any(j['id'] == book['id'] for j in contexts[1].request.get(state_url).json()['journals'])
    alice.locator('.journal-window [data-action=close]').click()

    # All-player delivery and permanent access work for every journal type.
    for title in ['Ownership journal', 'Ownership quest', 'Ownership quest board', 'Ownership roll table']:
        modal = open_modal(title)
        modal.locator('[name=ownership]').select_option('read')
        modal.locator('[type=submit]').click()
        expect(modal).to_have_count(0)
        for player in [alice, bruno]:
            expect(player.locator('.journal-window')).to_be_visible(timeout=15000)
            expect(player.locator('.journal-window [data-title]')).to_have_text(title)
            expect(player.locator('.journal-window [data-action=permissions]')).to_be_hidden()
            player.locator('.journal-window [data-action=close]').click()

    # Sharing one public page opens only that page.
    gm.evaluate('id => window.gravewrightJournals.open(id)', book['id'])
    expect(gm.locator('[data-page-id=first]')).to_be_visible()
    gm.locator('[data-page-id=first]').click(button='right')
    gm.locator('.journal-context').get_by_role('button', name='Exibir para os jogadores', exact=True).click()
    modal = gm.locator('.journal-presentation-modal')
    expect(modal.locator('[data-access]')).to_be_hidden()
    gm.set_viewport_size({'width': 390, 'height': 844})
    box = modal.bounding_box()
    assert box['x'] >= 0 and box['x'] + box['width'] <= 390
    gm.screenshot(path=str(screenshots / 'presentation-mobile.png'))
    modal.locator('[type=submit]').click()
    for player in [alice, bruno]:
        expect(player.locator('[data-page-id=first]')).to_be_visible(timeout=15000)
        expect(player.locator('[data-page-id=second]')).to_have_count(0)
        expect(player.locator('.journal-window')).not_to_contain_text('GM secret page')
    browser.close()
    print('Presentation browser checks passed: selected recipients, everyone, temporary access, document types, page scope and mobile modal.')
