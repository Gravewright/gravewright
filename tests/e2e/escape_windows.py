"""Run against ownership_server.py; verify Escape closes one surface safely."""
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from playwright._impl._errors import TargetClosedError

ROOT = Path(__file__).resolve().parents[2]
seed = json.loads((ROOT / 'data/permissions-review-seed.json').read_text())
base = 'http://127.0.0.1:30002'

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    context.add_cookies([{**seed['sessions'][0], 'url': base}])
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(base + '/game/' + seed['campaign'])
    page.wait_for_function('!!window.gravewrightJournals && !!window.gravewrightActors')
    page.evaluate('(id) => window.gravewrightJournals.open(id)', seed['journal'])
    journal = page.locator('.journal-window')
    expect(journal).to_be_visible()
    page.evaluate('(id) => window.gravewrightActors.open(id)', seed['actor'])
    sheet = page.locator('.actor-directory__sheet')
    expect(sheet.locator('.pdf-sheet__tabs')).to_be_visible()
    # A sheet must run its asynchronous flush lifecycle, rather than be removed.
    sheet.evaluate("""el => el.addEventListener('gravewright:sheet-flush', event => {
      event.detail.waitUntil(new Promise(resolve => setTimeout(() => {
        window.escapeFlushCompleted = true; resolve();
      }, 100)));
    }, {once:true})""")
    sheet.locator('.gw-window__titlebar').click(position={'x': 80, 'y': 12})
    page.keyboard.press('Escape')
    expect(sheet).to_have_count(0)
    assert page.evaluate('window.escapeFlushCompleted')
    expect(journal).to_be_visible()

    # Focused inputs are not excluded, and the modal closes ahead of its journal.
    page.evaluate("""async () => {
      const {openFormModal} = await import('/static/gravewright_table/form-modal.js');
      window.reviewModal = openFormModal('Escape review', [{name:'name', label:'Name'}], () => {});
    }""")
    modal = page.locator('.table-form-modal')
    modal.locator('input').fill('Unsaved modal input')
    page.keyboard.press('Escape')
    expect(modal).to_have_count(0)
    expect(journal).to_be_visible()

    # Busy close guards consume Escape without closing a window behind them.
    page.evaluate("""async () => {
      const {mountModal} = await import('/static/gravewright_table/modal.js');
      const modal = document.createElement('section'); modal.id = 'busy-review';
      modal.innerHTML = '<input aria-label="Busy input">';
      window.reviewBusy = true;
      window.reviewModal = mountModal(modal, {canClose: () => !window.reviewBusy});
    }""")
    page.keyboard.press('Escape')
    expect(page.locator('#busy-review')).to_be_visible()
    expect(journal).to_be_visible()
    page.evaluate('window.reviewBusy = false')
    page.keyboard.press('Escape')
    expect(page.locator('#busy-review')).to_have_count(0)

    # The same shortcut works after adoption into an independent browser window.
    with page.expect_popup() as opened:
        journal.locator('[data-action=detach]').click()
    popup = opened.value
    expect(popup.locator('.journal-window')).to_be_visible()
    with popup.expect_event('close'):
        try:
            popup.keyboard.press('Escape')
        except TargetClosedError:
            pass  # The close lifecycle can finish before keyup is delivered.
    expect(page.locator('.journal-window')).to_have_count(0)

    # A confirmation uses Cancel, never the destructive action.
    page.evaluate("""() => {
      const modal = document.getElementById('journal-confirm').content.firstElementChild.cloneNode(true);
      modal.id = 'confirm-review';
      modal.querySelector('button').onclick = () => { window.escapeDeleted = true; };
      modal.querySelector('[data-escape-close]').onclick = () => modal.remove();
      document.body.append(modal);
    }""")
    page.keyboard.press('Escape')
    expect(page.locator('#confirm-review')).to_have_count(0)
    assert not page.evaluate('!!window.escapeDeleted')

    # Search owns Escape even though its results use a listbox.
    page.keyboard.press('Control+k')
    expect(page.locator('[data-command-palette]')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('[data-command-palette]')).to_be_hidden()

    for panel_name, panel_id in [('scenes', 'maps'), ('actors', 'actors'), ('journals', 'journals'),
                                 ('chat', 'chat'), ('items', 'items'), ('combat', 'combat'),
                                 ('content', 'compendiums')]:
        page.locator(f'[data-panel="{panel_name}"]').click()
        panel = page.locator(f'#{panel_id}-panel')
        expect(panel).to_be_visible()
        page.keyboard.press('Escape')
        expect(panel).to_be_hidden()

    for section in ['table', 'extensions', 'preferences']:
        page.locator('.game-menubar__logo').click()
        house = page.locator('.house-menu')
        expect(house).to_be_visible()
        house.locator('.house-menu__section').nth(['table', 'extensions', 'preferences'].index(section)).click()
        page.keyboard.press('Escape')
        expect(house).to_be_hidden()

    page.locator('.game-menubar__roster > button').click()
    expect(page.locator('.game-roster')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('.game-roster')).to_be_hidden()
    assert not errors, errors
    print('PASS: sheet flush, stacked windows, inputs, modal guard, detached journal, cancellation, search, 7 directories, settings tabs and roster.')
    browser.close()
