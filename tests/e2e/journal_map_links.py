"""Document links and persistent scene markers against the isolated fixture."""
import json
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SEED = json.loads((ROOT / 'data/permissions-review-seed.json').read_text())
BASE = 'http://127.0.0.1:30002'
URL = f'{BASE}/game/{SEED["campaign"]}'


def login(browser, index):
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    context.add_cookies([{**SEED['sessions'][index], 'url': BASE}])
    page = context.new_page()
    page.goto(URL)
    page.wait_for_function('Boolean(window.gravewrightMaps?.current && window.gravewrightJournals && window.gravewrightItems)')
    expect(page.locator('.journal-map-pins')).to_be_attached()
    if index:
        page.wait_for_function('document.querySelector("#table-workspace").dataset.onboardingReady === "true"')
    page.keyboard.press('Escape')
    return context, page


def drop(page, source, target='.game-board__surface'):
    page.locator(source).evaluate('''(source, target) => {
      const transfer = new DataTransfer();
      source.dispatchEvent(new DragEvent('dragstart', {bubbles: true, dataTransfer: transfer}));
      const surface = document.querySelector(target), rect = surface.getBoundingClientRect();
      surface.dispatchEvent(new DragEvent('drop', {bubbles: true, cancelable: true,
        clientX: rect.left + 250, clientY: rect.top + 220, dataTransfer: transfer}));
    }''', target)


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context, gm = login(browser, 0)
    errors = []
    gm.on('pageerror', lambda error: errors.append(str(error)))
    # Start from a clean fixture scene, making this check repeatable.
    pins = gm.request.get(f'{BASE}/api/maps/{SEED["scene"]}/state').json()['journalPins']
    for pin in pins:
        gm.evaluate('(pin) => window.gravewrightRealtime.mapCommand("objects", {mapId: window.gravewrightMaps.current.id, area:"journalPins", action:"delete", data:{id:pin.id,version:pin.version}})', pin)
    gm.evaluate('''async id => {
      const {initialContent} = await import('/static/gravewright_table/content-state.js');
      const journal = initialContent('journals').journals.find(j => j.id === id);
      await window.gravewrightRealtime.journalCommand('update', {journal_id: id, title: journal.title,
        visibility: journal.visibility, version: journal.version,
        data: {sections: [{id:'page',title:'Ownership page',kind:'text'}]}});
    }''', SEED['journal'])
    book = gm.evaluate('''async () => {
      const {initialContent} = await import('/static/gravewright_table/content-state.js');
      return initialContent('journals').journals.find(j => j.title === 'Presentation book').id;
    }''')
    gm.evaluate('(id) => window.gravewrightJournals.open(id)', book)
    book_window = gm.locator(f'.journal-window[data-journal-id="{book}"]')
    expect(book_window).to_be_visible()
    surface = gm.locator('.game-board__surface')
    point = surface.evaluate('''surface => {
      const rect = surface.getBoundingClientRect();
      for (let y = rect.height - 40; y > 12; y -= 25) for (let x = rect.width - 12; x > 12; x -= 25)
        if (surface.contains(document.elementFromPoint(rect.left+x, rect.top+y))) return {x,y};
      throw Error('Move the journal to expose the scene before dragging.');
    }''')
    book_window.locator('[data-page-id=second]').drag_to(surface,
        target_position=point)
    expect(gm.locator('.journal-map-pin')).to_have_count(1)
    expect(gm.locator('.journal-map-pins__status')).to_be_hidden()
    pin = gm.request.get(f'{BASE}/api/maps/{SEED["scene"]}/state').json()['journalPins'][0]
    assert pin['pageId'] == 'second' and pin['journalId'] == book and not pin['public']
    book_window.locator('[data-action=close]').click()
    gm.locator('.journal-map-pin').click()
    expect(book_window.locator('[data-page-id=second]')).to_have_attribute('aria-current', 'page')
    # Clicking an existing marker also changes the page of an already-open book.
    book_window.locator('[data-page-id=first]').click()
    gm.locator('.journal-map-pin').dispatch_event('click')
    expect(book_window.locator('[data-page-id=second]')).to_have_attribute('aria-current', 'page')
    book_window.locator('[data-action=close]').click()
    gm.reload(); expect(gm.locator('.journal-map-pin')).to_have_count(1)
    player_context, player = login(browser, 1)
    expect(player.locator('.journal-map-pin')).to_have_count(0)
    # A shared journal location is independently shared, and can be moved and removed.
    gm.evaluate('(id) => window.gravewrightJournals.open(id)', SEED['journal'])
    journal = gm.locator(f'.journal-window[data-journal-id="{SEED["journal"]}"]')
    drop(gm, f'[data-journal-id="{SEED["journal"]}"] [data-page-id=page]')
    expect(gm.locator('.journal-map-pin')).to_have_count(2)
    journal.locator('[data-action=close]').click()
    shared_pin = gm.locator('.journal-map-pin[aria-label="Ownership page"]')
    shared_pin.click(button='right')
    modal = gm.locator('.table-form-modal')
    expect(modal).to_be_visible()
    assert modal.evaluate('el => el.tagName') == 'SECTION'
    assert modal.bounding_box()['width'] <= 420
    gm.screenshot(path=str(ROOT / 'data/journal-marker-options.png'))
    modal.locator('[name=public]').check()
    expect(modal.locator('[name=x],[name=y]')).to_have_count(0)
    modal.locator('[type=submit]').click()
    expect(modal).to_have_count(0)
    expect(player.locator('.journal-map-pin')).to_have_count(1)
    before = next(pin for pin in gm.request.get(f'{BASE}/api/maps/{SEED["scene"]}/state').json()['journalPins'] if pin['journalId'] == SEED['journal'])
    box = shared_pin.bounding_box()
    gm.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
    gm.mouse.down(); gm.mouse.move(box['x'] + box['width']/2 + 50, box['y'] + box['height']/2 + 25, steps=5); gm.mouse.up()
    gm.wait_for_function('''async data => {
      const state = await (await fetch(`/api/maps/${data.scene}/state`)).json();
      const pin = state.journalPins.find(pin => pin.id === data.id);
      return pin.version > data.version && pin.x !== data.x;
    }''', arg={'scene':SEED['scene'], **before})
    expect(gm.locator('.journal-window')).to_have_count(0)
    player.locator('.journal-map-pin').click()
    expect(player.locator('.journal-window [data-page-id=page]')).to_have_attribute('aria-current', 'page')
    gm.evaluate('(id) => window.gravewrightJournals.open(id)', SEED['journal'])
    # Typing @ opens the permission-filtered campaign resource catalog.
    journal.locator('.tiptap[contenteditable=true]').first.focus()
    gm.keyboard.press('Control+End'); gm.keyboard.type(' @')
    modal = gm.locator('[data-resource-picker]')
    modal.locator('input[type=search]').fill('Ownership hero')
    modal.locator('select:not([size])').select_option('actor')
    expect(modal.locator('select[size] option')).to_have_text(['Ownership hero'])
    modal.locator('select[size]').select_option('0')
    modal.locator('[type=submit]').click()
    expect(journal.locator('[data-gw-resource-link]').filter(has_text='Ownership hero')).to_have_count(1)
    # Items and quest cards use the same draggable reference payload.
    gm.locator('button[data-panel=items]').click()
    drop(gm, f'.item-card[data-item-id="{SEED["item"]}"]', '.journal-rich-text__surface .tiptap')
    expect(journal.locator('[data-gw-resource-link]').filter(has_text='Ownership item')).to_have_count(1)
    gm.locator('[data-native-directory=items] [data-close]').click()
    journal.locator('[data-gw-resource-link][data-resource-state=available]').filter(has_text='Ownership item').click()
    expect(gm.locator('.item-sheet')).to_be_visible()
    gm.locator('.item-sheet [data-close]').click()
    # Quest board cards can create locations and insert a reference into prose.
    board = gm.evaluate('''async () => {
      const {initialContent} = await import('/static/gravewright_table/content-state.js');
      const rows = initialContent('journals').journals;
      const quest = rows.find(j => j.type === 'quest'), board = rows.find(j => j.type === 'quest_board');
      await window.gravewrightRealtime.journalCommand('status', {journal_id: quest.id, status:'available'});
      await window.gravewrightRealtime.journalCommand('board-add', {journal_id: board.id, quest_id: quest.id});
      window.gravewrightJournals.open(board.id);
      return {id:board.id, quest:quest.id};
    }''')
    board_window = gm.locator(f'.journal-window[data-journal-id="{board["id"]}"]')
    expect(board_window.locator('article[data-status=available]')).to_be_visible()
    card = f'[data-journal-id="{board["id"]}"] article[data-status=available]'
    drop(gm, card)
    expect(gm.locator('.journal-map-pin')).to_have_count(3)
    drop(gm, card, '.journal-rich-text__surface .tiptap')
    expect(journal.locator('[data-gw-resource-link]').filter(has_text='Ownership quest')).to_have_count(1)
    board_window.locator('[data-action=close]').click()
    # Wait for the autosave acknowledgment, then verify links survive a full reload.
    gm.wait_for_function('document.querySelector(".journal-window__save")?.textContent === "Saved"')
    journal.locator('[data-action=close]').click()
    gm.reload(); expect(gm.locator('.journal-map-pin')).to_have_count(3)
    gm.evaluate('(id) => window.gravewrightJournals.open(id)', SEED['journal'])
    for label in ('Ownership hero', 'Ownership item', 'Ownership quest'):
        expect(journal.locator('[data-gw-resource-link]').filter(has_text=label)).to_have_count(1)
    journal.locator('[data-action=close]').click()
    # The page deep link has a valid table URL and also works in a fresh tab.
    deep = context.new_page()
    deep.goto(URL + '?document=journal:' + book + '&page=second')
    expect(deep.locator('.journal-window [data-page-id=second]')).to_have_attribute('aria-current', 'page')
    deep.close()
    # Changing document permissions removes and restores an already-shared pin live.
    for access, count in [('none', 0), ('read', 1)]:
        gm.evaluate('''async data => {
          const response = await fetch(`/api/containers/${data.table}/ownership/journals/${data.id}`);
          const current = await response.json();
          const token = document.cookie.split('; ').find(v => v.startsWith('gravewright-csrf=')).split('=').slice(1).join('=');
          const saved = await fetch(`/api/containers/${data.table}/ownership/journals/${data.id}`, {
            method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':decodeURIComponent(token)},
            body:JSON.stringify({version:current.version,permissions:{default:data.access}})});
          if (!saved.ok) throw Error(await saved.text());
        }''', {'table':SEED['campaign'], 'id':SEED['journal'], 'access':access})
        expect(player.locator('.journal-map-pin')).to_have_count(count)
    player.locator('.journal-map-pin').focus()
    player.keyboard.press('Delete')
    expect(player.locator('.journal-map-pin')).to_have_count(1)
    # Text editing must never delete a map marker.
    gm.evaluate('(id) => window.gravewrightJournals.open(id)', SEED['journal'])
    title = journal.locator('.journal-window__title')
    title.focus()
    gm.keyboard.press('Delete')
    expect(gm.locator('.journal-map-pin')).to_have_count(3)
    journal.locator('[data-action=close]').click()
    shared_pin.focus()
    gm.keyboard.press('Delete')
    expect(player.locator('.journal-map-pin')).to_have_count(0)
    expect(gm.locator('.journal-map-pin')).to_have_count(2)
    gm.locator('.journal-map-pin[aria-label="Second public page"]').focus()
    gm.keyboard.press('Backspace')
    expect(gm.locator('.journal-map-pin')).to_have_count(1)
    assert errors == [], errors
    context.close(); player_context.close(); browser.close()
    print('Journal map links: exact pages, persistence, player visibility and document references passed.')
