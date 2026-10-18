"""Exercise named, persistent one-shot timers through Blueprint authoring and play.

The scenario uses only synthetic artwork and its own campaign, database, media,
sessions and server. The Delay harness supplies the real server restart fixture;
no operator Runner, database or browser session is touched.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import sys
import time
from uuid import uuid4

import map_builder_blueprints as harness
import map_builder_delay as delay_harness
from map_builder import MEASURE, ROOT, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import close_panel, set_name, upload_asset, wait_ready


def check_browser(base, seed, output, executable, restart):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    builder = f'/game/{campaign}/map-builder'
    long_name = 'Countdown' + 'L' * 55
    records, errors, dialogs = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = player_context = None
        page = player = None

        def observe(target):
            target.on('pageerror', lambda error: errors.append(str(error)))
            target.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))

        def create_context(role, viewport=None):
            result = browser.new_context(base_url=base, viewport=viewport or {'width': 1440, 'height': 900})
            result.add_cookies([{**seed['sessions'][role], 'url': base}])
            return result

        context = create_context('gm')
        page = context.new_page()
        observe(page)
        review = BuilderReview(page, campaign)

        def open_editor(identifier, group='doors'):
            builder_tool(page, 'select')
            builder_workspace(page)
            target = page.locator(f'[data-builder-{group}] [data-object-id="{identifier}"]')
            if group == 'doors':
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

        def add_signal(modal, name):
            modal.locator('[data-blueprint-signal-name]').fill(name)
            modal.locator('[data-blueprint-signal-add]').click()
            expect(modal.locator(f'[data-blueprint-event="signal:{name}"]')).to_be_visible()

        def event_wire(modal, target):
            connect(modal, modal.locator('[data-blueprint-instance] [data-blueprint-event-port^="signal:"][aria-pressed=true][data-blueprint-output=next]'),
                    card(modal, target).locator('[data-blueprint-input]'))

        def wait_game(target=None):
            target = target or page
            target.wait_for_url(f'{base}/game/{campaign}')
            target.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(target.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        try:
            page.goto(builder)
            wait_ready(page)
            set_name(page, 'Synthetic named one-shot timer')
            door_asset = upload_asset(page, 'door', 'Synthetic timer door.png', harness.artwork('#426f95'))['id']
            lever_asset = upload_asset(page, 'decoration', 'Synthetic timer control.png', harness.artwork('#b47d32'))['id']
            builder_tool(page, 'door')
            page.locator('[data-builder-brush-material]').select_option(door_asset)
            review.stroke((8, 6), (10, 6))
            builder_tool(page, 'light')
            review.stroke((12, 9), (12, 9))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=enabled]').uncheck()
            close_panel(page)
            for x in (10, 16, 22):
                builder_tool(page, 'decoration')
                page.locator('[data-builder-brush-material]').select_option(lever_asset)
                review.stroke((x, 12), (x + 2, 14))
                builder_sidebar(page, 'selection')
                page.locator('[data-builder-property=behavior]').select_option('lever')
                close_panel(page)
            initial = review.save()
            door, = initial['document']['doors']
            light, = initial['document']['lights']
            senders = initial['document']['decorations']

            modal = open_editor(door['id'])
            add_signal(modal, 'StartCountdown')
            clear = add_node(modal, 'setVariable', scope='scene', valueType='number', name='TimerProgress', value=0)
            start_timer = add_node(modal, 'timer', name='CloseDoor')
            expect(card(modal, start_timer).locator('[data-blueprint-param=action]')).to_have_value('start')
            expect(card(modal, start_timer).locator('[data-blueprint-param=seconds]')).to_have_value('3')
            progress = add_node(modal, 'setVariable', scope='scene', valueType='number', name='TimerProgress', value=1)
            lit = add_node(modal, 'light', targetId=light['id'], enabled=True)
            event_wire(modal, clear)
            for first, second in ((clear, start_timer), (start_timer, progress), (progress, lit)):
                execution_wire(modal, first, second)
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator(f'[data-blueprint-trace-node="{start_timer}"]')).to_be_visible()
            expect(modal.locator(f'[data-blueprint-trace-node="{progress}"]')).to_be_visible()
            expect(modal.locator(f'[data-blueprint-trace-node="{lit}"]')).to_be_visible()
            assert review.project(initial['id'])['document'] == initial['document']
            records.append({'case': 'actual-editor-authors-named-start-and-simulation-continues-immediately-without-persistence'})
            parameter(modal, start_timer, 'seconds', 180)

            add_signal(modal, 'StopCountdown')
            stop_timer = add_node(modal, 'timer', name='CloseDoor', action='stop')
            expect(card(modal, stop_timer).locator('[data-blueprint-param=seconds]')).not_to_be_visible()
            event_wire(modal, stop_timer)
            add_signal(modal, 'RestartCountdown')
            restart_timer = add_node(modal, 'timer', name='CloseDoor', action='restart', seconds=180)
            event_wire(modal, restart_timer)
            add_signal(modal, 'CloseDoor')
            value = add_node(modal, 'getVariable', scope='scene', valueType='number', name='TimerProgress', default=0)
            compare = add_node(modal, 'compareValue', valueType='number', operator='eq', expected=1)
            condition = add_node(modal, 'condition')
            closed = add_node(modal, 'state', targetState='closed')
            dark = add_node(modal, 'light', targetId=light['id'], enabled=False)
            data_wire(modal, value, compare, 'value', 'value')
            data_wire(modal, compare, condition, 'result', 'test')
            event_wire(modal, condition)
            execution_wire(modal, condition, closed, 'true')
            execution_wire(modal, closed, dark)
            modal.locator('[data-blueprint-save]').click()
            owner = review.save()
            stop_source = owner['document']['doors'][0]['blueprint']['graphs']['signal:StopCountdown']
            assert 'seconds' not in next(node for node in stop_source['nodes'] if node['id'] == stop_timer)
            records.append({'case': 'actual-editor-authors-stop-without-duration-restart-and-timeout-signal-reading-a-new-snapshot'})

            for sender, signal in zip(senders, ('StartCountdown', 'StopCountdown', 'RestartCountdown')):
                modal = open_editor(sender['id'], 'decorations')
                legacy = modal.locator('[data-blueprint-state-events]')
                if legacy.get_attribute('open') is None:
                    legacy.locator('summary').click()
                modal.locator('[data-blueprint-event="enter:on"]').click()
                reference = add_node(modal, 'reference', targetId=door['id'])
                emit = add_node(modal, 'emitEvent', scope='element', name=signal)
                data_wire(modal, reference, emit, 'door', 'target')
                connect(modal, modal.locator('[data-blueprint-state-port=on]'),
                        card(modal, emit).locator('[data-blueprint-input]'))
                modal.locator('[data-blueprint-save]').click()
                review.save()
            authored = review.save()

            modal = open_editor(door['id'])
            modal.locator('[data-blueprint-event="signal:StartCountdown"]').click()
            parameter(modal, start_timer, 'action', 'stop')
            expect(card(modal, start_timer).locator('[data-blueprint-param=seconds]')).not_to_be_visible()
            modal.locator('[data-blueprint-undo]').click()
            expect(card(modal, start_timer).locator('[data-blueprint-param=action]')).to_have_value('start')
            expect(card(modal, start_timer).locator('[data-blueprint-param=seconds]')).to_have_value('180')
            parameter(modal, start_timer, 'name', long_name)
            name_hint = card(modal, start_timer).locator('[data-blueprint-timer-event]')
            expect(name_hint).to_contain_text(long_name)
            name_metrics = name_hint.evaluate('element=>({width:element.clientWidth,scrollWidth:element.scrollWidth})')
            assert name_metrics['scrollWidth'] <= name_metrics['width'], name_metrics
            modal.locator('[data-blueprint-fit]').click()
            page.screenshot(path=str(output / 'timer-editor-long-name.png'))
            modal.locator('[data-blueprint-cancel]').click()
            assert review.save()['document'] == authored['document']
            records.append({'case': 'timer-action-hides-duration-undo-restores-it-and-long-name-wraps-before-cancel-discards-edits',
                            'nameLength': len(long_name), 'nameMetrics': name_metrics})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    page.goto(builder + '?project=' + authored['id'])
                    wait_ready(page)
                    modal = open_editor(door['id'])
                    modal.locator('[data-blueprint-event="signal:StartCountdown"]').click()
                    expect(card(modal, start_timer).locator('[data-blueprint-param=name]')).to_have_value('CloseDoor')
                    expect(card(modal, start_timer).locator('[data-blueprint-param=seconds]')).to_have_value('180')
                    modal.locator('[data-blueprint-add]').click()
                    modal.locator('[data-blueprint-picker-search]').fill('timer')
                    expect(modal.locator('[data-blueprint-pick-type=timer]')).to_be_visible()
                    modal.locator('[data-blueprint-picker-cancel]').click()
                    modal.locator('[data-blueprint-fit]').click()
                    metrics = modal.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'timer-editor-{locale}-{width}.png'))
                    for _ in range(8):
                        page.keyboard.press('Tab')
                        assert modal.evaluate('element=>element.closest("[role=dialog]").contains(document.activeElement)')
                    page.keyboard.press('Escape')
                    expect(modal).to_have_count(0)
                    records.append({'case': 'localized-responsive-timer-controls-keep-authored-names-and-modal-focus',
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

            def command(area, action, data, target=None):
                return (target or page).evaluate("""a=>gravewrightRealtime.mapCommand('objects',{
                  mapId:a.scene,area:a.area,action:a.action,data:a.data})""",
                                                {'scene': scene, 'area': area, 'action': action, 'data': data})

            def state(target=None):
                response = (target or page).request.get(f'/api/maps/{scene}/state')
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
            native_senders = {}
            for row in native['images']:
                if not row.get('lever'):
                    continue
                signal_node, = [node for node in row['blueprint']['graphs']['enter:on']['nodes'] if node['type'] == 'emitEvent']
                native_senders[signal_node['name']] = row['id']

            def create_player():
                nonlocal player_context, player
                player_context = create_context('player', {'width': 1200, 'height': 800})
                player = player_context.new_page()
                observe(player)
                player.goto(f'{base}/game/{campaign}')
                wait_game(player)

            def press(signal):
                control = player.locator(f'[data-smart-image-id="{native_senders[signal]}"][data-smart-image-action=interact]')
                if control.get_attribute('aria-pressed') == 'true':
                    control.focus()
                    control.press('Enter')
                    expect(control).to_have_attribute('aria-pressed', 'false')
                control.focus()
                control.press('Enter')
                expect(control).to_have_attribute('aria-pressed', 'true')

            def wall_state():
                return next(row for row in state()['walls'] if row['id'] == native_door['id'])['door_state']

            def light_enabled():
                return next(row for row in state()['lights'] if row['id'] == native_light['id'])['enabled']

            def pending():
                return automation()['delays']

            def open_door():
                command('walls', 'door', {'wall_id': native_door['id'], 'door_state': 'open'})

            def receipt(identifier, image):
                return player.evaluate("""a=>new Promise((resolve,reject)=>{
                  const stop=()=>{clearTimeout(timer);removeEventListener('gravewright:api-event',receive);};
                  const receive=({detail})=>{
                    if(detail.payload.requestId!==a.id||!['maps.ack','maps.error'].includes(detail.type))return;
                    stop();detail.type==='maps.ack'?resolve(detail.payload.result):reject(Error(detail.payload.message));};
                  const timer=setTimeout(()=>{stop();reject(Error('Timer receipt timed out'));},15000);
                  addEventListener('gravewright:api-event',receive);
                  gravewrightRealtime.tableTool('maps.command',{action:'objects',requestId:a.id,
                    data:{mapId:a.scene,area:'images',action:'interact',data:{image_id:a.image}}});
                })""", {'scene': scene, 'id': identifier, 'image': image})

            create_player()
            open_door()
            request_id = str(uuid4())
            first_receipt = receipt(request_id, native_senders['StartCountdown'])
            first, = pending()
            assert first['kind'] == 'timer' and first['name'] == 'CloseDoor', first
            assert first['elementId'] == native_door['id'] and first['nodeId'] == start_timer, first
            assert automation()['variables']['scene']['TimerProgress'] == {'type': 'number', 'value': 1}
            assert wall_state() == 'open' and light_enabled() is True
            assert receipt(request_id, native_senders['StartCountdown']) == first_receipt
            assert pending() == [first]
            records.append({'case': 'player-start-queues-named-timer-and-next-actions-run-immediately-while-receipt-retry-is-idempotent'})
            press('StartCountdown')
            assert pending() == [first], pending()
            records.append({'case': 'second-start-of-same-owner-name-keeps-original-identity-and-deadline'})
            assert 'CloseDoor' not in json.dumps(state(player))
            assert 'automationVariables' not in json.dumps(state(player))
            assert player.request.get(f'/api/maps/{scene}/automation').status == 404
            records.append({'case': 'player-cannot-read-private-timer-name-queue-variable-memory-or-authoring'})

            press('RestartCountdown')
            restarted, = pending()
            assert restarted['id'] != first['id'] and restarted['dueAt'] > first['dueAt'], (first, restarted)
            assert restarted['name'] == first['name'] and restarted['elementId'] == first['elementId']
            stale = page.evaluate("""a=>gravewrightRealtime.mapCommand('objects',{
              mapId:a.scene,area:'automation',action:'cancel-delay',
              data:{delayId:a.job.id,expectedDueAt:a.job.dueAt}})
              .then(result=>({accepted:true,result}),error=>({accepted:false,message:error.message}))""",
                                  {'scene': scene, 'job': first})
            assert stale['accepted'] is False and pending() == [restarted], stale
            records.append({'case': 'restart-replaces-only-the-named-timer-and-a-stale-cancel-cannot-remove-the-replacement'})
            refused = player.evaluate("""a=>gravewrightRealtime.mapCommand('objects',{
              mapId:a.scene,area:'automation',action:'cancel-delay',data:{delayId:a.job.id,expectedDueAt:a.job.dueAt}})
              .then(result=>({accepted:true,result}),error=>({accepted:false,message:error.message}))""",
                                      {'scene': scene, 'job': restarted})
            assert refused['accepted'] is False and pending() == [restarted], refused
            records.append({'case': 'player-cannot-forge-a-gm-timer-cancel-command'})

            stale_restart = page.evaluate("""a=>gravewrightRealtime.mapCommand('objects',{
              mapId:a.scene,area:'automation',action:'restart-timer',
              data:{delayId:a.job.id,expectedDueAt:'2000-01-01T00:00:00Z'}})
              .then(result=>({accepted:true,result}),error=>({accepted:false,message:error.message}))""",
                                          {'scene': scene, 'job': restarted})
            assert stale_restart['accepted'] is False and pending() == [restarted], stale_restart
            refused_restart = player.evaluate("""a=>gravewrightRealtime.mapCommand('objects',{
              mapId:a.scene,area:'automation',action:'restart-timer',
              data:{delayId:a.job.id,expectedDueAt:a.job.dueAt}})
              .then(result=>({accepted:true,result}),error=>({accepted:false,message:error.message}))""",
                                              {'scene': scene, 'job': restarted})
            assert refused_restart['accepted'] is False and pending() == [restarted], refused_restart
            page.locator('.game-menubar__layer').nth(5).click()
            page.locator('[data-dock-tool=automation]').click()
            log = page.locator('.automation-log')
            log.locator('[data-automation-view=delays]').click()
            old_restart = restarted
            log.locator(f'[data-automation-delay-id="{restarted["id"]}"] [data-automation-restart-timer]').click()
            expect(log.locator(f'[data-automation-delay-id="{old_restart["id"]}"]')).to_have_count(0)
            restarted, = pending()
            assert restarted['id'] != old_restart['id'] and restarted['dueAt'] > old_restart['dueAt']
            assert restarted['actor'] == old_restart['actor'] and restarted['seconds'] == old_restart['seconds']
            log.locator('[data-automation-close]').click()
            records.append({'case': 'gm-native-restart-replaces-identity-keeps-original-actor-and-duration-and-rejects-stale-or-player-command'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    page.set_viewport_size({'width': 1440, 'height': 900})
                    page.goto(f'/game/{campaign}')
                    wait_game()
                    page.locator('.game-menubar__layer').nth(5).click()
                    page.locator('[data-dock-tool=automation]').click()
                    log = page.locator('.automation-log')
                    log.locator('[data-automation-view=delays]').click()
                    row = log.locator(f'[data-automation-delay-id="{restarted["id"]}"]')
                    expect(row).to_be_visible()
                    expect(row).to_contain_text('CloseDoor')
                    expect(row.locator('[data-automation-cancel-delay]')).to_be_enabled()
                    expect(row.locator('[data-automation-restart-timer]')).to_be_enabled()
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    metrics = log.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'timer-pending-{locale}-{width}.png'))
                    long_metrics = None
                    if locale == 'pt-BR' and width == 390:
                        # Stress the real row with synthetic display text only.
                        # Runtime timer identity/name and campaign data stay intact.
                        original = row.evaluate('''(element,name)=>{
                          const title=element.querySelector('strong'),hint=element.querySelector('.automation-log__hint');
                          const original={title:title.textContent,hint:hint.textContent};
                          title.textContent=title.textContent.replace('CloseDoor',name);
                          hint.textContent=hint.textContent.replace('CloseDoor',name);
                          return original;
                        }''', long_name)
                        long_metrics = log.evaluate(MEASURE)
                        assert not long_metrics['tiny'] and not long_metrics['overflow'], long_metrics
                        page.screenshot(path=str(output / 'timer-pending-long-name-pt-BR-390.png'))
                        row.evaluate('''(element,original)=>{
                          element.querySelector('strong').textContent=original.title;
                          element.querySelector('.automation-log__hint').textContent=original.hint;
                        }''', original)
                    log.locator('[data-automation-close]').click()
                    records.append({'case': 'localized-responsive-gm-waiting-tab-distinguishes-named-timer-and-shows-cancel-control',
                                    'locale': locale, 'width': width, 'metrics': metrics, 'longNameMetrics': long_metrics})

            assert pending() == [restarted]
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(builder + '?project=' + authored['id'])
            wait_ready(page)
            set_name(page, 'Synthetic named timer renamed while running')
            review.save()
            builder_sidebar(page, 'review')
            with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                page.locator('[data-builder-review-update]').click()
            assert updated.value.ok, updated.value.text()
            wait_game()
            assert pending() == [restarted], pending()
            records.append({'case': 'unrelated-source-name-change-preserves-running-timer-identity-and-original-deadline'})
            press('StopCountdown')
            assert not pending() and wall_state() == 'open' and light_enabled() is True
            records.append({'case': 'authored-stop-removes-the-matching-owner-timer-without-firing-its-signal'})

            def edit_duration(seconds):
                page.set_viewport_size({'width': 1440, 'height': 900})
                page.goto(builder + '?project=' + authored['id'])
                wait_ready(page)
                modal = open_editor(door['id'])
                for event, identifier in (('StartCountdown', start_timer), ('RestartCountdown', restart_timer)):
                    modal.locator(f'[data-blueprint-event="signal:{event}"]').click()
                    parameter(modal, identifier, 'seconds', seconds)
                modal.locator('[data-blueprint-save]').click()
                review.save()
                builder_sidebar(page, 'review')
                with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                    page.locator('[data-builder-review-update]').click()
                assert updated.value.ok, updated.value.text()
                wait_game()

            change_locale(page, 'en', campaign)
            edit_duration(3)
            press('StartCountdown')
            disconnected, = pending()
            player_context.close()
            player_context = None
            context.close()
            context = None
            # The production worker, with no pages or WebSockets, emits a new
            # event that can see TimerProgress written after the Start node.
            time.sleep(3.6)
            context = create_context('gm')
            resumed = context.request.get(f'/api/maps/{scene}/state').json()
            assert next(row for row in resumed['walls'] if row['id'] == native_door['id'])['door_state'] == 'closed'
            assert next(row for row in resumed['lights'] if row['id'] == native_light['id'])['enabled'] is False
            page = context.new_page()
            observe(page)
            page.goto(f'{base}/game/{campaign}')
            wait_game()
            review = BuilderReview(page, campaign)
            assert not pending()
            records.append({'case': 'timer-fires-own-named-signal-with-fresh-variable-snapshot-and-no-open-pages-or-polling',
                            'jobId': disconnected['id'], 'pollingRequestsDuringWait': 0})

            create_player()
            open_door()
            press('StartCountdown')
            paused, = pending()
            command('automation', 'pause', {'paused': True})
            player.wait_for_timeout(3600)
            assert pending() == [paused] and wall_state() == 'open' and light_enabled() is True
            command('automation', 'pause', {'paused': False})
            player.wait_for_timeout(800)
            assert not pending() and wall_state() == 'closed' and light_enabled() is False
            records.append({'case': 'paused-scene-keeps-overdue-timer-and-resume-delivers-the-signal-once'})

            open_door()
            press('StartCountdown')
            locked_job, = pending()
            command('walls', 'door', {'wall_id': native_door['id'], 'door_state': 'locked'})
            player.wait_for_timeout(3600)
            assert not pending() and wall_state() == 'locked' and light_enabled() is True
            locked_run, = [run for run in automation()['runs'] if run.get('delayId') == locked_job['id']]
            assert locked_run['outcome'] in ('blocked', 'failed', 'cancelled') and locked_run.get('message'), locked_run
            records.append({'case': 'timer-expiry-keeps-original-player-authority-and-rolls-back-later-effects-on-a-now-locked-owner'})

            open_door()
            press('StartCountdown')
            stopped, = pending()
            press('StopCountdown')
            player.wait_for_timeout(3600)
            assert not pending() and wall_state() == 'open' and light_enabled() is True
            records.append({'case': 'stopped-short-timer-never-fires-after-its-original-deadline', 'jobId': stopped['id']})

            press('StartCountdown')
            recovered, = pending()
            player_context.close()
            player_context = None
            context.close()
            context = None
            restart(3.6)
            context = create_context('gm')
            time.sleep(1.2)
            resumed = context.request.get(f'/api/maps/{scene}/state').json()
            assert next(row for row in resumed['walls'] if row['id'] == native_door['id'])['door_state'] == 'closed'
            assert next(row for row in resumed['lights'] if row['id'] == native_light['id'])['enabled'] is False
            page = context.new_page()
            observe(page)
            page.goto(f'{base}/game/{campaign}')
            wait_game()
            review = BuilderReview(page, campaign)
            assert not pending()
            records.append({'case': 'real-server-restart-recovers-persisted-timer-and-fires-without-open-clients',
                            'jobId': recovered['id'], 'deadlinePassedWhileStopped': True})

            edit_duration(180)
            create_player()
            open_door()
            press('StartCountdown')
            changed, = pending()
            edit_duration(181)
            assert not pending() and wall_state() == 'open' and light_enabled() is True
            records.append({'case': 'linked-behavior-duration-change-cancels-an-obsolete-timer-without-firing', 'jobId': changed['id']})

            press('StartCountdown')
            cancelled, = pending()
            page.locator('.game-menubar__layer').nth(5).click()
            page.locator('[data-dock-tool=automation]').click()
            log = page.locator('.automation-log')
            log.locator('[data-automation-view=delays]').click()
            log.locator(f'[data-automation-delay-id="{cancelled["id"]}"] [data-automation-cancel-delay]').click()
            expect(log.locator(f'[data-automation-delay-id="{cancelled["id"]}"]')).to_have_count(0)
            assert not pending() and wall_state() == 'open' and light_enabled() is True
            log.locator('[data-automation-close]').click()
            records.append({'case': 'gm-native-cancel-removes-named-timer-without-executing-timeout-effects'})

        except Exception:
            if page and not page.is_closed():
                page.screenshot(path=str(output / 'failure.png'), full_page=True)
            (output / 'progress.json').write_text(json.dumps({'cases': records, 'pageErrors': errors,
                                                             'nativeDialogs': dialogs}, indent=2,
                                                            ensure_ascii=False), encoding='utf-8')
            raise
        finally:
            if player_context:
                player_context.close()
            if context:
                context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Generated solid-color PNGs and isolated campaign state; no operator data.'}


def main():
    if not any(argument == '--output' or argument.startswith('--output=') for argument in sys.argv[1:]):
        output = ROOT / 'data/map-builder-timer' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        sys.argv.extend(['--output', str(output)])
    delay_harness.check_browser = check_browser
    delay_harness.main()


if __name__ == '__main__':
    main()
