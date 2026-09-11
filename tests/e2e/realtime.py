"""Browser flows and optional pixel comparison against the original compiled Vue UI.

uv run python tests/e2e/realtime.py --original /path/to/reference
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
    output = ROOT / 'test-results' / 'realtime'
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
                if reference:
                    # The migrated tray is available before scenes exist. Match the
                    # original button's enabled state; dice.py exercises its window.
                    reference.locator('.game-dice-tray button').evaluate('el=>el.disabled=false')
                expect(page.locator('#chat-panel')).to_be_visible()
                capture('chat-empty')
                player_context=browser.new_context(viewport={'width':1440,'height':1000})
                player=player_context.new_page()
                player.on('pageerror',lambda error:errors.append(str(error)))
                player.goto(base+'/register')
                player.locator('#owner-name').fill('Browser Player')
                player.locator('#owner-email').fill('player@example.test')
                player.locator('#owner-password').fill(PASSWORD)
                player.get_by_role('button',name='Create my account',exact=True).click()
                player.get_by_placeholder('XXXX-XXXX',exact=True).fill(invitation)
                player.get_by_role('button',name='Join a table',exact=True).click()
                player.get_by_role('button',name='Open The Lost Keep',exact=True).click()
                player.get_by_role('button',name='Enter table',exact=True).click()
                seated(player)
                # First-time players see preferences before using the table.
                expect(player.locator('#table-workspace')).to_have_attribute('data-onboarding-ready','true')
                expect(player.locator('.house-menu-scrim')).to_be_visible()
                player.keyboard.press('Escape')
                expect(player.locator('.house-menu-scrim')).not_to_be_visible()
                expect(page.locator('.game-menubar__roster b')).to_have_text('2')
                online_members.append({'id':'player','name':'Browser Player','role':'player'})
                if reference:
                    reference_sockets[-1].send(json.dumps({'type':'table.presence','payload':{'members':online_members}}))
                both('Participants')
                capture('online-participants')
                both('Participants')
                page.get_by_role('textbox',name='Message… (/ for commands)').fill('Welcome to the table!')
                page.get_by_role('button',name='Send',exact=True).click()
                expect(page.locator('#chat-log article')).to_have_count(1)
                expect(page.locator('#chat-form textarea')).to_have_value('')
                player.get_by_role('button',name='Chat',exact=True).click()
                expect(player.locator('#chat-log article')).to_have_count(1)
                echo('Welcome to the table!','Browser Owner',1)
                player.locator('#chat-form textarea').fill('<img src=x onerror=alert(1)>')
                player.locator('#chat-form textarea').press('Enter')
                expect(page.locator('#chat-log article')).to_have_count(2)
                expect(player.locator('#chat-log article')).to_have_count(2)
                assert not page.locator('#chat-log img').count()
                echo('<img src=x onerror=alert(1)>','Browser Player',2)
                capture('chat-messages')
                both('Minimize')
                capture('chat-minimized')
                both('Minimize')
                # The movable panel keeps its original drag/resize behavior.
                header=page.locator('#chat-panel header')
                box=header.bounding_box()
                page.mouse.move(box['x']+50,box['y']+15);page.mouse.down();page.mouse.move(box['x']-80,box['y']+55);page.mouse.up()
                assert page.locator('#chat-panel').evaluate("el=>el.style.position")=='fixed'
                # A dropped connection restores history without duplicating messages.
                page.evaluate('window.__sockets.at(-1).close(4000)')
                seated(page)
                expect(page.locator('#chat-log article')).to_have_count(2)
                expect(page.locator('.game-menubar__roster b')).to_have_text('2')
                # Duplicate tabs and the detached chat count as one person.
                duplicate=player_context.new_page();duplicate.goto(base+'/game/'+rows[0]['id']);seated(duplicate)
                expect(page.locator('.game-menubar__roster b')).to_have_text('2')
                duplicate.close()
                with page.expect_popup() as opened:
                    page.get_by_role('button',name='Open in a window',exact=True).click()
                popup=opened.value
                expect(popup.locator('#chat-panel')).to_be_visible()
                expect(popup.locator('#chat-log article')).to_have_count(2)
                expect(page.locator('.game-menubar__roster b')).to_have_text('2')
                popup.close()
                expect(page.locator('#chat-panel')).to_be_visible()
                # A different table must never receive this chat or presence.
                other=post(page,'/api/containers',{'name':'Private table','system':'gravewright-pdf-system'}).json()
                other_page=context.new_page();other_page.goto(base+'/game/'+other['id']);seated(other_page)
                other_page.get_by_role('button',name='Chat',exact=True).click()
                expect(other_page.locator('#chat-log article')).to_have_count(0)
                other_page.locator('#chat-form textarea').fill('Only this other table')
                other_page.get_by_role('button',name='Send',exact=True).click()
                expect(other_page.locator('#chat-log article')).to_have_count(1)
                expect(page.locator('#chat-log article')).to_have_count(2)
                other_page.close()
                # Logout invalidates an already-open WebSocket, not just new requests.
                assert post(player,'/api/auth/logout',{}).ok
                expect(player.locator('.game-menubar__presence')).to_have_attribute('data-presence','offline',timeout=15000)
                expect(page.locator('.game-menubar__roster b')).to_have_text('1',timeout=15000)
                page.reload();seated(page);page.get_by_role('button',name='Chat',exact=True).click()
                expect(page.locator('#chat-log article')).to_have_count(2)
                assert not errors,errors
                browser.close()
            (output / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
            assert all(item['changed_pixel_ratio'] < 0.001 for item in report), report
            print('Browser WebSocket presence/chat flows passed; development database untouched.', flush=True)
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Reap only this fixture's server after its shutdown grace.
                server.kill()
                server.wait()
            log.close()
            if reference_server:
                reference_server.shutdown()
                reference_server.server_close()


if __name__ == '__main__':
    main()
