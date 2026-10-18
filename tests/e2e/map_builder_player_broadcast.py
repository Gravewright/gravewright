"""Broadcast a newly generated private MapBuilder scene to an already seated player.

Real generation and scene-directory controls run against the common disposable
fixture. Synthetic floor and image pixels, public asset access, private layers,
blueprint filtering and a player reload are verified without operator data.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder_asset_removal import BuilderReview
from map_builder_combination_matrix import behavior
from map_builder_reference import close_panel, upload_asset, wait_ready


FLOOR = (56, 112, 80)
PUBLIC = (36, 93, 201)
BASE_SERVE = harness.serve


def serve(fixture, port):
    source = os.environ.get('GRAVEWRIGHT_E2E_MAP_SERVICES_SOURCE')
    if source:
        import django
        django.setup()
        from gravewright.maps import services
        # A saved source is loaded only into this disposable fixture process.
        exec(compile(Path(source).read_text(encoding='utf-8'), source, 'exec'), services.__dict__)
    BASE_SERVE(fixture, port)


def check_browser(base, seed, output, executable):
    from PIL import Image
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    cases, errors, dialogs, contexts, clients, observations = [], [], [], [], {}, {}
    scene = None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))

        def client(role):
            context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
            context.add_cookies([{**seed['sessions'][role], 'url': base}])
            context.add_init_script('''window.__broadcastUpdates={maps:[],layers:[]};
              addEventListener('gravewright:maps',e=>__broadcastUpdates.maps.push(e.detail));
              addEventListener('gravewright:map-layers',e=>__broadcastUpdates.layers.push(e.detail));''')
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append({'role': role, 'message': str(error), 'stack': error.stack}))
            page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
            contexts.append(context)
            clients[role] = page
            return page

        gm, player = client('gm'), client('player')
        review = BuilderReview(gm, campaign)

        def game(page):
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def projection(page):
            response = page.request.get(f'/api/containers/{campaign}/scenes')
            assert response.ok, response.text()
            return response.json()

        def current(page, identifier):
            page.wait_for_function('id=>gravewrightMaps.current?.id===id && !!gravewrightMaps.board?.viewport()', arg=identifier)

        def state(page):
            response = page.request.get(f'/api/maps/{scene}/state')
            assert response.ok, response.text()
            return response.json()

        def rendered(page, name):
            close = page.locator('[data-map-panel=close]')
            if close.is_visible():
                close.click()
            page.mouse.move(1, 1)
            samples = [(160, 160, FLOOR), (352, 96, PUBLIC), (352, 224, FLOOR)]
            deadline, actual = time.monotonic() + 10, []
            while time.monotonic() < deadline:
                points = page.evaluate('''rows=>{
                  const r=document.querySelector('.game-board__surface').getBoundingClientRect(),v=gravewrightMaps.board.viewport();
                  return rows.map(([x,y])=>({x:r.x+v.x+x*v.scale,y:r.y+v.y+y*v.scale}));
                }''', samples)
                with Image.open(BytesIO(page.screenshot())) as shot, shot.convert('RGB') as image:
                    actual = [image.getpixel((round(point['x']), round(point['y']))) for point in points]
                if all(max(abs(left - right) for left, right in zip(pixel, sample[2])) < 18
                       for pixel, sample in zip(actual, samples)):
                    break
                page.wait_for_timeout(100)
            assert all(max(abs(left - right) for left, right in zip(pixel, sample[2])) < 18
                       for pixel, sample in zip(actual, samples)), {'samples': samples, 'actual': actual, 'points': points}
            page.screenshot(path=str(output / f'{name}.png'))
            return {'pixels': actual, 'viewport': page.evaluate('gravewrightMaps.board.viewport()')}

        def diagnostics():
            for role, page in clients.items():
                observations[role] = page.evaluate('''()=>({url:location.href,current:window.gravewrightMaps?.current,
                  updates:window.__broadcastUpdates,empty:document.querySelector('.game-table__empty-scene')?.checkVisibility()})''')
            (output / 'observations.json').write_text(json.dumps({
                'cases': cases, 'observations': observations, 'pageErrors': errors, 'nativeDialogs': dialogs},
                indent=2), encoding='utf-8')

        try:
            player.goto(f'/game/{campaign}')
            game(player)
            current(player, seed['broadcastScene'])
            initial_projection = projection(player)
            assert initial_projection['activeMapId'] == seed['broadcastScene']
            cases.append({'case': 'player-is-seated-on-existing-broadcast-before-generation'})

            gm.goto(review.builder)
            wait_ready(gm)
            gm.locator('[data-builder-quick-name]').fill('Synthetic player broadcast map')
            gm.locator('[data-builder-quick-name]').press('Tab')
            floor = upload_asset(gm, 'floor', 'Synthetic public floor.png', harness.artwork('#387050'))['id']
            public = upload_asset(gm, 'decoration', 'Synthetic public lever.png', harness.artwork('#245dc9'))['id']
            private = upload_asset(gm, 'decoration', 'Synthetic private GM artwork.png', harness.artwork('#cd25ab'))['id']
            expect(gm.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved', timeout=20_000)
            project = review.project(gm.evaluate("new URL(location.href).searchParams.get('project')"))
            document = deepcopy(project['document'])
            layer = document['layers'][0]['id']
            document.update(columns=8, rows=6, cellSize=64, background='#18222c',
                floors=[{'id': str(uuid4()), 'layerId': layer, 'assetId': floor,
                    'x': 0, 'y': 0, 'width': 8, 'height': 6, 'rotation': 0}],
                decorations=[{'id': str(uuid4()), 'layerId': layer, 'assetId': public,
                    'x': 5, 'y': 1, 'width': 1, 'height': 1, 'rotation': 0,
                    'lever': {'state': 'off'}, 'blueprint': behavior('lever', {})}])
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
            current(gm, scene)
            generated_scene = next(row for row in projection(gm)['maps'] if row['id'] == scene)
            assert generated_scene['visibility'] == 'gm', generated_scene
            assert projection(gm)['activeMapId'] == seed['broadcastScene']
            assert projection(player) == initial_projection, 'generation must preserve the public broadcast'
            assert player.evaluate('gravewrightMaps.current?.id') == seed['broadcastScene']
            assert player.request.get(f'/api/maps/{scene}/state').status == 404
            assert player.request.get(f'/api/maps/{scene}/tiles/0/0/0.webp').status == 404
            assert player.request.get(f'/game/map-assets/{public}').status == 404
            cases.append({'case': 'generation-keeps-scene-private-and-existing-player-broadcast-unchanged'})

            private_image = gm.evaluate('''a=>gravewrightRealtime.mapCommand('objects',{
              mapId:a.scene,area:'images',action:'create',data:{asset_id:a.asset,
                x:352,y:224,scale:.5,layer:'gm-image-layer'}})''', {'scene': scene, 'asset': private})['image']
            gm_state = state(gm)
            assert any('blueprint' in row for row in gm_state['images']), 'fixture includes a private authoring graph'
            assert any(row['id'] == private_image['id'] for row in gm_state['images'])
            assert gm.request.get(f'/game/map-assets/{private}').ok

            gm.evaluate('gravewrightMaps.showDirectory()')
            for identifier in (seed['parentFolder'], seed['folder']):
                toggle = gm.locator(f'[data-map-folder="{identifier}"] > header > .gw-folder__toggle')
                if toggle.get_attribute('aria-expanded') != 'true':
                    toggle.click()
            gm.locator(f'.game-directory__scene[data-scene-id="{scene}"]').click(button='right')
            gm.get_by_role('menuitem', name='Activate for players', exact=True).click()
            expect(gm.locator(f'[data-scene-id="{scene}"] [data-broadcast]')).to_be_visible()
            active_projection = projection(player)
            observations['afterActivateProjection'] = active_projection
            assert active_projection['activeMapId'] == scene and len(active_projection['maps']) == 1, (
                'Activating a generated GM scene must expose the active scene to the player', active_projection)
            assert active_projection['maps'][0]['visibility'] == 'players'
            current(player, scene)
            player.wait_for_function('id=>__broadcastUpdates.maps.some(s=>s.activeMapId===id)', arg=scene)
            samples = rendered(player, 'connected-player-generated-map')
            cases.append({'case': 'real-activation-promotes-private-scene-and-connected-player-renders-floor-and-art', **samples})

            public_state = state(player)
            assert all(row['id'] != private_image['id'] and row.get('layer') not in ('gm', 'gm-image-layer')
                       for row in public_state['images'])
            assert 'blueprint' not in json.dumps(public_state)
            assert private not in json.dumps(public_state)
            assert all('builderProjectId' not in row for row in active_projection['maps'])
            assert player.request.get(f'/game/map-assets/{public}').ok
            assert player.request.get(f'/game/map-assets/{private}').status == 404
            assert player.request.get(f'/api/maps/{scene}/tiles/0/0/0.webp').ok
            assert player.request.get(review.api + '/projects/' + project['id']).status == 403
            assert player.request.get(f'/api/maps/{scene}/automation').status == 404
            delivered = player.evaluate('__broadcastUpdates.layers')
            assert private not in json.dumps(delivered) and 'blueprint' not in json.dumps(delivered)
            cases.append({'case': 'broadcast-permits-public-tiles-and-art-while-filtering-GM-art-blueprints-and-source-project'})

            player.reload()
            game(player)
            current(player, scene)
            samples = rendered(player, 'reloaded-player-generated-map')
            cases.append({'case': 'reloaded-player-renders-the-same-broadcast-map', **samples})
            assert not errors, errors
            assert not dialogs, dialogs
        finally:
            diagnostics()
            for context in contexts:
                context.close()
            browser.close()
    return {'passed': True, 'cases': cases, 'pageErrors': errors, 'nativeDialogs': dialogs,
        'data': 'Only synthetic floor PNGs, images, projects and disposable campaign state.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--services-source', type=Path,
        help='Saved maps/services.py source to load only in the isolated fixture process')
    options, remaining = parser.parse_known_args()
    if options.services_source:
        os.environ['GRAVEWRIGHT_E2E_MAP_SERVICES_SOURCE'] = str(options.services_source.resolve())
    sys.argv = [sys.argv[0], *remaining]
    harness.__file__ = __file__
    harness.serve = serve
    harness.check_browser = check_browser
    harness.main()
