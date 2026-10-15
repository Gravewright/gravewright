"""Native compendium layout, sorting, authorized preview and copy regression.

Start compendium_server.py with a fresh fixture, optionally supplying browser
system ZIPs, and pass its seed.json. Every mutation below is fixture-scoped.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from playwright.sync_api import expect, sync_playwright


MEASURE = """root=>{
 const visible=el=>el.checkVisibility({checkVisibilityCSS:true})&&!el.closest('[hidden]');
 const rect=root.getBoundingClientRect(),tiny=[],overflow=[];
 for(const el of [root,...root.querySelectorAll('*')]){
  if(!visible(el)||el.closest('svg')||el.matches('option'))continue;
  const css=getComputedStyle(el),r=el.getBoundingClientRect();
  const text=[...el.childNodes].some(n=>n.nodeType===3&&n.textContent.trim());
  if((text||el.matches('input,select,textarea'))&&parseFloat(css.fontSize)<12)tiny.push({tag:el.tagName,size:css.fontSize});
  if(r.width>0&&(r.left<rect.left-2||r.right>rect.right+2))overflow.push({tag:el.tagName,cls:el.className});
 }
 return {x:rect.x,y:rect.y,width:rect.width,height:rect.height,tiny,overflow};
}"""


def api(page, code, payload=None):
    return page.evaluate('async args=>{'+code+'}', payload)


def locale(page, value, campaign):
    result = api(page, """
      const response=await fetch('/__gravewright/csrf',{credentials:'same-origin'}),csrf=await response.json();
      const changed=await fetch('/inside/language',{method:'POST',credentials:'same-origin',
        headers:{Accept:'application/json',[csrf.header]:csrf.token,'Content-Type':'application/x-www-form-urlencoded'},
        body:new URLSearchParams({locale:args.locale,next:'/game/'+args.campaign})});
      return {status:changed.status,body:await changed.json()};
    """, {'locale': value, 'campaign': campaign})
    assert result['status'] == 200, result
    page.reload(); page.wait_for_function('v=>window.gravewright?.i18n.locale===v', arg=value)


def open_directory(page, base, seed):
    page.goto(base+'/game/'+seed['campaign'])
    page.wait_for_function('!!window.gravewrightActors && !!window.gravewrightItems')
    page.locator('[data-native-directory-toggle=content]').click()
    panel = page.locator('#compendiums-panel')
    expect(panel).to_be_visible(); expect(panel.locator('.gw-compendiums')).to_be_visible()
    return panel


def alphabetical(page, values):
    return page.evaluate("values=>values.toSorted(new Intl.Collator(gravewright.i18n.locale,{sensitivity:'base',numeric:true}).compare)", values)


def check_window_controls(page, panel):
    before=panel.bounding_box();panel.locator('[data-window-action=minimize]').click()
    assert panel.bounding_box()['height']<80
    panel.locator('[data-window-action=minimize]').click()
    assert abs(panel.bounding_box()['height']-before['height'])<2
    # Move away from the right edge before exercising the actual resize handle.
    box=panel.bounding_box();header=panel.locator(':scope>header').bounding_box()
    page.mouse.move(box['x']+80,header['y']+16);page.mouse.down()
    page.mouse.move(box['x']-220,header['y']+16,steps=6);page.mouse.up()
    box=panel.bounding_box()
    page.mouse.move(box['x']+box['width']-3,box['y']+box['height']-3);page.mouse.down()
    page.mouse.move(box['x']+box['width']+40,box['y']+box['height']+60,steps=6);page.mouse.up()
    resized=panel.bounding_box();assert resized['height']>box['height']+30,(box,resized)
    panel.locator('input[type=search]').fill('No matches after manual resize')
    assert abs(panel.bounding_box()['height']-resized['height'])<2
    panel.locator('[data-close]').click();page.locator('[data-native-directory-toggle=content]').click()
    assert abs(panel.bounding_box()['height']-resized['height'])<2
    panel.locator('[data-window-action=reset]').click()
    assert panel.bounding_box()['height']<250
    return panel.evaluate(MEASURE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'test-results/compendiums')
    parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--windows-only', action='store_true', help='Review only native window controls on both systems.')
    args = parser.parse_args()
    seed = json.loads(args.seed.read_text(encoding='utf-8'))
    assert seed.get('kind') == 'compendium-layout-review', 'Use a disposable compendium_server.py fixture.'
    assert (Path(seed['fixture'])/'review.sqlite3').is_file()
    from scripts.runtime_storage import configure_runtime_storage
    configure_runtime_storage(ROOT, 'data/runner/compendium-layout')
    args.output.mkdir(parents=True, exist_ok=True)
    base = seed['base']; records = []; errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(**({'executable_path':str(args.browser_executable)} if args.browser_executable else {}))
        for system, data in seed['systems'].items():
            key = system.replace('.', '-')
            if args.windows_only:
                context=browser.new_context(viewport={'width':1440,'height':900})
                context.add_cookies([{**data['sessions']['gm'],'url':base}]);page=context.new_page()
                panel=open_directory(page,base,data)
                pack=next(v for v in data['packs'] if v['name']=='Alfa review')
                panel.locator('.gw-compendiums__filters select').nth(1).select_option(pack['id'])
                metrics=check_window_controls(page,panel)
                records.append({'system':system,'case':'window-controls','viewport':{'width':1440,'height':900},**metrics})
                page.screenshot(path=str(args.output/f'{key}-window-controls.png'));context.close()
                continue
            for width, height in [(1440,900),(390,844),(320,700)]:
                context = browser.new_context(viewport={'width':width,'height':height})
                context.add_cookies([{**data['sessions']['gm'],'url':base}]); page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                panel = open_directory(page, base, data)
                for language in ('en','pt-BR','es'):
                    locale(page, language, data['campaign'])
                    page.locator('[data-native-directory-toggle=content]').click(); expect(panel).to_be_visible()
                    initial = api(page, 'return await gravewright.compendiums.state();')
                    names = panel.locator('.gw-compendiums__pack-name').all_text_contents()
                    assert names == alphabetical(page, names), names
                    options = panel.locator('.gw-compendiums__filters select').nth(1).locator('option').all_text_contents()[1:]
                    assert options == alphabetical(page, options), options
                    pack = next(v for v in data['packs'] if v['name']=='Alfa review')
                    panel.locator('.gw-compendiums__filters select').nth(1).select_option(pack['id'])
                    expect(panel.locator('.gw-compendiums__pack')).to_have_count(1)
                    names = panel.locator('.gw-compendiums__name').all_text_contents()
                    assert names == alphabetical(page, names), names
                    metrics = panel.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    assert metrics['width']<=width and metrics['height']<height-100, metrics
                    assert metrics['height']<400, 'A small pack must not reserve a screen-height frame.'
                    page.screenshot(path=str(args.output/f'{key}-{width}-{language}-entries.png'))
                    records.append({'system':system,'viewport':{'width':width,'height':height},'locale':language,'case':'entries',**metrics})
                    search = panel.locator('input[type=search]'); search.fill('arvore')
                    expect(panel.locator('.gw-compendiums__entry')).to_have_count(2)
                    search.fill('No synthetic matches here'); expect(panel.locator('.gw-compendiums__entry')).to_have_count(0)
                    expect(panel.locator('.gw-compendiums__empty')).to_be_visible()
                    search.fill(''); panel.locator('.gw-compendiums__filters select').first.select_option('actor')
                    expect(panel.locator('.gw-compendiums__entry')).to_have_count(1)
                    panel.locator('.gw-compendiums__filters select').first.select_option('')
                    for entry_name, case in [('Alfa hero','short'),('Long empty','empty'),('Zebra 10','long')]:
                        trigger = panel.locator('.gw-compendiums__name').filter(has_text=entry_name).first
                        trigger.click(); modal = page.locator('.gw-compendium-preview'); expect(modal).to_be_visible()
                        expect(modal.locator('.gw-compendium-preview__text')).to_be_visible()
                        metrics = modal.evaluate(MEASURE)
                        assert not metrics['tiny'] and not metrics['overflow'], metrics
                        assert metrics['x']>=0 and metrics['y']>=0 and metrics['width']<=width and metrics['height']<=height-30, metrics
                        assert case=='long' or metrics['height']<200, metrics
                        # Focus stays in the native modal, then returns to the exact entry.
                        modal.locator('footer button').focus(); page.keyboard.press('Tab')
                        expect(modal.locator('button').first).to_be_focused()
                        if case=='long':
                            body=modal.locator('.table-modal-body')
                            assert body.evaluate('el=>el.scrollHeight>el.clientHeight+100')
                            body.evaluate('el=>el.scrollTop=el.scrollHeight')
                            expect(modal.locator('footer button')).to_be_in_viewport()
                        page.screenshot(path=str(args.output/f'{key}-{width}-{language}-preview-{case}.png'))
                        records.append({'system':system,'viewport':{'width':width,'height':height},'locale':language,'case':case,**metrics})
                        page.keyboard.press('Escape'); expect(modal).to_have_count(0); expect(trigger).to_be_focused()
                    assert api(page,'return await gravewright.compendiums.state();') == initial, 'Presentation must not reorder or write stored packs.'
                context.close()
            # Every installed type and every available native pack goes through actual authorized reads/previews.
            context = browser.new_context(viewport={'width':1440,'height':900})
            context.add_cookies([{**data['sessions']['gm'],'url':base}]); page=context.new_page(); panel=open_directory(page,base,data)
            locale(page,'en',data['campaign']);page.locator('[data-native-directory-toggle=content]').click()
            current=api(page,'return await gravewright.compendiums.state();')
            samples=[]
            for pack in current['packs']:
                selected=[e for e in pack['entries'] if e['name'].startswith('Synthetic ')]
                if pack['id'].startswith('native:') and pack['entries']: selected=[pack['entries'][0]]
                for entry in selected: samples.append((pack,entry))
            for pack,entry in samples:
                panel.locator('.gw-compendiums__filters select').nth(1).select_option(pack['id'])
                trigger=panel.locator(f'.gw-compendiums__entry[data-compendium-entry="{entry["id"]}"] .gw-compendiums__name')
                trigger.click();modal=page.locator('.gw-compendium-preview');expect(modal.locator('.gw-compendium-preview__text')).to_be_visible()
                metrics=modal.evaluate(MEASURE);assert not metrics['tiny'] and not metrics['overflow'],metrics
                page.screenshot(path=str(args.output/f'{key}-type-{entry["kind"]}-{entry.get("type") or "unknown"}-{len(records)}.png'))
                records.append({'system':system,'viewport':{'width':1440,'height':900},'case':'type-preview','kind':entry['kind'],'type':entry.get('type'),'pack':pack['name'],**metrics})
                page.keyboard.press('Escape');expect(modal).to_have_count(0)
            # Import creates an independent editable document; source reads and revisions remain exact.
            pack=next(v for v in data['packs'] if v['name']=='Alfa review');entry=next(e for e in pack['entries'] if e['name']=='Árvore 2')
            payload={'packId':pack['id'],'id':entry['id']};original=api(page,'return await gravewright.compendiums.read(args);',payload)
            panel.locator('.gw-compendiums__filters select').nth(1).select_option(pack['id'])
            trigger=panel.get_by_role('button',name='Árvore 2',exact=True);trigger.click();modal=page.locator('.gw-compendium-preview');expect(modal.locator('footer button')).to_be_visible()
            before=api(page,'return (await gravewright.items.state()).items.map(i=>i.id);')
            modal.locator('footer button').click();expect(modal).to_have_count(0)
            page.wait_for_function('before=>gravewright.items.state().then(s=>s.items.some(i=>!before.includes(i.id)))',arg=before)
            copied=api(page,'return (await gravewright.items.state()).items.find(i=>!args.includes(i.id));',before)
            assert copied['name']==original['data']['name'] and copied['data']==original['data']['data'],(copied,original)
            api(page,'return await gravewright.items.update({...args,name:"Edited synthetic copy",data:{...args.data,review:{copy:"changed"}}});',copied)
            assert api(page,'return await gravewright.compendiums.read(args);',payload)==original
            # A real API failure stays in the preview and restores its action for retry.
            trigger.click();expect(modal.locator('footer button')).to_be_visible()
            def reject_import(route):
                request=route.request
                body=request.post_data_json if request.method=='POST' else {}
                if body.get('domain')=='compendiums' and body.get('method')=='import':
                    route.fulfill(status=409,content_type='application/json',body=json.dumps({'error':'conflict'}))
                else: route.continue_()
            page.route('**/api/tables/*/api',reject_import)
            modal.locator('footer button').click();expect(modal.locator('[role=alert]')).to_be_visible();expect(modal.locator('footer button')).to_be_enabled()
            page.unroute('**/api/tables/*/api',reject_import);page.keyboard.press('Escape')
            # Reader UI and API retain the server's visibility and write boundaries.
            reader_context=browser.new_context(viewport={'width':390,'height':844})
            reader_context.add_cookies([{**data['sessions']['reader'],'url':base}]);reader=reader_context.new_page();reader_panel=open_directory(reader,base,data)
            assert not reader_panel.locator('.gw-compendiums__create,.gw-compendiums__import,.gw-compendiums__permissions').count()
            assert 'Beta review' not in reader_panel.locator('.gw-compendiums__pack-name').all_text_contents()
            reader_panel.locator('.gw-compendiums__filters select').nth(1).select_option(pack['id'])
            reader_panel.get_by_role('button',name='Árvore 2',exact=True).click();expect(reader.locator('.gw-compendium-preview__text')).to_be_visible();expect(reader.locator('.gw-compendium-preview footer')).to_have_count(0)
            denied=api(reader,'try{await gravewright.compendiums.import(args);return false;}catch(error){return !!error.code;}',payload)
            assert denied is True
            reader.keyboard.press('Escape')
            # Pack permissions are still available without consuming an entire row.
            group=panel.locator(f'.gw-compendiums__pack[data-compendium-pack="{pack["id"]}"]')
            group.locator('.gw-compendiums__permissions').click();permission=page.locator('.ownership-dialog');expect(permission).to_be_visible()
            permission.locator('select').first.select_option('none');permission.locator('[type=submit]').click();expect(permission).to_have_count(0)
            reader.reload();reader.wait_for_function('!!window.gravewrightActors');reader.locator('[data-native-directory-toggle=content]').click()
            expect(reader_panel.locator(f'.gw-compendiums__pack[data-compendium-pack="{pack["id"]}"]')).to_have_count(0)
            # Native controls keep manual layout choices independent of filtering.
            check_window_controls(page,panel)
            reader_context.close();context.close()
        if seed.get('emptyCampaign') and not args.windows_only:
            context=browser.new_context(viewport={'width':390,'height':844});context.add_cookies([{**seed['sessions']['gm'],'url':base}]);page=context.new_page()
            panel=open_directory(page,base,{'campaign':seed['emptyCampaign']})
            expect(panel.locator('.gw-compendiums__empty')).to_be_visible();panel.locator('.gw-compendiums__create').click()
            modal=page.locator('.table-form-modal');expect(modal).to_be_visible();modal.locator('[name=name]').fill('First synthetic pack')
            modal.locator('[type=submit]').click();expect(modal).to_have_count(0)
            expect(panel.locator('.gw-compendiums__pack-name')).to_have_text('First synthetic pack');expect(panel.locator('.gw-compendiums__empty')).to_be_visible()
            page.screenshot(path=str(args.output/'first-pack-created.png'));context.close()
        assert not errors, errors
        browser.close()
    (args.output/'records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'views':len(records),'systems':len(seed['systems']),'errors':errors,'output':str(args.output)}))


if __name__=='__main__': main()
