"""Test draft and native mechanisms without changing a real campaign.

The shared harness creates disposable sessions, database, media and modules.
Besides checking the public UI, each dry run compares read-only database and
media snapshots and observes a connected player for accidental notifications.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import sqlite3
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import close_panel, set_name, upload_asset, wait_ready


def node(identifier, kind, **values):
    return {'id': identifier, 'type': kind, 'x': 50, 'y': 80, **values}


def chain(event, actions, values=(), data=()):
    nodes = [node('event', 'event', event=event), *actions, *values]
    for index, value in enumerate(nodes):
        value.update(x=40 + index * 350, y=100)
    path = ['event', *[value['id'] for value in actions]]
    edges = [{'kind': 'execution', 'from': before, 'to': after, 'output': 'next'}
             for before, after in zip(path, path[1:])]
    edges += [{'kind': 'data', 'from': before, 'output': output, 'to': after, 'input': port}
              for before, output, after, port in data]
    return {'nodes': nodes, 'edges': edges}


def behavior(kind, graphs):
    states = {'door': ('closed', 'open', 'locked'), 'lever': ('off', 'on'),
              'region': ('empty', 'occupied')}[kind]
    return {'version': 2, 'kind': kind,
            'states': {state: {'appearance': 'inherit'} for state in states}, 'graphs': graphs}


def post(page, url, body):
    """Use the official CSRF endpoint and the authenticated public HTTP API."""
    return page.evaluate('''async args=>{
      const csrf=await(await fetch('/__gravewright/csrf')).json();
      const response=await fetch(args.url,{method:'POST',
        headers:{'Content-Type':'application/json',[csrf.header]:csrf.token},
        body:JSON.stringify(args.body)});
      const text=await response.text();let body;
      try{body=JSON.parse(text);}catch{body={error:text.slice(0,120)};}
      return {status:response.status,body};
    }''', {'url': url, 'body': body})


def persistent_snapshot(output):
    """Read only this fixture's domain rows and hash its synthetic media."""
    fixture = output / 'fixture'
    with sqlite3.connect((fixture / 'review.sqlite3').as_uri() + '?mode=ro', uri=True) as database:
        tables = [row[0] for row in database.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            if row[0].startswith(('gravewright_maps_', 'gravewright_tokens_', 'gravewright_audio_',
                                  'gravewright_actors_'))]
        assert tables, 'Expected the disposable map domain tables'
        rows = {}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            rows[table] = sorted(database.execute(f'SELECT * FROM {quoted}').fetchall(), key=repr)
    media = {str(path.relative_to(fixture)): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in sorted((fixture / 'media').rglob('*')) if path.is_file()}
    return {'rows': rows, 'media': media}


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    records, errors, dialogs, guests = [], [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        context.add_init_script('''window.__playtestEvents=[];
          addEventListener('gravewright:api-event',event=>window.__playtestEvents.push(event.detail));''')
        page = context.new_page()

        def observe(target):
            target.on('pageerror', lambda error: errors.append(str(error)))
            target.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))

        observe(page)
        review = BuilderReview(page, campaign)

        def game(target=page):
            target.wait_for_url(f'{base}/game/{campaign}')
            target.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(target.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def state():
            response = page.request.get(f'/api/maps/{scene}/state')
            assert response.ok, response.text()
            return response.json()

        try:
            page.goto(f'/game/{campaign}')
            game()
            actor = page.evaluate('''()=>gravewrightRealtime.resourceCommand('actors','actor.create',
              {name:'Synthetic long named playtest traveler'})''')
            page.evaluate('''id=>gravewrightRealtime.resourceCommand('actors','actor.permissions',
              {id,permissions:{default:'owner'}})''', actor['id'])
            page.goto(review.builder)
            wait_ready(page)
            set_name(page, 'Synthetic safe playtest with deliberately long authored mechanism names')
            lever_asset = upload_asset(page, 'decoration', 'Synthetic playtest lever.png',
                                       harness.artwork('#b87932'))['id']
            floor_asset = upload_asset(page, 'floor', 'Synthetic original floor.png',
                                       harness.artwork('#a84735'))['id']
            replacement_asset = upload_asset(page, 'floor', 'Synthetic replacement floor.png',
                                             harness.artwork('#397ca5'))['id']
            for x in (10, 20):
                builder_tool(page, 'door')
                review.stroke((x, 8), (x + 2, 8))
            builder_tool(page, 'light')
            review.stroke((8, 15), (8, 15))
            for kind, preset, x in (('particle', 'smoke', 10), ('shader', 'orb-1', 26)):
                builder_sidebar(page, 'library')
                page.locator('[data-builder-role=effect]').click()
                page.locator('[data-builder-collection-filter]').select_option(kind)
                page.locator(f'[data-builder-{kind}-preset="{preset}"]').click()
                review.stroke((x, 22), (x, 22))
            project = review.save()
            document = deepcopy(project['document'])
            owner, receiver = [row['id'] for row in document['doors']]
            lamp = document['lights'][0]['id']
            document['lights'][0]['enabled'] = False
            document['particles'][0]['enabled'] = False
            document['shaders'][0]['enabled'] = False
            layer = document['layers'][0]['id']
            lever, region, floor = str(uuid4()), str(uuid4()), str(uuid4())
            document['floors'] = [{'id': floor, 'layerId': layer, 'assetId': floor_asset,
                'x': 4, 'y': 4, 'width': 3, 'height': 3, 'rotation': 0, 'dynamic': True}]
            document['decorations'] = [{'id': lever, 'layerId': layer, 'assetId': lever_asset,
                'x': 18, 'y': 16, 'width': 2, 'height': 2, 'rotation': 0, 'lever': {'state': 'off'},
                'blueprint': behavior('lever', {'interact:off': chain('interact:off', [
                    node('turnOn', 'state', targetState='on')])})}]
            document['regions'] = [{'id': region, 'layerId': layer, 'x': 24, 'y': 16,
                'width': 3, 'height': 3, 'enabled': True,
                'name': 'Synthetic long named occupancy region for the safe test fixture',
                'blueprint': behavior('region', {'presence:enter': chain('presence:enter', [
                    node('entered', 'setVariable', scope='element', name='Visited', valueType='boolean', value=True)])})}]
            document['doors'][0]['blueprint'] = behavior('door', {
                'interact:closed': chain('interact:closed', [
                    node('lampOn', 'light', targetId=lamp, enabled=True),
                    node('mark', 'setVariable', scope='element', name='PlaytestFlag', valueType='boolean', value=True),
                    node('broadcast', 'emitEvent', name='PlaytestBroadcast', scope='scene'),
                    node('message', 'showMessage', text='Synthetic <b>safe test message</b>', audience={'scope': 'players'}),
                    node('transport', 'teleport', destinationId=region),
                    node('clock', 'timer', name='PlaytestTick', action='restart', seconds=30),
                    node('wait', 'delay', seconds=30),
                    node('after', 'setVariable', scope='element', name='AfterWait', valueType='boolean', value=True),
                ], [node('lamps', 'elementGroup', name='Synthetic lamp group', memberType='light', targetIds=[lamp])],
                    [('lamps', 'targets', 'lampOn', 'target')]),
                'signal:PlaytestTick': chain('signal:PlaytestTick', [
                    node('expired', 'setVariable', scope='element', name='Expired', valueType='boolean', value=True)]),
            })
            document['doors'][1]['blueprint'] = behavior('door', {
                'signal:PlaytestBroadcast': chain('signal:PlaytestBroadcast', [
                    node('received', 'setVariable', scope='scene', name='Received', valueType='boolean', value=True)])})
            project = review.store(project['id'], project['version'], project['folderId'], document)
            page.goto(review.builder + '?project=' + project['id'])
            wait_ready(page)

            # The checks below intentionally use the same visible entry points
            # as the GM; HTTP is used only for fixture creation and assertions.
            guest = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
            guests.append(guest)
            guest.add_cookies([{**seed['sessions']['player'], 'url': base}])
            guest.add_init_script('''window.__playtestEvents=[];
              addEventListener('gravewright:api-event',event=>window.__playtestEvents.push(event.detail));''')
            player = guest.new_page()
            observe(player)
            player.goto(f'/game/{campaign}')
            game(player)

            def rehearsal():
                return page.locator('[data-playtest]')

            def result_check(result, source=False, with_token=False):
                assert result['dryRun'] is True and result['ok'] is True, result
                changed = result['changes']['elements']
                light = next(row for row in changed if (row.get('sourceId') == lamp if source
                             else row['id'] == native_lamp))
                assert light['before']['data']['enabled'] is False, light
                assert light['after']['data']['enabled'] is True, light
                assert result['changes']['sceneVariables']['after']['Received']['value'] is True, result
                assert {row['after']['kind'] for row in result['scheduled']} == {'delay', 'timer'}, result
                assert {'timing-not-advanced', 'presentation-not-delivered'} <= set(result['warnings']), result
                assert ('missing-test-token' not in result['warnings']) == with_token, result
                assert bool(result['changes']['tokens']) == with_token, result
                all_runs = [*result['runs'], result['run']]
                steps = [step for run in all_runs for event in run['events'] for step in event['steps']]
                assert any(step['type'] == 'showMessage' and step['text'] == 'Synthetic <b>safe test message</b>'
                           for step in steps), result
                assert not any(step.get('name') == 'AfterWait' for step in steps), result

            def no_deliveries():
                for target in (page, player):
                    events = target.evaluate('window.__playtestEvents')
                    assert not any(event.get('type') in ('automation.presentation', 'room.automation') for event in events), events
                    expect(target.locator('[data-automation-presentation]')).to_have_count(0)

            set_name(page, document['name'] + ' — unsaved rehearsal draft')
            expect(page.locator('[data-map-builder]')).not_to_have_attribute('data-save-state', 'saved')
            before_draft = review.draft(project['id'])
            before = persistent_snapshot(output)
            page.locator('[data-builder-test]').click()
            expect(rehearsal()).to_be_visible()
            rehearsal().locator('[data-playtest-element]').select_option(owner)
            rehearsal().locator('[data-playtest-event]').select_option('interact:closed')
            player.evaluate('window.__playtestEvents=[]')
            page.evaluate('window.__playtestEvents=[]')
            with page.expect_response(lambda response: response.request.method == 'POST'
                                      and response.url.endswith('/map-builder/test')) as tested:
                rehearsal().locator('[data-playtest-run]').click()
            response = tested.value
            assert response.ok, response.text()
            predicted = response.json()
            assert response.request.post_data_json['document'] == before_draft
            assert predicted['sourceElementId'] == owner
            result_check(predicted, source=True)
            expect(rehearsal().locator('[data-playtest-results]')).to_contain_text('Synthetic <b>safe test message</b>')
            assert rehearsal().locator('[data-playtest-results] b').count() == 0
            assert persistent_snapshot(output) == before
            assert review.project(project['id']) == project
            no_deliveries()
            records.append({'case': 'builder-tests-unsaved-draft-through-real-engine-with-signals-and-predicted-waits-but-no-persisted-effects-or-delivery'})

            rehearsal().locator('[data-playtest-actor]').select_option(actor['id'])
            with page.expect_response(lambda response: response.request.method == 'POST'
                                      and response.url.endswith('/map-builder/test')) as tested:
                rehearsal().locator('[data-playtest-run]').click()
            assert tested.value.ok, tested.value.text()
            result_check(tested.value.json(), source=True, with_token=True)
            expect(rehearsal().locator('[data-playtest-token-position]')).to_have_count(1)
            expect(rehearsal().locator('.playtest__effects')).to_have_attribute('data-render-state', 'ready')
            expect(rehearsal().locator('.playtest__effects canvas')).to_be_visible()
            page.screenshot(path=str(output / 'predicted-native-effects-and-token.png'))
            assert persistent_snapshot(output) == before
            no_deliveries()
            rehearsal().locator('[data-playtest-reset]').click()
            expect(rehearsal().locator('[data-playtest-token-position]')).to_have_count(0)
            expect(rehearsal().locator('[data-playtest-results]')).to_be_empty()
            expect(rehearsal().locator('.playtest__effects canvas')).to_have_count(0)
            assert persistent_snapshot(output) == before
            page.keyboard.press('Escape')
            expect(rehearsal()).to_have_count(0)
            assert review.draft(project['id']) == before_draft
            expect(page.locator('[data-map-builder]')).not_to_have_attribute('data-save-state', 'saved')
            page.locator('[data-builder-undo]').click()
            expect(page.locator('[data-builder-quick-name]')).to_have_value(document['name'])
            page.locator('[data-builder-redo]').click()
            expect(page.locator('[data-builder-quick-name]')).to_have_value(before_draft['name'])
            page.locator('[data-builder-undo]').click()
            assert review.project(project['id']) == project
            records.append({'case': 'optional-test-actor-enables-token-prediction-and-exiting-preserves-draft-dirty-status-and-history'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    page.goto(review.builder + '?project=' + project['id'])
                    wait_ready(page)
                    page.locator('[data-builder-test]').click()
                    expect(rehearsal()).to_be_visible()
                    rehearsal().locator('[data-playtest-element]').select_option(owner)
                    metrics = rehearsal().evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'playtest-{locale}-{width}.png'))
                    page.keyboard.press('Escape')
                    expect(rehearsal()).to_have_count(0)
                    records.append({'case': 'localized-rehearsal-supports-long-names-and-keyboard-close',
                                    'locale': locale, 'width': width, 'metrics': metrics})

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(review.builder + '?project=' + project['id'])
            wait_ready(page)
            close_panel(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            game()
            project = review.project(project['id'])
            scene = project['sceneId']
            page.evaluate('a=>gravewrightRealtime.mapCommand("update",{mapId:a.scene,version:a.version,settings:{visibility:"players"}})',
                          {'scene': scene, 'version': project['sceneVersion']})
            page.evaluate('scene=>gravewrightRealtime.mapCommand("activate",{mapId:scene})', scene)
            player.reload()
            game(player)
            native = state()
            network_endpoint = f'/api/maps/{scene}/automation/network'

            def catalog():
                response = page.request.get(network_endpoint)
                assert response.ok, response.text()
                return response.json()

            live = catalog()
            native_owner = next(row for row in live['elements'] if 'interact:closed' in (row.get('blueprint') or {}).get('graphs', {}))['id']
            native_receiver = next(row for row in live['elements'] if 'signal:PlaytestBroadcast' in (row.get('blueprint') or {}).get('graphs', {}))['id']
            native_lever = next(row for row in live['elements'] if row['kind'] == 'lever')['id']
            native_region = next(row for row in live['elements'] if row['kind'] == 'region')['id']
            native_floor = next(row for row in live['elements'] if row.get('surfaceKind') == 'floor')['id']
            native_lamp = native['lights'][0]['id']
            created = page.evaluate('''a=>gravewrightRealtime.resourceCommand('tokens','place',
              {mapId:a.scene,actorId:a.actor,gridX:2,gridY:2})''', {'scene': scene, 'actor': actor['id']})
            token = created['createdIds'][0]
            page.locator('.game-menubar__layer').nth(5).click()
            page.locator('[data-dock-tool=automation]').click()
            page.locator('[data-automation-view=doors]').click()
            controls = page.locator('[data-scene-controls]')
            expect(controls).to_be_visible()
            controls.locator(f'[data-scene-controls-element="{native_owner}"]').click()
            expect(controls).to_have_attribute('aria-busy', 'false')
            delayed = []
            delayed_catalog = catalog()

            def hold_test_catalog(route):
                delayed.append(route)

            test_catalog_route = '**' + network_endpoint
            page.route(test_catalog_route, hold_test_catalog, times=1)
            with page.expect_request(lambda request: request.url.endswith('/automation/network')):
                controls.locator('[data-scene-controls-test]').click()
            # Keep the old read unresolved until the window has a new lifetime.
            page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(resolve))')
            assert len(delayed) == 1
            page.locator('[data-automation-close]').click()
            expect(controls).to_have_count(0)
            page.locator('[data-dock-tool=automation]').click()
            expect(controls).to_be_visible()
            expect(controls).to_have_attribute('aria-busy', 'false')
            delayed[0].fulfill(status=200, content_type='application/json', body=json.dumps(delayed_catalog))
            page.unroute(test_catalog_route)
            page.wait_for_timeout(200)
            expect(rehearsal()).to_have_count(0)
            expect(controls.locator('[data-scene-controls-element]')).to_have_count(8)
            controls.locator(f'[data-scene-controls-element="{native_owner}"]').click()
            records.append({'case': 'late-test-catalog-response-cannot-open-a-modal-after-automation-window-closes-and-reopens'})
            before = persistent_snapshot(output)
            page.evaluate('window.__playtestEvents=[]')
            player.evaluate('window.__playtestEvents=[]')
            controls.locator('[data-scene-controls-test]').click()
            expect(rehearsal()).to_be_visible()
            rehearsal().locator('[data-playtest-event]').select_option('interact:closed')
            rehearsal().locator('[data-playtest-token]').select_option(token)
            with page.expect_response(lambda response: response.request.method == 'POST'
                                      and '/automation/test/' in response.url) as tested:
                rehearsal().locator('[data-playtest-run]').click()
            assert tested.value.ok, tested.value.text()
            result_check(tested.value.json(), with_token=True)
            assert persistent_snapshot(output) == before
            no_deliveries()
            page.keyboard.press('Escape')
            expect(rehearsal()).to_have_count(0)
            expect(controls).to_be_visible()
            records.append({'case': 'native-gm-rehearsal-predicts-real-token-and-effects-but-rolls-back-scene-logs-variables-jobs-audio-and-files'})
            before_edit = persistent_snapshot(output)
            controls.locator('[data-scene-controls-edit]').click()
            editor = page.locator('[data-smart-object-modal]')
            expect(editor).to_be_visible()
            editor.locator('[data-blueprint-event="interact:closed"]').click()
            expect(editor.locator('[data-blueprint-node=lampOn]')).to_have_count(1)
            editor.locator('[data-blueprint-cancel]').click()
            expect(editor).to_have_count(0)
            expect(page.locator('[data-scene-network]')).to_be_visible()
            page.locator('[data-network-close]').click()
            expect(controls).to_be_visible()
            assert persistent_snapshot(output) == before_edit
            records.append({'case': 'live-edit-behavior-opens-original-owner-graph-directly-and-cancel-preserves-scene'})

            def choose(identifier):
                controls.locator('[data-scene-controls-search]').fill('')
                controls.locator('[data-scene-controls-type]').select_option('all')
                controls.locator(f'[data-scene-controls-element="{identifier}"]').click()

            def apply(control):
                with page.expect_response(lambda response: response.request.method == 'POST'
                                          and '/automation/control/' in response.url) as changed:
                    control()
                assert changed.value.ok, changed.value.text()
                expect(controls).to_have_attribute('aria-busy', 'false')
                return changed.value

            authored_baseline = deepcopy(review.project(project['id']))
            choose(native_owner)
            changed = apply(lambda: controls.locator('[data-scene-controls-action=state][data-scene-controls-value=open]').click())
            assert next(row for row in state()['walls'] if row['id'] == native_owner)['door_state'] == 'open'
            assert review.project(project['id']) == authored_baseline
            retry_before = persistent_snapshot(output)
            assert post(page, changed.url.replace(base, ''), changed.request.post_data_json)['status'] == 200
            assert persistent_snapshot(output) == retry_before
            stale = {**changed.request.post_data_json, 'request_id': str(uuid4()), 'value': 'locked'}
            conflict = post(page, changed.url.replace(base, ''), stale)
            assert conflict['status'] == 409 and conflict['body']['code'] == 'conflict', conflict
            assert persistent_snapshot(output) == retry_before
            records.append({'case': 'live-door-control-is-versioned-retry-safe-and-conflicts-without-overwriting-authored-source'})

            apply(lambda: controls.locator('[data-scene-controls-flag=interaction]').uncheck())
            assert next(row for row in catalog()['elements'] if row['id'] == native_owner)['interactionEnabled'] is False
            blocked = player.evaluate('''async a=>{
              try{await gravewrightRealtime.mapCommand('objects',{mapId:a.scene,area:'walls',action:'door',
                data:{wall_id:a.owner,door_state:'closed'}});return {ok:true};}
              catch(error){return {ok:false,message:error.message};}
            }''', {'scene': scene, 'owner': native_owner})
            assert blocked['ok'] is False, blocked
            assert next(row for row in state()['walls'] if row['id'] == native_owner)['door_state'] == 'open'
            apply(lambda: controls.locator('[data-scene-controls-action=state][data-scene-controls-value=closed]').click())
            assert next(row for row in state()['walls'] if row['id'] == native_owner)['door_state'] == 'closed'
            apply(lambda: controls.locator('[data-scene-controls-flag=interaction]').check())
            choose(native_lever)
            apply(lambda: controls.locator('[data-scene-controls-action=interact]').click())
            assert next(row for row in catalog()['elements'] if row['id'] == native_lever)['state'] == 'on'
            choose(native_region)
            apply(lambda: controls.locator('[data-scene-controls-flag=region]').uncheck())
            assert next(row for row in catalog()['elements'] if row['id'] == native_region)['enabled'] is False
            apply(lambda: controls.locator('[data-scene-controls-flag=region]').check())
            assert next(row for row in catalog()['elements'] if row['id'] == native_region)['enabled'] is True
            assert review.project(project['id']) == authored_baseline
            records.append({'case': 'live-mechanism-flags-and-region-state-use-native-authorized-controls-and-gm-override-without-changing-source'})

            choose(native_floor)
            apply(lambda: controls.locator('[data-scene-controls-action=visibility][data-scene-controls-value=false]').click())
            assert next(row for row in catalog()['elements'] if row['id'] == native_floor)['visible'] is False
            apply(lambda: controls.locator('[data-scene-controls-action=visibility][data-scene-controls-value=true]').click())
            controls.locator('[data-scene-controls-material]').select_option(replacement_asset)
            player.evaluate('''a=>gravewrightRealtime.mapCommand('objects',{mapId:a.scene,area:'walls',action:'door',
              data:{wall_id:a.owner,door_state:'open'}})''', {'scene': scene, 'owner': native_receiver})
            expect(controls.locator(f'[data-scene-controls-element="{native_receiver}"]')).to_contain_text('Opened')
            expect(controls.locator('[data-scene-controls-material]')).to_have_value(replacement_asset)
            records.append({'case': 'real-remote-map-update-refreshes-live-controls-without-losing-selected-material'})
            apply(lambda: controls.locator('[data-scene-controls-apply-material]').click())
            assert next(row for row in catalog()['elements'] if row['id'] == native_floor)['materialId'] == replacement_asset
            apply(lambda: controls.locator('[data-scene-controls-restore-material]').click())
            assert next(row for row in catalog()['elements'] if row['id'] == native_floor).get('materialId') is None
            assert review.project(project['id']) == authored_baseline
            records.append({'case': 'live-dynamic-artwork-visibility-and-material-can-be-adjusted-and-restored-without-editing-recipe'})

            for kind, area, label, field, value in (
                ('light', 'lights', 'Intensity', 'intensity', .65),
                ('particle', 'particles', 'Quantity', 'density', .4),
                ('shader', 'shaders', 'Opacity', 'opacity', .55),
            ):
                resources = catalog()
                resource = (resources['lights'][0] if kind == 'light'
                            else next(row for row in resources['effects'] if row['nativeKind'] == area))
                choose(resource['id'])
                flag = controls.locator('[data-scene-controls-flag=enabled]')
                expect(flag).not_to_be_checked()
                flag.check()
                expect(controls).to_have_attribute('aria-busy', 'false')
                assert next(row for row in state()[area] if row['id'] == resource['id'])['enabled'] is True
                before_editor = persistent_snapshot(output)

                def settings():
                    controls.locator('[data-scene-controls-settings]').click()
                    editor = page.locator(f'[data-builder-native-editor="{area}"]')
                    expect(editor).to_be_visible()
                    control = editor.get_by_label(label, exact=True)
                    control.scroll_into_view_if_needed()
                    control.evaluate('''(input,value)=>{
                      input.value=String(value);
                      input.dispatchEvent(new Event('input',{bubbles:true}));
                      input.dispatchEvent(new Event('change',{bubbles:true}));
                    }''', value)
                    return editor

                editor = settings()
                editor.locator('[data-native-editor-cancel]').click()
                expect(editor).to_have_count(0)
                assert persistent_snapshot(output) == before_editor
                editor = settings()
                editor.locator('[data-native-editor-save]').click()
                expect(editor).to_have_count(0)
                assert next(row for row in state()[area] if row['id'] == resource['id'])[field] == value
                expect(controls).to_have_attribute('aria-busy', 'false')
                controls.locator('[data-scene-controls-flag=enabled]').uncheck()
                expect(controls).to_have_attribute('aria-busy', 'false')
                assert next(row for row in state()[area] if row['id'] == resource['id'])['enabled'] is False
                assert review.project(project['id']) == authored_baseline
                records.append({'case': 'live-native-settings-cancel-is-private-and-apply-uses-authorized-native-command',
                                'kind': kind, 'field': field, 'value': value})

            page.locator('[data-automation-close]').click()
            expect(controls).to_have_count(0)
            page.locator('[data-dock-tool=automation]').click()
            controls = page.locator('[data-scene-controls]')
            expect(controls).to_be_visible()
            expect(controls.locator('[data-scene-controls-element]')).to_have_count(8)
            records.append({'case': 'reopening-automation-on-elements-reloads-the-native-resource-catalog'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    # The native game layer bar needs desktop width to expose
                    # its controls; resize the open window to inspect its layout.
                    page.set_viewport_size({'width': 1440, 'height': 900})
                    page.reload()
                    game()
                    page.locator('.game-menubar__layer').nth(5).click()
                    page.locator('[data-dock-tool=automation]').click()
                    page.locator('[data-automation-view=doors]').click()
                    controls = page.locator('[data-scene-controls]')
                    expect(controls).to_be_visible()
                    controls.locator('[data-scene-controls-type]').select_option('region')
                    controls.locator('[data-scene-controls-search]').fill('long named occupancy')
                    expect(controls.locator('[data-scene-controls-element]')).to_have_count(1)
                    controls.locator(f'[data-scene-controls-element="{native_region}"]').click()
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    metrics = controls.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'live-controls-{locale}-{width}.png'))
                    page.locator('[data-automation-close]').click()
                    records.append({'case': 'localized-live-controls-filter-and-inspect-long-authored-names',
                                    'locale': locale, 'width': width, 'metrics': metrics})

            for role in ('player', 'streamer'):
                denied = browser.new_context(base_url=base)
                guests.append(denied)
                denied.add_cookies([{**seed['sessions'][role], 'url': base}])
                denied_page = denied.new_page()
                observe(denied_page)
                denied_page.goto(f'/game/{campaign}')
                denied_page.wait_for_function('!!window.gravewrightRealtime')
                expect(denied_page.locator('[data-dock-tool=automation]')).to_have_count(0)
                denied_before = persistent_snapshot(output)
                for endpoint, body in (
                    (review.api + '/test', {'request_id': str(uuid4()), 'document': document, 'elementId': owner, 'event': 'interact:closed'}),
                    (f'/api/maps/{scene}/automation/test/{native_owner}', {'request_id': str(uuid4()), 'expected_version': 1, 'event': 'interact:closed'}),
                    (f'/api/maps/{scene}/automation/control/{native_owner}', {'request_id': str(uuid4()), 'expected_version': 1, 'action': 'state', 'value': 'open'}),
                ):
                    rejected = post(denied_page, endpoint, body)
                    assert rejected['status'] in (403, 404), (role, rejected)
                assert persistent_snapshot(output) == denied_before
            assert review.project(project['id']) == authored_baseline
            records.append({'case': 'player-and-streamer-cannot-open-private-controls-or-execute-test-and-live-control-endpoints'})

        except Exception:
            if not page.is_closed():
                page.screenshot(path=str(output / 'failure.png'), full_page=True)
            (output / 'progress.json').write_text(json.dumps({
                'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs}, indent=2), encoding='utf-8')
            raise
        finally:
            for guest in guests:
                guest.close()
            context.close()
            browser.close()
    assert records, 'Playtest checks must exercise the public controls'
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Disposable doors, lever, light, region and explicit synthetic rule graphs.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
