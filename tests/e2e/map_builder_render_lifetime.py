"""Keep both GPU boards alive while presence portals rebuild masked effects.

Artwork, actors, sessions and all persistence belong to a disposable fixture.
The test observes real token commands, rendered pixels and browser exceptions.
"""
from __future__ import annotations

from copy import deepcopy
from io import BytesIO
import json
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder_asset_removal import BuilderReview
from map_builder_combination_matrix import behavior
from map_builder_playtest import chain, node
from map_builder_reference import close_panel, upload_asset, wait_ready


def check_browser(base, seed, output, executable):
    from PIL import Image, ImageChops
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    cases, errors, dialogs, contexts, clients = [], [], [], [], {}
    scene = None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))

        def client(role):
            context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
            context.add_cookies([{**seed['sessions'][role], 'url': base}])
            context.add_init_script('''window.__renderLifetime={layers:[],errors:[]};
              addEventListener('gravewright:map-layers',e=>__renderLifetime.layers.push(e.detail));
              addEventListener('error',e=>__renderLifetime.errors.push(e.error?.stack||e.message));''')
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append({'role': role, 'message': str(error), 'stack': error.stack}))
            page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
            contexts.append(context)
            clients[role] = page
            return page

        gm = client('gm')
        review = BuilderReview(gm, campaign)

        def game(page):
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.board?.viewport() && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def command(area, action, data):
            return gm.evaluate('''a=>gravewrightRealtime.mapCommand('objects',{
              mapId:a.scene,area:a.area,action:a.action,data:a.data})''',
                {'scene': scene, 'area': area, 'action': action, 'data': data})

        def resource(area, action, data, page=gm):
            return page.evaluate('''a=>gravewrightRealtime.resourceCommand(a.area,a.action,a.data)''',
                {'area': area, 'action': action, 'data': data})

        def tokens():
            response = gm.request.get(f'/api/containers/{campaign}/maps/{scene}/tokens')
            assert response.ok, response.text()
            return response.json()['tokens']

        def record(label):
            for page in clients.values():
                page.wait_for_timeout(120)
                page.screenshot(path=str(output / f'{len(cases):02d}-{label}-{next(k for k,v in clients.items() if v is page)}.png'))
            cases.append({'case': label})
            assert not errors, errors

        try:
            gm.goto(review.builder)
            wait_ready(gm)
            gm.locator('[data-builder-quick-name]').fill('Synthetic portal render lifetime')
            gm.locator('[data-builder-quick-name]').press('Tab')
            blue = upload_asset(gm, 'decoration', 'Synthetic portal blue.png', harness.artwork('#245dc9'))['id']
            orange = upload_asset(gm, 'decoration', 'Synthetic portal orange.png', harness.artwork('#ed7822'))['id']
            expect(gm.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved', timeout=20_000)
            project = review.project(gm.evaluate("new URL(location.href).searchParams.get('project')"))
            document = deepcopy(project['document'])
            layer = document['layers'][0]['id']
            source, destination, lamp, target = [str(uuid4()) for _ in range(4)]
            document['background'] = '#24303a'
            document['decorations'] = [{'id': target, 'layerId': layer, 'assetId': blue,
                'x': 17, 'y': 16, 'width': 3, 'height': 3, 'rotation': 0}]
            document['regions'] = []
            for index, (identifier, other, x) in enumerate(((source, destination, 8), (destination, source, 23))):
                graph = chain('presence:enter', [
                    node('sprite', 'sprite', appearance='asset', assetId=orange if index == 0 else blue),
                    node('light', 'light', targetId=lamp, enabled=index == 0),
                    node('transport', 'teleport', destinationId=other)],
                    [node('target', 'reference', targetId=target)], [('target', 'door', 'sprite', 'target')])
                document['regions'].append({'id': identifier, 'layerId': layer, 'x': x, 'y': 8,
                    'width': 3, 'height': 3, 'name': f'Synthetic portal {index}', 'enabled': True,
                    'blueprint': behavior('region', {'presence:enter': graph})})
            document['lights'] = [{'id': lamp, 'layerId': layer, 'x': 17, 'y': 10,
                'brightRadius': 3, 'dimRadius': 6, 'color': '#ffbb66', 'intensity': .8,
                'enabled': True, 'rotation': 35, 'angle': 225, 'animation': 'pulse'}]
            document['particles'] = [{'id': str(uuid4()), 'layerId': layer, 'kind': 'smoke',
                'x': 17, 'y': 10, 'scale': 2, 'density': .3, 'color': '#aabbee',
                'enabled': True, 'rotation': 0, 'light_response': .4, 'light_emission': .2}]
            document['shaders'] = [{'id': str(uuid4()), 'layerId': layer, 'name': 'Synthetic masked aura',
                'x': 17, 'y': 10, 'source': 'gravewright-preset://orb-1/v1', 'radius': 4,
                'scale': 1, 'intensity': .8, 'opacity': .65, 'speed': 1, 'color': '#8fb6ff',
                'rotation': 0, 'blend_mode': 'add', 'enabled': True, 'light_response': .4, 'light_emission': .3}]
            project = review.store(project['id'], project['version'], project['folderId'], document)
            gm.goto(review.builder + '?project=' + project['id'])
            wait_ready(gm)
            close_panel(gm)
            with gm.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                gm.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            game(gm)
            project = review.project(project['id'])
            scene = project['sceneId']
            gm.evaluate('''a=>gravewrightRealtime.mapCommand('update',{mapId:a.scene,version:a.version,
              settings:{visibility:'players'}})''', {'scene': scene, 'version': project['sceneVersion']})
            gm.evaluate("scene=>gravewrightRealtime.mapCommand('activate',{mapId:scene})", scene)
            command('lighting', 'update', {'mode': 'dynamic', 'darkness': .6, 'lights_out': False})
            actor = resource('actors', 'actor.create', {'name': 'Synthetic portal traveler'})
            resource('actors', 'actor.permissions', {'id': actor['id'], 'permissions': {'default': 'owner'}})
            csrf = gm.request.get('/__gravewright/csrf').json()
            uploaded = gm.request.post(f'/api/containers/{campaign}/actor-upload',
                headers={csrf['header']: csrf['token']}, multipart={
                    'actorId': actor['id'], 'kind': 'token',
                    'file': {'name': 'Synthetic shared token.png', 'mimeType': 'image/png',
                             'buffer': harness.artwork('#78b53a')}})
            assert uploaded.ok, uploaded.text()
            placed = resource('tokens', 'place', {'mapId': scene, 'actorId': actor['id'], 'gridX': 5, 'gridY': 12})
            token_id = placed['createdIds'][0]
            twin = resource('tokens', 'place', {'mapId': scene, 'actorId': actor['id'], 'gridX': 5, 'gridY': 15})['createdIds'][0]
            current = next(row for row in tokens() if row['id'] == token_id)
            resource('tokens', 'vision', {'mapId': scene, 'tokenIds': [token_id],
                'enabled': True, 'range': 14})
            player = client('player')
            player.goto(f'/game/{campaign}')
            game(player)
            player.wait_for_function('id=>gravewrightMaps.current.id===id', arg=scene)
            record('initial-masked-effects-and-dynamic-vision')

            # A native dry run must leave the live board and real token intact.
            gm.locator('.game-menubar__layer').get_by_text('Walls', exact=True).click()
            gm.locator('[data-dock-tool=automation]').click()
            gm.locator('[data-automation-view=doors]').click()
            controls = gm.locator('[data-scene-controls]')
            expect(controls).to_have_attribute('aria-busy', 'false')
            network = gm.request.get(f'/api/maps/{scene}/automation/network').json()
            owner = next(row for row in network['elements'] if row['name'] == 'Synthetic portal 0')['id']
            controls.locator(f'[data-scene-controls-element="{owner}"]').click()
            controls.locator('[data-scene-controls-test]').click()
            rehearsal = gm.locator('[data-playtest]')
            expect(rehearsal).to_be_visible()
            rehearsal.locator('[data-playtest-event]').select_option('presence:enter')
            rehearsal.locator('[data-playtest-token]').select_option(token_id)
            with gm.expect_response(lambda response: response.request.method == 'POST'
                                    and '/automation/test/' in response.url) as tested:
                rehearsal.locator('[data-playtest-run]').click()
            assert tested.value.ok, tested.value.text()
            rehearsal.locator('[data-playtest-close]').click()
            expect(rehearsal).to_have_count(0)
            gm.locator('[data-automation-close]').click()
            record('live-board-survives-closing-native-rehearsal')

            # Exercise the renderer's real same-URL release/reacquire boundary.
            # Both calls complete in one browser task, before another frame;
            # Pixi's asynchronous last-reference unload can still be pending.
            native_tokens = tokens()
            pieces = [{'key': row['id'], 'x': (row['gridX'] + .5) * 70,
                       'y': (row['gridY'] + .5) * 70, 'size': 70,
                       'height': 70, 'label': row['name'], 'imageUrl': uploaded.json()['url'],
                       'accent': '#79c39a', 'rotation': 0, 'selected': True, 'bars': [], 'conditions': []}
                      for row in native_tokens]
            for page in clients.values():
                page.evaluate('''async pieces=>{
                  await gravewrightMaps.board.update({pieces});
                  await new Promise(requestAnimationFrame);
                  await gravewrightMaps.board.update({pieces:[]});
                  await gravewrightMaps.board.update({pieces});
                  await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
                }''', pieces)
            record('same-url-token-art-reacquired-during-asynchronous-unload')

            for index in range(8):
                for x, y in ((5, 12), (8, 8)) if index % 2 == 0 else ((28, 12), (23, 8)):
                    current = next(row for row in tokens() if row['id'] == token_id)
                    resource('tokens', 'move', {'mapId': scene, 'id': token_id,
                        'expectedVersion': current['version'], 'gridX': x, 'gridY': y}, player)
                expected_x = 23 if index % 2 == 0 else 8
                current = next(row for row in tokens() if row['id'] == token_id)
                assert expected_x <= current['gridX'] < expected_x + 3, current
                player.wait_for_function('''a=>__renderLifetime.layers.some(s=>s.sceneId===a.scene&&
                  s.vision?.some(v=>v.x>=a.x*70&&v.x<(a.x+3)*70))''',
                    arg={'scene': scene, 'id': token_id, 'x': expected_x})
                record(f'portal-hop-{index}')
                if index % 2 == 0:
                    # Unloading the last matching token and reacquiring it
                    # during rapid presence/vision updates must not revive a
                    # texture whose asynchronous unload is still pending.
                    resource('tokens', 'hidden', {'mapId': scene,
                        'tokenIds': [token_id, twin], 'hidden': True})
                    resource('tokens', 'hidden', {'mapId': scene,
                        'tokenIds': [token_id, twin], 'hidden': False})
                    record(f'shared-token-art-reacquired-{index}')
                if index % 2:
                    for page in clients.values():
                        page.set_viewport_size({'width': 1230 if index % 4 else 1440, 'height': 840})
                    record(f'resize-after-hop-{index}')

            for role, page in clients.items():
                board = page.locator('.game-board canvas').first
                before = Image.open(BytesIO(board.screenshot())).convert('RGB')
                page.wait_for_timeout(300)
                after = Image.open(BytesIO(board.screenshot())).convert('RGB')
                assert ImageChops.difference(before, after).getbbox(), f'{role} masked effects stopped animating'
            cases.append({'case': 'both-gpu-boards-continue-to-animate-after-repeated-portals'})
        finally:
            (output / 'observations.json').write_text(json.dumps({'cases': cases, 'pageErrors': errors,
                'nativeDialogs': dialogs, 'probes': {role: page.evaluate('window.__renderLifetime')
                    for role, page in clients.items()}}, indent=2), encoding='utf-8')
            for context in reversed(contexts):
                context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': cases, 'pageErrors': errors, 'nativeDialogs': dialogs}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
