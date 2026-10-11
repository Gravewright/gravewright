"""Verify scene-first startup and reconnect against ownership_server.py."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
SEED = json.loads((ROOT / 'data/permissions-review-seed.json').read_text())
BASE = 'http://127.0.0.1:30002'

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1280, 'height': 900})
    context.add_cookies([{**SEED['sessions'][0], 'url': BASE}])
    page = context.new_page()
    # The scene starts from the page snapshot; directories wait for its initial render.
    held = []
    page.route('**/api/maps/*/manifest', lambda route: held.append(route))
    page.add_init_script('''
      window.restorationOrder = [];
      new MutationObserver(records => {
        for (const record of records) for (const node of record.addedNodes) {
          if (node.nodeType !== 1) continue;
          const found = node.matches('canvas') || node.querySelector('canvas') ? 'scene'
            : record.target.closest('#actors-panel') && node.textContent.includes('Ownership hero') ? 'actors'
            : record.target.closest('#journals-panel') && node.textContent.includes('Ownership journal') ? 'journals'
            : node.matches('.item-card') ? 'items' : null;
          if(found && !restorationOrder.includes(found)) restorationOrder.push(found);
        }
      }).observe(document, {childList:true, subtree:true});
    ''')
    page.route_web_socket('**/ws/tables/**', lambda socket: None)
    page.goto(f'{BASE}/game/{SEED["campaign"]}', wait_until='domcontentloaded')
    page.wait_for_function('Boolean(window.gravewrightJournals?.open && window.gravewrightMaps?.current)')
    assert held
    expect(page.locator('#actors-panel strong').get_by_text('Ownership hero', exact=True)).to_have_count(0)
    expect(page.locator('#journals-panel strong').get_by_text('Ownership journal', exact=True)).to_have_count(0)
    expect(page.locator('.item-card')).to_have_count(0)
    for route in held:
        route.continue_()
    page.locator('button[data-panel=actors]').click()
    party = page.locator('#actors-panel .gw-folder__toggle').filter(has_text='Party')
    expect(party).to_be_visible()
    if party.get_attribute('aria-expanded') != 'true':
        party.click()
    expect(page.locator('#actors-panel strong').get_by_text('Ownership hero', exact=True)).to_be_visible()
    page.locator('#actors-panel strong').get_by_text('Ownership hero', exact=True).click()
    expect(page.locator('.actor-directory__sheet')).to_be_visible()
    expect(page.locator('.actor-directory__sheet .pdf-sheet__loading')).to_be_hidden(timeout=15000)
    page.locator('.actor-directory__sheet [data-window=close]').click()
    page.locator('button[data-panel=journals]').click()
    expect(page.locator('#journals-panel strong').get_by_text('Ownership journal', exact=True)).to_be_visible()
    page.locator('#journals-panel strong').get_by_text('Ownership journal', exact=True).click()
    expect(page.locator('.journal-window')).to_be_visible()
    expect(page.locator('[data-page-id=page]')).to_be_visible()
    expect(page.locator('.item-card')).to_have_count(1)
    assert page.evaluate('restorationOrder') == ['scene', 'actors', 'journals', 'items']
    print('Restored in order: scene, actors, journals, then items; WebSocket blocked.', flush=True)
    page.close()
    failed_scene = context.new_page()
    failed_scene.route_web_socket('**/ws/tables/**', lambda socket: None)
    failed_scene.route('**/api/maps/*/manifest', lambda route: route.fulfill(status=403, body='{}'))
    failed_scene.goto(f'{BASE}/game/{SEED["campaign"]}', wait_until='domcontentloaded')
    expect(failed_scene.locator('#journals-panel strong').get_by_text('Ownership journal', exact=True)).to_have_count(1)
    expect(failed_scene.locator('.item-card')).to_have_count(1)
    failed_scene.close()
    page = context.new_page()
    page.add_init_script('''
      window.reviewSockets = [];
      const NativeSocket = window.WebSocket;
      window.WebSocket = class extends NativeSocket {
        constructor(...args) { super(...args); this.sentTypes = []; reviewSockets.push(this); }
        send(value) { this.sentTypes.push(JSON.parse(value).type); super.send(value); }
      };
      window.startupMarks = {};
      for (const name of ['connected', 'maps', 'module-scene'])
        window.addEventListener('gravewright:' + name, () => {
          if (name === 'module-scene' && !window.gravewrightMaps?.board) return;
          startupMarks[name] ??= performance.now();
        });
    ''')
    for run in range(2):
        page.goto(f'{BASE}/game/{SEED["campaign"]}', wait_until='domcontentloaded')
        page.wait_for_function("Boolean(startupMarks['module-scene'] && startupMarks.maps && startupMarks.connected)", timeout=60000)
        result = page.evaluate(r'''() => {
          const resources = performance.getEntriesByType('resource');
          const manifest = resources.find(r => r.name.endsWith('/manifest'));
          const state = resources.find(r => /\/api\/maps\/[^/]+\/state$/.test(r.name));
          return {marks: startupMarks, types: reviewSockets[0].sentTypes,
                  parallel: Math.abs(manifest.startTime - state.startTime),
                  current: gravewrightMaps.current.id};
        }''')
        assert result['current'] == SEED['scene']
        assert result['types'][0] == 'maps.sync', result['types']
        assert result['types'][:3] == ['maps.sync', 'actors.sync', 'journals.sync'], result['types']
        assert result['types'].count('maps.sync') == 1, result['types']
        assert result['types'].count('actors.sync') <= 1, result['types']
        assert result['types'].count('journals.sync') <= 1, result['types']
        assert result['parallel'] < 60, result['parallel']
        assert page.evaluate('''() => {
          gravewrightRealtime.subscribeModule('items', gravewrightMaps.current.id);
          const before = reviewSockets[0].sentTypes.length;
          gravewrightRealtime.subscribeModule('items', gravewrightMaps.current.id);
          return reviewSockets[0].sentTypes.length === before;
        }''')
        print(f'Startup {run + 1}: scene restored in {result["marks"]["module-scene"]:.0f} ms; '
              f'{result["marks"]["maps"] - result["marks"]["connected"]:.0f} ms from connection to scene state.', flush=True)
    page.evaluate('reviewSockets[0].close(4000, "startup reconnect test")')
    page.wait_for_function("reviewSockets.length > 1 && reviewSockets[1].sentTypes.includes('journals.sync')", timeout=30000)
    types = page.evaluate('reviewSockets[1].sentTypes')
    assert types[0] == 'maps.sync', types
    assert types.count('maps.sync') == 1, types
    assert types.count('actors.sync') == 1, types
    assert types.count('journals.sync') == 1, types
    assert page.evaluate('gravewrightMaps.current.id') == SEED['scene']
    browser.close()
    print('Table startup checks passed: scene priority, parallel reads, single subscriptions and reconnect restoration.')
