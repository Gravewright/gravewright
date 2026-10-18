"""Exercise the GM's independent Map Builder entry with disposable campaigns.

Creates its own database, synthetic language package and map tiles. No operator
configuration, campaign, media or installed package is reused. Browser results
remain under the installation's data directory by default.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import sysconfig
import time
from urllib.request import urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def fixture_environment(fixture, port):
    from scripts.runtime_storage import configure_runtime_storage

    configure_runtime_storage(ROOT, fixture / 'tools')
    os.environ.update({
        'PYTHON_DOTENV_DISABLED': '1', 'PYTHONDONTWRITEBYTECODE': '1',
        'DJANGO_SETTINGS_MODULE': 'config.settings', 'DJANGO_DEBUG': 'true',
        'DJANGO_SECRET_KEY': secrets.token_urlsafe(64), 'DEFAULT_LOCALE': 'en',
        'DJANGO_ALLOWED_HOSTS': '127.0.0.1,localhost,testserver',
        'DJANGO_SECURE_COOKIES': 'false',
        'GRAVEWRIGHT_DATABASE': str(fixture / 'review.sqlite3'),
        'GRAVEWRIGHT_MEDIA_ROOT': str(fixture / 'media'),
        'GRAVEWRIGHT_MODULES_ROOT': str(fixture / 'modules'),
        'GRAVEWRIGHT_CONTENT_ROOT': str(fixture / 'content'),
        'GRAVEWRIGHT_SERVER_APPS': '', 'GRAVEWRIGHT_SERVER_APP_PATHS': '',
        'GRAVEWRIGHT_API_MODULES_ROOT': '', 'GRAVEWRIGHT_DJANGO_MODULES_ROOT': '',
        'GRAVEWRIGHT_DJANGO_REGISTRY': str(fixture / 'modules/server-apps.json'),
        'GRAVEWRIGHT_REDIS_URL': '', 'GRAVEWRIGHT_MARKETPLACE_URL': '',
        'GRAVEWRIGHT_MARKETPLACE_KEYS_FILE': '', 'GRAVEWRIGHT_RELEASES_REPOSITORY': '',
        'GRAVEWRIGHT_PUBLIC_ORIGIN': '', 'TRUSTED_PROXIES': '',
        'GRAVEWRIGHT_HOST': '127.0.0.1', 'GRAVEWRIGHT_PORT': str(port),
    })
    # Launch the base interpreter directly on Windows so terminating the owned
    # server does not leave the venv redirector's child Daphne process behind.
    os.environ['PYTHONPATH'] = os.pathsep.join((sysconfig.get_path('purelib'), str(ROOT)))


def serve(fixture, port):
    import django
    django.setup()
    from copy import deepcopy
    from datetime import timedelta
    from django.conf import settings
    from django.core.files.base import ContentFile
    from django.core.management import call_command
    from django.test import Client
    from django.utils import timezone as django_timezone
    from gravewright.accounts.models import User
    from gravewright.campaigns.models import Campaign, Membership, Onboarding, StreamerLink
    from gravewright.maps.models import Broadcast, Folder, Scene, SceneNavigation, SceneState, Tile
    from gravewright.maps.services import DEFAULTS
    from gravewright.modules.packages import host
    from PIL import Image

    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    call_command('migrate', verbosity=0, interactive=False)
    users = {
        name: User.objects.create_user(
            f'{name}@map-builder.test', secrets.token_urlsafe(20), name=name.title(),
            role='owner' if name == 'gm' else 'participant',
        ) for name in ('gm', 'player', 'streamer')
    }
    campaign = Campaign.objects.create(owner=users['gm'], name='Synthetic map workshop', system='')
    sessions = {}
    for role, user in users.items():
        member = Membership.objects.create(campaign=campaign, user=user, role=role)
        Onboarding.objects.create(membership=member, dismissed=True, player_shown_at=django_timezone.now())
        if role == 'streamer':
            StreamerLink.objects.create(
                campaign=campaign, guest=user, digest='a' * 64,
                expires_at=django_timezone.now() + timedelta(hours=2),
            )
        client = Client(); client.force_login(user)
        sessions[role] = {'name': settings.SESSION_COOKIE_NAME,
                          'value': client.cookies[settings.SESSION_COOKIE_NAME].value}

    # The fixture package activates the host's reviewed pt-BR/es catalogs via
    # the same public package path as a real Translator installation.
    manifest = {
        'id': 'gravewright.translator', 'version': '0.1.0',
        'name': 'Synthetic builder languages', 'description': 'Disposable browser fixture',
        'author': 'Gravewright tests', 'license': 'MIT', 'entry': 'main.js',
        'sdk': {'requires': '>=1.0.0 <2.0.0', 'tested': '1.0.0'},
        'locales': {locale: {'name': locale, 'path': f'locales/{locale}.json'}
                    for locale in ('pt-BR', 'es')},
    }
    source = BytesIO()
    with ZipFile(source, 'w') as archive:
        archive.writestr('manifest.json', json.dumps(manifest))
        archive.writestr('main.js', 'export default {start(){},stop(){}};')
        common = {
            'pt-BR': {'Map Builder': 'Map Builder', 'Folder': 'Pasta', 'Width': 'Largura',
                      'Height': 'Altura', 'Background': 'Fundo'},
            'es': {'Map Builder': 'Map Builder', 'Folder': 'Carpeta', 'Width': 'Anchura',
                   'Height': 'Altura', 'Background': 'Fondo'},
        }
        for locale in manifest['locales']:
            archive.writestr(f'locales/{locale}.json', json.dumps(common[locale]))
    host().install_local(source.getvalue(), expected_type='module')
    client = Client(); client.force_login(users['gm'])
    activated = client.post('/api/module-packages/activation', {
        'id': manifest['id'], 'version': manifest['version'], 'enabled': True,
    }, content_type='application/json')
    assert activated.status_code == 200, activated.content

    parent = Folder.objects.create(campaign=campaign, label='Prepared encounters')
    folder = Folder.objects.create(campaign=campaign, parent=parent, label='Workshop maps')
    scenes = []
    for name, color in [('Players remain here', '#45635c'), ('GM private selection', '#605840')]:
        scene = Scene.objects.create(
            campaign=campaign, folder=folder, name=name, width=512, height=512,
            settings={**deepcopy(DEFAULTS), 'initialView': {'x': 0, 'y': 0, 'scale': 1}},
        )
        image = BytesIO(); Image.new('RGB', (512, 512), color).save(image, 'WEBP')
        tile = Tile(scene=scene, lod=0, x=0, y=0)
        tile.file.save(f'{scene.pk}.webp', ContentFile(image.getvalue()), save=True)
        SceneState.objects.create(scene=scene, lighting={'darkness': 0.25})
        scenes.append(scene)
    Broadcast.objects.create(campaign=campaign, scene=scenes[0])
    SceneNavigation.objects.create(membership=campaign.memberships.get(user=users['gm']), scene=scenes[1])
    seed = {
        'campaign': str(campaign.pk), 'selectedScene': str(scenes[1].pk),
        'broadcastScene': str(scenes[0].pk), 'folder': str(folder.pk),
        'parentFolder': str(parent.pk), 'sessions': sessions,
    }
    (fixture / 'seed.json').write_text(json.dumps(seed, indent=2), encoding='utf-8')
    call_command('runserver', f'127.0.0.1:{port}', use_reloader=False, verbosity=0)


def snapshot():
    import django
    django.setup()
    from django.apps import apps
    print(json.dumps({
        model._meta.label: list(model.objects.order_by('pk').values())
        for model in apps.get_app_config('gravewright_maps').get_models()
    }, default=str, sort_keys=True))


MEASURE = """root=>{
 const tiny=[],overflow=[],viewport=document.documentElement.clientWidth;
 for(const el of [root,...root.querySelectorAll('*')]){
  if(!el.checkVisibility({checkVisibilityCSS:true})||el.closest('svg')||el.matches('option'))continue;
  const css=getComputedStyle(el),r=el.getBoundingClientRect();
  const text=[...el.childNodes].some(n=>n.nodeType===3&&n.textContent.trim());
  if((text||el.matches('input,select,textarea'))&&parseFloat(css.fontSize)<12)tiny.push({tag:el.tagName,size:css.fontSize});
  let left=r.left,right=r.right;
  for(let parent=el.parentElement;parent;parent=parent.parentElement){
   if(/auto|scroll|hidden|clip/.test(getComputedStyle(parent).overflowX)&&parent.scrollWidth>parent.clientWidth){
    const clip=parent.getBoundingClientRect();left=Math.max(left,clip.left);right=Math.min(right,clip.right);
   }
  }
  if(right>left&&(left < -2 || right>viewport+2))overflow.push({tag:el.tagName,cls:el.className});
  if(el.matches('button')&&css.overflowX==='visible'&&el.scrollWidth>el.clientWidth+2)
   overflow.push({tag:el.tagName,cls:el.className,reason:'button-content-overflow',text:el.textContent.trim()});
 }
 return {tiny,overflow,scrollWidth:document.documentElement.scrollWidth,viewport};
}"""


def change_locale(page, locale, campaign):
    result = page.evaluate("""async args=>{
      const csrf=await (await fetch('/__gravewright/csrf')).json();
      const response=await fetch('/inside/language',{method:'POST',
        headers:{Accept:'application/json',[csrf.header]:csrf.token,
          'Content-Type':'application/x-www-form-urlencoded'},
        body:new URLSearchParams({locale:args.locale,next:'/game/'+args.campaign})});
      return response.status;
    }""", {'locale': locale, 'campaign': campaign})
    assert result == 200, (locale, result)


def builder_workspace(page):
    """Leave the canvas accessible without changing the library dock."""
    close = page.locator('[data-builder-close-panel]')
    if close.is_visible():
        close.click()


def builder_sidebar(page, tab):
    """Open the bottom library or an auxiliary panel through visible controls."""
    if tab == 'library':
        builder_workspace(page)
        toggle = page.locator('[data-builder-library-toggle]')
        if toggle.get_attribute('aria-expanded') == 'false':
            toggle.click()
        return
    drawer_tab = page.locator(f'[data-builder-sidebar-tab={tab}][role=tab]:visible')
    if drawer_tab.is_visible():
        if drawer_tab.get_attribute('aria-selected') != 'true':
            drawer_tab.click()
    else:
        page.locator('.map-builder__layers-toggle').click()
        if tab != 'layers':
            page.locator(f'[data-builder-sidebar-tab={tab}][role=tab]').click()
    if tab == 'settings':
        details = page.locator('[data-builder-settings]')
        if not details.evaluate('el=>el.open'):
            details.locator('summary').click()


def builder_tool(page, tool):
    """Choose a tool from the editor panel; its contextual options stay open."""
    if tool in ('erase', 'pan'):
        builder_workspace(page)
        page.locator('[data-builder-viewport]').focus()
        page.keyboard.press('e' if tool == 'erase' else 'h')
    else:
        builder_sidebar(page, 'tools')
        page.locator(f'[data-builder-tool={tool}]').click()


def builder_library_settings(page):
    builder_sidebar(page, 'library')
    details = page.locator('.map-builder__asset-details')
    if not details.evaluate('el=>el.open'):
        details.locator('summary').click()


def check_browser(base, seed, output, executable, db_snapshot):
    from PIL import Image
    from playwright.sync_api import expect, sync_playwright

    errors, records, failed_requests = [], [], []
    game = f"{base}/game/{seed['campaign']}"
    builder = game + '/map-builder'
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            ignore_default_args=['--disable-back-forward-cache'],
            **({'executable_path': str(executable)} if executable else {}),
        )

        def context(role='gm', width=1440, height=900):
            ctx = browser.new_context(viewport={'width': width, 'height': height})
            if role:
                ctx.add_cookies([{**seed['sessions'][role], 'url': base}])
            ctx.add_init_script("""window.builderSockets=[];
              window.builderPageShows=[];
              addEventListener('pageshow',event=>builderPageShows.push({persisted:event.persisted}));
              const Native=window.WebSocket;
              window.WebSocket=class extends Native{constructor(...args){super(...args);window.builderSockets.push(this)}};
            """)
            def observe(page):
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('requestfailed', lambda request: failed_requests.append({
                    'url': request.url, 'error': request.failure, 'page': page.url,
                }))
            ctx.on('page', observe)
            return ctx

        def open_game(page):
            page.goto(game)
            page.wait_for_function('id=>window.gravewrightMaps?.current?.id===id', arg=seed['selectedScene'])
            page.wait_for_function('window.gravewrightMaps?.board?.viewport()?.scale>0')
            expect(page.locator('.game-board__surface canvas')).to_be_visible()

        def returned_game(page):
            page.wait_for_function('id=>window.gravewrightMaps?.current?.id===id', arg=seed['selectedScene'])
            page.wait_for_function('window.gravewrightMaps?.board?.viewport()?.scale>0')
            surface = page.locator('.game-board__surface')
            expect(surface.locator('canvas')).to_be_visible()
            scale = page.evaluate('gravewrightMaps.board.viewport().scale')
            surface.dispatch_event('wheel', {'deltaY': -100, 'clientX': 900, 'clientY': 400, 'bubbles': True})
            page.wait_for_function('scale=>gravewrightMaps.board.viewport().scale>scale', arg=scale)
            return {'pageShows': page.evaluate('builderPageShows'), 'interactiveCanvas': True}

        def chooser(page, folder=None):
            page.evaluate('gravewrightMaps.showDirectory()')
            expect(page.locator('#maps-panel')).to_be_visible()
            if folder:
                toggle = page.locator(f'[data-map-folder="{seed["parentFolder"]}"] > header > .gw-folder__toggle')
                if toggle.get_attribute('aria-expanded') != 'true':
                    toggle.click()
                row = page.locator(f'[data-map-folder="{folder}"]').first
                row.locator('.gw-folder__actions button').first.click()
            else:
                page.locator('[data-map-panel=create]').click()
            dialog = page.locator('.game-scene-create')
            expect(dialog).to_be_visible()
            return dialog

        ctx = context(); page = ctx.new_page(); open_game(page)
        baseline = db_snapshot()
        dialog = chooser(page)
        expect(dialog.locator('[data-map-create=builder]')).to_have_attribute('href', builder)
        assert dialog.evaluate('el=>el.contains(document.activeElement)')
        dialog.locator('header button').first.focus()
        page.keyboard.press('Shift+Tab'); expect(dialog.locator('[data-map-create=builder]')).to_be_focused()
        page.keyboard.press('Tab'); expect(dialog.locator('header button').first).to_be_focused()
        page.screenshot(path=str(output / 'new-scene-1440.png'))
        page.keyboard.press('Escape'); expect(dialog).to_have_count(0)
        expect(page.locator('[data-map-panel=create]')).to_be_focused()
        dialog = chooser(page, seed['folder'])
        expect(dialog.locator('[data-map-create=builder]')).to_have_attribute('href', builder + '?folder=' + seed['folder'])
        dialog.locator('[data-map-create=builder]').focus(); page.keyboard.press('Enter')
        page.wait_for_url(builder + '?folder=' + seed['folder'])
        expect(page.locator('[data-map-builder]')).to_be_visible()
        assert len(ctx.pages) == 1, 'Builder opened an extra browser tab'
        assert page.locator('#table-workspace,.game-board,.game-panel').count() == 0
        assert page.evaluate('builderSockets.length') == 0, 'Builder started a table websocket'
        assert page.evaluate('!window.gravewrightMaps && !window.gravewrightRealtime')
        expect(page.locator('[data-builder-generate]')).to_be_visible()
        expect(page.locator('[data-builder-generate]')).to_be_enabled()
        builder_sidebar(page, 'settings')
        expect(page.locator('.map-builder__folder strong')).to_have_text('Workshop maps')
        form = page.locator('[data-builder-form]')
        authored_name = 'Synthetic map — ' + 'long name ' * 10
        form.locator('[name=name]').fill(authored_name)
        form.locator('[name=name]').press('Tab')
        expect(page.locator('[data-builder-title]')).to_have_text(authored_name.strip())
        for name, value in [('columns', '12'), ('rows', '8'), ('cellSize', '64')]:
            form.locator(f'[name={name}]').fill(value)
            form.locator(f'[name={name}]').press('Tab')
        expect(page.locator('[data-builder-paper]')).to_have_attribute('width', '12')
        expect(page.locator('[data-builder-paper]')).to_have_attribute('height', '8')
        expect(page.locator('[data-builder-dimensions]')).to_have_text('12 × 8 · 768 × 512 px')
        form.locator('[name=background]').fill('#344955')
        form.locator('[name=background]').dispatch_event('change')
        expect(page.locator('[data-builder-paper]')).to_have_attribute('fill', '#344955')
        form.locator('[name=grid]').uncheck(); expect(page.locator('[data-builder-grid]')).to_be_hidden()
        form.locator('[name=grid]').check()
        form.locator('[name=columns]').fill('201')
        form.locator('[name=columns]').press('Tab')
        assert not form.locator('[name=columns]').evaluate('el=>el.checkValidity()')
        expect(page.locator('[data-builder-paper]')).to_have_attribute('width', '12')
        form.locator('[name=columns]').fill('12')
        form.locator('[name=columns]').press('Tab')
        viewport = page.locator('[data-builder-viewport]')
        canvas = page.locator('[data-builder-canvas]')
        fitted = canvas.get_attribute('viewBox')
        fitted_zoom = page.locator('[data-builder-zoom-level]').text_content()
        left, top, w, h = map(float, fitted.split())
        assert left <= 0 and top <= 0 and left + w >= 12 and top + h >= 8
        # The horizontal toolbar and footer remain outside the viewport; fit
        # keeps the complete paper centered in the available drawing area.
        assert abs(top + h / 2 - 4) < .001
        page.locator('[data-builder-zoom=in]').click()
        assert int(page.locator('[data-builder-zoom-level]').text_content().strip('%')) > int(fitted_zoom.strip('%'))
        assert canvas.get_attribute('viewBox') != fitted
        page.locator('[data-builder-fit]').click()
        expect(page.locator('[data-builder-zoom-level]')).to_have_text(fitted_zoom)
        assert canvas.get_attribute('viewBox') == fitted
        viewport.focus(); page.keyboard.press('ArrowRight')
        assert canvas.get_attribute('viewBox') != fitted
        page.keyboard.press('0'); assert canvas.get_attribute('viewBox') == fitted
        box = viewport.bounding_box()
        x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
        page.locator('[data-builder-tool=pan]').click()
        page.mouse.move(x, y); page.mouse.down(); page.mouse.move(x + 60, y + 30, steps=5); page.mouse.up()
        assert canvas.get_attribute('viewBox') != fitted
        assert not viewport.evaluate("el=>el.classList.contains('is-panning')")
        viewport.focus(); page.keyboard.press('Home')
        assert canvas.get_attribute('viewBox') == fitted
        page.locator('[data-builder-tool=select]').click()
        viewport.focus(); page.keyboard.down('Space')
        page.mouse.move(x, y); page.mouse.down(); page.mouse.move(x + 30, y + 15, steps=5); page.mouse.up()
        page.keyboard.up('Space')
        assert canvas.get_attribute('viewBox') != fitted
        assert not viewport.evaluate("el=>el.classList.contains('is-panning')")
        viewport.focus(); page.keyboard.press('Home')
        assert canvas.get_attribute('viewBox') == fitted
        page.mouse.move(x, y); page.mouse.wheel(0, -120)
        expect(page.locator('[data-builder-zoom-level]')).not_to_have_text(fitted_zoom)
        # Headless shell may decline native BFcache even when its disabling
        # launch flag is removed. Exercise the persisted lifecycle explicitly
        # as well, without claiming that a real browser cache hit occurred.
        # A valid focused field must be flushed before listeners are disposed.
        builder_sidebar(page, 'settings')
        form.locator('[name=name]').fill('Restored synthetic workspace')
        stopped_box = canvas.get_attribute('viewBox')
        page.evaluate("dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}))")
        page.locator('[data-builder-zoom=in]').click()
        assert canvas.get_attribute('viewBox') == stopped_box, 'Disposed camera retained its controls'
        page.evaluate("dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))")
        expect(page.locator('[data-builder-title]')).to_have_text('Restored synthetic workspace')
        restored_box = canvas.get_attribute('viewBox')
        page.locator('[data-builder-zoom=in]').click()
        assert canvas.get_attribute('viewBox') != restored_box, 'Persisted lifecycle did not remount the camera'
        records.append({'case': 'simulated-persisted-builder-lifecycle', 'controlsDisposedAndRestored': True})
        page.reload(); expect(page.locator('[data-map-builder]')).to_be_visible()
        expect(form.locator('[name=name]')).to_have_value('Restored synthetic workspace')
        expect(page.locator('[data-builder-title]')).to_have_text('Restored synthetic workspace')
        expect(page.locator('[data-builder-paper]')).to_have_attribute('width', '12')
        expect(page.locator('[data-builder-paper]')).to_have_attribute('height', '8')
        expect(page.locator('[data-builder-paper]')).to_have_attribute('fill', '#344955')
        assert db_snapshot() == baseline, 'Builder entry/reload changed map state'
        page.go_back(); back_game = returned_game(page)
        assert db_snapshot() == baseline, 'Browser back changed broadcast or private navigation'
        records.append({'case': 'same-tab-entry-reload-back', 'sceneStatePreserved': True, 'websockets': 0, **back_game})
        page.go_forward(); expect(page.locator('[data-map-builder]')).to_be_visible()
        restored_canvas = page.locator('[data-builder-canvas]')
        before_zoom = restored_canvas.get_attribute('viewBox')
        page.locator('[data-builder-zoom=in]').click()
        assert restored_canvas.get_attribute('viewBox') != before_zoom, 'History restoration left a disposed camera'
        page.locator('[data-builder-fit]').click()
        assert restored_canvas.get_attribute('viewBox') == before_zoom
        records.append({'case': 'browser-forward-camera-lifetime', 'pageShows': page.evaluate('builderPageShows')})
        page.go_back(); returned_game(page)
        page.goto(builder)
        page.locator('.map-builder__back').focus(); page.keyboard.press('Enter')
        returned_game(page)
        assert db_snapshot() == baseline, 'Explicit return changed map state'
        records.append({'case': 'configuration-preview-camera-keyboard-return', 'sceneStatePreserved': True})
        with page.expect_navigation(wait_until='load'):
            page.evaluate("""()=>{
              dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}));
              dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}));
            }""")
        restored_game = returned_game(page)
        assert db_snapshot() == baseline, 'Game history remount changed map state'
        records.append({'case': 'simulated-persisted-game-remount', **restored_game})
        ctx.close()

        for role, status in [('player', 404), ('streamer', 404), (None, 302)]:
            ctx = context(role); page = ctx.new_page()
            response = ctx.request.get(builder, max_redirects=0)
            assert response.status == status, (role, response.status)
            response = page.goto(builder)
            assert page.locator('[data-map-builder]').count() == 0
            if role:
                assert response.status == 404
            else:
                assert '/login' in page.url
            records.append({'case': 'permission', 'role': role or 'anonymous', 'status': status})
            ctx.close()

        for width, height in [(1440, 900), (390, 844), (320, 700)]:
            ctx = context(width=width, height=height); page = ctx.new_page(); page.goto(game)
            page.wait_for_function('!!window.gravewrightMaps?.current')
            dialog = chooser(page)
            chooser_metrics = dialog.evaluate(MEASURE)
            assert not chooser_metrics['tiny'] and not chooser_metrics['overflow'], (width, chooser_metrics)
            page.screenshot(path=str(output / f'new-scene-{width}.png'))
            page.keyboard.press('Escape'); expect(dialog).to_have_count(0)
            records.append({'case': 'chooser-layout-keyboard', 'width': width, **chooser_metrics})
            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, seed['campaign'])
                page.goto(builder + '?folder=' + seed['folder'])
                root = page.locator('[data-map-builder]'); expect(root).to_be_visible()
                assert page.locator('html').get_attribute('lang') == locale
                assert page.evaluate('builderSockets.length') == 0
                assert page.locator('#table-workspace,.game-board,.game-panel').count() == 0
                metrics = root.evaluate(MEASURE)
                assert not metrics['tiny'], (locale, width, metrics['tiny'])
                assert not metrics['overflow'] and metrics['scrollWidth'] <= width + 1, (locale, width, metrics)
                page.screenshot(path=str(output / f'builder-{locale}-{width}.png'), full_page=True)
                records.append({'case': 'layout', 'locale': locale, 'width': width, **metrics})
                expect(page.locator('[data-builder-region=workspace]')).to_be_visible()
                expect(page.locator('.map-builder__library')).to_be_hidden()
                settings = page.locator('[data-builder-sidebar-tab=settings]:visible').first
                settings.focus(); page.keyboard.press('Enter')
                expect(settings).to_have_attribute('aria-pressed', 'true')
                expect(page.locator('[data-builder-viewport]')).to_be_visible()
                expect(page.locator('[data-builder-form]')).to_be_visible()
                expect(page.locator('[data-builder-assets-panel]')).to_be_visible()
                expanded = root.evaluate(MEASURE)
                assert not expanded['tiny'] and not expanded['overflow'], (locale, width, expanded)
                page.screenshot(path=str(output / f'builder-{locale}-{width}-settings.png'), full_page=True)
                details = page.locator('[data-builder-settings]')
                details.locator('summary').focus(); page.keyboard.press('Enter')
                expect(page.locator('[data-builder-form]')).to_be_hidden()
                page.keyboard.press('Enter')
                expect(page.locator('[data-builder-form]')).to_be_visible()
                close = page.locator('[data-builder-close-panel]')
                close.focus(); page.keyboard.press('Enter')
                expect(page.locator('.map-builder__library')).to_be_hidden()
                library = page.locator('[data-builder-library-toggle]')
                canvas_height = page.locator('[data-builder-viewport]').bounding_box()['height']
                library.focus(); page.keyboard.press('Enter')
                expect(library).to_have_attribute('aria-expanded', 'false')
                expect(page.locator('#builder-library-content')).to_be_hidden()
                expect(page.locator('.map-builder__dock-toolbar')).to_be_visible()
                assert page.locator('[data-builder-viewport]').bounding_box()['height'] > canvas_height
                expect(page.locator('[data-builder-tool=wall]')).to_be_visible()
                page.keyboard.press('Enter')
                expect(library).to_have_attribute('aria-expanded', 'true')
                expect(page.locator('[data-builder-assets]')).to_be_visible()
                library_metrics = root.evaluate(MEASURE)
                assert not library_metrics['tiny'] and not library_metrics['overflow'], (locale, width, library_metrics)
                records.append({'case': 'dock-and-panel-keyboard', 'locale': locale, 'width': width,
                                'libraryStaysVisibleWithSettings': True, 'collapsedLibraryExpandsCanvas': True})
            ctx.close()

        # Preserve the existing upload workflow, including the selected folder,
        # using one tiny synthetic image only after all read-only checks pass.
        ctx = context(); page = ctx.new_page(); open_game(page)
        dialog = chooser(page, seed['folder'])
        dialog.locator('[data-map-create=upload]').click()
        upload = page.locator('form.directory-dialog')
        expect(upload).to_be_visible()
        assert upload.locator('[name=groupId]').input_value() == seed['folder']
        content = BytesIO(); Image.new('RGB', (256, 256), '#486559').save(content, 'PNG')
        upload.locator('input[type=file]').set_input_files({
            'name': 'Synthetic uploaded scene.png', 'mimeType': 'image/png', 'buffer': content.getvalue(),
        })
        upload.locator('[name=activate]').uncheck()
        with page.expect_response(lambda response: '/scene-upload' in response.url) as uploaded:
            upload.locator('[type=submit]').click()
        assert uploaded.value.ok, uploaded.value.status
        new_scene = uploaded.value.json()
        assert new_scene['groupId'] == seed['folder'], new_scene
        expect(upload).to_have_count(0)
        assert page.evaluate('gravewrightMaps.current.id') == new_scene['id']
        after = db_snapshot()
        assert after['gravewright_maps.Broadcast'] == baseline['gravewright_maps.Broadcast']
        records.append({'case': 'existing-upload', 'folderPreserved': True, 'broadcastPreserved': True})
        ctx.close()
        browser.close()
    assert not errors, errors
    real_failures = [request for request in failed_requests if request['error'] != 'net::ERR_ABORTED']
    assert not real_failures, real_failures
    return {'passed': True, 'cases': records, 'pageErrors': errors,
            'failedRequests': failed_requests}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--snapshot', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--fixture', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--port', type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve:
        serve(args.fixture, args.port); return
    if args.snapshot:
        snapshot(); return
    output = (args.output or ROOT / 'data/map-builder-flow' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError('Use a fresh, empty output directory.')
    output.mkdir(parents=True, exist_ok=True)
    fixture = output / 'fixture'; fixture.mkdir()
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0)); port = connection.getsockname()[1]
    fixture_environment(fixture, port)
    executable = sys._base_executable if os.name == 'nt' else sys.executable
    base_command = [executable, '-B', '-X', 'utf8', str(Path(__file__).resolve())]
    base = f'http://127.0.0.1:{port}'
    with (output / 'server.log').open('w', encoding='utf-8') as log:
        server = subprocess.Popen([*base_command, '--serve', '--fixture', str(fixture), '--port', str(port)],
                                  cwd=ROOT, env=os.environ.copy(), stdout=log, stderr=log)
        try:
            for _ in range(200):
                if server.poll() is not None:
                    raise RuntimeError(f'Fixture server exited; inspect {output / "server.log"}')
                try:
                    with urlopen(base, timeout=1): break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Fixture server did not become ready.')
            seed = json.loads((fixture / 'seed.json').read_text(encoding='utf-8'))

            def db_snapshot():
                return json.loads(subprocess.check_output([*base_command, '--snapshot'], cwd=ROOT, env=os.environ.copy(), text=True))

            report = check_browser(base, seed, output, args.browser_executable, db_snapshot)
            (output / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
            print(json.dumps({'passed': True, 'cases': len(report['cases']), 'report': str(output / 'report.json')}))
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill(); server.wait()
            (output / 'server-exit.json').write_text(json.dumps({'pid': server.pid, 'exitCode': server.returncode}), encoding='utf-8')


if __name__ == '__main__':
    main()
