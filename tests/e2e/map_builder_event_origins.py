"""Keep root event wires visible and preserve sprites after state transitions.

The synthetic interaction graph mirrors a two-state mechanism: check Off,
activate and change sprite, otherwise deactivate and change sprite. All uploads,
project state, media, tabletop operations and diagnostics use a disposable fixture.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re
import time
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_playtest import behavior, chain, node
from map_builder_reference import close_panel, upload_asset, wait_ready


GEOMETRY = '''modal=>{
 const root=modal.querySelector('[data-blueprint-instance]'),box=root.getBoundingClientRect();
 const rect=element=>{const r=element.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2};};
 const ports=Object.fromEntries([...root.querySelectorAll('[data-blueprint-event-port]')].map(pin=>[
   pin.dataset.blueprintEventPort,{...rect(pin.querySelector('[data-blueprint-state-dot]')),output:pin.dataset.blueprintOutput||null}]));
 const group=modal.querySelector('[data-blueprint-edge="event:next:check"]'),path=group.querySelector('.smart-object__wire');
 const matrix=path.getScreenCTM(),point=length=>{const p=path.getPointAtLength(length).matrixTransform(matrix);return {x:p.x,y:p.y};};
 const start=point(0),length=path.getTotalLength(),hidden=[];let travelled=0,previous=start;
 for(let step=2;step<=length;step+=2){const p=point(step);travelled+=Math.hypot(p.x-previous.x,p.y-previous.y);previous=p;
   if(travelled>14&&p.x>box.left+1&&p.x<box.right-1&&p.y>box.top+1&&p.y<box.bottom-1)hidden.push({...p,travelled});}
 const distances=Object.fromEntries(Object.entries(ports).map(([key,p])=>[key,Math.hypot(start.x-p.x,start.y-p.y)]));
 return {zoom:modal.querySelector('[data-blueprint-zoom-reset]').textContent,ports,start,distances,
   root:{left:box.left,right:box.right,top:box.top,bottom:box.bottom},hidden: hidden.slice(0,8),hiddenCount:hidden.length,
   wireKind:group.dataset.wireKind,path:path.getAttribute('d')};
}'''


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    records, metrics, failures, errors, dialogs, commands, replies = [], [], [], [], [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1920, 'height': 1080})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        def frame_sent(payload):
            if not isinstance(payload, str):
                return
            value = json.loads(payload)
            data = value.get('payload', {}).get('data', {})
            if value.get('type') == 'maps.command' and data.get('area') == 'images' and data.get('action') == 'interact':
                commands.append(value)

        def frame_received(payload):
            if isinstance(payload, str):
                value = json.loads(payload)
                if value.get('type') in ('maps.ack', 'maps.error'):
                    replies.append(value)

        def websocket(connection):
            connection.on('framesent', frame_sent)
            connection.on('framereceived', frame_received)

        page.on('websocket', websocket)
        review = BuilderReview(page, campaign)

        def idle():
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved', timeout=20_000)

        def project():
            identifier = page.evaluate("new URL(location.href).searchParams.get('project')")
            assert identifier
            return review.project(identifier)

        def saved_sprite(expected):
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                current = project()
                blueprint = next(row for row in current['document']['decorations'] if row['id'] == owner_id)['blueprint']
                sprite = next(value for value in blueprint['graphs']['interact']['nodes'] if value['id'] == 'spriteOn')
                if sprite['assetId'] == expected:
                    idle()
                    return current
                page.wait_for_timeout(100)
            raise AssertionError({'message': 'Graph edit did not save automatically.', 'project': current})

        def open_editor(identifier, kind='decorations'):
            builder_tool(page, 'select')
            builder_workspace(page)
            page.locator(f'[data-builder-{kind}] [data-object-id="{identifier}"]').dblclick()
            modal = page.locator('[data-smart-object-modal]')
            expect(modal).to_be_visible()
            return modal

        def reveal_root(modal):
            canvas = modal.locator('[data-blueprint-canvas]')
            canvas_box = canvas.bounding_box()
            root_box = modal.locator('[data-blueprint-instance]').bounding_box()
            for _ in range(math.ceil(max(0, canvas_box['x'] + 16 - root_box['x']) / 40)):
                canvas.press('ArrowLeft')
            page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')

        def remember_failure(message, **details):
            failures.append({'message': message, **details})

        def save_diagnostics():
            (output / 'measurements.json').write_text(json.dumps({'metrics': metrics, 'failures': failures,
                'cases': records, 'pageErrors': errors, 'interactionCommands': commands, 'mapReplies': replies}, indent=2), encoding='utf-8')

        try:
            page.goto(review.builder)
            wait_ready(page)
            page.locator('[data-builder-quick-name]').fill('Synthetic onInteract wire and appearance branches')
            page.locator('[data-builder-quick-name]').press('Tab')
            base_asset = upload_asset(page, 'decoration', 'Synthetic original mechanism.png', harness.artwork('#6b6e73'))['id']
            on_asset = upload_asset(page, 'decoration', 'Synthetic activated mechanism.png', harness.artwork('#d8882d'))['id']
            off_asset = upload_asset(page, 'decoration', 'Synthetic deactivated mechanism.png', harness.artwork('#357aba'))['id']
            builder_tool(page, 'decoration')
            page.locator('[data-builder-brush-material]').select_option(base_asset)
            review.stroke((17, 12), (19, 14))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=behavior]').select_option('lever')
            close_panel(page)
            idle()
            authored = project()
            document = deepcopy(authored['document'])
            owner = document['decorations'][0]
            owner_id = owner['id']
            modal = open_editor(owner_id)
            object_events = {'interact', 'presence:enter', 'presence:exit', 'destroy'}
            assert set(modal.locator('[data-blueprint-event]').evaluate_all('nodes=>nodes.map(node=>node.dataset.blueprintEvent)')) == object_events
            assert set(modal.locator('[data-blueprint-event-port]').evaluate_all('nodes=>nodes.map(node=>node.dataset.blueprintEventPort)')) == object_events
            expect(modal.locator('[data-blueprint-state-events]')).to_have_count(0)
            expect(modal.locator('[data-blueprint-legacy-events]')).to_have_count(0)
            expect(modal.locator('[data-blueprint-instance] input, [data-blueprint-instance] select')).to_have_count(0)
            modal.locator('[data-blueprint-close]').click()
            idle()
            assert project()['document'] == authored['document']
            records.append({'case': 'fresh-mechanism-offers-direct-interaction-and-destruction-starts-without-state-filters-or-legacy-graphs'})
            nodes = [node('event', 'event', event='interact'), node('check', 'condition', state='off'),
                node('turnOn', 'state', targetState='on'), node('spriteOn', 'sprite', appearance='asset', assetId=on_asset),
                node('turnOff', 'state', targetState='off'), node('spriteOff', 'sprite', appearance='asset', assetId=off_asset)]
            positions = [(40, 60), (370, 220), (680, 70), (1030, 70), (680, 420), (1030, 420)]
            for value, (x, y) in zip(nodes, positions):
                value.update(x=x, y=y)
            graph = {'nodes': nodes, 'edges': [
                {'kind': 'execution', 'from': 'event', 'output': 'next', 'to': 'check'},
                {'kind': 'execution', 'from': 'check', 'output': 'true', 'to': 'turnOn'},
                {'kind': 'execution', 'from': 'turnOn', 'output': 'next', 'to': 'spriteOn'},
                {'kind': 'execution', 'from': 'check', 'output': 'false', 'to': 'turnOff'},
                {'kind': 'execution', 'from': 'turnOff', 'output': 'next', 'to': 'spriteOff'},
            ]}
            removed_events = ('change', 'enter:off', 'exit:on', 'interact:off')
            owner['blueprint'] = behavior('lever', {'interact': graph, **{event: chain(event, [node('removed', 'setVariable',
                scope='element', name='RemovedEventExecuted', valueType='boolean', value=True)]) for event in removed_events}})
            idle_id, simple_id = str(uuid4()), str(uuid4())
            empty = deepcopy(owner)
            empty.update(id=idle_id, x=22)
            empty['blueprint'] = behavior('lever', {'interact': {'nodes': [node('event', 'event', event='interact')], 'edges': []}})
            simple = deepcopy(owner)
            simple.update(id=simple_id, x=27, lever={'state': 'on'})
            simple['blueprint'] = behavior('lever', {'interact': chain('interact', [
                node('spriteOnly', 'sprite', appearance='asset', assetId=on_asset)])})
            document['decorations'].extend((empty, simple))
            authored = review.store(authored['id'], authored['version'], authored['folderId'], document)
            normalized = next(row for row in authored['document']['decorations'] if row['id'] == owner_id)['blueprint']
            assert set(normalized['graphs']) == {'interact'}, normalized
            records.append({'case': 'normalization-discards-old-change-and-state-scoped-events-instead-of-preserving-or-displaying-them'})
            page.goto(review.builder + '?project=' + authored['id'])
            wait_ready(page)
            builder_tool(page, 'select')
            builder_workspace(page)
            page.locator(f'[data-builder-decorations] [data-object-id="{owner_id}"]').dblclick()
            modal = page.locator('[data-smart-object-modal]')
            expect(modal).to_be_visible()
            expect(modal.locator('[data-blueprint-event="interact"] .smart-object__badge')).to_have_text('5')
            expect(modal.locator('[data-blueprint-event="interact"]')).to_have_attribute('aria-pressed', 'true')
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(5)
            expect(modal.locator('[data-blueprint-event="change"]')).to_have_count(0)
            assert set(modal.locator('[data-blueprint-event-port]').evaluate_all('nodes=>nodes.map(node=>node.dataset.blueprintEventPort)')) == object_events
            expect(modal.locator('[data-blueprint-state-events]')).to_have_count(0)
            expect(modal.locator('[data-blueprint-legacy-events]')).to_have_count(0)
            expect(modal.locator('[data-blueprint-transition-hint]')).to_have_count(0)
            expect(modal.locator('[data-blueprint-instance] input, [data-blueprint-instance] select')).to_have_count(0)

            sprite_input = modal.locator('[data-blueprint-node="spriteOn"] [data-blueprint-param="assetId"]')
            sprite_input.select_option(off_asset)
            saved_sprite(off_asset)
            modal.locator('[data-blueprint-undo]').click()
            saved_sprite(on_asset)
            modal.locator('[data-blueprint-redo]').click()
            saved_sprite(off_asset)
            modal.locator('[data-blueprint-undo]').click()
            authored = saved_sprite(on_asset)
            records.append({'case': 'complete-interaction-graph-edits-undo-redo-save-automatically-without-manual-save'})

            for zoom in (100, 74):
                modal.locator('[data-blueprint-zoom-reset]').click()
                if zoom != 100:
                    bounds = modal.locator('[data-blueprint-canvas]').bounding_box()
                    modal.locator('[data-blueprint-canvas]').dispatch_event('wheel', {
                        'deltaY': -math.log(zoom / 100) / .002,
                        'clientX': bounds['x'] + bounds['width'] / 2,
                        'clientY': bounds['y'] + bounds['height'] / 2})
                expect(modal.locator('[data-blueprint-zoom-reset]')).to_have_text(f'{zoom}%')
                reveal_root(modal)
                result = modal.evaluate(GEOMETRY)
                metrics.append(result)
                page.screenshot(path=str(output / f'interact-origin-{zoom}.png'))
                if result['distances']['interact'] > 1 or result['wireKind'] != 'interact':
                    remember_failure('The event wire is not anchored to onInteract.', geometry=result)
                if result['hiddenCount']:
                    remember_failure('The onInteract wire passes behind its own root card after leaving the active dot.', geometry=result)
                records.append({'case': 'interaction-wire-starts-at-active-port-and-stays-visible-outside-root', 'zoom': zoom})
                save_diagnostics()

            for current, expected, selected in (('off', 'on', 'turnOn'), ('on', 'off', 'turnOff')):
                modal.locator('[data-blueprint-simulation-state]').select_option(current)
                modal.locator('[data-blueprint-simulate]').click()
                expect(modal.locator(f'[data-blueprint-node="{selected}"]')).to_have_class(re.compile('is-executed'))
                expect(modal.locator(f'[data-blueprint-node="sprite{expected.title()}"]')).to_have_class(re.compile('is-executed'))
                expect(modal.locator('[data-blueprint-trace]')).to_contain_text('Activated' if expected == 'on' else 'Deactivated')
                records.append({'case': 'local-simulation-takes-interaction-branch-for-current-state', 'before': current, 'after': expected})
            modal.locator('[data-blueprint-close]').click()
            expect(modal).to_have_count(0)
            idle()

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width, height in ((1440, 900), (390, 844)):
                    page.set_viewport_size({'width': width, 'height': height})
                    page.goto(review.builder + '?project=' + authored['id'])
                    wait_ready(page)
                    modal = open_editor(owner_id)
                    expect(modal.locator('[data-blueprint-transition-hint]')).to_have_count(0)
                    expect(modal.locator('[data-blueprint-event="change"]')).to_have_count(0)
                    expect(modal.locator('[data-blueprint-legacy-events]')).to_have_count(0)
                    layout = modal.evaluate(MEASURE)
                    assert not layout['tiny'] and not layout['overflow'], layout
                    page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
                    localized = modal.evaluate(GEOMETRY)
                    assert localized['distances']['interact'] < 1 and localized['hiddenCount'] == 0, localized
                    page.screenshot(path=str(output / f'event-origin-{locale}-{width}.png'))
                    modal.locator('[data-blueprint-close]').click()
                    records.append({'case': 'localized-direct-event-starts-and-complete-chain-fit-desktop-mobile',
                        'locale': locale, 'width': width, 'layout': layout})
            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1920, 'height': 1080})
            page.goto(review.builder + '?project=' + authored['id'])
            wait_ready(page)
            modal = open_editor(owner_id)
            modal.locator('[data-blueprint-close]').click()

            for current, expected, asset_id in (('off', 'on', on_asset), ('on', 'off', off_asset)):
                if current == 'on':
                    builder_sidebar(page, 'selection')
                    page.locator('[data-builder-property=leverState]').select_option(current)
                    close_panel(page)
                    idle()
                before = project()
                before_history = [page.locator(selector).is_enabled() for selector in ('[data-builder-undo]', '[data-builder-redo]')]
                page.locator('[data-builder-test]').click()
                rehearsal = page.locator('[data-playtest]')
                expect(rehearsal).to_be_visible()
                rehearsal.locator('[data-playtest-element]').select_option(owner_id)
                rehearsal.locator('[data-playtest-event]').select_option('interact')
                with page.expect_response(lambda response: response.request.method == 'POST' and response.url.endswith('/map-builder/test')) as tested:
                    rehearsal.locator('[data-playtest-run]').click()
                assert tested.value.ok, tested.value.text()
                prediction = tested.value.json()
                assert prediction['run']['stateBefore'] == current and prediction['run']['stateAfter'] == expected, prediction
                changed = next(row for row in prediction['changes']['elements'] if row.get('sourceId') == owner_id)
                sprite = changed['after']['data'].get('sprite')
                assert sprite == {'appearance': 'asset', 'assetId': asset_id}, prediction
                assert project()['document'] == before['document']
                rehearsal.locator('[data-playtest-close]').click()
                assert [page.locator(selector).is_enabled() for selector in ('[data-builder-undo]', '[data-builder-redo]')] == before_history
                records.append({'case': 'server-rehearsal-runs-complete-interaction-chain-and-keeps-sprite-without-changing-source', 'before': current, 'after': expected})
                save_diagnostics()

            for identifier, current, appearance in ((idle_id, 'off', None), (simple_id, 'on', on_asset)):
                before = project()
                page.locator('[data-builder-test]').click()
                rehearsal = page.locator('[data-playtest]')
                rehearsal.locator('[data-playtest-element]').select_option(identifier)
                rehearsal.locator('[data-playtest-event]').select_option('interact')
                with page.expect_response(lambda response: response.request.method == 'POST' and response.url.endswith('/map-builder/test')) as tested:
                    rehearsal.locator('[data-playtest-run]').click()
                assert tested.value.ok, tested.value.text()
                prediction = tested.value.json()
                assert prediction['run']['stateBefore'] == prediction['run']['stateAfter'] == current, prediction
                if appearance:
                    changed = next(row for row in prediction['changes']['elements'] if row.get('sourceId') == identifier)
                    assert changed['after']['data']['sprite'] == {'appearance': 'asset', 'assetId': appearance}, prediction
                else:
                    for changed in prediction['changes']['elements']:
                        if changed.get('sourceId') == identifier:
                            assert changed['after']['data'].get('sprite') is None, prediction
                            assert changed['after']['data']['lever']['state'] == current, prediction
                assert project()['document'] == before['document']
                rehearsal.locator('[data-playtest-close]').click()
                records.append({'case': 'rehearsal-event-only-starts-connected-actions-without-implicit-state-checks-or-toggle', 'connected': bool(appearance)})

            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=leverState]').select_option('off')
            close_panel(page)
            idle()
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            scene_id = review.project(authored['id'])['sceneId']

            def native():
                response = page.request.get(f'/api/maps/{scene_id}/state')
                assert response.ok, response.text()
                return response.json()

            native_owner = next(row for row in native()['images'] if any(value['id'] == 'check'
                for value in row.get('blueprint', {}).get('graphs', {}).get('interact', {}).get('nodes', [])))

            def double_click(image, expected, asset_id):
                point = page.evaluate('''image=>{
                    const surface=document.querySelector('.game-board__surface').getBoundingClientRect(),view=gravewrightMaps.board.viewport();
                    const x=surface.x+view.x+image.x*view.scale,y=surface.y+view.y+image.y*view.scale;
                    const hit=document.elementFromPoint(x,y);return {x,y,hit:hit?.outerHTML?.slice(0,300)};
                }''', image)
                sent_before = len(commands)
                page.mouse.dblclick(point['x'], point['y'], delay=70)
                deadline = time.monotonic() + 12
                acknowledgement = None
                while time.monotonic() < deadline:
                    if len(commands) > sent_before:
                        request_id = commands[-1]['payload']['requestId']
                        acknowledgement = next((value for value in replies if value['payload'].get('requestId') == request_id), None)
                        if acknowledgement:
                            break
                    page.wait_for_timeout(50)
                assert len(commands) == sent_before + 1 and acknowledgement, {'commands': commands, 'replies': replies, 'point': point}
                assert acknowledgement['type'] == 'maps.ack', acknowledgement
                current = next(row for row in native()['images'] if row['id'] == image['id'])
                assert current['lever']['state'] == expected and current['asset_id'] == asset_id, current
                return current, point

            page.locator('.game-menubar__layer').get_by_text('Game', exact=True).click()
            for expected, asset_id in (('on', on_asset), ('off', off_asset)):
                current, point = double_click(native_owner, expected, asset_id)
                log = page.request.get(f'/api/maps/{scene_id}/automation').json()
                assert [event['event'] for event in log['runs'][0]['events']] == ['interact'], log['runs'][0]
                records.append({'case': 'real-native-double-click-runs-complete-interaction-chain-and-keeps-sprite',
                    'state': expected, 'point': point, 'assetId': current['asset_id'], 'command': commands[-1]})
                save_diagnostics()
            page.screenshot(path=str(output / 'native-two-branch-interaction.png'))

            native_idle = next(row for row in native()['images'] if row.get('blueprint', {}).get('graphs', {}).get('interact', {}).get('edges') == [])
            before_idle = deepcopy(native_idle)
            current, point = double_click(native_idle, 'off', base_asset)
            assert current['lever'] == before_idle['lever'] and current['asset_id'] == before_idle['asset_id']
            records.append({'case': 'real-unconnected-interaction-start-does-not-toggle-or-change-image', 'point': point})
            native_simple = next(row for row in native()['images'] if any(value['id'] == 'spriteOnly'
                for value in row.get('blueprint', {}).get('graphs', {}).get('interact', {}).get('nodes', [])))
            current, point = double_click(native_simple, 'on', on_asset)
            records.append({'case': 'real-unconditional-interaction-runs-connected-action-without-testing-or-changing-state', 'point': point})
            assert review.project(authored['id'])['document'] == authored['document']

            # The shared instance renderer must keep other root event types on
            # the same visible side. Removed events must not reappear on load.
            page.goto(review.builder + '?project=' + authored['id'])
            wait_ready(page)
            builder_tool(page, 'region')
            review.stroke((7, 7), (10, 10))
            idle()
            source = project()
            area_id = source['document']['regions'][0]['id']
            modal = open_editor(area_id, 'regions')
            assert set(modal.locator('[data-blueprint-event]').evaluate_all('nodes=>nodes.map(node=>node.dataset.blueprintEvent)')) == {'presence:enter', 'presence:exit', 'destroy'}
            assert set(modal.locator('[data-blueprint-event-port]').evaluate_all('nodes=>nodes.map(node=>node.dataset.blueprintEventPort)')) == {'presence:enter', 'presence:exit', 'destroy'}
            expect(modal.locator('[data-blueprint-state-events]')).to_have_count(0)
            expect(modal.locator('[data-blueprint-instance] input, [data-blueprint-instance] select')).to_have_count(0)
            modal.locator('[data-blueprint-close]').click()
            idle()
            assert project()['document'] == source['document']
            records.append({'case': 'fresh-region-starts-do-not-compare-occupancy-or-offer-state-event-branches'})
            port_document = deepcopy(source['document'])
            mechanism = next(row for row in port_document['decorations'] if row['id'] == owner_id)
            for event in ('signal:Inspect', 'change', 'enter:off'):
                mechanism['blueprint']['graphs'][event] = chain(event, [node('check', 'setVariable',
                    scope='element', name='Inspected', valueType='boolean', value=True)])
            area = port_document['regions'][0]
            area_id = area['id']
            area['blueprint'] = behavior('region', {event: chain(event, [node('check', 'setVariable',
                scope='element', name='Inspected', valueType='boolean', value=True)])
                for event in ('presence:enter', 'presence:exit')})
            area['blueprint']['graphs']['enter:occupied'] = chain('enter:occupied', [node('removed', 'setVariable',
                scope='element', name='RemovedEventExecuted', valueType='boolean', value=True)])
            source = review.store(source['id'], source['version'], source['folderId'], port_document)
            assert set(next(row for row in source['document']['decorations'] if row['id'] == owner_id)['blueprint']['graphs']) == {'interact', 'signal:Inspect'}
            assert set(source['document']['regions'][0]['blueprint']['graphs']) == {'presence:enter', 'presence:exit'}
            page.goto(review.builder + '?project=' + source['id'])
            wait_ready(page)
            for identifier, kind, events in ((owner_id, 'decorations', ('signal:Inspect',)),
                    (area_id, 'regions', ('presence:enter', 'presence:exit'))):
                modal = open_editor(identifier, kind)
                expect(modal.locator('[data-blueprint-state-events]')).to_have_count(0)
                expect(modal.locator('[data-blueprint-event="change"]')).to_have_count(0)
                expect(modal.locator('[data-blueprint-event^="enter:"]')).to_have_count(0)
                for event in events:
                    control = modal.locator(f'[data-blueprint-event="{event}"]')
                    control.click()
                    allowed_ports = {*object_events, event} if kind == 'decorations' else {'presence:enter', 'presence:exit', 'destroy'}
                    assert set(modal.locator('[data-blueprint-event-port]').evaluate_all('nodes=>nodes.map(node=>node.dataset.blueprintEventPort)')) == allowed_ports
                    modal.locator('[data-blueprint-zoom-reset]').click()
                    page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
                    event_geometry = modal.evaluate(GEOMETRY)
                    metrics.append(event_geometry)
                    assert event_geometry['distances'][event] < 1 and event_geometry['hiddenCount'] == 0, event_geometry
                    assert event_geometry['ports'][event]['output'] == 'next', event_geometry
                    expect(modal.locator('[data-blueprint-instance] input, [data-blueprint-instance] select')).to_have_count(0)
                    records.append({'case': 'signal-and-area-start-wires-leave-their-own-lateral-port-without-event-comparisons', 'event': event})
                modal.locator('[data-blueprint-close]').click()
            idle()
            assert project()['document'] == source['document']
            save_diagnostics()
            assert not failures, failures
        except Exception:
            save_diagnostics()
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'measurements': metrics, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Synthetic solid-color PNGs; no operator campaign or reference artwork.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
