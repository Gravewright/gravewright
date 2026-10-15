"""Native item directory density, locale ordering and document actions.

Use a new disposable compendium_server.py fixture with local system archives.
No operator content is read or changed. All mutations use the public browser API.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from compendium_layout import MEASURE, alphabetical, api, locale
from playwright.sync_api import expect, sync_playwright


def open_directory(page, base, campaign):
    page.goto(base + '/game/' + campaign)
    page.wait_for_function('!!window.gravewrightItems')
    toggle_directory(page)
    panel = page.locator('#items-panel')
    expect(panel).to_be_visible()
    return panel


def toggle_directory(page):
    def item_state(response):
        if not response.url.endswith('/api') or response.request.method != 'POST':
            return False
        payload = response.request.post_data_json
        return payload.get('domain') == 'items' and payload.get('method') == 'state'
    with page.expect_response(item_state) as response:
        page.locator('[data-native-directory-toggle=items]').click()
    response.value.json()
    page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--browser-executable', type=Path)
    args = parser.parse_args()
    seed = json.loads(args.seed.read_text(encoding='utf-8'))
    assert seed.get('kind') == 'compendium-layout-review'
    assert (Path(seed['fixture']) / 'review.sqlite3').is_file()
    from scripts.runtime_storage import configure_runtime_storage
    configure_runtime_storage(ROOT, 'data/runner/item-directory-layout')
    args.output.mkdir(parents=True, exist_ok=True)
    records, errors = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path':str(args.browser_executable)} if args.browser_executable else {}))
        for system, data in seed['systems'].items():
            context = browser.new_context(viewport={'width':1440, 'height':900})
            context.add_cookies([{**data['sessions']['gm'], 'url':seed['base']}])
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            panel = open_directory(page, seed['base'], data['campaign'])
            empty = panel.evaluate(MEASURE)
            assert empty['height'] < 250, empty
            page.screenshot(path=str(args.output / (system + '-empty.png')))
            initial = api(page, 'return await gravewright.items.state();')
            assert not initial['items'] and not initial['folders']
            kind = initial['types'][0]['id']
            folders = []
            for name in ('Zeta folder', 'Árvore folder', 'Alfa folder'):
                folders.append(api(page, 'return await gravewright.items.createFolder(args);', {'name':name})['id'])
            documents = []
            for folder in (None, folders[2]):
                for name in ('Zebra 10', 'Arvore 10', 'Árvore 2', 'Alfa ' + 'long authored name ' * 5):
                    documents.append(api(page, 'return await gravewright.items.create(args);',
                        {'name':name, 'type':kind, 'folderId':folder, 'data':{'description':'Synthetic content'}, 'permissions':{'default':'read'}})['item'])
            api(page, 'return await gravewright.items.create(args);', {'name':'Private fixture item', 'type':kind})
            before = api(page, 'return await gravewright.items.state();')
            for width, height in ((1440,900),(390,844),(320,700)):
                page.set_viewport_size({'width':width,'height':height})
                for language in ('en','pt-BR','es'):
                    locale(page, language, data['campaign'])
                    if not panel.is_visible():
                        page.locator('[data-native-directory-toggle=items]').click()
                    expect(panel.locator('.item-directory__entry')).to_have_count(9)
                    folder_names = panel.locator('.item-directory__folder-name').all_text_contents()
                    assert folder_names == alphabetical(page, folder_names), folder_names
                    for parent in ('', folders[2]):
                        names = panel.locator('[data-entries]' if not parent else f'.item-directory__folder-content[data-item-folder-id="{parent}"]')
                        values = names.locator(':scope > .item-directory__entry .item-directory__info strong').all_text_contents()
                        assert values == alphabetical(page, values), values
                    metrics = panel.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    assert metrics['width'] <= width and metrics['x'] >= 0 and metrics['x'] + metrics['width'] <= width + 1, metrics
                    records.append({'system':system,'width':width,'locale':language,'case':'populated','metrics':metrics})
                    page.screenshot(path=str(args.output / f'{system}-{width}-{language}.png'))
                    search = panel.locator('input[type=search]')
                    search.fill('arvore')
                    expect(panel.locator('.item-directory__entry')).to_have_count(4)
                    search.fill('no matching fixture text')
                    expect(panel.locator('.item-directory__entry')).to_have_count(0)
                    expect(panel.locator('.item-directory__empty')).to_be_visible()
                    no_results = panel.evaluate(MEASURE)
                    assert no_results['height'] < 260, no_results
                    records.append({'system':system,'width':width,'locale':language,'case':'no-results','metrics':no_results})
                    search.fill('')
                    panel.locator('[data-create]').click()
                    create = page.locator('[data-window-key="item:create"]')
                    expect(create).to_be_visible()
                    choices = create.locator('[name=type] option').all_text_contents()
                    assert choices == alphabetical(page, choices), choices
                    assert create.locator('[name=type]').input_value() == kind
                    page.keyboard.press('Escape')
                    expect(create).to_have_count(0)
            after = api(page, 'return await gravewright.items.state();')
            assert after == before, 'Viewing, searching and locale changes must not write document state.'
            locale(page, 'en', data['campaign'])
            if not panel.is_visible(): toggle_directory(page)
            page.set_viewport_size({'width':1440,'height':900})
            row = panel.locator(f'[data-item-id="{documents[0]["id"]}"]')
            trigger = row.locator('.item-directory__more')
            trigger.click()
            menu = page.locator('.item-directory-menu')
            expect(menu).to_be_visible()
            page.keyboard.press('End')
            expect(menu.locator('button').last).to_be_focused()
            api(page, "const state=await gravewright.items.state();for(const key of ['items','folders','types'])state[key].reverse();window.dispatchEvent(new CustomEvent('gravewright:resources',{detail:{module:'items',state}}));")
            expect(menu).to_be_visible()
            expect(menu.locator('button').last).to_be_focused()
            page.keyboard.press('Escape')
            expect(menu).to_have_count(0)
            expect(trigger).to_be_focused()
            trigger.click()
            api(page, "const item=await gravewright.items.get(args);await gravewright.items.update({id:item.id,version:item.version,name:item.name+' renamed'});const state=await gravewright.items.state();window.dispatchEvent(new CustomEvent('gravewright:resources',{detail:{module:'items',state}}));", documents[0]['id'])
            expect(menu).to_have_count(0)
            expect(row.locator('.item-directory__info strong')).to_have_text(documents[0]['name']+' renamed')
            row.locator('.item-directory__more').click()
            menu.get_by_role('menuitem', name='Duplicate', exact=True).click()
            expect(panel.locator('.item-directory__entry')).to_have_count(10)
            trigger = row.locator('.item-directory__more')
            trigger.click()
            menu.get_by_role('menuitem', name='Move to folder', exact=True).click()
            move = page.locator('[data-window-key^="item:move:"]')
            choices = move.locator('select option').all_text_contents()
            assert choices[0] == 'No folder' and choices[1:] == alphabetical(page, choices[1:])
            move.locator('select').select_option(folders[0])
            move.locator('[type=submit]').click()
            expect(move).to_have_count(0)
            expect(panel.locator(f'.item-directory__folder-content[data-item-folder-id="{folders[0]}"] [data-item-id="{documents[0]["id"]}"]')).to_have_count(1)
            context.close()
            reader = browser.new_context(viewport={'width':390,'height':844})
            reader.add_cookies([{**data['sessions']['reader'],'url':seed['base']}])
            page = reader.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            panel = open_directory(page, seed['base'], data['campaign'])
            expect(panel.locator('[data-create]')).to_be_hidden()
            expect(panel.locator('.item-directory__info strong').filter(has_text='Private fixture item')).to_have_count(0)
            panel.locator('.item-directory__more').first.click()
            expect(page.locator('.item-directory-menu [role=menuitem]')).to_have_count(1)
            expect(page.locator('.item-directory-menu')).to_contain_text('Open item sheet')
            page.keyboard.press('Escape')
            reader.close()
        browser.close()
    assert not errors, errors
    report = {'passed':True,'records':records,'pageErrors':errors,'functionalSystems':len(seed['systems'])}
    (args.output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'passed':True,'views':len(records),'systems':len(seed['systems'])}))


if __name__ == '__main__':
    main()
