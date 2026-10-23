"""Author and execute native clock actions with isolated MapBuilder campaigns."""
from __future__ import annotations

from copy import deepcopy
import json
import re
import sqlite3

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_playtest import persistent_snapshot
from map_builder_reference import close_panel, set_name, upload_asset, wait_ready


CLOCK_NAME = 'Synthetic expedition progress at the abandoned northern observatory with a long authored name'
PRIVATE_NAME = 'SYNTHETIC_PRIVATE_CLOCK: The observatory keeper prepares an ambush'


def snapshot(output):
    result = persistent_snapshot(output)
    path = output / 'fixture' / 'review.sqlite3'
    with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as database:
        tables = [row[0] for row in database.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name") if row[0].startswith('gravewright_table_')]
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            result['rows'][table] = sorted(database.execute(f'SELECT * FROM {quoted}').fetchall(), key=repr)
    return result


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    records, errors, dialogs, failed, contexts = [], [], [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        pages = {}

        def client(name, role):
            context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
            contexts.append(context)
            context.add_cookies([{**seed['sessions'][role], 'url': base}])
            context.add_init_script('''window.__clockWire=[];addEventListener('gravewright:api-event',event=>__clockWire.push(event.detail));
            window.__clockStates=[];addEventListener('gravewright:resources',event=>{
              if(event.detail.module==='clocks') __clockStates.push(event.detail.state);
            });''')
            page = context.new_page()
            pages[name] = page
            page.on('pageerror', lambda error: errors.append(error.stack or str(error)))
            page.on('requestfailed', lambda request: failed.append({'url': request.url, 'error': request.failure}))
            page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
            return page

        page = client('gm', 'gm')
        review = BuilderReview(page, campaign)

        def game(target):
            target.wait_for_url(f'{base}/game/{campaign}')
            target.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(target.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def clocks(target=page):
            return target.evaluate('''async campaign=>gravewright.forTable(campaign).clocks.state({
              sceneId:window.gravewrightMaps?.current?.id||null})''', campaign)['clocks']

        def clock_value(identifier, target=page):
            return next(row['value'] for row in clocks(target) if row['id'] == identifier)

        def hud_progress(target, identifier, value):
            expect(target.locator(f'[data-clock-hud] [data-clock-id="{identifier}"] [data-clock-value]')).to_have_text(
                re.compile(rf'^{value}\s*/\s*8$'))

        def open_editor(owner):
            builder_tool(page, 'select')
            builder_workspace(page)
            shape = page.locator(f'[data-builder-decorations] [data-object-id="{owner}"]')
            box = shape.bounding_box()
            page.mouse.click(box['x'] + box['width'] * .25, box['y'] + box['height'] * .25)
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-edit-behavior]').click()
            editor = page.locator('[data-smart-object-modal]')
            expect(editor).to_be_visible()
            editor.locator('[data-blueprint-event=interact]').click()
            return editor

        def card(editor, identifier):
            return editor.locator(f'[data-blueprint-node="{identifier}"]')

        def parameter(editor, identifier, key, value):
            control = card(editor, identifier).locator(f'[data-blueprint-param="{key}"]')
            if control.evaluate('element=>element.tagName') == 'SELECT':
                control.select_option(str(value).lower() if isinstance(value, bool) else str(value))
            else:
                control.fill(str(value))
                control.dispatch_event('change')

        def add(editor, kind, **params):
            before = set(editor.locator('[data-blueprint-node]').evaluate_all('nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            editor.locator('[data-blueprint-add]').click()
            editor.locator(f'[data-blueprint-pick-type="{kind}"]').click()
            after = set(editor.locator('[data-blueprint-node]').evaluate_all('nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            identifier, = after - before
            for key, value in params.items():
                parameter(editor, identifier, key, value)
            return identifier

        def wire(editor, source, target):
            editor.locator('[data-blueprint-fit]').click()
            source.click()
            target.click()

        def execution(editor, source, target):
            wire(editor, card(editor, source).locator('[data-blueprint-output=next]'),
                 card(editor, target).locator('[data-blueprint-input]'))

        try:
            page.goto(f'/game/{campaign}')
            game(page)
            initial_clocks = page.evaluate('''async ([campaign,name,privateName])=>{
              const api=gravewright.forTable(campaign);const sceneId=gravewrightMaps.current.id;
              const create=(name,visibility,value,pinned)=>api.clocks.create({name,visibility,value,pinned,
                segments:8,color:'#c69638',playersCanEdit:false,scopeSceneId:null,sceneId});
              return [await create(name,'players',1,true),await create(privateName,'gm',0,false)];
            }''',
                [campaign, CLOCK_NAME, PRIVATE_NAME])
            public_id, private_id = [result['id'] for result in initial_clocks]
            player = client('player', 'player')
            player.goto(f'/game/{campaign}')
            game(player)
            hud_progress(player, public_id, 1)
            assert PRIVATE_NAME not in json.dumps(clocks(player)) and PRIVATE_NAME not in player.content()

            page.goto(review.builder)
            wait_ready(page)
            set_name(page, 'Synthetic MapBuilder clock controls')
            artwork = upload_asset(page, 'decoration', 'Synthetic clock mechanism.png', harness.artwork('#38779a'))['id']
            builder_tool(page, 'decoration')
            page.locator('[data-builder-brush-material]').select_option(artwork)
            review.stroke((6, 6), (8, 8))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=behavior]').select_option('lever')
            close_panel(page)
            project = review.save()
            document = deepcopy(project['document'])
            document.update(columns=14, rows=12, cellSize=64)
            project = review.store(project['id'], project['version'], project['folderId'], document)
            owner = project['document']['decorations'][0]['id']
            page.goto(review.builder + '?project=' + project['id'])
            wait_ready(page)
            editor = open_editor(owner)
            action = add(editor, 'clockControl', clockId=public_id, action='advance', amount=1)
            expect(card(editor, action).locator('[data-blueprint-param=clockId] option:checked')).to_have_text(CLOCK_NAME)
            value = add(editor, 'getVariable', valueType='number', scope='element', name='ExpeditionAdvanceAmount', default=2)
            private_action = add(editor, 'clockControl', clockId=private_id, action='advance', amount=1)
            continuation = add(editor, 'setVariable', valueType='boolean', scope='element', name='ClockChainFinished', value=True)
            wire(editor, editor.locator('[data-blueprint-instance] [data-blueprint-event-port=interact][data-blueprint-output=next]'),
                 card(editor, action).locator('[data-blueprint-input]'))
            execution(editor, action, private_action)
            execution(editor, private_action, continuation)
            wire(editor, card(editor, value).locator('[data-blueprint-data-output=value]'),
                 card(editor, action).locator('[data-blueprint-data-input=amount]'))
            expect(card(editor, action).locator('[data-blueprint-data-input=amount]')).to_have_attribute('data-port-type', 'number')
            expect(card(editor, action).locator('[data-blueprint-param=amount]')).to_be_disabled()
            expect(editor.locator('[data-blueprint-edge]')).to_have_count(4)
            editor.locator('[data-blueprint-simulate]').click()
            expect(editor.locator('[data-blueprint-trace]')).to_contain_text(CLOCK_NAME)
            assert clock_value(public_id) == 1 and clock_value(private_id) == 0
            expect(editor.locator('[data-blueprint-autosave]')).to_have_attribute('data-state', 'saved')
            editor.locator('[data-blueprint-close]').click()
            expect(editor).to_have_count(0)
            saved = review.save()
            graph = saved['document']['decorations'][0]['blueprint']['graphs']['interact']
            assert any(edge.get('kind') == 'data' and edge.get('input') == 'amount' for edge in graph['edges'])
            records.append({'case': 'native-node-chooser-authors-clock-actions-numeric-amount-and-execution-continuation'})

            page.reload()
            wait_ready(page)
            editor = open_editor(owner)
            expect(card(editor, action).locator('[data-blueprint-param=clockId]')).to_have_value(public_id)
            expect(card(editor, action).locator('[data-blueprint-param=amount]')).to_be_disabled()
            editor.locator('[data-blueprint-close]').click()
            expect(editor).to_have_count(0)
            records.append({'case': 'saved-clock-bindings-and-numeric-connections-survive-reload'})

            before = snapshot(output)
            player.evaluate('window.__clockStates=[]')
            page.locator('[data-builder-test]').click()
            rehearsal = page.locator('[data-playtest]')
            expect(rehearsal).to_be_visible()
            rehearsal.locator('[data-playtest-element]').select_option(owner)
            rehearsal.locator('[data-playtest-event]').select_option('interact')
            with page.expect_response(lambda response: response.request.method == 'POST' and response.url.endswith('/map-builder/test')) as tested:
                rehearsal.locator('[data-playtest-run]').click()
            assert tested.value.ok, tested.value.text()
            prediction = tested.value.json()
            assert prediction['ok'] and prediction['dryRun'], prediction
            changed = {entry['id']: entry for entry in prediction['changes']['clocks']}
            assert changed[public_id]['before']['value'] == 1 and changed[public_id]['after']['value'] == 3, changed
            assert changed[private_id]['before']['value'] == 0 and changed[private_id]['after']['value'] == 1, changed
            expect(rehearsal.locator('[data-playtest-results]')).to_contain_text(CLOCK_NAME)
            assert snapshot(output) == before
            hud_progress(player, public_id, 1)
            page.screenshot(path=str(output / 'clock-rehearsal-rollback-1440.png'))
            page.keyboard.press('Escape')
            expect(rehearsal).to_have_count(0)
            records.append({'case': 'server-rehearsal-predicts-both-clock-changes-and-rolls-back-rows-receipts-media-and-notifications'})

            labels = {'en': 'Control clock', 'pt-BR': 'Controlar relógio', 'es': 'Controlar reloj'}
            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 320):
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    page.goto(review.builder + '?project=' + project['id'])
                    wait_ready(page)
                    editor = open_editor(owner)
                    expect(card(editor, action).locator('[data-blueprint-param=clockId] option:checked')).to_have_text(CLOCK_NAME)
                    expect(card(editor, action)).to_contain_text(labels[locale])
                    editor.locator('[data-blueprint-fit]').click()
                    metrics = editor.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], (locale, width, metrics)
                    page.screenshot(path=str(output / f'clock-node-{locale}-{width}.png'))
                    page.keyboard.press('Escape')
                    expect(editor).to_have_count(0)
                    records.append({'case': f'localized-clock-node-editor-{locale}-{width}'})
            assert snapshot(output) == before
            assert all(clock['value'] == 1 for state in player.evaluate('window.__clockStates')
                       for clock in state.get('clocks', []) if clock['id'] == public_id)

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(review.builder + '?project=' + project['id'])
            wait_ready(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            game(page)
            project = review.project(project['id'])
            scene = project['sceneId']
            page.evaluate('args=>gravewrightRealtime.mapCommand("update",{mapId:args.scene,version:args.version,settings:{visibility:"players"}})',
                          {'scene': scene, 'version': project['sceneVersion']})
            page.evaluate('scene=>gravewrightRealtime.mapCommand("activate",{mapId:scene})', scene)
            player.wait_for_function('scene=>gravewrightMaps.current?.id===scene', arg=scene)
            native = page.request.get(f'/api/maps/{scene}/state').json()
            lever, = [image for image in native['images'] if image.get('lever')]
            control = player.locator(f'[data-smart-image-id="{lever["id"]}"][data-smart-image-action=interact]')
            direct_write = player.evaluate('''async ({campaign,id})=>{
              const api=gravewright.forTable(campaign),state=await api.clocks.state({sceneId:gravewrightMaps.current.id});
              try{await api.clocks.advance({id,version:state.clocks.find(clock=>clock.id===id).version,delta:1});return 'accepted';}
              catch(error){return error.status;}
            }''', {'campaign': campaign, 'id': public_id})
            assert direct_write == 403, direct_write

            def interact(expected, private_expected):
                control.focus()
                control.press('Enter')
                hud_progress(player, public_id, expected)
                hud_progress(page, public_id, expected)
                assert clock_value(private_id) == private_expected
                assert PRIVATE_NAME not in json.dumps(clocks(player)) and PRIVATE_NAME not in player.content()
                public_wire = json.dumps(player.evaluate('window.__clockWire'))
                assert PRIVATE_NAME not in public_wire and private_id not in public_wire

            interact(3, 1)
            native = page.request.get(f'/api/maps/{scene}/state').json()
            live = next(image for image in native['images'] if image['id'] == lever['id'])
            assert live['automationVariables']['ClockChainFinished']['value'] is True, live
            player.screenshot(path=str(output / 'player-map-interaction-clock-hud-1440.png'))
            records.append({'case': 'player-mechanism-executes-gm-bound-public-and-private-clock-actions-without-general-clock-write-access'})

            for operation, amount, expected, private_expected in (('reduce', 1, 2, 2), ('set', 5, 5, 3), ('reset', 5, 0, 4)):
                page.get_by_role('button', name='Walls', exact=True).click()
                page.locator('[data-dock-tool=automation]').click()
                page.locator('[data-automation-network]').click()
                network = page.locator('[data-scene-network]')
                expect(network).to_be_visible()
                network.locator(f'[data-network-open="{lever["id"]}"]').click()
                editor = page.locator('[data-smart-object-modal]')
                expect(editor).to_be_visible()
                editor.locator('[data-blueprint-event=interact]').click()
                parameter(editor, action, 'action', operation)
                parameter(editor, value, 'default', amount)
                expect(card(editor, action).locator('[data-blueprint-param=amount]')).to_be_disabled()
                expect(editor.locator('[data-blueprint-autosave]')).to_have_attribute('data-state', 'saved')
                editor.locator('[data-blueprint-close]').click()
                expect(editor).to_have_count(0)
                expect(network).to_be_visible()
                network.locator('[data-network-close]').click()
                page.locator('[data-automation-close]').click()
                interact(expected, private_expected)
                source = review.project(project['id'])['document']['decorations'][0]['blueprint']['graphs']['interact']
                assert next(node for node in source['nodes'] if node['id'] == action)['action'] == operation
                records.append({'case': f'live-editor-saves-{operation}-back-to-source-and-map-interaction-updates-clock'})
            assert not errors, errors
            assert not dialogs, dialogs
            assert not [request for request in failed if request['error'] != 'net::ERR_ABORTED'], failed
        except Exception:
            (output / 'progress.json').write_text(json.dumps({'cases': records, 'pageErrors': errors,
                'nativeDialogs': dialogs, 'failedRequests': failed}, indent=2), encoding='utf-8')
            for name, target in pages.items():
                target.screenshot(path=str(output / f'failure-{name}.png'), full_page=True)
            raise
        finally:
            for context in contexts:
                context.close()
            browser.close()
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'failedRequests': failed, 'assets': 'Generated solid-color PNG, silent WAV and synthetic authored clock names only.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
