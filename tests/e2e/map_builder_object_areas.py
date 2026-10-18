"""Exercise object area events through the editor, rehearsal and real token moves.

All artwork, actors, sessions, database, media and server belong to the disposable
browser fixture. Object events never change a mechanism's state implicitly.
"""
from __future__ import annotations

from copy import deepcopy
import json
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_playtest import chain, node, persistent_snapshot
from map_builder_reference import close_panel, upload_asset, wait_ready


OBJECT_EVENTS = {'interact', 'presence:enter', 'presence:exit', 'destroy'}


def behavior(kind):
    return {'version': 2, 'kind': kind,
            'states': {state: {'appearance': 'inherit'} for state in ('off', 'on')},
            'graphs': {event: chain(event, [node('inside', 'setVariable',
                scope='element', name='AreaInside', valueType='boolean', value=inside)])
                for event, inside in (('presence:enter', True), ('presence:exit', False))}}


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
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

        def saved():
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved', timeout=20_000)
            identifier = page.evaluate("new URL(location.href).searchParams.get('project')")
            assert identifier
            return review.project(identifier)

        def editor(identifier):
            builder_tool(page, 'select')
            builder_workspace(page)
            point = page.locator(f'[data-builder-decorations] [data-object-id="{identifier}"]').evaluate('''group=>{
              const box=group.getBBox(),point=new DOMPoint(box.x+box.width*.25,box.y+box.height*.5)
                .matrixTransform(group.getScreenCTM());
              return [point.x,point.y];
            }''')
            page.mouse.dblclick(*point)
            modal = page.locator('[data-smart-object-modal]')
            expect(modal).to_be_visible()
            return modal

        def game(target=page):
            target.wait_for_url(f'{base}/game/{campaign}')
            target.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(target.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        try:
            page.goto(f'/game/{campaign}')
            game()
            actor = page.evaluate('''()=>gravewrightRealtime.resourceCommand('actors','actor.create',
              {name:'Synthetic object area traveler'})''')
            page.evaluate('''id=>gravewrightRealtime.resourceCommand('actors','actor.permissions',
              {id,permissions:{default:'owner'}})''', actor['id'])
            page.goto(review.builder)
            wait_ready(page)
            page.locator('[data-builder-quick-name]').fill('Synthetic smart object area events')
            page.locator('[data-builder-quick-name]').press('Tab')
            artwork = upload_asset(page, 'decoration', 'Synthetic object area artwork.png',
                                   harness.artwork('#a56632'))['id']
            project = saved()
            document = deepcopy(project['document'])
            layer = document['layers'][0]['id']
            lever, empty, torch, lamp = (str(uuid4()) for _ in range(4))
            document['decorations'] = [
                {'id': lever, 'layerId': layer, 'assetId': artwork,
                 'x': 8, 'y': 8, 'width': 4, 'height': 3, 'rotation': 0,
                 'lever': {'state': 'off'}, 'blueprint': behavior('lever')},
                {'id': empty, 'layerId': layer, 'assetId': None, 'empty': True,
                 'name': 'Invisible encounter area with an intentionally long authored label',
                 'x': 16, 'y': 8, 'width': 4, 'height': 3, 'rotation': 0,
                 'lever': {'state': 'off'}, 'blueprint': behavior('lever')},
                {'id': torch, 'layerId': layer, 'assetId': artwork,
                 'x': 26, 'y': 8, 'width': 4, 'height': 1, 'rotation': 45,
                 'torch': {'state': 'off', 'lit': True, 'lightId': lamp}, 'blueprint': behavior('torch')},
            ]
            document['lights'] = [{'id': lamp, 'layerId': layer, 'x': 28, 'y': 8.5,
                'brightRadius': 2, 'dimRadius': 3, 'color': '#ffbb66', 'intensity': .8,
                'enabled': True, 'rotation': 0, 'angle': 360, 'animation': 'torch'}]
            project = review.store(project['id'], project['version'], project['folderId'], document)
            page.goto(review.builder + '?project=' + project['id'])
            wait_ready(page)
            for identifier, kind in ((lever, 'lever'), (torch, 'torch'), (empty, 'empty')):
                modal = editor(identifier)
                assert set(modal.locator('[data-blueprint-event]').evaluate_all(
                    'rows=>rows.map(row=>row.dataset.blueprintEvent)')) == OBJECT_EVENTS
                for event, code in (('presence:enter', 'onAreaEnter'), ('presence:exit', 'onAreaExited')):
                    port = modal.locator(f'[data-blueprint-event-port="{event}"]')
                    expect(port).to_be_visible()
                    expect(port).to_contain_text(code)
                    modal.locator(f'[data-blueprint-event="{event}"]').click()
                    modal.locator('[data-blueprint-simulate]').click()
                    expect(modal.locator('[data-blueprint-trace]')).to_contain_text('AreaInside')
                metrics = modal.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], metrics
                page.screenshot(path=str(output / f'{kind}-area-events-desktop.png'))
                modal.locator('[data-blueprint-close]').click()
                records.append({'case': 'object-editor-exposes-and-simulates-both-area-events', 'kind': kind})

            for locale in ('pt-BR', 'es'):
                change_locale(page, locale, campaign)
                page.set_viewport_size({'width': 390, 'height': 844})
                page.goto(review.builder + '?project=' + project['id'])
                wait_ready(page)
                modal = editor(empty)
                modal.locator('[data-blueprint-event="presence:enter"]').click()
                metrics = modal.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], metrics
                page.screenshot(path=str(output / f'empty-area-events-{locale}-390.png'))
                modal.locator('[data-blueprint-close]').click()
                records.append({'case': 'localized-narrow-area-event-editor-remains-readable', 'locale': locale})

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(review.builder + '?project=' + project['id'])
            wait_ready(page)
            before = persistent_snapshot(output)
            page.locator('[data-builder-test]').click()
            rehearsal = page.locator('[data-playtest]')
            rehearsal.locator('[data-playtest-element]').select_option(empty)
            rehearsal.locator('[data-playtest-event]').select_option('presence:enter')
            rehearsal.locator('[data-playtest-actor]').select_option(actor['id'])
            with page.expect_response(lambda response: response.request.method == 'POST'
                                      and response.url.endswith('/map-builder/test')) as rehearsed:
                rehearsal.locator('[data-playtest-run]').click()
            assert rehearsed.value.ok, rehearsed.value.text()
            prediction = rehearsed.value.json()
            assert prediction['ok'] and prediction['dryRun'], prediction
            change = next(row for row in prediction['changes']['elements'] if row.get('sourceId') == empty)
            assert change['after']['data']['automationVariables']['AreaInside']['value'] is True, prediction
            assert change['after']['data']['lever']['state'] == 'off', prediction
            assert persistent_snapshot(output) == before
            rehearsal.locator('[data-playtest-close]').click()
            records.append({'case': 'draft-area-rehearsal-predicts-only-authored-action-and-rolls-back-all-state'})

            close_panel(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            game()
            project = review.project(project['id'])
            scene = project['sceneId']

            def state(target=page):
                response = target.request.get(f'/api/maps/{scene}/state')
                assert response.ok, response.text()
                return response.json()

            def automation():
                response = page.request.get(f'/api/maps/{scene}/automation')
                assert response.ok, response.text()
                return response.json()

            native = state()
            native_lever = next(row['id'] for row in native['images'] if row.get('lever') and not row.get('empty'))
            native_empty = next(row['id'] for row in native['images'] if row.get('empty'))
            native_torch = next(row['id'] for row in native['images'] if row.get('torch'))
            page.evaluate('''a=>gravewrightRealtime.mapCommand('update',{
              mapId:a.scene,version:a.version,settings:{visibility:'players'}})''',
                          {'scene': scene, 'version': project['sceneVersion']})
            page.evaluate("scene=>gravewrightRealtime.mapCommand('activate',{mapId:scene})", scene)
            page.evaluate('''scene=>gravewrightRealtime.mapCommand('objects',{
              mapId:scene,area:'lighting',action:'update',data:{mode:'none',darkness:0,lights_out:false}})''', scene)
            tokens = [page.evaluate('''a=>gravewrightRealtime.resourceCommand('tokens','place',
              {mapId:a.scene,actorId:a.actor,gridX:a.x,gridY:3})''',
                      {'scene': scene, 'actor': actor['id'], 'x': x})['createdIds'][0] for x in (2, 3)]
            player_context = browser.new_context(base_url=base, viewport={'width': 1200, 'height': 800})
            player_context.add_cookies([{**seed['sessions']['player'], 'url': base}])
            player = player_context.new_page()
            observe(player)
            player.goto(f'/game/{campaign}')
            game(player)
            player.wait_for_function('scene=>window.gravewrightMaps?.current?.id===scene', arg=scene)

            def move(identifier, x, y):
                return player.evaluate('''async a=>{
                  const body=await(await fetch(`/api/containers/${a.campaign}/maps/${a.scene}/tokens`)).json();
                  const token=body.tokens.find(row=>row.id===a.id);
                  return gravewrightRealtime.resourceCommand('tokens','move',{mapId:a.scene,id:a.id,
                    expectedVersion:token.version,gridX:a.x,gridY:a.y});
                }''', {'campaign': campaign, 'scene': scene, 'id': identifier, 'x': x, 'y': y})

            def area_events(identifier):
                return [{**event, 'context': run.get('context', {})} for run in reversed(automation()['runs'])
                        if run.get('doorId') == identifier or run.get('elementId') == identifier
                        for event in run.get('events', []) if event['event'].startswith('presence:')]

            def verify(identifier, inside):
                current = next(row for row in state()['images'] if row['id'] == identifier)
                assert current.get('torch', current.get('lever'))['state'] == 'off', current
                assert current['automationVariables']['AreaInside']['value'] is inside, current
                assert 'areaPresence' not in current, current
                return current

            move(tokens[0], 9, 9)
            verify(native_lever, True)
            move(tokens[1], 10, 9)
            verify(native_lever, True)
            move(tokens[0], 9, 16)
            verify(native_lever, False)
            move(tokens[1], 10, 16)
            verify(native_lever, False)
            entered = area_events(native_lever)
            assert [event['event'] for event in entered] == ['presence:enter', 'presence:enter', 'presence:exit', 'presence:exit'], entered
            assert [event['context']['count'] for event in entered] == [1, 2, 1, 0], entered
            assert [event['context']['tokenId'] for event in entered] == [tokens[0], tokens[1], tokens[0], tokens[1]], entered
            records.append({'case': 'real-player-multi-token-object-entry-and-exit-start-every-time-without-state-comparisons-or-toggles'})

            move(tokens[0], 17, 9)
            verify(native_empty, True)
            move(tokens[0], 17, 16)
            verify(native_empty, False)
            records.append({'case': 'image-free-object-area-runs-on-real-player-token-movement'})

            before_torch = area_events(native_torch)
            move(tokens[0], 27, 9)
            assert area_events(native_torch) == before_torch
            move(tokens[0], 27, 7)
            verify(native_torch, True)
            move(tokens[0], 27, 9)
            current_torch = verify(native_torch, False)
            assert current_torch['rotation'] == 45 and current_torch['torch']['lit'] is True, current_torch
            assert [event['event'] for event in area_events(native_torch)] == ['presence:enter', 'presence:exit']
            records.append({'case': 'rotated-torch-area-uses-actual-image-bounds-and-preserves-mechanism-and-flame'})

            move(tokens[0], 5, 9)
            crossing_before = len(area_events(native_lever))
            move(tokens[0], 13, 9)
            crossed = area_events(native_lever)[crossing_before:]
            assert [event['event'] for event in crossed] == ['presence:enter', 'presence:exit'], crossed
            verify(native_lever, False)
            records.append({'case': 'one-accepted-movement-segment-crossing-an-entire-object-starts-entry-then-exit'})

            public = json.dumps(state(player))
            assert all(key not in public for key in ('areaPresence', 'occupants', 'automationVariables', '"blueprint"')), public
            page.screenshot(path=str(output / 'native-object-areas-after-player-crossings.png'))
            records.append({'case': 'player-projection-keeps-private-area-occupancy-variables-and-graphs-hidden'})
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
            'assets': 'Synthetic solid PNG, disposable actors and shared fixture silent WAV only.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
