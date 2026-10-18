"""Check the finite editor connection matrix using real public controls.

Synthetic resources are seeded through the public project API. Actual socket
selection, producer creation, type changes, undo, autosave and scene replacement
run in Edge/Chromium against the shared disposable fixture.
"""
from __future__ import annotations

from copy import deepcopy
import json
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import builder_sidebar, builder_tool, builder_workspace
from map_builder_asset_removal import BuilderReview
from map_builder_playtest import chain, node
from map_builder_reference import close_panel, upload_asset, wait_ready


ELEMENT_ACTIONS = {
    'state': {'targetState': 'on'}, 'interact': {}, 'flame': {'enabled': True},
    'reveal': {}, 'barrier': {'channel': 'movement', 'mode': 'pass'},
    'emitEvent': {'scope': 'element', 'name': 'MatrixSignal'},
    'move': {'dx': 1, 'dy': 0}, 'rotate': {'degrees': 90},
    'setInteraction': {'enabled': True}, 'setRegion': {'enabled': True},
    'setVisibility': {'visible': True}, 'setAppearance': {},
}


def behavior(kind, graphs):
    states = {'door': ('closed', 'open', 'locked'), 'lever': ('off', 'on'),
              'torch': ('off', 'on'), 'region': ('empty', 'occupied')}[kind]
    return {'version': 2, 'kind': kind,
            'states': {state: {'appearance': 'inherit'} for state in states}, 'graphs': graphs}


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    records, failures, errors, dialogs = [], [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1920, 'height': 1080})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        review = BuilderReview(page, seed['campaign'])

        def diagnostics():
            (output / 'measurements.json').write_text(json.dumps({
                'cases': records, 'failures': failures,
                'pageErrors': errors, 'nativeDialogs': dialogs}, indent=2), encoding='utf-8')

        def saved():
            expect(page.locator('[data-map-builder]')).to_have_attribute(
                'data-save-state', 'saved', timeout=20_000)
            return review.project(page.evaluate("new URL(location.href).searchParams.get('project')"))

        def editor(identifier, collection='decorations'):
            builder_tool(page, 'select')
            builder_workspace(page)
            element = page.locator(f'[data-builder-{collection}] [data-object-id="{identifier}"]')
            point = element.evaluate('''group=>{
              const b=group.getBBox(),p=new DOMPoint(b.x+b.width*.2,b.y+b.height*.5)
                .matrixTransform(group.getScreenCTM());return [p.x,p.y];}''')
            if collection == 'doors':
                page.mouse.dblclick(*point)
            else:
                page.mouse.click(*point)
                builder_sidebar(page, 'selection')
                page.locator('[data-builder-edit-behavior]').click()
            modal = page.locator('[data-smart-object-modal]')
            expect(modal).to_be_visible()
            return modal

        def card(modal, identifier):
            return modal.locator(f'[data-blueprint-node="{identifier}"]')

        def select_graph(modal, event):
            modal.locator(f'[data-blueprint-event="{event}"]').click()
            modal.locator('[data-blueprint-fit]').click()

        def edges(modal):
            return modal.locator('[data-blueprint-edge].is-data')

        def ids(modal):
            return set(modal.locator('[data-blueprint-node]').evaluate_all(
                'nodes=>nodes.map(node=>node.dataset.blueprintNode)'))

        def connect(modal, source, target, reverse=False):
            modal.locator('[data-blueprint-fit]').click()
            if reverse:
                target.press('Shift+Enter')
                source.press('Enter')
            else:
                source.click()
                target.click()

        def producer(modal, consumer, port, kind, value_type=None):
            before = ids(modal)
            target = card(modal, consumer).locator(f'[data-blueprint-data-input="{port}"]')
            target.click()
            picker = modal.locator('[data-blueprint-node-picker]')
            expect(picker).to_be_visible()
            choice = picker.locator(f'[data-blueprint-pick-type="{kind}"]')
            expect(choice).to_be_enabled()
            choice.click()
            expect(picker).to_have_count(0)
            expect(edges(modal)).to_have_count(1)
            created, = ids(modal) - before
            if value_type:
                param = 'memberType' if kind == 'elementGroup' else 'valueType'
                expect(card(modal, created).locator(f'[data-blueprint-param="{param}"]')).to_have_value(value_type)
            modal.locator('[data-blueprint-undo]').click()
            expect(edges(modal)).to_have_count(0)
            assert ids(modal) == before
            return created

        def consumer(modal, source_id, port, kind, value_type=None):
            before = ids(modal)
            modal.locator('[data-blueprint-fit]').click()
            source = card(modal, source_id).locator(f'[data-blueprint-data-output="{port}"]')
            bounds = source.bounding_box()
            assert bounds
            blank = modal.locator('[data-blueprint-canvas]').evaluate('''canvas=>{
              const r=canvas.getBoundingClientRect();
              for(const fy of [.88,.7,.4,.15])for(const fx of [.9,.65,.4,.15]){
                const x=r.left+r.width*fx,y=r.top+r.height*fy,hit=document.elementFromPoint(x,y);
                if(hit&&canvas.contains(hit)&&!hit.closest('[data-blueprint-node],[data-blueprint-edge]'))return [x,y];
              }throw Error('No visible blank graph point');}''')
            page.mouse.move(bounds['x'] + bounds['width']/2, bounds['y'] + bounds['height']/2)
            page.mouse.down()
            page.mouse.move(*blank, steps=10)
            expect(modal.locator('[data-blueprint-wire-preview]')).to_have_count(1)
            page.mouse.up()
            picker = modal.locator('[data-blueprint-node-picker]')
            expect(picker).to_be_visible()
            picker.locator(f'[data-blueprint-pick-type="{kind}"]').click()
            expect(picker).to_have_count(0)
            expect(edges(modal)).to_have_count(1)
            created, = ids(modal) - before
            if value_type:
                expect(card(modal, created).locator('[data-blueprint-param="valueType"]')).to_have_value(value_type)
            modal.locator('[data-blueprint-undo]').click()
            expect(edges(modal)).to_have_count(0)
            assert ids(modal) == before

        def game():
            page.wait_for_url(f'{base}/game/{seed["campaign"]}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        try:
            page.goto(review.builder)
            wait_ready(page)
            page.locator('[data-builder-quick-name]').fill('Synthetic connection combination matrix')
            page.locator('[data-builder-quick-name]').press('Tab')
            artwork = upload_asset(page, 'decoration', 'Synthetic matrix off.png', harness.artwork('#375eaa'))['id']
            alternate = upload_asset(page, 'decoration', 'Synthetic matrix on.png', harness.artwork('#e58e32'))['id']
            initial = saved()
            document = deepcopy(initial['document'])
            layer = document['layers'][0]['id']
            owner, empty, torch, door, region, light, ordinary = (str(uuid4()) for _ in range(7))
            graphs = {}
            names = list(ELEMENT_ACTIONS)
            for index in range(0, len(names), 4):
                event = f'signal:Elements{index // 4}'
                actions = [node(name, name, **({**ELEMENT_ACTIONS[name], 'assetId': alternate}
                           if name == 'setAppearance' else ELEMENT_ACTIONS[name])) for name in names[index:index + 4]]
                graphs[event] = {'nodes': [node('event', 'event', event=event, x=40, y=50),
                    node('ref', 'reference', targetId=torch, x=350, y=50),
                    node('group', 'elementGroup', name='Synthetic targets', memberType='element',
                         targetIds=[torch], x=350, y=330),
                    *[dict(value, x=700, y=50 + place*230) for place, value in enumerate(actions)]], 'edges': []}
            graphs['signal:Resources'] = {'nodes': [node('event', 'event', event='signal:Resources'),
                node('lightRef', 'lightReference', targetId=light, x=350, y=50),
                node('lightGroup', 'elementGroup', name='Synthetic lights', memberType='light', targetIds=[light], x=350, y=330),
                node('soundRef', 'soundReference', trackId=seed['track'], x=350, y=600),
                node('soundGroup', 'elementGroup', name='Synthetic sounds', memberType='sound', targetIds=[seed['track']], x=350, y=850),
                node('light', 'light', targetId=light, enabled=True, x=700, y=50),
                node('sound', 'sound', trackId=seed['track'], volume=.1, x=700, y=330),
                node('soundControl', 'soundControl', trackId=seed['track'], action='stop', volume=.1, x=700, y=600),
                node('move', 'move', dx=1, dy=0, x=1000, y=50),
                node('rotate', 'rotate', degrees=90, x=1000, y=330)], 'edges': []}
            for value_type, default in (('boolean', False), ('number', 0), ('text', 'synthetic')):
                event = f'signal:Scalar{value_type}'
                graphs[event] = {'nodes': [node('event', 'event', event=event),
                    node('value', 'getVariable', scope='element', name=f'matrix{value_type}',
                         valueType=value_type, default=default, x=350, y=50),
                    node('set', 'setVariable', scope='element', name=f'matrix{value_type}',
                         valueType=value_type, value=default, x=700, y=50),
                    node('compare', 'compareValue', valueType=value_type, operator='eq', expected=default, x=700, y=350),
                    node('switch', 'switch', valueType=value_type, value=default,
                         cases=[{'id': 'case1', 'value': default}], x=1000, y=50)], 'edges': []}
            graphs['signal:Logic'] = {'nodes': [node('event', 'event', event='signal:Logic'),
                node('property', 'property', property='state', x=350, y=50),
                node('compare', 'compare', state='off', x=700, y=50),
                node('condition', 'condition', state='off', x=1000, y=50),
                node('all', 'all', x=1000, y=350), node('any', 'any', x=1000, y=650)], 'edges': []}
            graphs['interact'] = chain('interact', [node('on', 'state', targetState='on'),
                node('art', 'sprite', appearance='asset', assetId=alternate),
                node('lamp', 'light', targetId=light, enabled=True)])
            graphs['signal:Unsupported'] = chain('signal:Unsupported', [node('unsupported', 'state', targetState='on')],
                [node('image', 'reference', targetId=ordinary)], [('image', 'door', 'unsupported', 'target')])
            area_graph = chain('presence:enter', [node('operate', 'interact')],
                [node('target', 'reference', targetId=owner)], [('target', 'door', 'operate', 'target')])
            document['decorations'] = [
                {'id': owner, 'layerId': layer, 'assetId': artwork,
                 'x': 5, 'y': 5, 'width': 2, 'height': 2, 'rotation': 0, 'lever': {'state': 'off'},
                 'blueprint': behavior('lever', graphs)},
                {'id': empty, 'layerId': layer, 'assetId': None, 'empty': True, 'name': 'Matrix Empty',
                 'x': 10, 'y': 5, 'width': 3, 'height': 3, 'rotation': 20, 'lever': {'state': 'off'},
                 'blueprint': behavior('lever', {'presence:enter': area_graph})},
                {'id': torch, 'layerId': layer, 'assetId': artwork,
                 'x': 16, 'y': 5, 'width': 2, 'height': 2, 'rotation': 0,
                 'torch': {'state': 'off', 'lit': False, 'lightId': light}, 'blueprint': behavior('torch', {})},
                {'id': ordinary, 'layerId': layer, 'assetId': artwork,
                 'x': 16, 'y': 12, 'width': 2, 'height': 2, 'rotation': 0},
            ]
            document['doors'] = [{'id': door, 'layerId': layer, 'assetId': None,
                'x1': 22, 'y1': 5, 'x2': 24, 'y2': 5, 'thickness': .4, 'state': 'closed',
                'blueprint': behavior('door', {})}]
            document['regions'] = [{'id': region, 'layerId': layer, 'x': 27, 'y': 5,
                'width': 3, 'height': 3, 'name': 'Matrix region', 'enabled': True,
                'blueprint': behavior('region', {})}]
            document['lights'] = [{'id': light, 'layerId': layer, 'x': 17, 'y': 6,
                'brightRadius': 2, 'dimRadius': 3, 'color': '#ffbb66', 'intensity': .8,
                'enabled': False, 'rotation': 0, 'angle': 360, 'animation': 'torch'}]
            project = review.store(initial['id'], initial['version'], initial['folderId'], document)
            page.goto(review.builder + '?project=' + project['id'])
            wait_ready(page)
            modal = editor(owner)

            for index in range(0, len(names), 4):
                select_graph(modal, f'signal:Elements{index // 4}')
                for action in names[index:index + 4]:
                    for source_id, port, member_type in (('ref', 'door', None), ('group', 'targets', 'element')):
                        for reverse in (False, True):
                            connect(modal, card(modal, source_id).locator(f'[data-blueprint-data-output="{port}"]'),
                                card(modal, action).locator('[data-blueprint-data-input="target"]'), reverse)
                            expect(edges(modal)).to_have_count(1)
                            modal.locator('[data-blueprint-undo]').click()
                            expect(edges(modal)).to_have_count(0)
                            records.append({'case': 'existing-target-wire', 'action': action,
                                            'producer': source_id, 'reverse': reverse})
                    producer(modal, action, 'target', 'reference')
                    producer(modal, action, 'target', 'elementGroup', 'element')
                    records.append({'case': 'target-producer-picker', 'action': action, 'types': ['element', 'elementset']})
                    diagnostics()

            select_graph(modal, 'signal:Resources')
            for action, reference, group, port, member_type in (
                ('light', 'lightRef', 'lightGroup', 'light', 'light'),
                ('sound', 'soundRef', 'soundGroup', 'sound', 'sound'),
                ('soundControl', 'soundRef', 'soundGroup', 'sound', 'sound'),
                ('move', 'lightRef', 'lightGroup', 'light', 'light'),
                ('rotate', 'lightRef', 'lightGroup', 'light', 'light')):
                for source_id, output_port in ((reference, port), (group, 'targets')):
                    for reverse in (False, True):
                        connect(modal, card(modal, source_id).locator(f'[data-blueprint-data-output="{output_port}"]'),
                            card(modal, action).locator('[data-blueprint-data-input="target"]'), reverse)
                        expect(edges(modal)).to_have_count(1)
                        modal.locator('[data-blueprint-undo]').click()
                        expect(edges(modal)).to_have_count(0)
                        records.append({'case': 'resource-target-wire', 'action': action,
                                        'producer': source_id, 'reverse': reverse})
                # Transform inputs prefer element groups; resource-specific
                # actions must instead produce the correct resource group.
                if action not in ('move', 'rotate'):
                    producer(modal, action, 'target', member_type + 'Reference')
                    producer(modal, action, 'target', 'elementGroup', member_type)
                    records.append({'case': 'resource-producer-picker', 'action': action, 'memberType': member_type})
                diagnostics()

            for value_type in ('boolean', 'number', 'text'):
                select_graph(modal, f'signal:Scalar{value_type}')
                for action in ('set', 'compare', 'switch'):
                    for reverse in (False, True):
                        connect(modal, card(modal, 'value').locator('[data-blueprint-data-output="value"]'),
                            card(modal, action).locator('[data-blueprint-data-input="value"]'), reverse)
                        expect(edges(modal)).to_have_count(1)
                        modal.locator('[data-blueprint-undo]').click()
                        expect(edges(modal)).to_have_count(0)
                        records.append({'case': 'scalar-value-wire', 'action': action,
                                        'valueType': value_type, 'reverse': reverse})
                    producer(modal, action, 'value', 'getVariable', value_type)
                    producer(modal, action, 'value', 'eventContext')
                    records.append({'case': 'typed-producer-picker', 'action': action, 'valueType': value_type})
                for action in ('setVariable', 'compareValue', 'switch'):
                    consumer(modal, 'value', 'value', action, value_type)
                    records.append({'case': 'typed-consumer-picker', 'action': action, 'valueType': value_type})
                diagnostics()

            select_graph(modal, 'signal:Logic')
            connect(modal, card(modal, 'property').locator('[data-blueprint-data-output="value"]'),
                card(modal, 'compare').locator('[data-blueprint-data-input="value"]'))
            expect(edges(modal)).to_have_count(1)
            modal.locator('[data-blueprint-undo]').click()
            for action, port in (('condition', 'test'), ('all', 'a'), ('any', 'd')):
                connect(modal, card(modal, 'compare').locator('[data-blueprint-data-output="result"]'),
                    card(modal, action).locator(f'[data-blueprint-data-input="{port}"]'), True)
                expect(edges(modal)).to_have_count(1)
                modal.locator('[data-blueprint-undo]').click()
                producer(modal, action, port, 'compare')
                records.append({'case': 'state-property-boolean-logic', 'action': action, 'port': port})

            # The incompatible state value may not reach a Boolean socket, and
            # cancelling a producer chooser must not add either nodes or wires.
            before = ids(modal)
            connect(modal, card(modal, 'property').locator('[data-blueprint-data-output="value"]'),
                card(modal, 'condition').locator('[data-blueprint-data-input="test"]'))
            expect(modal.locator('[role="alert"]')).to_be_visible()
            expect(edges(modal)).to_have_count(0)
            assert ids(modal) == before
            page.keyboard.press('Escape')
            card(modal, 'condition').locator('[data-blueprint-data-input="test"]').click()
            expect(modal.locator('[data-blueprint-node-picker]')).to_be_visible()
            page.keyboard.press('Escape')
            expect(edges(modal)).to_have_count(0)
            assert ids(modal) == before
            records.append({'case': 'incompatible-value-and-picker-cancellation-preserve-graph'})
            modal.locator('[data-blueprint-close]').click()
            saved()

            for identifier, collection, kind, expected in (
                (owner, 'decorations', 'lever', {'interact', 'presence:enter', 'presence:exit', 'destroy'}),
                (empty, 'decorations', 'empty', {'interact', 'presence:enter', 'presence:exit', 'destroy'}),
                (torch, 'decorations', 'torch', {'interact', 'presence:enter', 'presence:exit', 'destroy'}),
                (door, 'doors', 'door', {'interact', 'destroy'}),
                (region, 'regions', 'region', {'presence:enter', 'presence:exit', 'destroy'})):
                modal = editor(identifier, collection)
                actual = set(modal.locator('[data-blueprint-event]').evaluate_all(
                    'items=>items.map(item=>item.dataset.blueprintEvent).filter(event=>!event.startsWith("signal:"))'))
                assert actual == expected, (kind, actual, expected)
                modal.locator('[data-blueprint-close]').click()
                records.append({'case': 'owner-event-capability', 'kind': kind, 'events': sorted(actual)})

            close_panel(page)
            page.locator('[data-builder-test]').click()
            rehearsal = page.locator('[data-playtest]')
            rehearsal.locator('[data-playtest-element]').select_option(owner)
            rehearsal.locator('[data-playtest-event]').select_option('signal:Unsupported')
            with page.expect_response(lambda response: response.request.method == 'POST'
                                     and response.url.endswith('/map-builder/test')) as rehearsed:
                rehearsal.locator('[data-playtest-run]').click()
            assert rehearsed.value.ok, rehearsed.value.text()
            prediction = rehearsed.value.json()
            assert prediction['ok'] and prediction['dryRun'], prediction
            (output / 'unsupported-prediction.json').write_text(
                json.dumps(prediction, indent=2), encoding='utf-8')
            expect(rehearsal.locator('[data-playtest-unsupported-targets]')).to_contain_text('Unsupported targets')
            expect(rehearsal.locator('[data-playtest-unsupported-targets]')).to_contain_text('Synthetic matrix off')
            page.screenshot(path=str(output / 'unsupported-existing-target-rehearsal.png'))
            rehearsal.locator('[data-playtest-close]').click()
            records.append({'case': 'unsupported-state-to-ordinary-image-shows-existing-target-name-in-server-rehearsal'})

            # Persist one real cross-object connection authored through a
            # socket, then verify that reload and in-place scene update retain it.
            modal = editor(empty)
            select_graph(modal, 'presence:enter')
            expect(edges(modal)).to_have_count(1)
            card(modal, 'operate').locator('[data-blueprint-delete]').click()
            expect(edges(modal)).to_have_count(0)
            modal.locator('[data-blueprint-undo]').click()
            expect(edges(modal)).to_have_count(1)
            modal.locator('[data-blueprint-close]').click()
            project = saved()
            page.reload()
            wait_ready(page)
            modal = editor(empty)
            select_graph(modal, 'presence:enter')
            expect(edges(modal)).to_have_count(1)
            modal.locator('[data-blueprint-close]').click()
            close_panel(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            game()
            linked = review.project(project['id'])
            scene = linked['sceneId']
            page.goto(review.builder + '?project=' + project['id'])
            wait_ready(page)
            page.locator('[data-builder-quick-name]').fill('Synthetic verified matrix update')
            page.locator('[data-builder-quick-name]').press('Tab')
            saved()
            with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                page.locator('[data-builder-generate]').click()
            assert updated.value.ok, updated.value.text()
            game()
            assert review.project(project['id'])['sceneId'] == scene
            native = page.request.get(f'/api/maps/{scene}/state').json()
            empty_native = next(row for row in native['images'] if row.get('empty'))
            assert empty_native['blueprint']['graphs']['presence:enter']['nodes']
            records.append({'case': 'typed-connection-autosave-reload-and-linked-scene-replacement'})

            # A map with no external elements or lights must not offer an
            # unavailable reference. Self remains a valid element group.
            stripped = deepcopy(project['document'])
            stripped['name'] = 'Synthetic resource-free matrix'
            stripped['lights'], stripped['doors'], stripped['regions'] = [], [], []
            stripped['decorations'] = [deepcopy(document['decorations'][0])]
            stripped['decorations'][0]['blueprint'] = behavior('lever', {
                'interact': chain('interact', [node('move', 'move', dx=1, dy=0)])})
            stripped['decorations'][0].pop('name', None)
            project_without_resources = review.store(str(uuid4()), 0, project['folderId'], stripped)
            page.goto(review.builder + '?project=' + project_without_resources['id'])
            wait_ready(page)
            modal = editor(owner)
            card(modal, 'move').locator('[data-blueprint-data-input="target"]').click()
            picker = modal.locator('[data-blueprint-node-picker]')
            expect(picker.locator('[data-blueprint-pick-type="reference"]')).to_be_disabled()
            expect(picker.locator('[data-blueprint-pick-type="lightReference"]')).to_be_disabled()
            expect(picker.locator('[data-blueprint-pick-type="elementGroup"]')).to_be_enabled()
            page.keyboard.press('Escape')
            producer(modal, 'move', 'target', 'elementGroup', 'element')
            modal.locator('[data-blueprint-close]').click()
            records.append({'case': 'no-external-elements-or-lights-disables-unavailable-references-and-allows-self-group'})
            diagnostics()
        except Exception:
            diagnostics()
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors,
            'nativeDialogs': dialogs, 'scope': 'Finite UI socket and chooser matrix; synthetic campaign only.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
