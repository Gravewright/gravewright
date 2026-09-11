"""Browser flows and optional pixel comparison against the original compiled Vue UI.

uv run python tests/e2e/table.py --original /path/to/reference
Uses a temporary database; never creates accounts in the development database.
"""
import argparse
import functools
import json
from io import BytesIO
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
PASSWORD = 'browser-password-123'
OFFLINE_SOCKET = """
window.WebSocket = class extends EventTarget {
  static OPEN = 1;
  readyState = 3;
  constructor() { super(); setTimeout(() => this.dispatchEvent(new CloseEvent('close', {code: 4403})), 0); }
  close() {}
};
"""


def port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--original', type=Path)
    args = parser.parse_args()
    output = ROOT / 'test-results' / 'table'
    output.mkdir(parents=True, exist_ok=True)
    report = []
    with tempfile.TemporaryDirectory(prefix='grave-table-browser-') as temp:
        env = {**os.environ, 'GRAVEWRIGHT_DATABASE': str(Path(temp) / 'browser.sqlite3'), 'GRAVEWRIGHT_MEDIA_ROOT': str(Path(temp) / 'media')}
        subprocess.run([sys.executable, 'manage.py', 'migrate', '--noinput'], cwd=ROOT, env=env,
                       check=True, stdout=subprocess.DEVNULL)
        address = f'127.0.0.1:{port()}'
        base = f'http://{address}'
        log = (output / 'server.log').open('w')
        server = subprocess.Popen([sys.executable, 'manage.py', 'runserver', address, '--noreload'],
                                  cwd=ROOT, env=env, stdout=log, stderr=log)
        reference_server = None
        try:
            for _ in range(100):
                try:
                    with urlopen(base, timeout=1):
                        break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Django did not start; inspect test-results/table/server.log')
            if args.original:
                handler = functools.partial(QuietHandler, directory=str(args.original / 'dist/frontend'))
                reference_server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
                threading.Thread(target=reference_server.serve_forever, daemon=True).start()
                reference_url = f'http://127.0.0.1:{reference_server.server_port}'
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                context = browser.new_context(viewport={'width': 1440, 'height': 1000},reduced_motion='reduce')
                # This suite compares the offline shell; realtime.py exercises live sockets.
                context.add_init_script(OFFLINE_SOCKET)
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                reference = None
                account = {'name':'Browser Owner','email':'owner@example.test','role':'owner'}
                rows = []
                temporary_code = ''
                cover_file = BytesIO()
                Image.new('RGB', (640,360), '#354b66').save(cover_file, 'PNG')
                page.goto(base)
                page.locator('#owner-name').fill(account['name'])
                page.locator('#owner-email').fill(account['email'])
                page.locator('#owner-password').fill(PASSWORD)
                page.get_by_role('button', name='Create administrator').click()
                expect(page.locator('#inside-shell')).to_be_visible()
                if reference_server:
                    reference = browser.new_page(viewport={'width': 1440, 'height': 1000},reduced_motion='reduce')
                    def mock_auth(route):
                        path = route.request.url.split(reference_url)[-1].split('?')[0]
                        if path.endswith('/status'):
                            body = {'configured': True}
                        elif path.endswith('/session'):
                            body = {'authenticated': True, 'account':account}
                        elif path == '/api/containers':
                            body = rows
                        elif path == '/api/rulesets':
                            body = {'rulesets':[{'systemId':'gravewright-pdf-system','title':'Gravewright PDF System','actorTypes':[{'id':'character','label':'Character'}]}]}
                        elif path.endswith('/map'):
                            body = None
                        elif path.endswith('/modules'):
                            body = {'modules':[], 'moduleSetRevision':'1','tableId':rows[0]['id'],'replacements':{}}
                        elif path.endswith('/capabilities'):
                            body = {'items':False}
                        elif path.endswith(('/blocks','/scene-directory','/folders','/journals')):
                            body = []
                        elif path == '/api/player-preferences':
                            body = {'pingColor':'#f2c679'}
                        elif path.endswith('/invitation') or path.endswith('/removal-code'):
                            body = {'code':temporary_code, 'expiresAt':9999999999999}
                        else:
                            body = {'ready': True, 'token': 'reference'}
                        route.fulfill(status=200, json=body)
                    reference.route('**/campaigns/*/cover', lambda route: route.fulfill(content_type='image/png',body=cover_file.getvalue()))
                    reference.route('**/api/**', mock_auth)
                    reference.route('**/__gravewright/csrf', mock_auth)
                    reference.goto(reference_url)
                    expect(reference.locator('.gw-shell')).to_be_visible()

                def capture(name):
                    for width, height in [(1440, 1000), (390, 844)]:
                        label = f'{name}-{width}'
                        # Reflow both pages from the same viewport to normalize cached
                        # compositor layers after a modal changes height.
                        page.set_viewport_size({'width': width+1, 'height': height})
                        page.set_viewport_size({'width': width, 'height': height})
                        page.mouse.move(0, 0)
                        page.evaluate('document.activeElement?.blur()')
                        # Let CSS transitions settle after mouse/focus changes.
                        page.wait_for_timeout(250)
                        target = output / f'{label}-django.png'
                        page.screenshot(path=str(target), full_page=True, animations='disabled', caret='hide')
                        if reference:
                            reference.set_viewport_size({'width': width+1, 'height': height})
                            reference.set_viewport_size({'width': width, 'height': height})
                            reference.mouse.move(0, 0)
                            reference.evaluate('document.activeElement?.blur()')
                            reference.wait_for_timeout(250)
                            original = output / f'{label}-original.png'
                            reference.screenshot(path=str(original), full_page=True, animations='disabled', caret='hide')
                            a, b = Image.open(target).convert('RGB'), Image.open(original).convert('RGB')
                            assert a.size == b.size, (label, a.size, b.size)
                            difference = ImageChops.difference(a, b)
                            changed = sum(1 for pixel in difference.get_flattened_data() if max(pixel) > 8)
                            ratio = changed / (a.width * a.height)
                            difference.save(output / f'{label}-diff.png')
                            report.append({'screen': label, 'changed_pixel_ratio': ratio,
                                           'exact_match': difference.getbbox() is None})
                            print(label, f'{ratio:.6%} pixels differ', flush=True)
                    page.set_viewport_size({'width': 1440, 'height': 1000})
                    if reference:
                        reference.set_viewport_size({'width': 1440, 'height': 1000})

                def click_both(name):
                    page.get_by_role('button',name=name,exact=True).click()
                    if reference:
                        reference.get_by_role('button',name=name,exact=True).click()

                page.get_by_role('button',name='Begin my first journey').click()
                page.get_by_placeholder('Campaign name').fill('The Lost Keep')
                page.get_by_role('button',name='Create table',exact=True).click()
                expect(page.get_by_role('dialog')).to_have_count(0)
                rows = page.request.get(base+'/api/containers').json()
                page.get_by_role('button',name='Open The Lost Keep',exact=True).click()
                page.get_by_role('button',name='Enter table',exact=True).click()
                expect(page.locator('#table-workspace')).to_be_visible()
                if reference:
                    reference.reload()
                    reference.get_by_role('button',name='Open The Lost Keep',exact=True).click()
                    reference.get_by_role('button',name='Enter table',exact=True).click()
                    expect(reference.locator('.game-table')).to_be_visible()
                    # Compare the disconnected state of both interfaces.
                    reference.wait_for_timeout(1500)
                capture('owner-game')
                for layer in ['GM','Images','Sound','Effects','Walls','Lighting']:
                    page.locator('.game-menubar__layers').get_by_role('button',name=layer,exact=True).click()
                    if reference:
                        reference.locator('.game-menubar__layers').get_by_role('button',name=layer,exact=True).click()
                    capture('layer-'+layer.lower())
                page.locator('.game-menubar__layers').get_by_role('button',name='Game',exact=True).click()
                if reference:
                    reference.locator('.game-menubar__layers').get_by_role('button',name='Game',exact=True).click()
                page.keyboard.press('r')
                expect(page.get_by_role('button',name='Measure',exact=True).filter(visible=True)).to_have_attribute('aria-pressed','true')
                page.keyboard.press('v')
                click_both('Settings')
                expect(page.get_by_role('dialog')).to_be_visible()
                capture('table-menu')
                page.keyboard.press('Escape')
                if reference:
                    reference.locator('.house-menu-scrim').click(position={'x':1,'y':1})
                click_both('Participants')
                capture('roster')
                click_both('Return to tables')
                expect(page.locator('#inside-shell')).to_be_visible()
                # Seed a real player membership through the migrated invitation API.
                token=next(c['value'] for c in context.cookies() if c['name']=='gravewright-csrf')
                invitation=page.request.post(base+'/api/containers/'+rows[0]['id']+'/invitation',data={},headers={'X-CSRF-Token':token}).json()['code']
                player_context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                player_context.add_init_script(OFFLINE_SOCKET)
                page=player_context.new_page()
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(base+'/register')
                page.locator('#owner-name').fill('Browser Player')
                page.locator('#owner-email').fill('player@example.test')
                page.locator('#owner-password').fill(PASSWORD)
                page.get_by_role('button',name='Create my account',exact=True).click()
                page.get_by_placeholder('XXXX-XXXX',exact=True).fill(invitation)
                page.get_by_role('button',name='Join a table',exact=True).click()
                expect(page.get_by_role('heading',name='The Lost Keep')).to_be_visible()
                page.get_by_role('button',name='Open The Lost Keep',exact=True).click()
                page.get_by_role('button',name='Enter table',exact=True).click()
                expect(page.locator('#table-workspace')).to_be_visible()
                account={'name':'Browser Player','email':'player@example.test','role':'participant'}
                if reference:
                    reference.goto(reference_url)
                    reference.get_by_role('button',name='Open The Lost Keep',exact=True).click()
                    reference.get_by_role('button',name='Enter table',exact=True).click()
                    expect(reference.locator('.game-table')).to_be_visible()
                    reference.wait_for_timeout(1500)
                capture('player-game')
                assert not page.locator('.game-menubar__layers').count()
                assert not page.locator('[data-panel=scenes]').count()
                assert not page.locator('canvas').count()
                assert not errors,errors
                browser.close()
            (output / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
            assert all(item['changed_pixel_ratio'] < 0.001 for item in report), report
            print('Browser table-shell flows passed; development database untouched.', flush=True)
        finally:
            server.terminate()
            server.wait(timeout=10)
            log.close()
            if reference_server:
                reference_server.shutdown()
                reference_server.server_close()


if __name__ == '__main__':
    main()
