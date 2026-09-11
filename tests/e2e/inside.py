"""Browser flows and optional pixel comparison against the original compiled Vue UI.

uv run python tests/e2e/inside.py --original /path/to/reference
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
    output = ROOT / 'test-results' / 'inside'
    output.mkdir(parents=True, exist_ok=True)
    report = []
    with tempfile.TemporaryDirectory(prefix='grave-auth-browser-') as temp:
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
                raise RuntimeError('Django did not start; inspect test-results/inside/server.log')
            if args.original:
                handler = functools.partial(QuietHandler, directory=str(args.original / 'dist/frontend'))
                reference_server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
                threading.Thread(target=reference_server.serve_forever, daemon=True).start()
                reference_url = f'http://127.0.0.1:{reference_server.server_port}'
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                context = browser.new_context(viewport={'width': 1440, 'height': 1000})
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
                    reference = browser.new_page(viewport={'width': 1440, 'height': 1000})
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

                def both_button(name, **kwargs):
                    page.get_by_role('button',name=name,**kwargs).click()
                    if reference:
                        reference.get_by_role('button',name=name,**kwargs).click()

                def close_dialog():
                    both_button('Close',exact=True)
                    expect(page.get_by_role('dialog')).to_have_count(0)

                def refresh_reference():
                    if reference:
                        reference.reload()
                        expect(reference.locator('.gw-shell' if account['role']=='owner' else '.player-home')).to_be_visible()
                        reference.wait_for_timeout(200)

                capture('owner-empty')
                both_button('Settings',exact=True)
                expect(page.get_by_role('heading',name='Settings',exact=True)).to_be_visible()
                capture('owner-settings')
                both_button('Tables',exact=True)
                both_button('Begin my first journey',exact=True)
                expect(page.get_by_role('dialog')).to_be_visible()
                capture('create')
                for target in [page]+([reference] if reference else []):
                    target.get_by_placeholder('Campaign name').fill('The Lost Keep')
                    target.locator('textarea').fill('An old ruin and an unfinished story.')
                capture('create-filled')
                for target in [page]+([reference] if reference else []):
                    target.locator('input[type=file]').set_input_files({'name':'cover.png','mimeType':'image/png','buffer':cover_file.getvalue()})
                    expect(target.locator('.campaign-dialog__preview')).to_be_visible()
                capture('create-cover')
                page.get_by_role('button',name='Create table',exact=True).click()
                expect(page.get_by_role('dialog')).to_have_count(0)
                expect(page.get_by_role('heading',name='The Lost Keep')).to_be_visible()
                rows = page.request.get(base+'/api/containers').json()
                refresh_reference()
                capture('owner-library')
                both_button('List view',exact=True)
                capture('owner-list')
                both_button('Grid view',exact=True)
                both_button('Table options',exact=True)
                capture('owner-menu')
                both_button('Edit',exact=True)
                capture('edit')
                page.get_by_placeholder('Campaign name').fill('The Forgotten Keep')
                page.get_by_role('button',name='Save changes',exact=True).click()
                expect(page.get_by_role('dialog')).to_have_count(0)
                rows = page.request.get(base+'/api/containers').json()
                refresh_reference()
                both_button('Open The Forgotten Keep',exact=True)
                capture('owner-preview')
                close_dialog()
                both_button('Table options',exact=True)
                both_button('Invite',exact=True)
                capture('invite')
                page.get_by_role('button',name='Generate new code',exact=True).click()
                expect(page.locator('.campaign-dialog__code strong')).to_be_visible()
                temporary_code = page.locator('.campaign-dialog__code strong').inner_text()
                invitation = temporary_code
                if reference:
                    reference.get_by_role('button',name='Generate new code',exact=True).click()
                    expect(reference.locator('.campaign-dialog__code strong')).to_have_text(temporary_code)
                capture('invite-code')
                close_dialog()
                page.get_by_placeholder('Search tables',exact=True).fill('missing')
                expect(page.get_by_text('No tables match your search.')).to_be_visible()
                page.get_by_placeholder('Search tables',exact=True).fill('')
                expect(page.get_by_role('heading',name='The Forgotten Keep')).to_be_visible()
                # Keep owner browser alive while a separate player joins by invitation.
                owner_page = page
                player_context = browser.new_context(viewport={'width':1440,'height':1000})
                page = player_context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(base+'/register')
                page.locator('#owner-name').fill('Browser Player')
                page.locator('#owner-email').fill('player@example.test')
                page.locator('#owner-password').fill(PASSWORD)
                page.get_by_role('button',name='Create my account',exact=True).click()
                expect(page.locator('.player-home')).to_be_visible()
                account = {'name':'Browser Player','email':'player@example.test','role':'participant'}
                rows = []
                refresh_reference()
                capture('player-empty')
                page.get_by_placeholder('XXXX-XXXX',exact=True).fill(invitation)
                page.get_by_role('button',name='Join a table',exact=True).click()
                expect(page.get_by_role('heading',name='The Forgotten Keep')).to_be_visible()
                rows = page.request.get(base+'/api/containers').json()
                refresh_reference()
                capture('player-library')
                both_button('Open The Forgotten Keep',exact=True)
                capture('player-preview')
                close_dialog()
                both_button('Join campaign',exact=True)
                capture('player-join-another')
                both_button('Player settings',exact=True)
                capture('player-settings')
                page.get_by_label('Display name',exact=True).fill('Renamed Player')
                page.get_by_role('button',name='Save account',exact=True).click()
                expect(page.get_by_text('Profile saved.',exact=True)).to_be_visible()
                color = page.get_by_label('Identification color',exact=True)
                color.fill('#123456')
                color.dispatch_event('change')
                expect(page.get_by_text('Color saved for your account.',exact=True)).to_be_visible()
                page.get_by_role('button',name='Classic Icons over tokens on the map.').click()
                page.reload()
                page.get_by_role('button',name='Player settings',exact=True).click()
                expect(page.get_by_label('Identification color',exact=True)).to_have_value('#123456')
                expect(page.get_by_role('button',name='Classic Icons over tokens on the map.')).to_have_attribute('aria-pressed','true')
                page.get_by_label('Current password',exact=True).fill(PASSWORD)
                page.get_by_label('New password',exact=True).fill('changed-browser-password-123')
                page.get_by_label('Confirm new password',exact=True).fill('changed-browser-password-123')
                page.get_by_role('button',name='Save account',exact=True).click()
                expect(page.get_by_text('Account saved. Other sessions have been signed out.',exact=True)).to_be_visible()
                expect(page.get_by_label('New password',exact=True)).to_have_value('')
                expect(page.get_by_label('Current password',exact=True)).to_have_value('')
                expect(page.get_by_label('Confirm new password',exact=True)).to_have_value('')
                player_page = page
                page = owner_page
                account = {'name':'Browser Owner','email':'owner@example.test','role':'owner'}
                rows = page.request.get(base+'/api/containers').json()
                page.reload()
                refresh_reference()
                both_button('Table options',exact=True)
                both_button('Remove',exact=True)
                capture('remove')
                page.get_by_role('button',name='Confirm removal',exact=True).click()
                expect(page.locator('.campaign-dialog__code strong')).to_be_visible()
                temporary_code = page.locator('.campaign-dialog__code strong').inner_text()
                if reference:
                    reference.get_by_role('button',name='Confirm removal',exact=True).click()
                    expect(reference.locator('.campaign-dialog__code strong')).to_have_text(temporary_code)
                capture('remove-code')
                page.get_by_placeholder('XXXX-XXXX',exact=True).fill(temporary_code)
                page.get_by_role('button',name='Confirm removal',exact=True).click()
                expect(page.get_by_role('heading',name='Every universe begins in the void.')).to_be_visible()
                player_page.reload()
                expect(player_page.get_by_role('heading',name='Your next journey has not arrived yet.')).to_be_visible()
                assert not errors, errors
                assert not page.locator('script[src*="vue"]').count()
                browser.close()
            (output / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
            assert all(item['changed_pixel_ratio'] < 0.001 for item in report), report
            print('Browser Inside flows passed; development database untouched.', flush=True)
        finally:
            server.terminate()
            server.wait(timeout=10)
            log.close()
            if reference_server:
                reference_server.shutdown()
                reference_server.server_close()


if __name__ == '__main__':
    main()
