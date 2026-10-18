"""Author an area event that changes another object's image directly.

The disposable fixture checks every owner's complete node catalog, typed sprite
targets, project persistence, scene replacement and actual player token drags.
Both connected boards must receive and render the alternate artwork without
running an interaction handler or changing the target mechanism's state.
"""
from __future__ import annotations

from copy import deepcopy
from io import BytesIO
import json
import time
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import builder_sidebar, builder_tool, builder_workspace
from map_builder_asset_removal import BuilderReview
from map_builder_combination_matrix import behavior
from map_builder_reference import close_panel, upload_asset, wait_ready


def check_browser(base, seed, output, executable):
    from PIL import Image
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    cases, errors, dialogs, measurements = [], [], [], []
    clients, contexts, scene = {}, [], None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))

        def client(role):
            context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
            context.add_cookies([{**seed['sessions'][role], 'url': base}])
            context.add_init_script('''window.__spriteLayers=[];
              addEventListener('gravewright:map-layers',event=>window.__spriteLayers.push(event.detail));''')
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append({'role': role, 'message': str(error)}))
            page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
            clients[role] = page
            contexts.append(context)
            return page

        gm = client('gm')
        review = BuilderReview(gm, campaign)

        def diagnostics():
            (output / 'measurements.json').write_text(json.dumps({
                'cases': cases, 'measurements': measurements, 'pageErrors': errors,
                'nativeDialogs': dialogs, 'layers': {
                    role: page.evaluate('window.__spriteLayers') for role, page in clients.items()},
                'server': gm.request.get(f'/api/maps/{scene}/state').json() if scene else None,
            }, indent=2), encoding='utf-8')

        def saved():
            expect(gm.locator('[data-map-builder]')).to_have_attribute(
                'data-save-state', 'saved', timeout=20_000)
            return review.project(gm.evaluate("new URL(location.href).searchParams.get('project')"))

        def game(page):
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def editor(identifier, collection='decorations'):
            builder_tool(gm, 'select')
            builder_workspace(gm)
            point = gm.locator(f'[data-builder-{collection}] [data-object-id="{identifier}"]').evaluate('''group=>{
              const b=group.getBBox(),p=new DOMPoint(b.x+b.width*.2,b.y+b.height*.5)
                .matrixTransform(group.getScreenCTM());return [p.x,p.y];}''')
            if collection == 'doors':
                gm.mouse.dblclick(*point)
            else:
                gm.mouse.click(*point)
                builder_sidebar(gm, 'selection')
                gm.locator('[data-builder-edit-behavior]').click()
            modal = gm.locator('[data-smart-object-modal]')
            expect(modal).to_be_visible()
            return modal

        def node_ids(modal):
            return set(modal.locator('[data-blueprint-node]').evaluate_all(
                'nodes=>nodes.map(node=>node.dataset.blueprintNode)'))

        def card(modal, identifier):
            return modal.locator(f'[data-blueprint-node="{identifier}"]')

        def new_node(modal, kind):
            before = node_ids(modal)
            modal.locator('[data-blueprint-add]').click()
            choice = modal.locator(f'[data-blueprint-pick-type="{kind}"]')
            expect(choice).to_be_visible()
            expect(choice).to_be_enabled()
            choice.click()
            identifier, = node_ids(modal) - before
            return identifier

        try:
            gm.goto(review.builder)
            wait_ready(gm)
            gm.locator('[data-builder-quick-name]').fill('Synthetic direct sprite targets')
            gm.locator('[data-builder-quick-name]').press('Tab')
            blue = upload_asset(gm, 'decoration', 'Synthetic ordinary blue.png', harness.artwork('#245dc9'))['id']
            orange = upload_asset(gm, 'decoration', 'Synthetic ordinary orange.png', harness.artwork('#ed7822'))['id']
            project = saved()
            document = deepcopy(project['document'])
            layer = document['layers'][0]['id']
            empty, ordinary, lever, torch, door, region, lamp = (str(uuid4()) for _ in range(7))
            document['decorations'] = [
                {'id': empty, 'layerId': layer, 'assetId': None, 'empty': True,
                 'name': 'Synthetic sprite area', 'x': 8, 'y': 8, 'width': 4, 'height': 3,
                 'rotation': 0, 'lever': {'state': 'off'}, 'blueprint': behavior('lever', {})},
                {'id': ordinary, 'layerId': layer, 'assetId': blue,
                 'x': 16, 'y': 8, 'width': 2, 'height': 2, 'rotation': 0},
                {'id': lever, 'layerId': layer, 'assetId': blue,
                 'x': 22, 'y': 5, 'width': 2, 'height': 2, 'rotation': 0,
                 'lever': {'state': 'off'}, 'blueprint': behavior('lever', {})},
                {'id': torch, 'layerId': layer, 'assetId': blue,
                 'x': 26, 'y': 5, 'width': 2, 'height': 2, 'rotation': 0,
                 'torch': {'state': 'off', 'lit': False, 'lightId': lamp}, 'blueprint': behavior('torch', {})},
            ]
            document['doors'] = [{'id': door, 'layerId': layer, 'assetId': None,
                'x1': 22, 'y1': 12, 'x2': 24, 'y2': 12, 'thickness': .4,
                'state': 'closed', 'blueprint': behavior('door', {})}]
            document['regions'] = [{'id': region, 'layerId': layer, 'x': 27, 'y': 12,
                'width': 3, 'height': 3, 'name': 'Synthetic region catalog',
                'enabled': True, 'blueprint': behavior('region', {})}]
            document['lights'] = [{'id': lamp, 'layerId': layer, 'x': 27, 'y': 6,
                'brightRadius': 2, 'dimRadius': 3, 'color': '#ffbb66', 'intensity': .8,
                'enabled': False, 'rotation': 0, 'angle': 360, 'animation': 'none'}]
            project = review.store(project['id'], project['version'], project['folderId'], document)
            gm.goto(review.builder + '?project=' + project['id'])
            wait_ready(gm)
            expected_catalog = set(gm.evaluate('''async()=>{
              const {blueprintContract}=await import('/static/gravewright_maps/builder/blueprint-model.js');
              return Object.entries(blueprintContract.nodes)
                .filter(([,node])=>!['element','event'].includes(node.category)).map(([type])=>type);
            }'''))
            for identifier, collection, kind in ((empty, 'decorations', 'empty'),
                    (lever, 'decorations', 'lever'), (torch, 'decorations', 'torch'),
                    (door, 'doors', 'door'), (region, 'regions', 'region')):
                modal = editor(identifier, collection)
                modal.locator('[data-blueprint-add]').click()
                actual = set(modal.locator('[data-blueprint-pick-type]').evaluate_all(
                    'items=>items.map(item=>item.dataset.blueprintPickType)'))
                assert 'sprite' in actual and 'setAppearance' in actual, (kind, actual)
                assert actual == expected_catalog, (kind, actual ^ expected_catalog)
                expect(modal.locator('[data-blueprint-pick-type="sprite"]')).to_be_enabled()
                gm.keyboard.press('Escape')
                modal.locator('[data-blueprint-close]').click()
                cases.append({'case': 'complete-identical-node-catalog', 'owner': kind,
                              'nodes': sorted(actual)})

            # Build both flows with the actual Add node and typed input pickers.
            modal = editor(empty)
            authored = {}
            for event, artwork in (('presence:enter', orange), ('presence:exit', blue)):
                modal.locator(f'[data-blueprint-event="{event}"]').click()
                sprite = new_node(modal, 'sprite')
                sprite_card = card(modal, sprite)
                sprite_card.locator('[data-blueprint-param="appearance"]').select_option('asset')
                sprite_card.locator('[data-blueprint-param="assetId"]').select_option(artwork)
                before = node_ids(modal)
                sprite_card.locator('[data-blueprint-data-input="target"]').click()
                picker = modal.locator('[data-blueprint-node-picker]')
                expect(picker.locator('[data-blueprint-pick-type="reference"]')).to_be_enabled()
                expect(picker.locator('[data-blueprint-pick-type="elementGroup"]')).to_be_enabled()
                picker.locator('[data-blueprint-pick-type="reference"]').click()
                reference, = node_ids(modal) - before
                card(modal, reference).locator('[data-blueprint-param="targetId"]').select_option(ordinary)
                modal.locator('[data-blueprint-fit]').click()
                modal.locator(f'[data-blueprint-event-port="{event}"]').click()
                sprite_card.locator('[data-blueprint-input]').click()
                expect(modal.locator('[data-blueprint-edge]')).to_have_count(2)
                authored[event] = {'sprite': sprite, 'reference': reference, 'asset': artwork}
                gm.screenshot(path=str(output / f'{event.replace(":", "-")}-direct-sprite.png'))
                cases.append({'case': 'ui-authored-area-direct-sprite-target', 'event': event,
                              'target': ordinary, 'asset': artwork})
            modal.locator('[data-blueprint-close]').click()
            project = saved()
            source = next(row for row in project['document']['decorations'] if row['id'] == empty)
            for event, values in authored.items():
                graph = source['blueprint']['graphs'][event]
                assert len(graph['edges']) == 2, graph
                assert next(row for row in graph['nodes'] if row['id'] == values['sprite'])['assetId'] == values['asset']
                assert next(row for row in graph['nodes'] if row['id'] == values['reference'])['targetId'] == ordinary
            cases.append({'case': 'both-direct-sprite-graphs-autosave'})

            gm.reload()
            wait_ready(gm)
            modal = editor(empty)
            for event, values in authored.items():
                modal.locator(f'[data-blueprint-event="{event}"]').click()
                expect(card(modal, values['sprite']).locator('[data-blueprint-param="assetId"]')).to_have_value(values['asset'])
                expect(card(modal, values['reference']).locator('[data-blueprint-param="targetId"]')).to_have_value(ordinary)
                expect(modal.locator('[data-blueprint-edge]')).to_have_count(2)
            modal.locator('[data-blueprint-close]').click()
            close_panel(gm)
            cases.append({'case': 'authored-sprite-targets-survive-reload'})
            with gm.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                gm.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            game(gm)
            project = review.project(project['id'])
            scene = project['sceneId']
            native = gm.request.get(f'/api/maps/{scene}/state').json()
            native_target = next(row for row in native['images']
                                 if row.get('asset_id') == blue and not row.get('lever') and not row.get('torch'))
            native_owner = next(row for row in native['images'] if row.get('empty'))
            assert native_owner['layer'] == native_owner['lever']['baseLayer'] == 'gm-image-layer'
            assert not native_target.get('lever') and not native_target.get('blueprint'), native_target
            for event, values in authored.items():
                graph = native_owner['blueprint']['graphs'][event]
                assert next(row for row in graph['nodes'] if row['id'] == values['reference'])['targetId'] == native_target['id']
            cases.append({'case': 'generation-remaps-sprite-references-to-ordinary-native-image'})

            # Updating the existing scene keeps the same native target and graph.
            gm.goto(review.builder + '?project=' + project['id'])
            wait_ready(gm)
            close_panel(gm)
            expect(gm.locator('[data-builder-generate]')).to_have_text('Update scene')
            with gm.expect_response(lambda response: response.url.endswith('/update')) as updated:
                gm.locator('[data-builder-generate]').click()
            assert updated.value.ok, updated.value.text()
            game(gm)
            project = review.project(project['id'])
            assert project['sceneId'] == scene
            updated_native = gm.request.get(f'/api/maps/{scene}/state').json()
            assert any(row['id'] == native_target['id'] for row in updated_native['images'])
            cases.append({'case': 'scene-update-preserves-native-target-id-and-graphs'})
            gm.evaluate('''a=>gravewrightRealtime.mapCommand('update',{
              mapId:a.scene,version:a.version,settings:{visibility:'players'}})''',
                {'scene': scene, 'version': project['sceneVersion']})
            gm.evaluate("scene=>gravewrightRealtime.mapCommand('activate',{mapId:scene})", scene)
            gm.evaluate('''scene=>gravewrightRealtime.mapCommand('objects',{
              mapId:scene,area:'lighting',action:'update',data:{mode:'none',darkness:0,lights_out:false}})''', scene)
            actor = gm.evaluate('''()=>gravewrightRealtime.resourceCommand('actors','actor.create',
              {name:'Synthetic sprite traveler'})''')
            gm.evaluate('''id=>gravewrightRealtime.resourceCommand('actors','actor.permissions',
              {id,permissions:{default:'owner'}})''', actor['id'])
            token = gm.evaluate('''a=>gravewrightRealtime.resourceCommand('tokens','place',
              {mapId:a.scene,actorId:a.actor,gridX:5,gridY:9})''',
                {'scene': scene, 'actor': actor['id']})['createdIds'][0]
            gm.locator('.game-menubar__layer').get_by_text('Game', exact=True).click()
            player = client('player')
            player.goto(f'/game/{campaign}')
            game(player)
            player.wait_for_function('scene=>gravewrightMaps.current.id===scene', arg=scene)
            assert all(not row.get('empty') for row in player.request.get(f'/api/maps/{scene}/state').json()['images'])
            expect(player.locator(f'[data-smart-image-id="{native_owner["id"]}"]')).to_have_count(0)

            def point(page, x, y):
                page.wait_for_function('!!gravewrightMaps.board?.viewport()')
                return page.evaluate('''p=>{
                  const r=document.querySelector('.game-board__surface').getBoundingClientRect(),v=gravewrightMaps.board.viewport();
                  return {x:r.x+v.x+p.x*v.scale,y:r.y+v.y+p.y*v.scale};
                }''', {'x': x, 'y': y})

            def pixels(page, artwork, role):
                at = point(page, native_target['x'], native_target['y'])
                deadline = time.monotonic() + 10
                while True:
                    with Image.open(BytesIO(page.screenshot())) as image:
                        rgb = image.convert('RGB').getpixel((round(at['x']), round(at['y'])))
                    if artwork == orange and rgb[0] > rgb[2] + 70 or artwork == blue and rgb[2] > rgb[0] + 70:
                        measurements.append({'role': role, 'asset': artwork, 'pixel': rgb})
                        return
                    if time.monotonic() >= deadline:
                        raise AssertionError({'role': role, 'expectedAsset': artwork, 'pixel': rgb})
                    page.wait_for_timeout(100)

            def verify(artwork, label, received=True):
                for role, page in clients.items():
                    if received:
                        page.wait_for_function('''a=>window.__spriteLayers.some(state=>
                          state.images?.some(image=>image.id===a.id&&image.asset_id===a.asset))''',
                            arg={'id': native_target['id'], 'asset': artwork})
                    pixels(page, artwork, role)
                    page.screenshot(path=str(output / f'{label}-{role}.png'))
                current = gm.request.get(f'/api/maps/{scene}/state').json()
                owner = next(row for row in current['images'] if row['id'] == native_owner['id'])
                target = next(row for row in current['images'] if row['id'] == native_target['id'])
                assert owner['lever']['state'] == 'off' and owner.get('empty') and owner['asset_id'] is None, owner
                assert owner['layer'] == 'gm-image-layer', owner
                for page in clients.values():
                    expect(page.locator(f'[data-smart-image-id="{native_owner["id"]}"]')).to_have_count(0)
                assert target['asset_id'] == artwork and not target.get('lever') and not target.get('blueprint'), target
                cases.append({'case': label, 'clients': ['gm', 'player'], 'asset': artwork,
                              'ownerState': 'off', 'targetHasInteraction': False})
                diagnostics()

            def drag_to(x):
                hero = player.get_by_role('button', name='Token: Synthetic sprite traveler', exact=True)
                expect(hero).to_be_visible()
                box = hero.bounding_box()
                at = point(player, (x + .5) * 70, 9.5 * 70)
                player.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                player.mouse.down()
                player.mouse.move(at['x'], at['y'], steps=12)
                player.mouse.up()
                expect(hero).to_have_attribute('x', str(x * 70), timeout=10_000)

            verify(blue, 'initial-ordinary-image-blue', received=False)
            for artwork, x, label in ((orange, 9, 'area-enter-directly-changes-image-orange'),
                    (blue, 5, 'area-exit-directly-restores-image-blue'),
                    (orange, 9, 'area-reenter-directly-changes-image-orange')):
                for page in clients.values():
                    page.evaluate('window.__spriteLayers=[]')
                drag_to(x)
                verify(artwork, label)
            cases.append({'case': 'real-player-drag-entry-exit-reentry-without-target-handler', 'tokenId': token})

            # Updating unchanged authored geometry retains an active override.
            # A later native move/resize must keep that artwork; source updates
            # then retain their existing conflict guard against replacing edits.
            current = gm.request.get(f'/api/maps/{scene}/state').json()
            before = next(row for row in current['images'] if row['id'] == native_target['id'])
            player.evaluate('window.__spriteLayers=[]')
            gm.goto(review.builder + '?project=' + project['id'])
            wait_ready(gm)
            close_panel(gm)
            with gm.expect_response(lambda response: response.url.endswith('/update')) as updated:
                gm.locator('[data-builder-generate]').click()
            assert updated.value.ok, updated.value.text()
            game(gm)
            gm.locator('.game-menubar__layer').get_by_text('Game', exact=True).click()
            after = gm.request.get(f'/api/maps/{scene}/state').json()
            restored = next(row for row in after['images'] if row['id'] == native_target['id'])
            for key in ('x', 'y', 'scale', 'asset_id', 'sprite', 'spriteBase'):
                assert restored[key] == before[key], (key, restored[key], before[key])
            player.wait_for_function('''a=>window.__spriteLayers.some(state=>state.images?.some(image=>
              image.id===a.id&&image.asset_id===a.asset&&image.x===a.x&&image.scale===a.scale))''',
                arg={'id': restored['id'], 'asset': orange, 'x': restored['x'], 'scale': restored['scale']})
            verify(orange, 'same-source-scene-update-preserves-active-sprite-and-live-geometry', received=False)
            for page in clients.values():
                page.evaluate('window.__spriteLayers=[]')
            changed = gm.evaluate('''a=>gravewrightRealtime.mapCommand('objects',{
              mapId:a.scene,area:'images',action:'update',data:{placement_id:a.id,
                expected_version:a.version,x:a.x,y:a.y,scale:a.scale}})''',
                {'scene': scene, 'id': restored['id'], 'version': restored['version'],
                 'x': restored['x'] + 70, 'y': restored['y'], 'scale': restored['scale'] * 1.4})['image']
            assert changed['asset_id'] == orange and changed['spriteBase']['assetId'] == blue, changed
            native_target.update(changed)
            verify(orange, 'native-move-resize-preserves-active-sprite')
            gm.goto(review.builder + '?project=' + project['id'])
            wait_ready(gm)
            close_panel(gm)
            with gm.expect_response(lambda response: response.url.endswith('/update')) as conflicted:
                gm.locator('[data-builder-generate]').click()
            assert conflicted.value.status == 409 and conflicted.value.json()['code'] == 'conflict', conflicted.value.text()
            preserved = gm.request.get(f'/api/maps/{scene}/state').json()
            preserved_target = next(row for row in preserved['images'] if row['id'] == native_target['id'])
            assert preserved_target == changed, (preserved_target, changed)
            cases.append({'case': 'source-update-rejects-native-geometry-conflict-without-overwriting-sprite-or-edits'})
            gm.goto(f'/game/{campaign}')
            game(gm)
            gm.wait_for_function('id=>gravewrightMaps.current.id===id', arg=scene)
            gm.locator('.game-menubar__layer').get_by_text('Game', exact=True).click()
            for page in clients.values():
                page.evaluate('window.__spriteLayers=[]')
            drag_to(5)
            verify(blue, 'exit-after-native-edits-and-scene-update-still-restores-image')
            final = gm.request.get(f'/api/maps/{scene}/state').json()
            final_target = next(row for row in final['images'] if row['id'] == native_target['id'])
            assert all(final_target[key] == changed[key] for key in ('x', 'y', 'scale')), final_target
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
    return {'passed': True, 'cases': cases, 'measurements': measurements,
            'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Two generated solid PNGs and a disposable player-owned actor.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
