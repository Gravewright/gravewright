"""Check real door-instance nodes, verb ports and legacy graph continuity.

Uses the common disposable builder fixture, synthetic art/audio and an owned
localhost server. All screenshots and state stay inside the selected output.
"""
from __future__ import annotations

from copy import deepcopy
import re
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_tool, builder_workspace, change_locale
from map_builder_reference import set_name, upload_asset, wait_ready


def legacy_blueprint(track_id):
    """Different events make accidental graph replacement observable."""
    graphs = {}
    for index, event in enumerate(('enter:open', 'exit:open', 'interact:closed')):
        action = f'legacy_sound_{index}'
        graphs[event] = {
            'nodes': [
                {'id': 'event', 'type': 'event', 'event': event, 'x': 40, 'y': 60},
                {'id': action, 'type': 'sound', 'trackId': track_id,
                 'volume': .2 + index * .1, 'x': 400, 'y': 80 + index * 30},
            ],
            'edges': [{'from': 'event', 'output': 'next', 'to': action}],
        }
    return {'version': 1, 'kind': 'door',
            'states': {state: {'appearance': 'inherit'}
                       for state in ('closed', 'open', 'locked')},
            'graphs': graphs}


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    records, errors, dialogs, failed = [], [], [], []
    campaign = seed['campaign']
    builder = f'/game/{campaign}/map-builder'
    api = f'/api/containers/{campaign}/map-builder'
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base,
                                      viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('requestfailed', lambda request: failed.append(
            {'url': request.url, 'error': request.failure}))

        def native_dialog(dialog):
            dialogs.append(dialog.message)
            dialog.dismiss()

        page.on('dialog', native_dialog)
        try:
            page.goto(builder)
            wait_ready(page)
            set_name(page, 'Synthetic instance nodes')
            image_id = upload_asset(page, 'door', 'Synthetic instance door.png',
                                    harness.artwork('#bb6942'))['id']

            def stroke(start, end):
                points = page.locator('[data-builder-canvas]').evaluate(
                    """(canvas, points) => points.map(([x,y]) => {
                      const point = new DOMPoint(x,y).matrixTransform(canvas.getScreenCTM());
                      return {x:point.x,y:point.y};
                    })""", [start, end])
                page.mouse.move(points[0]['x'], points[0]['y'])
                page.mouse.down()
                page.mouse.move(points[1]['x'], points[1]['y'], steps=5)
                page.mouse.up()

            def save():
                if page.locator('[data-map-builder]').get_attribute('data-save-state') != 'saved':
                    with page.expect_response(lambda response:
                                              response.request.method == 'POST'
                                              and '/map-builder/projects/' in response.url
                                              and not response.url.endswith(('/generate', '/update'))) as saved:
                        page.locator('[data-builder-save]').click()
                    response = saved.value
                else:
                    project_id = page.evaluate("new URL(location.href).searchParams.get('project')")
                    response = page.request.get(api + '/projects/' + project_id)
                assert response.ok, response.text()
                return response.json()['project']

            def store(project):
                result = page.evaluate("""async args => {
                  const csrf = await (await fetch('/__gravewright/csrf')).json();
                  const response = await fetch(args.url, {method:'POST',
                    headers:{'Content-Type':'application/json', [csrf.header]:csrf.token},
                    body:JSON.stringify(args.body)});
                  return {status:response.status, body:await response.json()};
                }""", {'url': api + '/projects/' + project['id'], 'body': {
                    'request_id': str(uuid4()), 'expected_version': project['version'],
                    'folder_id': project['folderId'], 'document': project['document']}})
                assert result['status'] == 200, result
                page.evaluate('sessionStorage.clear()')
                page.goto(builder + '?project=' + project['id'])
                wait_ready(page)
                return result['body']['project']

            builder_tool(page, 'door')
            page.locator('[data-builder-brush-material]').select_option(image_id)
            stroke((8, 6), (10, 6))
            stroke((14, 9), (16, 9))
            initial = save()
            first, second = initial['document']['doors']
            assert 'blueprint' not in first and 'blueprint' not in second, initial

            def open_editor(door_id, tool='select'):
                builder_tool(page, tool)
                builder_workspace(page)
                page.locator(f'[data-builder-doors] [data-object-id="{door_id}"]').dblclick()
                modal = page.locator('[data-smart-object-modal]')
                expect(modal).to_be_visible()
                expect(modal.locator('[data-blueprint-instance]')).to_have_count(1)
                expect(modal.locator('[data-blueprint-instance]')).to_have_attribute(
                    'data-blueprint-instance-id', door_id)
                assert modal.evaluate('element => !!element.closest("[role=dialog]")')
                return modal

            def choose_event(modal, key):
                target = modal.locator(f'[data-blueprint-event="{key}"]')
                if not target.is_visible():
                    modal.locator('[data-blueprint-state-events] summary').click()
                target.click()

            def drag_back(heading):
                heading.scroll_into_view_if_needed()
                before = heading.evaluate('element => ({left:element.parentElement.style.left,top:element.parentElement.style.top})')
                box = heading.bounding_box()
                start = {'x': box['x'] + box['width'] * .35,
                         'y': box['y'] + box['height'] * .5}
                page.mouse.move(start['x'], start['y'])
                page.mouse.down()
                page.mouse.move(start['x'] + 60, start['y'] + 30, steps=4)
                moved = heading.evaluate('element => ({left:element.parentElement.style.left,top:element.parentElement.style.top})')
                assert moved != before, (before, moved)
                page.mouse.move(start['x'], start['y'], steps=4)
                page.mouse.up()
                assert heading.evaluate('element => ({left:element.parentElement.style.left,top:element.parentElement.style.top})') == before

            def check_ports(modal, labels):
                instance = modal.locator('[data-blueprint-instance]')
                ports = instance.locator('[data-blueprint-event-port="change"], [data-blueprint-event-port="interact"]')
                expect(ports).to_have_count(2)
                assert ports.evaluate_all(
                    'ports => ports.map(port => port.dataset.blueprintEventPort)') == ['interact', 'change']
                verb_labels = {'en': ('On state change', 'On interaction'),
                               'pt-BR': ('Ao mudar estado', 'Ao interagir'),
                               'es': ('Al cambiar de estado', 'Al interactuar')}[page.locator('html').get_attribute('lang')]
                for key, label in zip(('change', 'interact'), verb_labels):
                    expect(instance.locator(f'[data-blueprint-event-port="{key}"]')).to_have_accessible_name(
                        re.compile(label))
                for state, label in zip(('open', 'closed', 'locked'), labels):
                    expect(modal.locator(f'[data-blueprint-appearance-state] option[value="{state}"]')).to_contain_text(label)
                colors = ports.evaluate_all(
                    'ports => ports.map(port => getComputedStyle(port.querySelector("[data-blueprint-state-dot]")).backgroundColor)')
                assert len(colors) == 2 and len(set(colors)) == 2, colors
                rgb = [[int(component) for component in color.removeprefix('rgb(').removesuffix(')').split(',')]
                       for color in colors]
                assert rgb[0][1] > rgb[0][0] and rgb[0][1] > rgb[0][2], colors
                assert rgb[1][0] > rgb[1][2] and rgb[1][1] > rgb[1][2], colors
                geometry = instance.evaluate("""element => {
                  const box = element.getBoundingClientRect();
                  const content=element.querySelector('.smart-object__node-content').getBoundingClientRect();
                  return {height:box.height,contentBottom:content.bottom-box.top,
                    ports:[...element.querySelectorAll('[data-blueprint-event-port]')]
                    .map(port => {const rect=port.getBoundingClientRect(); return {top:rect.top-box.top,bottom:rect.bottom-box.top};})};
                }""")
                assert all(port['top'] >= geometry['contentBottom'] - 1
                           for port in geometry['ports']), geometry
                return colors

            modal = open_editor(first['id'], 'door')
            expect(modal.locator('[data-blueprint-instance-name]')).to_have_text('Door 1')
            expect(modal.locator('[data-blueprint-instance-state]')).to_contain_text('Closed')
            colors = check_ports(modal, ('Open', 'Closed', 'Locked'))
            page.screenshot(path=str(output / 'instance-door-desktop.png'))
            drag_back(modal.locator('[data-blueprint-instance] [data-blueprint-drag]'))
            modal.locator('[data-blueprint-save]').click()
            expect(modal).to_have_count(0)
            assert save()['document'] == initial['document']
            records.append({'case': 'real-door-instance-with-labeled-verb-bottom-ports', 'colors': colors})
            records.append({'case': 'save-without-editing-does-not-create-empty-blueprint'})

            modal = open_editor(second['id'])
            expect(modal.locator('[data-blueprint-instance-name]')).to_have_text('Door 2')
            modal.locator('[data-blueprint-appearance-state]').select_option('open')
            modal.locator('[data-blueprint-appearance]').select_option('hidden')
            modal.locator('[data-blueprint-cancel]').click()
            expect(modal).to_have_count(0)
            expect(page.locator('[data-builder-viewport]')).to_be_focused()
            assert save()['document'] == initial['document']
            expect(page.locator('[data-builder-doors] [data-object-id]')).to_have_count(2)
            records.append({'case': 'second-door-has-own-identity-and-cancel-preserves-geometry-and-state'})

            legacy = deepcopy(initial)
            legacy['document']['doors'][0]['blueprint'] = legacy_blueprint(seed['track'])
            legacy['document']['doors'][1]['state'] = 'locked'
            legacy = store(legacy)
            modal = open_editor(second['id'])
            expect(modal.locator('[data-blueprint-instance-state]')).to_contain_text('Locked')
            modal.locator('[data-blueprint-close]').click()
            records.append({'case': 'instance-label-reflects-native-state-without-changing-it'})

            modal = open_editor(first['id'])
            choose_event(modal, 'enter:open')
            drag_back(modal.locator('[data-blueprint-drag=legacy_sound_0]'))
            for trigger, state, action in (
                    ('enter', 'open', 'legacy_sound_0'),
                    ('exit', 'open', 'legacy_sound_1'),
                    ('interact', 'closed', 'legacy_sound_2')):
                modal.locator(f'[data-blueprint-event="{trigger}:{state}"]').click()
                expect(modal.locator(f'[data-blueprint-event="{trigger}:{state}"]')).to_have_attribute('aria-pressed', 'true')
                expect(modal.locator(f'[data-blueprint-node="{action}"]')).to_have_count(1)
                expect(modal.locator('[data-blueprint-edge]')).to_have_count(1)
            modal.locator('[data-blueprint-save]').click()
            expect(modal).to_have_count(0)
            assert save()['document'] == legacy['document']
            records.append({'case': 'legacy-enter-exit-interaction-graphs-open-and-save-without-conversion'})
            records.append({'case': 'root-and-action-pointer-drags-return-to-origin-without-saving-transient-changes'})

            modal = open_editor(first['id'])
            choose_event(modal, 'enter:open')
            modal.locator('[data-blueprint-appearance]').select_option('hidden')
            old_nodes = set(modal.locator('[data-blueprint-node]').evaluate_all(
                'nodes => nodes.map(node => node.dataset.blueprintNode)'))
            modal.locator('[data-blueprint-add]').click()
            picker = modal.locator('[data-blueprint-node-picker]')
            picker.locator('[data-blueprint-picker-search]').fill('play sound')
            expect(picker.locator('[data-blueprint-pick-type=state]')).to_be_hidden()
            picker.locator('[data-blueprint-picker-search]').press('Enter')
            expect(picker).to_have_count(0)
            added_id, = set(modal.locator('[data-blueprint-node]').evaluate_all(
                'nodes => nodes.map(node => node.dataset.blueprintNode)')) - old_nodes
            added_sound = modal.locator(f'[data-blueprint-node="{added_id}"]')
            positions = modal.locator('[data-blueprint-node]').evaluate_all("""nodes => nodes.map(node => ({
              id:node.dataset.blueprintNode,x:node.offsetLeft,y:node.offsetTop,width:node.offsetWidth,height:node.offsetHeight}))""")
            added_position, = [position for position in positions if position['id'] == added_id]
            assert not any(added_position['x'] < position['x'] + position['width']
                           and added_position['x'] + added_position['width'] > position['x']
                           and added_position['y'] < position['y'] + position['height']
                           and added_position['y'] + added_position['height'] > position['y']
                           for position in positions if position['id'] != added_id), positions
            added_sound.locator('[data-blueprint-param=volume]').fill('.333')
            added_sound.locator('[data-blueprint-param=volume]').press('Tab')
            modal.locator('[data-blueprint-instance] [data-blueprint-output=next]').click()
            modal.locator(f'[data-blueprint-input="{added_id}"]').click()
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(2)
            modal.locator('[data-blueprint-simulate]').click()
            assert modal.locator('[data-blueprint-trace-node]').evaluate_all(
                'nodes => nodes.map(node => node.dataset.blueprintTraceNode)') == ['legacy_sound_0', added_id]
            assert page.request.get(api + '/projects/' + legacy['id']).json()['project']['document'] == legacy['document']
            modal.locator('[data-blueprint-fit]').click()
            page.screenshot(path=str(output / 'instance-door-two-branches.png'))
            modal.locator('[data-blueprint-save]').click()
            edited = save()
            blueprint = edited['document']['doors'][0]['blueprint']
            assert blueprint['version'] == 2, blueprint
            assert blueprint['states']['open'] == {'appearance': 'hidden'}, blueprint
            expected_graphs = deepcopy(legacy['document']['doors'][0]['blueprint']['graphs'])
            for graph in expected_graphs.values():
                for edge in graph['edges']:
                    edge['kind'] = 'execution'
            added_node, = [node for node in blueprint['graphs']['enter:open']['nodes']
                           if node['id'] == added_id]
            assert added_node['type'] == 'sound' and added_node['trackId'] == seed['track'], added_node
            assert added_node['volume'] == .333, added_node
            expected_graphs['enter:open']['nodes'].append(added_node)
            expected_graphs['enter:open']['edges'].append(
                {'from': 'event', 'output': 'next', 'to': added_id, 'kind': 'execution'})
            assert blueprint['graphs'] == expected_graphs, blueprint
            assert edited['document']['doors'][1] == legacy['document']['doors'][1]
            page.reload()
            wait_ready(page)
            assert save()['document'] == edited['document']
            modal = open_editor(first['id'])
            choose_event(modal, 'enter:open')
            expect(modal.locator('[data-blueprint-appearance]')).to_have_value('hidden')
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(2)
            expect(modal.locator('[data-blueprint-type=sound]')).to_have_count(2)
            modal.locator('[data-blueprint-close]').click()
            records.append({'case': 'meaningful-edit-explicitly-upgrades-and-preserves-all-legacy-effects-on-reload'})
            records.append({'case': 'one-instance-port-keeps-two-ordered-execution-branches-and-simulates-without-writes'})

            labels_by_locale = {
                'en': ('Smart object', ('Open', 'Closed', 'Locked')),
                'pt-BR': ('Objeto Inteligente', ('Aberta', 'Fechada', 'Trancada')),
                'es': ('Objeto inteligente', ('Abierta', 'Cerrada', 'Bloqueada')),
            }
            for locale, (title, labels) in labels_by_locale.items():
                change_locale(page, locale, campaign)
                for width, height in ((390, 844), (320, 700)):
                    page.set_viewport_size({'width': width, 'height': height})
                    page.goto(builder + '?project=' + edited['id'])
                    wait_ready(page)
                    modal = open_editor(first['id'])
                    expect(modal).to_contain_text(title)
                    check_ports(modal, labels)
                    modal.locator('[data-blueprint-instance]').scroll_into_view_if_needed()
                    bounds = modal.locator('[data-blueprint-instance]').evaluate("""element => {
                      const root=element.getBoundingClientRect(), canvas=element.closest('[data-blueprint-canvas]').getBoundingClientRect();
                      return {root:{left:root.left,right:root.right},canvas:{left:canvas.left,right:canvas.right}};
                    }""")
                    assert bounds['root']['left'] >= bounds['canvas']['left'] - 1, bounds
                    assert bounds['root']['right'] <= bounds['canvas']['right'] + 1, bounds
                    page.screenshot(path=str(output / f'instance-door-{locale}-{width}.png'))
                    choose_event(modal, 'enter:open')
                    modal.locator('[data-blueprint-event-port="enter:open"]').focus()
                    page.keyboard.press('Enter')
                    expect(modal.locator('[data-blueprint-appearance]')).to_have_value('hidden')
                    metrics = modal.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    for _ in range(22):
                        page.keyboard.press('Tab')
                        assert modal.evaluate('element => element.closest("[role=dialog]").contains(document.activeElement)')
                    modal.locator('[data-blueprint-close]').click()
                    expect(modal).to_have_count(0)
                    assert save()['document'] == edited['document']
                    records.append({'case': 'localized-responsive-instance-node-with-keyboard-lifecycle',
                                    'locale': locale, 'width': width, 'metrics': metrics})

            # Door 1 targets Door 2 through an Element reference and a typed door wire.
            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(builder + '?project=' + edited['id'])
            wait_ready(page)
            modal = open_editor(first['id'])
            choose_event(modal, 'enter:closed')

            def center(locator):
                box = locator.bounding_box()
                return box['x'] + box['width'] / 2, box['y'] + box['height'] / 2

            def drag_to(source, point):
                page.mouse.move(*center(source))
                page.mouse.down()
                page.mouse.move(*point, steps=8)
                page.mouse.up()

            def empty_point():
                return modal.locator('[data-blueprint-canvas]').evaluate("""canvas => {
                  const r = canvas.getBoundingClientRect();
                  for (const fy of [.8, .6, .35]) for (const fx of [.85, .65, .45]) {
                    const x = r.left + r.width * fx, y = r.top + r.height * fy, hit = document.elementFromPoint(x, y);
                    if (hit && canvas.contains(hit) && !hit.closest('[data-blueprint-node]')) return [x, y];
                  }
                  throw Error('No empty graph point');
                }""")

            modal.locator('[data-blueprint-add]').click()
            modal.locator('[data-blueprint-node-picker] [data-blueprint-pick-type=reference]').click()
            reference = modal.locator('[data-blueprint-type=reference]')
            expect(reference.locator('[data-blueprint-param=targetId] option')).to_have_count(1)
            expect(reference.locator('[data-blueprint-param=targetId]')).to_have_value(second['id'])
            modal.locator('[data-blueprint-fit]').click()
            drag_to(reference.locator('[data-blueprint-data-output=door]'), empty_point())
            picker = modal.locator('[data-blueprint-node-picker]')
            compatible = set(picker.locator('[data-blueprint-pick-type]').evaluate_all(
                'items => items.map(item => item.dataset.blueprintPickType)'))
            assert {'barrier', 'property', 'reveal', 'state'} <= compatible, compatible
            assert not {'condition', 'sound', 'light', 'sequence'} & compatible, compatible
            picker.locator('[data-blueprint-pick-type=state]').click()
            action = modal.locator('[data-blueprint-type=state]')
            modal.locator('[data-blueprint-fit]').click()
            drag_to(modal.locator('[data-blueprint-state-port=closed]'), center(action.locator('[data-blueprint-input]')))
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(2)
            # Pick the target on the map: the modal steps aside, Escape cancels, a click picks.
            pick = reference.locator('[data-blueprint-pick-map=elements]')
            pick.click()
            expect(modal).to_be_hidden()
            expect(page.locator('[data-builder-notice]')).to_be_visible()
            page.keyboard.press('Escape')
            expect(modal).to_be_visible()
            expect(page.locator('[data-builder-notice]')).to_be_hidden()
            modal.locator('[data-blueprint-type=reference] [data-blueprint-pick-map=elements]').click()
            expect(modal).to_be_hidden()
            spot = page.locator('[data-builder-canvas]').evaluate(
                """canvas => { const p = new DOMPoint(15, 9).matrixTransform(canvas.getScreenCTM()); return [p.x, p.y]; }""")
            page.mouse.click(*spot)
            expect(modal).to_be_visible()
            expect(modal.locator('[data-blueprint-type=reference] [data-blueprint-param=targetId]')).to_have_value(second['id'])
            expect(modal.locator('[data-blueprint-type=reference] [data-blueprint-pick-map=elements]')).to_be_focused()
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator('[data-blueprint-trace]')).to_contain_text('Change state: Opened · Door 2')
            page.screenshot(path=str(output / 'element-reference.png'))
            modal.locator('[data-blueprint-save]').click()
            expect(modal).to_have_count(0)
            referenced = save()
            graph = referenced['document']['doors'][0]['blueprint']['graphs']['enter:closed']
            ref_node, = [row for row in graph['nodes'] if row['type'] == 'reference']
            assert ref_node['targetId'] == second['id'], graph
            assert any(edge['kind'] == 'data' and edge['input'] == 'target' for edge in graph['edges']), graph
            records.append({'case': 'element-reference-targets-another-door-through-a-typed-wire'})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    assert not [request for request in failed if request['error'] != 'net::ERR_ABORTED'], failed
    return {'passed': True, 'cases': records, 'pageErrors': errors,
            'nativeDialogs': dialogs, 'failedRequests': failed,
            'assets': 'Generated solid-color PNG and silent WAV; no operator data.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
