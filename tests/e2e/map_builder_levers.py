"""Exercise authored lever behavior and real player double-click interactions.

Uses the common disposable campaign, synthetic images and owned localhost
server. Project state, browser artifacts and media stay in the chosen output.
"""
from __future__ import annotations

from io import BytesIO
import time

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, change_locale
from map_builder_reference import close_panel, set_name, upload_asset, wait_ready


def check_browser(base, seed, output, executable):
    from PIL import Image
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    builder = f'/game/{campaign}/map-builder'
    api = f'/api/containers/{campaign}/map-builder'
    records, errors, failed, dialogs = [], [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        player_context = None

        def observe(target):
            target.on('pageerror', lambda error: errors.append(str(error)))
            target.on('requestfailed', lambda request: failed.append(
                {'url': request.url, 'error': request.failure}))

            def native_dialog(dialog):
                dialogs.append(dialog.message)
                dialog.dismiss()

            target.on('dialog', native_dialog)

        observe(page)
        try:
            page.goto(builder)
            wait_ready(page)
            set_name(page, 'Synthetic lever controls a locked door')
            off_asset = upload_asset(page, 'decoration',
                                     'Synthetic deactivated mechanism with a deliberately long descriptive label.png',
                                     harness.artwork('#b94a28'))['id']
            on_asset = upload_asset(page, 'decoration',
                                    'Synthetic activated mechanism alternate image with a deliberately long descriptive label.png',
                                    harness.artwork('#2677dd'))['id']
            door_asset = upload_asset(page, 'door', 'Synthetic door.png', harness.artwork('#559344'))['id']

            def position(x, y):
                return page.locator('[data-builder-canvas]').evaluate("""(canvas, point) => {
                  const p = new DOMPoint(...point).matrixTransform(canvas.getScreenCTM());
                  return [p.x, p.y];
                }""", [x, y])

            def stroke(start, end):
                page.mouse.move(*position(*start))
                page.mouse.down()
                page.mouse.move(*position(*end), steps=5)
                page.mouse.up()

            def save():
                if page.locator('[data-map-builder]').get_attribute('data-save-state') == 'saved':
                    project_id = page.evaluate("new URL(location.href).searchParams.get('project')")
                    response = page.request.get(api + '/projects/' + project_id)
                else:
                    with page.expect_response(lambda response: response.request.method == 'POST'
                                              and '/map-builder/projects/' in response.url
                                              and not response.url.endswith(('/generate', '/update'))) as saved:
                        page.locator('[data-builder-save]').click()
                    response = saved.value
                assert response.ok, response.text()
                return response.json()['project']

            builder_tool(page, 'door')
            page.locator('[data-builder-brush-material]').select_option(door_asset)
            stroke((8, 6), (10, 6))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-door-state=locked]').click()
            close_panel(page)
            builder_tool(page, 'decoration')
            page.locator('[data-builder-brush-material]').select_option(off_asset)
            stroke((12, 8), (14, 10))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=assetId]').select_option('')
            page.locator('[data-builder-property=behavior]').select_option('lever')
            expect(page.locator('[data-builder-property=behavior]')).to_have_value('none')
            expect(page.locator('[data-builder-notice]')).to_contain_text('Choose an object image')
            page.locator('[data-builder-notice] button').click()
            page.locator('[data-builder-property=assetId]').select_option(off_asset)
            page.locator('[data-builder-property=behavior]').select_option('lever')
            expect(page.locator('[data-builder-property=leverState]')).to_have_value('off')
            expect(page.locator('[data-builder-property=assetId] option[value=""]')).to_have_attribute('disabled', '')
            close_panel(page)
            initial = save()
            lever, = initial['document']['decorations']
            door, = initial['document']['doors']
            assert lever['lever'] == {'state': 'off'} and 'blueprint' not in lever, lever
            assert door['state'] == 'locked', door
            records.append({'case': 'visible-object-behavior-control-creates-deactivated-lever'})

            def open_editor(kind, identifier):
                builder_tool(page, 'select')
                close_panel(page)
                page.locator(f'[data-builder-{kind}] [data-object-id="{identifier}"]').dblclick()
                modal = page.locator('[data-smart-object-modal]')
                expect(modal).to_be_visible()
                return modal

            def add_node(modal, kind):
                modal.locator('[data-blueprint-add]').click()
                modal.locator(f'[data-blueprint-pick-type={kind}]').click()
                modal.locator('[data-blueprint-fit]').click()
                return modal.locator(f'[data-blueprint-type={kind}]')

            def connect(modal, source, target):
                modal.locator('[data-blueprint-fit]').click()
                source.click()
                target.click()

            def choose_event(modal, key):
                target = modal.locator(f'[data-blueprint-event="{key}"]')
                if not target.is_visible():
                    modal.locator('[data-blueprint-state-events] summary').click()
                target.click()

            modal = open_editor('decorations', lever['id'])
            expect(modal.locator('[data-blueprint-state-port]')).to_have_count(0)
            expect(modal.locator('[data-blueprint-event-port]')).to_have_count(3)
            expect(modal.locator('[data-blueprint-event]')).to_have_count(9)
            expect(modal.locator('[data-blueprint-instance-name]')).to_have_text('Lever 1')
            choose_event(modal, 'enter:on')
            modal.locator('[data-blueprint-appearance-state]').select_option('on')
            modal.locator('[data-blueprint-appearance]').select_option('asset')
            options = modal.locator('[data-blueprint-asset] option').evaluate_all('rows => rows.map(row => row.value)')
            assert off_asset in options and on_asset in options and door_asset not in options, options
            modal.locator('[data-blueprint-asset]').select_option(on_asset)
            reference = add_node(modal, 'reference')
            expect(reference.locator('[data-blueprint-param=targetId]')).to_have_value(door['id'])
            action = add_node(modal, 'state')
            connect(modal, reference.locator('[data-blueprint-data-output=door]'),
                    action.locator('[data-blueprint-data-input=target]'))
            action = modal.locator('[data-blueprint-type=state]')
            action.locator('[data-blueprint-param=targetState]').select_option('open')
            action = modal.locator('[data-blueprint-type=state]')
            action.locator('[data-blueprint-param=players]').select_option('true')
            connect(modal, modal.locator('[data-blueprint-state-port=on]'),
                    action.locator('[data-blueprint-input]'))
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(2)
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator('[data-blueprint-trace]')).to_contain_text('Door 1')
            assert page.request.get(api + '/projects/' + initial['id']).json()['project']['document'] == initial['document']
            page.screenshot(path=str(output / 'lever-connected-desktop.png'))
            modal.locator('[data-blueprint-save]').click()
            edited = save()
            blueprint = edited['document']['decorations'][0]['blueprint']
            assert blueprint['version'] == 2 and blueprint['kind'] == 'lever', blueprint
            assert blueprint['states']['on'] == {'appearance': 'asset', 'assetId': on_asset}, blueprint
            graph = blueprint['graphs']['enter:on']
            state_node, = [node for node in graph['nodes'] if node['type'] == 'state']
            assert state_node['targetState'] == 'open' and state_node['players'] is True, graph
            records.append({'case': 'lever-alternate-decoration-image-reference-and-authorized-door-action-save-with-dry-simulation'})

            page.reload()
            wait_ready(page)
            modal = open_editor('decorations', lever['id'])
            choose_event(modal, 'enter:on')
            modal.locator('[data-blueprint-appearance-state]').select_option('on')
            expect(modal.locator('[data-blueprint-asset]')).to_have_value(on_asset)
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(2)
            modal.locator('[data-blueprint-close]').click()
            assert save()['document'] == edited['document']

            # The existing door editor can pick the new element kind on the map.
            # Cancel the draft so this inspection cannot affect the playable chain.
            modal = open_editor('doors', door['id'])
            reference = add_node(modal, 'reference')
            expect(reference.locator('[data-blueprint-param=targetId]')).to_have_value(lever['id'])
            reference.locator('[data-blueprint-pick-map=elements]').click()
            expect(modal).to_be_hidden()
            page.mouse.click(*position(13, 9))
            expect(modal).to_be_visible()
            expect(modal.locator('[data-blueprint-type=reference] [data-blueprint-param=targetId]')).to_have_value(lever['id'])
            modal.locator('[data-blueprint-cancel]').click()
            assert save()['document'] == edited['document']
            records.append({'case': 'door-reference-can-pick-lever-on-builder-map-and-cancel-keeps-saved-project'})

            localized = {'en': ('Deactivated', 'Activated'), 'pt-BR': ('Desativada', 'Ativada'),
                         'es': ('Desactivada', 'Activada')}
            for locale, labels in localized.items():
                change_locale(page, locale, campaign)
                for width, height in ((1440, 900), (390, 844)):
                    page.set_viewport_size({'width': width, 'height': height})
                    page.goto(builder + '?project=' + edited['id'])
                    wait_ready(page)
                    modal = open_editor('decorations', lever['id'])
                    expect(modal.locator('[data-blueprint-event]')).to_have_count(9)
                    for state, label in zip(('off', 'on'), labels):
                        expect(modal.locator(f'[data-blueprint-appearance-state] option[value={state}]')).to_have_text(label)
                    choose_event(modal, 'enter:on')
                    modal.locator('[data-blueprint-appearance-state]').select_option('on')
                    modal.locator('[data-blueprint-event-port="enter:on"]').focus()
                    page.keyboard.press('Enter')
                    expect(modal.locator('[data-blueprint-asset]')).to_have_value(on_asset)
                    modal.locator('[data-blueprint-fit]').click()
                    metrics = modal.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'lever-{locale}-{width}.png'))
                    for _ in range(18):
                        page.keyboard.press('Tab')
                        assert modal.evaluate('element => element.closest("[role=dialog]").contains(document.activeElement)')
                    page.keyboard.press('Escape')
                    expect(modal).to_have_count(0)
                    records.append({'case': 'localized-responsive-lever-modal-with-long-asset-labels-and-keyboard-focus',
                                    'locale': locale, 'width': width, 'metrics': metrics})

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(builder + '?project=' + edited['id'])
            wait_ready(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            project = page.request.get(api + '/projects/' + edited['id']).json()['project']
            scene_id = project['sceneId']

            def native_command(area, action, data):
                return page.evaluate("""args => gravewrightRealtime.mapCommand('objects', {
                  mapId: args.scene, area: args.area, action: args.action, data: args.data})""",
                                     {'scene': scene_id, 'area': area, 'action': action, 'data': data})

            native_command('lighting', 'update', {'mode': 'none', 'darkness': 0, 'lights_out': False})
            page.evaluate("""args => gravewrightRealtime.mapCommand('update', {
              mapId: args.scene, version: args.version, settings: {visibility:'players'}})""",
                          {'scene': scene_id, 'version': project['sceneVersion']})
            page.evaluate("scene => gravewrightRealtime.mapCommand('activate', {mapId: scene})", scene_id)
            player_context = browser.new_context(base_url=base, viewport={'width': 1200, 'height': 800})
            player_context.add_cookies([{**seed['sessions']['player'], 'url': base}])
            player_page = player_context.new_page()
            observe(player_page)
            player_page.goto(f'{base}/game/{campaign}')
            player_page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(player_page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            native = page.request.get(f'/api/maps/{scene_id}/state').json()
            native_lever, = [image for image in native['images'] if image.get('lever')]
            native_door, = [wall for wall in native['walls'] if wall['kind'] == 'door']
            assert native_lever['blueprint']['kind'] == 'lever', native_lever

            def state(target=player_page):
                return target.request.get(f'/api/maps/{scene_id}/state').json()

            def public_lever(document):
                return next(image for image in document['images'] if image['id'] == native_lever['id'])

            public = public_lever(state())
            assert public['lever']['state'] == 'off' and 'blueprint' not in public, public
            assert player_page.request.get(f'/game/map-assets/{on_asset}').status == 404
            assert player_page.request.get(f'/api/maps/{scene_id}/automation').status == 404
            expect(player_page.locator('#automation-log-window')).to_have_count(0)

            def screen_point(target):
                return target.evaluate("""image => {
                  const surface = document.querySelector('.game-board__surface').getBoundingClientRect();
                  const view = gravewrightMaps.board.viewport();
                  return {x:surface.x + view.x + image.x * view.scale,
                          y:surface.y + view.y + image.y * view.scale};
                }""", native_lever)

            def toggle(expected):
                point = screen_point(player_page)
                player_page.mouse.dblclick(point['x'], point['y'], delay=70)
                deadline = time.monotonic() + 12
                document = state()
                while public_lever(document)['lever']['state'] != expected and time.monotonic() < deadline:
                    player_page.wait_for_timeout(100)
                    document = state()
                assert public_lever(document)['lever']['state'] == expected, {'point': point, 'state': document}
                return document

            opened = toggle('on')
            assert next(wall for wall in opened['walls'] if wall['id'] == native_door['id'])['door_state'] == 'open', opened
            active = public_lever(opened)
            assert active['asset_id'] == on_asset and 'blueprint' not in active, active
            assert player_page.request.get(f'/game/map-assets/{on_asset}').ok
            assert player_page.request.get(f'/game/map-assets/{off_asset}').status == 404
            samples = []
            for target, device in ((page, 'gm'), (player_page, 'player')):
                deadline = time.monotonic() + 10
                color = (0, 0, 0)
                while time.monotonic() < deadline:
                    point = screen_point(target)
                    # Sample away from the selectable object's center handle.
                    point['x'] += 10
                    with Image.open(BytesIO(target.screenshot())) as screenshot:
                        color = screenshot.getpixel((round(point['x']), round(point['y'])))[:3]
                    if color[2] > color[0] + 70 and color[2] > color[1] + 35:
                        break
                    target.wait_for_timeout(100)
                assert color[2] > color[0] + 70 and color[2] > color[1] + 35, {'device': device, 'color': color, 'point': point}
                samples.append({'device': device, 'rgb': color})
            player_page.screenshot(path=str(output / 'lever-player-activated.png'))
            deactivated = toggle('off')
            assert public_lever(deactivated)['asset_id'] == off_asset, deactivated
            assert next(wall for wall in deactivated['walls'] if wall['id'] == native_door['id'])['door_state'] == 'open'
            records.append({'case': 'real-player-double-click-toggles-lever-and-authorized-chain-opens-locked-door', 'samples': samples})

            page.locator('.game-menubar__layer').nth(5).click()
            page.locator('[data-dock-tool=automation]').click()
            log = page.locator('.automation-log')
            expect(log).to_be_visible()
            expect(log.locator('[data-automation-run]')).to_have_count(2)
            log.locator('[data-automation-view=doors]').click()
            expect(log).to_contain_text('Lever 1')
            row = log.locator(f'[data-scene-controls-element="{native_lever["id"]}"]')
            expect(row).to_contain_text('Lever 1')
            expect(row).to_contain_text('Deactivated')
            row.click()
            expect(log.locator('[data-scene-controls-inspector] [data-scene-controls-action=interact]')).to_be_enabled()
            page.screenshot(path=str(output / 'lever-gm-automation.png'))
            records.append({'case': 'gm-only-automation-lists-native-lever-runs-and-state-without-player-blueprint-leak'})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            if player_context:
                player_context.close()
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    assert not [request for request in failed if request['error'] != 'net::ERR_ABORTED'], failed
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'failedRequests': failed, 'assets': 'Synthetic solid-color PNGs and silent WAV; no operator data.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
