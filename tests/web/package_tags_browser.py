"""Package tags follow the installed Translator without changing catalog identity.

Uses an isolated Django account, signed synthetic packages and real language
preferences. Only Marketplace catalog/status replies are simulated in Chromium.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import unicodedata
from urllib.request import urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests/e2e')]
from map_builder import fixture_environment

LONG_TAG = 'HouseRule-' + 'x' * 54
ALIASES = {'Tradução': 'Translation', 'Idiomas': 'Languages', 'Dados': 'Dice',
           'Rolagens': 'Rolls', 'Fichas': 'Sheets', 'Automação': 'Automation'}
LABELS = {
    'en': {},
    'pt-BR': {'Translation': 'Tradução', 'Languages': 'Idiomas', 'Dice': 'Dados',
              'Rolls': 'Rolagens', 'Sheets': 'Fichas', 'Automation': 'Automação',
              'Interface': 'Interface', 'Django · Server': 'Django · Servidor'},
    'es': {'Translation': 'Traducción', 'Languages': 'Idiomas', 'Dice': 'Dados',
           'Rolls': 'Tiradas', 'Sheets': 'Fichas', 'Automation': 'Automatización',
           'Interface': 'Interfaz', 'Django · Server': 'Django · Servidor'},
}


def label(tag, locale):
    source = ALIASES.get(tag, tag)
    return LABELS[locale].get(source, source)


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value)
                   if not '\u0300' <= c <= '\u036f').lower()


def serve(fixture, port):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    key = Ed25519PrivateKey.generate()
    keyfile = fixture / 'public-keys.json'
    keyfile.write_text(json.dumps({'fixture': base64.b64encode(
        key.public_key().public_bytes_raw()).decode()}), encoding='utf-8')
    os.environ['GRAVEWRIGHT_MARKETPLACE_KEYS_FILE'] = str(keyfile)
    import django
    django.setup()
    from django.conf import settings
    from django.core.management import call_command
    from django.test import Client
    from gravewright.accounts.models import User
    from gravewright.modules.packages import canonical, host

    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    call_command('migrate', verbosity=0, interactive=False)
    owner = User.objects.create_user('tags@example.test', secrets.token_urlsafe(24),
                                     name='Synthetic tag reviewer', role='owner')
    client = Client(); client.force_login(owner)
    records, installed = [], []

    def package(identifier, name, kind='module', tags=None, locales=None, install=True):
        manifest = {'id': identifier, 'version': '0.1.0', 'name': name,
                    'description': 'Authored description: Settings / D&D / PDF.',
                    'author': 'Synthetic author', 'license': 'MIT', 'entry': 'main.js',
                    'sdk': {'requires': '>=1.0.0 <2.0.0', 'tested': '1.0.0'}}
        if kind == 'system': manifest['system'] = {'actorTypes': [{'id': 'character', 'label': 'Character'}]}
        if locales: manifest['locales'] = {code: {'name': code, 'path': f'{code}.json'} for code in locales}
        buffer = io.BytesIO()
        with ZipFile(buffer, 'w') as archive:
            archive.writestr('manifest.json', json.dumps(manifest))
            archive.writestr('main.js', 'export default {start(){},stop(){}};')
            for code, messages in (locales or {}).items(): archive.writestr(f'{code}.json', json.dumps(messages))
        raw = buffer.getvalue()
        record = {'id': identifier, 'version': '0.1.0', 'sdk': manifest['sdk']['requires'],
                  'download': 'https://publisher.invalid/package.zip', 'sha256': hashlib.sha256(raw).hexdigest(),
                  'keyId': 'fixture', 'name': name, 'description': manifest['description'], 'type': kind,
                  'tags': tags or []}
        record['signature'] = base64.b64encode(key.sign(canonical(record))).decode()
        if install:
            host().install(record, raw); installed.append(record)
        return record

    package('gravewright.translator', 'Synthetic Translator', locales={
        'pt-BR': {'Settings': 'Configurações'}, 'es': {'Settings': 'Configuración'}})
    samples = [('a', 'Settings', ['Translation', 'Languages', 'PDF', 'D&D', LONG_TAG], True),
               ('b', 'Beta synthetic', ['Tradução', 'Rolagens', 'Sheets'], True),
               ('c', 'Gamma synthetic', ['Idiomas', 'Dice', 'Automation', 'Interface', 'Fichas', 'Automação', 'Dados'], False),
               ('d', 'Delta synthetic', ['translation', 'Custom lore'], True)]
    for kind in ('system', 'module'):
        for suffix, name, tags, install in samples:
            records.append(package(f'example.tags-{kind}-{suffix}', name, kind, tags, install=install))
    server = dict(records[-2], id='example.tags-server', name='Synthetic Django package', type='django', tags=['Automation'])
    records.append(server)
    seed = {'records': records, 'installed': installed,
            'session': {'name': settings.SESSION_COOKIE_NAME, 'value': client.session.session_key}}
    (fixture / 'seed.json').write_text(json.dumps(seed, ensure_ascii=False), encoding='utf-8')
    call_command('runserver', f'127.0.0.1:{port}', use_reloader=False, verbosity=0)


def request(page, path, payload, form=False):
    return page.evaluate("""async ({path,payload,form}) => {
      const csrf=await (await fetch('/__gravewright/csrf')).json();
      const response=await fetch(path,{method:'POST',headers:{Accept:'application/json',
        [csrf.header]:csrf.token,'Content-Type':form?'application/x-www-form-urlencoded':'application/json'},
        body:form?new URLSearchParams(payload):JSON.stringify(payload)});
      return {status:response.status,body:await response.json()};
    }""", {'path': path, 'payload': payload, 'form': form})


def check_browser(base, seed, output, executable):
    from playwright.sync_api import Error as BrowserError, expect, sync_playwright
    cases, errors = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str(executable) if executable else None)
        context = browser.new_context(viewport={'width': 1440, 'height': 950})
        context.add_cookies([{**seed['session'], 'url': base}])
        context.add_init_script("""window.tagLocaleListeners=new Set();
          const add=window.addEventListener,remove=window.removeEventListener;
          window.addEventListener=function(type,listener,...rest){if(type==='gravewright:locale')tagLocaleListeners.add(listener);return add.call(this,type,listener,...rest)};
          window.removeEventListener=function(type,listener,...rest){if(type==='gravewright:locale')tagLocaleListeners.delete(listener);return remove.call(this,type,listener,...rest)};
        """)
        page = context.new_page(); page.on('pageerror', lambda error: errors.append(str(error)))
        page.route('**/api/marketplace/status', lambda route: route.fulfill(json={
            'ready': True, 'catalogConfigured': True, 'trustedKeysConfigured': True, 'errors': []}))
        page.route('**/api/marketplace?*', lambda route: route.fulfill(json=seed['records']))

        def identities(root):
            return root.locator('[data-package-id]').evaluate_all('els=>els.map(el=>el.dataset.packageId).sort()')

        def search(root, rows, locale):
            field = root.locator('input[type=search]')
            for query in dict.fromkeys(['Translation', 'Tradução', label('Translation', locale),
                                       'Rolagens', label('Rolls', locale), 'translation', LONG_TAG]):
                expected = sorted(row['id'] for row in rows if normalized(query) in normalized(' '.join([
                    row['id'], row['name'], row['description'], row['version'],
                    *row['tags'], *(label(tag, locale) for tag in row['tags'])])))
                field.fill(query)
                expect(root.locator('[data-count]')).to_have_text(f'{len(expected)} / {len(rows)}')
                assert identities(root) == expected, (locale, query, identities(root), expected)
            field.fill('')

        for active, locale in [(False, 'en'), (True, 'en'), (True, 'pt-BR'), (True, 'es')]:
            if active:
                if locale == 'en':
                    reply = request(page, '/api/module-packages/activation', {'id': 'gravewright.translator', 'version': '0.1.0', 'enabled': True})
                    assert reply['status'] == 200, reply
                reply = request(page, '/inside/language', {'locale': locale, 'next': '/inside'}, True)
                assert reply['status'] == 200, reply
            for kind, section in [('system', 'systems'), ('module', 'addons')]:
                page.goto(base + '/inside?section=' + section)
                expect(page.locator('html')).to_have_attribute('lang', locale)
                config = page.locator('#gravewright-language')
                if active: assert json.loads(config.text_content())['id'] == locale
                else: expect(config).to_have_count(0)
                installed = page.locator(f'[data-module-catalog=installed][data-package-kind={kind}]')
                expect(installed).to_have_attribute('data-busy', 'false')
                local = [row for row in seed['installed'] if row['type'] == kind]
                if kind == 'system':
                    local += [{'id': 'gravewright-pdf-system', 'name': 'Gravewright PDF System', 'description': '', 'version': '', 'tags': []}]
                search(installed, local, locale)
                expect(installed.locator('[data-package-id$="-a"] h3')).to_have_text('Settings')
                installed.locator('[data-action=browse]').click()
                catalog = page.locator(f'[data-module-catalog=marketplace][data-package-kind={kind}]')
                rows = [row for row in seed['records'] if (row['type'] == 'system') == (kind == 'system')]
                expect(catalog.locator('[data-package-id]')).to_have_count(len(rows))
                expected_counts = {}
                for row in rows:
                    for tag in row['tags']: expected_counts[tag] = expected_counts.get(tag, 0) + 1
                    card = catalog.locator(f'[data-package-id="{row["id"]}"]')
                    expect(card.locator('h3')).to_have_text(row['name'])
                    expect(card.locator('[data-card-description]')).to_have_text(row['description'])
                    expected_tags = [label(tag, locale) for tag in row['tags']]
                    if row['type'] == 'django': expected_tags.insert(0, label('Django · Server', locale))
                    assert card.locator('[data-tags] span').all_text_contents() == expected_tags
                category = catalog.locator('[data-category]').evaluate_all('els=>els.map(el=>({raw:el.dataset.category,label:el.firstElementChild.textContent,count:el.lastElementChild.textContent}))')
                for tag, count in expected_counts.items():
                    actual = next(row for row in category if row['raw'] == tag)
                    assert (actual['label'], actual['count']) == (label(tag, locale), str(count)), actual
                labels = [row['label'] for row in category if row['raw']]
                assert page.evaluate('({labels,locale})=>labels.every((v,i)=>!i||new Intl.Collator(locale,{numeric:true,sensitivity:"base"}).compare(labels[i-1],v)<=0)', {'labels': labels, 'locale': locale})
                catalog.locator('[data-category="Tradução"]').click()
                expect(catalog.locator('[data-category="Tradução"]')).to_have_attribute('aria-pressed', 'true')
                assert identities(catalog) == sorted(row['id'] for row in rows if 'Tradução' in row['tags'])
                catalog.locator('[data-state=installed]').click()
                expect(catalog.locator('[data-filter]')).to_have_value('installed')
                catalog.locator('[data-state=all]').click(); catalog.locator('[data-category=""]').click()
                search(catalog, rows, locale)
                authored = catalog.locator('[data-package-id$="-a"]')
                authored.scroll_into_view_if_needed()
                page.screenshot(path=str(output / f'{"translator" if active else "native"}-{locale}-{kind}-1440.png'))
                page.set_viewport_size({'width': 320, 'height': 844})
                authored.scroll_into_view_if_needed()
                geometry = catalog.evaluate('el=>({viewport:innerWidth,right:el.getBoundingClientRect().right,scroll:el.scrollWidth,width:el.clientWidth})')
                badges = authored.evaluate('el=>{const r=el.getBoundingClientRect(),tags=el.querySelector("[data-tags]").getBoundingClientRect();return [...el.querySelectorAll("[data-tags] span")].map(b=>({text:b.textContent,right:b.getBoundingClientRect().right,cardRight:r.right,tagsRight:tags.right,width:b.scrollWidth,client:b.clientWidth}))}')
                page.screenshot(path=str(output / f'{"translator" if active else "native"}-{locale}-{kind}-320.png'))
                assert geometry['right'] <= 321 and geometry['scroll'] <= geometry['width'] + 1, geometry
                assert all(badge['right'] <= min(badge['cardRight'], badge['tagsRight']) + 1
                           and badge['width'] <= badge['client'] + 1 for badge in badges), badges
                page.set_viewport_size({'width': 1440, 'height': 950})
                cases.append({'translator': active, 'locale': locale, 'kind': kind, 'categories': expected_counts, 'mobile': geometry})

        # Fetch the new real preference/configuration; exercise the adapter event
        # without replacing any rendered label or catalog identifier.
        reply = request(page, '/inside/language', {'locale': 'pt-BR', 'next': '/inside'}, True)
        assert reply['status'] == 200, reply
        catalog.locator('[data-category="Tradução"]').click()
        page.evaluate("""async()=>{
          const html=await (await fetch('/inside?section=addons')).text();
          const parsed=new DOMParser().parseFromString(html,'text/html');
          window.gravewrightLocale=JSON.parse(parsed.querySelector('#gravewright-language').textContent);
          window.dispatchEvent(new CustomEvent('gravewright:locale',{detail:window.gravewrightLocale}));
        }""")
        expect(catalog.locator('[data-category="Tradução"] span').first).to_have_text('Tradução')
        expect(catalog.locator('[data-category="Tradução"]')).to_have_attribute('aria-pressed', 'true')
        before = page.evaluate('tagLocaleListeners.size')
        catalog.evaluate('el=>el.remove()')
        page.wait_for_function('before=>tagLocaleListeners.size===before-1', arg=before)

        pending = []
        def delay_packages(route): pending.append(route)
        page.route('**/api/module-packages', delay_packages)
        page.goto(base + '/inside?section=systems')
        page.wait_for_function('document.querySelector("[data-module-catalog=installed]")?.dataset.busy==="true"')
        page.wait_for_function('!!window.gravewrightInside')
        page.locator('[data-package-manager]').evaluate('el=>{window.tagMount={el,parent:el.parentElement};el.remove()}')
        page.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
        page.evaluate('tagMount.parent.append(tagMount.el)')
        page.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
        page.unroute('**/api/module-packages', delay_packages)
        for route in pending:
            try: route.continue_()
            except BrowserError as error:
                if 'already handled' not in str(error) and 'closed' not in str(error) and 'Invalid InterceptionId' not in str(error): raise
        installed = page.locator('[data-module-catalog=installed]')
        expect(installed).to_have_attribute('data-busy', 'false')
        expect(installed.locator('[data-package-id$="-a"]')).to_be_visible()
        overflow = page.evaluate('document.body.style.overflow')
        installed.locator('[data-action=browse]').click()
        catalog = page.locator('[data-module-catalog=marketplace]')
        catalog.locator('[data-package-id$="-a"] [data-action=details]').click()
        expect(page.locator('.ownership-modal-overlay [data-package-detail]')).to_be_visible()
        page.locator('[data-package-manager]').evaluate('el=>el.remove()')
        expect(page.locator('.ownership-modal-overlay')).to_have_count(0)
        assert page.locator('#app').evaluate('el=>!el.inert')
        assert page.evaluate('document.body.style.overflow') == overflow
        page.evaluate('tagMount.parent.append(tagMount.el)')
        expect(installed).to_have_attribute('data-initialized', 'true')
        expect(catalog).to_have_attribute('data-initialized', 'true')
        assert installed.evaluate('el=>!el.inert')
        expect(installed.locator('[data-package-id$="-a"]')).to_be_visible()
        assert not errors, errors
        browser.close()
    return {'passed': True, 'cases': cases, 'dynamicLocaleAndDispose': True,
            'pendingRemountAndModalCleanup': True, 'pageErrors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--fixture', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--port', type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve: serve(args.fixture, args.port); return
    output = (args.output or ROOT / 'data/runner/tag-language-browser' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
    if output.exists() and any(output.iterdir()): raise RuntimeError('Use a fresh, empty output directory.')
    fixture = output / 'fixture'; fixture.mkdir(parents=True)
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0)); port = connection.getsockname()[1]
    fixture_environment(fixture, port)
    executable = sys._base_executable if os.name == 'nt' else sys.executable
    with (output / 'server.log').open('w', encoding='utf-8') as log:
        server = subprocess.Popen([executable, '-B', '-X', 'utf8', str(Path(__file__).resolve()), '--serve',
            '--fixture', str(fixture), '--port', str(port)], cwd=ROOT, env=os.environ.copy(), stdout=log, stderr=log)
        try:
            base = f'http://127.0.0.1:{port}'
            for _ in range(200):
                if server.poll() is not None: raise RuntimeError(f'Fixture failed: {output / "server.log"}')
                try:
                    with urlopen(base, timeout=1): break
                except OSError: time.sleep(.1)
            else: raise RuntimeError('Fixture did not start.')
            seed = json.loads((fixture / 'seed.json').read_text(encoding='utf-8'))
            report = check_browser(base, seed, output, args.browser_executable)
            (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps({'passed': True, 'cases': len(report['cases']), 'report': str(output / 'report.json')}))
        finally:
            server.terminate()
            try: server.wait(timeout=10)
            except subprocess.TimeoutExpired: server.kill(); server.wait()
            (output / 'server-exit.json').write_text(json.dumps({'pid': server.pid, 'exitCode': server.returncode}), encoding='utf-8')


if __name__ == '__main__':
    main()
