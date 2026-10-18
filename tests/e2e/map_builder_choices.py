"""Author and play typed Switch branches and weighted Random choices.

Synthetic artwork, isolated campaign/database and the real restartable server
exercise editor drafts, receipts and durable Delay/Timer interoperability.
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

        def change(control, value):
            if control.get_attribute('type') == 'checkbox':
                control.set_checked(value)
            elif control.evaluate('element=>element.tagName') == 'SELECT':
                control.select_option(str(value).lower() if isinstance(value, bool) else str(value))
            else:
                control.fill(str(value))
                control.dispatch_event('change')

        def parameter(modal, identifier, name, value):
            change(card(modal, identifier).locator(f'[data-blueprint-param="{name}"]').first, value)

        def weight(modal, identifier, branch, value):
            change(card(modal, identifier).locator(f'[data-blueprint-branch="{branch}"] [data-blueprint-param=weight]'), value)

        def add_node(modal, kind, **params):
            before = set(modal.locator('[data-blueprint-node]').evaluate_all('nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            modal.locator('[data-blueprint-add]').click()
            modal.locator(f'[data-blueprint-pick-type="{kind}"]').click()
            after = set(modal.locator('[data-blueprint-node]').evaluate_all('nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
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

        def choice_layout(modal):
            result = modal.evaluate('''element=>{
              const cards=[...element.querySelectorAll('.smart-object__node')].map(node=>({
                id:node.dataset.blueprintNode||'instance',type:node.dataset.blueprintType,
                rect:node.getBoundingClientRect()}));
              const choices=cards.filter(node=>['switch','random'].includes(node.type)),overlap=[];
              for(const choice of choices)for(const other of cards){
                if(choice===other)continue;
                const width=Math.min(choice.rect.right,other.rect.right)-Math.max(choice.rect.left,other.rect.left);
                const height=Math.min(choice.rect.bottom,other.rect.bottom)-Math.max(choice.rect.top,other.rect.top);
                if(width>.25&&height>.25)overlap.push({choice:choice.id,other:other.id,width,height});
              }
              return {choiceCount:choices.length,overlap};
            }''')
            assert result['choiceCount'] and not result['overlap'], result
            return result

        try:
            page.goto(builder)
            wait_ready(page)
            set_name(page, 'Synthetic typed choices and durable weighted branches')
            door_asset = upload_asset(page, 'door', 'Synthetic choice door.png', harness.artwork('#426f95'))['id']
            lever_asset = upload_asset(page, 'decoration', 'Synthetic choice control.png', harness.artwork('#b47d32'))['id']
            builder_tool(page, 'door')
            page.locator('[data-builder-brush-material]').select_option(door_asset)
            review.stroke((8, 6), (10, 6))
            review.stroke((20, 6), (22, 6))
            builder_tool(page, 'light')
            review.stroke((12, 9), (12, 9))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=enabled]').uncheck()
            close_panel(page)
            signals = ('ChooseOne', 'ChooseTwo', 'ChooseDefault', 'DelayedChoose', 'TimerChoice', 'WeightedChoice')
            for x in (4, 10, 16, 22, 28, 34):
                builder_tool(page, 'decoration')
                page.locator('[data-builder-brush-material]').select_option(lever_asset)
                review.stroke((x, 12), (x + 2, 14))
                builder_sidebar(page, 'selection')
                page.locator('[data-builder-property=behavior]').select_option('lever')
                close_panel(page)
            initial = review.save()
            owner, other = initial['document']['doors']
            light, = initial['document']['lights']
            senders = initial['document']['decorations']

            modal = open_editor(owner['id'])
            add_signal(modal, 'Choose')
            route = add_node(modal, 'getVariable', scope='scene', valueType='number', name='Route', default=0)
            switch = add_node(modal, 'switch')
            expect(card(modal, switch).locator('[data-blueprint-param=valueType]')).to_have_value('number')
            reference = add_node(modal, 'reference', targetId=other['id'])
            opened_self = add_node(modal, 'state', targetState='open')
            opened_other = add_node(modal, 'state')
            data_wire(modal, reference, opened_other, 'door', 'target')
            parameter(modal, opened_other, 'targetState', 'open')
            random = add_node(modal, 'random')
            weight(modal, random, 'branch1', 0)
            lit = add_node(modal, 'light', targetId=light['id'], enabled=True)
            dark = add_node(modal, 'light', targetId=light['id'], enabled=False)
            data_wire(modal, route, switch, 'value', 'value')
            event_wire(modal, switch)
            execution_wire(modal, switch, opened_self, 'case1')
            execution_wire(modal, switch, opened_other, 'case2')
            execution_wire(modal, switch, dark, 'default')
            execution_wire(modal, opened_self, random)
            execution_wire(modal, opened_other, random)
            execution_wire(modal, random, dark, 'branch1')
            execution_wire(modal, random, lit, 'branch2')
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator('[data-blueprint-trace-choice=default]')).to_be_visible()
            expect(modal.locator(f'[data-blueprint-trace-node="{random}"]')).to_have_count(0)
            modal.locator('[data-blueprint-simulation-variables] > summary').click()
            change(modal.locator('[data-blueprint-simulation-variable=Route]'), 2)
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator('[data-blueprint-trace-choice=case2]')).to_be_visible()
            expect(modal.locator('[data-blueprint-trace-choice=branch2]')).to_be_visible()
            expect(modal.locator(f'[data-blueprint-trace-node="{lit}"]')).to_be_visible()
            assert review.project(initial['id'])['document'] == initial['document']
            records.append({'case': 'real-editor-wires-number-variable-to-switch-and-zero-weight-random-preview-is-local',
                            'layout': choice_layout(modal)})

            add_signal(modal, 'DelayedChoose')
            before_delay = add_node(modal, 'delay', seconds=3)
            delayed_random = add_node(modal, 'random')
            weight(modal, delayed_random, 'branch1', 0)
            after_delay = add_node(modal, 'delay', seconds=8)
            delayed_dark = add_node(modal, 'light', targetId=light['id'], enabled=False)
            event_wire(modal, before_delay)
            execution_wire(modal, before_delay, delayed_random)
            execution_wire(modal, delayed_random, after_delay, 'branch2')
            execution_wire(modal, after_delay, delayed_dark)
            add_signal(modal, 'TimerChoice')
            timer = add_node(modal, 'timer', name='RandomTick', seconds=3)
            timer_lit = add_node(modal, 'light', targetId=light['id'], enabled=True)
            event_wire(modal, timer)
            execution_wire(modal, timer, timer_lit)
            add_signal(modal, 'RandomTick')
            timer_random = add_node(modal, 'random')
            weight(modal, timer_random, 'branch1', 0)
            timer_dark = add_node(modal, 'light', targetId=light['id'], enabled=False)
            event_wire(modal, timer_random)
            execution_wire(modal, timer_random, timer_dark, 'branch2')
            add_signal(modal, 'WeightedChoice')
            weighted_random = add_node(modal, 'random')
            weight(modal, weighted_random, 'branch2', 3)
            first_value = add_node(modal, 'setVariable', scope='scene', valueType='text', name='Roll', value='First')
            second_value = add_node(modal, 'setVariable', scope='scene', valueType='text', name='Roll', value='Second')
            event_wire(modal, weighted_random)
            execution_wire(modal, weighted_random, first_value, 'branch1')
            execution_wire(modal, weighted_random, second_value, 'branch2')
            modal.locator('[data-blueprint-save]').click()
            review.save()

            for sender, signal in zip(senders, signals):
                modal = open_editor(sender['id'], 'decorations')
                legacy = modal.locator('[data-blueprint-state-events]')
                if legacy.get_attribute('open') is None:
                    legacy.locator('summary').click()
                modal.locator('[data-blueprint-event="enter:on"]').click()
                reference = add_node(modal, 'reference', targetId=owner['id'])
                emit = add_node(modal, 'emitEvent', scope='element', name='Choose' if signal.startswith('Choose') else signal)
                data_wire(modal, reference, emit, 'door', 'target')
                if signal.startswith('Choose'):
                    value = add_node(modal, 'setVariable', scope='scene', valueType='number', name='Route',
                                     value={'ChooseOne': 1, 'ChooseTwo': 2, 'ChooseDefault': 3}[signal])
                    connect(modal, modal.locator('[data-blueprint-state-port=on]'), card(modal, value).locator('[data-blueprint-input]'))
                    execution_wire(modal, value, emit)
                else:
                    connect(modal, modal.locator('[data-blueprint-state-port=on]'), card(modal, emit).locator('[data-blueprint-input]'))
                modal.locator('[data-blueprint-save]').click()
                review.save()
            authored = review.save()
            records.append({'case': 'real-editor-authors-signal-driven-switch-weighted-random-delay-and-timer-graphs'})

            modal = open_editor(owner['id'])
            modal.locator('[data-blueprint-event="signal:Choose"]').click()
            first_case = card(modal, switch).locator('[data-blueprint-case=case1] [data-blueprint-param=caseValue]')
            second_case = card(modal, switch).locator('[data-blueprint-case=case2] [data-blueprint-param=caseValue]')
            change(first_case, 2)
            assert not first_case.evaluate('element=>element.checkValidity()')
            change(second_case, 3)
            assert first_case.evaluate('element=>element.checkValidity()')
            assert second_case.evaluate('element=>element.checkValidity()')
            modal.locator('[data-blueprint-simulation-variables] > summary').click()
            for route_value, expected_choice in ((2, 'case1'), (3, 'case2')):
                change(modal.locator('[data-blueprint-simulation-variable=Route]'), route_value)
                modal.locator('[data-blueprint-simulate]').click()
                expect(modal.locator(f'[data-blueprint-trace-choice="{expected_choice}"]')).to_be_visible()
            modal.locator('[data-blueprint-undo]').click()
            expect(first_case).to_have_value('1')
            expect(second_case).to_have_value('2')
            modal.locator('[data-blueprint-redo]').click()
            expect(first_case).to_have_value('2')
            expect(second_case).to_have_value('3')
            modal.locator('[data-blueprint-save]').click()
            corrected = review.save()
            saved_switch = next(node for node in corrected['document']['doors'][0]['blueprint']['graphs']['signal:Choose']['nodes']
                                if node['id'] == switch)
            assert saved_switch['cases'] == [{'id': 'case1', 'value': 2}, {'id': 'case2', 'value': 3}], saved_switch
            records.append({'case': 'switch-cross-field-validation-clears-duplicate-errors-commits-visible-values-and-undoes-as-one-action'})
            page.locator('[data-builder-undo]').click()
            assert review.save()['document'] == authored['document']
            modal = open_editor(owner['id'])
            modal.locator('[data-blueprint-event="signal:Choose"]').click()
            change(card(modal, switch).locator('[data-blueprint-case=case1] [data-blueprint-param=caseValue]'), 2)
            change(card(modal, switch).locator('[data-blueprint-case=case2] [data-blueprint-param=caseValue]'), 3)
            modal.locator('[data-blueprint-cancel]').click()
            assert review.save()['document'] == authored['document']
            records.append({'case': 'builder-undo-restores-before-corrected-switch-save-and-cancel-discards-valid-group-edits'})

            modal = open_editor(owner['id'])
            modal.locator('[data-blueprint-event="signal:Choose"]').click()
            number_wire = modal.locator('[data-blueprint-edge].is-data').count()
            parameter(modal, switch, 'valueType', 'text')
            expect(card(modal, switch).locator('[data-blueprint-data-input=value]')).to_have_attribute('data-port-type', 'text')
            expect(modal.locator('[data-blueprint-edge].is-data')).to_have_count(number_wire - 1)
            modal.locator('[data-blueprint-undo]').click()
            expect(card(modal, switch).locator('[data-blueprint-data-input=value]')).to_have_attribute('data-port-type', 'number')
            expect(modal.locator('[data-blueprint-edge].is-data')).to_have_count(number_wire)
            for _ in range(2):
                card(modal, switch).locator('[data-blueprint-add-case]').click()
                choice_layout(modal)
            expect(card(modal, switch).locator('[data-blueprint-add-case]')).to_be_disabled()
            execution_wire(modal, switch, dark, 'case3')
            edge3 = f'{switch}:case3:{dark}'
            expect(modal.locator(f'[data-blueprint-edge="{edge3}"]')).to_have_count(1)
            card(modal, switch).locator('[data-blueprint-remove-case=case1]').click()
            expect(card(modal, switch).locator('[data-blueprint-output=case1]')).to_have_count(0)
            expect(card(modal, switch).locator('[data-blueprint-output=case2]')).to_have_count(1)
            expect(modal.locator(f'[data-blueprint-edge="{edge3}"]')).to_have_count(1)
            modal.locator('[data-blueprint-undo]').click()
            parameter(modal, switch, 'valueType', 'boolean')
            expect(card(modal, switch).locator('[data-blueprint-output=case3]')).to_have_count(0)
            expect(modal.locator(f'[data-blueprint-edge="{edge3}"]')).to_have_count(0)
            expect(card(modal, switch).locator('[data-blueprint-add-case]')).to_be_disabled()
            modal.locator('[data-blueprint-undo]').click()
            expect(modal.locator(f'[data-blueprint-edge="{edge3}"]')).to_have_count(1)
            parameter(modal, switch, 'valueType', 'text')
            long_case = 'Câmara secreta 雪 ✨ ' + 'passagem_' * 16
            change(card(modal, switch).locator('[data-blueprint-case=case3] [data-blueprint-param=caseValue]'), long_case)
            modal.locator('[data-blueprint-fit]').click()
            metrics = modal.evaluate(MEASURE)
            assert not metrics['tiny'] and not metrics['overflow'], metrics
            layout = choice_layout(modal)
            page.screenshot(path=str(output / 'choices-switch-long-text.png'))
            modal.locator('[data-blueprint-cancel]').click()
            assert review.save()['document'] == authored['document']
            records.append({'case': 'switch-type-changes-prune-incompatible-wires-stable-case-ids-and-undo-restore-removed-branches',
                            'textLength': len(long_case), 'metrics': metrics, 'layout': layout})

            modal = open_editor(owner['id'])
            modal.locator('[data-blueprint-event="signal:Choose"]').click()
            card(modal, random).locator('[data-blueprint-add-branch]').click()
            execution_wire(modal, random, dark, 'branch3')
            random_edge = f'{random}:branch3:{dark}'
            expect(modal.locator(f'[data-blueprint-edge="{random_edge}"]')).to_have_count(1)
            weight(modal, random, 'branch2', 0)
            expect(card(modal, random).locator('[data-blueprint-remove-branch=branch3]')).to_be_disabled()
            weight(modal, random, 'branch2', 1)
            card(modal, random).locator('[data-blueprint-remove-branch=branch3]').click()
            expect(modal.locator(f'[data-blueprint-edge="{random_edge}"]')).to_have_count(0)
            modal.locator('[data-blueprint-undo]').click()
            expect(modal.locator(f'[data-blueprint-edge="{random_edge}"]')).to_have_count(1)
            choice_layout(modal)
            modal.locator('[data-blueprint-cancel]').click()
            assert review.save()['document'] == authored['document']
            records.append({'case': 'random-weight-controls-prevent-zero-total-and-remove-only-last-branch-with-undoable-wire-cleanup'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    page.goto(builder + '?project=' + authored['id'])
                    wait_ready(page)
                    modal = open_editor(owner['id'])
                    modal.locator('[data-blueprint-event="signal:Choose"]').click()
                    expect(card(modal, switch).locator('[data-blueprint-output=default]')).to_have_count(1)
                    expect(card(modal, random).locator('[data-blueprint-branch=branch1] [data-blueprint-param=weight]')).to_have_value('0')
                    for kind in ('switch', 'random'):
                        modal.locator('[data-blueprint-add]').click()
                        modal.locator('[data-blueprint-picker-search]').fill(kind)
                        expect(modal.locator(f'[data-blueprint-pick-type="{kind}"]')).to_be_visible()
                        modal.locator('[data-blueprint-picker-cancel]').click()
                    modal.locator('[data-blueprint-fit]').click()
                    metrics = modal.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    layout = choice_layout(modal)
                    page.screenshot(path=str(output / f'choices-editor-{locale}-{width}.png'))
                    for _ in range(8):
                        page.keyboard.press('Tab')
                        assert modal.evaluate('element=>element.closest("[role=dialog]").contains(document.activeElement)')
                    page.keyboard.press('Escape')
                    expect(modal).to_have_count(0)
                    records.append({'case': 'localized-responsive-switch-and-random-controls-support-keyboard-focus-and-search',
                                    'locale': locale, 'width': width, 'metrics': metrics, 'layout': layout})

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
            native_owner = next(row for row in native['walls'] if row.get('blueprint', {}).get('graphs', {}).get('signal:Choose'))
            native_other = next(row for row in native['walls'] if row['kind'] == 'door' and row['id'] != native_owner['id'])
            native_light, = native['lights']
            native_senders = {}
            for row in native['images']:
                if not row.get('lever'):
                    continue
                graph = row['blueprint']['graphs']['enter:on']
                emit, = [node for node in graph['nodes'] if node['type'] == 'emitEvent']
                route_node = next((node for node in graph['nodes'] if node['type'] == 'setVariable'), None)
                signal = {1: 'ChooseOne', 2: 'ChooseTwo', 3: 'ChooseDefault'}[route_node['value']] if route_node else emit['name']
                native_senders[signal] = row['id']

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

            def receipt(identifier, image):
                return player.evaluate("""a=>new Promise((resolve,reject)=>{
                  const stop=()=>{clearTimeout(timer);removeEventListener('gravewright:api-event',receive);};
                  const receive=({detail})=>{
                    if(detail.payload.requestId!==a.id||!['maps.ack','maps.error'].includes(detail.type))return;
                    stop();detail.type==='maps.ack'?resolve(detail.payload.result):reject(Error(detail.payload.message));};
                  const timer=setTimeout(()=>{stop();reject(Error('Choice receipt timed out'));},15000);
                  addEventListener('gravewright:api-event',receive);
                  gravewrightRealtime.tableTool('maps.command',{action:'objects',requestId:a.id,
                    data:{mapId:a.scene,area:'images',action:'interact',data:{image_id:a.image}}});
                })""", {'scene': scene, 'id': identifier, 'image': image})

            def light_enabled():
                return next(row for row in state()['lights'] if row['id'] == native_light['id'])['enabled']

            def decision(node, event):
                for run in automation()['runs']:
                    for entry in run['events']:
                        if entry['event'] == event:
                            for step in entry['steps']:
                                if step['id'] == node:
                                    return step['output']
                raise AssertionError(f'No logged decision for {event}/{node}')

            create_player()
            for signal, selected in (('ChooseOne', 'case1'), ('ChooseTwo', 'case2'), ('ChooseDefault', 'default')):
                command('walls', 'door', {'wall_id': native_owner['id'], 'door_state': 'closed'})
                command('walls', 'door', {'wall_id': native_other['id'], 'door_state': 'closed'})
                press(signal)
                current = state()
                assert decision(switch, 'signal:Choose') == selected
                owner_state = next(row for row in current['walls'] if row['id'] == native_owner['id'])['door_state']
                other_state = next(row for row in current['walls'] if row['id'] == native_other['id'])['door_state']
                assert owner_state == ('open' if selected == 'case1' else 'closed')
                assert other_state == ('open' if selected == 'case2' else 'closed')
                assert light_enabled() is (selected != 'default')
                if selected != 'default':
                    assert decision(random, 'signal:Choose') == 'branch2'
                records.append({'case': 'real-player-switch-routes-typed-scene-variable-to-only-matching-output', 'selected': selected})

            weighted_id = str(uuid4())
            original = receipt(weighted_id, native_senders['WeightedChoice'])
            selected = decision(weighted_random, 'signal:WeightedChoice')
            assert selected in ('branch1', 'branch2')
            expected = 'First' if selected == 'branch1' else 'Second'
            assert automation()['variables']['scene']['Roll'] == {'type': 'text', 'value': expected}
            before_retry = automation()['runs']
            assert receipt(weighted_id, native_senders['WeightedChoice']) == original
            assert automation()['runs'] == before_retry
            records.append({'case': 'real-weighted-random-is-logged-and-operation-retry-keeps-original-decision-and-effects', 'selected': selected})
            assert 'decision' not in json.dumps(state(player))
            assert 'automationVariables' not in json.dumps(state(player))
            assert player.request.get(f'/api/maps/{scene}/automation').status == 404
            records.append({'case': 'player-cannot-read-private-random-decisions-variables-or-authoring-graphs'})

            page.locator('.game-menubar__layer').nth(5).click()
            page.locator('[data-dock-tool=automation]').click()
            log = page.locator('.automation-log')
            expect(log.locator('[data-automation-runs]')).to_contain_text('WeightedChoice')
            page.screenshot(path=str(output / 'choices-native-decisions.png'))
            log.locator('[data-automation-close]').click()

            command('lights', 'update', {'light_id': native_light['id'], 'enabled': True})
            delayed_id = str(uuid4())
            delayed_receipt = receipt(delayed_id, native_senders['DelayedChoose'])
            first_wait, = automation()['delays']
            assert first_wait['nodeId'] == before_delay and light_enabled() is True
            player_context.close()
            player_context = None
            context.close()
            context = None
            restart(3.6)
            context = create_context('gm')
            time.sleep(.7)
            page = context.new_page()
            observe(page)
            page.goto(f'{base}/game/{campaign}')
            wait_game()
            # The first overdue wait chooses exactly once, then schedules the
            # second wait. Pausing prevents setup/network time racing its expiry.
            command('automation', 'pause', {'paused': True})
            second_waits = automation()['delays']
            if second_waits:
                second_wait, = second_waits
                assert second_wait['nodeId'] == after_delay and second_wait['id'] != first_wait['id']
                assert decision(delayed_random, 'signal:DelayedChoose') == 'branch2'
                create_player()
                assert receipt(delayed_id, native_senders['DelayedChoose']) == delayed_receipt
                assert automation()['delays'] == [second_wait]
                records.append({'case': 'restart-before-random-recovers-delay-and-records-one-choice-before-a-second-persistent-wait'})
                player_context.close()
                player_context = None
                command('automation', 'pause', {'paused': False})
                context.close()
                context = None
                restart(8.6)
                context = create_context('gm')
                time.sleep(.7)
                page = context.new_page()
                observe(page)
                page.goto(f'{base}/game/{campaign}')
                wait_game()
                assert not automation()['delays'] and light_enabled() is False
                assert decision(delayed_random, 'signal:DelayedChoose') == 'branch2'
                records.append({'case': 'restart-after-random-recovers-second-delay-without-rerolling-or-repeating-effects'})
            else:
                raise AssertionError('The second Delay expired before the restart checkpoint could be inspected.')

            create_player()
            press('TimerChoice')
            timer_wait, = automation()['delays']
            assert timer_wait['kind'] == 'timer' and timer_wait['name'] == 'RandomTick' and light_enabled() is True
            player_context.close()
            player_context = None
            context.close()
            context = None
            time.sleep(3.6)
            context = create_context('gm')
            page = context.new_page()
            observe(page)
            page.goto(f'{base}/game/{campaign}')
            wait_game()
            assert not automation()['delays'] and light_enabled() is False
            assert decision(timer_random, 'signal:RandomTick') == 'branch2'
            records.append({'case': 'timer-expiry-runs-zero-weight-random-on-own-signal-with-no-open-browser-or-polling'})

        except Exception:
            if page and not page.is_closed():
                page.screenshot(path=str(output / 'failure.png'), full_page=True)
            (output / 'progress.json').write_text(json.dumps({'cases': records, 'pageErrors': errors,
                                                             'nativeDialogs': dialogs}, indent=2, ensure_ascii=False), encoding='utf-8')
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
            'assets': 'Generated solid-color synthetic PNGs; no operator data.'}


def main():
    if not any(argument == '--output' or argument.startswith('--output=') for argument in sys.argv[1:]):
        output = ROOT / 'data/map-builder-choices' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        sys.argv.extend(['--output', str(output)])
    delay_harness.check_browser = check_browser
    delay_harness.main()


if __name__ == '__main__':
    main()
