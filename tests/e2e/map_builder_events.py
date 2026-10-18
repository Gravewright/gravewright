"""Author verb-based Smart Object events with isolated campaign state.

The real editor, simulation, generated tabletop and player controls exercise one
interaction graph for both mechanism states and one state-change graph. Artwork,
campaign sessions, media, database and output belong only to this fixture.
"""
from __future__ import annotations

from copy import deepcopy
import re
import time
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_playtest import behavior, chain, node
from map_builder_reference import close_panel, set_name, upload_asset, wait_ready


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    records, errors, dialogs = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))
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
            page.locator(f'[data-builder-decorations] [data-object-id="{identifier}"]').dblclick()
            modal = page.locator('[data-smart-object-modal]')
            expect(modal).to_be_visible()
            return modal

        def card(modal, identifier):
            return modal.locator(f'[data-blueprint-node="{identifier}"]')

        def add_node(modal, kind, **params):
            before = set(modal.locator('[data-blueprint-node]').evaluate_all(
                'nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            modal.locator('[data-blueprint-add]').click()
            modal.locator(f'[data-blueprint-pick-type="{kind}"]').click()
            after = set(modal.locator('[data-blueprint-node]').evaluate_all(
                'nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            identifier, = after - before
            for name, value in params.items():
                control = card(modal, identifier).locator(f'[data-blueprint-param="{name}"]').first
                if control.evaluate('element=>element.tagName') == 'SELECT':
                    control.select_option(str(value).lower() if isinstance(value, bool) else str(value))
                else:
                    control.fill(str(value))
                    control.dispatch_event('change')
            return identifier

        def connect(modal, source, target, port='next'):
            modal.locator('[data-blueprint-fit]').click()
            card(modal, source).locator(f'[data-blueprint-output="{port}"]').click()
            card(modal, target).locator('[data-blueprint-input]').click()

        def start(modal, event, target):
            modal.locator('[data-blueprint-fit]').click()
            modal.locator(f'[data-blueprint-event-port="{event}"]').click()
            card(modal, target).locator('[data-blueprint-input]').click()

        def game(target):
            target.wait_for_url(f'{base}/game/{campaign}')
            target.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(target.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        try:
            page.goto(review.builder)
            wait_ready(page)
            set_name(page, 'Synthetic verb events and legacy state graph compatibility')
            native_asset = upload_asset(page, 'decoration', 'Synthetic normal mechanism.png',
                                        harness.artwork('#b87735'))['id']
            changed_asset = upload_asset(page, 'decoration', 'Synthetic changed mechanism.png',
                                         harness.artwork('#286fbc'))['id']
            builder_tool(page, 'decoration')
            page.locator('[data-builder-brush-material]').select_option(native_asset)
            review.stroke((12, 8), (14, 10))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=behavior]').select_option('lever')
            close_panel(page)
            initial = review.save()
            lever_id = initial['document']['decorations'][0]['id']

            # Opening a fresh object exposes verbs rather than one execution
            # branch for every state. The detached draft still discards cleanly.
            modal = open_editor(lever_id)
            expect(modal.locator('[data-blueprint-event-port="change"]')).to_be_visible()
            expect(modal.locator('[data-blueprint-event-port="interact"]')).to_be_visible()
            expect(modal.locator('[data-blueprint-state-port]')).to_have_count(0)
            modal.locator('[data-blueprint-event="interact"]').click()
            add_node(modal, 'condition', state='on')
            modal.locator('[data-blueprint-cancel]').click()
            assert review.save()['document'] == initial['document']
            records.append({'case': 'fresh-instance-exposes-verb-ports-and-cancel-discards-private-draft'})

            # One interaction graph checks the event's initial state, then
            # selects the opposite native state. Appearance follows onChange.
            modal = open_editor(lever_id)
            modal.locator('[data-blueprint-event="interact"]').click()
            check = add_node(modal, 'condition', state='on')
            turn_off = add_node(modal, 'state', targetState='off')
            turn_on = add_node(modal, 'state', targetState='on')
            start(modal, 'interact', check)
            connect(modal, check, turn_off, 'true')
            connect(modal, check, turn_on, 'false')
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(3)
            modal.locator('[data-blueprint-undo]').click()
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(2)
            modal.locator('[data-blueprint-redo]').click()
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(3)
            modal.locator('[data-blueprint-simulate]').click()
            expect(modal.locator('[data-blueprint-trace]')).to_contain_text('Activated')

            modal.locator('[data-blueprint-event="change"]').click()
            check_changed = add_node(modal, 'condition', state='on')
            show_changed = add_node(modal, 'sprite', appearance='asset', assetId=changed_asset)
            show_native = add_node(modal, 'sprite', appearance='inherit')
            start(modal, 'change', check_changed)
            connect(modal, check_changed, show_changed, 'true')
            connect(modal, check_changed, show_native, 'false')
            modal.locator('[data-blueprint-save]').click()
            authored = review.save()
            blueprint = authored['document']['decorations'][0]['blueprint']
            assert {'interact', 'change'} <= blueprint['graphs'].keys(), blueprint
            assert len(blueprint['graphs']['interact']['edges']) == len(blueprint['graphs']['change']['edges']) == 3
            records.append({'case': 'one-interaction-graph-branches-by-state-and-one-change-graph-selects-appearance-with-undo-redo'})

            # A legacy graph remains distinct and unchanged. A no-op Save or
            # visiting its view does not convert or merge its execution paths.
            document = deepcopy(authored['document'])
            # Node identifiers are scoped to each event graph. Reuse one ID in
            # both views to expose stale graph selection after a port switch.
            changed_graph = document['decorations'][0]['blueprint']['graphs']['change']
            for value in changed_graph['nodes']:
                if value['id'] == check_changed:
                    value['id'] = check
            for edge in changed_graph['edges']:
                for key in ('from', 'to'):
                    if edge[key] == check_changed:
                        edge[key] = check
            legacy_id = str(uuid4())
            legacy_graph = chain('enter:on', [node('legacyMark', 'setVariable', scope='element',
                                                 name='LegacyMark', valueType='boolean', value=True)])
            legacy = {'id': legacy_id, 'layerId': document['layers'][0]['id'],
                      'assetId': native_asset, 'x': 19, 'y': 8, 'width': 2, 'height': 2,
                      'rotation': 0, 'lever': {'state': 'off'},
                      'blueprint': behavior('lever', {'enter:on': legacy_graph})}
            document['decorations'].append(legacy)
            document['doors'] = [{
                'id': str(uuid4()), 'layerId': document['layers'][0]['id'],
                'assetId': None, 'x1': 6, 'y1': 6, 'x2': 8, 'y2': 6,
                'thickness': .2, 'state': 'locked',
                'blueprint': behavior('door', {
                    'interact': chain('interact', [
                        node('unlock', 'state', targetState='open', players=True)]),
                    'change': chain('change', [
                        node('markDoorChange', 'setVariable', scope='element', name='DoorChanged',
                             valueType='boolean', value=True)]),
                }),
            }]
            authored = review.store(authored['id'], authored['version'], authored['folderId'], document)
            page.goto(review.builder + '?project=' + authored['id'])
            wait_ready(page)
            modal = open_editor(legacy_id)
            legacy_button = modal.locator('[data-blueprint-event="enter:on"]')
            if not legacy_button.is_visible():
                modal.locator('[data-blueprint-state-events] summary').click()
            legacy_button.click()
            expect(modal.locator('[data-blueprint-node="legacyMark"]')).to_be_visible()
            modal.locator('[data-blueprint-save]').click()
            assert review.save()['document'] == authored['document']
            records.append({'case': 'legacy-state-events-remain-accessible-and-no-op-save-preserves-exact-source'})

            modal = open_editor(lever_id)
            modal.locator('[data-blueprint-event="interact"]').click()
            card(modal, check).locator('[data-blueprint-drag]').focus()
            expect(card(modal, check)).to_have_class(re.compile('is-selected'))
            modal.locator('[data-blueprint-event-port="change"]').click()
            expect(card(modal, check)).to_be_visible()
            expect(modal.locator('[data-blueprint-node].is-selected')).to_have_count(0)
            modal.locator('[data-blueprint-cancel]').click()
            assert review.save()['document'] == authored['document']
            records.append({'case': 'switching-event-by-instance-port-clears-selection-even-when-events-share-node-identifiers'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width, height in ((1440, 900), (390, 844)):
                    page.set_viewport_size({'width': width, 'height': height})
                    page.goto(review.builder + '?project=' + authored['id'])
                    wait_ready(page)
                    modal = open_editor(lever_id)
                    modal.locator('[data-blueprint-event="change"]').click()
                    metrics = modal.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    for value in ('change', 'interact'):
                        expect(modal.locator(f'[data-blueprint-event-port="{value}"]')).to_be_visible()
                        expect(modal.locator(f'[data-blueprint-event="{value}"] .smart-object__event-label')).to_be_visible()
                    styles = modal.locator('.smart-object__verb-events').evaluate('''element=>({
                      display:getComputedStyle(element).display,
                      columns:getComputedStyle(element).gridTemplateColumns,
                      labelDisplay:getComputedStyle(element.querySelector('.smart-object__event-label')).display
                    })''')
                    assert styles['display'] == 'grid' and styles['labelDisplay'] == 'grid', styles
                    page.screenshot(path=str(output / f'verb-events-{locale}-{width}.png'))
                    modal.locator('[data-blueprint-cancel]').click()
                    records.append({'case': 'localized-verb-event-editor-keeps-readable-controls-within-viewport',
                                    'locale': locale, 'width': width, 'metrics': metrics, 'styles': styles})

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(review.builder + '?project=' + authored['id'])
            wait_ready(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            game(page)
            project = review.project(authored['id'])
            scene_id = project['sceneId']
            page.evaluate('''args=>gravewrightRealtime.mapCommand('update',{
              mapId:args.scene,version:args.version,settings:{visibility:'players'}})''',
                          {'scene': scene_id, 'version': project['sceneVersion']})
            page.evaluate("scene=>gravewrightRealtime.mapCommand('activate',{mapId:scene})", scene_id)
            player_context = browser.new_context(base_url=base, viewport={'width': 1200, 'height': 800})
            player_context.add_cookies([{**seed['sessions']['player'], 'url': base}])
            player = player_context.new_page()
            observe(player)
            player.goto(f'/game/{campaign}')
            game(player)

            def state(target=page):
                response = target.request.get(f'/api/maps/{scene_id}/state')
                assert response.ok, response.text()
                return response.json()

            native = state()
            owner = next(row for row in native['images'] if row.get('blueprint', {}).get('graphs', {}).get('change'))
            control = player.locator(f'[data-smart-image-id="{owner["id"]}"][data-smart-image-action=interact]')

            def toggle(expected, asset_id):
                control.focus()
                control.press('Enter')
                deadline = time.monotonic() + 12
                while time.monotonic() < deadline:
                    current = next(row for row in state()['images'] if row['id'] == owner['id'])
                    if current['lever']['state'] == expected:
                        break
                    player.wait_for_timeout(100)
                assert current['lever']['state'] == expected and current['asset_id'] == asset_id, current
                public = next(row for row in state(player)['images'] if row['id'] == owner['id'])
                assert 'blueprint' not in public and public['asset_id'] == asset_id, public
                log = page.request.get(f'/api/maps/{scene_id}/automation').json()
                latest = log['runs'][0]
                assert latest['doorId'] == owner['id'] and latest['outcome'] == 'completed', latest
                assert [event['event'] for event in latest['events']] == ['interact', 'change'], latest
                changed, = [event for event in latest['events'] if event['event'] == 'change']
                assert changed['previous'] == ('off' if expected == 'on' else 'on'), changed
                return current, log

            active, active_log = toggle('on', changed_asset)
            inactive, inactive_log = toggle('off', native_asset)
            assert active['id'] == inactive['id'] == owner['id']
            page.screenshot(path=str(output / 'native-verb-events-two-state-toggle.png'))
            assert review.project(authored['id'])['document'] == authored['document']
            records.append({'case': 'real-player-interaction-uses-one-graph-in-both-states-and-change-updates-visible-sprite-with-source-private'})

            public_door, = [wall for wall in state(player)['walls'] if wall['kind'] == 'door']
            assert public_door['door_state'] == 'locked' and 'blueprint' not in public_door, public_door
            assert public_door.get('blueprintInteraction') is True, public_door
            door_control = player.locator('.door-controls [role=button]')
            expect(door_control).to_have_count(1)
            expect(door_control).to_have_attribute('aria-disabled', 'false')
            door_control.focus()
            door_control.press('Enter')
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                operated, = [wall for wall in state(player)['walls'] if wall['kind'] == 'door']
                if operated['door_state'] == 'open':
                    break
                player.wait_for_timeout(100)
            assert operated['door_state'] == 'open' and 'blueprint' not in operated, operated
            records.append({'case': 'locked-door-generic-interaction-keeps-authorized-player-keyboard-control-without-exposing-private-graph'})

            gm_door_control = page.locator('.door-controls [role=button]')
            expect(gm_door_control).to_have_attribute('aria-label', 'Porta open')
            gm_door_control.click(button='right')
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                locked, = [wall for wall in state()['walls'] if wall['kind'] == 'door']
                if locked['door_state'] == 'locked':
                    break
                page.wait_for_timeout(100)
            assert locked['door_state'] == 'locked', locked
            newest = page.request.get(f'/api/maps/{scene_id}/automation').json()['runs'][0]
            assert newest['doorId'] == public_door['id'], newest
            assert newest['stateBefore'] == 'open' and newest['stateAfter'] == 'locked', newest
            assert [event['event'] for event in newest['events']] == ['change'], newest
            records.append({'case': 'gm-explicit-lock-changes-native-state-once-without-running-interaction-graph'})
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
            'assets': 'Synthetic solid-color PNGs and silent WAV; no operator campaign data.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
