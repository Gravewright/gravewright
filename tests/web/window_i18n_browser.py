"""Native floating-window controls use the real host Translator adapter.

This standalone browser test serves only static host files and a generic window;
it requires no Django database, campaign, system package or language override.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread
import unittest

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
CATALOGS = {
    'en': {},
    'pt-BR': {'Reset window layout': 'Restaurar disposição das janelas',
              'Minimize': 'Minimizar', 'Restore': 'Restaurar'},
    'es': {'Reset window layout': 'Restablecer disposición de ventanas',
           'Minimize': 'Minimizar', 'Restore': 'Restaurar'},
}
ASSETS = {
    '/static/gravewright_web/windows.js': ROOT / 'gravewright/web/static/gravewright_web/windows.js',
    '/static/gravewright_modules/i18n.js': ROOT / 'gravewright/modules/static/gravewright_modules/i18n.js',
    '/static/gravewright_modules/lifetime.js': ROOT / 'gravewright/modules/static/gravewright_modules/lifetime.js',
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path in ASSETS:
            raw = ASSETS[self.path].read_bytes()
            kind = 'text/javascript; charset=utf-8'
        elif self.path.removeprefix('/') in CATALOGS:
            locale = self.path[1:]
            config = json.dumps({'id': locale, 'messages': CATALOGS[locale]}, ensure_ascii=False)
            raw = f'''<!doctype html><html lang="{locale}"><head>
              <script id="gravewright-language" type="application/json">{config}</script>
              <script src="/static/gravewright_web/windows.js" defer></script>
              <style>section{{position:fixed;left:40px;top:40px;width:400px;height:300px}}
              header{{height:40px}}[data-window-minimized]{{height:40px}}</style></head>
              <body><section class="game-panel" data-movable translate="no">
              <header><h2>Settings</h2><button aria-label="Authored close">×</button></header>
              <p>Armor</p><input value="Settings"></section></body></html>'''.encode('utf-8')
            kind = 'text/html; charset=utf-8'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class WindowTranslationBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_native_owned_controls_translate_inside_excluded_windows_and_dispose(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            for locale, messages in CATALOGS.items():
                page.goto(self.base + '/' + locale)
                window = page.locator('[data-movable]')
                reset = window.locator('[data-window-action="reset"]')
                minimize = window.locator('[data-window-action="minimize"]')
                expect(reset).to_have_attribute('aria-label', messages.get('Reset window layout', 'Reset window layout'))
                expect(reset).to_have_attribute('title', messages.get('Reset window layout', 'Reset window layout'))
                expect(minimize).to_have_attribute('aria-label', messages.get('Minimize', 'Minimize'))
                minimize.click()
                expect(minimize).to_have_attribute('aria-label', messages.get('Restore', 'Restore'))
                expect(minimize).to_have_attribute('title', messages.get('Restore', 'Restore'))
                minimize.click()
                expect(minimize).to_have_attribute('aria-label', messages.get('Minimize', 'Minimize'))
                expect(window.locator('h2')).to_have_text('Settings')
                expect(window.locator('p')).to_have_text('Armor')
                expect(window.locator('input')).to_have_value('Settings')
                expect(window.locator('[aria-label="Authored close"]')).to_have_count(1)

            # The documented adapter event updates native controls without
            # requiring legacy DOM translation or touching user-owned text.
            page.evaluate('''config=>{
              document.querySelector('#gravewright-language').textContent=JSON.stringify(config);
              window.dispatchEvent(new Event('gravewright:locale'));
            }''', {'id': 'en', 'messages': {}})
            expect(reset).to_have_attribute('aria-label', 'Reset window layout')
            expect(minimize).to_have_attribute('aria-label', 'Minimize')
            expect(window.locator('h2')).to_have_text('Settings')
            # Removing a window releases both controls and their listeners.
            page.evaluate('''()=>{
              window.removedControl=document.querySelector('[data-window-action=reset]');
              document.querySelector('[data-movable]').remove();
            }''')
            page.wait_for_function('window.removedControl.parentElement===null')
            page.evaluate('''config=>{
              document.querySelector('#gravewright-language').textContent=JSON.stringify(config);
              window.dispatchEvent(new Event('gravewright:locale'));
            }''', {'id': 'pt-BR', 'messages': CATALOGS['pt-BR']})
            self.assertEqual(page.evaluate('window.removedControl.getAttribute("aria-label")'), 'Reset window layout')
            self.assertEqual(errors, [])
            browser.close()


if __name__ == '__main__':
    unittest.main()
