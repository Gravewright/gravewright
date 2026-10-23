"""Check transparent, locally movable progress indicators with real clients.

All accounts, clock/clue records, artwork and browser storage belong to a new
installation-local fixture. The running operator application is never used.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
import traceback
from urllib.request import urlopen

from map_builder import ROOT, MEASURE, change_locale, fixture_environment, serve as serve_builder


CLOCK_NAME = 'Synthetic expedition progress at the northern observatory'
CLOCK_DESCRIPTION = 'Synthetic expedition description: interview the observatory keeper before the northern storm. ' * 12
EDITED_DESCRIPTION = 'Synthetic revised description: the expedition must inspect the eastern lens and return safely. ' * 24
CLUE_NAME = 'Synthetic staged discovery with a deliberately long authored title'
CLUE_SECRET = 'SYNTHETIC_HUD_SECRET: The keeper concealed the eastern lens.'
CLUE_CONTENT = 'Synthetic public finding: the eastern lens points to the river.'
PUBLIC_CLUE_CONTENT = 'Synthetic public finding: the old bridge remains intact.'


def serve(fixture, port):
    from django.core import management

    original = management.call_command

    def command(name, *args, **kwargs):
        if name == 'runserver':
            from django.conf import settings
            from django.test import Client
            from gravewright.accounts.models import User
            from gravewright.campaigns.models import Membership, Onboarding
            from gravewright.table.models import ProgressClock, ProgressClue

            seed_file = fixture / 'seed.json'
            seed = json.loads(seed_file.read_text(encoding='utf-8'))
            assistant = User.objects.create_user('assistant@progress-hud.test', 'synthetic-browser-pass', name='Synthetic assistant GM')
            membership = Membership.objects.create(campaign_id=seed['campaign'], user=assistant, role='gm')
            Onboarding.objects.create(membership=membership, dismissed=True)
            client = Client(); client.force_login(assistant)
            seed['sessions']['assistant'] = {'name': settings.SESSION_COOKIE_NAME,
                                            'value': client.cookies[settings.SESSION_COOKIE_NAME].value}
            seed['assistant'] = str(assistant.pk)
            shared = {'campaign_id': seed['campaign'], 'pinned': True, 'visibility': 'players'}
            editable = ProgressClock.objects.create(**shared, name=CLOCK_NAME,
                segments=6, value=2, color='#4a90e2', players_can_edit=True, description=CLOCK_DESCRIPTION)
            readonly = ProgressClock.objects.create(**shared, name='Synthetic GM-controlled clock',
                segments=4, value=1, color='#d29030', players_can_edit=False)
            staged = ProgressClue.objects.create(**shared, name=CLUE_NAME, segments=4, value=1,
                content=CLUE_CONTENT, gm_notes=CLUE_SECRET)
            discovered = ProgressClue.objects.create(**shared, name='Synthetic discovered clue', segments=3,
                value=3, content=PUBLIC_CLUE_CONTENT, gm_notes=CLUE_SECRET)
            seed.update(clock=str(editable.pk), readonlyClock=str(readonly.pk),
                        clue=str(staged.pk), discoveredClue=str(discovered.pk))
            seed_file.write_text(json.dumps(seed, indent=2), encoding='utf-8')
        return original(name, *args, **kwargs)

    management.call_command = command
    try:
        serve_builder(fixture, port)
    finally:
        management.call_command = original


def demote_assistant(fixture):
    """Change only the disposable account while its fresh HTTP read is pending."""
    import django
    django.setup()
    from gravewright.campaigns.models import Membership
    seed = json.loads((fixture / 'seed.json').read_text(encoding='utf-8'))
    assert Membership.objects.filter(campaign_id=seed['campaign'], user_id=seed['assistant'], role='gm').update(role='player') == 1


def persistent_state(fixture):
    database = (fixture / 'review.sqlite3').resolve()
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as connection:
        tables = ('gravewright_table_progressclock', 'gravewright_table_progressclue',
                  'gravewright_table_clockreceipt', 'gravewright_table_cluereceipt',
                  'gravewright_maps_broadcast', 'gravewright_maps_scenenavigation')
        return {name: sorted(connection.execute('SELECT * FROM "' + name + '"').fetchall(), key=repr)
                for name in tables}


def check_browser(base, seed, output, executable, fixture):
    from PIL import Image
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    records, errors, dialogs, failed, contexts = [], [], [], [], []
    pages, requests, frames = {}, {}, {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))

        def observe(page, name):
            pages[name], requests[name], frames[name] = page, [], []
            page.on('pageerror', lambda error: errors.append({'client': name, 'message': error.stack or str(error)}))
            page.on('requestfailed', lambda request: failed.append({'client': name, 'url': request.url, 'error': request.failure}))
            page.on('request', lambda request: requests[name].append({'method': request.method, 'url': request.url,
                                                                      'body': request.post_data}))
            page.on('websocket', lambda stream: stream.on('framesent', lambda data: frames[name].append(data)))
            page.on('dialog', lambda dialog: (dialogs.append({'client': name, 'message': dialog.message}), dialog.dismiss()))

        def ready(page):
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            expect(page.locator('[data-clock-hud] [data-clock-id]').first).to_be_visible()

        def client(name, role):
            context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 1000})
            contexts.append(context)
            context.add_cookies([{**seed['sessions'][role], 'url': base}])
            page = context.new_page()
            observe(page, name)
            response = page.goto(f'/game/{campaign}')
            assert response.ok, (name, response.status)
            ready(page)
            return page

        def card(page, kind, identifier):
            return page.locator(f'[data-{kind}-hud] [data-{kind}-id="{identifier}"]')

        def face(page, kind, identifier):
            return card(page, kind, identifier).locator('[data-clock-face]' if kind == 'clock' else '[data-clue-progress]')

        def progress(page, kind, identifier, value, segments):
            indicator = face(page, kind, identifier)
            if kind == 'clock':
                expect(indicator.locator('.clocks__number')).to_have_text(str(value))
                expect(indicator).to_have_attribute('aria-label', f'{row(page, kind, identifier)["name"]}: {value}/{segments}')
            else:
                expect(indicator).to_have_attribute('aria-valuenow', str(value))
                expect(indicator).to_have_attribute('aria-valuemax', str(segments))

        def heading(page, kind, identifier):
            return card(page, kind, identifier).locator(f'[data-{kind}-name]')

        def details(page, kind, identifier, *, key=None):
            trigger = heading(page, kind, identifier)
            if key:
                trigger.focus(); page.keyboard.press(key)
            else:
                trigger.dblclick()
            modal = page.locator(f'.progress-details[data-{kind}-view="{identifier}"]')
            expect(modal).to_be_visible()
            expect(modal.locator('input,textarea,select,[type=submit]')).to_have_count(0)
            expect(modal).not_to_contain_text(CLUE_SECRET)
            return modal

        def close_details(modal):
            modal.locator('header button').click()
            expect(modal).to_have_count(0)

        def mutate(page, kind, method, identifier, **fields):
            current = row(page, kind, identifier)
            return page.evaluate('''async ([campaign,kind,method,payload])=>gravewright.forTable(campaign)[kind+'s'][method](payload)''',
                [campaign, kind, method, {'id': identifier, 'version': current['version'], **fields}])

        def state(page, kind):
            return page.evaluate('''async ([campaign,kind])=>gravewright.forTable(campaign)[kind].state({
              sceneId:gravewrightMaps.current.id})''', [campaign, kind + 's'])

        def row(page, kind, identifier):
            return next(row for row in state(page, kind)[kind + 's'] if row['id'] == identifier)

        def bounds(page, kind, identifier):
            target = card(page, kind, identifier)
            expect(target).to_be_visible()
            # Realtime can replace the card between reading its progress and
            # this measurement; query and read geometry in one browser task.
            box = target.evaluate('''el=>{const r=el.getBoundingClientRect();
              return {x:r.x,y:r.y,width:r.width,height:r.height}}''')
            assert box['width'] and box['height'], (kind, identifier, box)
            return {key: round(value, 2) for key, value in box.items()}

        def near(actual, expected, tolerance=2):
            assert abs(actual['x'] - expected['x']) <= tolerance and abs(actual['y'] - expected['y']) <= tolerance, (actual, expected)

        def disjoint_cards(page):
            boxes = [(kind, identifier, bounds(page, kind, identifier)) for kind, identifier in (
                ('clock', seed['clock']), ('clock', seed['readonlyClock']),
                ('clue', seed['clue']), ('clue', seed['discoveredClue']))]
            for index, (kind, identifier, left) in enumerate(boxes):
                for other_kind, other_id, right in boxes[index + 1:]:
                    overlap_x = min(left['x'] + left['width'], right['x'] + right['width']) - max(left['x'], right['x'])
                    overlap_y = min(left['y'] + left['height'], right['y'] + right['height']) - max(left['y'], right['y'])
                    assert overlap_x <= 1 or overlap_y <= 1, ((kind, identifier, left), (other_kind, other_id, right))
            return boxes

        def move(page, kind, identifier, dx, dy):
            handle = card(page, kind, identifier).locator('[data-progress-move-handle]')
            expect(handle).to_be_visible()
            box = handle.bounding_box()
            start = (box['x'] + box['width'] / 2, box['y'] + min(box['height'] / 2, 16))
            page.mouse.move(*start)
            page.mouse.down()
            page.mouse.move(start[0] + dx, start[1] + dy, steps=10)
            page.mouse.up()
            return bounds(page, kind, identifier)

        def checkpoint(page, *, camera=True):
            return {'database': persistent_state(fixture),
                    'camera': page.evaluate('gravewrightMaps.board.viewport()') if camera else None}

        def only_local(before, name, request_mark, frame_mark):
            assert persistent_state(fixture) == before['database'], 'Moving an indicator changed campaign data.'
            if before['camera'] is not None:
                assert pages[name].evaluate('gravewrightMaps.board.viewport()') == before['camera'], 'Moving an indicator moved the board.'
            writes = [request for request in requests[name][request_mark:] if request['method'] not in ('GET', 'HEAD', 'OPTIONS')]
            assert not writes, writes
            mutations = []
            for frame in frames[name][frame_mark:]:
                try:
                    message = json.loads(frame)
                except (TypeError, ValueError):
                    mutations.append(frame)
                    continue
                if message.get('type') == 'scene.viewport':
                    # Tile visibility reports are read-only and can finish
                    # after initial board rendering during a local gesture.
                    payload = message.get('payload', {})
                    assert payload.get('camera_speed', 0) == 0 and payload.get('interaction_count', 0) == 0, message
                    continue
                if message.get('type') not in ('ping', 'pong', 'heartbeat'):
                    mutations.append(message)
            assert not mutations, mutations

        def local_layout(page):
            return page.evaluate('''()=>Object.fromEntries(Object.entries(localStorage)
              .filter(([key])=>key.startsWith('gravewright.progress-hud.v1.')))''')

        try:
            gm, other, player, streamer = (client(name, role) for name, role in (
                ('gm', 'gm'), ('other', 'gm'), ('player', 'player'), ('streamer', 'streamer')))
            clock, clue = seed['clock'], seed['clue']
            progress(gm, 'clock', clock, 2, 6)
            progress(gm, 'clue', clue, 1, 4)
            transparent = gm.evaluate('''()=>({
              cards:[...document.querySelectorAll('[data-clock-hud] article,[data-clue-hud] article')].map(el=>{
                const css=getComputedStyle(el);return {background:css.backgroundColor,shadow:css.boxShadow};}),
              sectors:[...document.querySelectorAll('[data-clock-hud] .clocks__sector:not(.clocks__sector--filled)')]
                .map(el=>getComputedStyle(el).fill),
              steps:[...document.querySelectorAll('[data-clue-hud] .clues__step:not(.clues__step--filled)')]
                .map(el=>getComputedStyle(el).backgroundColor)
            })''')
            assert len(transparent['cards']) == 4 and transparent['sectors'] and transparent['steps'], transparent
            assert all(row['background'] == 'rgba(0, 0, 0, 0)' and row['shadow'] == 'none' for row in transparent['cards']), transparent
            assert all(fill in ('none', 'rgba(0, 0, 0, 0)') for fill in transparent['sectors']), transparent
            assert all(fill == 'rgba(0, 0, 0, 0)' for fill in transparent['steps']), transparent
            for kind, identifier in (('clock', clock), ('clock', seed['readonlyClock']), ('clue', clue), ('clue', seed['discoveredClue'])):
                target = card(gm, kind, identifier)
                assert target.evaluate('el=>el.children.length') == 2
                expect(target.locator('button,output,[data-clock-action],[data-clue-action],small,p')).to_have_count(0)
            bar = face(gm, 'clue', clue)
            assert abs(bar.bounding_box()['height'] - 24) < 1
            geometry = face(gm, 'clock', clock).evaluate('''el=>{
              const r=el.getBoundingClientRect(),path=el.querySelector('path').getBBox();
              return {width:r.width,height:r.height,outer:r.width*110/128,sectorWidth:path.width};}''')
            assert 62 <= geometry['outer'] <= 70 and abs(geometry['width'] - geometry['height']) < 1, geometry
            # Filled annular sectors remain distinct from the transparent hole
            # and empty sectors in the actual rendered browser pixels.
            ring = face(gm, 'clock', clock).bounding_box()
            with Image.open(BytesIO(gm.screenshot())) as screenshot:
                pixels = screenshot.convert('RGB')
                def pixel(x, y):
                    return pixels.getpixel((round(ring['x'] + x * ring['width'] / 128), round(ring['y'] + y * ring['height'] / 128)))
                blue, hole, empty, outside = pixel(107, 64), pixel(50, 50), pixel(21, 64), pixel(1, 1)
                assert blue[2] > blue[0] + 70 and blue[1] > blue[0] + 25, (blue, hole, empty, outside)
                assert hole == empty == outside, (blue, hole, empty, outside)
            gm.screenshot(path=str(output / 'transparent-hud-1440.png'), full_page=True)
            records.append({'case': 'minimal-hud-has-only-names-and-transparent-24px-clue-bar-or-66px-segmented-donut',
                            'styles': transparent, 'clockGeometry': geometry})

            # GMs configure through the name; other roles receive a small
            # readonly description modal through the same native gesture.
            before_layout = local_layout(gm)
            heading(gm, 'clock', clock).dblclick()
            clock_editor = gm.locator('[data-clock-editor]')
            expect(clock_editor).to_be_visible()
            expect(clock_editor.locator('[name=description]')).to_have_value(CLOCK_DESCRIPTION)
            clock_editor.locator('[name=description]').fill(EDITED_DESCRIPTION)
            clock_editor.locator('[type=submit]').click(); expect(clock_editor).to_have_count(0)
            assert row(gm, 'clock', clock)['description'] == EDITED_DESCRIPTION
            assert local_layout(gm) == before_layout
            heading(gm, 'clue', clue).dblclick()
            clue_editor = gm.locator('[data-clue-editor]')
            expect(clue_editor).to_be_visible()
            expect(clue_editor.locator('[name=content]')).to_have_value(CLUE_CONTENT)
            clue_editor.locator('[data-cancel]').click(); expect(clue_editor).to_have_count(0)
            records.append({'case': 'native-double-click-name-opens-gm-editors-and-saves-authored-clock-description-without-moving-or-advancing'})

            readonly_before = persistent_state(fixture)
            for target in (player, streamer):
                description = details(target, 'clock', clock)
                expect(description.locator('[data-progress-description]')).to_have_text(EDITED_DESCRIPTION)
                expect(description.locator('[data-progress-details-title]')).to_have_text(CLOCK_NAME)
                close_details(description)
                description = details(target, 'clue', seed['discoveredClue'])
                expect(description.locator('[data-progress-description]')).to_have_text(PUBLIC_CLUE_CONTENT)
                close_details(description)
                description = details(target, 'clock', seed['readonlyClock'], key='Enter')
                expect(description.locator('[data-progress-description]')).to_have_text('No description provided.')
                close_details(description)
                description = details(target, 'clock', clock, key='Space')
                expect(description.locator('[data-progress-description]')).to_have_text(EDITED_DESCRIPTION)
                close_details(description)
            assert persistent_state(fixture) == readonly_before
            records.append({'case': 'player-and-streamer-double-click-enter-and-space-open-readonly-fresh-details-with-empty-state-and-no-gm-notes'})

            live = details(player, 'clock', clock)
            mutate(gm, 'clock', 'update', clock, description='Synthetic description updated while the modal remains open.')
            expect(live.locator('[data-progress-description]')).to_have_text('Synthetic description updated while the modal remains open.')
            mutate(gm, 'clock', 'update', clock, visibility='gm')
            expect(live).to_have_count(0)
            expect(card(player, 'clock', clock)).to_have_count(0)
            mutate(gm, 'clock', 'update', clock, visibility='players', description=EDITED_DESCRIPTION)
            expect(heading(player, 'clock', clock)).to_be_visible()
            live = details(streamer, 'clue', seed['discoveredClue'])
            mutate(gm, 'clue', 'advance', seed['discoveredClue'], delta=-1)
            expect(live).to_have_count(0)
            expect(card(streamer, 'clue', seed['discoveredClue'])).to_have_count(0)
            mutate(gm, 'clue', 'advance', seed['discoveredClue'], delta=1)
            expect(heading(streamer, 'clue', seed['discoveredClue'])).to_be_visible()
            records.append({'case': 'open-details-refresh-live-and-close-when-clock-or-discovered-clue-access-is-revoked'})

            held = {}
            route_pattern = '**/modules-native/clocks*'
            def delay_state(route):
                if held:
                    route.continue_(); return
                response = route.fetch()
                held.update(route=route, response=response)
            player.route(route_pattern, delay_state)
            try:
                with player.expect_request(lambda request: '/modules-native/clocks' in request.url):
                    heading(player, 'clock', clock).dblclick()
                deadline = time.monotonic() + 5
                while not held and time.monotonic() < deadline:
                    player.wait_for_timeout(20)
                assert held
                mutate(gm, 'clock', 'update', clock, visibility='gm')
                expect(card(player, 'clock', clock)).to_have_count(0)
                held['route'].fulfill(response=held['response'])
                player.wait_for_timeout(150)
                expect(player.locator(f'[data-clock-view="{clock}"]')).to_have_count(0)
                expect(card(player, 'clock', clock)).to_have_count(0)
            finally:
                player.unroute(route_pattern, delay_state)
            mutate(gm, 'clock', 'update', clock, visibility='players')
            expect(heading(player, 'clock', clock)).to_be_visible()
            records.append({'case': 'late-fresh-state-response-cannot-reopen-clock-details-after-live-access-revocation'})

            private_clock = gm.evaluate('''campaign=>gravewright.forTable(campaign).clocks.create({
              name:'SYNTHETIC_PENDING_PRIVATE_CLOCK',description:'Synthetic private pending description.',
              segments:4,value:0,color:'#c9a44c',visibility:'gm',playersCanEdit:false,pinned:true})''', campaign)
            private_id = private_clock['id']
            assistant = client('assistant', 'assistant')
            held_role = {}
            def delay_role_read(route):
                if held_role:
                    route.continue_(); return
                held_role['route'] = route
            assistant.route(route_pattern, delay_role_read)
            try:
                with assistant.expect_request(lambda request: '/modules-native/clocks' in request.url):
                    heading(assistant, 'clock', private_id).dblclick()
                deadline = time.monotonic() + 5
                while not held_role and time.monotonic() < deadline:
                    assistant.wait_for_timeout(20)
                assert held_role
                executable = sys._base_executable if os.name == 'nt' else sys.executable
                subprocess.check_call([executable, '-B', '-X', 'utf8', str(Path(__file__).resolve()),
                                       '--demote-assistant', '--fixture', str(fixture)], cwd=ROOT, env=os.environ.copy())
                with assistant.expect_response(lambda response: '/modules-native/clocks' in response.url) as fresh_role:
                    held_role['route'].continue_()
                assert fresh_role.value.ok
                # The table can navigate away immediately after demotion, so
                # its old response body is no longer retained by Chromium.
                projection = assistant.request.get(fresh_role.value.url)
                assert projection.ok and projection.json()['is_gm'] is False
                assert private_id not in {value['id'] for value in projection.json()['clocks']}
                assistant.wait_for_timeout(150)
                expect(assistant.locator('[data-clock-editor],.progress-details')).to_have_count(0)
            finally:
                assistant.unroute(route_pattern, delay_role_read)
            mutate(gm, 'clock', 'delete', private_id)
            assistant.context.close()
            records.append({'case': 'pending-name-activation-cannot-open-private-gm-edit-after-membership-demotion'})

            for kind, identifier, initial, maximum in (('clock', clock, 2, 6), ('clue', clue, 1, 4)):
                version = row(gm, kind, identifier)['version']
                face(gm, kind, identifier).click()
                progress(gm, kind, identifier, initial + 1, maximum)
                assert row(gm, kind, identifier)['version'] == version + 1
                face(gm, kind, identifier).click(button='right')
                progress(gm, kind, identifier, initial, maximum)
                assert row(gm, kind, identifier)['version'] == version + 2
                expect(gm.locator('.directory-context-menu:visible')).to_have_count(0)
                records.append({'case': f'{kind}-face-left-click-adds-one-right-click-removes-one-without-context-menu'})
                face(gm, kind, identifier).focus()
                gm.keyboard.press('ArrowRight')
                progress(gm, kind, identifier, initial + 1, maximum)
                expect(face(gm, kind, identifier)).to_be_focused()
                gm.keyboard.press('ArrowLeft')
                progress(gm, kind, identifier, initial, maximum)
                expect(face(gm, kind, identifier)).to_be_focused()
                assert row(gm, kind, identifier)['version'] == version + 4
                records.append({'case': f'{kind}-progress-keyboard-retains-focus-across-canonical-refreshes'})

            # Player-editable clocks retain their existing permission; clues
            # remain controlled by the GM even once their content is public.
            progress(player, 'clock', clock, 2, 6)
            face(player, 'clock', clock).click()
            progress(player, 'clock', clock, 3, 6)
            progress(gm, 'clock', clock, 3, 6)
            face(player, 'clock', clock).click(button='right')
            progress(player, 'clock', clock, 2, 6)
            readonly_before = persistent_state(fixture)
            write_marks = {name: len(requests[name]) for name in ('player', 'streamer')}
            for target in (player, streamer):
                for kind, identifier in (('clock', seed['readonlyClock']), ('clue', seed['discoveredClue'])):
                    face(target, kind, identifier).click()
                    face(target, kind, identifier).click(button='right')
            face(streamer, 'clock', clock).click()
            face(streamer, 'clock', clock).click(button='right')
            gm.wait_for_timeout(150)
            assert persistent_state(fixture) == readonly_before
            for name, mark in write_marks.items():
                assert not [request for request in requests[name][mark:] if request['method'] == 'POST'], requests[name][mark:]
            assert clue not in {entry['id'] for entry in state(player, 'clue')['clues']}
            assert CLUE_SECRET not in player.content() and CLUE_SECRET not in json.dumps(state(player, 'clue'))
            records.append({'case': 'editable-player-clock-works-readonly-player-streamer-and-clue-permissions-remain-enforced'})

            before, request_mark, frame_mark = checkpoint(streamer), len(requests['streamer']), len(frames['streamer'])
            streamer_origin = bounds(streamer, 'clue', seed['discoveredClue'])
            streamer_moved = move(streamer, 'clue', seed['discoveredClue'], 350, 220)
            assert abs(streamer_moved['x'] - streamer_origin['x']) > 100
            only_local(before, 'streamer', request_mark, frame_mark)
            records.append({'case': 'readonly-streamer-can-move-a-visible-clue-without-changing-progress-or-campaign-state'})

            origin_clock, origin_clue = bounds(gm, 'clock', clock), bounds(gm, 'clue', clue)
            other_clock = bounds(other, 'clock', clock)
            before, request_mark, frame_mark = checkpoint(gm), len(requests['gm']), len(frames['gm'])
            moved_clock = move(gm, 'clock', clock, -400, 260)
            assert abs(moved_clock['x'] - origin_clock['x']) > 100
            near(bounds(gm, 'clue', clue), origin_clue)
            moved_clue = move(gm, 'clue', clue, 350, 280)
            assert abs(moved_clue['x'] - origin_clue['x']) > 100
            near(bounds(gm, 'clock', clock), moved_clock)
            near(bounds(other, 'clock', clock), other_clock)
            expect(gm.locator('[data-clock-editor],[data-clue-editor],.progress-details')).to_have_count(0)
            only_local(before, 'gm', request_mark, frame_mark)
            gm.screenshot(path=str(output / 'independently-moved-hud-1440.png'), full_page=True)
            records.append({'case': 'clock-and-clue-move-independently-without-api-socket-progress-or-scene-changes',
                            'clock': moved_clock, 'clue': moved_clue})

            before, request_mark, frame_mark = checkpoint(gm), len(requests['gm']), len(frames['gm'])
            handle = card(gm, 'clock', clock).locator('[data-progress-move-handle]')
            handle.focus()
            handle.press('Shift+ArrowRight')
            keyboard_clock = bounds(gm, 'clock', clock)
            near(keyboard_clock, {**moved_clock, 'x': moved_clock['x'] + 10})
            moved_clock = keyboard_clock
            saved_layout = local_layout(gm)
            gm.evaluate('''document.addEventListener('pointerdown',event=>window.__hudPointer=event.pointerId,{once:true,capture:true})''')
            box = handle.bounding_box()
            start = (box['x'] + box['width'] / 2, box['y'] + 8)
            gm.mouse.move(*start)
            gm.mouse.down()
            gm.mouse.move(start[0] - 60, start[1] + 50, steps=5)
            handle.press('Escape')
            gm.mouse.up()
            near(bounds(gm, 'clock', clock), moved_clock)
            assert local_layout(gm) == saved_layout
            gm.mouse.move(*start)
            gm.mouse.down()
            gm.mouse.move(start[0] - 40, start[1] + 40, steps=5)
            handle.evaluate("el=>el.dispatchEvent(new PointerEvent('pointercancel',{pointerId:window.__hudPointer,pointerType:'mouse',bubbles:true}))")
            gm.mouse.up()
            near(bounds(gm, 'clock', clock), moved_clock)
            assert local_layout(gm) == saved_layout
            only_local(before, 'gm', request_mark, frame_mark)
            records.append({'case': 'keyboard-movement-is-local-escape-and-pointercancel-restore-position-without-saving'})

            # A normal feed render must retain the user's local placement.
            face(gm, 'clock', clock).click()
            progress(gm, 'clock', clock, 3, 6)
            near(bounds(gm, 'clock', clock), moved_clock)
            near(bounds(gm, 'clue', clue), moved_clue)
            face(gm, 'clock', clock).click(button='right')
            progress(gm, 'clock', clock, 2, 6)
            gm.reload()
            ready(gm)
            near(bounds(gm, 'clock', clock), moved_clock)
            near(bounds(gm, 'clue', clue), moved_clue)
            near(bounds(other, 'clock', clock), other_clock)
            records.append({'case': 'local-placement-survives-live-rerender-and-reload-and-other-browser-remains-independent'})

            # Same browser storage, different authenticated profile.
            saved_storage = local_layout(gm)
            gm.context.clear_cookies()
            gm.context.add_cookies([{**seed['sessions']['player'], 'url': base}])
            gm.goto(f'/game/{campaign}')
            ready(gm)
            near(bounds(gm, 'clock', clock), bounds(player, 'clock', clock))
            current_storage = local_layout(gm)
            assert all(current_storage.get(key) == value for key, value in saved_storage.items())
            moved_player = move(gm, 'clock', clock, -180, 160)
            assert abs(moved_player['x'] - moved_clock['x']) > 20
            gm.context.clear_cookies()
            gm.context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
            gm.goto(f'/game/{campaign}')
            ready(gm)
            near(bounds(gm, 'clock', clock), moved_clock)
            records.append({'case': 'same-browser-local-layout-is-scoped-to-the-authenticated-profile'})

            manager = gm.context.new_page()
            observe(manager, 'manager')
            for kind, identifier, initial, maximum in (('clock', clock, 2, 6), ('clue', clue, 1, 4)):
                manager.goto(f'/campaigns/{campaign}/manage?section={kind}s')
                expect(manager.locator('[data-manager-ready=true]')).to_be_attached(timeout=30000)
                panel = manager.locator(f'[data-manager-view={kind}s] [data-{kind}-id="{identifier}"]')
                indicator = panel.locator('[data-clock-face]' if kind == 'clock' else '[data-clue-progress]')
                indicator.click()
                expect(panel.locator(f'[data-{kind}-value]')).to_have_text(f'{initial + 1}/{maximum}')
                indicator.click(button='right')
                expect(panel.locator(f'[data-{kind}-value]')).to_have_text(f'{initial}/{maximum}')
                records.append({'case': f'campaign-manager-{kind}-uses-the-same-left-and-right-progress-gestures'})
            manager.close()

            before, request_mark, frame_mark = checkpoint(gm, camera=False), len(requests['gm']), len(frames['gm'])
            gm.set_viewport_size({'width': 320, 'height': 740})
            gm.wait_for_function('''()=>[...document.querySelectorAll('[data-clock-hud] article,[data-clue-hud] article')]
              .every(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=320&&r.top>=0&&r.bottom<=740})''')
            compact_defaults = disjoint_cards(gm)
            dock = gm.locator('.game-dock').bounding_box()
            assert dock
            for kind, identifier, box in compact_defaults:
                if kind == 'clock':
                    assert box['y'] + box['height'] <= dock['y'] - 7, (identifier, box, dock)
            only_local(before, 'gm', request_mark, frame_mark)
            records.append({'case': 'resizing-the-live-table-uses-nonoverlapping-compact-layout-without-navigation-or-network-writes',
                            'compactDefaults': compact_defaults})

            compact_clock = move(gm, 'clock', clock, -8, 0)
            assert any(key.endswith('.compact') for key in local_layout(gm)), local_layout(gm)
            gm.reload()
            ready(gm)
            near(bounds(gm, 'clock', clock), compact_clock)
            gm.set_viewport_size({'width': 1440, 'height': 1000})
            gm.wait_for_function('''([id,x])=>{
              const el=document.querySelector('[data-clock-hud] [data-clock-id="'+id+'"]');
              return el&&Math.abs(el.getBoundingClientRect().x-x)<2}''', arg=[clock, moved_clock['x']])
            near(bounds(gm, 'clock', clock), moved_clock)
            near(bounds(gm, 'clue', clue), moved_clue)
            gm.set_viewport_size({'width': 320, 'height': 740})
            gm.wait_for_function('''([id,x])=>{
              const el=document.querySelector('[data-clock-hud] [data-clock-id="'+id+'"]');
              return el&&Math.abs(el.getBoundingClientRect().x-x)<2}''', arg=[clock, compact_clock['x']])
            near(bounds(gm, 'clock', clock), compact_clock)
            disjoint_cards(gm)
            records.append({'case': 'compact-layout-persists-separately-and-resizing-restores-the-desktop-layout'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(gm, locale, campaign)
                gm.set_viewport_size({'width': 320, 'height': 740})
                gm.goto(f'/game/{campaign}')
                ready(gm)
                expect(gm.locator('[data-mindmaps-open] > span')).to_be_hidden()
                for kind, identifier in (('clock', clock), ('clock', seed['readonlyClock']),
                                         ('clue', clue), ('clue', seed['discoveredClue'])):
                    box = bounds(gm, kind, identifier)
                    assert box['x'] >= -1 and box['x'] + box['width'] <= 321, box
                    assert box['y'] >= -1 and box['y'] + box['height'] <= 741, box
                for selector in ('[data-clock-hud]', '[data-clue-hud]'):
                    dimensions = gm.locator(selector).evaluate(MEASURE)
                    assert not dimensions['tiny'] and not dimensions['overflow'], dimensions
                gm.screenshot(path=str(output / f'transparent-hud-{locale}-320.png'), full_page=True)
                heading(gm, 'clock', clock).dblclick()
                configured = gm.locator('[data-clock-editor]')
                expect(configured).to_be_visible()
                expect(configured.locator('[name=description]')).to_have_value(EDITED_DESCRIPTION)
                dimensions = configured.evaluate(MEASURE)
                assert not dimensions['tiny'] and not dimensions['overflow'], (locale, dimensions)
                configured.locator('[data-cancel]').click(); expect(configured).to_have_count(0)
                change_locale(player, locale, campaign)
                player.set_viewport_size({'width': 320, 'height': 740})
                player.goto(f'/game/{campaign}'); ready(player)
                description = details(player, 'clock', clock)
                expect(description.locator('[data-progress-description]')).to_have_text(EDITED_DESCRIPTION)
                dimensions = description.evaluate(MEASURE)
                assert not dimensions['tiny'] and not dimensions['overflow'], (locale, dimensions)
                player.screenshot(path=str(output / f'clock-details-{locale}-320.png'), full_page=True)
                close_details(description)
                description = details(player, 'clue', seed['discoveredClue'])
                expect(description.locator('[data-progress-description]')).to_have_text(PUBLIC_CLUE_CONTENT)
                player.screenshot(path=str(output / f'clue-details-{locale}-320.png'), full_page=True)
                close_details(description)
                records.append({'case': f'{locale}-320px-local-positions-clamp-without-overflow-or-small-text'})

            assert not errors, errors
            assert not dialogs, dialogs
            assert not [request for request in failed if request['error'] != 'net::ERR_ABORTED'], failed
        except Exception:
            (output / 'browser-diagnostics.json').write_text(json.dumps({'completedCases': records,
                'pageErrors': errors, 'nativeDialogs': dialogs, 'failedRequests': failed}, indent=2), encoding='utf-8')
            for name, page in pages.items():
                if not page.is_closed():
                    page.screenshot(path=str(output / f'failure-{name}.png'), full_page=True)
            raise
        finally:
            for context in contexts:
                context.close()
            browser.close()
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'failedRequests': failed, 'assets': 'Synthetic artwork and authored clock/clue records only.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--demote-assistant', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--fixture', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--port', type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve:
        serve(args.fixture, args.port)
        return
    if args.demote_assistant:
        demote_assistant(args.fixture)
        return
    output = (args.output or ROOT / 'data/progress-hud' /
              datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError('Use a fresh, empty output directory.')
    output.mkdir(parents=True, exist_ok=True)
    fixture = output / 'fixture'
    fixture.mkdir()
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0))
        port = connection.getsockname()[1]
    fixture_environment(fixture, port)
    executable = sys._base_executable if os.name == 'nt' else sys.executable
    command = [executable, '-B', '-X', 'utf8', str(Path(__file__).resolve())]
    base = f'http://127.0.0.1:{port}'
    with (output / 'server.log').open('w', encoding='utf-8') as log:
        server = subprocess.Popen([*command, '--serve', '--fixture', str(fixture), '--port', str(port)],
                                  cwd=ROOT, env=os.environ.copy(), stdout=log, stderr=log)
        try:
            for _ in range(300):
                if server.poll() is not None:
                    raise RuntimeError(f"Fixture exited; inspect {output / 'server.log'}")
                try:
                    with urlopen(base, timeout=1):
                        break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Fixture did not become ready.')
            seed = json.loads((fixture / 'seed.json').read_text(encoding='utf-8'))
            report = check_browser(base, seed, output, args.browser_executable, fixture)
            (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(json.dumps({'passed': True, 'cases': len(report['cases']), 'report': str(output / 'report.json')}))
        except Exception:
            (output / 'failure.txt').write_text(traceback.format_exc(), encoding='utf-8')
            raise
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
            (output / 'server-exit.json').write_text(json.dumps({'pid': server.pid, 'exitCode': server.returncode}), encoding='utf-8')


if __name__ == '__main__':
    main()
