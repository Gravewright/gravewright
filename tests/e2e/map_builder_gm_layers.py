"""Exercise GM-only Empty Objects and reversible image-layer moves.

The scenario uses the actual layer tabs, image context menus and player token
drags on two live boards. All artwork, sessions and persisted data are synthetic
and stay in the disposable installation-local fixture.
"""
from __future__ import annotations

from copy import deepcopy
from io import BytesIO
import json
import time
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder_asset_removal import BuilderReview
from map_builder_combination_matrix import behavior
from map_builder_playtest import chain, node
from map_builder_reference import close_panel, upload_asset, wait_ready


def check_browser(base, seed, output, executable):
    from PIL import Image
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    cases, errors, dialogs, observations = [], [], [], []
    clients, scene = {}, None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))
        contexts = []

        def client(role):
            context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
            context.add_cookies([{**seed['sessions'][role], 'url': base}])
            context.add_init_script('''window.__gmLayerUpdates=[];
              addEventListener('gravewright:map-layers',event=>window.__gmLayerUpdates.push(event.detail));''')
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append({'role': role, 'message': str(error)}))
            page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
            contexts.append(context)
            clients[role] = page
            return page

        gm = client('gm')
        review = BuilderReview(gm, campaign)

        def game(page):
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def layers(page):
            response = page.request.get(f'/api/maps/{scene}/state')
            assert response.ok, response.text()
            return response.json()

        def image(identifier):
            return next(row for row in layers(gm)['images'] if row['id'] == identifier)

        def tab(label):
            gm.locator('.game-menubar__layer').get_by_text(label, exact=True).click()

        def point(page, x, y):
            return page.evaluate('''p=>{
              const r=document.querySelector('.game-board__surface').getBoundingClientRect(),v=gravewrightMaps.board.viewport();
              return {x:r.x+v.x+p.x*v.scale,y:r.y+v.y+p.y*v.scale};
            }''', {'x': x, 'y': y})

        def selected(identifier):
            return gm.locator(f'[data-selected-object="image:{identifier}"]')

        def menu_for(row):
            at = point(gm, row['x'], row['y'])
            gm.mouse.click(at['x'], at['y'], button='right')
            menu = gm.locator('.directory-context-menu')
            expect(menu).to_be_visible()
            return menu

        def rgb(page, row):
            page.mouse.move(1, 1)
            at = point(page, row['x'], row['y'])
            with Image.open(BytesIO(page.screenshot())) as shot:
                return shot.convert('RGB').getpixel((round(at['x']), round(at['y'])))

        def artwork(page, row, expected):
            deadline = time.monotonic() + 10
            while True:
                pixel = rgb(page, row)
                is_blue = pixel[2] > pixel[0] + 70
                is_orange = pixel[0] > pixel[2] + 70
                if expected == 'blue' and is_blue or expected == 'orange' and is_orange:
                    return pixel
                if time.monotonic() >= deadline:
                    raise AssertionError({'expected': expected, 'pixel': pixel, 'id': row['id']})
                page.wait_for_timeout(100)

        def diagnostics():
            report = {'cases': cases, 'observations': observations, 'pageErrors': errors,
                      'nativeDialogs': dialogs}
            if scene:
                report['gmState'] = layers(gm)
            for role, page in clients.items():
                report[role] = page.evaluate('''()=>({url:location.href,updates:window.__gmLayerUpdates,
                  controls:[...document.querySelectorAll('[data-smart-image-id]')].map(row=>row.dataset.smartImageId),
                  selected:[...document.querySelectorAll('[data-selected-object]')].map(row=>row.dataset.selectedObject)})''')
            (output / 'observations.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

        try:
            gm.goto(review.builder)
            wait_ready(gm)
            gm.locator('[data-builder-quick-name]').fill('Synthetic GM object layers')
            gm.locator('[data-builder-quick-name]').press('Tab')
            blue = upload_asset(gm, 'decoration', 'Synthetic public blue.png', harness.artwork('#245dc9'))['id']
            orange = upload_asset(gm, 'decoration', 'Synthetic public orange.png', harness.artwork('#ed7822'))['id']
            expect(gm.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved', timeout=20_000)
            project = review.project(gm.evaluate("new URL(location.href).searchParams.get('project')"))
            document = deepcopy(project['document'])
            layer = document['layers'][0]['id']
            empty, ordinary, lever, torch, lamp = (str(uuid4()) for _ in range(5))
            graphs = {event: chain(event,
                [node('sprite', 'sprite', appearance='asset', assetId=asset)],
                [node('target', 'reference', targetId=ordinary)],
                [('target', 'door', 'sprite', 'target')])
                for event, asset in (('presence:enter', orange), ('presence:exit', blue))}
            document['decorations'] = [
                {'id': empty, 'layerId': layer, 'assetId': None, 'empty': True,
                 'name': 'Synthetic hidden area controller', 'x': 8, 'y': 8, 'width': 4, 'height': 3,
                 'rotation': 0, 'lever': {'state': 'off'}, 'blueprint': behavior('lever', graphs)},
                {'id': ordinary, 'layerId': layer, 'assetId': blue,
                 'x': 16, 'y': 8, 'width': 2, 'height': 2, 'rotation': 0},
                {'id': lever, 'layerId': layer, 'assetId': blue,
                 'x': 22, 'y': 5, 'width': 2, 'height': 2, 'rotation': 0,
                 'lever': {'state': 'off'}, 'blueprint': behavior('lever', {})},
                {'id': torch, 'layerId': layer, 'assetId': blue,
                 'x': 26, 'y': 5, 'width': 2, 'height': 2, 'rotation': 0,
                 'torch': {'state': 'off', 'lit': False, 'lightId': lamp},
                 'blueprint': behavior('torch', {})},
            ]
            document['lights'] = [{'id': lamp, 'layerId': layer, 'x': 27, 'y': 6,
                'brightRadius': 2, 'dimRadius': 3, 'color': '#ffbb66', 'intensity': .8,
                'enabled': False, 'rotation': 0, 'angle': 360, 'animation': 'none'}]
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
            native = layers(gm)
            owner = next(row for row in native['images'] if row.get('empty'))
            target = next(row for row in native['images']
                          if not row.get('empty') and not row.get('lever') and not row.get('torch'))
            native_lever = next(row for row in native['images'] if row.get('lever') and not row.get('empty'))
            native_torch = next(row for row in native['images'] if row.get('torch'))
            assert owner['layer'] == owner['lever']['baseLayer'] == 'gm-image-layer', owner
            assert owner['src'] == '' and owner['asset_id'] is None, owner
            cases.append({'case': 'generated-empty-object-is-persisted-on-gm-image-layer', 'id': owner['id']})

            gm.evaluate('''a=>gravewrightRealtime.mapCommand('update',{
              mapId:a.scene,version:a.version,settings:{visibility:'players'}})''',
                {'scene': scene, 'version': project['sceneVersion']})
            gm.evaluate("scene=>gravewrightRealtime.mapCommand('activate',{mapId:scene})", scene)
            gm.evaluate('''scene=>gravewrightRealtime.mapCommand('objects',{
              mapId:scene,area:'lighting',action:'update',data:{mode:'none',darkness:0,lights_out:false}})''', scene)
            actor = gm.evaluate('''()=>gravewrightRealtime.resourceCommand('actors','actor.create',
              {name:'Synthetic GM area traveler'})''')
            gm.evaluate('''id=>gravewrightRealtime.resourceCommand('actors','actor.permissions',
              {id,permissions:{default:'owner'}})''', actor['id'])
            gm.evaluate('''a=>gravewrightRealtime.resourceCommand('tokens','place',
              {mapId:a.scene,actorId:a.actor,gridX:5,gridY:9})''', {'scene': scene, 'actor': actor['id']})
            tab('Game')
            player = client('player')
            player.goto(f'/game/{campaign}')
            game(player)
            player.wait_for_function('id=>gravewrightMaps.current.id===id', arg=scene)

            def no_empty_game_controls():
                expect(gm.locator(f'[data-smart-image-id="{owner["id"]}"]')).to_have_count(0)
                expect(player.locator(f'[data-smart-image-id="{owner["id"]}"]')).to_have_count(0)
                assert all(not row.get('empty') for row in layers(player)['images'])
                at = point(gm, owner['x'], owner['y'])
                gm.mouse.click(at['x'], at['y'])
                expect(selected(owner['id'])).to_have_count(0)

            no_empty_game_controls()
            gm.screenshot(path=str(output / 'empty-faint-game-gm.png'))
            player.screenshot(path=str(output / 'empty-absent-game-player.png'))
            cases.append({'case': 'empty-object-has-no-game-controls-hit-target-or-player-payload'})
            tab('GM')
            expect(gm.locator(f'[data-smart-image-id="{owner["id"]}"][data-smart-image-action="interact"]')).to_have_count(1)
            menu = menu_for(owner)
            expect(selected(owner['id'])).to_have_count(1)
            expect(menu.get_by_role('button', name='Move to image layer', exact=True)).to_have_count(0)
            gm.screenshot(path=str(output / 'empty-selectable-on-gm.png'))
            gm.keyboard.press('Escape')
            cases.append({'case': 'empty-object-is-selectable-on-gm-and-cannot-be-sent-to-public-image-layer'})

            # Native creation also normalizes a legacy/public layer request.
            extra = gm.evaluate('''scene=>gravewrightRealtime.mapCommand('objects',{
              mapId:scene,area:'images',action:'create',data:{empty:true,asset_id:null,
                src:'',natural_width:70,natural_height:70,x:2170,y:1400,
                name:'Synthetic native empty',layer:'map',
                lever:{state:'off',baseAssetId:null,baseLayer:'map',width:70,height:70}}})''', scene)['image']
            assert extra['layer'] == extra['lever']['baseLayer'] == 'gm-image-layer', extra
            assert all(row['id'] != extra['id'] for row in layers(player)['images'])
            cases.append({'case': 'native-empty-create-normalizes-public-layer-request-to-gm'})
            tab('Game')

            def roundtrip(row, label, expected='blue', start='Game'):
                tab(start)
                current = image(row['id'])
                before = {key: deepcopy(current.get(key)) for key in
                          ('asset_id', 'sprite', 'spriteBase', 'lever', 'torch', 'x', 'y', 'scale')}
                artwork(player, row, expected)
                menu_for(current).get_by_role('button', name='Move to GM image layer', exact=True).click()
                player.wait_for_function('''id=>window.__gmLayerUpdates.some(state=>
                  state.images && !state.images.some(image=>image.id===id))''', arg=row['id'])
                hidden = image(row['id'])
                assert hidden['layer'] == 'gm-image-layer', hidden
                assert all(item['id'] != row['id'] for item in layers(player)['images'])
                pixel = rgb(player, row)
                assert abs(pixel[2] - pixel[0]) < 70, pixel
                tab('Game')
                at = point(gm, row['x'], row['y'])
                gm.mouse.click(at['x'], at['y'])
                expect(selected(row['id'])).to_have_count(0)
                tab('Images')
                # Three public images exist in this fixture. Neither Empty
                # controller nor the image just made private belongs here.
                expect(gm.locator('.image-workspace__image')).to_have_count(2)
                tab('GM')
                menu = menu_for(hidden)
                expect(selected(row['id'])).to_have_count(1)
                menu.get_by_role('button', name='Move to image layer', exact=True).click()
                public = image(row['id'])
                assert public['layer'] == 'map', public
                # Explicit layer changes update the remembered base layer;
                # artwork and all other mechanism metadata stay intact.
                for key in before:
                    assert public.get(key) == before[key], (label, key, before[key], public.get(key))
                player.wait_for_function('''a=>window.__gmLayerUpdates.some(state=>
                  state.images?.some(image=>image.id===a.id&&image.asset_id===a.asset&&image.layer==='map'))''',
                    arg={'id': row['id'], 'asset': public['asset_id']})
                artwork(player, row, expected)
                tab('Game')
                if public.get('lever') or public.get('torch'):
                    expect(gm.locator(f'[data-smart-image-id="{row["id"]}"][data-smart-image-action="interact"]')).to_have_count(1)
                    expect(player.locator(f'[data-smart-image-id="{row["id"]}"][data-smart-image-action="interact"]')).to_have_count(1)
                cases.append({'case': label, 'id': row['id'], 'publicPixel': rgb(player, row)})
                for page in clients.values():
                    page.evaluate('window.__gmLayerUpdates=[]')

            for row, kind in ((target, 'ordinary-image'), (native_lever, 'lever'), (native_torch, 'torch')):
                roundtrip(row, f'{kind}-can-move-game-to-gm-and-back-through-real-tabs-and-context-menus')
            roundtrip(target, 'images-tab-can-send-image-to-gm-and-gm-tab-can-return-it', start='Images')

            def drag_to(x):
                hero = player.get_by_role('button', name='Token: Synthetic GM area traveler', exact=True)
                expect(hero).to_be_visible()
                box = hero.bounding_box()
                at = point(player, (x + .5) * 70, 9.5 * 70)
                player.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                player.mouse.down()
                player.mouse.move(at['x'], at['y'], steps=12)
                player.mouse.up()
                expect(hero).to_have_attribute('x', str(x * 70), timeout=10_000)

            def area_change(x, asset, label):
                for page in clients.values():
                    page.evaluate('window.__gmLayerUpdates=[]')
                started = time.monotonic()
                drag_to(x)
                pixels = {}
                for role, page in clients.items():
                    page.wait_for_function('''a=>window.__gmLayerUpdates.some(state=>state.images?.some(image=>
                      image.id===a.id&&image.asset_id===a.asset))''', arg={'id': target['id'], 'asset': asset})
                    pixels[role] = artwork(page, target, 'orange' if asset == orange else 'blue')
                elapsed = (time.monotonic() - started) * 1000
                no_empty_game_controls()
                assert image(owner['id'])['lever']['state'] == 'off'
                observations.append({'case': label, 'elapsedIncludingScreenshotsMs': round(elapsed, 2), 'pixels': pixels})
                cases.append({'case': label, 'clients': ['gm', 'player']})

            area_change(9, orange, 'player-entry-runs-hidden-empty-area-sprite-action-on-both-live-boards')
            roundtrip(target, 'active-sprite-override-survives-gm-hide-and-return', expected='orange')
            area_change(5, blue, 'player-exit-restores-image-with-empty-hidden-on-gm-layer')
            area_change(9, orange, 'player-reentry-still-runs-after-image-layer-roundtrips')

            # Reapplying the source uses the existing scene and keeps controller
            # privacy, player tokens and an active sprite override.
            gm.goto(review.builder + '?project=' + project['id'])
            wait_ready(gm)
            gm.locator('[data-builder-quick-name]').fill('Synthetic GM object layers updated')
            gm.locator('[data-builder-quick-name]').press('Tab')
            expect(gm.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved', timeout=20_000)
            source = review.project(project['id'])
            assert source['document']['name'].endswith('updated')
            close_panel(gm)
            expect(gm.locator('[data-builder-generate]')).to_have_text('Update scene')
            with gm.expect_response(lambda response: response.url.endswith('/update')) as updated:
                gm.locator('[data-builder-generate]').click()
            assert updated.value.ok, updated.value.text()
            game(gm)
            assert review.project(project['id'])['sceneId'] == scene
            tab('Game')
            assert image(owner['id'])['layer'] == 'gm-image-layer'
            assert image(target['id'])['asset_id'] == orange
            assert image(extra['id'])['layer'] == 'gm-image-layer'
            no_empty_game_controls()
            cases.append({'case': 'source-autosave-and-same-scene-update-preserve-gm-empty-native-extra-and-active-sprite'})
            gm.reload()
            game(gm)
            tab('Game')
            no_empty_game_controls()
            tab('GM')
            expect(gm.locator(f'[data-smart-image-id="{owner["id"]}"][data-smart-image-action="interact"]')).to_have_count(1)
            gm.screenshot(path=str(output / 'persisted-empty-gm-layer.png'))
            cases.append({'case': 'gm-only-empty-object-persists-after-reload'})
            diagnostics()
        except Exception:
            diagnostics()
            for role, page in clients.items():
                page.screenshot(path=str(output / f'failure-{role}.png'), full_page=True)
            raise
        finally:
            for context in reversed(contexts):
                context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': cases, 'observations': observations,
            'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Generated two-color artwork and a disposable player-owned actor.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
