"""Observe real area-driven state and appearance changes on two live boards.

Unlike database-only checks, this scenario drags a player's token and waits for
both clients' native controls, received layer payloads and rendered RGB pixels.
All campaigns, media, actors and sessions belong to the disposable fixture.
"""
from __future__ import annotations

from copy import deepcopy
from io import BytesIO
import json
import time
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_playtest import behavior, chain, node
from map_builder_reference import close_panel, upload_asset, wait_ready


def check_browser(base, seed, output, executable):
    from PIL import Image
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    records, errors, dialogs, measurements = [], [], [], []
    clients, scene = {}, None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))
        contexts = []

        def client(role):
            context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
            context.add_cookies([{**seed['sessions'][role], 'url': base}])
            context.add_init_script('''window.__areaLayers=[];
              addEventListener('gravewright:map-layers',event=>window.__areaLayers.push(event.detail));''')
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append({'role': role, 'message': str(error)}))
            page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
            contexts.append(context)
            clients[role] = page
            return page

        gm = client('gm')
        review = BuilderReview(gm, campaign)

        def diagnostics():
            observations = {}
            for role, page in clients.items():
                observations[role] = page.evaluate('''()=>({url:location.href,layers:window.__areaLayers,
                  controls:[...document.querySelectorAll('[data-smart-image-id]')].map(element=>({
                    id:element.dataset.smartImageId,pressed:element.getAttribute('aria-pressed'),
                    name:element.getAttribute('aria-label')}))})''')
            if scene:
                observations['server'] = gm.request.get(f'/api/maps/{scene}/state').json()
            (output / 'measurements.json').write_text(json.dumps({
                'cases': records, 'measurements': measurements, 'observations': observations,
                'pageErrors': errors, 'nativeDialogs': dialogs}, indent=2), encoding='utf-8')

        def game(page):
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def editor(identifier):
            builder_tool(gm, 'select')
            builder_workspace(gm)
            point = gm.locator(f'[data-builder-decorations] [data-object-id="{identifier}"]').evaluate('''group=>{
              const box=group.getBBox(),point=new DOMPoint(box.x+box.width*.25,box.y+box.height*.5)
                .matrixTransform(group.getScreenCTM());return [point.x,point.y];
            }''')
            gm.mouse.dblclick(*point)
            modal = gm.locator('[data-smart-object-modal]')
            expect(modal).to_be_visible()
            return modal

        try:
            gm.goto(review.builder)
            wait_ready(gm)
            gm.locator('[data-builder-quick-name]').fill('Synthetic live area synchronization')
            gm.locator('[data-builder-quick-name]').press('Tab')
            blue = upload_asset(gm, 'decoration', 'Synthetic lever off blue.png',
                                harness.artwork('#245dc9'))['id']
            orange = upload_asset(gm, 'decoration', 'Synthetic lever on orange.png',
                                  harness.artwork('#ed7822'))['id']
            expect(gm.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved', timeout=20_000)
            project = review.project(gm.evaluate("new URL(location.href).searchParams.get('project')"))
            document = deepcopy(project['document'])
            layer = document['layers'][0]['id']
            owner, target, lamp = str(uuid4()), str(uuid4()), str(uuid4())
            graph = chain('presence:enter', [node('operate', 'interact')],
                [node('target', 'reference', targetId=target)], [('target', 'door', 'operate', 'target')])
            for value, (x, y) in zip(graph['nodes'], ((40, 60), (700, 60), (350, 250))):
                value.update(x=x, y=y)
            graphs = {'presence:enter': graph}
            target_graph = {'nodes': [node('event', 'event', event='interact'),
                node('check', 'condition', state='off'), node('on', 'state', targetState='on'),
                node('spriteOn', 'sprite', appearance='asset', assetId=orange),
                node('lightOn', 'light', targetId=lamp, enabled=True),
                node('off', 'state', targetState='off'),
                node('spriteOff', 'sprite', appearance='asset', assetId=blue),
                node('lightOff', 'light', targetId=lamp, enabled=False)], 'edges': [
                    {'kind': 'execution', 'from': before, 'output': port, 'to': after}
                    for before, port, after in (('event', 'next', 'check'), ('check', 'true', 'on'),
                        ('on', 'next', 'spriteOn'), ('spriteOn', 'next', 'lightOn'),
                        ('check', 'false', 'off'), ('off', 'next', 'spriteOff'), ('spriteOff', 'next', 'lightOff'))]}
            target_behavior = behavior('lever', {'interact': target_graph})
            document['decorations'] = [
                {'id': owner, 'layerId': layer, 'assetId': None, 'empty': True,
                 'name': 'Synthetic occupancy controller', 'x': 8, 'y': 8, 'width': 4, 'height': 3,
                 'rotation': 0, 'lever': {'state': 'off'}, 'blueprint': behavior('lever', graphs)},
                {'id': target, 'layerId': layer, 'assetId': blue,
                 'x': 16, 'y': 8, 'width': 2, 'height': 2, 'rotation': 0,
                 'lever': {'state': 'off'}, 'blueprint': target_behavior},
            ]
            document['lights'] = [{'id': lamp, 'layerId': layer, 'x': 18, 'y': 9,
                'brightRadius': 2, 'dimRadius': 3, 'color': '#ffbb66', 'intensity': .8,
                'enabled': False, 'rotation': 0, 'angle': 360, 'animation': 'none'}]
            project = review.store(project['id'], project['version'], project['folderId'], document)
            gm.goto(review.builder + '?project=' + project['id'])
            wait_ready(gm)
            modal = editor(owner)
            for event in graphs:
                modal.locator(f'[data-blueprint-event="{event}"]').click()
                expect(modal.locator('[data-blueprint-edge]')).to_have_count(2)
                expect(modal.locator('[data-blueprint-node="target"] [data-blueprint-param="targetId"]')).to_have_value(target)
                gm.screenshot(path=str(output / (event.replace(':', '-') + '-correct-authoring.png')))
            modal.locator('[data-blueprint-close]').click()
            close_panel(gm)
            with gm.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                gm.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            game(gm)
            project = review.project(project['id'])
            scene = project['sceneId']
            gm.evaluate('''a=>gravewrightRealtime.mapCommand('update',{
              mapId:a.scene,version:a.version,settings:{visibility:'players'}})''',
                {'scene': scene, 'version': project['sceneVersion']})
            gm.evaluate("scene=>gravewrightRealtime.mapCommand('activate',{mapId:scene})", scene)
            gm.evaluate('''scene=>gravewrightRealtime.mapCommand('objects',{
              mapId:scene,area:'lighting',action:'update',data:{mode:'none',darkness:0,lights_out:false}})''', scene)
            actor = gm.evaluate('''()=>gravewrightRealtime.resourceCommand('actors','actor.create',
              {name:'Synthetic area sync traveler'})''')
            gm.evaluate('''id=>gravewrightRealtime.resourceCommand('actors','actor.permissions',
              {id,permissions:{default:'owner'}})''', actor['id'])
            token = gm.evaluate('''a=>gravewrightRealtime.resourceCommand('tokens','place',
              {mapId:a.scene,actorId:a.actor,gridX:5,gridY:9})''',
                {'scene': scene, 'actor': actor['id']})['createdIds'][0]
            native = gm.request.get(f'/api/maps/{scene}/state').json()
            native_target = next(row for row in native['images'] if not row.get('empty'))
            native_owner = next(row for row in native['images'] if row.get('empty'))
            assert native_owner['layer'] == native_owner['lever']['baseLayer'] == 'gm-image-layer'
            native_lamp = native['lights'][0]['id']
            assert 'presence:exit' not in native_owner['blueprint']['graphs']
            gm.locator('.game-menubar__layer').get_by_text('Game', exact=True).click()
            player = client('player')
            player.goto(f'/game/{campaign}')
            game(player)
            player.wait_for_function('scene=>gravewrightMaps.current.id===scene', arg=scene)
            assert all(not row.get('empty') for row in player.request.get(f'/api/maps/{scene}/state').json()['images'])
            expect(player.locator(f'[data-smart-image-id="{native_owner["id"]}"]')).to_have_count(0)

            # Save an additional exit graph to the project first. The existing
            # live scene must retain its prior graph until the explicit update.
            gm.goto(review.builder + '?project=' + project['id'])
            wait_ready(gm)
            modal = editor(owner)
            modal.locator('[data-blueprint-event="presence:exit"]').click()
            before = set(modal.locator('[data-blueprint-node]').evaluate_all('rows=>rows.map(row=>row.dataset.blueprintNode)'))
            modal.locator('[data-blueprint-add]').click()
            modal.locator('[data-blueprint-pick-type="interact"]').click()
            action, = set(modal.locator('[data-blueprint-node]').evaluate_all('rows=>rows.map(row=>row.dataset.blueprintNode)')) - before
            action_card = modal.locator(f'[data-blueprint-node="{action}"]')
            action_card.locator('[data-blueprint-data-input="target"]').click()
            modal.locator('[data-blueprint-pick-type="reference"]').click()
            expect(modal.locator('[data-blueprint-node] [data-blueprint-param="targetId"]')).to_have_value(target)
            modal.locator('[data-blueprint-fit]').click()
            modal.locator('[data-blueprint-event-port="presence:exit"]').click()
            action_card.locator('[data-blueprint-input]').click()
            expect(modal.locator('[data-blueprint-edge]')).to_have_count(2)
            gm.screenshot(path=str(output / 'authored-explicit-interact-on-exit.png'))
            modal.locator('[data-blueprint-close]').click()
            expect(gm.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved', timeout=20_000)
            project = review.project(project['id'])
            source = next(row for row in project['document']['decorations'] if row['id'] == owner)
            assert 'presence:exit' in source['blueprint']['graphs']
            stored = gm.request.get(f'/api/maps/{scene}/state').json()
            assert 'presence:exit' not in next(row for row in stored['images'] if row.get('empty'))['blueprint']['graphs']
            records.append({'case': 'linked-project-autosave-keeps-live-scene-unchanged-until-update'})

            change_locale(gm, 'pt-BR', campaign)
            gm.set_viewport_size({'width': 390, 'height': 844})
            gm.reload()
            wait_ready(gm)
            modal = editor(owner)
            modal.locator('[data-blueprint-event="presence:exit"]').click()
            interact_card = modal.locator(f'[data-blueprint-node="{action}"]')
            expect(interact_card).to_contain_text('Interagir com objeto')
            expect(interact_card).to_contain_text('Inicia explicitamente')
            interact_card.locator('[data-blueprint-drag]').press('ArrowRight')
            status = modal.locator('[data-blueprint-autosave]')
            expect(status).to_have_attribute('data-state', 'saved', timeout=20_000)
            expect(status).to_contain_text('Projeto salvo.')
            expect(status).to_contain_text('Atualize a cena')
            metrics = modal.evaluate(MEASURE)
            assert not metrics['tiny'] and not metrics['overflow'], metrics
            assert metrics['scrollWidth'] <= metrics['viewport'] + 1, metrics
            measurements.append({'case': 'pt-BR-mobile-editor', **metrics})
            status.scroll_into_view_if_needed()
            gm.screenshot(path=str(output / 'interact-linked-status-pt-BR-390.png'))
            interact_card.scroll_into_view_if_needed()
            gm.screenshot(path=str(output / 'interact-node-pt-BR-390.png'))
            modal.locator('[data-blueprint-close]').click()
            records.append({'case': 'pt-BR-390-editor-wraps-linked-autosave-note-and-translates-explicit-interaction'})
            change_locale(gm, 'en', campaign)
            gm.set_viewport_size({'width': 1440, 'height': 900})
            gm.reload()
            wait_ready(gm)
            close_panel(gm)
            expect(gm.locator('[data-builder-generate]')).to_have_text('Update scene')
            with gm.expect_response(lambda response: response.url.endswith('/update')) as updated:
                gm.locator('[data-builder-generate]').click()
            assert updated.value.ok, updated.value.text()
            game(gm)
            applied = gm.request.get(f'/api/maps/{scene}/state').json()
            assert 'presence:exit' in next(row for row in applied['images'] if row.get('empty'))['blueprint']['graphs']
            gm.locator('.game-menubar__layer').get_by_text('Game', exact=True).click()
            records.append({'case': 'explicit-update-applies-new-exit-graph-to-the-same-scene-and-connected-player'})

            def control(page):
                return page.locator(f'[data-smart-image-id="{native_target["id"]}"][data-smart-image-action="interact"]')

            def point(page, x, y):
                return page.evaluate('''p=>{
                  const rect=document.querySelector('.game-board__surface').getBoundingClientRect(),v=gravewrightMaps.board.viewport();
                  return {x:rect.x+v.x+p.x*v.scale,y:rect.y+v.y+p.y*v.scale};
                }''', {'x': x, 'y': y})

            def pixels(page, expected, label):
                at = point(page, native_target['x'], native_target['y'])
                deadline = time.monotonic() + 10
                while True:
                    image = Image.open(BytesIO(page.screenshot())).convert('RGB')
                    rgb = image.getpixel((round(at['x']), round(at['y'])))
                    measurements.append({'role': label, 'expected': expected, 'pixel': rgb})
                    if expected == 'on' and rgb[0] > rgb[2] + 70 or expected == 'off' and rgb[2] > rgb[0] + 70:
                        return rgb
                    if time.monotonic() >= deadline:
                        raise AssertionError({'message': 'Live board artwork did not update',
                                              'role': label, 'expected': expected, 'pixel': rgb})
                    page.wait_for_timeout(100)

            def verify(state, label):
                for role, page in clients.items():
                    expect(control(page)).to_have_attribute('aria-pressed', str(state == 'on').lower(), timeout=10_000)
                    pixels(page, state, role)
                    page.wait_for_function('''a=>window.__areaLayers.some(state=>state.images?.some(image=>
                      image.id===a.id&&image.lever?.state===a.state&&image.asset_id===a.asset)
                      &&state.lights?.some(light=>light.id===a.light&&light.enabled===a.enabled))''',
                        arg={'id': native_target['id'], 'state': state, 'asset': orange if state == 'on' else blue,
                             'light': native_lamp, 'enabled': state == 'on'})
                    page.screenshot(path=str(output / f'{label}-{role}.png'))
                rows = gm.request.get(f'/api/maps/{scene}/state').json()['images']
                owner_row = next(row for row in rows if row['id'] == native_owner['id'])
                assert owner_row['lever']['state'] == 'off' and owner_row['layer'] == 'gm-image-layer'
                for page in clients.values():
                    expect(page.locator(f'[data-smart-image-id="{native_owner["id"]}"]')).to_have_count(0)
                records.append({'case': label, 'state': state, 'clients': ['gm', 'player']})
                diagnostics()

            def drag_to(x, y):
                hero = player.get_by_role('button', name='Token: Synthetic area sync traveler', exact=True)
                expect(hero).to_be_visible()
                box = hero.bounding_box()
                at = point(player, (x + .5) * 70, (y + .5) * 70)
                player.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                player.mouse.down()
                player.mouse.move(at['x'], at['y'], steps=12)
                player.mouse.up()
                expect(hero).to_have_attribute('x', str(x * 70), timeout=10_000)

            verify('off', 'initial-off-blue-on-both-live-boards')
            for state, x, label in (('on', 9, 'entry-turns-external-lever-orange-live'),
                                    ('off', 5, 'exit-restores-external-lever-blue-live'),
                                    ('on', 9, 'reentry-turns-external-lever-orange-live')):
                for page in clients.values():
                    page.evaluate('window.__areaLayers=[]')
                drag_to(x, 9)
                verify(state, label)
            records.append({'case': 'real-player-ui-drag-enter-exit-reenter-no-refresh-no-http-state-substitution', 'tokenId': token})
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
    return {'passed': True, 'cases': records, 'measurements': measurements,
            'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Two generated solid PNGs and a disposable player-owned actor.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
