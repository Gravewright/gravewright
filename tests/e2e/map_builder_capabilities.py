"""Exercise authored groups, native actions and filtered event context end to end.

Only this scenario's disposable campaign, synthetic actors, artwork and server
are used. Blueprint graphs and filter drafts are authored through real controls.
"""
from __future__ import annotations

import json

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

        def wait_game(target=None):
            target = target or page
            target.wait_for_url(f'{base}/game/{campaign}')
            target.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(target.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def select_source(identifier, kind):
            builder_tool(page, 'select'); builder_workspace(page)
            target = page.locator(f'[data-builder-{kind}] [data-object-id="{identifier}"]')
            box = target.bounding_box()
            page.mouse.click(box['x'] + box['width'] * .2, box['y'] + box['height'] * .2)
            builder_sidebar(page, 'selection')

        def open_editor(identifier, kind='decorations'):
            select_source(identifier, kind)
            page.locator('[data-builder-edit-behavior]').click()
            modal = page.locator('[data-smart-object-modal]')
            expect(modal).to_be_visible()
            return modal

        def card(modal, identifier):
            return modal.locator(f'[data-blueprint-node="{identifier}"]')

        def change(control, value):
            if control.evaluate('element=>element.tagName') == 'SELECT':
                control.select_option(str(value).lower() if isinstance(value, bool) else str(value))
            else:
                control.fill(str(value)); control.dispatch_event('change')

        def parameter(modal, identifier, name, value):
            change(card(modal, identifier).locator(f'[data-blueprint-param="{name}"]'), value)

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
            modal.locator('[data-blueprint-fit]').click(); source.click(); target.click()

        def wire(modal, source, target, port='next'):
            connect(modal, card(modal, source).locator(f'[data-blueprint-output="{port}"]'), card(modal, target).locator('[data-blueprint-input]'))

        def data_wire(modal, source, target, output_port, input_port='target'):
            connect(modal, card(modal, source).locator(f'[data-blueprint-data-output="{output_port}"]'),
                    card(modal, target).locator(f'[data-blueprint-data-input="{input_port}"]'))

        def group(modal, kind, identifiers, name):
            identifier = add_node(modal, 'elementGroup', name=name)
            if kind != 'element':
                parameter(modal, identifier, 'memberType', kind)
            for member in identifiers:
                if not card(modal, identifier).locator(f'[data-blueprint-member="{member}"]').count():
                    card(modal, identifier).locator('[data-blueprint-member-choice]').select_option(member)
                    card(modal, identifier).locator('[data-blueprint-member-add]').click()
            for member in card(modal, identifier).locator('[data-blueprint-member]').evaluate_all('rows=>rows.map(row=>row.dataset.blueprintMember)'):
                if member not in identifiers:
                    card(modal, identifier).locator(f'[data-blueprint-member-remove="{member}"]').click()
            return identifier

        def begin(modal, state, identifier):
            connect(modal, modal.locator(f'[data-blueprint-state-port="{state}"]'), card(modal, identifier).locator('[data-blueprint-input]'))

        try:
            page.goto(f'/game/{campaign}'); wait_game()
            actors = []
            for name in ('Synthetic keeper with a deliberately long authored name 雪', 'Synthetic excluded observer'):
                actor = page.evaluate("name=>gravewrightRealtime.resourceCommand('actors','actor.create',{name})", name)
                page.evaluate("id=>gravewrightRealtime.resourceCommand('actors','actor.permissions',{id,permissions:{default:'owner'}})", actor['id'])
                actors.append(actor['id'])
            page.goto(builder); wait_ready(page)
            set_name(page, 'Synthetic groups and filtered context')
            prop_asset = upload_asset(page, 'decoration', 'Synthetic movable props.png', harness.artwork('#61904b'))['id']
            lever_asset = upload_asset(page, 'decoration', 'Synthetic group lever.png', harness.artwork('#bb7838'))['id']
            builder_tool(page, 'door'); review.stroke((20, 8), (22, 8))
            builder_tool(page, 'light'); review.stroke((8, 15), (8, 15)); review.stroke((10, 15), (10, 15))
            for x in (14, 20):
                builder_tool(page, 'decoration'); page.locator('[data-builder-brush-material]').select_option(prop_asset)
                review.stroke((x, 14), (x + 2, 16))
            for x in (10, 16):
                builder_tool(page, 'decoration'); page.locator('[data-builder-brush-material]').select_option(lever_asset)
                review.stroke((x, 20), (x + 2, 22))
                builder_sidebar(page, 'selection'); page.locator('[data-builder-property=behavior]').select_option('lever'); close_panel(page)
            builder_tool(page, 'region'); review.stroke((8, 8), (12, 12))
            builder_sidebar(page, 'selection')
            filters = page.locator('[data-builder-region-filters]')
            filters.locator('summary').click()
            expect(filters.locator('[data-builder-region-filter=actorIds] option')).to_have_count(2)
            filters.locator('[data-builder-region-filter=actorIds]').select_option(actors[0])
            filters = page.locator('[data-builder-region-filters]')
            if not filters.evaluate('element=>element.open'): filters.locator('summary').click()
            filters.locator('[data-builder-region-filter=dispositions]').select_option('friendly')
            filters = page.locator('[data-builder-region-filters]')
            if not filters.evaluate('element=>element.open'): filters.locator('summary').click()
            filters.locator('[data-builder-region-filter=visibility]').select_option('visible')
            initial = review.save()
            region, = initial['document']['regions']; door, = initial['document']['doors']
            lights = [row['id'] for row in initial['document']['lights']]
            props = [row['id'] for row in initial['document']['decorations'] if not row.get('lever')]
            main, reset = [row for row in initial['document']['decorations'] if row.get('lever')]
            assert region['filters'] == {'actorIds': [actors[0]], 'tokenIds': [], 'dispositions': ['friendly'], 'visibility': 'visible'}
            records.append({'case': 'real-builder-authors-campaign-actor-disposition-and-visibility-filters-before-generation'})

            modal = open_editor(region['id'], 'regions')
            modal.locator('[data-blueprint-state-port=occupied]').click()
            context_nodes, stores = {}, []
            for prop, name, value_type in (('userName', 'Instigator', 'text'), ('actorId', 'ActorSeen', 'text'), ('count', 'PresenceCount', 'number')):
                context_nodes[prop] = add_node(modal, 'eventContext', property=prop)
                store = add_node(modal, 'setVariable', scope='scene', valueType=value_type, name=name)
                data_wire(modal, context_nodes[prop], store, 'value', 'value'); stores.append(store)
            for prop in ('tokenId', 'hasToken'):
                context_nodes[prop] = add_node(modal, 'eventContext', property=prop)
            light_group = group(modal, 'light', lights, 'Lâmpadas do salão 雪')
            on = add_node(modal, 'light', targetId=lights[0], enabled=True)
            data_wire(modal, light_group, on, 'targets')
            reference = add_node(modal, 'reference', targetId=door['id'])
            opened = add_node(modal, 'state'); data_wire(modal, reference, opened, 'door'); parameter(modal, opened, 'targetState', 'open')
            begin(modal, 'occupied', stores[0])
            for before, after in zip(stores + [on], stores[1:] + [on, opened]): wire(modal, before, after)
            modal.locator('[data-blueprint-simulate]').click()
            assert review.project(initial['id'])['document'] == initial['document']
            modal.locator('[data-blueprint-simulation-context] > summary').click()
            change(modal.locator('[data-blueprint-context-property=userName]'), 'Local preview only')
            change(modal.locator('[data-blueprint-context-property=count]'), 7)
            expect(modal.locator('[data-blueprint-context-property=hasToken]')).to_have_value('false')
            change(modal.locator('[data-blueprint-context-property=tokenId]'), actors[0])
            expect(modal.locator('[data-blueprint-context-property=hasToken]')).to_have_value('true')
            change(modal.locator('[data-blueprint-context-property=hasToken]'), False)
            change(modal.locator('[data-blueprint-context-property=tokenId]'), actors[1])
            expect(modal.locator('[data-blueprint-context-property=hasToken]')).to_have_value('false')
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator('[data-blueprint-trace]')).to_contain_text('Local preview only')
            assert review.project(initial['id'])['document'] == initial['document']
            modal.locator('[data-blueprint-state-port=empty]').click()
            off_group = group(modal, 'light', lights, 'Lâmpadas do salão 雪')
            off = add_node(modal, 'light', targetId=lights[0], enabled=False); data_wire(modal, off_group, off, 'targets')
            target = add_node(modal, 'reference', targetId=door['id'])
            closed = add_node(modal, 'state'); data_wire(modal, target, closed, 'door'); parameter(modal, closed, 'targetState', 'closed')
            begin(modal, 'empty', off); wire(modal, off, closed)
            modal.locator('[data-blueprint-save]').click(); review.save()
            records.append({'case': 'real-editor-authors-event-context-typed-writes-group-lights-and-door-actions-with-local-only-preview'})

            modal = open_editor(main['id']); modal.locator('[data-blueprint-state-port=on]').click()
            props_group = group(modal, 'element', props, 'Objetos móveis com nome longo 雪')
            move = add_node(modal, 'move', dx=1, dy=0); data_wire(modal, props_group, move, 'targets')
            rotate = add_node(modal, 'rotate', degrees=90); data_wire(modal, props_group, rotate, 'targets')
            doors_group = group(modal, 'element', [door['id']], 'Door interactions')
            disable = add_node(modal, 'setInteraction', enabled=False); data_wire(modal, doors_group, disable, 'targets')
            plate = add_node(modal, 'reference', targetId=region['id'])
            disable_region = add_node(modal, 'setRegion', enabled=False); data_wire(modal, plate, disable_region, 'door')
            begin(modal, 'on', move)
            for before, after in ((move, rotate), (rotate, disable), (disable, disable_region)): wire(modal, before, after)
            modal.locator('[data-blueprint-save]').click(); review.save()
            modal = open_editor(reset['id']); modal.locator('[data-blueprint-state-port=on]').click()
            doors_reset = group(modal, 'element', [door['id']], 'Door interactions')
            enable = add_node(modal, 'setInteraction', enabled=True); data_wire(modal, doors_reset, enable, 'targets')
            plate_reset = add_node(modal, 'reference', targetId=region['id'])
            enable_region = add_node(modal, 'setRegion', enabled=True); data_wire(modal, plate_reset, enable_region, 'door')
            begin(modal, 'on', enable); wire(modal, enable, enable_region)
            modal.locator('[data-blueprint-save]').click()
            authored = review.save()
            records.append({'case': 'real-editor-authors-ordered-group-move-rotate-player-interaction-and-presence-controls'})

            modal = open_editor(main['id']); modal.locator('[data-blueprint-state-port=on]').click()
            card(modal, props_group).locator(f'[data-blueprint-member-up="{props[1]}"]').click()
            expect(card(modal, props_group).locator('[data-blueprint-member]').first).to_have_attribute('data-blueprint-member', props[1])
            modal.locator('[data-blueprint-undo]').click()
            expect(card(modal, props_group).locator('[data-blueprint-member]').first).to_have_attribute('data-blueprint-member', props[0])
            parameter(modal, doors_group, 'memberType', 'light')
            expect(card(modal, doors_group).locator('[data-blueprint-data-output=targets]')).to_have_attribute('data-port-type', 'lightset')
            expect(modal.locator(f'[data-blueprint-edge="{doors_group}:targets:{disable}:target"]')).to_have_count(0)
            modal.locator('[data-blueprint-undo]').click()
            expect(card(modal, doors_group).locator('[data-blueprint-data-output=targets]')).to_have_attribute('data-port-type', 'elementset')
            expect(modal.locator(f'[data-blueprint-edge="{doors_group}:targets:{disable}:target"]')).to_have_count(1)
            modal.locator('[data-blueprint-cancel]').click()
            assert review.save()['document'] == authored['document']
            records.append({'case': 'group-order-and-type-edits-have-undoable-typed-sockets-and-cancel-preserves-source'})

            select_source(door['id'], 'doors')
            expect(page.locator('[data-builder-property=interactionEnabled]')).to_be_checked()
            page.locator('[data-builder-property=interactionEnabled]').uncheck()
            assert review.save()['document']['doors'][0]['interactionEnabled'] is False
            page.locator('[data-builder-undo]').click()
            assert review.save()['document'] == authored['document']
            records.append({'case': 'builder-door-player-interaction-setting-is-optional-and-undo-restores-legacy-omission'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    page.goto(builder + '?project=' + authored['id']); wait_ready(page)
                    modal = open_editor(main['id']); modal.locator('[data-blueprint-state-port=on]').click()
                    modal.locator('[data-blueprint-fit]').click()
                    blueprint_metrics = modal.evaluate(MEASURE)
                    assert not blueprint_metrics['tiny'] and not blueprint_metrics['overflow'], blueprint_metrics
                    page.screenshot(path=str(output / f'capabilities-editor-{locale}-{width}.png'))
                    for _ in range(8):
                        page.keyboard.press('Tab')
                        assert modal.evaluate('element=>element.closest("[role=dialog]").contains(document.activeElement)')
                    page.keyboard.press('Escape'); expect(modal).to_have_count(0)
                    records.append({'case': 'localized-responsive-group-actions-and-keyboard-focus', 'locale': locale, 'width': width,
                                    'blueprintMetrics': blueprint_metrics})

            change_locale(page, 'en', campaign); page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(builder + '?project=' + authored['id']); wait_ready(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            wait_game()
            project = review.project(authored['id']); scene = project['sceneId']

            def command(area, action, data, target=None):
                return (target or page).evaluate("""a=>gravewrightRealtime.mapCommand('objects',{
                  mapId:a.scene,area:a.area,action:a.action,data:a.data})""", {'scene': scene, 'area': area, 'action': action, 'data': data})

            def state(target=None):
                response = (target or page).request.get(f'/api/maps/{scene}/state'); assert response.ok, response.text()
                return response.json()

            def automation():
                response = page.request.get(f'/api/maps/{scene}/automation'); assert response.ok, response.text()
                return response.json()

            def token_rows(target=None):
                response = (target or page).request.get(f'/api/containers/{campaign}/maps/{scene}/tokens'); assert response.ok, response.text()
                return response.json()['tokens']

            def token_command(action, data, target=None):
                return (target or page).evaluate("a=>gravewrightRealtime.resourceCommand('tokens',a.action,{mapId:a.scene,...a.data})",
                                                 {'scene': scene, 'action': action, 'data': data})

            command('lighting', 'update', {'mode': 'none', 'darkness': 0, 'lights_out': False})
            page.evaluate("a=>gravewrightRealtime.mapCommand('update',{mapId:a.scene,version:a.version,settings:{visibility:'players'}})",
                          {'scene': scene, 'version': project['sceneVersion']})
            page.evaluate("scene=>gravewrightRealtime.mapCommand('activate',{mapId:scene})", scene)
            native = state(); native_region, = native['zones']; native_door, = [row for row in native['walls'] if row['kind'] == 'door']
            native_main = next(row for row in native['images'] if row.get('blueprint', {}).get('graphs', {}).get('enter:on', {}).get('nodes')
                               and any(node['id'] == move for node in row['blueprint']['graphs']['enter:on']['nodes']))
            native_reset = next(row for row in native['images'] if row.get('lever') and row['id'] != native_main['id'])
            moved_ids = next(node['targetIds'] for node in native_main['blueprint']['graphs']['enter:on']['nodes'] if node['id'] == props_group)
            before_props = {row['id']: row for row in native['images'] if row['id'] in moved_ids}
            tokens = []
            for actor, x in ((actors[0], 4), (actors[0], 5), (actors[1], 6)):
                created = token_command('place', {'actorId': actor, 'gridX': x, 'gridY': 5})
                tokens.append(created['createdIds'][0])
            for identifier in tokens[:2]:
                current = next(row for row in token_rows() if row['id'] == identifier)
                token_command('configure', {'tokenIds': [identifier], 'expectedVersion': current['version'], 'values': {'disposition': 'friendly'}})
            guest = browser.new_context(base_url=base, viewport={'width': 1200, 'height': 800}); guests.append(guest)
            guest.add_cookies([{**seed['sessions']['player'], 'url': base}])
            player = guest.new_page(); observe(player); player.goto(f'/game/{campaign}'); wait_game(player)

            def move_token(identifier, x, y=9):
                current = next(row for row in token_rows(player) if row['id'] == identifier)
                return token_command('move', {'id': identifier, 'expectedVersion': current['version'], 'gridX': x, 'gridY': y}, player)

            def presence():
                return next(row for row in state()['zones'] if row['id'] == native_region['id'])

            def press(identifier):
                control = player.locator(f'[data-smart-image-id="{identifier}"][data-smart-image-action=interact]')
                control.focus(); control.press('Enter'); expect(control).to_have_attribute('aria-pressed', 'true')

            move_token(tokens[2], 9)
            assert presence()['region']['count'] == 0
            move_token(tokens[0], 9)
            assert presence()['region']['count'] == 1
            assert all(row['enabled'] for row in state()['lights'])
            variables = automation()['variables']['scene']
            assert variables['Instigator'] == {'type': 'text', 'value': 'Player'}
            assert variables['ActorSeen'] == {'type': 'text', 'value': actors[0]}
            assert variables['PresenceCount'] == {'type': 'number', 'value': 1}
            assert state(player)['zones'] == []
            assert 'automationVariables' not in json.dumps(state(player))
            assert player.request.get(f'/api/maps/{scene}/automation').status == 404
            records.append({'case': 'real-player-presence-filters-actor-and-authentic-context-drives-group-lights-with-private-memory'})

            def door_editor():
                page.locator('.game-menubar__layer').nth(5).click()
                page.locator('[data-dock-tool=select]:visible').first.click()
                current = next(row for row in state()['walls'] if row['id'] == native_door['id'])
                point = page.evaluate('''wall=>{
                  const box=document.querySelector('.game-table__scene-frame').getBoundingClientRect(),view=gravewrightMaps.board.viewport();
                  return [box.x+view.x+(wall.x1+(wall.x2-wall.x1)*.15)*view.scale,
                    box.y+view.y+(wall.y1+(wall.y2-wall.y1)*.15)*view.scale];
                }''', current)
                page.mouse.dblclick(*point)
                editor = page.locator('.wall-editor'); expect(editor).to_be_visible()
                return editor

            editor = door_editor()
            expect(editor.locator('[name=interactionEnabled]')).to_be_checked()
            editor.locator('[name=interactionEnabled]').uncheck()
            editor.locator('[type=submit]').click(); expect(editor).to_have_count(0)
            editor = door_editor()
            expect(editor.locator('[name=interactionEnabled]')).not_to_be_checked()
            metrics = editor.evaluate(MEASURE); assert not metrics['tiny'] and not metrics['overflow'], metrics
            page.screenshot(path=str(output / 'capabilities-native-door-interaction.png'))
            editor.locator('[aria-label="Close editor"]').click()
            expect(player.locator('.door-controls [role=button]').first).to_have_attribute('aria-disabled', 'true')
            player.locator('.door-controls [role=button]').first.press('Enter')
            assert next(row for row in state()['walls'] if row['id'] == native_door['id'])['door_state'] == 'open'
            page.locator('.door-controls [role=button]').first.press('Enter')
            page.wait_for_function('''async a=>{
              const state=await(await fetch(`/api/maps/${a.scene}/state`)).json();
              return state.walls.find(row=>row.id===a.door).door_state==='closed';
            }''', arg={'scene': scene, 'door': native_door['id']})
            page.locator('.door-controls [role=button]').first.press('Enter')
            page.wait_for_function('''async a=>{
              const state=await(await fetch(`/api/maps/${a.scene}/state`)).json();
              return state.walls.find(row=>row.id===a.door).door_state==='open';
            }''', arg={'scene': scene, 'door': native_door['id']})
            records.append({'case': 'native-door-window-persists-player-interaction-checkbox-while-gm-can-still-operate', 'metrics': metrics})

            press(native_main['id'])
            current = state()
            for identifier, previous in before_props.items():
                moved = next(row for row in current['images'] if row['id'] == identifier)
                assert moved['x'] == previous['x'] + authored['document']['cellSize'] and moved['y'] == previous['y'], (previous, moved)
                assert moved['rotation'] == (previous['rotation'] + 90) % 360
            assert next(row for row in current['walls'] if row['id'] == native_door['id'])['interactionEnabled'] is False
            assert presence()['enabled'] is False and presence()['region']['count'] == 0
            blocked = player.evaluate("""a=>gravewrightRealtime.mapCommand('objects',{mapId:a.scene,area:'walls',action:'door',
              data:{wall_id:a.door,door_state:'closed'}}).then(result=>({accepted:true}),error=>({accepted:false,message:error.message}))""",
                                      {'scene': scene, 'door': native_door['id']})
            assert blocked['accepted'] is False, blocked
            command('walls', 'door', {'wall_id': native_door['id'], 'door_state': 'closed'})
            records.append({'case': 'real-player-group-moves-and-rotates-props-disables-presence-and-server-blocks-direct-door-interaction'})

            page.goto(builder + '?project=' + authored['id']); wait_ready(page); builder_sidebar(page, 'review')
            with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                page.locator('[data-builder-review-update]').click()
            assert updated.value.ok, updated.value.text()
            wait_game()
            current = state()
            for identifier, previous in before_props.items():
                restored = next(row for row in current['images'] if row['id'] == identifier)
                assert (restored['x'], restored['y'], restored['rotation']) == (previous['x'], previous['y'], previous['rotation'])
            assert presence()['enabled'] is False
            assert next(row for row in current['walls'] if row['id'] == native_door['id'])['interactionEnabled'] is False
            records.append({'case': 'explicit-source-update-restores-authored-geometry-and-preserves-runtime-interaction-and-presence-flags'})
            before_runs = len(automation()['runs'])
            press(native_reset['id'])
            assert presence()['enabled'] is True and presence()['region']['count'] == 1
            assert next(row for row in state()['walls'] if row['id'] == native_door['id'])['interactionEnabled'] is True
            assert len(automation()['runs']) == before_runs + 1
            move_token(tokens[0], 5)
            assert presence()['region']['count'] == 0 and all(not row['enabled'] for row in state()['lights'])
            records.append({'case': 'authored-reset-reenables-interaction-and-quiet-baseline-then-normal-exit-runs-again'})

        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            (output / 'progress.json').write_text(json.dumps({'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs},
                                                            indent=2, ensure_ascii=False), encoding='utf-8')
            raise
        finally:
            for guest in guests: guest.close()
            context.close(); browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Synthetic actors, generated solid-color PNGs and isolated campaign state only.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
