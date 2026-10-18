"""Publish dynamic artwork and exercise private presentations and token transport.

All geometry, actors, documents, assets, sessions and server state are disposable.
The fixture never opens the operator database or modifies installation settings.
"""
from __future__ import annotations

from copy import deepcopy
from io import BytesIO
import json
import time
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import set_name, upload_asset, wait_ready


def node(identifier, kind, **values):
    return {'id': identifier, 'type': kind, 'x': 50, 'y': 80, **values}


def chain(event, actions, values=(), data=()):
    nodes = [node('event', 'event', event=event), *actions, *values]
    for index, value in enumerate(nodes): value.update(x=40 + index * 360, y=100)
    path = ['event', *[value['id'] for value in actions]]
    edges = [{'kind': 'execution', 'from': before, 'to': after, 'output': 'next'} for before, after in zip(path, path[1:])]
    edges += [{'kind': 'data', 'from': before, 'output': output, 'to': after, 'input': port} for before, output, after, port in data]
    return {'nodes': nodes, 'edges': edges}


def blueprint(kind, graphs):
    states = ['off', 'on'] if kind == 'lever' else ['empty', 'occupied']
    return {'version': 2, 'kind': kind, 'states': {state: {'appearance': 'inherit'} for state in states}, 'graphs': graphs}


def check_browser(base, seed, output, executable):
    from PIL import Image
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']; builder = f'/game/{campaign}/map-builder'
    records, errors, dialogs = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page(); guests = []

        def observe(target):
            target.on('pageerror', lambda error: errors.append(str(error)))
            target.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))

        observe(page); review = BuilderReview(page, campaign)

        def game(target=page):
            target.wait_for_url(f'{base}/game/{campaign}')
            target.wait_for_function('!!gravewrightMaps?.current && !!gravewrightRealtime')
            expect(target.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            target.wait_for_function('!!gravewrightMaps.board?.viewport && Number.isFinite(gravewrightMaps.board.viewport()?.scale)')

        def resource(area, action, data, target=page):
            return target.evaluate('a=>gravewrightRealtime.resourceCommand(a.area,a.action,a.data)', {'area': area, 'action': action, 'data': data})

        def journal(action, data):
            return page.evaluate('a=>gravewrightRealtime.journalCommand(a.action,a.data)', {'action': action, 'data': data})

        def select(identifier, kind):
            builder_tool(page, 'select'); builder_workspace(page)
            shape = page.locator(f'[data-builder-{kind}] [data-object-id="{identifier}"]')
            box = shape.bounding_box(); page.mouse.click(box['x'] + box['width'] * .2, box['y'] + box['height'] * .2)
            builder_sidebar(page, 'selection')

        try:
            page.goto(f'/game/{campaign}'); game()
            actor = resource('actors', 'actor.create', {'name': 'Synthetic traveler'})
            resource('actors', 'actor.permissions', {'id': actor['id'], 'permissions': {'default': 'owner'}})
            public = journal('create', {'title': 'Synthetic readable handout'})
            private = journal('create', {'title': 'Synthetic private handout'})
            page.goto(builder); wait_ready(page); set_name(page, 'Synthetic dynamic world')
            red = upload_asset(page, 'floor', 'Synthetic red floor.png', harness.artwork('#b02020'))['id']
            green = upload_asset(page, 'floor', 'Synthetic green underlay.png', harness.artwork('#3b8e4a'))['id']
            blue = upload_asset(page, 'floor', 'Synthetic blue replacement.png', harness.artwork('#2050d0'))['id']
            wall_art = upload_asset(page, 'wall', 'Synthetic wall.png', harness.artwork('#888888'))['id']
            lever_art = upload_asset(page, 'decoration', 'Synthetic surface lever.png', harness.artwork('#bb7838'))['id']
            initial = review.save(); document = deepcopy(initial['document']); layer = document['layers'][0]['id']
            floor_id, wall_id, lever_id, source_id, destination_id = [str(uuid4()) for _ in range(5)]
            document['background'] = '#112233'
            document['floors'] = [
                {'id': str(uuid4()), 'layerId': layer, 'assetId': green, 'x': 3, 'y': 3, 'width': 8, 'height': 8, 'rotation': 0},
                {'id': floor_id, 'layerId': layer, 'assetId': red, 'x': 4, 'y': 4, 'width': 6, 'height': 6, 'rotation': 90,
                 'paint': {'color': None, 'opacity': .7}},
                {'id': str(uuid4()), 'layerId': layer, 'assetId': blue, 'x': 8, 'y': 4, 'width': 2, 'height': 6, 'rotation': 0,
                 'paint': {'color': None, 'opacity': .4}},
                {'id': str(uuid4()), 'layerId': layer, 'assetId': None, 'x': 8, 'y': 8, 'width': 2, 'height': 2, 'rotation': 0,
                 'brush': {'operation': 'erase', 'points': [[.5, .5, 1]], 'radius': [.5, .5], 'hardness': 1}},
            ]
            document['walls'] = [{'id': wall_id, 'layerId': layer, 'assetId': wall_art, 'x1': 4, 'y1': 4, 'x2': 10, 'y2': 4, 'thickness': .4}]
            document['doors'] = [{'id': str(uuid4()), 'layerId': layer, 'assetId': None, 'x1': 7, 'y1': 4, 'x2': 8, 'y2': 4, 'thickness': .4, 'state': 'closed'}]
            document['decorations'] = [{'id': lever_id, 'layerId': layer, 'assetId': lever_art, 'x': 16, 'y': 18, 'width': 2, 'height': 2,
                                        'rotation': 0, 'lever': {'state': 'off'}}]
            document['regions'] = [{'id': identifier, 'layerId': layer, 'x': x, 'y': 8, 'width': 3, 'height': 3,
                                     'name': name, 'enabled': True} for identifier, x, name in (
                (source_id, 12, 'Synthetic departure'), (destination_id, 22, 'Synthetic arrival'))]
            saved = review.store(initial['id'], initial['version'], initial['folderId'], document)
            page.goto(builder + '?project=' + saved['id']); wait_ready(page)
            for identifier, kind in ((floor_id, 'floors'), (wall_id, 'walls')):
                select(identifier, kind); expect(page.locator('[data-builder-property=dynamic]')).not_to_be_checked()
                page.locator('[data-builder-property=dynamic]').check()
            promoted = review.save()
            assert all(next(row for row in promoted['document'][kind] if row['id'] == identifier)['dynamic']
                       for identifier, kind in ((floor_id, 'floors'), (wall_id, 'walls')))
            records.append({'case': 'real-selection-promotes-floor-and-wall-with-optional-dynamic-checkboxes'})

            page.goto(f'/game/{campaign}'); game()
            users = page.request.get(f'/api/containers/{campaign}/map-builder').json()['users']
            player_id = next(user['id'] for user in users if user['name'] == 'Player')
            journal('access', {'journal_id': public['journal_id'], 'target_user_id': player_id, 'access_level': 'read'})
            authored = deepcopy(promoted['document'])
            targets = node('targets', 'elementGroup', name='Synthetic surfaces', memberType='element', targetIds=[floor_id, wall_id])
            authored['decorations'][0]['blueprint'] = blueprint('lever', {
                'enter:on': chain('enter:on', [node('hide', 'setVisibility', visible=False)], [targets], [('targets', 'targets', 'hide', 'target')]),
                'enter:off': chain('enter:off', [node('show', 'setVisibility', visible=True), node('paint', 'setAppearance', assetId=blue)],
                                   [deepcopy(targets)], [('targets', 'targets', 'show', 'target'), ('targets', 'targets', 'paint', 'target')]),
            })
            message = '<img src=x onerror=window.__unsafe=1> Mensagem de chegada ' + '\u96ea' * 20
            authored['regions'][0]['blueprint'] = blueprint('region', {'enter:occupied': chain('enter:occupied', [
                node('message', 'showMessage', text=message, audience={'scope': 'trigger'}),
                node('public', 'showHandout', journalId=public['journal_id'], audience={'scope': 'trigger'}),
                node('private', 'showHandout', journalId=private['journal_id'], audience={'scope': 'trigger'}),
                node('focus', 'cameraFocus', focusX=24, focusY=10, audience={'scope': 'trigger'}),
                node('transport', 'teleport', destinationId=destination_id),
            ])})
            authored['regions'][1]['blueprint'] = blueprint('region', {'enter:occupied': chain('enter:occupied', [node('return', 'teleport', destinationId=source_id)])})
            saved = review.store(promoted['id'], promoted['version'], promoted['folderId'], authored)
            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    page.goto(builder + '?project=' + saved['id']); wait_ready(page)
                    select(source_id, 'regions'); page.locator('[data-builder-edit-behavior]').click()
                    modal = page.locator('[data-smart-object-modal]'); expect(modal).to_be_visible()
                    modal.locator('[data-blueprint-state-port=occupied]').click(); modal.locator('[data-blueprint-fit]').click()
                    expect(modal.locator('[data-blueprint-param=text]')).to_have_value(message)
                    modal.locator('[data-blueprint-simulate]').click()
                    expect(modal.locator('[data-blueprint-trace]')).to_contain_text(message)
                    metrics = modal.evaluate(MEASURE); assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'world-editor-{locale}-{width}.png'))
                    page.keyboard.press('Escape'); expect(modal).to_have_count(0)
                    assert review.project(saved['id'])['document'] == authored
                    records.append({'case': 'localized-world-action-editor-preview-is-local-only', 'locale': locale, 'width': width, 'metrics': metrics})
            change_locale(page, 'en', campaign); page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(builder + '?project=' + saved['id']); wait_ready(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text(); game()
            project = review.project(saved['id']); scene = project['sceneId']; cell = authored['cellSize']

            def command(area, action, data, target=page):
                return target.evaluate('a=>gravewrightRealtime.mapCommand("objects",{mapId:a.scene,area:a.area,action:a.action,data:a.data})',
                                       {'scene': scene, 'area': area, 'action': action, 'data': data})

            def state(target=page):
                response = target.request.get(f'/api/maps/{scene}/state'); assert response.ok, response.text()
                return response.json()

            def tokens(target=page):
                return target.request.get(f'/api/containers/{campaign}/maps/{scene}/tokens').json()['tokens']

            command('lighting', 'update', {'mode': 'none', 'darkness': 0, 'lights_out': False})
            page.evaluate('a=>gravewrightRealtime.mapCommand("update",{mapId:a.scene,version:a.version,settings:{visibility:"players"}})',
                          {'scene': scene, 'version': project['sceneVersion']})
            page.evaluate('scene=>gravewrightRealtime.mapCommand("activate",{mapId:scene})', scene)
            native = state(); surfaces = {row['surface']['kind']: row for row in native['images'] if row.get('surface')}
            lever = next(row for row in native['images'] if row.get('lever'))
            before_walls = native['walls']
            created = resource('tokens', 'place', {'mapId': scene, 'actorId': actor['id'], 'gridX': 11, 'gridY': 12})
            token_id = created['createdIds'][0]
            guest = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900}); guests.append(guest)
            guest.add_cookies([{**seed['sessions']['player'], 'url': base}])
            player = guest.new_page(); observe(player); player.goto(f'/game/{campaign}'); game(player)

            def pixel(x, y, expected):
                deadline, color = time.monotonic() + 8, None
                while time.monotonic() < deadline:
                    point = player.evaluate('''p=>{const frame=document.querySelector('.game-table__scene-frame').getBoundingClientRect(),v=gravewrightMaps.board.viewport();
                      return [frame.x+v.x+p[0]*v.scale,frame.y+v.y+p[1]*v.scale];}''', [x * cell, y * cell])
                    with Image.open(BytesIO(player.screenshot())) as image: color = image.convert('RGB').getpixel(tuple(round(value) for value in point))
                    if max(abs(actual - wanted) for actual, wanted in zip(color, expected)) <= 5: return color
                    player.wait_for_timeout(100)
                raise AssertionError({'point': [x, y], 'color': color, 'expected': expected})

            pixel(5.5, 6.5, (141, 65, 45)); pixel(5.5, 4.08, (136, 136, 136)); pixel(9.1, 9.1, (17, 34, 51))
            player.screenshot(path=str(output / 'world-native-initial.png'))
            records.append({'case': 'native-renderer-shows-translucent-dynamic-floor-wall-and-composed-layer-eraser'})

            control = player.locator(f'[data-smart-image-id="{lever["id"]}"][data-smart-image-action=interact]')
            control.focus(); control.press('Enter'); expect(control).to_have_attribute('aria-pressed', 'true')
            pixel(5.5, 6.5, (59, 142, 74)); pixel(5.5, 4.08, (59, 142, 74)); pixel(9.1, 9.1, (17, 34, 51))
            assert state()['walls'] == before_walls
            player.screenshot(path=str(output / 'world-native-hidden.png'))
            records.append({'case': 'player-hides-dynamic-floor-and-wall-without-old-baked-pixels-or-barrier-changes'})
            control.press('Enter'); expect(control).to_have_attribute('aria-pressed', 'false')
            pixel(5.5, 6.5, (40, 99, 168)); pixel(5.5, 4.08, (32, 80, 208)); pixel(9.1, 9.1, (17, 34, 51))
            assert all(row['surface'].get('materialId') == blue for row in state()['images'] if row.get('surface'))
            player.screenshot(path=str(output / 'world-native-material.png'))
            records.append({'case': 'group-set-appearance-retains-floor-alpha-wall-mask-world-scale-and-eraser'})

            def events():
                player.evaluate('''()=>{window.__worldEvents=[];window.__worldPings=[];
                  addEventListener('gravewright:api-event',({detail})=>{if(detail.type==='automation.presentation')__worldEvents.push(detail.payload)});
                  const ping=gravewrightMaps.board.ping.bind(gravewrightMaps.board);
                  gravewrightMaps.board.ping=(...args)=>{__worldPings.push(args);return ping(...args)};}''')

            events(); expect(player.locator('[data-automation-camera-preference]')).not_to_be_checked()
            receipt_payloads = {}

            def move(x, y, request_id=None):
                current = next(row for row in tokens(player) if row['id'] == token_id)
                payload = {'mapId': scene, 'id': token_id, 'expectedVersion': current['version'], 'gridX': x, 'gridY': y}
                if request_id is None: return resource('tokens', 'move', payload, player)
                payload = receipt_payloads.setdefault(request_id, payload)
                return player.evaluate('''a=>new Promise((resolve,reject)=>{
                  const done=()=>{clearTimeout(timer);removeEventListener('gravewright:api-event',receive)};
                  const receive=({detail})=>{if(detail.payload.requestId!==a.id||!['tokens.ack','tokens.error'].includes(detail.type))return;
                    done();detail.type==='tokens.ack'?resolve(detail.payload.result):reject(Error(detail.payload.message))};
                  const timer=setTimeout(()=>{done();reject(Error('Token receipt timed out'))},15000);
                  addEventListener('gravewright:api-event',receive);gravewrightRealtime.tableTool('tokens.command',{action:'move',requestId:a.id,data:a.payload});
                })''', {'id': request_id, 'payload': payload})

            request_id = str(uuid4()); move(12, 8, request_id)
            player.wait_for_function('window.__worldEvents.some(event=>event.type==="camera")')
            expected_token = next(row for row in tokens() if row['id'] == token_id)
            assert 22 <= expected_token['gridX'] < 25 and 8 <= expected_token['gridY'] < 11, expected_token
            message_modal = player.locator('[data-automation-presentation]'); expect(message_modal).to_be_visible()
            expect(message_modal.locator('p')).to_have_text(message); expect(message_modal.locator('img')).to_have_count(0)
            assert player.evaluate('window.__unsafe') is None
            assert player.evaluate('__worldPings.length') == 0
            assert not page.locator('[data-automation-presentation]').count()
            player.wait_for_function('''id=>window.__worldEvents.some(event=>event.type==='handout'&&event.journalId===id)''', arg=public['journal_id'])
            expect(player.locator('.journal-window [data-title]')).to_have_text('Synthetic readable handout')
            assert not any(event.get('journalId') == private['journal_id'] for event in player.evaluate('__worldEvents'))
            assert all(row['id'] != private['journal_id'] for row in player.request.get(f'/api/containers/{campaign}/journals').json()['journals'])
            player.screenshot(path=str(output / 'world-player-private-presentation.png'))
            records.append({'case': 'real-token-teleports-without-bounce-and-only-instigator-gets-safe-message-and-readable-handout-camera-off'})
            before_events = player.evaluate('__worldEvents.length')
            move(12, 8, request_id)
            assert next(row for row in tokens() if row['id'] == token_id)['version'] == expected_token['version']
            assert player.evaluate('__worldEvents.length') == before_events
            records.append({'case': 'retrying-token-request-does-not-repeat-teleport-or-presentation'})
            message_modal.locator('[data-presentation-close]').click()
            player.locator('.journal-window [data-action=close]').evaluate_all('nodes=>nodes.forEach(node=>node.click())')
            expect(player.locator('.journal-window')).to_have_count(0)
            player.locator('.game-menubar__logo').click(); player.locator('.house-menu__section').nth(2).click()
            player.locator('[data-automation-camera-preference]').check(); player.keyboard.press('Escape')
            player.reload(); game(player); expect(player.locator('[data-automation-camera-preference]')).to_be_checked()
            events(); pixel(5.5, 6.5, (40, 99, 168)); pixel(5.5, 4.08, (32, 80, 208))
            move(20, 12); move(12, 8)
            player.wait_for_function('window.__worldPings.length===1')
            assert player.evaluate('__worldPings[0][0]') == {'x': 24 * cell, 'y': 10 * cell}
            assert 22 <= next(row for row in tokens() if row['id'] == token_id)['gridX'] < 25
            records.append({'case': 'camera-opt-in-and-materials-survive-reload-and-transport-rearms-after-leaving-destination'})
            assert state(player)['zones'] == []
            assert 'arrivalGates' not in json.dumps(state(player))
            assert player.request.get(f'/api/maps/{scene}/automation').status == 404
            records.append({'case': 'arrival-gates-recipes-and-automation-state-remain-private'})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            if 'player' in locals(): player.screenshot(path=str(output / 'failure-player.png'), full_page=True)
            (output / 'progress.json').write_text(json.dumps({'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs}, indent=2, ensure_ascii=False), encoding='utf-8')
            raise
        finally:
            for guest in guests: guest.close()
            context.close(); browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Only synthetic artwork, actors, documents and disposable campaign state.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
