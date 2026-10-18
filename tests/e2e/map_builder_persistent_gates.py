"""Exercise persistent Counter, Once and Cooldown gates through authoring and play.

The actual Blueprint controls author every source graph. Native player input,
receipts, reconnects, linked updates and GM recovery use a disposable campaign,
synthetic artwork and the isolated Blueprint acceptance server.
"""
from __future__ import annotations

from copy import deepcopy
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
        player_context = None

        def observe(target):
            target.on('pageerror', lambda error: errors.append(str(error)))
            target.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))

        observe(page)
        review = BuilderReview(page, campaign)

        def open_editor(identifier):
            builder_tool(page, 'select')
            builder_workspace(page)
            target = page.locator(f'[data-builder-decorations] [data-object-id="{identifier}"]')
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
            if control.get_attribute('type') == 'checkbox':
                control.set_checked(value)
            elif control.evaluate('element=>element.tagName') == 'SELECT':
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

        def execution_wire(modal, source, target, port='next'):
            connect(modal, card(modal, source).locator(f'[data-blueprint-output="{port}"]'),
                    card(modal, target).locator('[data-blueprint-input]'))

        def data_wire(modal, source, target, output_port, input_port):
            connect(modal, card(modal, source).locator(f'[data-blueprint-data-output="{output_port}"]'),
                    card(modal, target).locator(f'[data-blueprint-data-input="{input_port}"]'))

        def state_wire(modal, target):
            connect(modal, modal.locator('[data-blueprint-state-port=on]'),
                    card(modal, target).locator('[data-blueprint-input]'))

        def wait_game():
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')

        try:
            page.goto(builder)
            wait_ready(page)
            set_name(page, 'Synthetic persistent puzzle gates')
            door_asset = upload_asset(page, 'door', 'Synthetic gated door.png',
                                      harness.artwork('#426f95'))['id']
            lever_asset = upload_asset(page, 'decoration', 'Synthetic gate lever.png',
                                       harness.artwork('#b47d32'))['id']
            builder_tool(page, 'door')
            page.locator('[data-builder-brush-material]').select_option(door_asset)
            review.stroke((8, 6), (10, 6))
            builder_tool(page, 'light')
            review.stroke((12, 9), (12, 9))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=enabled]').uncheck()
            close_panel(page)
            builder_tool(page, 'decoration')
            page.locator('[data-builder-brush-material]').select_option(lever_asset)
            review.stroke((12, 12), (14, 14))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=behavior]').select_option('lever')
            close_panel(page)
            review.stroke((20, 12), (22, 14))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=behavior]').select_option('lever')
            close_panel(page)
            initial = review.save()
            door, = initial['document']['doors']
            light, = initial['document']['lights']
            main_lever, cooldown_lever = initial['document']['decorations']

            modal = open_editor(main_lever['id'])
            modal.locator('[data-blueprint-state-port=on]').click()
            counter = add_node(modal, 'counter', target=3)
            once = add_node(modal, 'once')
            recipient = add_node(modal, 'reference', targetId=door['id'])
            opened = add_node(modal, 'state')
            lit = add_node(modal, 'light', targetId=light['id'], enabled=True)
            data_wire(modal, recipient, opened, 'door', 'target')
            parameter(modal, opened, 'targetState', 'open')
            state_wire(modal, counter)
            execution_wire(modal, counter, once, 'true')
            execution_wire(modal, once, opened, 'true')
            execution_wire(modal, opened, lit)
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator(f'[data-blueprint-trace-node="{counter}"]')).to_be_visible()
            expect(modal.locator(f'[data-blueprint-trace-node="{opened}"]')).to_have_count(0)
            assert review.project(initial['id'])['document'] == initial['document']
            records.append({'case': 'actual-editor-authors-counter-once-chain-and-local-preview-does-not-write-project'})
            modal.locator('[data-blueprint-simulation-gates] > summary').click()
            preview_count = modal.locator(f'[data-blueprint-simulation-memory="{counter}"]')
            preview_count.fill('2')
            preview_count.dispatch_event('change')
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator(f'[data-blueprint-trace-node="{opened}"]')).to_be_visible()
            modal.locator(f'[data-blueprint-simulation-memory="{once}"]').select_option('true')
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator(f'[data-blueprint-trace-node="{once}"]')).to_be_visible()
            expect(modal.locator(f'[data-blueprint-trace-node="{opened}"]')).to_have_count(0)
            assert review.project(initial['id'])['document'] == initial['document']
            records.append({'case': 'temporary-counter-and-once-preview-values-change-branches-without-writing-game-state'})
            parameter(modal, counter, 'target', 4)
            modal.locator('[data-blueprint-undo]').click()
            expect(card(modal, counter).locator('[data-blueprint-param=target]')).to_have_value('3')
            modal.locator('[data-blueprint-fit]').click()
            page.screenshot(path=str(output / 'gates-counter-once-authoring.png'))
            modal.locator('[data-blueprint-save]').click()
            with_counter = review.save()
            records.append({'case': 'gate-parameter-undo-restores-target-and-saves-connected-true-branches'})

            modal = open_editor(cooldown_lever['id'])
            modal.locator('[data-blueprint-state-port=on]').click()
            cooldown = add_node(modal, 'cooldown', seconds=5)
            cooldown_recipient = add_node(modal, 'reference', targetId=door['id'])
            cooldown_opened = add_node(modal, 'state')
            data_wire(modal, cooldown_recipient, cooldown_opened, 'door', 'target')
            parameter(modal, cooldown_opened, 'targetState', 'open')
            state_wire(modal, cooldown)
            execution_wire(modal, cooldown, cooldown_opened, 'true')
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator(f'[data-blueprint-trace-node="{cooldown_opened}"]')).to_be_visible()
            modal.locator('[data-blueprint-simulation-gates] > summary').click()
            preview_remaining = modal.locator(f'[data-blueprint-simulation-memory="{cooldown}"]')
            preview_remaining.fill('2')
            preview_remaining.dispatch_event('change')
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator(f'[data-blueprint-trace-node="{cooldown_opened}"]')).to_have_count(0)
            assert review.project(initial['id'])['document'] == with_counter['document']
            modal.locator('[data-blueprint-save]').click()
            authored = review.save()
            records.append({'case': 'actual-editor-authors-cooldown-true-branch-and-preview-is-independent-of-game-memory'})

            modal = open_editor(main_lever['id'])
            modal.locator('[data-blueprint-state-port=on]').click()
            parameter(modal, counter, 'target', 9)
            card(modal, once).locator('[data-blueprint-delete]').click()
            modal.locator('[data-blueprint-cancel]').click()
            assert review.save()['document'] == authored['document']
            records.append({'case': 'cancelling-gate-parameter-and-node-deletion-preserves-authored-project'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    page.goto(builder + '?project=' + authored['id'])
                    wait_ready(page)
                    modal = open_editor(main_lever['id'])
                    modal.locator('[data-blueprint-state-port=on]').click()
                    expect(card(modal, counter).locator('[data-blueprint-param=target]')).to_have_value('3')
                    modal.locator('[data-blueprint-add]').click()
                    modal.locator('[data-blueprint-picker-search]').fill('cooldown')
                    expect(modal.locator('[data-blueprint-pick-type=cooldown]')).to_be_visible()
                    modal.locator('[data-blueprint-picker-cancel]').click()
                    modal.locator('[data-blueprint-fit]').click()
                    metrics = modal.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'gates-editor-{locale}-{width}.png'))
                    for _ in range(8):
                        page.keyboard.press('Tab')
                        assert modal.evaluate('element=>element.closest("[role=dialog]").contains(document.activeElement)')
                    page.keyboard.press('Escape')
                    expect(modal).to_have_count(0)
                    records.append({'case': 'localized-responsive-persistent-gates-preserve-parameters-and-modal-focus',
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
            native_light, = native['lights']
            native_main, = [row for row in native['images'] if row.get('lever') and
                            any(node['id'] == counter for graph in row['blueprint']['graphs'].values()
                                for node in graph['nodes'])]
            native_cooldown, = [row for row in native['images'] if row.get('lever') and row['id'] != native_main['id']]
            assert not automation()['memory']['elements'], automation()
            records.append({'case': 'generation-remaps-effect-targets-and-starts-gates-with-empty-private-memory'})

            player_context = browser.new_context(base_url=base, viewport={'width': 1200, 'height': 800})
            player_context.add_cookies([{**seed['sessions']['player'], 'url': base}])
            player = player_context.new_page()
            observe(player)
            player.goto(f'{base}/game/{campaign}')
            player.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(player.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

            def interact(element, pressed):
                control = player.locator(f'[data-smart-image-id="{element}"][data-smart-image-action=interact]')
                expect(control).to_have_attribute('aria-pressed', str(not pressed).lower())
                control.focus()
                control.press('Enter')
                expect(control).to_have_attribute('aria-pressed', str(pressed).lower())

            def wall_state():
                return next(row for row in state()['walls'] if row['id'] == native_door['id'])['door_state']

            def light_enabled():
                return next(row for row in state()['lights'] if row['id'] == native_light['id'])['enabled']

            def memory():
                return automation()['memory']['elements']

            def node_memory(element, identifier):
                return memory()[element]['enter:on'][identifier]

            for activation in (1, 2, 3):
                interact(native_main['id'], True)
                assert node_memory(native_main['id'], counter) == {'type': 'counter', 'value': activation}, automation()
                assert wall_state() == ('open' if activation == 3 else 'closed')
                assert light_enabled() is (activation == 3)
                if activation < 3:
                    before_off = deepcopy(memory())
                    interact(native_main['id'], False)
                    assert memory() == before_off
            spent_memory = deepcopy(memory())
            assert node_memory(native_main['id'], once) == {'type': 'once', 'value': True}
            player.screenshot(path=str(output / 'gates-player-third-activation-opens-door.png'))
            records.append({'case': 'real-player-third-on-activation-opens-door-and-enables-native-light'})
            records.append({'case': 'intermediate-off-events-do-not-consume-counter-or-once-memory'})

            command('walls', 'door', {'wall_id': native_door['id'], 'door_state': 'closed'})
            command('lights', 'update', {'light_id': native_light['id'], 'enabled': False})
            interact(native_main['id'], False)
            interact(native_main['id'], True)
            assert node_memory(native_main['id'], counter) == {'type': 'counter', 'value': 4}
            assert node_memory(native_main['id'], once) == {'type': 'once', 'value': True}
            assert wall_state() == 'closed' and light_enabled() is False
            spent_memory = deepcopy(memory())
            records.append({'case': 'counter-keeps-counting-and-spent-once-blocks-later-otherwise-eligible-events'})

            public = json.dumps(state(player))
            assert 'automationMemory' not in public and '"blueprint":' not in public, public
            assert player.request.get(f'/api/maps/{scene}/automation').status == 404
            records.append({'case': 'player-projection-hides-persistent-gate-memory-and-authoring-graphs'})

            request_id = str(uuid4())

            def receipt(identifier):
                return player.evaluate("""a=>new Promise((resolve,reject)=>{
                  const stop=()=>{clearTimeout(timer);removeEventListener('gravewright:api-event',receive);};
                  const receive=({detail})=>{
                    if(detail.payload.requestId!==a.id||!['maps.ack','maps.error'].includes(detail.type))return;
                    stop();detail.type==='maps.ack'?resolve(detail.payload.result):reject(Error(detail.payload.message));};
                  const timer=setTimeout(()=>{stop();reject(Error('Gate receipt timed out'));},15000);
                  addEventListener('gravewright:api-event',receive);
                  gravewrightRealtime.tableTool('maps.command',{action:'objects',requestId:a.id,
                    data:{mapId:a.scene,area:'images',action:'interact',data:{image_id:a.image}}});
                })""", {'scene': scene, 'id': identifier, 'image': native_main['id']})

            original_receipt = receipt(request_id)
            before_retry, before_runs = state(), automation()['runs']
            assert receipt(request_id) == original_receipt
            assert state() == before_retry and automation()['runs'] == before_runs
            records.append({'case': 'duplicate-operation-reuses-receipt-without-toggling-lever-or-mutating-gate-memory'})

            player.reload()
            player.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            page.reload()
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            assert memory() == spent_memory
            records.append({'case': 'gm-and-player-reconnect-retain-counter-and-once-progress'})

            interact(native_cooldown['id'], True)
            assert wall_state() == 'open'
            accepted_memory = deepcopy(node_memory(native_cooldown['id'], cooldown))
            command('walls', 'door', {'wall_id': native_door['id'], 'door_state': 'closed'})
            command('images', 'interact', {'image_id': native_cooldown['id']}, player)
            command('images', 'interact', {'image_id': native_cooldown['id']}, player)
            assert wall_state() == 'closed'
            assert node_memory(native_cooldown['id'], cooldown) == accepted_memory
            records.append({'case': 'cooldown-first-activation-passes-and-immediate-next-activation-is-blocked'})
            wait_started = time.monotonic()
            player.wait_for_timeout(5100)
            command('images', 'interact', {'image_id': native_cooldown['id']}, player)
            command('images', 'interact', {'image_id': native_cooldown['id']}, player)
            assert wall_state() == 'open'
            assert node_memory(native_cooldown['id'], cooldown) != accepted_memory
            records.append({'case': 'cooldown-becomes-eligible-after-server-deadline',
                            'waitedSeconds': round(time.monotonic() - wait_started, 3)})

            persisted = deepcopy(memory())
            page.goto(builder + '?project=' + authored['id'])
            wait_ready(page)
            set_name(page, 'Synthetic persistent puzzle gates updated')
            modal = open_editor(main_lever['id'])
            modal.locator('[data-blueprint-state-port=on]').click()
            parameter(modal, counter, 'target', 4)
            modal.locator('[data-blueprint-save]').click()
            modal = open_editor(cooldown_lever['id'])
            modal.locator('[data-blueprint-state-port=on]').click()
            parameter(modal, cooldown, 'seconds', 6)
            modal.locator('[data-blueprint-save]').click()
            review.save()
            builder_sidebar(page, 'review')
            with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                page.locator('[data-builder-review-update]').click()
            assert updated.value.ok, updated.value.text()
            wait_game()
            assert review.project(authored['id'])['sceneId'] == scene
            assert memory() == persisted
            assert wall_state() == 'open'
            records.append({'case': 'linked-project-update-preserves-gate-progress-native-ids-and-live-effects'})

            for locale, width in (('en', 1440), ('en', 390), ('pt-BR', 390), ('es', 390)):
                change_locale(page, locale, campaign)
                page.set_viewport_size({'width': 1440, 'height': 900})
                page.goto(f'/game/{campaign}')
                page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
                page.locator('.game-menubar__layer').nth(5).click()
                page.locator('[data-dock-tool=automation]').click()
                log = page.locator('.automation-log')
                log.locator('[data-automation-view=memory]').click()
                expect(log.locator(f'[data-automation-memory-node="{counter}"]')).to_be_visible()
                expect(log.locator(f'[data-automation-memory-node="{once}"]')).to_be_visible()
                expect(log.locator(f'[data-automation-memory-node="{cooldown}"]')).to_be_visible()
                page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                metrics = log.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], metrics
                page.screenshot(path=str(output / f'gate-memory-{locale}-{width}.png'))
                log.locator('[data-automation-close]').click()
                records.append({'case': 'localized-gm-memory-inspector-shows-counter-once-and-cooldown-progress',
                                'locale': locale, 'width': width, 'metrics': metrics})

            before_reset = deepcopy(memory())
            runs_before_reset = automation()['runs']
            stale_reset = page.evaluate("""a=>gravewrightRealtime.mapCommand('objects',{
              mapId:a.scene,area:'automation',action:'reset-memory',
              data:{elementId:a.element,event:'enter:on',nodeId:a.node,expected:{type:'counter',value:2}}})
              .then(result=>({accepted:true,result}),error=>({accepted:false,message:error.message}))""",
                                       {'scene': scene, 'element': native_main['id'], 'node': counter})
            assert stale_reset['accepted'] is False, stale_reset
            assert 'changed' in stale_reset['message'].lower(), stale_reset
            assert memory() == before_reset and automation()['runs'] == runs_before_reset
            records.append({'case': 'stale-gm-memory-reset-is-rejected-without-overwriting-progress-or-running-effects'})
            page.locator('[data-dock-tool=automation]').click()
            log = page.locator('.automation-log')
            log.locator('[data-automation-view=memory]').click()
            log.locator(f'[data-automation-memory-node="{once}"] [data-automation-reset-memory]').click()
            expect(log.locator(f'[data-automation-memory-node="{once}"]')).to_have_count(0)
            expected_reset = deepcopy(before_reset)
            del expected_reset[native_main['id']]['enter:on'][once]
            assert memory() == expected_reset
            assert automation()['runs'] == runs_before_reset and wall_state() == 'open'
            log.locator('[data-automation-close]').click()
            command('walls', 'door', {'wall_id': native_door['id'], 'door_state': 'closed'})
            expect(player.locator(f'[data-smart-image-id="{native_main["id"]}"][data-smart-image-action=interact]')).to_have_attribute('aria-pressed', 'false')
            interact(native_main['id'], True)
            assert wall_state() == 'open' and node_memory(native_main['id'], once) == {'type': 'once', 'value': True}
            records.append({'case': 'gm-node-reset-clears-only-once-without-running-effects-and-next-eligible-event-passes'})

            refused = player.evaluate("""a=>gravewrightRealtime.mapCommand('objects',{
              mapId:a.scene,area:'automation',action:'reset-memory',
              data:{elementId:a.element,event:'enter:on',nodeId:a.node,expected:a.expected}})
              .then(result=>({accepted:true,result}),error=>({accepted:false,message:error.message}))""",
                                      {'scene': scene, 'element': native_main['id'], 'node': once,
                                       'expected': node_memory(native_main['id'], once)})
            assert refused['accepted'] is False, refused
            assert node_memory(native_main['id'], once) == {'type': 'once', 'value': True}
            records.append({'case': 'player-cannot-reset-persistent-gates-through-a-forged-command'})

            before_counter_reset = deepcopy(memory())
            page.locator('[data-dock-tool=automation]').click()
            log = page.locator('.automation-log')
            log.locator('[data-automation-view=memory]').click()
            log.locator(f'[data-automation-memory-node="{counter}"] [data-automation-reset-memory]').click()
            expect(log.locator(f'[data-automation-memory-node="{counter}"]')).to_have_count(0)
            expected_counter_reset = deepcopy(before_counter_reset)
            del expected_counter_reset[native_main['id']]['enter:on'][counter]
            assert memory() == expected_counter_reset and wall_state() == 'open'
            log.locator('[data-automation-close]').click()
            command('walls', 'door', {'wall_id': native_door['id'], 'door_state': 'closed'})
            interact(native_main['id'], False)
            interact(native_main['id'], True)
            assert node_memory(native_main['id'], counter) == {'type': 'counter', 'value': 1}
            assert node_memory(native_main['id'], once) == {'type': 'once', 'value': True}
            assert wall_state() == 'closed'
            records.append({'case': 'gm-counter-reset-starts-the-count-again-and-keeps-unrelated-once-and-cooldown-memory'})

            before_cooldown_reset = deepcopy(memory())
            runs_before_cooldown_reset = automation()['runs']
            page.locator('[data-dock-tool=automation]').click()
            log = page.locator('.automation-log')
            log.locator('[data-automation-view=memory]').click()
            log.locator(f'[data-automation-memory-node="{cooldown}"] [data-automation-reset-memory]').click()
            expect(log.locator(f'[data-automation-memory-node="{cooldown}"]')).to_have_count(0)
            expected_cooldown_reset = deepcopy(before_cooldown_reset)
            del expected_cooldown_reset[native_cooldown['id']]
            assert memory() == expected_cooldown_reset
            assert wall_state() == 'closed' and automation()['runs'] == runs_before_cooldown_reset
            log.locator('[data-automation-close]').click()
            command('images', 'interact', {'image_id': native_cooldown['id']}, player)
            interact(native_cooldown['id'], True)
            assert wall_state() == 'open'
            records.append({'case': 'gm-cooldown-reset-clears-only-that-gate-and-next-activation-starts-a-new-deadline'})

        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            (output / 'progress.json').write_text(json.dumps({'cases': records, 'pageErrors': errors,
                                                             'nativeDialogs': dialogs}, indent=2,
                                                            ensure_ascii=False), encoding='utf-8')
            raise
        finally:
            if player_context:
                player_context.close()
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Generated solid-color PNGs; no operator data.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
