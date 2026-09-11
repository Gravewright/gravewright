"""Browser flows and optional pixel comparison against the original compiled Vue UI.

uv run python tests/e2e/dice.py --original /path/to/reference
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
    output = ROOT / 'test-results' / 'dice'
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
                raise RuntimeError('Django did not start; inspect test-results/realtime/server.log')
            if args.original:
                handler = functools.partial(QuietHandler, directory=str(args.original / 'dist/frontend'))
                reference_server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
                threading.Thread(target=reference_server.serve_forever, daemon=True).start()
                reference_url = f'http://127.0.0.1:{reference_server.server_port}'
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                context = browser.new_context(viewport={'width': 1440, 'height': 1000},reduced_motion='reduce')
                context.add_init_script("window.__sockets=[]; const Native=window.WebSocket; window.WebSocket=class extends Native{constructor(...args){super(...args);window.__sockets.push(this)}}")
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                reference = None
                account = {'name':'Browser Owner','email':'owner@example.test','role':'owner'}
                rows = []
                temporary_code = ''
                online_members = [{'id':'owner', 'name':'Browser Owner','role':'gm'}]
                reference_sockets = []
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
                            body = {'id':'reference-scene','blockId':'reference-block','status':'processing','name':'Reference scene'}
                        elif path.endswith('/modules'):
                            body = {'modules':[], 'moduleSetRevision':'1','tableId':rows[0]['id'],'replacements':{}}
                        elif path.endswith('/capabilities'):
                            body = {'items':False}
                        elif path.endswith(('/blocks','/scene-directory','/folders','/journals','/maps','/map-folders','/messages')):
                            body = []
                        elif path == '/api/player-preferences':
                            body = {'pingColor':'#f2c679'}
                        elif path.endswith('/invitation') or path.endswith('/removal-code'):
                            body = {'code':temporary_code, 'expiresAt':9999999999999}
                        else:
                            body = {'ready': True, 'token': 'reference'}
                        route.fulfill(status=200, json=body)
                    reference.route('**/campaigns/*/cover', lambda route: route.fulfill(content_type='image/png',body=cover_file.getvalue()))
                    def mock_socket(ws):
                        reference_sockets.append(ws)
                        def received(raw):
                            message=json.loads(raw)
                            if message['type']=='table.join':
                                ws.send(json.dumps({'type':'table.joined','payload':{'tableId':rows[0]['id'],'role':'gm'}}))
                                ws.send(json.dumps({'type':'table.presence','payload':{'members':online_members}}))
                        ws.on_message(received)
                    reference.route_web_socket('**/ws', mock_socket)
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
                        page.locator('.dice-tray').screenshot(path=str(target), animations='disabled', caret='hide')
                        if reference:
                            reference.set_viewport_size({'width': width+1, 'height': height})
                            reference.set_viewport_size({'width': width, 'height': height})
                            reference.mouse.move(0, 0)
                            reference.evaluate('document.activeElement?.blur()')
                            reference.wait_for_timeout(250)
                            original = output / f'{label}-original.png'
                            reference.locator('.dice-tray').screenshot(path=str(original), animations='disabled', caret='hide')
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

                def both(name):
                    page.get_by_role('button',name=name,exact=True).click()
                    if reference:
                        reference.get_by_role('button',name=name,exact=True).click()

                def post(target_page,path,data):
                    token=next(c['value'] for c in target_page.context.cookies() if c['name']=='gravewright-csrf')
                    return target_page.request.post(base+path,data=data,headers={'X-CSRF-Token':token})

                def seated(target):
                    expect(target.locator('.game-menubar__presence')).to_have_attribute('data-presence','seated',timeout=15000)

                def echo(text,name,identifier):
                    if reference:
                        reference_sockets[-1].send(json.dumps({'type':'chat.message','payload':{'id':str(identifier),'mapId':'','tableId':rows[0]['id'],'from':{'name':name},'text':text,'at':identifier}}))

                page.get_by_role('button',name='Begin my first journey').click()
                page.get_by_placeholder('Campaign name').fill('The Lost Keep')
                page.get_by_role('button',name='Create table',exact=True).click()
                expect(page.get_by_role('dialog')).to_have_count(0)
                rows=page.request.get(base+'/api/containers').json()
                invitation=post(page,'/api/containers/'+rows[0]['id']+'/invitation',{}).json()['code']
                page.get_by_role('button',name='Open The Lost Keep',exact=True).click()
                page.get_by_role('button',name='Enter table',exact=True).click()
                seated(page)
                if reference:
                    reference.reload()
                    reference.get_by_role('button',name='Open The Lost Keep',exact=True).click()
                    reference.get_by_role('button',name='Enter table',exact=True).click()
                    seated(reference)
                both('Chat')
                both('Dice tray')
                tray=page.locator('.dice-tray')
                expect(tray).to_be_visible()
                def action(name):
                    tray.get_by_role('button',name=name,exact=True).click()
                    if reference: reference.locator('.dice-tray').get_by_role('button',name=name,exact=True).click()
                def fill(selector,value):
                    tray.locator(selector).fill(value)
                    if reference: reference.locator('.dice-tray').locator(selector).fill(value)
                def dice_capture(name):
                    tray.evaluate('el=>el.scrollTop=0')
                    if reference: reference.locator('.dice-tray').evaluate('el=>el.scrollTop=0')
                    capture(name)
                dice_capture('empty')
                action('d6');action('d6')
                tray.locator('.dice-tray__options select').select_option('dl')
                if reference: reference.locator('.dice-tray').locator('.dice-tray__options select').select_option('dl')
                fill('#dice-modifier','2')
                expect(tray.locator('.dice-tray__expression')).to_have_value('2d6dl1 + 2')
                dice_capture('pool')
                action('RPG presets')
                left=tray.locator('.dice-tray__preset-column').bounding_box()
                right=tray.locator('.dice-tray__roll-column').bounding_box()
                assert right['x'] >= left['x'] + left['width']
                assert abs(right['y']-left['y']) < 2
                assert tray.bounding_box()['width'] > 700
                dice_capture('presets')
                action('Success pool')
                dice_capture('success-preset')
                action('Use preset')
                expect(tray.locator('.dice-tray__expression')).to_have_value('5d10 >= 8')
                expect(tray.locator('[data-dice-tab=presets]')).to_have_attribute('aria-pressed','true')
                # Save a user preset without evaluating it.
                action('RPG presets')
                tray.locator('.dice-presets__saved summary').click()
                if reference: reference.locator('.dice-presets__saved summary').click()
                tray.get_by_label('Preset name',exact=True).fill('My pool')
                if reference: reference.locator('.dice-tray').get_by_label('Preset name',exact=True).fill('My pool')
                action('Save current expression')
                expect(tray.locator('[data-saved-count]')).to_have_text('1')
                dice_capture('saved-presets')
                action('Dice')
                fill('.dice-tray__expression','4d1')
                tray.locator('[name="repeat"]').fill('2')
                tray.locator('[name="label"]').fill('Attributes')
                tray.get_by_role('button',name='Roll',exact=True).click()
                expect(tray).to_be_hidden(timeout=10000)
                expect(page.locator('#chat-log article')).to_have_count(1)
                expect(page.locator('.dice-result__batch .dice-result__summary strong')).to_have_text(['4','4'])
                page.get_by_role('button',name='Dice tray',exact=True).click()
                tray.get_by_role('button',name='Recent 1',exact=True).click()
                expect(tray.locator('.dice-tray__history')).to_contain_text('Attributes')
                tray.locator('[name="expression"]').fill('1d0')
                tray.get_by_role('button',name='Roll',exact=True).click()
                expect(tray.locator('.dice-tray__error')).to_be_visible()
                expect(page.locator('#chat-log article')).to_have_count(1)
                tray.locator('[name="expression"]').fill('2d1')
                tray.locator('[name="repeat"]').fill('1')
                tray.get_by_role('button',name='To GM',exact=True).click()
                expect(tray).to_be_hidden(timeout=10000)
                expect(page.locator('.dice-result__secret').filter(visible=True)).to_have_text('GM roll')
                page.locator('#chat-form textarea').fill('/r 3d1')
                page.locator('#chat-form textarea').press('Enter')
                expect(page.locator('#chat-log article')).to_have_count(3)
                page.reload();seated(page);page.get_by_role('button',name='Chat',exact=True).click()
                expect(page.locator('#chat-log article')).to_have_count(3)
                page.get_by_role('button',name='Dice tray',exact=True).click()
                expect(tray.locator('[data-history-count]')).to_have_text('2')
                tray.get_by_role('button',name='Minimize',exact=True).click()
                expect(tray.locator('form')).to_be_hidden()
                tray.get_by_role('button',name='Minimize',exact=True).click()
                with page.expect_popup() as info:
                    tray.get_by_role('button',name='Detach window',exact=True).click()
                popup=info.value
                expect(popup.locator('.dice-tray')).to_be_visible()
                popup.close()
                expect(tray).to_be_visible()
                action('RPG presets')
                page.set_viewport_size({'width':390,'height':740})
                tray.evaluate("el=>{el.style.left='8px';el.style.top='8px'}")
                left=tray.locator('.dice-tray__preset-column').bounding_box()
                right=tray.locator('.dice-tray__roll-column').bounding_box()
                assert right['y'] >= left['y'] + left['height']
                assert tray.bounding_box()['width'] <= 374
                assert not errors,errors
                browser.close()
            (output / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
            assert all(item['changed_pixel_ratio'] < 0.001 for item in report), report
            print('Browser dice tray and server roll flows passed; development database untouched.', flush=True)
        finally:
            server.terminate()
            server.wait(timeout=10)
            log.close()
            if reference_server:
                reference_server.shutdown()
                reference_server.server_close()


if __name__ == '__main__':
    main()
