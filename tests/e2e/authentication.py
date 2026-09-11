"""Browser flows and optional pixel comparison against the original compiled Vue UI.

uv run python tests/e2e/authentication.py --original /path/to/reference
Uses a temporary database; never creates accounts in the development database.
"""
import argparse
import functools
import json
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
    output = ROOT / 'test-results' / 'authentication'
    output.mkdir(parents=True, exist_ok=True)
    report = []
    with tempfile.TemporaryDirectory(prefix='grave-auth-browser-') as temp:
        env = {**os.environ, 'GRAVEWRIGHT_DATABASE': str(Path(temp) / 'browser.sqlite3')}
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
                raise RuntimeError('Django did not start; inspect test-results/authentication/server.log')
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
                configured = False
                if reference_server:
                    reference = browser.new_page(viewport={'width': 1440, 'height': 1000})
                    def mock_auth(route):
                        path = route.request.url.split(reference_url)[-1].split('?')[0]
                        if path.endswith('/status'):
                            body, status = {'configured': configured}, 200
                        elif path.endswith('/session'):
                            body, status = {'authenticated': False}, 200
                        elif path.endswith('/login'):
                            body, status = {'error': 'invalid_credentials'}, 401
                        else:
                            body, status = {'ready': True, 'token': 'reference'}, 200
                        route.fulfill(status=status, json=body)
                    reference.route('**/api/**', mock_auth)
                    reference.route('**/__gravewright/csrf', mock_auth)
                    reference.goto(reference_url)
                    expect(reference.locator('#owner-name')).to_be_visible()
                page.goto(base)
                expect(page.locator('#owner-name')).to_be_visible()
                # Datastar loaded locally, with no Vue runtime in the new page.
                assert not errors, errors

                def capture(name):
                    for width, height in [(1440, 1000), (390, 844)]:
                        label = f'{name}-{width}'
                        page.set_viewport_size({'width': width, 'height': height})
                        page.mouse.move(0, 0)
                        page.locator('body').click(position={'x': 1, 'y': 1})
                        # Let CSS transitions settle after mouse/focus changes.
                        page.wait_for_timeout(250)
                        target = output / f'{label}-django.png'
                        page.screenshot(path=str(target), full_page=True, animations='disabled', caret='hide')
                        if reference:
                            reference.set_viewport_size({'width': width, 'height': height})
                            reference.mouse.move(0, 0)
                            reference.locator('body').click(position={'x': 1, 'y': 1})
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

                capture('setup')
                page.get_by_role('tab', name='Privacy').click()
                expect(page.locator('#owner-privacy-panel')).to_be_visible()
                if reference:
                    reference.get_by_role('tab', name='Privacy').click()
                capture('privacy-setup')
                page.get_by_role('tab', name='Setup').click()
                page.locator('#owner-name').fill('Browser Owner')
                page.locator('#owner-email').fill('owner@example.test')
                page.locator('#owner-password').fill(PASSWORD)
                page.get_by_role('button', name='Create administrator').click()
                expect(page.get_by_role('heading', name='Every universe begins in the void.')).to_be_visible()
                page.reload()
                expect(page.get_by_role('heading', name='Every universe begins in the void.')).to_be_visible()
                page.get_by_role('button', name='Sign out').click()
                expect(page.get_by_role('button', name='Enter Gravewright')).to_be_visible()
                configured = True
                if reference:
                    reference.goto(reference_url)
                    expect(reference.get_by_role('button', name='Enter Gravewright')).to_be_visible()
                capture('login')
                page.locator('#owner-email').fill('wrong@example.test')
                page.locator('#owner-password').fill('wrong-password-123')
                page.get_by_role('button', name='Enter Gravewright').click()
                expect(page.get_by_role('alert').filter(has_text='The email or password is incorrect.')).to_be_visible()
                # Like the original, failed login preserves the local input value;
                # the server response never echoes passwords.
                expect(page.locator('#owner-password')).to_have_value('wrong-password-123')
                if reference:
                    reference.locator('#owner-email').fill('wrong@example.test')
                    reference.locator('#owner-password').fill('wrong-password-123')
                    reference.get_by_role('button', name='Enter Gravewright').click()
                    expect(reference.get_by_role('alert')).to_be_visible()
                capture('login-error')
                page.get_by_role('button', name='Create account', exact=True).click()
                expect(page.locator('#owner-name')).to_be_visible()
                expect(page.locator('#owner-password')).to_have_value('')
                if reference:
                    reference.get_by_role('button', name='Create account', exact=True).click()
                capture('register')
                page.locator('#owner-name').fill('Browser Player')
                page.locator('#owner-email').fill('player@example.test')
                page.get_by_role('button', name='Return to login').click()
                expect(page.get_by_role('button', name='Enter Gravewright')).to_be_visible()
                expect(page.locator('#owner-email')).to_have_value('player@example.test')
                page.get_by_role('button', name='Create account', exact=True).click()
                expect(page.locator('#owner-name')).to_have_value('Browser Player')
                page.locator('#owner-password').fill(PASSWORD)
                page.get_by_role('button', name='Create my account').click()
                expect(page.get_by_role('heading', name='Your next journey has not arrived yet.')).to_be_visible()
                assert page.request.get(base + '/api/home/gm').status == 403
                assert page.request.get(base + '/api/home/player').status == 200
                page.get_by_role('button', name='Sign out').click()
                expect(page.get_by_role('button', name='Enter Gravewright')).to_be_visible()
                page.locator('#owner-email').fill(' OWNER@EXAMPLE.TEST ')
                page.locator('#owner-password').fill(PASSWORD)
                page.get_by_role('button', name='Enter Gravewright').click()
                expect(page.get_by_role('heading', name='Every universe begins in the void.')).to_be_visible()
                assert page.request.get(base + '/api/home/gm').status == 200
                page.get_by_role('button', name='Sign out').click()
                expect(page.get_by_role('button', name='Enter Gravewright')).to_be_visible()
                page.locator('#owner-email').fill('owner@example.test')
                page.locator('#owner-password').fill(PASSWORD)
                page.locator('[name=csrfmiddlewaretoken]').evaluate("el => el.value = 'forged'")
                page.get_by_role('button', name='Enter Gravewright').click()
                expect(page.get_by_role('alert').filter(has_text='The secure form expired. Try again.')).to_be_visible()
                assert not page.request.get(base + '/api/auth/session').json()['authenticated']
                page.get_by_role('button', name='Enter Gravewright').click()
                expect(page.get_by_role('heading', name='Every universe begins in the void.')).to_be_visible()
                assert not errors, errors
                assert not page.locator('script[src*="vue"]').count()
                browser.close()
            (output / 'comparison.json').write_text(json.dumps(report, indent=2) + '\n')
            assert all(item['changed_pixel_ratio'] < 0.001 for item in report), report
            print('Browser authentication flows passed; development database untouched.', flush=True)
        finally:
            server.terminate()
            server.wait(timeout=10)
            log.close()
            if reference_server:
                reference_server.shutdown()
                reference_server.server_close()


if __name__ == '__main__':
    main()
