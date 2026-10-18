"""Exercise private presence regions and multi-token pressure plates in the real game.

The campaign, synthetic actor, database, media and server belong to this fixture.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import map_builder_blueprints as harness
from map_builder import ROOT, MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import close_panel, set_name, wait_ready


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    builder = f'/game/{campaign}/map-builder'
    records, errors, dialogs = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        guests = []

        def observe(target):
            target.on('pageerror', lambda error: errors.append(str(error)))
            target.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))

        observe(page)
        review = BuilderReview(page, campaign)

        def select_region(identifier):
            builder_tool(page, 'select')
            builder_workspace(page)
            shape = page.locator(f'[data-builder-regions] [data-object-id="{identifier}"]')
            box = shape.bounding_box()
            page.mouse.click(box['x'] + box['width'] * .2, box['y'] + box['height'] * .2)
            builder_sidebar(page, 'selection')
            expect(page.locator('[data-builder-property=regionName]')).to_be_visible()

        try:
            page.goto(builder)
            wait_ready(page)
            set_name(page, 'Synthetic multi-token pressure plate')
            builder_tool(page, 'region')
            review.stroke((10, 8), (14, 12))
            builder_sidebar(page, 'selection')
            name = page.locator('[data-builder-property=regionName]')
            expect(name).to_be_visible()
            name.fill('Synthetic pressure plate with a long authored region name')
            name.press('Tab')
            first = review.save()
            region, = first['document']['regions']
            assert not first['document']['assets']
            assert region['x'] == 10 and region['y'] == 8 and region['width'] == 4 and region['height'] == 4, region
            assert region['name'].startswith('Synthetic pressure') and region['enabled'] is True
            records.append({'case': 'fresh-empty-map-draws-and-names-a-private-region-without-assets'})

            page.locator('[data-builder-property=regionEnabled]').uncheck()
            low = page.locator('[data-builder-property=region-bottom]')
            low.fill('-2'); low.press('Tab')
            high = page.locator('[data-builder-property=region-top]')
            high.fill('3'); high.press('Tab')
            bounded = review.save()['document']['regions'][0]
            assert bounded['enabled'] is False and bounded['vertical'] == {'bottom': -2, 'top': 3}, bounded
            page.locator('[data-builder-property=regionEnabled]').check()
            page.locator('[data-builder-duplicate]').click()
            assert len(review.save()['document']['regions']) == 2
            close_panel(page)
            page.locator('[data-builder-viewport]').focus(); page.keyboard.press('Delete')
            assert len(review.save()['document']['regions']) == 1
            page.locator('[data-builder-undo]').click()
            assert len(review.save()['document']['regions']) == 2
            page.locator('[data-builder-redo]').click()
            assert len(review.save()['document']['regions']) == 1
            records.append({'case': 'region-settings-duplicate-delete-and-undo-redo-persist'})

            builder_tool(page, 'door')
            review.stroke((20, 10), (23, 10))
            authored = review.save()
            door, = authored['document']['doors']
            select_region(region['id'])
            page.locator('[data-builder-region-door]').select_option(door['id'])
            page.locator('[data-builder-region-apply]').click()
            page.locator('[data-builder-edit-behavior]').click()
            modal = page.locator('[data-smart-object-modal]')
            expect(modal.locator('[data-blueprint-event-port="presence:enter"]')).to_be_visible()
            expect(modal.locator('[data-blueprint-event-port="presence:exit"]')).to_be_visible()
            modal.locator('[data-blueprint-event="presence:enter"]').click()
            preview_context = modal.locator('[data-blueprint-simulation-context]')
            preview_context.locator('summary').click()
            modal.locator('[data-blueprint-context-property=count]').fill('1')
            modal.locator('[data-blueprint-context-property=count]').press('Tab')
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator('[data-blueprint-trace]')).to_contain_text('Opened')
            modal.locator('[data-blueprint-event="presence:exit"]').click()
            modal.locator('[data-blueprint-context-property=count]').fill('0')
            modal.locator('[data-blueprint-context-property=count]').press('Tab')
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator('[data-blueprint-trace]')).to_contain_text('Closed')
            page.screenshot(path=str(output / 'region-blueprint-desktop.png'))
            modal.locator('[data-blueprint-close]').click()
            configured = review.save()
            blueprint = configured['document']['regions'][0]['blueprint']
            assert blueprint['kind'] == 'region' and set(blueprint['graphs']) == {'presence:enter', 'presence:exit'}
            for event, count in (('presence:enter', 1), ('presence:exit', 0)):
                graph = blueprint['graphs'][event]
                assert next(row for row in graph['nodes'] if row['type'] == 'event')['event'] == event
                assert next(row for row in graph['nodes'] if row['type'] == 'eventContext')['property'] == 'count'
                assert next(row for row in graph['nodes'] if row['type'] == 'compareValue')['expected'] == count
            records.append({'case': 'pressure-plate-preset-wires-first-entry-and-last-exit-to-the-selected-door'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                page.set_viewport_size({'width': 390, 'height': 844})
                page.goto(builder + '?project=' + configured['id'])
                wait_ready(page)
                select_region(region['id'])
                page.locator('[data-builder-region-apply]').scroll_into_view_if_needed()
                metrics = page.locator('#builder-editor-panels').evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], metrics
                page.screenshot(path=str(output / f'region-{locale}-390.png'))
                records.append({'case': 'localized-mobile-region-properties-and-pressure-preset', 'locale': locale, 'metrics': metrics})
                page.locator('[data-builder-edit-behavior]').click()
                modal = page.locator('[data-smart-object-modal]')
                for phase in ('enter', 'exit'):
                    presence = modal.locator(f'[data-blueprint-event="presence:{phase}"]')
                    presence.scroll_into_view_if_needed()
                    expect(presence).to_be_visible()
                    expect(presence.locator('.smart-object__event-label')).to_be_visible()
                page.screenshot(path=str(output / f'region-blueprint-{locale}-390.png'))
                modal.locator('[data-blueprint-cancel]').click()

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(builder + '?project=' + configured['id'])
            wait_ready(page)
            close_panel(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            project = review.project(configured['id'])
            scene = project['sceneId']

            def command(area, action, data):
                return page.evaluate("""a=>gravewrightRealtime.mapCommand('objects',{
                  mapId:a.scene,area:a.area,action:a.action,data:a.data})""",
                                     {'scene': scene, 'area': area, 'action': action, 'data': data})

            def state(target=page):
                return target.request.get(f'/api/maps/{scene}/state').json()

            def automation():
                return page.request.get(f'/api/maps/{scene}/automation').json()

            def state_actions():
                return sum(step['type'] == 'state' for run in automation()['runs']
                           for event in run.get('events', []) for step in event.get('steps', []))

            command('lighting', 'update', {'mode': 'none', 'darkness': 0, 'lights_out': False})
            page.evaluate("""a=>gravewrightRealtime.mapCommand('update',{
              mapId:a.scene,version:a.version,settings:{visibility:'players'}})""",
                          {'scene': scene, 'version': project['sceneVersion']})
            page.evaluate("scene=>gravewrightRealtime.mapCommand('activate',{mapId:scene})", scene)
            python = sys._base_executable if os.name == 'nt' else sys.executable
            prepared = subprocess.run([python, '-B', '-X', 'utf8', str(ROOT / 'tests/e2e/map_builder_studio.py'),
                                       '--fixture', str(output / 'fixture'), '--prepare-scene', scene],
                                      cwd=ROOT, env=os.environ.copy(), capture_output=True, text=True, encoding='utf-8', check=True)
            token = json.loads(prepared.stdout)['token']
            duplicated = page.evaluate("""a=>gravewrightRealtime.resourceCommand('tokens','duplicate',{
              mapId:a.scene,tokenIds:[a.token]})""", {'scene': scene, 'token': token})
            second, = duplicated['createdIds']
            region_native, = state()['zones']
            assert region_native['region']['name'] == region['name'] and region_native['region']['state'] == 'empty', region_native
            assert 'occupants' not in region_native['region'], region_native
            native_door, = [row for row in state()['walls'] if row['kind'] == 'door']

            guest = browser.new_context(base_url=base, viewport={'width': 1200, 'height': 800})
            guests.append(guest)
            guest.add_cookies([{**seed['sessions']['player'], 'url': base}])
            player = guest.new_page(); observe(player)
            player.goto(f'/game/{campaign}')
            player.wait_for_function('id=>window.gravewrightMaps?.current?.id===id&&!!window.gravewrightRealtime', arg=scene)
            expect(player.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            assert state(player)['zones'] == [], state(player)['zones']
            records.append({'case': 'generation-uses-native-private-zones-without-token-identifiers-or-player-geometry'})

            def move(identifier, x, y):
                return player.evaluate("""async a=>{
                  const body=await(await fetch(`/api/containers/${a.campaign}/maps/${a.scene}/tokens`)).json();
                  const token=body.tokens.find(row=>row.id===a.id);
                  return gravewrightRealtime.resourceCommand('tokens','move',{mapId:a.scene,id:a.id,
                    expectedVersion:token.version,gridX:a.x,gridY:a.y});
                }""", {'campaign': campaign, 'scene': scene, 'id': identifier, 'x': x, 'y': y})

            def verify(count, door_state):
                native = state()
                current = next(row for row in native['zones'] if row['id'] == region_native['id'])
                assert current['region'] == {'name': region['name'], 'state': 'occupied' if count else 'empty', 'count': count}, current
                assert next(row for row in native['walls'] if row['id'] == native_door['id'])['door_state'] == door_state, native
                return native

            move(token, 11, 9)
            verify(1, 'open')
            actions_first = state_actions()
            move(second, 12, 10)
            verify(2, 'open')
            assert state_actions() == actions_first
            move(token, 6, 3)
            verify(1, 'open')
            assert state_actions() == actions_first
            move(second, 7, 4)
            verify(0, 'closed')
            assert state_actions() == actions_first + 1
            records.append({'case': 'real-player-first-token-opens-last-token-closes-and-intermediate-occupancy-does-not-retrigger'})

            move(token, 12, 10)
            verify(1, 'open')
            before_reload = len(automation()['runs'])
            page.reload()
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            verify(1, 'open')
            assert len(automation()['runs']) == before_reload
            page.goto(builder + '?project=' + configured['id'])
            wait_ready(page)
            builder_sidebar(page, 'review')
            with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                page.locator('[data-builder-review-update]').click()
            assert updated.value.ok, updated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            verify(1, 'open')
            assert len(automation()['runs']) == before_reload
            records.append({'case': 'reloading-and-updating-linked-scene-preserves-occupancy-and-live-door-without-entry-replay'})

            page.locator('.game-menubar__layer').nth(5).click()
            page.locator('[data-dock-tool=automation]').click()
            log = page.locator('[data-automation-log]')
            if not log.count(): log = page.locator('.automation-log')
            expect(log.locator('[data-automation-presence-context]').first).to_contain_text(token)
            expect(log.locator('[data-automation-presence-context]').first).to_contain_text('Tokens inside: 1')
            log.locator('[data-automation-view=doors]').click()
            row = log.locator(f'[data-scene-controls-element="{region_native["id"]}"]')
            expect(row).to_contain_text(region['name'])
            expect(row).to_contain_text('Occupied')
            row.click()
            expect(log.locator('[data-scene-controls-inspector] [data-scene-controls-action=interact]')).to_have_count(0)
            expect(log.locator('[data-scene-controls-flag=region]')).to_be_checked()
            page.screenshot(path=str(output / 'region-native-automation.png'))
            page.keyboard.press('Escape')
            current = next(row for row in state()['zones'] if row['id'] == region_native['id'])
            page.locator('[data-dock-tool=select]:visible').first.click()
            position = page.evaluate("""geometry=>{
              const surface=document.querySelector('.game-table__scene-frame').getBoundingClientRect();
              const view=gravewrightMaps.board.viewport();
              return [surface.x+view.x+(geometry.x+geometry.width*.08)*view.scale,
                surface.y+view.y+(geometry.y+geometry.height*.08)*view.scale];
            }""", current['geometry'])
            page.mouse.dblclick(*position)
            editor = page.locator('[data-region-editor]')
            expect(editor).to_be_visible()
            expect(editor.locator('[data-region-status]')).to_contain_text('Occupied')
            page.screenshot(path=str(output / 'region-native-editor.png'))
            editor.locator('[name=width]').fill('0')
            editor.locator('[type=submit]').click()
            expect(editor).to_be_visible()
            assert editor.locator('[name=width]').evaluate('input=>input.checkValidity()') is False
            editor.locator('[name=width]').fill(str(current['geometry']['width']))
            native_name = ('Native edited pressure plate with a long authored name at the full supported limit — ' * 2)[:120]
            assert len(native_name) == 120
            expect(editor.locator('[name=name]')).to_have_attribute('maxlength', '120')
            editor.locator('[name=name]').fill(native_name)
            expect(editor.locator('[name=name]')).to_have_value(native_name)
            editor.locator('[type=submit]').click()
            expect(editor).to_have_count(0)
            revised = next(row for row in state()['zones'] if row['id'] == region_native['id'])
            assert revised['region']['name'] == native_name and revised['region']['count'] == 1, revised
            assert len(automation()['runs']) == before_reload
            records.append({'case': 'gm-native-editor-validates-dimensions-and-full-120-character-name-without-synthetic-presence-events'})

            page.mouse.dblclick(*position)
            editor = page.locator('[data-region-editor]')
            expect(editor).to_be_visible()
            move(token, 6, 3)
            editor.locator('[name=name]').fill('Stale form must preserve the live region')
            editor.locator('[type=submit]').click()
            expect(editor.locator('[role=alert]')).to_contain_text('changed')
            latest = next(row for row in state()['zones'] if row['id'] == region_native['id'])
            assert latest['region']['name'] == native_name and latest['region']['count'] == 0, latest
            editor.locator('[data-cancel]').click()
            page.mouse.dblclick(*position)
            editor = page.locator('[data-region-editor]')
            expect(editor.locator('[data-region-status]')).to_contain_text('Empty')
            expect(editor.locator('[name=name]')).to_have_value(native_name)
            editor.locator('[data-cancel]').click()
            records.append({'case': 'live-presence-change-refuses-stale-native-form-and-reopens-current-state'})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            for guest in guests: guest.close()
            context.close(); browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'No map artwork; synthetic disposable actor and silent fixture WAV only.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
