"""Exercise capability-based events and explicit in-game object destruction.

Uses synthetic artwork and independent database, media, sessions and localhost
server from the Builder harness. The browser authors a destruction graph and
observes real player area crossings, safe rehearsal and atomic native removal.
"""
from __future__ import annotations

from copy import deepcopy
import json
import time
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_playtest import behavior, chain, node, persistent_snapshot
from map_builder_reference import close_panel, set_name, upload_asset, wait_ready


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    records, errors, dialogs = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        player_context = None

        def observe(target):
            target.on('pageerror', lambda error: errors.append(str(error)))
            target.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))

        observe(page)
        review = BuilderReview(page, campaign)

        def game(target=page):
            target.wait_for_url(f'{base}/game/{campaign}')
            target.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(target.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def resource(area, action, payload, target=page):
            return target.evaluate('a=>gravewrightRealtime.resourceCommand(a.area,a.action,a.data)',
                                   {'area': area, 'action': action, 'data': payload})

        def open_editor(identifier, kind='decorations'):
            builder_tool(page, 'select')
            builder_workspace(page)
            page.locator(f'[data-builder-{kind}] [data-object-id="{identifier}"]').dblclick()
            modal = page.locator('[data-smart-object-modal]')
            expect(modal).to_be_visible()
            return modal

        def card(modal, identifier):
            return modal.locator(f'[data-blueprint-node="{identifier}"]')

        def add_node(modal, kind, **params):
            before = set(modal.locator('[data-blueprint-node]').evaluate_all(
                'nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            modal.locator('[data-blueprint-add]').click()
            modal.locator(f'[data-blueprint-pick-type="{kind}"]').click()
            after = set(modal.locator('[data-blueprint-node]').evaluate_all(
                'nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            identifier, = after - before
            for name, value in params.items():
                control = card(modal, identifier).locator(f'[data-blueprint-param="{name}"]').first
                if control.evaluate('element=>element.tagName') == 'SELECT':
                    control.select_option(str(value).lower() if isinstance(value, bool) else str(value))
                else:
                    control.fill(str(value))
                    control.dispatch_event('change')
            return identifier

        def wire(modal, source, target, event=False):
            modal.locator('[data-blueprint-fit]').click()
            output_port = modal.locator(f'[data-blueprint-event-port="{source}"]') if event else (
                card(modal, source).locator('[data-blueprint-output="next"]'))
            output_port.click()
            card(modal, target).locator('[data-blueprint-input]').click()

        try:
            page.goto(f'/game/{campaign}')
            game()
            actor = resource('actors', 'actor.create', {'name': 'Synthetic lifecycle area explorer'})
            resource('actors', 'actor.permissions', {'id': actor['id'], 'permissions': {'default': 'owner'}})
            page.goto(review.builder)
            wait_ready(page)
            set_name(page, 'Synthetic capability-based lifecycle events')
            asset = upload_asset(page, 'decoration', 'Synthetic destructible mechanism.png',
                                 harness.artwork('#b97935'))['id']
            builder_tool(page, 'decoration')
            page.locator('[data-builder-brush-material]').select_option(asset)
            review.stroke((18, 14), (20, 16))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=behavior]').select_option('lever')
            close_panel(page)
            builder_tool(page, 'light')
            review.stroke((16, 10), (16, 10))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=enabled]').uncheck()
            close_panel(page)
            builder_tool(page, 'region')
            review.stroke((10, 8), (14, 12))
            initial = review.save()
            owner_id = initial['document']['decorations'][0]['id']
            lamp_id = initial['document']['lights'][0]['id']
            area_id = initial['document']['regions'][0]['id']

            modal = open_editor(owner_id)
            for key in ('interact', 'change', 'destroy'):
                expect(modal.locator(f'[data-blueprint-event-port="{key}"]')).to_be_visible()
            expect(modal.locator('[data-blueprint-event-port^="presence:"]')).to_have_count(0)
            modal.locator('[data-blueprint-event="destroy"]').click()
            lamp = add_node(modal, 'light', targetId=lamp_id, enabled=True)
            mark = add_node(modal, 'setVariable', scope='scene', valueType='boolean', name='Destroyed', value=True)
            signal = add_node(modal, 'emitEvent', scope='scene', name='DestructionWitness')
            wire(modal, 'destroy', lamp, event=True)
            wire(modal, lamp, mark)
            wire(modal, mark, signal)
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(3)
            modal.locator('[data-blueprint-undo]').click()
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(2)
            modal.locator('[data-blueprint-redo]').click()
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(3)
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator('[data-blueprint-trace]')).to_contain_text('Destroyed')
            assert review.project(initial['id'])['document'] == initial['document']
            modal.locator('[data-blueprint-save]').click()
            authored = review.save()
            records.append({'case': 'lever-events-follow-capabilities-and-author-destroy-effects-with-undo-redo-and-local-simulation'})

            document = deepcopy(authored['document'])
            layer = document['layers'][0]['id']
            bad_id, paused_id, witness_id = (str(uuid4()) for _ in range(3))
            for identifier, x, graphs in (
                (bad_id, 23, {
                    'destroy': chain('destroy', [
                        node('badLamp', 'light', targetId=lamp_id, enabled=False),
                        node('badMark', 'setVariable', scope='scene', valueType='boolean', name='FailedDestroy', value=True),
                        node('badLoop', 'emitEvent', scope='element', name='DestroyLoop')]),
                    'signal:DestroyLoop': chain('signal:DestroyLoop', [
                        node('loop', 'emitEvent', scope='element', name='DestroyLoop')]),
                }),
                (paused_id, 28, {'destroy': chain('destroy', [
                    node('pausedMark', 'setVariable', scope='scene', valueType='boolean', name='PausedDestroy', value=True)])}),
            ):
                document['decorations'].append({
                    'id': identifier, 'layerId': layer, 'assetId': asset, 'x': x, 'y': 14,
                    'width': 2, 'height': 2, 'rotation': 0, 'lever': {'state': 'off'},
                    'blueprint': behavior('lever', graphs),
                })
            document['doors'] = [{
                'id': witness_id, 'layerId': layer, 'assetId': None,
                'x1': 24, 'y1': 6, 'x2': 26, 'y2': 6, 'thickness': .2, 'state': 'closed',
                'blueprint': behavior('door', {'signal:DestructionWitness': chain('signal:DestructionWitness', [
                    node('witness', 'setVariable', scope='scene', name='Witnessed', valueType='boolean', value=True)])}),
            }]
            area = document['regions'][0]
            area['name'] = 'Synthetic lifecycle area with a deliberately long authored name'
            area['blueprint'] = behavior('region', {
                'presence:enter': chain('presence:enter', [
                    node('arrival', 'setVariable', scope='scene', name='AreaEntered', valueType='boolean', value=True)]),
                'presence:exit': chain('presence:exit', [
                    node('departure', 'setVariable', scope='scene', name='AreaExited', valueType='boolean', value=True)]),
                'change': chain('change', [
                    node('occupancy', 'setVariable', scope='scene', name='OccupancyChanged', valueType='boolean', value=True)]),
                'signal:AreaSignal': chain('signal:AreaSignal', [
                    node('areaSignal', 'setVariable', scope='element', name='AreaSignalReceived', valueType='boolean', value=True)]),
            })
            authored = review.store(authored['id'], authored['version'], authored['folderId'], document)

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width, height in ((1440, 900), (390, 844)):
                    page.set_viewport_size({'width': width, 'height': height})
                    page.goto(review.builder + '?project=' + authored['id'])
                    wait_ready(page)
                    modal = open_editor(area_id, 'regions')
                    expect(modal.locator('[data-blueprint-event-port="interact"]')).to_have_count(0)
                    for key, code in (('presence:enter', 'onAreaEnter'), ('presence:exit', 'onAreaExited'),
                                      ('change', 'onChange'), ('destroy', 'onDestroy')):
                        port = modal.locator(f'[data-blueprint-event-port="{key}"]')
                        expect(port).to_be_visible()
                        expect(port).to_contain_text(code)
                    modal.locator('[data-blueprint-event="presence:enter"]').click()
                    expect(modal.locator('[data-blueprint-type="event"]')).to_have_count(0)
                    modal.locator('[data-blueprint-event="signal:AreaSignal"]').click()
                    signal_port = modal.locator('[data-blueprint-event-port="signal:AreaSignal"]')
                    expect(signal_port).to_be_visible()
                    expect(signal_port).to_contain_text('onSignal')
                    expect(modal.locator('[data-blueprint-type="event"]')).to_have_count(0)
                    name = modal.locator('[data-blueprint-instance-name]')
                    expect(name).to_have_attribute('title', area['name'])
                    name_bounds = name.evaluate('''element=>{
                      const text=element.getBoundingClientRect(),card=element.closest('[data-blueprint-instance]').getBoundingClientRect();
                      return {left:text.left,right:text.right,cardLeft:card.left,cardRight:card.right};
                    }''')
                    assert name_bounds['left'] >= name_bounds['cardLeft'] - 1, name_bounds
                    assert name_bounds['right'] <= name_bounds['cardRight'] + 1, name_bounds
                    metrics = modal.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'lifecycle-events-{locale}-{width}.png'))
                    modal.locator('[data-blueprint-cancel]').click()
                    assert review.project(authored['id'])['document'] == authored['document']
                    records.append({'case': 'localized-region-and-signal-events-share-instance-root-with-capability-correct-ports',
                                    'locale': locale, 'width': width, 'metrics': metrics})

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(review.builder + '?project=' + authored['id'])
            wait_ready(page)
            before = persistent_snapshot(output)
            page.locator('[data-builder-test]').click()
            rehearsal = page.locator('[data-playtest]')
            rehearsal.locator('[data-playtest-element]').select_option(owner_id)
            rehearsal.locator('[data-playtest-event]').select_option('destroy')
            with page.expect_response(lambda response: response.url.endswith('/map-builder/test')) as tested:
                rehearsal.locator('[data-playtest-run]').click()
            assert tested.value.ok, tested.value.text()
            prediction = tested.value.json()
            assert prediction['dryRun'] is True and prediction['ok'] is True, prediction
            removed = next(row for row in prediction['changes']['elements'] if row.get('sourceId') == owner_id)
            assert removed['before'] and removed['after'] is None, removed
            expect(rehearsal.locator('[data-playtest-removed]')).to_have_count(1)
            assert prediction['changes']['sceneVariables']['after']['Witnessed']['value'] is True, prediction
            assert persistent_snapshot(output) == before
            rehearsal.locator('[data-playtest-close]').click()
            assert review.project(authored['id'])['document'] == authored['document']
            records.append({'case': 'destroy-rehearsal-predicts-removal-and-cross-element-effects-with-complete-rollback'})

            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            game()
            project = review.project(authored['id'])
            scene = project['sceneId']

            def state(target=page):
                response = target.request.get(f'/api/maps/{scene}/state')
                assert response.ok, response.text()
                return response.json()

            def log():
                response = page.request.get(f'/api/maps/{scene}/automation')
                assert response.ok, response.text()
                return response.json()

            def command(area, action, data, target=page):
                return target.evaluate('''async a=>{try{return {ok:true,result:await gravewrightRealtime.mapCommand('objects',{
                  mapId:a.scene,area:a.area,action:a.action,data:a.data})}}catch(error){return {ok:false,message:error.message}}}''',
                                       {'scene': scene, 'area': area, 'action': action, 'data': data})

            def find_image(marker):
                return next(row for row in state()['images'] if any(
                    value.get('name') == marker for graph in row.get('blueprint', {}).get('graphs', {}).values()
                    for value in graph['nodes']))

            good, bad, paused = (find_image(marker) for marker in ('Destroyed', 'FailedDestroy', 'PausedDestroy'))
            native_area, = state()['zones']
            native_lamp, = state()['lights']
            page.evaluate('''a=>gravewrightRealtime.mapCommand('update',{
              mapId:a.scene,version:a.version,settings:{visibility:'players'}})''',
                          {'scene': scene, 'version': project['sceneVersion']})
            page.evaluate("scene=>gravewrightRealtime.mapCommand('activate',{mapId:scene})", scene)
            first = resource('tokens', 'place', {'mapId': scene, 'actorId': actor['id'], 'gridX': 3, 'gridY': 3})['createdIds'][0]
            second = resource('tokens', 'duplicate', {'mapId': scene, 'tokenIds': [first]})['createdIds'][0]
            player_context = browser.new_context(base_url=base, viewport={'width': 1200, 'height': 800})
            player_context.add_cookies([{**seed['sessions']['player'], 'url': base}])
            player = player_context.new_page()
            observe(player)
            player.goto(f'/game/{campaign}')
            game(player)
            assert state(player)['zones'] == []

            def move(identifier, x, y):
                tokens = player.request.get(f'/api/containers/{campaign}/maps/{scene}/tokens').json()['tokens']
                token = next(row for row in tokens if row['id'] == identifier)
                return resource('tokens', 'move', {'mapId': scene, 'id': identifier,
                    'expectedVersion': token['version'], 'gridX': x, 'gridY': y}, player)

            def area_events():
                return [{**event, 'context': run.get('context', {})} for run in reversed(log()['runs']) for event in run['events']
                        if event.get('doorId', run['doorId']) == native_area['id']]

            for identifier, x, y in ((first, 11, 9), (second, 12, 10), (first, 3, 3), (second, 3, 4)):
                move(identifier, x, y)
            events = area_events()
            assert sum(event['event'] == 'presence:enter' for event in events) == 2, events
            assert sum(event['event'] == 'presence:exit' for event in events) == 2, events
            assert sum(event['event'] == 'change' for event in events) == 2, events
            for event in events:
                if event['event'].startswith('presence:'):
                    assert event['context']['tokenId'] in (first, second), event
            assert log()['variables']['scene']['AreaEntered']['value'] is True
            assert log()['variables']['scene']['AreaExited']['value'] is True
            records.append({'case': 'real-player-area-events-run-per-token-and-change-only-on-first-entry-last-exit-with-private-region'})

            refused = command('images', 'delete', {'placement_id': good['id'], 'expected_version': good['version']}, player)
            assert not refused['ok']
            assert any(row['id'] == good['id'] for row in state()['images'])
            records.append({'case': 'player-cannot-delete-smart-element-or-request-its-destruction-event'})

            assert command('automation', 'pause', {'paused': True})['ok']
            assert command('images', 'delete', {'placement_id': paused['id'], 'expected_version': paused['version']})['ok']
            assert all(row['id'] != paused['id'] for row in state()['images'])
            assert 'PausedDestroy' not in log()['variables']['scene']
            assert command('automation', 'pause', {'paused': False})['ok']
            records.append({'case': 'paused-automation-allows-explicit-removal-without-running-destroy-effects'})

            # A repeated signal is a valid authored graph whose execution fails
            # the bounded world chain. Removal and its earlier effects roll back.
            before_lamp = next(row for row in state()['lights'] if row['id'] == native_lamp['id'])
            failed = command('images', 'delete', {'placement_id': bad['id'], 'expected_version': bad['version']})
            assert not failed['ok'], failed
            assert any(row['id'] == bad['id'] for row in state()['images'])
            assert next(row for row in state()['lights'] if row['id'] == native_lamp['id']) == before_lamp
            assert 'FailedDestroy' not in log()['variables']['scene']
            records.append({'case': 'failing-destroy-chain-rolls-back-owner-removal-light-and-scene-variable'})

            request_id = str(uuid4())
            payload = {'mapId': scene, 'area': 'images', 'action': 'delete',
                       'data': {'placement_id': good['id'], 'expected_version': good['version']}}

            def remove_with_receipt():
                return page.evaluate('''a=>new Promise((resolve,reject)=>{
                  const stop=()=>{clearTimeout(timer);removeEventListener('gravewright:api-event',receive)};
                  const receive=({detail})=>{if(detail.payload?.requestId!==a.id||!['maps.ack','maps.error'].includes(detail.type))return;
                    stop();detail.type==='maps.ack'?resolve(detail.payload.result):reject(Error(detail.payload.message))};
                  const timer=setTimeout(()=>{stop();reject(Error('Lifecycle receipt timed out'))},15000);
                  addEventListener('gravewright:api-event',receive);
                  if(!gravewrightRealtime.tableTool('maps.command',{requestId:a.id,action:'objects',data:a.data})){
                    stop();reject(Error('Table disconnected'))}
                })''', {'id': request_id, 'data': payload})

            accepted = remove_with_receipt()
            assert all(row['id'] != good['id'] for row in state()['images'])
            after_lamp = next(row for row in state()['lights'] if row['id'] == native_lamp['id'])
            assert after_lamp['enabled'] is True
            after_log = log()
            assert after_log['variables']['scene']['Destroyed']['value'] is True
            assert after_log['variables']['scene']['Witnessed']['value'] is True
            own_events = [event for run in after_log['runs'] for event in run['events']
                          if event.get('doorId', run['doorId']) == good['id']]
            assert sum(event['event'] == 'destroy' for event in own_events) == 1, own_events
            assert remove_with_receipt() == accepted
            assert next(row for row in state()['lights'] if row['id'] == native_lamp['id']) == after_lamp
            assert log()['runs'] == after_log['runs']
            assert review.project(authored['id'])['document'] == authored['document']
            page.screenshot(path=str(output / 'lifecycle-native-after-destruction.png'))
            records.append({'case': 'explicit-native-removal-runs-destroy-once-delivers-scene-signal-and-reuses-receipt-with-source-preserved'})
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
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Synthetic solid-color PNG and silent WAV; no operator campaign data.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
