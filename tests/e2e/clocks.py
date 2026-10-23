"""Exercise native progress clocks with disposable campaigns and real clients."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import traceback
from urllib.request import urlopen
import uuid

from campaign_management import serve, snapshot
from map_builder import ROOT, MEASURE, change_locale, fixture_environment


CLOCK_NAME = 'Synthetic expedition preparations at the abandoned northern observatory'
EDITED_NAME = 'Synthetic expedition preparations reviewed by the party at the northern observatory'
PRIVATE_NAME = 'SYNTHETIC_GM_CLOCK_SECRET: The patron is preparing an ambush'
SCENE_NAME = 'Synthetic progress visible only in the privately selected scene'


def check_browser(base, seed, output, executable, read_snapshot):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    records, errors, dialogs, failed = [], [], [], []
    before = read_snapshot()
    (output / 'control-before.json').write_text(json.dumps(before, indent=2), encoding='utf-8')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        contexts, pages, sockets = [], {}, {}

        def client(name, role, *, manager=False):
            context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 1000})
            contexts.append(context)
            context.add_cookies([{**seed['sessions'][role], 'url': base}])
            page = context.new_page()
            pages[name], sockets[name] = page, []
            page.on('pageerror', lambda error: errors.append(error.stack or str(error)))
            page.on('requestfailed', lambda request: failed.append({'url': request.url, 'error': request.failure}))
            page.on('websocket', lambda socket: sockets[name].append(socket.url))

            def native_dialog(dialog):
                dialogs.append({'type': dialog.type, 'message': dialog.message})
                dialog.dismiss()

            page.on('dialog', native_dialog)
            response = page.goto(base + (f'/campaigns/{campaign}/manage?section=clocks' if manager else f'/game/{campaign}'))
            assert response.ok, (name, response.status)
            if manager:
                expect(page.locator('#table-workspace')).to_have_attribute('data-manager-ready', 'true')
                expect(page.locator('[data-manager-section=clocks]')).to_have_attribute('aria-current', 'page')
                assert not sockets[name], sockets[name]
            else:
                page.wait_for_function('!!window.gravewrightMaps && !!window.gravewrightRealtime')
                expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            return page

        def api(page, method, payload=None, *, scene=None, request_id=None, table=None):
            result = page.evaluate('''async ({campaign,method,payload,scene,requestId})=>{
              const api=gravewright.forTable(campaign); const options=requestId?{requestId}:{};
              const current=scene ?? window.gravewrightMaps?.current?.id ?? null;
              try {
                const value=await api.clocks[method](method==='state'?{sceneId:current}:{...payload,sceneId:current},options);
                return {ok:true,value};
              } catch(error) {return {ok:false,code:error.code,status:error.status,message:error.message};}
            }''', {'campaign': table or campaign, 'method': method, 'payload': payload,
                  'scene': scene, 'requestId': request_id})
            return result

        def state(page, scene=None):
            result = api(page, 'state', scene=scene)
            assert result['ok'], result
            return result['value']

        def row(page, clock_id, scene=None):
            return next(clock for clock in state(page, scene)['clocks'] if clock['id'] == clock_id)

        def mutate(page, method, payload, **options):
            result = api(page, method, payload, **options)
            assert result['ok'], result
            return result['value']

        def open_panel(page):
            page.locator('[data-clocks-open]').click()
            panel = page.locator('[data-clock-panel]')
            expect(panel).to_be_visible()
            expect(panel.locator('[data-clocks-root]')).to_be_visible()
            expect(page.locator('.upload-library:visible')).to_have_count(0)
            return panel

        def card(root, clock_id):
            return root.locator(f'[data-clock-id="{clock_id}"]')

        def progress(root, clock_id, value, segments):
            expect(card(root, clock_id).locator('[data-clock-value]')).to_have_text(re.compile(rf'^{value}\s*/\s*{segments}$'))

        def controls_readonly(root, clock_id):
            clock = card(root, clock_id)
            expect(clock.locator('[data-clock-action]:visible:not(:disabled)')).to_have_count(0)

        try:
            manager = client('manager', 'gm', manager=True)
            management_root = manager.locator('[data-manager-view=clocks] [data-clocks-root]')
            expect(management_root).to_be_visible()
            expect(management_root.locator('[data-clocks-empty]')).to_be_visible()
            management_root.locator('[data-clock-action=create]').click()
            editor = manager.locator('[data-clock-editor]')
            expect(editor).to_be_visible()
            editor.locator('[name=name]').fill(CLOCK_NAME)
            editor.locator('[name=preset]').select_option('custom')
            editor.locator('[name=segments]').fill('7')
            editor.locator('[name=value]').fill('2')
            editor.locator('[name=color]').evaluate("input=>{input.value='#4a90e2';input.dispatchEvent(new Event('input',{bubbles:true}));}")
            editor.locator('[name=visibility]').select_option('players')
            editor.locator('[name=playersCanEdit]').check()
            editor.locator('[name=pinned]').check()
            editor.locator('[type=submit]').click()
            expect(editor).to_have_count(0)
            public = next(clock for clock in state(manager)['clocks'] if clock['name'] == CLOCK_NAME)
            public_id = public['id']
            assert public['sceneId'] is None and public['segments'] == 7 and public['value'] == 2, public
            progress(management_root, public_id, 2, 7)
            management_root.screenshot(path=str(output / 'management-created-1440.png'))
            records.append({'case': 'gm-creates-campaign-clock-with-custom-segments-through-native-management-editor'})

            management_root.locator('[data-clock-action=create]').click()
            expect(editor).to_be_visible()
            editor.locator('[name=name]').fill('Cancelled synthetic clock')
            manager.keyboard.press('Escape')
            expect(editor).to_have_count(0)
            assert len(state(manager)['clocks']) == 1
            records.append({'case': 'escape-cancels-native-clock-editor-without-persisting-a-draft'})

            private = mutate(manager, 'create', {'name': PRIVATE_NAME, 'segments': 6, 'value': 1,
                'color': '#9056aa', 'visibility': 'gm', 'playersCanEdit': False, 'pinned': False, 'scopeSceneId': None})['clock']
            scene_clock = mutate(manager, 'create', {'name': SCENE_NAME, 'segments': 4, 'value': 0,
                'color': '#c09030', 'visibility': 'players', 'playersCanEdit': True, 'pinned': True,
                'scopeSceneId': seed['selectedScene']}, scene=seed['selectedScene'])['clock']
            assert scene_clock['id'] in {clock['id'] for clock in state(manager, seed['selectedScene'])['clocks']}
            assert scene_clock['id'] not in {clock['id'] for clock in state(manager, seed['broadcastScene'])['clocks']}
            records.append({'case': 'campaign-and-scene-clock-scopes-use-distinct-authoritative-records'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(manager, locale, campaign)
                manager.set_viewport_size({'width': 320, 'height': 844})
                manager.goto(f'{base}/campaigns/{campaign}/manage?section=clocks')
                expect(manager.locator('#table-workspace')).to_have_attribute('data-manager-ready', 'true')
                labels = {'en': 'Clocks', 'pt-BR': 'Relógios', 'es': 'Relojes'}
                expect(manager.locator('[data-manager-section=clocks]')).to_have_text(labels[locale])
                progress(management_root, public_id, 2, 7)
                expect(card(management_root, public_id).locator('[data-clock-name]')).to_have_text(CLOCK_NAME)
                metrics = management_root.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                assert manager.evaluate('document.documentElement.scrollWidth<=innerWidth+1'), locale
                manager.screenshot(path=str(output / f'clocks-{locale}-320.png'), full_page=True)
                card(management_root, public_id).locator('[data-clock-action=edit]').click()
                expect(editor).to_be_visible()
                expect(editor.locator('[name=name]')).to_have_value(CLOCK_NAME)
                custom_labels = {'en': 'Custom', 'pt-BR': 'Personalizado', 'es': 'Personalizado'}
                expect(editor.locator('[name=preset] option:checked')).to_have_text(custom_labels[locale])
                metrics = editor.evaluate(MEASURE)
                bounds = editor.bounding_box()
                assert bounds and bounds['x'] >= -1 and bounds['y'] >= -1 and bounds['x'] + bounds['width'] <= 321 and bounds['y'] + bounds['height'] <= 845, bounds
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                editor.screenshot(path=str(output / f'editor-{locale}-320.png'))
                manager.keyboard.press('Escape')
                expect(editor).to_have_count(0)
                records.append({'case': f'localized-clock-list-and-native-editor-{locale}-320'})

            after = read_snapshot()
            (output / 'control-after.json').write_text(json.dumps(after, indent=2), encoding='utf-8')
            assert before == after, {'before': before, 'after': after}
            assert not sockets['manager'], sockets['manager']
            records.append({'case': 'management-clocks-do-not-open-websockets-or-change-broadcast-navigation-and-presence'})

            change_locale(manager, 'en', campaign)
            manager.set_viewport_size({'width': 1440, 'height': 1000})
            manager.goto(f'{base}/campaigns/{campaign}/manage?section=clocks')
            expect(manager.locator('#table-workspace')).to_have_attribute('data-manager-ready', 'true')
            gm = client('gm', 'gm')
            player = client('player', 'player')
            streamer = client('streamer', 'streamer')
            gm.wait_for_function('id=>gravewrightMaps.current?.id===id', arg=seed['selectedScene'])
            for page in (player, streamer):
                page.wait_for_function('id=>gravewrightMaps.current?.id===id', arg=seed['broadcastScene'])
            panels = {name: open_panel(page) for name, page in (('gm', gm), ('player', player), ('streamer', streamer))}
            for name, page in (('gm', gm), ('player', player), ('streamer', streamer)):
                progress(panels[name], public_id, 2, 7)
                progress(page.locator('[data-clock-hud]'), public_id, 2, 7)
            expect(card(panels['gm'], private['id'])).to_be_visible()
            expect(card(panels['gm'], scene_clock['id'])).to_be_visible()
            for name, page in (('player', player), ('streamer', streamer)):
                projection = json.dumps(state(page, seed['broadcastScene']))
                assert PRIVATE_NAME not in projection and SCENE_NAME not in projection
                assert PRIVATE_NAME not in page.content() and SCENE_NAME not in page.content()
                expect(card(panels[name], private['id'])).to_have_count(0)
                expect(card(panels[name], scene_clock['id'])).to_have_count(0)
            controls_readonly(panels['streamer'], public_id)
            records.append({'case': 'shared-table-and-pinned-clocks-filter-private-and-other-scene-records-before-delivery'})
            gm.keyboard.press('Escape')
            expect(gm.locator('[data-clock-panel]')).to_have_count(0)
            gm.locator('.game-menubar__library').click()
            expect(gm.locator('.upload-library')).to_be_visible()
            gm.locator('.upload-library').get_by_role('button', name='Close library', exact=True).click()
            expect(gm.locator('.upload-library')).to_be_hidden()
            panels['gm'] = open_panel(gm)
            records.append({'case': 'clock-and-library-toolbar-actions-open-their-own-independent-windows'})

            card(panels['gm'], public_id).locator('[data-clock-action=advance][data-clock-delta="1"]').click()
            for panel in panels.values():
                progress(panel, public_id, 3, 7)
            manager.evaluate("window.dispatchEvent(new Event('focus'))")
            progress(management_root, public_id, 3, 7)
            card(panels['player'], public_id).locator('[data-clock-action=advance][data-clock-delta="1"]').click()
            for panel in panels.values():
                progress(panel, public_id, 4, 7)
            records.append({'case': 'gm-and-authorized-player-progress-arrives-realtime-and-management-refreshes-on-focus'})

            latest = row(gm, public_id, seed['selectedScene'])
            for page, action, payload in (
                (streamer, 'advance', {'id': public_id, 'version': latest['version'], 'delta': 1}),
                (player, 'reset', {'id': public_id, 'version': latest['version']}),
                (player, 'delete', {'id': public_id, 'version': latest['version']}),
                (player, 'advance', {'id': private['id'], 'version': private['version'], 'delta': 1}),
            ):
                denied = api(page, action, payload)
                assert not denied['ok'] and denied['status'] in (403, 404), denied
            denied = api(gm, 'state', table=seed['otherCampaign'])
            assert not denied['ok'] and denied['status'] in (403, 404), denied
            records.append({'case': 'server-rejects-streamer-writes-player-configuration-private-id-and-foreign-campaign-access'})

            mutate(gm, 'advance', {'id': public_id, 'version': latest['version'], 'delta': 1})
            conflict = api(player, 'advance', {'id': public_id, 'version': latest['version'], 'delta': 1})
            assert not conflict['ok'] and conflict['code'] == 'conflict' and conflict['status'] == 409, conflict
            for panel in panels.values():
                progress(panel, public_id, 5, 7)
            canonical = row(gm, public_id, seed['selectedScene'])
            operation = {'id': public_id, 'version': canonical['version'], 'delta': 1}
            request_id = str(uuid.uuid4())
            first = mutate(gm, 'advance', operation, request_id=request_id)
            replay = mutate(gm, 'advance', operation, request_id=request_id)
            assert first == replay and first['clock']['value'] == 6, (first, replay)
            for panel in panels.values():
                progress(panel, public_id, 6, 7)
            records.append({'case': 'concurrent-version-conflict-and-idempotent-retry-preserve-canonical-progress'})

            card(panels['gm'], public_id).locator('[data-clock-action=edit]').click()
            gm_editor = gm.locator('[data-clock-editor]')
            expect(gm_editor).to_be_visible()
            gm_editor.locator('[name=name]').fill('Synthetic draft preserved after a concurrent update')
            latest = row(player, public_id, seed['broadcastScene'])
            mutate(player, 'advance', {'id': public_id, 'version': latest['version'], 'delta': 1})
            gm_editor.locator('[type=submit]').click()
            expect(gm_editor.locator('[role=alert]')).to_be_visible()
            expect(gm_editor.locator('[name=name]')).to_have_value('Synthetic draft preserved after a concurrent update')
            canonical = row(gm, public_id, seed['selectedScene'])
            assert canonical['name'] == CLOCK_NAME and canonical['value'] == 7, canonical
            gm.keyboard.press('Escape')
            expect(gm_editor).to_have_count(0)
            mutate(gm, 'advance', {'id': public_id, 'version': canonical['version'], 'delta': -1})
            progress(panels['gm'], public_id, 6, 7)
            records.append({'case': 'native-editor-retains-draft-on-conflict-and-does-not-overwrite-concurrent-progress'})

            card(panels['gm'], public_id).locator('[data-clock-action=edit]').click()
            gm_editor = gm.locator('[data-clock-editor]')
            expect(gm_editor).to_be_visible()
            gm_editor.locator('[name=name]').fill(EDITED_NAME)
            gm_editor.locator('[name=preset]').select_option('8')
            gm_editor.locator('[name=value]').fill('6')
            gm_editor.locator('[name=color]').evaluate("input=>{input.value='#e2a04a';input.dispatchEvent(new Event('input',{bubbles:true}));}")
            gm_editor.locator('[type=submit]').click()
            expect(gm_editor).to_have_count(0)
            for panel in panels.values():
                progress(panel, public_id, 6, 8)
                expect(card(panel, public_id).locator('[data-clock-name]')).to_have_text(EDITED_NAME)
            manager.evaluate("window.dispatchEvent(new Event('focus'))")
            progress(management_root, public_id, 6, 8)
            gm.screenshot(path=str(output / 'table-gm-pinned-1440.png'), full_page=True)
            player.screenshot(path=str(output / 'table-player-pinned-1440.png'), full_page=True)
            records.append({'case': 'native-table-editor-updates-saved-config-and-manager-shares-the-same-clock'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(gm, locale, campaign)
                gm.set_viewport_size({'width': 320, 'height': 844})
                gm.reload()
                expect(gm.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
                panels['gm'] = open_panel(gm)
                progress(panels['gm'], public_id, 6, 8)
                for target in (panels['gm'], gm.locator('[data-clock-hud]')):
                    metrics = target.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                gm.screenshot(path=str(output / f'table-{locale}-320.png'), full_page=True)
                gm.keyboard.press('Escape')
                expect(gm.locator('[data-clock-panel]')).to_have_count(0)
                panels['gm'] = open_panel(gm)
                expect(gm.locator('[data-clock-panel]')).to_have_count(1)
                records.append({'case': f'localized-table-panel-and-pinned-hud-{locale}-320-close-and-reopen'})

            player.reload()
            expect(player.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            panels['player'] = open_panel(player)
            progress(panels['player'], public_id, 6, 8)
            card(panels['gm'], public_id).locator('[data-clock-action=reset]').click()
            for panel in panels.values():
                progress(panel, public_id, 0, 8)
            latest = row(gm, public_id, seed['selectedScene'])
            mutate(gm, 'update', {'id': public_id, 'version': latest['version'], 'playersCanEdit': False})
            controls_readonly(panels['player'], public_id)
            latest = row(gm, public_id, seed['selectedScene'])
            denied = api(player, 'advance', {'id': public_id, 'version': latest['version'], 'delta': 1})
            assert not denied['ok'] and denied['status'] == 403, denied
            records.append({'case': 'reload-restores-progress-reset-syncs-and-revoked-player-editing-is-enforced'})

            latest = row(gm, public_id, seed['selectedScene'])
            mutate(gm, 'update', {'id': public_id, 'version': latest['version'], 'visibility': 'gm'})
            for name, page in (('player', player), ('streamer', streamer)):
                expect(card(panels[name], public_id)).to_have_count(0)
                expect(card(page.locator('[data-clock-hud]'), public_id)).to_have_count(0)
            card(panels['gm'], public_id).locator('[data-clock-action=delete]').click()
            deletion = gm.locator('[data-clock-editor]')
            expect(deletion).to_be_visible()
            expect(deletion.locator('.clocks-editor__fields strong')).to_have_text(EDITED_NAME)
            deletion.locator('[type=submit]').click()
            expect(deletion).to_have_count(0)
            expect(card(panels['gm'], public_id)).to_have_count(0)
            records.append({'case': 'changing-audience-removes-live-player-hud-and-deleting-removes-the-clock'})
            assert not errors, errors
            assert not dialogs, dialogs
            assert not [request for request in failed if request['error'] != 'net::ERR_ABORTED'], failed
        except Exception:
            (output / 'browser-diagnostics.json').write_text(json.dumps({'completedCases': records,
                'pageErrors': errors, 'nativeDialogs': dialogs, 'failedRequests': failed, 'websockets': sockets}, indent=2), encoding='utf-8')
            for name, page in pages.items():
                page.screenshot(path=str(output / f'failure-{name}.png'), full_page=True)
            raise
        finally:
            for context in contexts:
                context.close()
            browser.close()
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'failedRequests': failed, 'managementPreservedTableState': before == after,
            'assets': 'Generated synthetic PDFs, silent audio and authored synthetic clock names only.'}


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
        serve(args.fixture, args.port)
        return
    if args.snapshot:
        snapshot(args.fixture)
        return
    output = (args.output or ROOT / 'data/clocks' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
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

            def read_snapshot():
                return json.loads(subprocess.check_output([*command, '--snapshot', '--fixture', str(fixture)],
                    cwd=ROOT, env=os.environ.copy(), text=True, encoding='utf-8'))

            report = check_browser(base, seed, output, args.browser_executable, read_snapshot)
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
