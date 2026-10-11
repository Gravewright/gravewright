"""Installed module controls against the isolated fixture and mocked marketplace."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT = Path(__file__).resolve().parents[2]
seed=json.loads((ROOT / 'data/permissions-review-seed.json').read_text())
base='http://127.0.0.1:30002'
packages=[{'id':'review.dice','version':'1.0.0','name':'Gravewright 3D Dice'},{'id':'review.translator','version':'1.0.0','name':'Translator','globalEnabled':True,'locales':{'pt-BR':{'name':'Português','path':'pt.json'}}}]
calls=[]
with sync_playwright() as p:
 browser=p.chromium.launch()
 context=browser.new_context(viewport={'width':1440,'height':900})
 context.add_cookies([{**seed['sessions'][0],'url':base}])
 page=context.new_page()
 errors=[]
 page.on('pageerror',lambda error:errors.append(str(error)))
 page.route('**/api/module-packages',lambda route:route.fulfill(json=packages))
 def update(route):
  payload=route.request.post_data_json;calls.append(('update',payload))
  packages[0]['version']='1.1.0'
  route.fulfill(json={'updated':True,'version':'1.1.0'})
 def remove(route):
  payload=route.request.post_data_json;calls.append(('remove',payload))
  packages[:]=[row for row in packages if row['id']!=payload['id']]
  route.fulfill(json={'removed':True})
 page.route('**/api/module-packages/update',update)
 page.route('**/api/module-packages/remove',remove)
 page.route('**/api/module-packages/removal-preview',lambda route:route.fulfill(json={'tables':[{'id':seed['campaign'],'name':'Permissions browser review'}],'system':False}))
 page.goto(base+'/inside')
 page.get_by_role('button',name='Modules',exact=True).click()
 card=page.locator('[data-module-catalog=installed] [data-package-id="review.dice"]')
 expect(card).to_be_visible()
 expect(card.locator('[data-action=update]')).to_be_visible()
 expect(card.locator('[data-action=remove]')).to_be_visible()
 page.screenshot(path=str(ROOT / 'data/module-actions-review.png'))
 card.locator('[data-action=update]').click()
 expect(card.locator('[data-version]')).to_have_text('v1.1.0')
 card.locator('[data-action=remove]').click()
 modal=page.locator('.package-removal [role=dialog]')
 expect(modal).to_be_visible()
 expect(modal.locator('li')).to_have_text('Permissions browser review')
 modal.locator('[data-cancel]').click()
 expect(card).to_be_visible()
 assert len(calls)==1,calls
 card.locator('[data-action=remove]').click()
 modal.locator('[data-remove]').click()
 expect(card).to_have_count(0)
 assert calls==[('update',{'id':'review.dice','version':'1.0.0'}),('remove',{'id':'review.dice','version':'1.1.0','confirmedTables':[seed['campaign']]})],calls
 # Installed packages also expose actions in the Marketplace browser.
 page.route('**/api/marketplace/status',lambda route:route.fulfill(json={'ready':True}))
 page.route('**/api/marketplace',lambda route:route.fulfill(json=packages))
 page.get_by_role('button',name='Install module',exact=True).click()
 market=page.locator('[data-module-catalog=marketplace] [data-package-id="review.translator"]')
 expect(market.locator('[data-action=update]')).to_be_visible()
 expect(market.locator('[data-action=remove]')).to_be_visible()
 page.locator('[data-action=close-browser]').click()
 # Systems share both installed and Marketplace controls.
 packages.append({'id':'review.system','version':'1.0.0','name':'Review system','system':{'actorTypes':[{'id':'character','label':'Character'}]}})
 page.get_by_role('button',name='Systems',exact=True).click()
 system=page.locator('[data-module-catalog=installed] [data-package-id="review.system"]')
 expect(system.locator('[data-action=update]')).to_be_visible()
 expect(system.locator('[data-action=remove]')).to_be_visible()
 page.get_by_role('button',name='Install system',exact=True).click()
 system_market=page.locator('[data-module-catalog=marketplace] [data-package-id="review.system"]')
 expect(system_market.locator('[data-action=update]')).to_be_visible()
 expect(system_market.locator('[data-action=remove]')).to_be_visible()
 page.locator('[data-action=close-browser]').click()
 # The in-game extensions list includes all package kinds and lifecycle actions.
 packages.append({'id':'review.tools','version':'1.0.0','name':'Review tools'})
 page.goto(base+'/game/'+seed['campaign'])
 page.wait_for_function('document.querySelector("#table-workspace").dataset.onboardingReady === "true"')
 page.locator('.game-menubar__logo').click()
 page.locator('.house-menu__section').nth(1).click()
 pane=page.locator('[data-table-modules]')
 tools=pane.locator('[data-package-id="review.tools"]')
 expect(tools).to_be_visible()
 for package_id in ['review.tools','review.translator','review.system']:
  installed=pane.locator('[data-package-id="'+package_id+'"]')
  expect(installed.locator('[data-action=update]')).to_be_visible()
  expect(installed.locator('[data-action=remove]')).to_be_visible()
 tools.locator('[data-action=remove]').click()
 expect(modal).to_be_visible()
 page.screenshot(path=str(ROOT / 'data/module-removal-confirmation.png'))
 modal.locator('[data-remove]').click()
 expect(tools).to_have_count(0)
 assert not errors,errors
 print('Playwright: update/remove buttons and payloads passed; no browser errors.')
 browser.close()
