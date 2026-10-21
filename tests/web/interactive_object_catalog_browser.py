"""Exercise the real object catalog modal with synthetic, static-only resources."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
STATIC = {
    f'/static/gravewright_{name}/': ROOT / f'gravewright/{name}/static/gravewright_{name}'
    for name in ('maps', 'table', 'web', 'modules')
}
IDENTIFIERS = [f'00000000-0000-4000-8000-{index:012d}' for index in range(1, 7)]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ('/en', '/pt-BR', '/es'):
            locale = path[1:]
            messages = {} if locale == 'en' else json.loads(
                (ROOT / f'gravewright/modules/locale_overrides/{locale}.json').read_text(encoding='utf-8'))
            config = json.dumps({'id': locale, 'messages': messages}, ensure_ascii=False)
            fixture = json.dumps(IDENTIFIERS)
            raw = f'''<!doctype html><html lang="{locale}"><head><meta charset="utf-8">
              <script id="gravewright-language" type="application/json">{config}</script>
              <link rel="stylesheet" href="/static/gravewright_web/css/tokens.css">
              <link rel="stylesheet" href="/static/gravewright_table/permissions.css">
              <link rel="stylesheet" href="/static/gravewright_table/window-polish.css">
              <style>body{{background:var(--surface);color:var(--text);font:14px var(--font);margin:0}}</style>
              </head><body><button id="opener">Catalog</button><script type="module">
              import {{createTranslator}} from '/static/gravewright_modules/i18n.js';
              import {{openInteractiveObjectCatalog,createInteractiveObjectPreset}} from '/static/gravewright_maps/builder/interactive-presets.js';
              const [doorId,journalId,userId,trackId,assetId,questId]={fixture};
              const translator=createTranslator(); window.applied=[];
              window.openCatalog=async ({{authored=false,empty=false,emptyObject=false,preserveState=false,initialPreset}}={{}})=>{{
                window.catalogAbort=new AbortController();
                const element={{id:doorId,name:'Synthetic object',empty:emptyObject,blueprint:authored?createInteractiveObjectPreset('chest').blueprint:null}};
                return await openInteractiveObjectCatalog({{element,preserveState,initialPreset,
                  doors:empty?[]:[{{id:doorId,name:'Synthetic door with a long name '.repeat(5)}}],
                  handouts:empty?[]:[{{id:journalId,type:'handout',name:'Synthetic journal '.repeat(12)}},{{id:questId,type:'quest',name:'Synthetic quest '.repeat(12)}}],
                  sounds:empty?[]:[{{id:trackId,name:'Synthetic sound '.repeat(12)}}],
                  assets:empty?[]:[{{id:assetId,name:'Synthetic image '.repeat(12)}}],
                  users:empty?[]:[{{id:userId,name:'Synthetic player '.repeat(12),role:'player'}},{{id:doorId,name:'Synthetic GM',role:'gm'}}],
                  t:key=>translator.t(key),signal:window.catalogAbort.signal,
                  onApply:result=>{{window.applied.push(result);}}}});
              }};
              document.querySelector('#opener').onclick=()=>window.openCatalog();
              </script></body></html>'''.encode('utf-8')
            kind = 'text/html; charset=utf-8'
        else:
            target = None
            for prefix, base in STATIC.items():
                if path.startswith(prefix):
                    candidate = (base / path.removeprefix(prefix)).resolve()
                    if candidate.is_relative_to(base.resolve()) and candidate.is_file():
                        target = candidate
                    break
            if target is None:
                self.send_error(404)
                return
            raw = target.read_bytes()
            kind = 'text/css; charset=utf-8' if target.suffix == '.css' else 'text/javascript; charset=utf-8'
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/runner/interactive-object-catalog')
    args = parser.parse_args()
    output = args.output.resolve()
    temporary = output / 'tmp'
    temporary.mkdir(parents=True, exist_ok=True)
    for name in ('TMP', 'TEMP', 'TMPDIR'):
        os.environ[name] = str(temporary)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=str(args.browser_executable) if args.browser_executable else None)
            page = browser.new_page(viewport={'width': 1200, 'height': 850})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            for locale in ('en', 'pt-BR', 'es'):
                page.goto(base + '/' + locale)
                page.wait_for_function("typeof window.openCatalog==='function'")
                for width, height in ((1200, 850), (390, 850), (320, 700)):
                    page.set_viewport_size({'width': width, 'height': height})
                    page.locator('#opener').click()
                    modal = page.locator('[data-interactive-object-catalog]')
                    expect(modal).to_be_visible()
                    expect(modal.locator('[data-interactive-preset]')).to_have_count(14)
                    modal.locator('[data-interactive-preset="chest"]').click()
                    modal.locator('[data-interactive-preset-message]').fill('Synthetic contents. ' * 60)
                    modal.locator('[data-interactive-preset-audience]').select_option('user')
                    expect(modal.locator('[data-interactive-preset-player] option')).to_have_count(2)
                    modal.locator('[data-interactive-preset-player]').select_option(IDENTIFIERS[2])
                    expect(modal.locator('[data-interactive-preset-sound]')).to_be_disabled()
                    expect(modal.locator('[data-interactive-preset-image]')).to_be_disabled()
                    modal.locator('[data-interactive-preset-include-sound]').check()
                    modal.locator('[data-interactive-preset-sound]').select_option(IDENTIFIERS[3])
                    modal.locator('[data-interactive-preset-volume]').fill('0.35')
                    modal.locator('[data-interactive-preset-include-image]').check()
                    modal.locator('[data-interactive-preset-image]').select_option(IDENTIFIERS[4])
                    assert modal.evaluate('(node)=>node.scrollWidth <= node.clientWidth+1'), (locale, width)
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (locale, width)
                    if width <= 600:
                        geometry = modal.evaluate('''node=>{
                          const sidebar=node.querySelector('.interactive-presets__sidebar').getBoundingClientRect();
                          const list=node.querySelector('.blueprint-templates__list').getBoundingClientRect();
                          const content=node.querySelector('.blueprint-templates__panes > .blueprint-templates__content').getBoundingClientRect();
                          return {listHeight:list.height,sidebarBottom:sidebar.bottom,contentTop:content.top};
                        }''')
                        assert geometry['listHeight'] >= 96, (locale, width, height, geometry)
                        assert geometry['sidebarBottom'] <= geometry['contentTop'], (locale, width, height, geometry)
                        modal.locator('.blueprint-templates__panes').evaluate('(node)=>node.scrollTop=0')
                    page.screenshot(path=str(output / f'catalog-{locale}-{width}.png'))
                    modal.locator('.blueprint-templates__primary').click()
                    expect(modal).to_have_count(0)
                    result = page.evaluate('window.applied.at(-1)')
                    message = next(row for row in result['blueprint']['graphs']['interact']['nodes'] if row['type'] == 'showMessage')
                    assert message['audience'] == {'scope': 'users', 'userIds': [IDENTIFIERS[2]]}
                    sound = next(row for row in result['blueprint']['graphs']['interact']['nodes'] if row['type'] == 'sound')
                    assert sound['trackId'] == IDENTIFIERS[3] and sound['volume'] == .35
                    assert result['blueprint']['states']['on'] == {'appearance': 'asset', 'assetId': IDENTIFIERS[4]}
                    assert result['blueprint']['states']['off'] == {'appearance': 'inherit'}
                    expect(page.locator('#opener')).to_be_focused()
                page.evaluate('window.openCatalog({authored:true})')
                modal = page.locator('[data-interactive-object-catalog]')
                modal.locator('[data-interactive-preset="book"]').click()
                modal.locator('[data-interactive-preset-journal]').select_option(IDENTIFIERS[1])
                modal.locator('[data-interactive-preset-audience]').select_option('players')
                before = page.evaluate('window.applied.length')
                modal.locator('.blueprint-templates__primary').click()
                expect(modal.locator('form')).to_have_count(0)
                assert page.evaluate('window.applied.length') == before
                modal.locator('.blueprint-templates__actions button').first.click()
                expect(modal.locator('form')).to_have_count(1)
                modal.locator('[data-interactive-preset-journal]').select_option(IDENTIFIERS[1])
                modal.locator('[data-interactive-preset-audience]').select_option('players')
                modal.locator('.blueprint-templates__primary').click()
                modal.locator('.blueprint-templates__primary').click()
                expect(modal).to_have_count(0)
                result = page.evaluate('window.applied.at(-1)')
                handout = next(row for row in result['blueprint']['graphs']['interact']['nodes'] if row['type'] == 'showHandout')
                assert handout['journalId'] == IDENTIFIERS[1]
                assert handout['audience'] == {'scope': 'players'}
                assert all(node['type'] != 'sound' for graph in result['blueprint']['graphs'].values() for node in graph['nodes'])
                assert result['blueprint']['states']['on'] == {'appearance': 'inherit'}
                page.evaluate('window.openCatalog({empty:true})')
                modal = page.locator('[data-interactive-object-catalog]')
                modal.locator('[data-interactive-preset="book"]').click()
                before = page.evaluate('window.applied.length')
                modal.locator('.blueprint-templates__primary').click()
                expect(modal).to_be_visible()
                assert page.evaluate('window.applied.length') == before
                page.keyboard.press('Escape')
                expect(modal).to_have_count(0)
                page.evaluate('window.openCatalog({preserveState:true})')
                modal = page.locator('[data-interactive-object-catalog]')
                modal.locator('[data-interactive-preset="trap"]').click()
                expect(modal.locator('[data-interactive-preserve-state]')).to_be_visible()
                page.keyboard.press('Escape')
                expect(modal).to_have_count(0)
                page.evaluate('window.openCatalog()')
                expect(page.locator('[data-interactive-object-catalog]')).to_be_visible()
                page.evaluate('window.catalogAbort.abort()')
                expect(page.locator('[data-interactive-object-catalog]')).to_have_count(0)
                page.set_viewport_size({'width': 1200, 'height': 850})
                page.evaluate("window.openCatalog({initialPreset:'dice-request'})")
                modal = page.locator('[data-interactive-object-catalog]')
                expect(modal.locator('[data-interactive-preset="dice-request"]')).to_have_attribute('aria-pressed', 'true')
                modal.locator('[data-interactive-preset-expression]').fill('2d6+3')
                modal.locator('[data-interactive-preset-roll-label]').fill('Synthetic roll')
                modal.locator('[data-interactive-preset-audience]').select_option('user')
                modal.locator('[data-interactive-preset-player]').select_option(IDENTIFIERS[2])
                modal.locator('.blueprint-templates__primary').click()
                expect(modal).to_have_count(0)
                roll = page.evaluate("window.applied.at(-1).blueprint.graphs.interact.nodes.find(row=>row.type==='requestRoll')")
                assert roll['expression'] == '2d6+3' and roll['audience']['userIds'] == [IDENTIFIERS[2]]
                page.evaluate("window.openCatalog({initialPreset:'quest-start'})")
                modal = page.locator('[data-interactive-object-catalog]')
                expect(modal.locator('[data-interactive-preset-journal] option')).to_have_count(2)
                modal.locator('[data-interactive-preset-journal]').select_option(IDENTIFIERS[5])
                modal.locator('.blueprint-templates__primary').click()
                expect(modal).to_have_count(0)
                quest = page.evaluate("window.applied.at(-1).blueprint.graphs.interact.nodes.find(row=>row.type==='setQuestStatus')")
                assert quest['journalId'] == IDENTIFIERS[5] and quest['status'] == 'active'
                page.evaluate("window.openCatalog({emptyObject:true,initialPreset:'bell'})")
                modal = page.locator('[data-interactive-object-catalog]')
                expect(modal.locator('[data-interactive-preset-include-image]')).to_be_disabled()
                expect(modal.locator('[data-interactive-preset-image]')).to_be_disabled()
                search = modal.locator('[data-interactive-preset-search]')
                search.fill(modal.locator('[data-interactive-preset="bell"]').inner_text())
                expect(modal.locator('[data-interactive-preset]:visible')).to_have_count(1)
                search.fill('no-such-synthetic-model')
                expect(modal.locator('[data-interactive-preset]:visible')).to_have_count(0)
                search.fill('')
                expect(modal.locator('[data-interactive-preset]:visible')).to_have_count(14)
                page.keyboard.press('Escape')
                expect(modal).to_have_count(0)
            assert not errors, errors
            browser.close()
        print(json.dumps({'passed': True, 'locales': 3, 'viewport_widths': [1200, 390, 320], 'viewport_heights': [850, 850, 700], 'output': str(output)}))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == '__main__':
    main()
