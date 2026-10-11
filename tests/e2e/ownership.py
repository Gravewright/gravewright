"""Exercise the ownership modal against a seeded, isolated running Django server.

Start: python tests/e2e/ownership_server.py (using the application environment).
Then: uv run --no-project --with playwright python tests/e2e/ownership.py
The seed contains test sessions only; never point this test at a real campaign.
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
SEED = json.loads((ROOT / 'data/permissions-review-seed.json').read_text())
BASE = 'http://127.0.0.1:30002'
URL = f'{BASE}/game/{SEED["campaign"]}'
OWNERSHIP = f'{BASE}/api/containers/{SEED["campaign"]}/ownership'


def context(browser, index):
    ctx = browser.new_context(viewport={'width': 1440, 'height': 1000})
    ctx.add_cookies([{**SEED['sessions'][index], 'url': BASE}])
    return ctx


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    gm = context(browser, 0)
    page = gm.new_page()
    page.goto(URL)
    page.wait_for_function('Boolean(window.gravewrightPermissions?.open)')
    page.evaluate("document.documentElement.lang = 'pt-BR'")
    # Reset the page policy so this test can be rerun on the same isolated seed.
    page.evaluate("""async url => {
      const current = await (await fetch(url)).json();
      const csrf = await (await fetch('/__gravewright/csrf')).json();
      const response = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json',[csrf.header]:csrf.token},body:JSON.stringify({version:current.version,permissions:{default:'inherit'}})});
      if (!response.ok) throw Error('Could not reset test page');
    }""", f'{OWNERSHIP}/pages/{SEED["journal"]}:page')

    def open_dialog(kind, key):
        page.evaluate('([kind,id]) => window.gravewrightPermissions.open(kind,id)', [kind, key])
        modal = page.locator('.ownership-dialog[role=dialog]')
        expect(modal).to_be_visible()
        return modal

    page.locator('button[data-panel=journals]').click()
    for title in ['Ownership journal', 'Ownership quest', 'Ownership quest board', 'Ownership roll table']:
        page.locator('#journals-panel strong').get_by_text(title, exact=True).click(button='right')
        page.locator('.gw-folder-menu').get_by_role('button', name='Permissions', exact=True).click()
        modal = page.locator('.ownership-dialog[role=dialog]')
        expect(modal).to_be_visible()
        expect(modal.locator('strong')).to_have_text(f'Permissões: {title}')
        expect(page.locator('.journal-window')).to_have_count(0)
        assert modal.evaluate('element => element.tagName') == 'SECTION'
        assert page.locator('#table-workspace').evaluate('element => element.closest("[inert]") !== null')
        modal.locator('[type=submit]').focus()
        page.keyboard.press('Tab')
        expect(modal.locator('[data-close]')).to_be_focused()
        page.keyboard.press('Shift+Tab')
        expect(modal.locator('[type=submit]')).to_be_focused()
        page.keyboard.press('Escape')
        expect(modal).to_have_count(0)
        assert not page.locator('#table-workspace').evaluate('element => element.closest("[inert]") !== null')

    page.locator('button[data-panel=actors]').click()
    party = page.locator('#actors-panel .gw-folder__toggle').filter(has_text='Party')
    expect(party).to_be_visible()
    if party.get_attribute('aria-expanded') != 'true':
        party.click()
    page.locator('#actors-panel strong').filter(has_text='Ownership hero').click(button='right')
    page.locator('.directory-context-menu').get_by_role('menuitem', name='Permissions', exact=True).click()
    modal = page.locator('.ownership-dialog[role=dialog]')
    expect(modal).to_be_visible()
    modal.locator('select[name=default]').select_option('limited')
    modal.locator(f'select[name="{SEED["users"][1]}"]').select_option('none')
    modal.locator(f'select[name="{SEED["users"][2]}"]').select_option('owner')
    expect(modal.locator('[data-gm]')).to_be_hidden()
    modal.locator('[name=showGM]').check()
    expect(modal.locator('[data-gm] select')).to_be_disabled()
    expect(modal.locator('[data-gm]')).to_be_visible()
    screenshots = ROOT / 'data/permissions-review-screenshots'
    screenshots.mkdir(exist_ok=True)
    page.screenshot(path=str(screenshots / 'ownership-desktop.png'))
    modal.get_by_role('button', name='Salvar alterações', exact=True).click()
    expect(modal).to_have_count(0)
    saved = gm.request.get(f'{OWNERSHIP}/actors/{SEED["actor"]}').json()
    assert saved['permissions']['default'] == 'limited'
    alice = context(browser, 1)
    bruno = context(browser, 2)
    path = f'{BASE}/api/containers/{SEED["campaign"]}/actors'
    assert alice.request.get(path).json()['actors'] == []
    assert bruno.request.get(path).json()['actors'][0]['canEdit']
    alice_page = alice.new_page()
    alice_page.goto(URL)
    alice_page.wait_for_function('Boolean(window.gravewrightJournals?.open)')
    alice_page.evaluate('id => window.gravewrightJournals.open(id)', SEED['journal'])
    expect(alice_page.locator('[data-page-id=page]')).to_be_visible(timeout=15000)

    modal = open_dialog('actors', SEED['actor'])
    modal.locator('select[name=default]').select_option('owner')
    page.keyboard.press('Escape')
    expect(modal).to_have_count(0)
    assert gm.request.get(f'{OWNERSHIP}/actors/{SEED["actor"]}').json()['permissions']['default'] == 'limited'

    modal = open_dialog('actors', SEED['actor'])
    page.evaluate("""async ([url,version]) => {
      const csrf = await (await fetch('/__gravewright/csrf')).json();
      const r = await fetch(url,{method:'POST',headers:{'Content-Type':'application/json',[csrf.header]:csrf.token},body:JSON.stringify({version,permissions:{default:'read'}})});
      if (!r.ok) throw Error('Concurrent test write failed');
    }""", [f'{OWNERSHIP}/actors/{SEED["actor"]}', saved['version']])
    modal.get_by_role('button', name='Salvar alterações', exact=True).click()
    expect(modal.locator('[role=alert]')).to_be_visible()
    modal.get_by_role('button', name='Recarregar permissões').click()
    modal = page.locator('.ownership-dialog[role=dialog]')
    expect(modal.locator('select[name=default]')).to_have_value('read')
    page.keyboard.press('Escape')

    modal = open_dialog('pages', f'{SEED["journal"]}:page')
    expect(modal.locator('select[name=default]')).to_have_value('inherit')
    modal.locator('select[name=default]').select_option('none')
    modal.get_by_role('button', name='Salvar alterações', exact=True).click()
    expect(modal).to_have_count(0)
    journal_state = alice.request.get(f'{BASE}/api/containers/{SEED["campaign"]}/journals').json()
    assert next(j for j in journal_state['journals'] if j['id'] == SEED['journal'])['sections'] == []
    expect(alice_page.locator('[data-page-id=page]')).to_have_count(0)

    modal = open_dialog('compendiums', SEED['pack'])
    assert modal.locator('select').count() == 3
    modal.locator('select[name=player]').select_option('read')
    modal.get_by_role('button', name='Salvar alterações', exact=True).click()
    expect(modal).to_have_count(0)
    packs = alice.request.get(f'{BASE}/api/containers/{SEED["campaign"]}/modules-native/compendiums').json()['packs']
    assert any(pack['id'] == SEED['pack'] for pack in packs)

    page.set_viewport_size({'width': 390, 'height': 844})
    modal = open_dialog('actor-folders', SEED['folder'])
    expect(modal.locator('select[name=default]')).to_have_value('unchanged')
    box = modal.bounding_box()
    assert box['x'] >= 0 and box['x'] + box['width'] <= 390
    page.screenshot(path=str(screenshots / 'ownership-mobile.png'))
    modal.locator('select[name=default]').select_option('read')
    modal.get_by_role('button', name='Salvar alterações', exact=True).click()
    expect(modal).to_have_count(0)
    assert gm.request.get(f'{OWNERSHIP}/actors/{SEED["actor"]}').json()['permissions']['default'] == 'read'
    browser.close()
    print('Ownership browser checks passed: persistence, denial, owner, cancellation, conflict, inheritance, roles and mobile layout.')
