"""Measurements and drawings made by any participant reach the other connected clients.

Four players (A-D), a GM and a streamer share one scene. Player A's area
measurement and drawings reach B, C, D, the GM and the streamer; GM-layer work
stays with GMs. Players edit only their own drawings, concurrent drawings are all
kept, undo affects only the author's own rows, and GMs can edit every drawing.
"""
import json
import os
import subprocess
import sys
import time

import map_builder as harness

PLAYERS = ('a', 'b', 'c', 'd')

ADD_PLAYERS = '''
import json, os, secrets
from django.conf import settings
from django.test import Client
from django.utils import timezone
from gravewright.accounts.models import User
from gravewright.campaigns.models import Campaign, Membership, Onboarding
campaign = Campaign.objects.get(pk=os.environ['SHARED_DRAWINGS_CAMPAIGN'])
sessions = {}
for name in ('b', 'c', 'd'):
    user = User.objects.create_user(f'player-{name}@map-builder.test', secrets.token_urlsafe(20),
                                    name='Player ' + name.upper(), role='participant')
    member = Membership.objects.create(campaign=campaign, user=user, role='player')
    Onboarding.objects.create(membership=member, dismissed=True, player_shown_at=timezone.now())
    client = Client(); client.force_login(user)
    sessions[name] = {'name': settings.SESSION_COOKIE_NAME, 'value': client.cookies[settings.SESSION_COOKIE_NAME].value}
print('SESSIONS=' + json.dumps(sessions))
'''


def add_players(campaign):
    """Create players B-D in the running fixture's database; A is the harness player."""
    output = subprocess.check_output(
        [sys.executable, '-B', '-X', 'utf8', 'manage.py', 'shell', '-c', ADD_PLAYERS],
        cwd=harness.ROOT, env={**os.environ, 'SHARED_DRAWINGS_CAMPAIGN': campaign}, text=True)
    line = next(value for value in output.splitlines() if value.startswith('SESSIONS='))
    return json.loads(line.removeprefix('SESSIONS='))


def check_browser(base, seed, output, executable, db_snapshot):
    from playwright.sync_api import expect, sync_playwright
    sessions = {**add_players(seed['campaign']), 'a': seed['sessions']['player'],
                'gm': seed['sessions']['gm'], 'streamer': seed['sessions']['streamer']}
    errors, timings = [], []
    scene = seed['broadcastScene']
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        pages, contexts = {}, []
        try:
            for role in ('gm', *PLAYERS, 'streamer'):
                context = browser.new_context(viewport={'width': 1440, 'height': 1000})
                contexts.append(context)
                context.add_cookies([{**sessions[role], 'url': base}])
                context.add_init_script('''window.receivedFrames=[];
                    const Native=WebSocket;window.WebSocket=class extends Native {
                    constructor(...args){super(...args);this.addEventListener('message',event=>window.receivedFrames.push(event.data));}};''')
                page = pages[role] = context.new_page()
                page.on('pageerror', lambda error, role=role: errors.append(f'{role}: {error}'))
                page.goto(f"{base}/game/{seed['campaign']}")
                page.wait_for_function('!!window.gravewrightMaps?.board?.viewport()')
            gm, streamer = pages['gm'], pages['streamer']
            a, b, c, d = (pages[name] for name in PLAYERS)
            everyone = [gm, a, b, c, d, streamer]
            gm.evaluate('(mapId)=>gravewrightRealtime.mapCommand("navigate",{mapId})', scene)
            gm.wait_for_function('(id)=>gravewrightMaps.current?.id===id', arg=scene)

            def state(page):
                return page.evaluate('async id=>(await (await fetch(`/api/maps/${id}/state`)).json())', scene)

            def wait_state(page, predicate, label):
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    current = state(page)
                    if predicate(current):
                        return current
                    page.wait_for_timeout(25)
                raise AssertionError(f'{label}: scene state did not reach the expected state: {current}')

            def wait_frame(page, needle, label):
                page.wait_for_function('needle=>receivedFrames.some(frame=>frame.includes(needle))', arg=needle, timeout=10000)

            def drag(page, start, end, steps=6):
                page.mouse.move(*start); page.mouse.down()
                page.mouse.move(*end, steps=steps); page.mouse.up()

            def tool(page, name):
                page.locator(f'.game-dock__group:visible [data-dock-tool={name}]').click()

            # 1. Player A's square area measurement reaches B, C, D, the GM and the streamer.
            started = time.perf_counter()
            tool(a, 'measure')
            a.locator('.measure-panel').get_by_role('button', name='Cube / rectangle', exact=True).click()
            a.keyboard.down('Shift'); drag(a, (420, 320), (560, 400)); a.keyboard.up('Shift')
            square = wait_state(a, lambda s: len(s['markers']) == 1, 'player measurement')['markers'][0]
            assert square['kind'] == 'rect' and abs(square['length'] - square['width']) < 1e-6, square
            for page in (gm, b, c, d, streamer):
                expect(page.locator('.measurement-workspace text')).to_have_count(1)
            timings.append({'action': 'Player area measurement visible to 3 players, GM and streamer',
                            'milliseconds': (time.perf_counter() - started) * 1000})
            for page, owner in ((a, True), (b, False), (gm, True), (streamer, False)):
                assert state(page)['markers'][0]['canEdit'] is owner
            a.locator('.measure-panel').get_by_role('button', name='Close measurement', exact=True).click()

            # 2. GM measurements reach everyone on the table layer and stay private on the GM layer.
            gm.locator('[data-menubar-shortcut=layer-gm]').click()
            tool(gm, 'measure')
            drag(gm, (1000, 350), (1120, 430))
            private_measure = next(m for m in wait_state(gm, lambda s: len(s['markers']) == 2, 'GM private measurement')['markers']
                                   if m['audience'] == 'gm')
            gm.locator('.measure-panel').get_by_role('button', name='Close measurement', exact=True).click()
            gm.locator('[data-menubar-shortcut=layer-game]').click()
            tool(gm, 'measure')
            drag(gm, (1000, 150), (1120, 230))
            wait_state(gm, lambda s: len(s['markers']) == 3, 'GM public measurement')
            gm.locator('.measure-panel').get_by_role('button', name='Close measurement', exact=True).click()
            for page in (a, b, c, d, streamer):
                expect(page.locator('.measurement-workspace text')).to_have_count(2)
                assert len(state(page)['markers']) == 2

            # 3. Every player has Mini Paint; streamers do not. Player A draws for everyone.
            expect(streamer.locator('[data-dock-tool=draw]')).to_have_count(0)
            for page in (a, b, c, d):
                expect(page.locator('.game-dock__group:visible [data-dock-tool=draw]')).to_have_count(1)
                tool(page, 'draw')
                expect(page.locator('.drawing-paint')).to_be_visible()
            a.locator('.drawing-paint').get_by_role('button', name='Rectangle', exact=True).click()
            started = time.perf_counter()
            drag(a, (400, 450), (580, 520))
            first = wait_state(a, lambda s: len(s['drawings']['rows']) == 1, 'player A drawing')['drawings']['rows'][0]
            for page in (gm, b, c, d, streamer):
                wait_frame(page, first['id'], 'player A drawing frame')
            timings.append({'action': 'Player drawing delivered to 3 players, GM and streamer',
                            'milliseconds': (time.perf_counter() - started) * 1000})
            assert first['canEdit'] is True and state(b)['drawings']['rows'][0]['canEdit'] is False

            # 4. Player B cannot erase A's drawing; the eraser only reaches B's own rows.
            b.locator('.drawing-paint').get_by_role('button', name='Stroke eraser', exact=True).click()
            drag(b, (400, 430), (400, 540), steps=40)
            b.wait_for_timeout(600)
            assert [row['id'] for row in state(gm)['drawings']['rows']] == [first['id']]
            expect(b.locator('.drawing-paint__hint[role=alert]')).to_have_count(0)

            # 5. B, C and D draw at the same time; every stroke is kept.
            strokes = ((b, 200), (c, 250), (d, 300))
            for page, _ in strokes:
                page.locator('.drawing-paint').get_by_role('button', name='Brush', exact=True).click()
            for page, y in strokes:
                page.mouse.move(150, y); page.mouse.down()
            for step in range(1, 9):
                for page, y in strokes:
                    page.mouse.move(150 + step * 30, y + (step % 2) * 8)
            for page in (b, c, d):
                page.mouse.up()
            rows = wait_state(gm, lambda s: len(s['drawings']['rows']) == 4, 'concurrent drawings')['drawings']['rows']
            for page in (a, b, c, d, streamer):
                wait_state(page, lambda s: len(s['drawings']['rows']) == 4, 'concurrent drawings delivered')
            for page in (a, b, c, d):
                expect(page.locator('.drawing-paint__hint[role=alert]')).to_have_count(0)

            # 6. Undo removes only the author's own latest drawing, not a peer's later one.
            drag(a, (1000, 200), (1140, 260))
            wait_state(a, lambda s: len(s['drawings']['rows']) == 5, 'player A second drawing')
            drag(b, (1000, 400), (1140, 460))
            after_peer = wait_state(a, lambda s: len(s['drawings']['rows']) == 6, 'peer drawing after A')['drawings']['rows']
            a.keyboard.press('Control+z')
            undone = wait_state(gm, lambda s: len(s['drawings']['rows']) == 5, 'undo')['drawings']['rows']
            assert after_peer[-1]['id'] in {row['id'] for row in undone}
            assert after_peer[-2]['id'] not in {row['id'] for row in undone}

            # 7. Players clear only their own drawings.
            clear = c.locator('.drawing-paint__clear')
            expect(clear).to_have_text('Clear my drawings')
            c.screenshot(path=str(output / 'player-mini-paint.png'))
            clear.click(); expect(clear).to_have_text('Confirm clearing'); clear.click()
            cleared = wait_state(gm, lambda s: len(s['drawings']['rows']) == 4, 'player clear')['drawings']['rows']
            c_rows = [row for row in rows if row['id'] not in {r['id'] for r in cleared}]
            assert len(c_rows) == 1, c_rows

            # 8. GM drawings on the GM layer stay private; the GM edits players' drawings.
            gm.locator('[data-menubar-shortcut=layer-gm]').click()
            tool(gm, 'draw')
            expect(gm.locator('.drawing-paint')).to_contain_text('GM only')
            drag(gm, (1200, 200), (1340, 260))
            secret = next(row for row in wait_state(gm, lambda s: len(s['drawings']['rows']) == 5, 'GM private drawing')['drawings']['rows']
                          if row['audience'] == 'gm')
            gm.locator('.drawing-paint').get_by_role('button', name='Close drawing').click()
            gm.locator('[data-menubar-shortcut=layer-game]').click()
            tool(gm, 'draw')
            expect(gm.locator('.drawing-paint__clear')).to_have_text('Clear layer')
            gm.locator('.drawing-paint').get_by_role('button', name='Stroke eraser', exact=True).click()
            drag(gm, (400, 430), (400, 540), steps=40)
            for page in everyone:
                wait_state(page, lambda s: first['id'] not in {row['id'] for row in s['drawings']['rows']}, 'GM erased player drawing')
            for page in (a, b, c, d, streamer):
                rows = state(page)['drawings']['rows']
                assert secret['id'] not in {row['id'] for row in rows} and len(rows) == 3
                assert not page.evaluate('ids=>receivedFrames.some(frame=>ids.some(id=>frame.includes(id)))',
                                         [secret['id'], private_measure['id']])
            gm.screenshot(path=str(output / 'gm-shared-drawings.png'))
            a.screenshot(path=str(output / 'player-a-shared-drawings.png'))
            streamer.screenshot(path=str(output / 'streamer-readonly.png'))

            # 9. Mobile layout of a player's Mini Paint keeps its controls reachable.
            d.set_viewport_size({'width': 390, 'height': 844})
            panel = d.locator('.drawing-paint')
            expect(panel).to_be_visible()
            box = panel.bounding_box()
            assert box['x'] >= 0 and box['x'] + box['width'] <= 390, box
            expect(d.locator('.drawing-paint__clear')).to_be_visible()
            d.screenshot(path=str(output / 'player-mini-paint-mobile.png'))
            assert not errors, errors
        except Exception:
            for role, page in pages.items():
                try:
                    page.screenshot(path=str(output / f'failure-{role}.png'))
                except Exception:
                    pass
            (output / 'diagnostics.json').write_text(json.dumps({'pageErrors': errors, 'timings': timings}, indent=2))
            raise
        finally:
            for context in contexts:
                context.close()
            browser.close()
    return {'passed': True, 'pageErrors': errors, 'timings': timings,
            'cases': ['Player area measurement reaches three players, the GM and the streamer',
                      'GM table-layer measurements reach everyone; GM-layer measurements stay private',
                      'Every player has Mini Paint; streamers do not',
                      'Player drawings reach every client; peers cannot erase them',
                      'Concurrent drawings from three players are all kept',
                      'Undo affects only the author\'s own drawings',
                      'Players clear only their own drawings',
                      'GM-layer drawings stay private; GMs edit players\' drawings',
                      'Player Mini Paint fits a 390px viewport']}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
