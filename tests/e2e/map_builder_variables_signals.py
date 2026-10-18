"""Exercise private typed variables and named signals through authoring and play.

All source graphs are authored with the real Blueprint controls. Native player
interaction, operation retries and linked updates use the same disposable
campaign, synthetic artwork and isolated server as the Blueprint acceptance suite.
"""
from __future__ import annotations

import json
import time
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import close_panel, set_name, upload_asset, wait_ready


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

        def open_editor(identifier, kind='doors'):
            builder_tool(page, 'select')
            builder_workspace(page)
            target = page.locator(f'[data-builder-{kind}] [data-object-id="{identifier}"]')
            if kind == 'doors':
                target.dblclick()
            else:
                box = target.bounding_box()
                page.mouse.click(box['x'] + box['width'] * .25, box['y'] + box['height'] * .25)
                builder_sidebar(page, 'selection')
                page.locator('[data-builder-edit-behavior]').click()
            modal = page.locator('[data-smart-object-modal]')
            expect(modal).to_be_visible()
            return modal

        def card(modal, identifier):
            return modal.locator(f'[data-blueprint-node="{identifier}"]')

        def parameter(modal, identifier, name, value):
            control = card(modal, identifier).locator(f'[data-blueprint-param="{name}"]')
            if control.evaluate('element=>element.tagName') == 'SELECT':
                control.select_option(str(value).lower() if isinstance(value, bool) else str(value))
            else:
                control.fill(str(value))
                control.dispatch_event('change')

        def add_node(modal, kind, **params):
            before = set(modal.locator('[data-blueprint-node]').evaluate_all(
                'nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            modal.locator('[data-blueprint-add]').click()
            modal.locator(f'[data-blueprint-pick-type="{kind}"]').click()
            after = set(modal.locator('[data-blueprint-node]').evaluate_all(
                'nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            identifier, = after - before
            for name, value in params.items():
                parameter(modal, identifier, name, value)
            return identifier

        def connect(modal, source, target):
            modal.locator('[data-blueprint-fit]').click()
            source.click()
            target.click()

        def data_wire(modal, source, target, output_port, input_port):
            connect(modal, card(modal, source).locator(f'[data-blueprint-data-output="{output_port}"]'),
                    card(modal, target).locator(f'[data-blueprint-data-input="{input_port}"]'))

        def execution_wire(modal, source, target, port='next'):
            connect(modal, card(modal, source).locator(f'[data-blueprint-output="{port}"]'),
                    card(modal, target).locator('[data-blueprint-input]'))

        def wait_game():
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')

        def add_signal(modal, name):
            modal.locator('[data-blueprint-signal-name]').fill(name)
            modal.locator('[data-blueprint-signal-add]').click()
            expect(modal.locator(f'[data-blueprint-event="signal:{name}"]')).to_be_visible()

        def event_wire(modal, name, target):
            connect(modal, modal.locator(f'[data-blueprint-instance] [data-blueprint-event-port="signal:{name}"][aria-pressed=true][data-blueprint-output=next]'),
                    card(modal, target).locator('[data-blueprint-input]'))

        try:
            page.goto(builder)
            wait_ready(page)
            set_name(page, 'Synthetic private variables and named signals')
            door_asset = upload_asset(page, 'door', 'Synthetic named signal receiver.png',
                                      harness.artwork('#427da4'))['id']
            lever_asset = upload_asset(page, 'decoration', 'Synthetic named signal sender.png',
                                       harness.artwork('#bc762e'))['id']
            builder_tool(page, 'door')
            page.locator('[data-builder-brush-material]').select_option(door_asset)
            review.stroke((8, 6), (10, 6))
            builder_tool(page, 'decoration')
            page.locator('[data-builder-brush-material]').select_option(lever_asset)
            review.stroke((12, 10), (14, 12))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=behavior]').select_option('lever')
            close_panel(page)
            initial = review.save()
            door, = initial['document']['doors']
            lever, = initial['document']['decorations']

            # One event writes the element variable; the next receives that
            # committed value rather than the triggering event's old snapshot.
            modal = open_editor(lever['id'], 'decorations')
            legacy = modal.locator('[data-blueprint-state-events]')
            if legacy.get_attribute('open') is None:
                legacy.locator('summary').click()
            modal.locator('[data-blueprint-event="enter:on"]').click()
            armed = add_node(modal, 'setVariable', scope='element', valueType='boolean', name='Armed', value=True)
            stage = add_node(modal, 'emitEvent', scope='element', name='StageNext')
            connect(modal, modal.locator('[data-blueprint-state-port=on]'),
                    card(modal, armed).locator('[data-blueprint-input]'))
            execution_wire(modal, armed, stage)
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator('[data-blueprint-trace]')).to_contain_text('Armed')
            assert review.project(initial['id'])['document'] == initial['document']
            records.append({'case': 'actual-editor-authors-private-boolean-write-and-self-signal-with-nonmutating-simulation'})

            modal.locator('[data-blueprint-signal-name]').fill('Invalid signal name')
            expect(modal.locator('[data-blueprint-signal-add]')).to_be_disabled()
            add_signal(modal, 'StageNext')
            read_armed = add_node(modal, 'getVariable', scope='element', valueType='boolean', name='Armed', default=False)
            stage_condition = add_node(modal, 'condition')
            progress = add_node(modal, 'setVariable', scope='scene', valueType='number', name='Progress', value=3)
            message = add_node(modal, 'setVariable', scope='scene', valueType='text', name='Message', value='Solved')
            recipient = add_node(modal, 'reference', targetId=door['id'])
            emit = add_node(modal, 'emitEvent', scope='element', name='PuzzleSolved')
            data_wire(modal, read_armed, stage_condition, 'value', 'test')
            data_wire(modal, recipient, emit, 'door', 'target')
            event_wire(modal, 'StageNext', stage_condition)
            execution_wire(modal, stage_condition, progress, 'true')
            execution_wire(modal, progress, message)
            execution_wire(modal, message, emit)
            modal.locator('[data-blueprint-fit]').click()
            page.screenshot(path=str(output / 'variables-sender-stage.png'))
            modal.locator('[data-blueprint-save]').click()
            sender = review.save()
            sender_blueprint = sender['document']['decorations'][0]['blueprint']
            assert sender_blueprint['graphs']['signal:StageNext']['nodes']
            records.append({'case': 'actual-editor-chains-typed-element-read-scene-number-text-writes-and-targeted-signal'})

            modal = open_editor(door['id'])
            add_signal(modal, 'PuzzleSolved')
            read_progress = add_node(modal, 'getVariable', scope='scene', valueType='number', name='Progress', default=0)
            compare_progress = add_node(modal, 'compareValue', valueType='number', operator='eq', expected=3)
            read_message = add_node(modal, 'getVariable', scope='scene', valueType='text', name='Message', default='Pending')
            compare_message = add_node(modal, 'compareValue', valueType='text', operator='eq', expected='Solved')
            all_values = add_node(modal, 'all')
            condition = add_node(modal, 'condition')
            opened = add_node(modal, 'state', targetState='open')
            data_wire(modal, read_progress, compare_progress, 'value', 'value')
            data_wire(modal, read_message, compare_message, 'value', 'value')
            data_wire(modal, compare_progress, all_values, 'result', 'a')
            data_wire(modal, compare_message, all_values, 'result', 'b')
            data_wire(modal, all_values, condition, 'result', 'test')
            event_wire(modal, 'PuzzleSolved', condition)
            execution_wire(modal, condition, opened, 'true')
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator(f'[data-blueprint-trace-value="{all_values}"]')).to_contain_text('False')
            expect(modal.locator(f'[data-blueprint-trace-node="{opened}"]')).to_have_count(0)
            modal.locator('[data-blueprint-fit]').click()
            page.screenshot(path=str(output / 'variables-receiver-typed-comparisons.png'))
            modal.locator('[data-blueprint-simulation-variables] > summary').click()
            for name, value in (('Progress', '3'), ('Message', 'Solved')):
                override = modal.locator(f'[data-blueprint-simulation-variable="{name}"]')
                override.fill(value)
                override.dispatch_event('change')
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator(f'[data-blueprint-trace-value="{all_values}"]')).to_contain_text('True')
            expect(modal.locator(f'[data-blueprint-trace-node="{opened}"]')).to_contain_text('Opened')
            assert review.project(initial['id'])['document'] == sender['document']
            page.screenshot(path=str(output / 'variables-local-preview-overrides.png'))
            add_signal(modal, 'EmptySignal')
            modal.locator('[data-blueprint-save]').click()
            authored = review.save()
            assert 'signal:EmptySignal' in authored['document']['doors'][0]['blueprint']['graphs']
            receiver_nodes = authored['document']['doors'][0]['blueprint']['graphs']['signal:PuzzleSolved']['nodes']
            assert next(node for node in receiver_nodes if node['id'] == read_progress)['default'] == 0
            assert next(node for node in receiver_nodes if node['id'] == read_message)['default'] == 'Pending'
            records.append({'case': 'actual-editor-receiver-compares-number-and-text-values-and-simulation-has-private-defaults'})
            records.append({'case': 'local-simulation-overrides-number-and-text-without-changing-project-or-authored-fallbacks'})

            # Retyping a value changes its sockets and prunes incompatible data
            # wires. The modal's Undo restores the original typed connection.
            modal = open_editor(door['id'])
            modal.locator('[data-blueprint-event="signal:PuzzleSolved"]').click()
            parameter(modal, read_progress, 'valueType', 'text')
            expect(card(modal, read_progress).locator('[data-blueprint-data-output=value]')).to_have_attribute('data-port-type', 'text')
            modal.locator('[data-blueprint-undo]').click()
            expect(card(modal, read_progress).locator('[data-blueprint-data-output=value]')).to_have_attribute('data-port-type', 'number')
            modal.locator('[data-blueprint-fit]').click()
            source = card(modal, read_progress).locator('[data-blueprint-data-output=value]')
            source.scroll_into_view_if_needed()
            start = source.bounding_box()
            blank = modal.locator('[data-blueprint-canvas]').evaluate("""canvas=>{
              const r=canvas.getBoundingClientRect();
              for(const fy of [.85,.65,.15,.4])for(const fx of [.88,.7,.5,.28,.1]){
                const x=r.left+Math.max(12,Math.min(r.width-12,r.width*fx));
                const y=r.top+Math.max(12,Math.min(r.height-12,r.height*fy));
                const hit=document.elementFromPoint(x,y);
                if(hit&&canvas.contains(hit)&&!hit.closest('[data-blueprint-node]'))return{x,y};
              }throw Error('No empty graph point is visible');
            }""")
            before_drag = set(modal.locator('[data-blueprint-node]').evaluate_all(
                'nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            page.mouse.move(start['x'] + start['width'] / 2, start['y'] + start['height'] / 2)
            page.mouse.down()
            page.mouse.move(blank['x'], blank['y'], steps=10)
            page.mouse.up()
            expect(modal.locator('[data-blueprint-pick-type=compareValue]')).to_be_visible()
            modal.locator('[data-blueprint-pick-type=compareValue]').click()
            after_drag = set(modal.locator('[data-blueprint-node]').evaluate_all(
                'nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            dragged_compare, = after_drag - before_drag
            expect(card(modal, dragged_compare).locator('[data-blueprint-param=valueType]')).to_have_value('number')
            expect(card(modal, dragged_compare).locator('[data-blueprint-data-input=value]')).to_have_attribute('data-port-type', 'number')
            numeric_default = add_node(modal, 'getVariable')
            parameter(modal, numeric_default, 'valueType', 'number')
            expect(card(modal, numeric_default).locator('[data-blueprint-param=name]')).to_have_value('variable')
            next_get = add_node(modal, 'getVariable')
            expect(card(modal, next_get).locator('[data-blueprint-param=name]')).to_have_value('variable2')
            next_set = add_node(modal, 'setVariable')
            assert card(modal, next_set).locator('[data-blueprint-param=name]').input_value() != 'variable'
            expect(card(modal, next_set).locator('[data-blueprint-param=valueType]')).to_have_value('boolean')
            add_signal(modal, 'CancelledSignal')
            modal.locator('[data-blueprint-undo]').click()
            expect(modal.locator('[data-blueprint-event="signal:CancelledSignal"]')).to_have_count(0)
            modal.locator('[data-blueprint-redo]').click()
            expect(modal.locator('[data-blueprint-event="signal:CancelledSignal"]')).to_have_count(1)
            modal.locator('[data-blueprint-event="signal:CancelledSignal"]').click()
            add_node(modal, 'emitEvent', scope='scene', name='SceneBroadcast')
            modal.locator('[data-blueprint-cancel]').click()
            assert review.save()['document'] == authored['document']
            records.append({'case': 'typed-port-reconfiguration-undo-and-cancel-preserve-the-authored-project'})
            records.append({'case': 'dragging-a-number-value-onto-empty-canvas-creates-a-compatible-typed-comparison'})
            records.append({'case': 'palette-default-variable-names-avoid-existing-incompatible-numeric-declarations'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    page.goto(builder + '?project=' + authored['id'])
                    wait_ready(page)
                    modal = open_editor(door['id'])
                    expect(modal.locator('[data-blueprint-event="signal:EmptySignal"]')).to_have_count(1)
                    modal.locator('[data-blueprint-event="signal:PuzzleSolved"]').click()
                    expect(card(modal, read_progress).locator('[data-blueprint-param=name]')).to_have_value('Progress')
                    expect(card(modal, read_message).locator('[data-blueprint-param=default]')).to_have_value('Pending')
                    modal.locator('[data-blueprint-add]').click()
                    modal.locator('[data-blueprint-picker-search]').fill('getVariable')
                    expect(modal.locator('[data-blueprint-pick-type=getVariable]')).to_be_visible()
                    modal.locator('[data-blueprint-picker-cancel]').click()
                    metrics = modal.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'variables-{locale}-{width}.png'))
                    for _ in range(10):
                        page.keyboard.press('Tab')
                        assert modal.evaluate('element=>element.closest("[role=dialog]").contains(document.activeElement)')
                    page.keyboard.press('Escape')
                    expect(modal).to_have_count(0)
                    records.append({'case': 'localized-responsive-variable-editor-preserves-authored-names-and-focus',
                                    'locale': locale, 'width': width, 'metrics': metrics})

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(builder + '?project=' + authored['id'])
            wait_ready(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            wait_game()
            project = review.project(authored['id'])
            scene = project['sceneId']

            def command(area, action, data, target=page):
                return target.evaluate("""a=>gravewrightRealtime.mapCommand('objects',{
                  mapId:a.scene,area:a.area,action:a.action,data:a.data})""",
                                       {'scene': scene, 'area': area, 'action': action, 'data': data})

            def state(target=page):
                response = target.request.get(f'/api/maps/{scene}/state')
                assert response.ok, response.text()
                return response.json()

            def automation():
                response = page.request.get(f'/api/maps/{scene}/automation')
                assert response.ok, response.text()
                return response.json()

            command('lighting', 'update', {'mode': 'none', 'darkness': 0, 'lights_out': False})
            page.evaluate("""a=>gravewrightRealtime.mapCommand('update',{
              mapId:a.scene,version:a.version,settings:{visibility:'players'}})""",
                          {'scene': scene, 'version': project['sceneVersion']})
            page.evaluate("scene=>gravewrightRealtime.mapCommand('activate',{mapId:scene})", scene)
            native = state()
            native_door, = [row for row in native['walls'] if row['kind'] == 'door']
            native_lever, = [row for row in native['images'] if row.get('lever')]
            reference, = [node for node in native_lever['blueprint']['graphs']['signal:StageNext']['nodes']
                          if node['type'] == 'reference']
            assert reference['targetId'] == native_door['id']
            records.append({'case': 'generation-preserves-signal-events-and-remaps-the-private-recipient-reference'})

            player_context = browser.new_context(base_url=base, viewport={'width': 1200, 'height': 800})
            guests.append(player_context)
            player_context.add_cookies([{**seed['sessions']['player'], 'url': base}])
            player = player_context.new_page()
            observe(player)
            player.goto(f'{base}/game/{campaign}')
            player.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(player.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            control = player.locator(f'[data-smart-image-id="{native_lever["id"]}"][data-smart-image-action=interact]')
            control.focus()
            control.press('Enter')
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                after = state()
                if next(row for row in after['walls'] if row['id'] == native_door['id'])['door_state'] == 'open':
                    break
                player.wait_for_timeout(80)
            else:
                raise AssertionError({'state': after, 'automation': automation()})
            stored_lever = next(row for row in after['images'] if row['id'] == native_lever['id'])
            assert stored_lever['automationVariables']['Armed'] == {'type': 'boolean', 'value': True}, stored_lever
            variables = automation()['variables']
            assert variables['scene']['Progress'] == {'type': 'number', 'value': 3}, variables
            assert variables['scene']['Message'] == {'type': 'text', 'value': 'Solved'}, variables
            assert 'signal:PuzzleSolved' in json.dumps(automation()['runs'])
            player.screenshot(path=str(output / 'variables-player-opens-signal-receiver.png'))
            records.append({'case': 'real-player-interaction-delivers-two-signals-and-compares-newly-persisted-private-variables'})

            public = state(player)
            serialized = json.dumps(public)
            assert 'automationVariables' not in serialized and '"blueprint":' not in serialized, serialized
            assert all(secret not in serialized for secret in ('Progress', 'Message', 'PuzzleSolved', 'StageNext', 'Armed'))
            assert player.request.get(f'/api/maps/{scene}/automation').status == 404
            records.append({'case': 'player-projection-omits-scene-and-element-memory-signals-and-private-graphs'})

            # Retry the exact same operation ID without replaying graph events.
            request_id = str(uuid4())

            def receipt(identifier):
                return player.evaluate("""a=>new Promise((resolve,reject)=>{
                  const stop=()=>{clearTimeout(timer);removeEventListener('gravewright:api-event',receive);};
                  const receive=({detail})=>{
                    if(detail.payload.requestId!==a.id||!['maps.ack','maps.error'].includes(detail.type))return;
                    stop();detail.type==='maps.ack'?resolve(detail.payload.result):reject(Error(detail.payload.message));};
                  const timer=setTimeout(()=>{stop();reject(Error('Signal receipt timed out'));},15000);
                  addEventListener('gravewright:api-event',receive);
                  gravewrightRealtime.tableTool('maps.command',{action:'objects',requestId:a.id,
                    data:{mapId:a.scene,area:'images',action:'interact',data:{image_id:a.image}}});
                })""", {'scene': scene, 'id': identifier, 'image': native_lever['id']})

            original_receipt = receipt(request_id)
            before_retry, before_runs = state(), automation()['runs']
            assert receipt(request_id) == original_receipt
            assert state() == before_retry and automation()['runs'] == before_runs
            records.append({'case': 'duplicate-operation-reuses-the-receipt-without-replaying-signals-or-memory-writes'})

            player.reload()
            player.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            page.reload()
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            assert automation()['variables'] == variables
            records.append({'case': 'gm-and-player-reconnect-retain-private-element-and-scene-memory'})

            refusal = player.evaluate("""a=>gravewrightRealtime.mapCommand('objects',{
                mapId:a.scene,area:'automation',action:'emitEvent',data:{name:'PuzzleSolved',targetId:a.door}})
                .then(result=>({accepted:true,result}),error=>({accepted:false,message:error.message}))""",
                                      {'scene': scene, 'door': native_door['id']})
            assert refusal['accepted'] is False, refusal
            assert automation()['variables'] == variables
            records.append({'case': 'player-cannot-inject-an-authored-named-signal-through-a-forged-command'})

            # Editing the fallback does not replace already stored values. The
            # linked update keeps the same scene, element IDs and live memory.
            page.goto(builder + '?project=' + authored['id'])
            wait_ready(page)
            modal = open_editor(door['id'])
            modal.locator('[data-blueprint-event="signal:PuzzleSolved"]').click()
            parameter(modal, read_progress, 'default', 99)
            modal.locator('[data-blueprint-save]').click()
            modal = open_editor(lever['id'], 'decorations')
            modal.locator('[data-blueprint-event="signal:StageNext"]').click()
            parameter(modal, emit, 'scope', 'scene')
            expect(card(modal, emit).locator('[data-blueprint-data-input=target]')).to_have_count(0)
            modal.locator('[data-blueprint-save]').click()
            review.save()
            builder_sidebar(page, 'review')
            with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                page.locator('[data-builder-review-update]').click()
            assert updated.value.ok, updated.value.text()
            wait_game()
            assert review.project(authored['id'])['sceneId'] == scene
            assert automation()['variables'] == variables
            live = state()
            assert next(row for row in live['images'] if row['id'] == native_lever['id'])['automationVariables']['Armed']['value'] is True
            assert next(row for row in live['walls'] if row['id'] == native_door['id'])['door_state'] == 'open'
            records.append({'case': 'linked-scene-update-preserves-live-memory-when-authored-get-fallback-changes'})
            command('walls', 'door', {'wall_id': native_door['id'], 'door_state': 'closed'})
            control = player.locator(f'[data-smart-image-id="{native_lever["id"]}"][data-smart-image-action=interact]')
            expect(control).to_have_attribute('aria-pressed', 'false')
            control.focus()
            control.press('Enter')
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                final = state()
                if next(row for row in final['walls'] if row['id'] == native_door['id'])['door_state'] == 'open':
                    break
                player.wait_for_timeout(80)
            else:
                raise AssertionError({'state': final, 'automation': automation()})
            assert automation()['variables'] == variables
            records.append({'case': 'actual-editor-scene-broadcast-reaches-receiver-after-linked-update-and-retains-typed-memory'})

            for locale, width in (('en', 1440), ('en', 390), ('pt-BR', 390), ('es', 390)):
                change_locale(page, locale, campaign)
                # Open through the desktop host toolbar, then exercise the new
                # window's responsive geometry without changing host navigation.
                page.set_viewport_size({'width': 1440, 'height': 900})
                page.goto(f'/game/{campaign}')
                page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
                page.locator('.game-menubar__layer').nth(5).click()
                page.locator('[data-dock-tool=automation]').click()
                log = page.locator('.automation-log')
                log.locator('[data-automation-view=variables]').click()
                expect(log.locator('[data-automation-variable-name="Progress"]')).to_contain_text('3')
                expect(log.locator('[data-automation-variable-name="Message"]')).to_contain_text('Solved')
                expect(log.locator('[data-automation-variable-name="Armed"]')).to_be_visible()
                page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                metrics = log.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], metrics
                page.screenshot(path=str(output / f'variable-inspector-{locale}-{width}.png'))
                log.locator('[data-automation-close]').click()
                records.append({'case': 'localized-gm-variable-inspector-shows-scopes-types-and-authored-values',
                                'locale': locale, 'width': width, 'metrics': metrics})

            page.locator('[data-dock-tool=automation]').click()
            log = page.locator('.automation-log')
            log.locator('[data-automation-view=variables]').click()
            log.locator('[data-automation-variable-name="Progress"] [data-automation-reset-variable]').click()
            expect(log.locator('[data-automation-variable-name="Progress"]')).to_have_count(0)
            reset = automation()['variables']
            assert 'Progress' not in reset['scene'] and reset['scene']['Message'] == variables['scene']['Message']
            assert reset['elements'] == variables['elements']
            assert next(row for row in state()['walls'] if row['id'] == native_door['id'])['door_state'] == 'open'
            records.append({'case': 'gm-reset-removes-only-the-chosen-variable-without-triggering-gameplay'})

        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            (output / 'progress.json').write_text(json.dumps({'cases': records, 'pageErrors': errors,
                                                             'nativeDialogs': dialogs}, indent=2,
                                                            ensure_ascii=False), encoding='utf-8')
            raise
        finally:
            for guest in guests:
                guest.close()
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Generated solid-color PNGs and silent WAV; no operator data.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
