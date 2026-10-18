"""Exercise dragging real graph cables and choosing a node at the drop point.

Uses disposable builder data and generated image/audio fixtures. Mouse and CDP
touch input exercise pointer capture rather than dispatching synthetic clicks.
"""
from __future__ import annotations

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_tool, change_locale
from map_builder_reference import set_name, upload_asset, wait_ready


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    records, errors, dialogs, failed = [], [], [], []
    campaign = seed['campaign']
    builder = f'/game/{campaign}/map-builder'
    api = f'/api/containers/{campaign}/map-builder'
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, has_touch=True,
                                      viewport={'width': 1440, 'height': 960})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        touch = context.new_cdp_session(page)
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
            set_name(page, 'Synthetic cable dragging')
            image_id = upload_asset(page, 'door', 'Synthetic drag door.png',
                                    harness.artwork('#a95e3c'))['id']
            builder_tool(page, 'door')
            page.locator('[data-builder-brush-material]').select_option(image_id)
            points = page.locator('[data-builder-canvas]').evaluate(
                """canvas => [[8,6],[10,6]].map(([x,y]) => {
                  const point = new DOMPoint(x,y).matrixTransform(canvas.getScreenCTM());
                  return {x:point.x,y:point.y};
                })""")
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

            initial = save()
            door_id, = [door['id'] for door in initial['document']['doors']]

            def stored():
                return page.request.get(api + '/projects/' + initial['id']).json()['project']

            def open_editor():
                builder_tool(page, 'select')
                page.locator(f'[data-builder-doors] [data-object-id="{door_id}"]').dblclick()
                modal = page.locator('[data-smart-object-modal]')
                expect(modal).to_be_visible()
                expect(modal.locator('[data-blueprint-instance]')).to_have_count(1)
                return modal

            def center(locator):
                locator.scroll_into_view_if_needed()
                box = locator.bounding_box()
                assert box, locator
                return {'x': box['x'] + box['width'] / 2,
                        'y': box['y'] + box['height'] / 2}

            def blank_point(modal, *, side='right'):
                canvas = modal.locator('[data-blueprint-canvas]')
                canvas.scroll_into_view_if_needed()
                return canvas.evaluate("""(canvas, side) => {
                  const r=canvas.getBoundingClientRect();
                  const xs=side==='left' ? [.08,.25,.45,.7,.9] : [.88,.7,.5,.28,.1];
                  for(const fy of [.85,.65,.4,.15]) for(const fx of xs) {
                    const x=r.left+Math.max(12,Math.min(r.width-12,r.width*fx));
                    const y=r.top+Math.max(12,Math.min(r.height-12,r.height*fy));
                    const hit=document.elementFromPoint(x,y);
                    if(hit && canvas.contains(hit) && !hit.closest('[data-blueprint-node]')) return {x,y};
                  }
                  throw Error('No empty graph point is visible');
                }""", side)

            def logical_point(modal, point):
                return modal.locator('.smart-object__plane').evaluate("""(plane,p) => {
                  const rect=plane.getBoundingClientRect(), zoom=rect.width/plane.offsetWidth;
                  return {x:Math.max(0,Math.min(4700,Math.round((p.x-rect.left)/zoom-320))),
                          y:Math.max(0,Math.min(4700,Math.round((p.y-rect.top)/zoom-160))),zoom};
                }""", point)

            def drag(modal, source, target=None, *, touch_input=False, release=True):
                start = center(source)
                target = target or blank_point(modal)
                if touch_input:
                    touch.send('Input.dispatchTouchEvent', {'type': 'touchStart',
                        'touchPoints': [{**start, 'id': 1, 'radiusX': 1, 'radiusY': 1}]})
                    for step in range(1, 8):
                        fraction = step / 7
                        point = {'x': start['x'] + (target['x'] - start['x']) * fraction,
                                 'y': start['y'] + (target['y'] - start['y']) * fraction,
                                 'id': 1, 'radiusX': 1, 'radiusY': 1}
                        touch.send('Input.dispatchTouchEvent', {'type': 'touchMove',
                                                               'touchPoints': [point]})
                else:
                    page.mouse.move(start['x'], start['y'])
                    page.mouse.down()
                    page.mouse.move(target['x'], target['y'], steps=10)
                expect(modal.locator('[data-blueprint-wire-preview]')).to_have_count(1)
                preview = modal.locator('[data-blueprint-wire-preview]').get_attribute('d')
                assert preview and 'C' in preview, preview
                if release:
                    if touch_input:
                        touch.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
                    else:
                        page.mouse.up()
                return target

            def choose(modal, type_name):
                picker = modal.locator('[data-blueprint-node-picker]')
                expect(picker).to_be_visible()
                assert picker.get_attribute('role') == 'dialog'
                before = set(modal.locator('[data-blueprint-node]').evaluate_all(
                    'nodes => nodes.map(node => node.dataset.blueprintNode)'))
                picker.locator(f'[data-blueprint-pick-type={type_name}]').click()
                expect(picker).to_have_count(0)
                after = set(modal.locator('[data-blueprint-node]').evaluate_all(
                    'nodes => nodes.map(node => node.dataset.blueprintNode)'))
                added, = after - before
                expect(modal.locator('[data-blueprint-wire-preview]')).to_have_count(0)
                return added

            modal = open_editor()
            expect(modal.locator('[data-blueprint-state-port=closed]')).to_have_attribute('aria-pressed', 'true')
            drag(modal, modal.locator('[data-blueprint-state-port=open]'))
            picker = modal.locator('[data-blueprint-node-picker]')
            expect(picker).to_be_visible()
            expect(picker.locator('[data-blueprint-pick-type=light]')).to_be_disabled()
            expect(picker.locator('[data-blueprint-pick-type=sound]')).to_be_enabled()
            expect(modal.locator('[data-blueprint-node]')).to_have_count(1)
            assert stored()['document'] == initial['document']
            page.screenshot(path=str(output / 'open-port-drag-node-picker.png'))
            page.keyboard.press('Escape')
            expect(picker).to_have_count(0)
            expect(modal).to_be_visible()
            expect(modal.locator('[data-blueprint-wire-preview]')).to_have_count(0)
            expect(modal.locator('[data-blueprint-state-port=open]')).to_be_focused()
            modal.locator('[data-blueprint-save]').click()
            assert save()['document'] == initial['document']
            records.append({'case': 'unselected-open-port-drags-live-wire-and-release-opens-node-choice-without-writing'})
            records.append({'case': 'escape-cancels-picker-and-save-does-not-create-phantom-graph'})

            modal = open_editor()
            outside = center(modal.locator('#smart-object-title'))
            drag(modal, modal.locator('[data-blueprint-state-port=open]'), outside)
            expect(modal.locator('[data-blueprint-node-picker]')).to_have_count(0)
            expect(modal.locator('[data-blueprint-wire-preview]')).to_have_count(0)
            drag(modal, modal.locator('[data-blueprint-state-port=locked]'), release=False)
            page.keyboard.press('Escape')
            page.mouse.up()
            expect(modal.locator('[data-blueprint-node-picker]')).to_have_count(0)
            expect(modal.locator('[data-blueprint-wire-preview]')).to_have_count(0)
            expect(modal).to_be_visible()
            drag(modal, modal.locator('[data-blueprint-state-port=locked]'),
                 touch_input=True, release=False)
            touch.send('Input.dispatchTouchEvent', {'type': 'touchCancel', 'touchPoints': []})
            expect(modal.locator('[data-blueprint-node-picker]')).to_have_count(0)
            expect(modal.locator('[data-blueprint-wire-preview]')).to_have_count(0)
            drag(modal, modal.locator('[data-blueprint-state-port=open]'))
            modal.locator('[data-blueprint-picker-cancel]').click()
            expect(modal.locator('[data-blueprint-node-picker]')).to_have_count(0)
            drag(modal, modal.locator('[data-blueprint-state-port=open]'))
            modal.locator('[data-blueprint-preview]').click()
            expect(modal.locator('[data-blueprint-node-picker]')).to_have_count(0)
            modal.locator('[data-blueprint-save]').click()
            assert save()['document'] == initial['document']
            records.append({'case': 'outside-release-escape-mid-drag-touch-cancel-cancel-button-and-outside-click-discard-pending-wire'})

            modal = open_editor()
            point = blank_point(modal)
            logical = logical_point(modal, point)
            drag(modal, modal.locator('[data-blueprint-state-port=open]'), point)
            first_sound = choose(modal, 'sound')
            sound = modal.locator(f'[data-blueprint-node="{first_sound}"]')
            sound.locator('[data-blueprint-param=volume]').fill('.26')
            sound.locator('[data-blueprint-param=volume]').press('Tab')
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(1)
            position = sound.evaluate('element => ({x:element.offsetLeft-320,y:element.offsetTop-160})')
            assert abs(position['x'] - logical['x']) <= 1 and abs(position['y'] - logical['y']) <= 1, (position, logical)
            drag(modal, modal.locator('[data-blueprint-state-port=open]'))
            second_sound = choose(modal, 'sound')
            sound_two = modal.locator(f'[data-blueprint-node="{second_sound}"]')
            sound_two.locator('[data-blueprint-param=volume]').fill('.61')
            sound_two.locator('[data-blueprint-param=volume]').press('Tab')
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(2)
            modal.locator('[data-blueprint-simulate]').click()
            assert modal.locator('[data-blueprint-trace-node]').evaluate_all(
                'nodes => nodes.map(node => node.dataset.blueprintTraceNode)') == [first_sound, second_sound]
            assert stored()['document'] == initial['document']
            records.append({'case': 'choose-play-sound-creates-node-at-drop-and-two-branches-preserve-execution-order'})

            # Place the two cards side by side through the editor's keyboard
            # controls so both endpoints stay visible while dragging a cable.
            for identifier, desired in ((first_sound, (400, 60)),
                                        (second_sound, (750, 60))):
                card = modal.locator(f'[data-blueprint-node="{identifier}"]')
                current = card.evaluate('element => ({x:element.offsetLeft-320,y:element.offsetTop-160})')
                heading = card.locator('[data-blueprint-drag]')
                heading.focus()
                for axis, negative, positive, value in (
                        ('x', 'ArrowLeft', 'ArrowRight', desired[0]),
                        ('y', 'ArrowUp', 'ArrowDown', desired[1])):
                    difference = value - current[axis]
                    key = positive if difference >= 0 else negative
                    for _ in range(int(abs(difference) // 50)):
                        heading.press('Shift+' + key)
                    for _ in range(round(abs(difference) % 50 / 10)):
                        heading.press(key)
            modal.locator('[data-blueprint-fit]').click()
            target = center(sound_two.locator('[data-blueprint-input]'))
            drag(modal, sound.locator('[data-blueprint-output=next]'), target)
            expect(modal.locator('[data-blueprint-node-picker]')).to_have_count(0)
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(3)
            target = center(sound.locator('[data-blueprint-input]'))
            drag(modal, sound_two.locator('[data-blueprint-output=next]'), target)
            expect(modal.locator('[data-blueprint-node-picker]')).to_have_count(0)
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(3)
            expect(modal.locator('[role=alert]')).to_be_visible()
            records.append({'case': 'dragging-to-input-connects-directly-and-cycle-rejection-preserves-existing-edges'})
            modal.locator('[data-blueprint-fit]').click()
            page.screenshot(path=str(output / 'open-port-connected-branches.png'))
            modal.locator('[data-blueprint-save]').click()
            edited = save()
            blueprint = edited['document']['doors'][0]['blueprint']
            graph = blueprint['graphs']['enter:open']
            assert blueprint['version'] == 2 and len(graph['nodes']) == 3 and len(graph['edges']) == 3, blueprint
            assert all(edge['kind'] == 'execution' for edge in graph['edges']), graph
            assert [node['volume'] for node in graph['nodes'] if node['type'] == 'sound'] == [.26, .61], graph
            page.reload()
            wait_ready(page)
            assert save()['document'] == edited['document']
            records.append({'case': 'chosen-node-parameters-and-execution-connections-survive-server-save-and-reload'})

            modal = open_editor()
            modal.locator('[data-blueprint-state-port=closed]').click()
            for _ in range(3):
                modal.get_by_role('button', name='Zoom out', exact=True).click()
            # Pan by dragging empty graph space; the drop position must follow the camera.
            start = blank_point(modal, side='left')
            plane_before = modal.locator('.smart-object__plane').bounding_box()
            page.mouse.move(start['x'], start['y'])
            page.mouse.down()
            page.mouse.move(start['x'] + 40, start['y'] + 25, steps=4)
            page.mouse.up()
            plane_after = modal.locator('.smart-object__plane').bounding_box()
            # The camera uses integer scroll offsets, so allow one pixel of rounding.
            assert abs(plane_after['x'] - plane_before['x'] - 40) <= 1 and abs(plane_after['y'] - plane_before['y'] - 25) <= 1, (plane_before, plane_after)
            expect(modal.locator('[data-blueprint-node-picker]')).to_have_count(0)
            point = blank_point(modal)
            logical = logical_point(modal, point)
            assert logical['zoom'] < .7, logical
            drag(modal, modal.locator('[data-blueprint-state-port=closed]'), point)
            state_node = choose(modal, 'state')
            value = modal.locator(f'[data-blueprint-node="{state_node}"]')
            position = value.evaluate('element => ({x:element.offsetLeft-320,y:element.offsetTop-160})')
            assert abs(position['x'] - logical['x']) <= 1 and abs(position['y'] - logical['y']) <= 1, (position, logical)
            modal.locator('[data-blueprint-cancel]').click()
            assert save()['document'] == edited['document']
            records.append({'case': 'zoom-and-scrolling-preserve-logical-drop-position-and-cancel-discards-created-node', 'zoom': logical['zoom']})

            modal = open_editor()
            port = modal.locator('[data-blueprint-state-port=locked]')
            port.focus()
            page.keyboard.press('Enter')
            expect(modal.locator('[data-blueprint-node-picker]')).to_be_visible()
            page.keyboard.press('Escape')
            expect(modal.locator('[data-blueprint-node-picker]')).to_have_count(0)
            expect(port).to_be_focused()
            page.keyboard.press('Space')
            picker = modal.locator('[data-blueprint-node-picker]')
            expect(picker).to_be_visible()
            picker.locator('[data-blueprint-pick-type=state]').focus()
            page.keyboard.press('Enter')
            expect(picker).to_have_count(0)
            expect(modal.locator('[data-blueprint-type=state]')).to_have_count(1)
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(1)
            port.focus()
            page.keyboard.press('Enter')
            condition_id = choose(modal, 'condition')
            state_output = modal.locator('[data-blueprint-type=state] [data-blueprint-output=next]')
            state_output.focus()
            page.keyboard.press('Shift+Enter')
            expect(modal.locator('[data-blueprint-node-picker]')).to_have_count(0)
            modal.locator(f'[data-blueprint-input="{condition_id}"]').focus()
            page.keyboard.press('Enter')
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(3)
            modal.locator('[data-blueprint-cancel]').click()
            assert save()['document'] == edited['document']
            records.append({'case': 'keyboard-enter-space-node-choice-focus-restoration-and-shift-enter-existing-input-connection'})

            # Typed value wires: Get property -> Compare state -> Check state's
            # Test, then Sequence -> Change sprite, all built by dragging real cables.
            modal = open_editor()
            modal.locator('[data-blueprint-event="enter:closed"]').click()
            modal.locator('[data-blueprint-add]').click()
            prop = choose(modal, 'property')
            expect(modal.locator(f'[data-blueprint-node="{prop}"] [data-blueprint-param=property]')).to_have_value('previous')
            modal.locator('[data-blueprint-fit]').click()
            drag(modal, modal.locator(f'[data-blueprint-node="{prop}"] [data-blueprint-data-output=value]'))
            picker = modal.locator('[data-blueprint-node-picker]')
            expect(picker.locator('[data-blueprint-pick-type]')).to_have_count(1)
            compare = choose(modal, 'compare')
            modal.locator(f'[data-blueprint-node="{compare}"] [data-blueprint-param=state]').select_option('locked')
            drag(modal, modal.locator('[data-blueprint-state-port=closed]'))
            check = choose(modal, 'condition')
            modal.locator('[data-blueprint-fit]').click()
            test_input = modal.locator(f'[data-blueprint-node="{check}"] [data-blueprint-data-input=test]')
            drag(modal, modal.locator(f'[data-blueprint-node="{compare}"] [data-blueprint-data-output=result]'), center(test_input))
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(3)
            expect(modal.locator(f'[data-blueprint-node="{check}"] [data-blueprint-param=state]')).to_be_disabled()
            drag(modal, modal.locator(f'[data-blueprint-node="{check}"] [data-blueprint-output=true]'))
            sequence = choose(modal, 'sequence')
            modal.locator('[data-blueprint-fit]').click()
            drag(modal, modal.locator(f'[data-blueprint-node="{sequence}"] [data-blueprint-output=then1]'))
            sprite = choose(modal, 'sprite')
            expect(modal.locator(f'[data-blueprint-node="{sprite}"] [data-blueprint-param=appearance]')).to_have_value('asset')
            modal.locator('[data-blueprint-fit]').click()
            # A value wire cannot reach an execution Input.
            drag(modal, modal.locator(f'[data-blueprint-node="{compare}"] [data-blueprint-data-output=result]'),
                 center(modal.locator(f'[data-blueprint-node="{sequence}"] [data-blueprint-input]')))
            expect(modal.locator('[role=alert]')).to_be_visible()
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(5)
            modal.locator('[data-blueprint-previous]').select_option('locked')
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator('[data-blueprint-trace-value]')).to_have_count(2)
            assert modal.locator('[data-blueprint-trace-node]').evaluate_all(
                'nodes => nodes.map(node => node.dataset.blueprintTraceNode)') == [sprite]
            page.screenshot(path=str(output / 'typed-value-wires.png'))
            modal.locator('[data-blueprint-save]').click()
            typed = save()
            graph = typed['document']['doors'][0]['blueprint']['graphs']['enter:closed']
            kinds = sorted((edge['kind'], edge.get('input')) for edge in graph['edges'])
            assert kinds == [('data', 'test'), ('data', 'value'), ('execution', None), ('execution', None), ('execution', None)], graph
            types = {node['id']: node['type'] for node in graph['nodes']}
            assert [types[key] for key in (prop, compare, check, sequence, sprite)] == ['property', 'compare', 'condition', 'sequence', 'sprite']
            assert typed['document']['doors'][0]['blueprint']['graphs']['enter:open'] == edited['document']['doors'][0]['blueprint']['graphs']['enter:open']
            edited = typed
            records.append({'case': 'typed-value-wires-sequence-and-change-sprite-save-and-simulate-previous-state'})

            # Multi-selection, clipboard, group moves, minimap and fuzzy search.
            modal = open_editor()
            modal.locator('[data-blueprint-event="enter:closed"]').click()
            canvas = modal.locator('[data-blueprint-canvas]')
            cards = modal.locator('.smart-object__nodes > [data-blueprint-node]')
            selected = modal.locator('.smart-object__nodes > .is-selected')
            expect(cards).to_have_count(6)
            canvas.focus()
            page.keyboard.press('Control+a')
            expect(selected).to_have_count(6)
            modal.locator(f'[data-blueprint-drag="{prop}"]').click()
            expect(selected).to_have_count(1)
            modal.locator(f'[data-blueprint-drag="{compare}"]').click(modifiers=['Shift'])
            expect(selected).to_have_count(2)
            edges_before = modal.locator('[data-blueprint-edge]').count()
            page.keyboard.press('Control+c')
            page.mouse.move(*blank_point(modal).values())
            page.keyboard.press('Control+v')
            expect(cards).to_have_count(8)
            expect(selected).to_have_count(2)
            expect(modal.locator('[data-blueprint-edge].is-data')).to_have_count(3)
            assert modal.locator('[data-blueprint-edge]').count() == edges_before + 1
            pasted = selected.evaluate_all('cards => cards.map(card => card.dataset.blueprintNode)')
            assert not {prop, compare} & set(pasted), pasted
            before = selected.evaluate_all('cards => cards.map(card => [card.offsetLeft, card.offsetTop])')
            heading = modal.locator(f'[data-blueprint-drag="{pasted[0]}"]')
            box = heading.bounding_box()
            page.mouse.move(box['x'] + box['width'] * .3, box['y'] + box['height'] / 2)
            page.mouse.down()
            page.mouse.move(box['x'] + box['width'] * .3 + 50, box['y'] + box['height'] / 2 + 30, steps=4)
            page.mouse.up()
            after = selected.evaluate_all('cards => cards.map(card => [card.offsetLeft, card.offsetTop])')
            moves = {(a[0] - b[0], a[1] - b[1]) for a, b in zip(after, before)}
            assert len(moves) == 1 and moves != {(0, 0)}, (before, after)
            canvas.focus()
            page.keyboard.press('Delete')
            expect(cards).to_have_count(6)
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(edges_before)
            modal.locator(f'[data-blueprint-drag="{sequence}"]').click()
            page.keyboard.press('Control+d')
            expect(cards).to_have_count(7)
            page.keyboard.press('Control+z')
            expect(cards).to_have_count(6)
            # Shift+drag over empty space draws a selection rectangle.
            bounds = canvas.bounding_box()
            page.keyboard.down('Shift')
            page.mouse.move(bounds['x'] + 8, bounds['y'] + 40)
            page.mouse.down()
            page.mouse.move(bounds['x'] + bounds['width'] * .6, bounds['y'] + bounds['height'] * .6, steps=5)
            expect(modal.locator('[data-blueprint-marquee]')).to_be_visible()
            page.mouse.up()
            page.keyboard.up('Shift')
            expect(modal.locator('[data-blueprint-marquee]')).to_be_hidden()
            assert selected.count() >= 1
            minimap = modal.locator('[data-blueprint-minimap]')
            expect(minimap).to_be_visible()
            expect(minimap.locator('rect')).to_have_count(7)
            plane_before = modal.locator('.smart-object__plane').bounding_box()
            minimap_box = minimap.bounding_box()
            page.mouse.click(minimap_box['x'] + minimap_box['width'] * .9, minimap_box['y'] + minimap_box['height'] * .9)
            assert modal.locator('.smart-object__plane').bounding_box() != plane_before
            modal.locator('[data-blueprint-add]').click()
            search = modal.locator('[data-blueprint-picker-search]')
            search.fill('pls')
            first = modal.locator('[data-blueprint-node-picker] [data-blueprint-pick-type]:visible').first
            expect(first).to_have_attribute('data-blueprint-pick-type', 'sound')
            search.press('Enter')
            expect(modal.locator('[data-blueprint-type=sound]')).to_have_count(1)
            # Barrier modes follow the channel; Control sound shows volume only to change it.
            modal.locator('[data-blueprint-add]').click()
            modal.locator('[data-blueprint-node-picker] [data-blueprint-pick-type=barrier]').click()
            barrier = modal.locator('[data-blueprint-type=barrier]')
            expect(barrier.locator('[data-blueprint-param=mode] option')).to_have_count(2)
            barrier.locator('[data-blueprint-param=channel]').select_option('sound')
            expect(modal.locator('[data-blueprint-type=barrier] [data-blueprint-param=mode] option')).to_have_count(3)
            modal.locator('[data-blueprint-add]').click()
            modal.locator('[data-blueprint-node-picker] [data-blueprint-pick-type=soundControl]').click()
            control = modal.locator('[data-blueprint-type=soundControl]')
            expect(control.locator('[data-blueprint-param=volume]')).to_have_count(0)
            control.locator('[data-blueprint-param=action]').select_option('volume')
            expect(modal.locator('[data-blueprint-type=soundControl] [data-blueprint-param=volume]')).to_have_count(1)
            modal.locator('[data-blueprint-add]').click()
            modal.locator('[data-blueprint-node-picker] [data-blueprint-pick-type=state]').click()
            expect(modal.locator('[data-blueprint-type=state] [data-blueprint-param=players]')).to_have_value('false')
            modal.locator('[data-blueprint-cancel]').click()
            assert save()['document'] == edited['document']
            records.append({'case': 'multi-selection-clipboard-group-move-box-select-minimap-and-fuzzy-search'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                page.set_viewport_size({'width': 390, 'height': 844})
                page.goto(builder + '?project=' + edited['id'])
                wait_ready(page)
                modal = open_editor()
                drag(modal, modal.locator('[data-blueprint-state-port=locked]'),
                     touch_input=True)
                picker = modal.locator('[data-blueprint-node-picker]')
                expect(picker).to_be_visible()
                bounds = picker.bounding_box()
                assert bounds['x'] >= 0 and bounds['x'] + bounds['width'] <= 390, bounds
                assert bounds['y'] >= 0 and bounds['y'] + bounds['height'] <= 844, bounds
                page.screenshot(path=str(output / f'touch-drag-node-picker-{locale}.png'))
                added = choose(modal, 'condition')
                expect(modal.locator(f'[data-blueprint-node="{added}"]')).to_have_attribute('data-blueprint-type', 'condition')
                expect(modal.locator('[data-blueprint-edge]')).to_have_count(1)
                metrics = modal.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], metrics
                modal.locator('[data-blueprint-cancel]').click()
                assert save()['document'] == edited['document']
                records.append({'case': 'real-touch-drag-release-node-picker-creation-and-cancel-at-mobile-width',
                                'locale': locale, 'metrics': metrics})
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
