"""Discover native clues through management, the table and MapBuilder mechanisms.

Only disposable campaigns, synthetic content and installation-local outputs are
used. Player JSON/event projections are checked alongside the visible interface.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import traceback
from urllib.request import urlopen
from uuid import uuid4

from campaign_management import serve, snapshot as control_snapshot
from map_builder import ROOT, MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale, fixture_environment
from map_builder_asset_removal import BuilderReview
from map_builder_blueprints import artwork
from map_builder_clocks import snapshot as domain_snapshot
from map_builder_reference import close_panel, set_name, upload_asset, wait_ready


NAME = 'Synthetic inscription in the abandoned northern observatory with a deliberately long authored clue name'
CONTENT = 'Synthetic public finding: the northern lens points toward an old mountain passage. ' * 12
GM_NOTES = 'SYNTHETIC_CLUE_GM_NOTES: The keeper planted the inscription to mislead the expedition.'
PRIVATE_NAME = 'Synthetic sealed clue reserved for the observatory keeper'
MAP_NAME = 'Synthetic map mechanism reveals the observatory expedition route after enough progress'


def check_browser(base, seed, output, executable, read_snapshot):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    records, errors, dialogs, failed, contexts = [], [], [], [], []
    pages, sockets, responses = {}, {}, {}
    before_controls = read_snapshot()
    (output / 'control-before.json').write_text(json.dumps(before_controls, indent=2), encoding='utf-8')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))

        def client(name, role, *, manager=False):
            context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 1000})
            contexts.append(context)
            context.add_cookies([{**seed['sessions'][role], 'url': base}])
            context.add_init_script('''window.__clueWire=[];window.__clueStates=[];
              addEventListener('gravewright:api-event',event=>__clueWire.push(event.detail));
              addEventListener('gravewright:resources',event=>{
                if(event.detail.module==='clues') __clueStates.push(event.detail.state);
              });''')
            page = context.new_page()
            pages[name], sockets[name], responses[name] = page, [], []
            page.on('pageerror', lambda error: errors.append(error.stack or str(error)))
            page.on('requestfailed', lambda request: failed.append({'url': request.url, 'error': request.failure}))
            page.on('websocket', lambda socket: sockets[name].append(socket.url))
            page.on('dialog', lambda dialog: (dialogs.append({'type': dialog.type, 'message': dialog.message}), dialog.dismiss()))

            def record_response(response):
                if '/api/' not in response.url or 'application/json' not in response.headers.get('content-type', ''):
                    return
                try:
                    responses[name].append({'url': response.url, 'status': response.status, 'body': response.json()})
                except Exception:
                    # Navigation can cancel a completed response before its body is read.
                    pass

            page.on('response', record_response)
            response = page.goto(f'{base}/campaigns/{campaign}/manage?section=clues' if manager else f'{base}/game/{campaign}')
            assert response.ok, (name, response.status)
            if manager:
                expect(page.locator('#table-workspace')).to_have_attribute('data-manager-ready', 'true')
                expect(page.locator('[data-manager-section=clues]')).to_have_attribute('aria-current', 'page')
                assert not sockets[name], sockets[name]
            else:
                game(page)
            return page

        def game(page):
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def api(page, method, payload=None, *, scene=None, request_id=None, table=None):
            return page.evaluate('''async ({campaign,method,payload,scene,requestId})=>{
              const api=gravewright.forTable(campaign),current=scene??window.gravewrightMaps?.current?.id??null;
              try {return {ok:true,value:await api.clues[method](
                {...payload,sceneId:current},requestId?{requestId}:{})};}
              catch(error){return {ok:false,code:error.code,status:error.status,message:error.message};}
            }''', {'campaign': table or campaign, 'method': method, 'payload': payload,
                  'scene': scene, 'requestId': request_id})

        def mutate(page, method, payload, **options):
            result = api(page, method, payload, **options)
            assert result['ok'], result
            return result['value']

        def state(page, scene=None):
            return mutate(page, 'state', {}, scene=scene)

        def clue(page, identifier, scene=None):
            return next(row for row in state(page, scene)['clues'] if row['id'] == identifier)

        def create(page, name, *, segments=4, value=0, visibility='players', pinned=True, scope=None, scene=None):
            return mutate(page, 'create', {'name': name, 'content': CONTENT, 'gmNotes': GM_NOTES,
                'segments': segments, 'value': value, 'color': '#c69638', 'visibility': visibility,
                'pinned': pinned, 'scopeSceneId': scope}, scene=scene)['clue']

        def panel(page):
            page.locator('[data-clues-open]').click()
            root = page.locator('[data-clue-panel]')
            expect(root).to_be_visible()
            expect(root.locator('[data-clues-root]')).to_be_visible()
            return root

        def card(root, identifier):
            return root.locator(f'[data-clue-id="{identifier}"]')

        def progress(root, identifier, value, segments):
            meter = card(root, identifier).locator('[data-clue-progress]')
            expect(meter).to_have_attribute('aria-valuenow', str(value))
            expect(meter).to_have_attribute('aria-valuemax', str(segments))
            expect(meter.locator('.clues__step')).to_have_count(segments)
            expect(meter.locator('.clues__step--filled')).to_have_count(value)

        def player_privacy(page, name):
            projection = state(page)
            assert GM_NOTES not in json.dumps(projection) and 'gmNotes' not in json.dumps(projection), projection
            assert GM_NOTES not in page.content()
            assert GM_NOTES not in json.dumps(responses[name]), responses[name]
            wire = json.dumps(page.evaluate('window.__clueWire'))
            assert GM_NOTES not in wire and 'gmNotes' not in wire, wire
            return projection

        def latest(page, identifier, action, **payload):
            row = clue(page, identifier)
            return mutate(page, action, {'id': identifier, 'version': row['version'], **payload})

        try:
            manager = client('manager', 'gm', manager=True)
            management = manager.locator('[data-manager-view=clues] [data-clues-root]')
            expect(management).to_be_visible()
            expect(management.locator('[data-clues-empty]')).to_be_visible()
            management.locator('[data-clue-action=create]').click()
            editor = manager.locator('[data-clue-editor]')
            expect(editor).to_be_visible()
            editor.locator('[name=name]').fill(NAME)
            editor.locator('[name=content]').fill(CONTENT)
            editor.locator('[name=gmNotes]').fill(GM_NOTES)
            editor.locator('[name=segments]').fill('1')
            editor.locator('[name=value]').fill('0')
            editor.locator('[name=visibility]').select_option('players')
            editor.locator('[name=pinned]').check()
            editor.locator('[type=submit]').click()
            expect(editor).to_have_count(0)
            immediate = next(row for row in state(manager)['clues'] if row['name'] == NAME)
            immediate_id = immediate['id']
            assert immediate['segments'] == 1 and immediate['value'] == 0 and immediate['gmNotes'] == GM_NOTES, immediate
            progress(management, immediate_id, 0, 1)
            management.locator('[data-clue-action=create]').click()
            expect(editor).to_be_visible()
            editor.locator('[name=name]').fill('Cancelled synthetic clue')
            manager.keyboard.press('Escape')
            expect(editor).to_have_count(0)
            assert len(state(manager)['clues']) == 1
            records.append({'case': 'native-management-editor-creates-one-step-clue-and-escape-discards-a-draft'})

            staged = create(manager, 'Synthetic four-step clue about the observatory lens', value=1)
            private = create(manager, PRIVATE_NAME, segments=1, value=1, visibility='gm', pinned=False)
            scoped = create(manager, 'Synthetic clue restricted to the GM selected scene', segments=1, value=1,
                            scope=seed['selectedScene'], scene=seed['selectedScene'])
            assert scoped['id'] in {row['id'] for row in state(manager, seed['selectedScene'])['clues']}
            assert scoped['id'] not in {row['id'] for row in state(manager, seed['broadcastScene'])['clues']}
            records.append({'case': 'progressive-private-and-scene-scoped-clues-retain-distinct-saved-state'})

            labels = {'en': 'Clues', 'pt-BR': 'Pistas', 'es': 'Pistas'}
            for locale in ('en', 'pt-BR', 'es'):
                change_locale(manager, locale, campaign)
                manager.set_viewport_size({'width': 320, 'height': 844})
                manager.goto(f'{base}/campaigns/{campaign}/manage?section=clues')
                expect(manager.locator('#table-workspace')).to_have_attribute('data-manager-ready', 'true')
                expect(manager.locator('[data-manager-section=clues]')).to_have_text(labels[locale])
                expect(card(management, immediate_id)).to_contain_text(NAME)
                card(management, immediate_id).locator('[data-clue-action=edit]').click()
                expect(editor).to_be_visible()
                expect(editor.locator('[name=name]')).to_have_value(NAME)
                expect(editor.locator('[name=gmNotes]')).to_have_value(GM_NOTES)
                metrics = editor.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                bounds = editor.bounding_box()
                assert bounds and bounds['x'] >= -1 and bounds['y'] >= -1 and bounds['x'] + bounds['width'] <= 321 and bounds['y'] + bounds['height'] <= 845, bounds
                assert manager.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                manager.screenshot(path=str(output / f'clue-editor-{locale}-320.png'), full_page=True)
                manager.keyboard.press('Escape')
                expect(editor).to_have_count(0)
                metrics = management.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                records.append({'case': f'localized-management-list-and-native-editor-{locale}-320'})
            after_controls = read_snapshot()
            (output / 'control-after.json').write_text(json.dumps(after_controls, indent=2), encoding='utf-8')
            assert after_controls == before_controls, (before_controls, after_controls)
            assert not sockets['manager'], sockets['manager']
            records.append({'case': 'management-preserves-broadcast-private-navigation-presence-and-websocket-boundaries'})

            change_locale(manager, 'en', campaign)
            manager.set_viewport_size({'width': 1440, 'height': 1000})
            manager.goto(f'{base}/campaigns/{campaign}/manage?section=clues')
            expect(manager.locator('#table-workspace')).to_have_attribute('data-manager-ready', 'true')
            gm, player, streamer = client('gm', 'gm'), client('player', 'player'), client('streamer', 'streamer')
            gm_panel = panel(gm)
            assert len(state(player)['clues']) == 0 and len(state(streamer)['clues']) == 0
            for name, page in (('player', player), ('streamer', streamer)):
                projection = player_privacy(page, name)
                assert NAME not in json.dumps(projection) and PRIVATE_NAME not in json.dumps(projection)
                assert NAME not in page.content() and PRIVATE_NAME not in page.content()
                received = json.dumps(responses[name]) + json.dumps(page.evaluate('window.__clueWire'))
                assert all(identifier not in received for identifier in (immediate_id, staged['id'], private['id'], scoped['id']))
            records.append({'case': 'unrevealed-and-private-clues-expose-no-player-record-name-content-id-or-gm-notes'})

            for page, method, payload in (
                (player, 'advance', {'id': immediate_id, 'version': immediate['version'], 'delta': 1}),
                (player, 'reveal', {'id': private['id'], 'version': private['version']}),
                (player, 'create', {'name': 'Forbidden synthetic clue'}),
                (streamer, 'advance', {'id': staged['id'], 'version': staged['version'], 'delta': 1}),
            ):
                denied = api(page, method, payload)
                assert not denied['ok'] and denied['status'] in (403, 404), denied
            denied = api(gm, 'state', table=seed['otherCampaign'])
            assert not denied['ok'] and denied['status'] in (403, 404), denied
            records.append({'case': 'player-streamer-and-foreign-campaign-requests-cannot-configure-or-discover-clues-directly'})

            request_id = str(uuid4())
            payload = {'id': staged['id'], 'version': staged['version'], 'delta': 1}
            first = mutate(gm, 'advance', payload, request_id=request_id)
            replay = mutate(gm, 'advance', payload, request_id=request_id)
            assert first == replay and clue(gm, staged['id'])['value'] == 2, (first, replay)
            conflict = api(gm, 'reset', {'id': staged['id'], 'version': staged['version']})
            assert not conflict['ok'] and conflict['status'] == 409, conflict
            assert staged['id'] not in {row['id'] for row in state(player)['clues']}
            records.append({'case': 'receipt-retry-advances-once-and-stale-revision-cannot-reset-concurrent-progress'})

            card(gm_panel, immediate_id).locator('[data-clue-action=reveal]').click()
            player_panel, streamer_panel = panel(player), panel(streamer)
            for root in (player_panel, streamer_panel, player.locator('[data-clue-hud]')):
                expect(card(root, immediate_id)).to_be_visible()
            expect(card(player_panel, immediate_id)).to_contain_text(NAME)
            player.keyboard.press('Escape')
            expect(player_panel).to_have_count(0)
            card(player.locator('[data-clue-hud]'), immediate_id).locator('[data-clue-name]').dblclick()
            reader = player.locator(f'[data-clue-view="{immediate_id}"]')
            expect(reader).to_be_visible()
            expect(reader).to_contain_text(CONTENT.strip())
            expect(reader.locator('[name=gmNotes]')).to_have_count(0)
            expect(reader.locator('[type=submit]:visible')).to_have_count(0)
            expect(reader.locator('input,textarea,select')).to_have_count(0)
            player.keyboard.press('Escape')
            expect(reader).to_have_count(0)
            player_panel = panel(player)
            for root in (player_panel, streamer_panel):
                expect(root.locator('[data-clue-action]:visible')).to_have_count(0)
                expect(card(root, immediate_id).locator('[data-clue-progress]')).to_have_attribute('role', 'progressbar')
            for name, page in (('player', player), ('streamer', streamer)):
                player_privacy(page, name)
            manager.evaluate("window.dispatchEvent(new Event('focus'))")
            progress(management, immediate_id, 1, 1)
            records.append({'case': 'gm-reveal-publishes-readonly-finding-and-pinned-display-without-gm-notes'})

            card(gm_panel, immediate_id).locator('[data-clue-action=hide]').click()
            expect(card(player_panel, immediate_id)).to_have_count(0)
            expect(card(player.locator('[data-clue-hud]'), immediate_id)).to_have_count(0)
            saved = clue(gm, immediate_id)
            assert saved['value'] == 1 and saved['visibility'] == 'gm', saved
            latest(gm, immediate_id, 'reveal')
            expect(card(player_panel, immediate_id)).to_be_visible()
            latest(gm, staged['id'], 'advance', delta=1)
            assert staged['id'] not in {row['id'] for row in state(player)['clues']}
            latest(gm, staged['id'], 'advance', delta=1)
            expect(card(player_panel, staged['id'])).to_be_visible()
            player.reload()
            game(player)
            player_panel = panel(player)
            expect(card(player_panel, immediate_id)).to_be_visible()
            expect(card(player_panel, staged['id'])).to_be_visible()
            player_privacy(player, 'player')
            player.screenshot(path=str(output / 'revealed-player-clues-1440.png'), full_page=True)
            records.append({'case': 'hide-preserves-progress-progressive-completion-reveals-and-reload-restores-only-discoveries'})

            map_clue = create(gm, MAP_NAME, value=2)
            gm.keyboard.press('Escape')
            expect(gm.locator('[data-clue-panel]')).to_have_count(0)
            player.keyboard.press('Escape')
            expect(player.locator('[data-clue-panel]')).to_have_count(0)
            review = BuilderReview(gm, campaign)
            gm.goto(review.builder)
            wait_ready(gm)
            set_name(gm, 'Synthetic clue discovery mechanism')
            image = upload_asset(gm, 'decoration', 'Synthetic clue mechanism.png', artwork('#38779a'))['id']
            builder_tool(gm, 'decoration')
            gm.locator('[data-builder-brush-material]').select_option(image)
            review.stroke((6, 6), (8, 8))
            builder_sidebar(gm, 'selection')
            gm.locator('[data-builder-property=behavior]').select_option('lever')
            close_panel(gm)
            project = review.save()
            document = deepcopy(project['document'])
            document.update(columns=14, rows=12, cellSize=64)
            project = review.store(project['id'], project['version'], project['folderId'], document)
            owner = project['document']['decorations'][0]['id']
            gm.goto(review.builder + '?project=' + project['id'])
            wait_ready(gm)

            def open_editor():
                builder_tool(gm, 'select')
                builder_workspace(gm)
                bounds = gm.locator(f'[data-builder-decorations] [data-object-id="{owner}"]').bounding_box()
                gm.mouse.click(bounds['x'] + bounds['width'] * .25, bounds['y'] + bounds['height'] * .25)
                builder_sidebar(gm, 'selection')
                gm.locator('[data-builder-edit-behavior]').click()
                editor = gm.locator('[data-smart-object-modal]')
                expect(editor).to_be_visible()
                editor.locator('[data-blueprint-event=interact]').click()
                return editor

            def node(editor, identifier):
                return editor.locator(f'[data-blueprint-node="{identifier}"]')

            def parameter(editor, identifier, key, value):
                control = node(editor, identifier).locator(f'[data-blueprint-param="{key}"]')
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

            def close_editor(editor, *, changed=True):
                expect(editor.locator('[data-blueprint-autosave]')).to_have_attribute('data-state', 'saved' if changed else 'idle')
                editor.locator('[data-blueprint-close]').click()
                expect(editor).to_have_count(0)

            editor = open_editor()
            action = add(editor, 'clueControl', clueId=map_clue['id'], action='advance', amount=1)
            numeric = add(editor, 'getVariable', valueType='number', scope='element', name='ClueDiscoveryAmount', default=2)
            reveal = add(editor, 'clueControl', clueId=private['id'], action='reveal')
            continuation = add(editor, 'setVariable', valueType='boolean', scope='element', name='ClueChainFinished', value=True)
            wire(editor, editor.locator('[data-blueprint-instance] [data-blueprint-event-port=interact][data-blueprint-output=next]'),
                 node(editor, action).locator('[data-blueprint-input]'))
            for source, target in ((action, reveal), (reveal, continuation)):
                wire(editor, node(editor, source).locator('[data-blueprint-output=next]'), node(editor, target).locator('[data-blueprint-input]'))
            wire(editor, node(editor, numeric).locator('[data-blueprint-data-output=value]'), node(editor, action).locator('[data-blueprint-data-input=amount]'))
            expect(node(editor, action).locator('[data-blueprint-param=amount]')).to_be_disabled()
            expect(node(editor, reveal).locator('[data-blueprint-param=amount]')).to_be_disabled()
            expect(editor.locator('[data-blueprint-edge]')).to_have_count(4)
            editor.locator('[data-blueprint-simulate]').click()
            expect(editor.locator('[data-blueprint-trace]')).to_contain_text(MAP_NAME)
            assert clue(gm, map_clue['id'])['value'] == 2
            close_editor(editor)
            review.save()
            gm.reload()
            wait_ready(gm)
            editor = open_editor()
            expect(node(editor, action).locator('[data-blueprint-param=clueId]')).to_have_value(map_clue['id'])
            expect(node(editor, action).locator('[data-blueprint-param=amount]')).to_be_disabled()
            close_editor(editor, changed=False)
            records.append({'case': 'native-clue-node-chooser-numeric-port-execution-chain-save-and-reload'})

            before = domain_snapshot(output)
            player.evaluate('window.__clueStates=[]')
            gm.locator('[data-builder-test]').click()
            rehearsal = gm.locator('[data-playtest]')
            expect(rehearsal).to_be_visible()
            rehearsal.locator('[data-playtest-element]').select_option(owner)
            rehearsal.locator('[data-playtest-event]').select_option('interact')
            with gm.expect_response(lambda response: response.request.method == 'POST' and response.url.endswith('/map-builder/test')) as tested:
                rehearsal.locator('[data-playtest-run]').click()
            assert tested.value.ok, tested.value.text()
            prediction = tested.value.json()
            assert prediction['ok'] and prediction['dryRun'], prediction
            changed = {entry['id']: entry for entry in prediction['changes']['clues']}
            assert changed[map_clue['id']]['before']['value'] == 2 and changed[map_clue['id']]['after']['value'] == 4, changed
            assert changed[private['id']]['before']['visibility'] == 'gm' and changed[private['id']]['after']['visibility'] == 'players', changed
            expect(rehearsal.locator('[data-playtest-results]')).to_contain_text(MAP_NAME)
            assert domain_snapshot(output) == before
            assert map_clue['id'] not in {row['id'] for row in state(player)['clues']}
            assert not any(row['id'] in (map_clue['id'], private['id'])
                           for projection in player.evaluate('window.__clueStates') for row in projection.get('clues', []))
            gm.screenshot(path=str(output / 'clue-rehearsal-rollback-1440.png'))
            gm.keyboard.press('Escape')
            expect(rehearsal).to_have_count(0)
            records.append({'case': 'clue-rehearsal-predicts-discovery-and-reverts-rows-receipts-media-and-player-notifications'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(gm, locale, campaign)
                gm.set_viewport_size({'width': 320, 'height': 844})
                gm.goto(review.builder + '?project=' + project['id'])
                wait_ready(gm)
                editor = open_editor()
                expect(node(editor, action).locator('[data-blueprint-param=clueId] option:checked')).to_have_text(MAP_NAME)
                editor.locator('[data-blueprint-fit]').click()
                metrics = editor.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)
                gm.screenshot(path=str(output / f'clue-node-{locale}-320.png'))
                close_editor(editor, changed=False)
                records.append({'case': f'localized-native-clue-node-editor-{locale}-320'})

            change_locale(gm, 'en', campaign)
            gm.set_viewport_size({'width': 1440, 'height': 1000})
            gm.goto(review.builder + '?project=' + project['id'])
            wait_ready(gm)
            with gm.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                gm.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            game(gm)
            project = review.project(project['id'])
            scene = project['sceneId']
            gm.evaluate('args=>gravewrightRealtime.mapCommand("update",{mapId:args.scene,version:args.version,settings:{visibility:"players"}})',
                        {'scene': scene, 'version': project['sceneVersion']})
            gm.evaluate('scene=>gravewrightRealtime.mapCommand("activate",{mapId:scene})', scene)
            player.wait_for_function('scene=>gravewrightMaps.current?.id===scene', arg=scene)
            native = gm.request.get(f'/api/maps/{scene}/state').json()
            lever, = [image for image in native['images'] if image.get('lever')]
            control = player.locator(f'[data-smart-image-id="{lever["id"]}"][data-smart-image-action=interact]')

            def interact(value, visibility):
                control.focus()
                control.press('Enter')
                gm.wait_for_function('''async ({campaign,id,value,visibility})=>{
                  const state=await gravewright.forTable(campaign).clues.state({sceneId:gravewrightMaps.current.id});
                  const row=state.clues.find(row=>row.id===id);return row?.value===value&&row.visibility===visibility;
                }''', arg={'campaign': campaign, 'id': map_clue['id'], 'value': value, 'visibility': visibility})
                discovered = value == 4 and visibility == 'players'
                if discovered:
                    expect(card(player.locator('[data-clue-hud]'), map_clue['id'])).to_be_visible()
                else:
                    expect(card(player.locator('[data-clue-hud]'), map_clue['id'])).to_have_count(0)
                projection = player_privacy(player, 'player')
                assert (map_clue['id'] in {row['id'] for row in projection['clues']}) == discovered, projection

            interact(4, 'players')
            assert private['id'] in {row['id'] for row in state(player)['clues']}
            native = gm.request.get(f'/api/maps/{scene}/state').json()
            assert next(image for image in native['images'] if image['id'] == lever['id'])['automationVariables']['ClueChainFinished']['value'] is True
            player.screenshot(path=str(output / 'player-map-discovery-hud-1440.png'))
            records.append({'case': 'player-mechanism-executes-gm-delegated-discovery-and-private-reveal-without-general-clue-permissions'})

            for operation, amount, value, visibility in (('reduce', 1, 3, 'players'), ('set', 4, 4, 'players'),
                    ('reset', 4, 0, 'players'), ('reveal', 4, 4, 'players'), ('hide', 4, 4, 'gm')):
                gm.get_by_role('button', name='Walls', exact=True).click()
                gm.locator('[data-dock-tool=automation]').click()
                gm.locator('[data-automation-network]').click()
                network = gm.locator('[data-scene-network]')
                expect(network).to_be_visible()
                network.locator(f'[data-network-open="{lever["id"]}"]').click()
                editor = gm.locator('[data-smart-object-modal]')
                expect(editor).to_be_visible()
                editor.locator('[data-blueprint-event=interact]').click()
                parameter(editor, action, 'action', operation)
                parameter(editor, numeric, 'default', amount)
                expect(node(editor, action).locator('[data-blueprint-param=amount]')).to_be_disabled()
                close_editor(editor)
                network.locator('[data-network-close]').click()
                gm.locator('[data-automation-close]').click()
                interact(value, visibility)
                source = review.project(project['id'])['document']['decorations'][0]['blueprint']['graphs']['interact']
                assert next(row for row in source['nodes'] if row['id'] == action)['action'] == operation
                records.append({'case': f'live-clue-node-{operation}-updates-shared-state-and-saved-source'})
            for name, page in (('player', player), ('streamer', streamer)):
                player_privacy(page, name)
            assert not errors, errors
            assert not dialogs, dialogs
            assert not [request for request in failed if request['error'] != 'net::ERR_ABORTED'], failed
        except Exception:
            (output / 'progress.json').write_text(json.dumps({'cases': records, 'pageErrors': errors,
                'nativeDialogs': dialogs, 'failedRequests': failed}, indent=2), encoding='utf-8')
            for name, page in pages.items():
                page.screenshot(path=str(output / f'failure-{name}.png'), full_page=True)
            raise
        finally:
            for context in contexts:
                context.close()
            browser.close()
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'failedRequests': failed, 'assets': 'Generated solid-color PNG and synthetic clue names/content/GM notes only.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--snapshot', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--fixture', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--port', type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve:
        serve(args.fixture, args.port)
        return
    if args.snapshot:
        control_snapshot(args.fixture)
        return
    output = (args.output or ROOT / 'data/clues' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError('Use a fresh, empty output directory.')
    output.mkdir(parents=True, exist_ok=True)
    fixture = output / 'fixture'
    fixture.mkdir()
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0))
        port = connection.getsockname()[1]
    fixture_environment(fixture, port)
    executable = sys._base_executable if os.name == 'nt' else sys.executable
    command = [executable, '-B', '-X', 'utf8', str(Path(__file__).resolve())]
    base = f'http://127.0.0.1:{port}'
    with (output / 'server.log').open('w', encoding='utf-8') as log:
        server = subprocess.Popen([*command, '--serve', '--fixture', str(fixture), '--port', str(port)],
                                  cwd=ROOT, env=os.environ.copy(), stdout=log, stderr=log)
        try:
            for _ in range(300):
                if server.poll() is not None:
                    raise RuntimeError(f"Fixture exited; inspect {output / 'server.log'}")
                try:
                    with urlopen(base, timeout=1):
                        break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Fixture did not become ready.')
            seed = json.loads((fixture / 'seed.json').read_text(encoding='utf-8'))

            def read_snapshot():
                return json.loads(subprocess.check_output([*command, '--snapshot', '--fixture', str(fixture)],
                    cwd=ROOT, env=os.environ.copy(), text=True, encoding='utf-8'))

            report = check_browser(base, seed, output, args.browser_executable, read_snapshot)
            (output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(json.dumps({'passed': True, 'cases': len(report['cases']), 'report': str(output / 'report.json')}))
        except Exception:
            (output / 'failure.txt').write_text(traceback.format_exc(), encoding='utf-8')
            raise
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
            (output / 'server-exit.json').write_text(json.dumps({'pid': server.pid, 'exitCode': server.returncode}), encoding='utf-8')


if __name__ == '__main__':
    main()
