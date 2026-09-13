"""Install a signed system through a temporary HTTPS marketplace in Chromium.

Run: uv run --locked python tests/e2e/marketplace.py
All keys, packages, certificates, accounts, databases and media are temporary.
"""

import base64
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import os
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from urllib.request import urlopen
import zipfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from playwright.sync_api import expect, sync_playwright

from https import certificate, free_port

ROOT = Path(__file__).resolve().parents[2]
SEED = """
import django, json
django.setup()
from django.conf import settings
from django.test import Client
from gravewright.accounts.models import User
user = User.objects.create_user('owner@marketplace.test', 'marketplace-password-123', name='Owner', role='owner')
client = Client()
client.force_login(user)
print(json.dumps({'name': settings.SESSION_COOKIE_NAME, 'value': client.session.session_key}))
"""


@contextmanager
def publisher(directory):
    key_path, cert_path, _ = certificate(directory)
    state = {'records': [], 'archive': b''}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/catalog.json':
                raw = json.dumps(state['records']).encode()
            elif self.path == '/system.zip':
                raw = state['archive']
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            if self.path == '/system.zip' and state.get('slow'):
                for offset in range(0, len(raw), 65536):
                    self.wfile.write(raw[offset:offset+65536]); self.wfile.flush(); time.sleep(.12)
            else:
                self.wfile.write(raw)

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cert_path, key_path)
        server.socket = tls.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f'https://127.0.0.1:{server.server_port}', cert_path, state
        finally:
            server.shutdown()
            thread.join(timeout=5)


def signed_system(base, state):
    key = Ed25519PrivateKey.generate()
    keys = {'browser-test': base64.b64encode(key.public_key().public_bytes_raw()).decode()}
    manifest = {
        'id': 'example.browser-system', 'name': 'Browser RPG', 'version': '1.0.0',
        'description': 'Signed system integration fixture', 'author': 'Test', 'license': 'MIT',
        'sdk': {'requires': '>=1.0.0 <2.0.0', 'tested': '1.0.0'}, 'entry': 'main.js',
        'system': {
            'actorTypes': [{'id': 'character', 'label': 'Character'}, {'id': 'npc', 'label': 'NPC'}],
            'itemTypes': [{'id': 'gear', 'label': 'Gear'}],
        },
    }
    archive = BytesIO()
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr('manifest.json', json.dumps(manifest))
        zipped.writestr('main.js', 'export default {start(){},register(){},stop(){}};')
        zipped.writestr('data/padding.json', json.dumps({'testData':'x' * 524288}))
    state['archive'] = archive.getvalue()
    record = {
        'id': manifest['id'], 'version': manifest['version'], 'sdk': manifest['sdk']['requires'],
        'download': base + '/system.zip', 'sha256': hashlib.sha256(state['archive']).hexdigest(),
        'keyId': 'browser-test', 'type': 'system', 'tags': ['RPG', 'Fantasy'],
    }
    canonical = json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    record['signature'] = base64.b64encode(key.sign(canonical)).decode()
    state['records'] = [record]
    return keys


def check(page, base, keys_file, keys, feed):
    library = page.locator('[data-module-catalog=installed]')
    browser = page.locator('[data-package-browser]')
    catalog = browser.locator('[data-module-catalog=marketplace]')
    page.goto(base + '/inside?section=addons')
    library.locator('[data-action=browse]').click()
    expect(catalog.locator('.module-catalog__empty')).to_be_visible()
    expect(catalog.locator('.module-catalog__card')).to_have_count(0)
    page.keyboard.press('Escape')
    page.goto(base + '/inside?section=systems')
    expect(library.locator('.module-catalog__card h3')).to_have_text('Gravewright PDF System')
    library.locator('[data-action=browse]').click()
    expect(catalog.locator('.module-catalog__card h3')).to_have_text('example.browser-system')
    assert len(page.request.get(base + '/api/rulesets').json()['rulesets']) == 1
    feed['slow'] = True
    catalog.locator('[data-action=install]').click()
    expect(catalog.locator('[data-install-progress]')).to_have_attribute('data-stage','download')
    expect(catalog.locator('[data-progress-label]')).to_contain_text('MB')
    page.screenshot(path='/tmp/marketplace-install-progress.png')
    expect(catalog.locator('[data-install-progress]')).to_have_attribute('data-stage','complete',timeout=15000)
    expect(catalog.locator('.module-catalog__notice')).to_contain_text('installed', timeout=15000)
    expect(catalog.locator('.module-catalog__card-footer [data-status]')).to_have_text('Installed')
    browser.locator('[data-action=close-browser]').click()
    expect(library.locator('.module-catalog__card h3')).to_have_text(['Browser RPG','Gravewright PDF System'])

    page.goto(base + '/inside/dialog/create')
    page.locator('[name=name][form=campaign-form]').fill('Marketplace campaign')
    page.locator('[name=system][form=campaign-form]').select_option('example.browser-system')
    page.locator('button[type=submit][form=campaign-form]').click()
    expect(page.locator('#campaign-dialog')).to_have_count(0)
    campaigns = page.request.get(base + '/api/containers').json()
    assert campaigns[0]['system'] == 'example.browser-system', campaigns

    campaign_id = campaigns[0]['id']
    page.evaluate("""async id => {
        const {HttpClient} = await import('/static/gravewright_modules/http-client.js');
        await new HttpClient().post(`/api/containers/${id}/onboarding`, {dismissed:true});
    }""", campaign_id)
    page.goto(base + '/game/' + campaign_id)
    page.get_by_role('button', name='Actors', exact=True).click()
    page.locator('[data-actor-panel=create]').click()
    form = page.locator('form.directory-dialog').filter(has=page.locator('[name=actorType]'))
    form.locator('[name=name]').fill('Marketplace NPC')
    form.locator('[name=actorType]').select_option('npc')
    form.locator('[type=submit]').click()
    expect(form).to_have_count(0)
    actors = page.request.get(base + f'/api/containers/{campaign_id}/actors').json()
    assert actors['actors'][0]['actorType'] == 'npc', actors
    assert actors['actors'][0]['systemId'] == 'example.browser-system', actors

    keys_file.write_text('invalid json')
    requests = []
    page.on('request', lambda request: requests.append(request.url))
    page.goto(base + '/inside?section=systems')
    expect(library.locator('.module-catalog__card h3')).to_have_text(['Browser RPG','Gravewright PDF System'])
    assert not any('/api/marketplace' in url for url in requests), requests
    library.locator('[data-action=browse]').click()
    expect(catalog.locator('.module-catalog__setup')).to_be_visible()
    expect(catalog.locator('[data-setup=keys]')).to_contain_text('JSON object')
    keys_file.write_text(json.dumps(keys))
    catalog.locator('[data-action=refresh]').click()
    expect(catalog.locator('.module-catalog__card h3')).to_have_text('Browser RPG')
    expect(catalog.locator('.module-catalog__setup')).to_be_hidden()
    feed['records'] = [{**feed['records'][0], 'signature': base64.b64encode(b'x' * 64).decode()}]
    catalog.locator('[data-action=refresh]').click()
    expect(catalog.locator('.module-catalog__error')).to_contain_text('signature')
    expect(catalog.locator('.module-catalog__card')).to_have_count(0)
    page.keyboard.press('Escape')
    expect(library.locator('.module-catalog__card h3')).to_have_text(['Browser RPG','Gravewright PDF System'])


def check_large_library(page, base):
    rows = [{'id': f'example.module{i:02}', 'name': f'Módulo {i:02}', 'version': '1.0.0',
             'description': 'Module details', 'revoked': False} for i in range(70)]
    rows.append({'id':'example.system', 'name':'Test system', 'version':'1.0.0', 'system':{}, 'revoked':False})
    records = [{'id':'example.new-module', 'name':'New module', 'version':'1.0.0', 'type':'module','tags':['Translation','Interface']},
               {'id':'example.new-system', 'name':'New system', 'version':'1.0.0', 'type':'system','tags':['Fantasy']}]
    page.route('**/api/module-packages', lambda route: route.fulfill(json=rows))
    page.route('**/api/marketplace/status', lambda route: route.fulfill(json={'ready':True,'catalogConfigured':True,'trustedKeysConfigured':True}))
    page.route('**/api/marketplace', lambda route: route.fulfill(json=records))
    page.set_viewport_size({'width':1600, 'height':1000})
    page.goto(base + '/inside?section=addons')
    root = page.locator('[data-module-catalog=installed]')
    cards = root.locator('.module-catalog__card')
    expect(cards).to_have_count(24)
    expect(root.locator('[data-count]')).to_have_text('70 / 70')
    left, right = cards.nth(0).bounding_box(), cards.nth(1).bounding_box()
    assert left['y'] == right['y'] and right['x'] > left['x']
    root.locator('[data-view-mode=list]').click()
    assert cards.nth(1).bounding_box()['y'] > cards.nth(0).bounding_box()['y']
    page.reload()
    expect(root).to_have_attribute('data-view', 'list')
    root.locator('[data-view-mode=tiles]').click()
    root.locator('[data-action=next]').click()
    expect(cards.first.locator('h3')).to_have_text('Módulo 24')
    root.locator('input[type=search]').fill('modulo 23')
    expect(cards).to_have_count(1)
    cards.locator('[data-action=details]').click()
    expect(root.locator('[data-package-detail]')).to_be_visible()
    page.keyboard.press('Escape')
    root.locator('[data-action=browse]').click()
    browser = page.locator('[data-package-browser]')
    expect(browser.locator('.module-catalog__card h3')).to_have_text('New module')
    expect(browser.locator('[data-category=Translation]')).to_be_visible()
    browser.locator('[data-category=Translation]').click()
    expect(browser.locator('.module-catalog__card')).to_have_count(1)
    browser.locator('[data-state=installed]').click()
    expect(browser.locator('.module-catalog__card')).to_have_count(0)
    browser.locator('[data-state=available]').click()
    expect(browser.locator('.module-catalog__card')).to_have_count(1)
    page.keyboard.press('Escape')
    expect(browser).not_to_be_visible()
    page.goto(base + '/inside?section=systems')
    expect(root.locator('.module-catalog__card h3')).to_have_text(['Gravewright PDF System','Test system'])
    root.locator('[data-action=browse]').click()
    expect(browser.locator('.module-catalog__card h3')).to_have_text('New system')
    expect(browser.locator('[data-category=Fantasy]')).to_be_visible()
    expect(browser.locator('[data-category=Translation]')).to_have_count(0)
    page.keyboard.press('Escape')
    page.set_viewport_size({'width':390, 'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.unroute_all(behavior='wait')


def main():
    with tempfile.TemporaryDirectory(prefix='grave-marketplace-') as temp:
        directory = Path(temp)
        with publisher(directory) as (catalog_base, certificate_path, feed):
            keys = signed_system(catalog_base, feed)
            keys_file = directory / 'keys.json'
            keys_file.write_text(json.dumps(keys))
            env = {
                **os.environ, 'DJANGO_SETTINGS_MODULE': 'config.settings', 'DJANGO_DEBUG': 'true',
                'DJANGO_ALLOWED_HOSTS': '127.0.0.1,localhost,testserver',
                'GRAVEWRIGHT_DATABASE': str(directory / 'db.sqlite3'),
                'GRAVEWRIGHT_MEDIA_ROOT': str(directory / 'media'),
                'GRAVEWRIGHT_PUBLIC_ORIGIN': '', 'DJANGO_SECURE_COOKIES': 'false',
                'GRAVEWRIGHT_REDIS_URL': '', 'TRUSTED_PROXIES': '', 'GRAVEWRIGHT_RELEASES_REPOSITORY': '',
                'GRAVEWRIGHT_MARKETPLACE_URL': catalog_base + '/catalog.json',
                'GRAVEWRIGHT_MARKETPLACE_KEYS_FILE': str(keys_file),
                'SSL_CERT_FILE': str(certificate_path),
            }
            subprocess.run([sys.executable, 'manage.py', 'migrate', '--noinput'], cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)
            cookie = json.loads(subprocess.check_output([sys.executable, '-c', SEED], cwd=ROOT, env=env, text=True))
            address = f'127.0.0.1:{free_port()}'
            base = f'http://{address}'
            with (directory / 'server.log').open('w') as log:
                server = subprocess.Popen([sys.executable, 'manage.py', 'runserver', address, '--noreload'], cwd=ROOT, env=env, stdout=log, stderr=log)
                try:
                    for _ in range(100):
                        try:
                            urlopen(base, timeout=1).close()
                            break
                        except OSError:
                            time.sleep(.1)
                    else:
                        raise RuntimeError('Test server failed to start')
                    with sync_playwright() as pw:
                        browser = pw.chromium.launch()
                        context = browser.new_context()
                        context.add_cookies([{**cookie, 'url': base}])
                        page = context.new_page()
                        errors = []
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        check(page, base, keys_file, keys, feed)
                        check_large_library(page, base)
                        assert not errors, errors
                        browser.close()
                    print('Marketplace: HTTPS signed installation, system selection, campaign and NPC creation, invalid keys, stale catalog cleanup, 70-package library and typed installation dialogs passed.')
                except Exception:
                    log.flush()
                    print((directory / 'server.log').read_text()[-8000:], file=sys.stderr)
                    raise
                finally:
                    server.terminate()
                    try:
                        server.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        server.kill()
                        server.wait()


if __name__ == '__main__':
    main()
