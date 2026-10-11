"""Check complete custom actor/token bodies and the bundled PDF provider."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
seed = json.loads((ROOT / 'data/system-sheets-seed.json').read_text())
base = 'http://127.0.0.1:30003'
module = """
export default {
  start(){}, stop(){},
  register({register}) {
    register('actor.sheet', { mode:'replace', types:['hero'], async mount({root, context, api, signal}) {
      const view = await api.actors.sheet(context.actorId, context.tokenId ? {tokenId:context.tokenId} : {});
      const title = document.createElement('h2'); title.textContent = context.tokenId ? 'Custom token sheet' : 'Custom actor sheet';
      const input = document.createElement('input'); input.type='number'; input.value=view.data.health; input.dataset.health='';
      const save = document.createElement('button'); save.textContent='Save health';
      save.onclick = async () => {
        const current = await api.actors.sheet(context.actorId, context.tokenId ? {tokenId:context.tokenId} : {});
        await api.actors.saveSheet({actorId:context.actorId,tokenId:context.tokenId,name:current.name,version:current.version,sheetVersion:current.sheetVersion,data:{health:Number(input.value)}});
        save.dataset.saved='true';
      };
      root.append(title,input,save);
      root.closest('.gw-window').addEventListener('gravewright:sheet-flush', event => {
        if(root.dataset.rejectClose) event.detail.waitUntil(Promise.reject(Error('Unsaved review change')));
      },{signal});
    } });
  }
};
"""
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(viewport={'width': 1440, 'height': 1000})
    context.add_cookies([{**seed['session'], 'url': base}])
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    requests = []
    page.on('request', lambda request: requests.append(request.url))
    page.route('**/api/module-packages/review.rules/**/main.js', lambda route: route.fulfill(body=module, content_type='text/javascript'))
    page.goto(base + '/game/' + seed['custom']['campaign'])
    page.wait_for_function('!!window.gravewrightActors')
    page.evaluate('(id)=>window.gravewrightActors.open(id)', seed['custom']['actor'])
    sheet = page.locator('.actor-directory__sheet')
    expect(sheet.get_by_role('heading', name='Custom actor sheet')).to_be_visible()
    expect(sheet.locator('.pdf-sheet__tabs')).to_have_count(0)
    assert not any('/gravewright_pdf_system/' in url for url in requests), requests
    sheet.locator('[data-health]').fill('8')
    sheet.get_by_role('button', name='Save health').click()
    expect(sheet.locator('[data-saved=true]')).to_be_visible()
    sheet.locator('[data-window=minimize]').click()
    expect(sheet.locator('.gw-window__body')).to_be_hidden()
    sheet.locator('[data-window=minimize]').click()
    expect(sheet.locator('.gw-window__body')).to_be_visible()
    with page.expect_popup() as event:
        sheet.locator('[data-window=detach]').click()
    popup = event.value
    expect(popup.get_by_role('heading', name='Custom actor sheet')).to_be_visible()
    popup.close()
    expect(sheet.get_by_role('heading', name='Custom actor sheet')).to_be_visible()
    sheet.locator('.gw-module-root').evaluate('(el)=>el.dataset.rejectClose="true"')
    sheet.locator('[data-window=close]').click()
    expect(sheet.get_by_role('alert')).to_have_text('Unsaved review change')
    sheet.locator('.gw-module-root').evaluate('(el)=>delete el.dataset.rejectClose')
    sheet.locator('[data-window=close]').click()
    expect(sheet).to_have_count(0)
    # A normal reload must reuse one version of entry modules and imports;
    # opening a sheet must not depend on a hard refresh of old cached files.
    page.reload()
    page.get_by_role('button', name='Token: custom hero', exact=True).press('Enter')
    token_sheet = page.locator('.token-sheet')
    expect(token_sheet.get_by_role('heading', name='Custom token sheet')).to_be_visible()
    expect(token_sheet.locator('[data-health]')).to_have_value('8')
    expect(token_sheet.locator('.pdf-sheet__tabs')).to_have_count(0)
    token_sheet.locator('[data-window=close]').click()
    page.goto(base + '/game/' + seed['pdf']['campaign'])
    page.wait_for_function('!!window.gravewrightActors')
    page.evaluate('(id)=>window.gravewrightActors.open(id)', seed['pdf']['actor'])
    sheet = page.locator('.actor-directory__sheet')
    expect(sheet.locator('.pdf-sheet__tabs')).to_be_visible()
    expect(sheet.locator('[data-panel=ficha]')).to_be_visible()
    sheet.locator('[data-tab=token]').click()
    expect(sheet.locator('[data-panel=token]')).to_be_visible()
    sheet.locator('[data-field=name]').fill('Renamed PDF hero')
    sheet.locator('[data-tab=notas]').click()
    expect(sheet.locator('[data-panel=notas]')).to_be_visible()
    sheet.locator('[data-window=close]').click()
    expect(sheet).to_have_count(0)
    page.evaluate('(id)=>window.gravewrightActors.open(id)', seed['pdf']['actor'])
    expect(sheet.locator('.actor-directory__sheet-heading strong')).to_have_text('Renamed PDF hero')
    for path in ['gravewright_actors/workspace.js', 'gravewright_actors/sheet.js', 'gravewright_modules/workspace.js']:
        urls = [url for url in requests if '/static/' + path in url]
        assert urls and all('?v=' in url for url in urls), (path, urls)
    assert not errors, errors
    browser.close()
print('Complete actor/token system sheets, persistence, window controls and PDF compatibility passed.')
