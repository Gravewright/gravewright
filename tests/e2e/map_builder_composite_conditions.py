"""Exercise composite Blueprint conditions through authoring and native play.

Three distinct synthetic torches must be turned before a passage opens. The
editor constructs the typed value graph, and the authoritative tabletop runs it
without counters or player-visible automation metadata. State and media remain
inside the common disposable fixture.
"""
from __future__ import annotations

from copy import deepcopy
import time

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

        def add_node(modal, kind, **params):
            before = set(modal.locator('[data-blueprint-node]').evaluate_all(
                'nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            modal.locator('[data-blueprint-add]').click()
            modal.locator(f'[data-blueprint-pick-type={kind}]').click()
            after = set(modal.locator('[data-blueprint-node]').evaluate_all(
                'nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            identifier, = after - before
            for name, value in params.items():
                control = modal.locator(f'[data-blueprint-node="{identifier}"] [data-blueprint-param="{name}"]')
                control.select_option(str(value))
            return identifier

        def card(modal, identifier):
            return modal.locator(f'[data-blueprint-node="{identifier}"]')

        def connect(modal, source, target):
            # Fitting clears a pending wire, so it runs before selecting either socket.
            modal.locator('[data-blueprint-fit]').click()
            source.click()
            target.click()

        def data_wire(modal, source, target, output_port, input_port):
            connect(modal, card(modal, source).locator(f'[data-blueprint-data-output={output_port}]'),
                    card(modal, target).locator(f'[data-blueprint-data-input={input_port}]'))

        def wait_game():
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')

        try:
            page.goto(builder)
            wait_ready(page)
            set_name(page, 'Three distinct torches open one synthetic passage')
            door_asset = upload_asset(page, 'door', 'Synthetic composite passage.png',
                                      harness.artwork('#427da4'))['id']
            torch_asset = upload_asset(page, 'decoration', 'Synthetic composite torch.png',
                                       harness.artwork('#bc762e'))['id']
            builder_tool(page, 'door')
            page.locator('[data-builder-brush-material]').select_option(door_asset)
            review.stroke((8, 6), (10, 6))
            for start, end in (((5, 10), (7, 12)), ((12, 10), (14, 12)), ((19, 10), (21, 12))):
                builder_tool(page, 'decoration')
                page.locator('[data-builder-brush-material]').select_option(torch_asset)
                review.stroke(start, end)
                builder_sidebar(page, 'selection')
                page.locator('[data-builder-property=behavior]').select_option('torch')
                close_panel(page)
            initial = review.save()
            door, = initial['document']['doors']
            torches = initial['document']['decorations']
            assert len(torches) == 3 and all(torch['torch']['state'] == 'off' for torch in torches)

            # Author the first complete graph using only the actual editor controls.
            # The door can reference all three torches explicitly, including the
            # one that will become the event owner in each subsequent native copy.
            modal = open_editor(door['id'])
            modal.locator('[data-blueprint-state-port=closed]').click()
            condition = add_node(modal, 'condition')
            aggregate = add_node(modal, 'all')
            expect(card(modal, aggregate).locator('[data-blueprint-input]')).to_have_count(0)
            expect(card(modal, aggregate).locator('[data-blueprint-output]')).to_have_count(0)
            assert card(modal, aggregate).locator('[data-blueprint-data-input]').evaluate_all(
                'ports=>ports.map(port=>port.dataset.blueprintDataInput)') == ['a', 'b', 'c', 'd']
            comparisons, references = [], []
            for index, torch in enumerate(torches):
                reference = add_node(modal, 'reference', targetId=torch['id'])
                prop = add_node(modal, 'property', property='state')
                compare = add_node(modal, 'compare', state='on')
                data_wire(modal, reference, prop, 'door', 'target')
                data_wire(modal, prop, compare, 'value', 'value')
                data_wire(modal, compare, aggregate, 'result', 'abcd'[index])
                comparisons.append(compare)
                references.append(reference)
            action = add_node(modal, 'state', targetState='open')
            data_wire(modal, aggregate, condition, 'result', 'test')
            connect(modal, modal.locator('[data-blueprint-state-port=closed]'),
                    card(modal, condition).locator('[data-blueprint-input]'))
            connect(modal, card(modal, condition).locator('[data-blueprint-output=true]'),
                    card(modal, action).locator('[data-blueprint-input]'))
            expect(card(modal, condition).locator('[data-blueprint-param=state]')).to_be_disabled()
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator(f'[data-blueprint-trace-value="{aggregate}"]')).to_contain_text('False')
            expect(modal.locator(f'[data-blueprint-trace-node="{action}"]')).to_have_count(0)
            assert review.project(initial['id'])['document'] == initial['document']
            page.screenshot(path=str(output / 'all-three-distinct-torch-references.png'))
            modal.locator('[data-blueprint-save]').click()
            authored = review.save()
            graph = authored['document']['doors'][0]['blueprint']['graphs']['enter:closed']
            assert len([node for node in graph['nodes'] if node['type'] == 'reference']) == 3
            assert {node['targetId'] for node in graph['nodes'] if node['type'] == 'reference'} == {
                torch['id'] for torch in torches}
            records.append({'case': 'actual-editor-builds-three-distinct-reference-property-compare-inputs-to-pure-all'})
            records.append({'case': 'all-false-simulation-follows-no-action-and-writes-no-project-or-scene'})

            # Reopen and replace the pure value node through the palette. One
            # comparison equals Off, making OR true while the other two are false.
            modal = open_editor(door['id'])
            card(modal, aggregate).locator('[data-blueprint-delete]').click()
            any_node = add_node(modal, 'any')
            for index, compare in enumerate(comparisons):
                data_wire(modal, compare, any_node, 'result', 'abcd'[index])
            data_wire(modal, any_node, condition, 'result', 'test')
            card(modal, comparisons[0]).locator('[data-blueprint-param=state]').select_option('off')
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator(f'[data-blueprint-trace-value="{any_node}"]')).to_contain_text('True')
            expect(modal.locator(f'[data-blueprint-trace-node="{action}"]')).to_contain_text('Opened')
            page.screenshot(path=str(output / 'any-one-true-two-false-simulation.png'))
            modal.locator('[data-blueprint-cancel]').click()
            assert review.save()['document'] == authored['document']
            records.append({'case': 'actual-editor-any-combines-mixed-boolean-values-and-cancel-preserves-all-graph'})

            # Reuse the proven graph on each mechanism. Each owner's own Property
            # reads Self; the other two keep explicit references. Only the event
            # and action target change, preserving the same three distinct tests.
            document = deepcopy(authored['document'])
            del document['doors'][0]['blueprint']
            for torch in document['decorations']:
                runtime_graph = deepcopy(graph)
                own_ref, = [node for node in runtime_graph['nodes']
                            if node['type'] == 'reference' and node['targetId'] == torch['id']]
                runtime_graph['nodes'].remove(own_ref)
                runtime_graph['edges'] = [edge for edge in runtime_graph['edges'] if edge['from'] != own_ref['id']]
                for node in runtime_graph['nodes']:
                    if node['type'] == 'event':
                        node['event'] = 'enter:on'
                target = f'door_for_{torch["id"].replace("-", "")}'
                runtime_graph['nodes'].append({'id': target, 'type': 'reference', 'targetId': door['id'], 'x': 100, 'y': 700})
                runtime_graph['edges'].append({'kind': 'data', 'from': target, 'output': 'door', 'to': action, 'input': 'target'})
                torch['blueprint'] = {'version': 2, 'kind': 'torch',
                                      'states': {state: {'appearance': 'inherit'} for state in ('off', 'on')},
                                      'graphs': {'enter:on': runtime_graph}}
            playable = review.store(authored['id'], authored['version'], authored['folderId'], document)
            page.evaluate('sessionStorage.clear()')
            page.goto(builder + '?project=' + playable['id'])
            wait_ready(page)
            assert review.save()['document'] == playable['document']
            records.append({'case': 'saved-composite-graphs-reopen-with-three-distinct-current-state-checks'})

            labels = {'en': 'All conditions', 'pt-BR': 'Todas as condições', 'es': 'Todas las condiciones'}
            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    page.goto(builder + '?project=' + playable['id'])
                    wait_ready(page)
                    modal = open_editor(torches[0]['id'], 'decorations')
                    modal.locator('[data-blueprint-state-port=on]').click()
                    expect(card(modal, aggregate)).to_contain_text(labels[locale])
                    modal.locator('[data-blueprint-simulate]').click()
                    expect(modal.locator(f'[data-blueprint-trace-value="{aggregate}"]')).to_be_visible()
                    card(modal, aggregate).scroll_into_view_if_needed()
                    overlaps = card(modal, aggregate).evaluate("""element=>{
                      const target=element.getBoundingClientRect();
                      return [...element.parentElement.querySelectorAll('[data-blueprint-node]')]
                        .filter(other=>other!==element).flatMap(other=>{
                          const box=other.getBoundingClientRect();
                          const width=Math.min(target.right,box.right)-Math.max(target.left,box.left);
                          const height=Math.min(target.bottom,box.bottom)-Math.max(target.top,box.top);
                          return width>1&&height>1?[{type:other.dataset.blueprintType,width,height}]:[];
                        });
                    }""")
                    assert not overlaps, {'locale': locale, 'width': width, 'overlaps': overlaps}
                    metrics = modal.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'composite-{locale}-{width}.png'))
                    for _ in range(12):
                        page.keyboard.press('Tab')
                        assert modal.evaluate('element=>element.closest("[role=dialog]").contains(document.activeElement)')
                    page.keyboard.press('Escape')
                    expect(modal).to_have_count(0)
                    records.append({'case': 'localized-responsive-composite-editor-and-focus-lifecycle',
                                    'locale': locale, 'width': width, 'metrics': metrics})

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(builder + '?project=' + playable['id'])
            wait_ready(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            wait_game()
            project = review.project(playable['id'])
            scene = project['sceneId']

            def command(area, operation, data):
                return page.evaluate("""a=>gravewrightRealtime.mapCommand('objects',{
                  mapId:a.scene,area:a.area,action:a.operation,data:a.data})""",
                                     {'scene': scene, 'area': area, 'operation': operation, 'data': data})

            command('lighting', 'update', {'mode': 'none', 'darkness': 0, 'lights_out': False})
            page.evaluate("""a=>gravewrightRealtime.mapCommand('update',{
              mapId:a.scene,version:a.version,settings:{visibility:'players'}})""",
                          {'scene': scene, 'version': project['sceneVersion']})
            page.evaluate("scene=>gravewrightRealtime.mapCommand('activate',{mapId:scene})", scene)

            def state(target=page):
                response = target.request.get(f'/api/maps/{scene}/state')
                assert response.ok, response.text()
                return response.json()

            native = state()
            native_door, = [wall for wall in native['walls'] if wall['kind'] == 'door']
            native_torches = sorted([image for image in native['images'] if image.get('torch')], key=lambda image: image['x'])
            assert len(native_torches) == 3
            native_ids = {image['id'] for image in native_torches}
            for image in native_torches:
                assert image['blueprint']['kind'] == 'torch'
                targets = {node['targetId'] for node in image['blueprint']['graphs']['enter:on']['nodes']
                           if node['type'] == 'reference'}
                assert targets == (native_ids - {image['id']}) | {native_door['id']}, targets
            player_context = browser.new_context(base_url=base, viewport={'width': 1200, 'height': 800})
            player_context.add_cookies([{**seed['sessions']['player'], 'url': base}])
            player = player_context.new_page()
            observe(player)
            player.goto(f'{base}/game/{campaign}')
            player.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(player.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            for image in state(player)['images']:
                assert 'blueprint' not in image
                if image.get('torch'):
                    assert image['torch'] == {'state': 'off', 'lit': True}, image
            assert player.request.get(f'/api/maps/{scene}/automation').status == 404
            records.append({'case': 'generation-remaps-every-element-reference-and-filters-private-graphs-from-real-player'})

            def toggle(index, expected, door_state):
                image = native_torches[index]
                control = player.locator(f'[data-smart-image-id="{image["id"]}"][data-smart-image-action=interact]')
                expect(control).to_have_attribute('aria-disabled', 'false')
                control.focus()
                control.press('Enter')
                deadline = time.monotonic() + 12
                while time.monotonic() < deadline:
                    current = state(player)
                    row = next(row for row in current['images'] if row['id'] == image['id'])
                    door_now = next(row for row in current['walls'] if row['id'] == native_door['id'])
                    if row['torch']['state'] == expected and door_now['door_state'] == door_state:
                        expect(control).to_have_attribute('aria-pressed', str(expected == 'on').lower())
                        expect(control).to_have_attribute('aria-disabled', 'false')
                        return current
                    player.wait_for_timeout(80)
                raise AssertionError({'expected': [expected, door_state], 'state': current})

            toggle(0, 'on', 'closed')
            toggle(0, 'off', 'closed')
            toggle(0, 'on', 'closed')
            toggle(1, 'on', 'closed')
            complete = toggle(2, 'on', 'open')
            assert all(image['torch']['state'] == 'on' for image in complete['images'] if image.get('torch'))
            player.screenshot(path=str(output / 'all-real-player-three-distinct-mechanisms.png'))
            records.append({'case': 'repeating-one-torch-never-substitutes-for-other-two-and-only-third-distinct-turn-opens-door'})

            # Set up one false input after all were true. A fresh true transition
            # of a different torch must consult that false state, not an old count.
            toggle(0, 'off', 'open')
            command('walls', 'door', {'wall_id': native_door['id'], 'door_state': 'closed'})
            toggle(1, 'off', 'closed')
            toggle(1, 'on', 'closed')
            records.append({'case': 'all-rechecks-current-distinct-states-after-a-previously-true-input-becomes-false'})

            # Change the same authored graph to Any through the actual editor,
            # update the linked scene, and run that new condition as the player.
            toggle(1, 'off', 'closed')
            toggle(2, 'off', 'closed')
            page.goto(builder + '?project=' + playable['id'])
            wait_ready(page)
            modal = open_editor(torches[0]['id'], 'decorations')
            modal.locator('[data-blueprint-state-port=on]').click()
            card(modal, aggregate).locator('[data-blueprint-delete]').click()
            any_live = add_node(modal, 'any')
            for index, compare in enumerate(comparisons):
                data_wire(modal, compare, any_live, 'result', 'abcd'[index])
            data_wire(modal, any_live, condition, 'result', 'test')
            modal.locator('[data-blueprint-save]').click()
            revised = review.save()
            assert any(node['type'] == 'any' for node in revised['document']['decorations'][0]['blueprint']['graphs']['enter:on']['nodes'])
            builder_sidebar(page, 'review')
            with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                page.locator('[data-builder-review-update]').click()
            assert updated.value.ok, updated.value.text()
            wait_game()
            assert review.project(playable['id'])['sceneId'] == scene
            current = state()
            assert all(image['torch']['state'] == 'off' for image in current['images'] if image.get('torch'))
            updated_first = next(image for image in current['images'] if image['id'] == native_torches[0]['id'])
            assert any(node['type'] == 'any' for node in updated_first['blueprint']['graphs']['enter:on']['nodes'])
            final = toggle(0, 'on', 'open')
            assert sum(image['torch']['state'] == 'on' for image in final['images'] if image.get('torch')) == 1
            player.screenshot(path=str(output / 'any-real-player-one-distinct-mechanism.png'))
            records.append({'case': 'actual-any-edit-updates-same-linked-scene-and-one-true-input-opens-door-in-real-player-game'})
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
            'assets': 'Generated solid-color PNGs and silent WAV; no operator data.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
