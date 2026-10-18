"""Build a playable room from synthetic assets in an isolated Map Builder Studio.

The fixture reuses the entry scenario's disposable campaign and language package.
It never reads the operator's database, .env, media, or installed RPG systems.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import traceback
from urllib.request import urlopen

from map_builder import (ROOT, MEASURE, builder_sidebar,
                         builder_tool, builder_workspace, change_locale,
                         fixture_environment, serve)
from map_builder_reference import upload_asset, wait_ready


def inspect_fixture(fixture, scene_id=None, prepare=False, legacy=False):
    """Read persisted results; optionally add an explicitly synthetic test token."""
    if fixture is None or os.environ.get('PYTHON_DOTENV_DISABLED') != '1':
        raise RuntimeError('Fixture inspection requires the isolated scenario environment.')
    fixture = fixture.resolve()
    expected_database = (fixture / 'review.sqlite3').resolve()
    if Path(os.environ.get('GRAVEWRIGHT_DATABASE', '')).resolve() != expected_database:
        raise RuntimeError('Refusing to inspect a database outside the requested fixture.')
    seed = json.loads((fixture / 'seed.json').read_text(encoding='utf-8'))
    import django
    django.setup()
    from gravewright.accounts.models import User
    from gravewright.actors.models import Actor
    from gravewright.maps.models import Broadcast, MapBuilderProject, Scene, SceneNavigation
    from gravewright.tokens.models import Token

    result = {
        'broadcast': list(Broadcast.objects.values('campaign_id', 'scene_id')),
        'navigation': list(SceneNavigation.objects.values('membership_id', 'scene_id')),
        'sceneCount': Scene.objects.count(),
    }
    if legacy:
        import uuid
        wall_id, door_id = str(uuid.uuid4()), str(uuid.uuid4())
        document = {
            'schemaVersion': 1, 'name': 'Legacy diagonal quarter-cell door',
            'columns': 12, 'rows': 12, 'cellSize': 64, 'background': '#253038',
            'floors': [], 'assets': [],
            'walls': [{'id': wall_id, 'assetId': None, 'x1': 2, 'y1': 2,
                       'x2': 10, 'y2': 10, 'thickness': .18}],
            'doors': [{'id': door_id, 'wallId': wall_id, 'assetId': None,
                       'offset': 3, 'width': .25, 'state': 'closed'}],
        }
        row = MapBuilderProject.objects.create(
            campaign_id=seed['campaign'], name=document['name'], document=document,
        )
        result['legacyProject'] = {'id': str(row.pk), 'document': document}
    if scene_id:
        scene = Scene.objects.get(pk=scene_id, campaign_id=seed['campaign'])
        result['scene'] = {
            'id': str(scene.pk), 'name': scene.name, 'folder': str(scene.folder_id),
            'width': scene.width, 'height': scene.height, 'settings': scene.settings,
            'tiles': list(scene.tiles.values('lod', 'x', 'y', 'file')),
            'objects': list(scene.elements.values('id', 'kind', 'data')),
        }
        if prepare:
            player = User.objects.get(email='player@map-builder.test')
            actor = Actor.objects.create(
                campaign=scene.campaign, name='Synthetic doorway explorer',
                type='character', permissions={str(player.pk): 'owner'},
                data={'token': {'size': 1}},
            )
            token = Token.objects.create(
                scene=scene, actor=actor, grid_x=5.5, grid_y=3,
                vision_enabled=True, vision_range=12,
            )
            result['token'] = str(token.pk)
    print(json.dumps(result, default=str, sort_keys=True))


def synthetic_image(kind):
    """Small authored patterns ensure the test ships no third-party assets."""
    from PIL import Image, ImageDraw
    width, height = (128, 32) if kind == 'door' else (64, 64)
    colors = {'floor': '#937955', 'wall': '#747d82', 'door': '#b86d39'}
    image = Image.new('RGB', (width, height), colors[kind])
    draw = ImageDraw.Draw(image)
    if kind == 'floor':
        for y in range(0, height, 16):
            draw.line((0, y, width, y), fill='#725a3d', width=2)
        for x in range(0, width, 32):
            draw.line((x, 0, x, height), fill='#806648', width=1)
    elif kind == 'wall':
        for y in range(0, height, 16):
            draw.line((0, y, width, y), fill='#343d43', width=3)
        draw.line((32, 0, 32, height), fill='#343d43', width=2)
    else:
        for x in range(8, width, 16):
            draw.line((x, 0, x, height), fill='#673b24', width=2)
        draw.rectangle((2, 2, width - 3, height - 3), outline='#d4ad60', width=2)
    content = BytesIO(); image.save(content, 'PNG')
    return content.getvalue()


def approved_studio_geometry(page):
    """The reference uses a left tool rail, bottom library and canvas overlays."""
    result = page.evaluate("""()=>{
      const box=selector=>{const r=document.querySelector(selector).getBoundingClientRect();
        return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};};
      const viewport=box('[data-builder-viewport]');
      const drawer=document.querySelector('.map-builder__library');
      return {rail:box('.map-builder__tool-rail'),dock:box('.map-builder__asset-dock'),viewport,
        drawer:drawer.checkVisibility({checkVisibilityCSS:true})?box('.map-builder__library'):null,
        footer:box('.map-builder__status'),zoom:box('[data-builder-zoom=in]'),
        tools:[...document.querySelectorAll('[data-builder-tool]')]
          .filter(el=>el.checkVisibility({checkVisibilityCSS:true}))
          .map(el=>({tool:el.dataset.builderTool,...box('[data-builder-tool='+el.dataset.builderTool+']')})),
        width:innerWidth,height:innerHeight};
    }""")
    rail, dock, viewport = result['rail'], result['dock'], result['viewport']
    assert 52 <= rail['width'] <= 90 and rail['left'] <= 8, result
    if result['width'] > 760:
        assert abs(rail['width'] - 78) <= 1, result
    assert viewport['left'] >= rail['right'] - 1, result
    assert viewport['right'] >= result['width'] - 12, result
    assert viewport['width'] >= result['width'] - rail['width'] - 12, result
    assert viewport['height'] >= 180, result
    assert dock['top'] >= viewport['bottom'] - 1 and dock['bottom'] <= result['height'] + 1, result
    assert dock['left'] <= 8 and dock['right'] >= result['width'] - 12, result
    assert all(tool['left'] >= rail['left'] and tool['right'] <= rail['right'] + 1 for tool in result['tools']), result
    for control in (result['footer'], result['zoom']):
        assert control['left'] >= viewport['left'] and control['right'] <= viewport['right'] + 1, result
        assert control['top'] >= viewport['top'] and control['bottom'] <= viewport['bottom'] + 1, result
    if result['drawer']:
        drawer = result['drawer']
        assert drawer['left'] >= viewport['left'] - 1 and drawer['right'] <= viewport['right'] + 1, result
        assert drawer['top'] >= viewport['top'] - 1 and drawer['bottom'] <= dock['top'] + 1, result
    return result


def native_room(gm, player, seed, scene_id, token_id, output):
    """Exercise the generated objects through the real GM/player runtime."""
    from PIL import Image, ImageStat
    from playwright.sync_api import expect

    game = f"/game/{seed['campaign']}"
    gm.goto(game)
    gm.wait_for_function('!!window.gravewrightMaps?.current && !!gravewrightRealtime')
    expect(gm.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
    gm.evaluate("id=>gravewrightRealtime.mapCommand('navigate',{mapId:id})", scene_id)
    gm.wait_for_function('id=>gravewrightMaps.current?.id===id', arg=scene_id)
    gm.evaluate("""id=>gravewrightRealtime.mapCommand('update',{
      mapId:id,version:gravewrightMaps.current.version,settings:{visibility:'players'}})
    """, scene_id)
    gm.evaluate("id=>gravewrightRealtime.mapCommand('activate',{mapId:id})", scene_id)
    player.goto(game)
    for page in (gm, player):
        page.wait_for_function('id=>gravewrightMaps?.current?.id===id', arg=scene_id)
        page.wait_for_function('gravewrightMaps.board?.viewport()?.scale>0')
        expect(page.locator('.game-board__surface canvas')).to_be_visible()
        expect(page.locator('.door-controls [role=button]')).to_have_count(1)

    def layers():
        return gm.request.get(f'/api/maps/{scene_id}/state').json()

    state = layers()
    doors = [wall for wall in state['walls'] if wall['kind'] == 'door']
    assert len(doors) == 1, state['walls']
    door = doors[0]
    assert door['door_state'] == 'closed'
    assert door['movement_behavior'] == door['vision_behavior'] == 'block'

    def move(y):
        return player.evaluate("""async args=>{
          const state=await(await fetch('/api/containers/'+args.campaign+'/maps/'+args.scene+'/tokens')).json();
          const token=state.tokens.find(row=>row.id===args.token);
          try{
            await gravewrightRealtime.resourceCommand('tokens','move',{
              mapId:args.scene,id:token.id,expectedVersion:token.version,gridX:5.5,gridY:args.y});
            return {ok:true};
          }catch(error){return {ok:false,error:error.message};}
        }""", {'campaign': seed['campaign'], 'scene': scene_id, 'token': token_id, 'y': y})

    blocked = move(.5)
    assert not blocked['ok'] and 'wall' in blocked['error'].lower(), blocked
    gm.evaluate("""id=>gravewrightRealtime.mapCommand('objects',{
      mapId:id,area:'lighting',action:'update',data:{mode:'dynamic',darkness:1,lights_out:true}})
    """, scene_id)
    gm.evaluate("""id=>gravewrightRealtime.mapCommand('objects',{
      mapId:id,area:'lights',action:'create',data:{x:384,y:256,bright_radius:8,
        dim_radius:9,color:'#ffffff',intensity:1,animation:'none'}})
    """, scene_id)
    player.wait_for_function("""async id=>{
      const state=await(await fetch('/api/maps/'+id+'/state')).json();
      return state.lights.length===1&&state.lighting.mode==='dynamic';
    }""", arg=scene_id)
    player.wait_for_timeout(400)

    def sample(name):
        position = player.evaluate("""()=>{
          const surface=document.querySelector('.game-board__surface').getBoundingClientRect();
          const view=gravewrightMaps.board.viewport();
          return {x:surface.x+view.x+6.15*64*view.scale,y:surface.y+view.y+1.15*64*view.scale};
        }""")
        screenshot = player.screenshot(path=str(output / name))
        image = Image.open(BytesIO(screenshot)).convert('RGB')
        x, y = round(position['x']), round(position['y'])
        assert 5 <= x < image.width - 5 and 5 <= y < image.height - 5, position
        return sum(ImageStat.Stat(image.crop((x - 4, y - 4, x + 5, y + 5))).mean) / 3

    closed_light = sample('native-door-closed-player.png')
    player.locator('.door-controls [role=button]').click()
    gm.wait_for_function("""async id=>{
      const state=await(await fetch('/api/maps/'+id+'/state')).json();
      return state.walls.find(w=>w.kind==='door')?.door_state==='open';
    }""", arg=scene_id)
    opened = None
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        opened = sample('native-door-open-player.png')
        if opened > closed_light + 8:
            break
        player.wait_for_timeout(150)
    assert opened > closed_light + 8, {'closed': closed_light, 'open': opened}
    passed = move(.5)
    assert passed['ok'], passed
    player.locator('.door-controls [role=button]').click()
    player.wait_for_function("""async id=>{
      const state=await(await fetch('/api/maps/'+id+'/state')).json();
      return state.walls.find(w=>w.kind==='door')?.door_state==='closed';
    }""", arg=scene_id)
    blocked_again = move(3)
    assert not blocked_again['ok'] and 'wall' in blocked_again['error'].lower(), blocked_again
    return {'case': 'generated-native-door', 'door': door['id'],
            'closedMovementRejected': True, 'openMovementAccepted': True,
            'closedMovementRejectedAgain': True, 'gmPlayerSynchronized': True,
            'outsideDoorBrightness': {'closed': closed_light, 'open': opened}}


def independent_doors(new_context, seed, output, inspect, door_asset):
    """Draw independent door segments and play through one between two walls."""
    from playwright.sync_api import expect

    records = []
    ctx = new_context(); page = ctx.new_page()
    builder = f"/game/{seed['campaign']}/map-builder"
    api = f"/api/containers/{seed['campaign']}/map-builder"
    output = output / 'independent-doors'; output.mkdir()
    try:
        page.goto(builder)
        wait_ready(page)
        expect(page.locator('[data-builder-assets]')).to_be_visible()
        builder_sidebar(page, 'settings')
        form = page.locator('[data-builder-form]')
        for name, value in [('name', 'Independent doorway segments'), ('columns', '12'),
                            ('rows', '12'), ('cellSize', '64')]:
            field = form.locator(f'[name={name}]'); field.fill(value); field.press('Tab')
        builder_sidebar(page, 'library')
        builder_tool(page, 'door')
        page.locator('[data-builder-role=door]').click()
        page.locator(f'[data-asset-id="{door_asset}"]').click()
        builder_tool(page, 'door')

        def point(x, y):
            builder_workspace(page)
            return page.locator('[data-builder-canvas]').evaluate("""(svg,p)=>{
              const result=new DOMPoint(p.x,p.y).matrixTransform(svg.getScreenCTM());
              return {x:result.x,y:result.y};
            }""", {'x': x, 'y': y})

        def click(x, y):
            p = point(x, y); page.mouse.click(p['x'], p['y'])

        def drag(x1, y1, x2, y2, finish=True):
            start, end = point(x1, y1), point(x2, y2)
            page.mouse.move(start['x'], start['y']); page.mouse.down()
            page.mouse.move(end['x'], end['y'], steps=8)
            if finish:
                page.mouse.up()

        def count(value):
            expect(page.locator('[data-builder-object-count]')).to_have_text(f'{value} objects')

        def endpoints(values):
            builder_sidebar(page, 'selection')
            for name, value in zip(('x1', 'y1', 'x2', 'y2'), values):
                expect(page.locator(f'[data-builder-property={name}]')).to_have_value(str(value))

        def undo():
            page.locator('[data-builder-viewport]').focus(); page.keyboard.press('Control+z')

        def save():
            with page.expect_response(lambda response: '/map-builder/projects/' in response.url and
                                      response.request.method == 'POST' and not response.url.endswith('/generate')) as response:
                page.locator('[data-builder-save]').click()
            assert response.value.ok, response.value.text()
            return response.value.json()['project']

        # A press does not place an object; both endpoints must describe a span.
        click(2, 5); count(0)
        drag(2, 5, 2, 5); count(0)
        drag(2, 5, 4, 5, finish=False)
        expect(page.locator('[data-builder-ghost] image')).to_have_count(1)
        page.keyboard.press('Escape'); page.mouse.up(); count(0)
        expect(page.locator('[data-builder-ghost]')).to_be_empty()
        records.append({'case': 'independent-door-cancellation', 'singleClickCreatesNothing': True,
                        'zeroSpanCreatesNothing': True, 'escapeDiscardsPreview': True})

        spans = [(5, 2, 7, 2), (9, 4, 9, 6), (3, 7, 5, 9)]
        for index, span in enumerate(spans, 1):
            drag(*span); count(index); endpoints(span)
        expect(page.locator('[data-builder-walls]')).to_be_empty()
        first = save(); project_id = first['id']
        document = first['document']
        assert document['schemaVersion'] == 3 and document['walls'] == [], document
        assert [tuple(door[key] for key in ('x1', 'y1', 'x2', 'y2'))
                for door in document['doors']] == spans, document['doors']
        assert all('wallId' not in door and door['assetId'] == door_asset
                   for door in document['doors']), document['doors']
        page.screenshot(path=str(output / 'three-independent-orientations.png'), full_page=True)
        page.reload(); count(3)
        records.append({'case': 'independent-door-directions', 'horizontal': True, 'vertical': True,
                        'diagonal': True, 'noWallRequired': True, 'savedAndReloaded': True})

        page.locator('[data-builder-tool=select]').click(); click(6, 2)
        endpoints(spans[0]); drag(6, 2, 6, 3); endpoints((5, 3, 7, 3))
        undo(); endpoints(spans[0])
        page.keyboard.press('Control+Shift+z'); endpoints((5, 3, 7, 3))
        undo(); endpoints(spans[0])
        start_x = page.locator('[data-builder-property=x1]')
        builder_sidebar(page, 'selection')
        start_x.fill('4.5'); start_x.press('Tab'); endpoints((4.5, 2, 7, 2))
        undo(); endpoints(spans[0])
        click(9, 5); endpoints(spans[1])
        page.locator('[data-builder-viewport]').focus(); page.keyboard.press('Delete'); count(2)
        undo(); count(3)
        page.keyboard.press('Control+Shift+z'); count(2)
        click(4, 8); endpoints(spans[2])
        builder_sidebar(page, 'selection')
        page.locator('[data-builder-delete]').click(); count(1)
        records.append({'case': 'independent-door-editing', 'freeMovement': True,
                        'endpointEditing': True, 'undoRedo': True, 'individualDeletion': True})

        # There is no parent wall crossing this opening: the door is the third
        # independent segment between the two deliberately separated wall ends.
        builder_tool(page, 'floor')
        page.locator('[data-builder-paint-mode]').select_option('rectangle')
        drag(.1, .1, 11.9, 11.9)
        builder_tool(page, 'wall')
        drag(2, 2, 5, 2); drag(7, 2, 10, 2); count(147)
        final = save()
        assert len(final['document']['walls']) == 2 and len(final['document']['doors']) == 1
        page.reload(); count(147)
        restored = page.request.get(api + '/projects/' + project_id).json()['project']
        assert restored['document'] == final['document']
        page.screenshot(path=str(output / 'door-between-wall-ends.png'), full_page=True)
        with page.expect_response(lambda response: response.url.endswith('/generate')) as response:
            page.locator('[data-builder-generate]').click()
        assert response.value.ok, response.value.status
        page.wait_for_url(f'**/game/{seed["campaign"]}')
        scene_id = page.request.get(api + '/projects/' + project_id).json()['project']['sceneId']
        page.wait_for_function('id=>gravewrightMaps?.current?.id===id', arg=scene_id)
        fixture = inspect(scene_id, prepare=True)
        native = [row['data'] for row in fixture['scene']['objects'] if row['kind'] == 'walls']
        assert len(native) == 3, native
        assert sorted((row['x1'], row['y1'], row['x2'], row['y2'], row['kind']) for row in native) == [
            (128, 128, 320, 128, 'wall'), (320, 128, 448, 128, 'door'),
            (448, 128, 640, 128, 'wall')], native
        records.append({'case': 'independent-door-native-generation', 'scene': scene_id,
                        'segments': 3, 'savedGeometryPreserved': True, 'noParentWall': True})
        player_ctx = new_context('player')
        try:
            played = native_room(page, player_ctx.new_page(), seed, scene_id, fixture['token'], output)
            played['case'] = 'independent-door-native-play'
            records.append(played)
        finally:
            player_ctx.close()

        # Seed a genuinely stored v1 source. Sending it through today's save API
        # would immediately normalize it and miss the browser's legacy reader.
        legacy = inspect(legacy=True)['legacyProject']
        stored = page.request.get(api + '/projects/' + legacy['id']).json()['project']
        assert stored['document'] == legacy['document'] and stored['document']['schemaVersion'] == 1
        page.goto(builder + '?project=' + legacy['id']); count(2)
        expect(page.locator('[data-builder-save-state]')).to_have_text('Saved')
        expect(page.locator('[data-builder-doors] [data-object-id]').first).to_have_attribute(
            'data-object-id', legacy['document']['doors'][0]['id'])
        page.locator('[data-builder-tool=select]').click()
        midpoint = 2 + 3.125 / (2 ** .5)
        click(midpoint, midpoint)
        builder_sidebar(page, 'selection')
        initial_fields = {key: page.locator(f'[data-builder-property={key}]').input_value()
                          for key in ('x1', 'y1', 'x2', 'y2')}
        click(midpoint, midpoint)
        expect(page.locator('[data-builder-save-state]')).to_have_text('Saved')
        for key, value in initial_fields.items():
            expect(page.locator(f'[data-builder-property={key}]')).to_have_value(value)
        builder_sidebar(page, 'settings')
        name = form.locator('[name=name]')
        name.fill('Legacy diagonal door preserved'); name.press('Tab')
        migrated = save()
        assert migrated['id'] == legacy['id'] and migrated['document']['schemaVersion'] == 3
        migrated_door = migrated['document']['doors'][0]
        assert migrated_door['id'] == legacy['document']['doors'][0]['id']
        assert migrated_door['thickness'] == .18 and migrated_door['state'] == 'closed'
        assert all(migrated_door[key] == float(value) for key, value in initial_fields.items())
        assert abs(((migrated_door['x2'] - migrated_door['x1']) ** 2 +
                    (migrated_door['y2'] - migrated_door['y1']) ** 2) ** .5 - .25) < 1e-12
        page.screenshot(path=str(output / 'legacy-diagonal-door-preserved.png'), full_page=True)
        records.append({'case': 'legacy-door-browser-migration', 'storedVersion1Opened': True,
                        'quarterCellDiagonal': True, 'selectionPreservesExactEndpoints': True,
                        'selectionDoesNotMarkDirty': True, 'savedVersion3PreservesIdAndGeometry': True})
    except Exception:
        if not page.is_closed():
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
        raise
    finally:
        ctx.close()
    return records


def check_browser(base, seed, output, executable, inspect):
    from playwright.sync_api import expect, sync_playwright

    errors, failed_requests, native_dialogs, records = [], [], [], []
    builder = f"{base}/game/{seed['campaign']}/map-builder"
    api = f"/api/containers/{seed['campaign']}/map-builder"
    authored_name = 'Taverna de São João — Synthetic playable room'
    floor_tiles, room_count = 144, 149
    baseline = inspect()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**({'executable_path': str(executable)} if executable else {}))

        def context(role='gm', width=1440, height=900):
            ctx = browser.new_context(base_url=base, viewport={'width': width, 'height': height})
            if role:
                ctx.add_cookies([{**seed['sessions'][role], 'url': base}])

            def observe(page):
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('requestfailed', lambda request: failed_requests.append({
                    'url': request.url, 'error': request.failure, 'page': page.url,
                }))

                def native_dialog(dialog):
                    native_dialogs.append({'type': dialog.type, 'message': dialog.message})
                    dialog.dismiss()

                page.on('dialog', native_dialog)
            ctx.on('page', observe)
            return ctx

        ctx = context(); page = ctx.new_page()
        try:
            page.goto(builder + '?folder=' + seed['folder'])
            wait_ready(page)
            root = page.locator('[data-map-builder]'); expect(root).to_be_visible()
            expect(page.locator('[data-builder-assets-empty]')).to_be_visible()
            builder_sidebar(page, 'projects')
            expect(page.locator('[data-builder-projects-empty]')).to_be_visible()
            builder_sidebar(page, 'library')
            records.append({'case': 'empty-studio', 'noAssetsOrProjects': True})

            builder_sidebar(page, 'settings')
            form = page.locator('[data-builder-form]')
            for name, value in [('name', authored_name), ('columns', '12'), ('rows', '12'), ('cellSize', '64')]:
                field = form.locator(f'[name={name}]')
                field.fill(value); field.press('Tab')
            expect(page.locator('[data-builder-title]')).to_have_text(authored_name)
            expect(page.locator('[data-builder-paper]')).to_have_attribute('width', '12')
            expect(page.locator('[data-builder-paper]')).to_have_attribute('height', '12')

            builder_sidebar(page, 'library')
            assets = {}
            for kind in ('floor', 'wall', 'door'):
                filename = f'Synthetic {kind} texture with a deliberately long authored filename.png'
                asset_id = upload_asset(page, kind, filename, synthetic_image(kind))['id']
                assets[kind] = asset_id
                page.locator(f'[data-builder-role={kind}]').click()
                asset_button = page.locator(f'[data-asset-id="{asset_id}"]')
                expect(asset_button).to_be_visible(); asset_button.click()
                expect(asset_button).to_have_attribute('data-asset-role', kind)
                expect(asset_button).to_be_visible()
            records.append({'case': 'own-assets-upload-and-classification', 'assets': assets})

            for kind in ('floor', 'wall'):
                builder_tool(page, kind)
                page.locator(f'[data-builder-role={kind}]').click()
                card = page.locator(f'[data-asset-id="{assets[kind]}"]')
                card.click()
                material = page.locator('[data-builder-brush-material]')
                thumbnail = page.locator('[data-builder-brush-thumbnail]')
                expect(material).to_have_value(assets[kind])
                expect(thumbnail).to_be_visible()
                expect(thumbnail).to_have_attribute('src', card.locator('img').get_attribute('src'))
                material.select_option('')
                expect(thumbnail).to_be_hidden()
                expect(material).to_have_value('')
                expect(page.locator('[data-builder-assets] [data-asset-id=""]')).to_have_count(0)
                expect(card).to_have_attribute('aria-pressed', 'false')
                material.select_option(assets[kind])
                expect(card).to_have_attribute('aria-pressed', 'true')
                expect(thumbnail).to_be_visible()
            page.locator('[data-builder-role=light]').click()
            expect(page.locator('[data-builder-tool=wall]')).to_have_attribute('aria-pressed', 'true')
            builder_tool(page, 'light')
            expect(page.locator('[data-builder-tool=light]')).to_have_attribute('aria-pressed', 'true')
            expect(page.locator('[data-builder-brush=lightRadius]')).to_be_visible()
            expect(page.locator('[data-builder-library-help]')).to_be_visible()
            assert page.locator('[data-builder-library-help]').inner_text().strip()
            expect(page.locator('[data-builder-import]')).to_be_visible()
            expect(page.locator('[data-builder-assets] [data-asset-id]')).to_have_count(0)
            page.locator('[data-builder-role=floor]').click()
            expect(page.locator('[data-builder-import]')).to_be_visible()
            expect(page.locator('[data-builder-assets]')).to_be_visible()
            expect(page.locator('[data-builder-tool=light]')).to_have_attribute('aria-pressed', 'true')
            builder_tool(page, 'floor')
            expect(page.locator(f'[data-asset-id="{assets["floor"]}"]')).to_have_attribute('aria-pressed', 'true')
            expect(page.locator('[data-builder-object-count]')).to_have_text('0 objects')
            records.append({'case': 'reference-toolbar-and-light-library',
                            'materialThumbnailAndCardsStayInSync': True, 'defaultMaterialCanRestoreUploadedMaterial': True,
                            'categoriesAndToolsIndependent': True, 'lightsExposeNativeBrush': True,
                            'floorRestoresCardsAndImportRemainsAccessible': True})

            def point(x, y):
                builder_workspace(page)
                return page.locator('[data-builder-canvas]').evaluate("""(svg,p)=>{
                  const result=new DOMPoint(p.x,p.y).matrixTransform(svg.getScreenCTM());
                  return {x:result.x,y:result.y};
                }""", {'x': x, 'y': y})

            def click_cell(x, y):
                p = point(x, y); page.mouse.click(p['x'], p['y'])

            def drag(x1, y1, x2, y2):
                start, end = point(x1, y1), point(x2, y2)
                page.mouse.move(start['x'], start['y']); page.mouse.down()
                page.mouse.move(end['x'], end['y'], steps=8); page.mouse.up()

            def count(value):
                expect(page.locator('[data-builder-object-count]')).to_have_text(f'{value} objects')

            page.locator('[data-builder-role=floor]').click()
            page.locator(f'[data-asset-id="{assets["floor"]}"]').click()
            builder_tool(page, 'floor')
            page.locator('[data-builder-paint-mode]').select_option('rectangle')
            drag(.1, .1, 11.9, 11.9)
            count(floor_tiles)
            builder_sidebar(page, 'library')
            page.locator('[data-builder-role=wall]').click()
            page.locator(f'[data-asset-id="{assets["wall"]}"]').click()
            builder_tool(page, 'wall')
            for span in [(2, 2, 10, 2), (10, 2, 10, 10), (10, 10, 2, 10), (2, 10, 2, 2)]:
                drag(*span)
            count(room_count - 1)
            builder_sidebar(page, 'library')
            page.locator('[data-builder-role=door]').click()
            page.locator(f'[data-asset-id="{assets["door"]}"]').click()
            builder_tool(page, 'door'); drag(5, 2, 7, 2)
            count(room_count)
            page.locator('[data-builder-viewport]').focus(); page.keyboard.press('Control+z'); count(room_count - 1)
            page.keyboard.press('Control+Shift+z'); count(room_count)
            page.locator('[data-builder-tool=select]').click(); click_cell(6, 2)
            for name, value in [('x1', '5'), ('y1', '2'), ('x2', '7'), ('y2', '2')]:
                expect(page.locator(f'[data-builder-property={name}]')).to_have_value(value)
            door_art = page.locator('[data-builder-doors] [data-object-id]')
            before_move = door_art.bounding_box()
            drag(9, 2, 9, 3)
            after_move = door_art.bounding_box()
            cell_pixels = page.locator('[data-builder-canvas]').evaluate('svg=>svg.getScreenCTM().a')
            assert abs(after_move['y'] - before_move['y']) < 2, (before_move, after_move, cell_pixels)
            page.locator('[data-builder-viewport]').focus(); page.keyboard.press('Control+z')
            restored_move = door_art.bounding_box()
            assert abs(restored_move['y'] - before_move['y']) < 2
            click_cell(9, 2)
            page.locator('[data-builder-viewport]').focus(); page.keyboard.press('Delete'); count(room_count - 1)
            expect(door_art).to_have_count(1)
            page.keyboard.press('Control+z'); count(room_count)
            builder_tool(page, 'wall'); drag(3, 7, 4, 7); count(room_count + 1)
            page.locator('[data-builder-tool=select]').click(); click_cell(3.5, 7)
            page.locator('[data-builder-viewport]').focus(); page.keyboard.press('Delete'); count(room_count)
            page.keyboard.press('Control+z'); count(room_count + 1)
            page.keyboard.press('Control+Shift+z'); count(room_count)
            builder_tool(page, 'wall'); drag(3, 8, 4, 8); count(room_count + 1)
            page.locator('[data-builder-viewport]').focus(); page.keyboard.press('e')
            click_cell(3.5, 8); count(room_count)
            page.locator('[data-builder-tool=select]').click()
            page.screenshot(path=str(output / 'studio-painted-room.png'), full_page=True)
            records.append({'case': 'paint-select-delete-erase-history', 'floor': floor_tiles, 'walls': 4, 'doors': 1,
                            'keyboardUndoRedo': True, 'doorEndpoints': [5, 2, 7, 2],
                            'movingOrDeletingWallPreservesIndependentDoor': True})

            # Selection stays in an auxiliary drawer while the asset dock and
            # tool rail remain available around the canvas.
            for width, height in [(1586, 992), (1440, 900)]:
                page.set_viewport_size({'width': width, 'height': height})
                builder_workspace(page)
                page.locator('[data-builder-fit]').click()
                click_cell(6, 2)
                expect(page.locator('.map-builder__library')).to_be_hidden()
                builder_sidebar(page, 'selection')
                expect(page.locator('[data-builder-sidebar-tab=selection][role=tab]')).to_have_attribute('aria-selected', 'true')
                field = page.locator('[data-builder-property=x1]')
                expect(field).to_be_visible()
                geometry = approved_studio_geometry(page)
                field_box = field.bounding_box()
                assert field_box['x'] >= geometry['drawer']['left'] and field_box['x'] + field_box['width'] <= geometry['drawer']['right'], geometry
                page.screenshot(path=str(output / f'approved-studio-selection-{width}.png'), full_page=True)
                records.append({'case': 'approved-studio-geometry', 'width': width,
                                'selectionPropertiesInsideAuxiliaryDrawer': True, **geometry})

            builder_sidebar(page, 'layers')
            page.locator('[data-builder-sidebar-tab=layers][role=tab]').focus()
            for key, expected in [('ArrowRight', 'selection'), ('ArrowRight', 'settings'),
                                  ('Home', 'layers'), ('End', 'review'), ('Home', 'layers'),
                                  ('ArrowRight', 'selection')]:
                page.keyboard.press(key)
                tab = page.locator(f'[data-builder-sidebar-tab={expected}][role=tab]')
                expect(tab).to_be_focused(); expect(tab).to_have_attribute('aria-selected', 'true')
            expect(page.locator('[data-builder-doors] image')).to_have_count(1)
            page.locator('[data-builder-material-id=""]').click()
            expect(page.locator('[data-builder-doors] image')).to_have_count(0)
            expect(page.locator('[data-builder-property=assetId]')).to_have_value('')
            page.locator('[data-builder-viewport]').focus(); page.keyboard.press('Control+z')
            expect(page.locator('[data-builder-doors] image')).to_have_count(1)
            appearance = page.locator('[data-builder-property=assetId]')
            appearance.select_option('')
            expect(page.locator('[data-builder-material-id=""]')).to_have_attribute('aria-pressed', 'true')
            expect(page.locator(f'[data-builder-material-id="{assets["door"]}"]')).to_have_attribute('aria-pressed', 'false')
            appearance.select_option(assets['door'])
            expect(page.locator(f'[data-builder-material-id="{assets["door"]}"]')).to_have_attribute('aria-pressed', 'true')
            expect(page.locator('[data-builder-material-id=""]')).to_have_attribute('aria-pressed', 'false')
            records.append({'case': 'studio-context-material-and-keyboard-tabs',
                            'rovingArrowHomeEndNavigation': True, 'materialChangesSelectedDoor': True,
                            'materialChangeCanBeUndone': True, 'dropdownAndPaletteStayInSync': True})

            for tool in ('floor', 'wall', 'door', 'decoration', 'light'):
                builder_tool(page, tool)
                expect(page.locator(f'[data-builder-tool={tool}]')).to_have_attribute('aria-pressed', 'true')
            builder_sidebar(page, 'review')
            expect(page.locator('[data-builder-review-panel]')).to_be_visible()
            expect(page.locator('[data-builder-review-summary]')).to_contain_text('12 × 12')
            assert page.locator('[data-builder-review-summary] strong').all_text_contents()[-7:] == [str(floor_tiles), '4', '1', '0', '0', '0', '0']
            records.append({'case': 'approved-studio-tool-rail', 'allBrushesAccessible': True,
                            'reviewHasLiveSummary': True})
            builder_tool(page, 'select'); click_cell(6, 2)
            builder_sidebar(page, 'selection')
            for name, value in [('x1', '5'), ('y1', '2'), ('x2', '7'), ('y2', '2')]:
                expect(page.locator(f'[data-builder-property={name}]')).to_have_value(value)
            page.locator('[data-builder-door-state=open]').click()
            expect(page.locator('[data-builder-doors] [data-object-id] line')).to_have_count(1)
            page.locator('[data-builder-preview]').click()
            expect(page.locator('[data-builder-doors] [data-object-id]')).to_be_empty()
            expect(page.locator('[data-builder-property=state]')).to_have_attribute('data-value', 'open')
            page.locator('[data-builder-preview]').click()
            expect(page.locator('[data-builder-doors] [data-object-id] line')).to_have_count(1)
            expect(page.locator('[data-builder-property=state]')).to_have_attribute('data-value', 'open')
            page.locator('[data-builder-door-state=closed]').click()
            records.append({'case': 'studio-open-door-preview', 'editingGuideHiddenInPreview': True,
                            'editingGuideRestoredOnExit': True, 'doorStatePreserved': True})
            rendered_before = {kind: page.locator(f'[data-builder-{kind}]').inner_html()
                               for kind in ('floors', 'walls', 'doors')}
            page.locator('[data-builder-preview]').click()
            expect(page.locator('[data-builder-preview]')).to_have_attribute('aria-pressed', 'true')
            expect(page.locator('[data-builder-grid]')).to_be_hidden()
            expect(page.locator('[data-builder-selection]')).to_be_hidden()
            expect(page.locator('[data-builder-undo]')).to_be_disabled()
            expect(page.locator('[data-builder-redo]')).to_be_disabled()
            drag(6, 2, 6, 3); count(room_count)
            page.locator('[data-builder-viewport]').focus(); page.keyboard.press('Control+z')
            count(room_count)
            for kind, markup in rendered_before.items():
                assert page.locator(f'[data-builder-{kind}]').inner_html() == markup, kind
            page.locator('[data-builder-zoom=in]').click()
            page.locator('[data-builder-fit]').click()
            page.screenshot(path=str(output / 'approved-studio-preview.png'), full_page=True)
            page.locator('[data-builder-preview]').click()
            expect(page.locator('[data-builder-grid]')).to_be_visible()
            records.append({'case': 'studio-preview', 'editorGeometryHidden': True,
                            'editingPrevented': True, 'paintedObjectsPreserved': True,
                            'cameraRemainsUsable': True, 'historyCannotEditDuringPreview': True})
            builder_sidebar(page, 'layers')
            authored_layers = page.locator('[data-builder-project-layer]')
            expect(authored_layers).to_have_count(1)
            mixed_layer = authored_layers.get_attribute('data-builder-project-layer')
            name = page.locator(f'[data-builder-layer-title="{mixed_layer}"]')
            name.fill('Mixed room surfaces'); name.dispatch_event('change')
            page.locator('[data-builder-layer-name]').fill('Doorway details')
            page.locator('[data-builder-layer-add]').click()
            expect(authored_layers).to_have_count(2)
            door_layer = page.locator('[data-builder-active-layer-select]').input_value()
            assert door_layer != mixed_layer
            expect(page.locator('[data-builder-layer]')).to_have_count(0)
            builder_tool(page, 'select')
            page.locator('[data-builder-doors] [data-object-id]').click()
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=layerId]').select_option(door_layer)
            builder_sidebar(page, 'layers')
            layered_before = {kind: page.locator(f'[data-builder-{kind}]').inner_html() for kind in rendered_before}
            for kind, markup in rendered_before.items():
                expected = markup.replace(f'data-object-layer="{mixed_layer}"', f'data-object-layer="{door_layer}"') if kind == 'doors' else markup
                assert layered_before[kind] == expected, kind
            for identifier, hidden_kinds, visible_kinds in (
                    (mixed_layer, ('floors', 'walls'), ('doors',)),
                    (door_layer, ('doors',), ('floors', 'walls'))):
                toggle = page.locator(f'[data-builder-layer-visible="{identifier}"]')
                toggle.uncheck()
                for kind in hidden_kinds:
                    assert page.locator(f'[data-builder-{kind}] [data-object-id]').evaluate_all(
                        'elements=>elements.length>0 && elements.every(el=>getComputedStyle(el).display==="none")'), kind
                for kind in visible_kinds:
                    expect(page.locator(f'[data-builder-{kind}] [data-object-id]').first).to_be_visible()
                count(room_count)
                toggle.check()
            for kind in ('floors', 'walls', 'doors'):
                assert page.locator(f'[data-builder-{kind}]').inner_html() == layered_before[kind], kind
            door_visibility = page.locator(f'[data-builder-layer-visible="{door_layer}"]')
            door_visibility.uncheck()
            page.locator('[data-builder-preview]').click()
            expect(page.locator('[data-builder-doors] [data-object-id]')).to_be_visible()
            expect(door_visibility).to_be_disabled()
            expect(door_visibility).not_to_be_checked()
            page.locator('[data-builder-preview]').click()
            expect(page.locator('[data-builder-doors] [data-object-id]')).to_be_hidden()
            expect(door_visibility).not_to_be_checked()
            door_visibility.check()
            page.screenshot(path=str(output / 'approved-studio-layers.png'), full_page=True)
            records.append({'case': 'studio-layers', 'visibilityIndependentForNamedMixedAndDoorLayers': True,
                            'geometryPreserved': True, 'visibilityIsEditorOnly': True,
                            'previewShowsAllLayersAndRestoresEditorVisibility': True})

            with page.expect_response(lambda response: '/map-builder/projects/' in response.url and
                                      response.request.method == 'POST' and not response.url.endswith('/generate')) as saved:
                page.locator('[data-builder-save]').click()
            assert saved.value.ok, saved.value.text()
            project = saved.value.json()['project']; project_id = project['id']
            assert project['folderId'] == seed['folder'], project
            document = project['document']
            assert document['name'] == authored_name
            assert len(document['floors']) == floor_tiles and len(document['walls']) == 4 and len(document['doors']) == 1, document
            assert {row['role']: row['assetId'] for row in document['assets']} == assets
            assert all(row['width'] == row['height'] == 1 for row in document['floors'])
            assert {(row['x'], row['y']) for row in document['floors']} == {(x, y) for x in range(12) for y in range(12)}
            assert document['schemaVersion'] == 3
            assert {key: document['doors'][0][key] for key in ('x1', 'y1', 'x2', 'y2')} == {
                'x1': 5, 'y1': 2, 'x2': 7, 'y2': 2}
            assert inspect()['sceneCount'] == baseline['sceneCount'], 'Saving a project created a playable scene'
            page.reload()
            page.wait_for_function('parseInt(document.querySelector("[data-builder-object-count]")?.textContent)===149')
            expect(page.locator('[data-builder-title]')).to_have_text(authored_name)
            builder_sidebar(page, 'projects')
            page.locator('[data-builder-new]').click(); count(0)
            builder_sidebar(page, 'projects')
            page.locator(f'button[data-project-id="{project_id}"]').click(); count(room_count)
            expect(form.locator('[name=name]')).to_have_value(authored_name)
            reopened = page.request.get(api + '/projects/' + project_id).json()['project']
            assert reopened['document'] == document, 'Reopening changed the persisted source'
            records.append({'case': 'save-reload-new-open', 'project': project_id,
                            'folderPreserved': True, 'documentPreserved': True})

            def save(page_to_save, name=None, shortcut=False, expected_status=200):
                name_input = page_to_save.locator('[data-builder-form] [name=name]')
                if name is not None:
                    builder_sidebar(page_to_save, 'settings')
                    name_input.fill(name)
                    if not shortcut:
                        name_input.press('Tab')
                with page_to_save.expect_response(lambda response: '/map-builder/projects/' in response.url and
                                                 response.request.method == 'POST' and not response.url.endswith('/generate')) as result:
                    if shortcut:
                        name_input.press('Control+s')
                    else:
                        page_to_save.locator('[data-builder-save]').click()
                assert result.value.status == expected_status, result.value.text()
                return result.value.json()

            focused_name = 'São João — Saved from the focused name field'
            focused = save(page, focused_name, shortcut=True)['project']
            assert focused['document']['name'] == focused_name
            records.append({'case': 'ctrl-s-focused-name', 'persistedName': focused_name})
            unsaved_name = 'São João — Guarded unsaved changes'
            builder_sidebar(page, 'settings')
            name_input = page.locator('[data-builder-form] [name=name]')
            name_input.fill(unsaved_name); name_input.press('Tab')
            builder_sidebar(page, 'projects')
            page.locator('[data-builder-new]').click()
            notice = page.locator('[data-builder-notice]')
            notice.get_by_role('button', name='Keep editing', exact=True).click()
            expect(name_input).to_have_value(unsaved_name); count(room_count)
            builder_sidebar(page, 'projects')
            page.locator('[data-builder-new]').click()
            notice.get_by_role('button', name='Discard changes', exact=True).click(); count(0)
            builder_sidebar(page, 'projects')
            page.locator(f'button[data-project-id="{project_id}"]').click(); count(room_count)
            expect(name_input).to_have_value(focused_name)
            records.append({'case': 'unsaved-project-guard', 'keepEditingPreservesWork': True,
                            'explicitDiscardOpensNew': True, 'savedProjectPreserved': True})

            draft_name = 'São João — Recovered local draft'
            builder_sidebar(page, 'settings')
            name_input.fill(draft_name); name_input.press('Tab')
            page.reload()
            expect(page.locator('[data-builder-form] [name=name]')).to_have_value(draft_name)
            count(room_count)
            expect(page.locator('[data-builder-notice-text]')).to_have_text('Recovered unsaved work from this tab.')
            persisted_before_recovery_save = page.request.get(api + '/projects/' + project_id).json()['project']
            assert persisted_before_recovery_save['document']['name'] == focused_name
            page.locator('[data-builder-dismiss]').click()
            focused_draft_name = 'São João — Focused draft survives reload'
            builder_sidebar(page, 'settings')
            page.locator('[data-builder-form] [name=name]').fill(focused_draft_name)
            page.reload()
            expect(page.locator('[data-builder-form] [name=name]')).to_have_value(focused_draft_name)
            count(room_count)
            draft_name = focused_draft_name
            recovered = save(page)['project']
            assert recovered['document']['name'] == draft_name
            records.append({'case': 'recover-local-draft-after-reload', 'localChangesPreserved': True,
                            'serverChangesOnlyAfterSave': True})

            other_ctx = context(); other = other_ctx.new_page()
            other.goto(builder + '?project=' + project_id)
            expect(other.locator('[data-builder-form] [name=name]')).to_have_value(draft_name)
            main_name = 'São João — Main saved project'
            main_saved = save(page, main_name)['project']
            conflicting_name = 'São João — Preserved conflicting draft'
            save(other, conflicting_name, expected_status=409)
            expect(other.locator('[data-builder-notice-text]')).to_have_text('The map project changed. Reload it before saving.')
            other.screenshot(path=str(output / 'studio-conflict-preserves-draft.png'), full_page=True)
            with other.expect_response(lambda response: '/map-builder/projects/' in response.url and
                                      response.request.method == 'POST') as copied:
                other.locator('[data-builder-notice]').get_by_role('button', name='Save a copy', exact=True).click()
            assert copied.value.ok, copied.value.text()
            copy_project = copied.value.json()['project']
            assert copy_project['id'] != project_id and copy_project['document']['name'] == conflicting_name
            unchanged_original = page.request.get(api + '/projects/' + project_id).json()['project']
            assert unchanged_original['document']['name'] == main_name
            assert unchanged_original['version'] == main_saved['version']
            builder_sidebar(other, 'projects')
            other.locator(f'button[data-project-id="{project_id}"]').click()
            expect(other.locator('[data-builder-form] [name=name]')).to_have_value(main_name)
            final_name = 'São João — Final playable room'
            save(page, final_name)
            save(other, 'São João — Stale draft for reload', expected_status=409)
            other.locator('[data-builder-notice]').get_by_role('button', name='Reload saved project', exact=True).click()
            other.locator('[data-builder-notice]').get_by_role('button', name='Discard changes', exact=True).click()
            expect(other.locator('[data-builder-form] [name=name]')).to_have_value(final_name)
            original = page.request.get(api + '/projects/' + project_id).json()['project']
            copied_durable = page.request.get(api + '/projects/' + copy_project['id']).json()['project']
            assert copied_durable['document']['name'] == conflicting_name
            assert original['document']['name'] == final_name
            document = original['document']; authored_name = final_name
            other_ctx.close()
            records.append({'case': 'two-window-version-conflicts', 'staleSaveRejected': True,
                            'saveCopyPreservesBoth': True, 'reloadRequiresExplicitDiscard': True,
                            'copiedProject': copy_project['id']})

            isolated_draft = 'São João — Project A draft survives visiting B'
            builder_sidebar(page, 'settings')
            page.locator('[data-builder-form] [name=name]').fill(isolated_draft)
            page.goto(builder + '?project=' + copy_project['id'])
            expect(page.locator('[data-builder-form] [name=name]')).to_have_value(conflicting_name)
            page.goto(builder + '?project=' + project_id)
            expect(page.locator('[data-builder-form] [name=name]')).to_have_value(isolated_draft)
            count(room_count)
            assert page.request.get(api + '/projects/' + project_id).json()['project']['document']['name'] == final_name
            save(page)
            save(page, final_name)
            assert page.request.get(api + '/projects/' + copy_project['id']).json()['project']['document']['name'] == conflicting_name
            records.append({'case': 'project-scoped-drafts', 'focusedFieldFlushedOnReload': True,
                            'visitingAnotherProjectPreservesDraft': True, 'otherProjectUnchanged': True})

            delayed_ctx = context(); delayed = delayed_ctx.new_page(); held = []
            delayed.route('**/map-builder/projects/' + project_id, lambda route: held.append(route))
            delayed.goto(builder + '?project=' + project_id, wait_until='domcontentloaded')
            delayed.wait_for_function("""()=>document.querySelector('[data-map-builder]')?.getAttribute('aria-busy')==='true'
              &&document.querySelectorAll('[data-builder-assets] [data-asset-id]').length>1""")
            deadline = time.monotonic() + 5
            while not held and time.monotonic() < deadline:
                delayed.wait_for_timeout(25)
            assert held, 'The initial project request was not intercepted'
            blocked_asset = delayed.locator(f'[data-asset-id="{assets["floor"]}"]')
            expect(blocked_asset).to_have_attribute('aria-pressed', 'false')
            box = blocked_asset.bounding_box()
            delayed.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
            expect(blocked_asset).to_have_attribute('aria-pressed', 'false')
            held.pop().continue_()
            expect(delayed.locator('[data-builder-form] [name=name]')).to_have_value(final_name)
            expect(delayed.locator('[data-builder-object-count]')).to_have_text('149 objects')
            delayed_ctx.close()
            records.append({'case': 'project-bootstrap-controls', 'newAssetControlsBlockedUntilLoad': True})

            page.locator('[data-builder-tool=select]').click(); click_cell(6, 2)
            builder_sidebar(page, 'selection')
            invalid_endpoint = page.locator('[data-builder-property=x2]')
            invalid_endpoint.fill('999')
            unexpected_posts = []

            def observe_invalid_save(request):
                if request.method == 'POST' and request.url.endswith('/map-builder/projects/' + project_id):
                    unexpected_posts.append(request.url)

            page.on('request', observe_invalid_save)
            invalid_endpoint.press('Control+s')
            expect(page.locator('[data-builder-notice]')).to_have_attribute('data-tone', 'error')
            expect(page.locator('[data-map-builder]')).to_have_attribute('aria-busy', 'false')
            assert not unexpected_posts, unexpected_posts
            assert not invalid_endpoint.evaluate('input=>input.checkValidity()')
            invalid_endpoint.fill('7'); invalid_endpoint.press('Tab')
            page.remove_listener('request', observe_invalid_save)
            assert page.request.get(api + '/projects/' + project_id).json()['project']['document']['doors'][0]['x2'] == 7
            records.append({'case': 'invalid-focused-selection-save', 'noInvalidWriteSent': True,
                            'persistedDoorPreserved': True})

            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.status
            page.wait_for_url(f'**/game/{seed["campaign"]}')
            # The successful UI immediately leaves the Studio. Read the durable
            # result instead of racing Chromium's discarded response body.
            published_project = page.request.get(api + '/projects/' + project_id).json()['project']
            scene_id = published_project['sceneId']
            page.wait_for_function('id=>gravewrightMaps?.current?.id===id', arg=scene_id)
            persistence = inspect(scene_id)
            scene = persistence['scene']
            assert persistence['sceneCount'] == baseline['sceneCount'] + 1
            assert persistence['broadcast'] == baseline['broadcast'], 'Generation changed the player broadcast'
            assert scene['width'] == scene['height'] == 768 and scene['folder'] == seed['folder'], scene
            assert len([tile for tile in scene['tiles'] if tile['lod'] == 0]) == 4, scene['tiles']
            walls = [row['data'] for row in scene['objects'] if row['kind'] == 'walls']
            assert len(walls) == 6 and len([wall for wall in walls if wall['kind'] == 'door']) == 1, walls
            door = next(wall for wall in walls if wall['kind'] == 'door')
            assert (door['x1'], door['y1'], door['x2'], door['y2']) == (320, 128, 448, 128), door
            solid_top = [wall for wall in walls if wall['kind'] == 'wall' and wall['y1'] == wall['y2'] == 128]
            assert sorted((wall['x1'], wall['x2']) for wall in solid_top) == [(128, 320), (448, 640)], solid_top
            manifest = page.request.get(f'/api/maps/{scene_id}/manifest')
            assert manifest.ok and manifest.json()['width'] == 768, manifest.text()
            page.screenshot(path=str(output / 'generated-native-scene-gm.png'))
            records.append({'case': 'generate-tiled-native-scene', 'scene': scene_id, 'width': 768,
                            'height': 768, 'fullResolutionTiles': 4, 'nativeSegments': 6,
                            'doorReplacesBlockingWall': True, 'broadcastPreserved': True})

            fixture_actor = inspect(scene_id, prepare=True)
            player_ctx = context('player'); player = player_ctx.new_page()
            records.append(native_room(page, player, seed, scene_id, fixture_actor['token'], output))
            player_ctx.close()

            # Revisit the saved source with long authored content and populated
            # asset/project libraries in every supported review viewport/locale.
            long_name = 'São João — ' + 'Long authored workshop map name ' * 3
            for width, height in [(1440, 900), (390, 844), (320, 700)]:
                layout_ctx = context(width=width, height=height); layout = layout_ctx.new_page()
                layout.goto(builder + '?project=' + project_id)
                for locale in ('en', 'pt-BR', 'es'):
                    change_locale(layout, locale, seed['campaign'])
                    layout.goto(builder + '?project=' + project_id)
                    layout.wait_for_function('parseInt(document.querySelector("[data-builder-object-count]")?.textContent)===149')
                    dismiss = layout.locator('[data-builder-dismiss]')
                    if dismiss.is_visible():
                        dismiss.click()
                    assert layout.locator('html').get_attribute('lang') == locale
                    expected_words = {
                        'en': ('Generate scene', 'Projects', 'Select', '149 objects'),
                        'pt-BR': ('Gerar cena', 'Projetos', 'Selecionar', '149 objetos'),
                        'es': ('Generar escena', 'Proyectos', 'Seleccionar', '149 objetos'),
                    }[locale]
                    expect(layout.locator('[data-builder-generate]')).to_have_text(expected_words[0])
                    builder_sidebar(layout, 'projects')
                    expect(layout.locator('[data-builder-sidebar-tab=projects][role=tab]')).to_have_text(expected_words[1])
                    expect(layout.locator('[data-builder-tool=select]')).to_have_attribute('aria-label', expected_words[2])
                    expect(layout.locator('[data-builder-object-count]')).to_have_text(expected_words[3])
                    assert layout.locator('[data-builder-form] [name=name]').input_value() in (authored_name, long_name[:120])
                    builder_sidebar(layout, 'settings')
                    name = layout.locator('[data-builder-form] [name=name]')
                    if locale == 'pt-BR' and width == 1440:
                        name.fill(authored_name); name.press('Tab')
                        dismiss = layout.locator('[data-builder-dismiss]')
                        if dismiss.is_visible():
                            dismiss.click()
                        builder_tool(layout, 'select')
                        layout.locator('[data-builder-fit]').click()
                        selected_point = layout.locator('[data-builder-canvas]').evaluate("""svg=>{
                          const p=new DOMPoint(6,2).matrixTransform(svg.getScreenCTM());return {x:p.x,y:p.y};
                        }""")
                        layout.mouse.click(selected_point['x'], selected_point['y'])
                        builder_sidebar(layout, 'selection')
                        expect(layout.locator('[data-builder-property=x1]')).to_be_visible()
                        layout.screenshot(path=str(output / 'approved-studio-pt-BR-1440.png'), full_page=True)
                        builder_sidebar(layout, 'settings')
                    name.fill(long_name[:120]); name.press('Tab')
                    builder_tool(layout, 'select')
                    position = layout.locator('[data-builder-canvas]').evaluate("""svg=>{
                      const p=new DOMPoint(6,2).matrixTransform(svg.getScreenCTM());return {x:p.x,y:p.y};
                    }""")
                    layout.mouse.click(position['x'], position['y'])
                    panels = ['workspace', 'library', 'layers', 'selection', 'settings', 'projects']
                    for panel in panels:
                        if panel == 'workspace':
                            builder_workspace(layout)
                            expect(layout.locator('[data-builder-viewport]')).to_be_visible()
                            canvas_box = layout.locator('[data-builder-viewport]').bounding_box()
                            rail_box = layout.locator('.map-builder__tool-rail').bounding_box()
                            assert canvas_box['height'] >= 180 and canvas_box['width'] >= width - rail_box['width'] - 12, canvas_box
                        elif panel == 'library':
                            builder_sidebar(layout, panel)
                            expect(layout.locator('.map-builder__asset-dock')).to_be_visible()
                        else:
                            builder_sidebar(layout, panel)
                            expect(layout.locator(f'[data-builder-sidebar-panel={panel}]')).to_be_visible()
                        if panel == 'selection':
                            expect(layout.locator('[data-builder-property=x1]')).to_have_value('5')
                            expect(layout.locator('[data-builder-property=x1]')).to_be_visible()
                        metrics = layout.locator('[data-map-builder]').evaluate(MEASURE)
                        assert not metrics['tiny'], (locale, width, panel, metrics['tiny'])
                        assert not metrics['overflow'] and metrics['scrollWidth'] <= width + 1, (locale, width, panel, metrics)
                        geometry = approved_studio_geometry(layout)
                        layout.screenshot(path=str(output / f'studio-{locale}-{width}-{panel}.png'), full_page=True)
                        records.append({'case': 'studio-layout', 'locale': locale, 'width': width,
                                        'panel': panel, **metrics, 'geometry': geometry})
                    builder_sidebar(layout, 'review')
                    expect(layout.locator('[data-builder-review-panel]')).to_be_visible()
                    review_metrics = layout.locator('[data-map-builder]').evaluate(MEASURE)
                    assert not review_metrics['tiny'] and not review_metrics['overflow'], (locale, width, review_metrics)
                    layout.screenshot(path=str(output / f'studio-{locale}-{width}-review.png'), full_page=True)
                    records.append({'case': 'studio-review-layout', 'locale': locale, 'width': width,
                                    **review_metrics})
                layout_ctx.close()

            for role in ('player', 'streamer'):
                denied = context(role)
                response = denied.request.get(builder)
                assert response.status == 404, (role, response.status)
                response = denied.request.get(api)
                assert response.status in (403, 404), (role, response.status, response.text())
                response = denied.request.get(api + '/projects/' + project_id)
                assert response.status in (403, 404), (role, response.status, response.text())
                records.append({'case': 'studio-permissions', 'role': role, 'sourceHidden': True})
                denied.close()

            # The shared VTT library may remove a texture after a project has
            # been saved. Its editable geometry must remain usable afterward.
            before_delete = page.request.get(api + '/projects/' + project_id).json()['project']
            before_copy_delete = page.request.get(api + '/projects/' + copy_project['id']).json()['project']
            deleted = page.evaluate("""async args=>{
              const csrf=await(await fetch('/__gravewright/csrf')).json();
              const response=await fetch('/api/containers/'+args.campaign+'/library/assets/delete',{
                method:'POST',headers:{[csrf.header]:csrf.token,'Content-Type':'application/json'},
                body:JSON.stringify({asset_id:args.asset})});
              return {status:response.status,result:await response.json()};
            }""", {'campaign': seed['campaign'], 'asset': assets['floor']})
            assert deleted['status'] == 200, deleted
            cleaned = page.request.get(api + '/projects/' + project_id).json()['project']
            cleaned_copy = page.request.get(api + '/projects/' + copy_project['id']).json()['project']
            for previous, current in [(before_delete, cleaned), (before_copy_delete, cleaned_copy)]:
                assert current['version'] == previous['version'] + 1, (previous, current)
                assert current['document']['floors'][0]['assetId'] is None
                assert all(asset['assetId'] != assets['floor'] for asset in current['document']['assets'])
                for kind, amount in [('floors', floor_tiles), ('walls', 4), ('doors', 1)]:
                    assert len(current['document'][kind]) == amount, current
            change_locale(page, 'en', seed['campaign'])
            page.goto(builder + '?project=' + project_id)
            count(room_count)
            expect(page.locator('[data-builder-form] [name=name]')).to_have_value(authored_name)
            recovered_after_delete = save(page, 'São João — Playable without the removed texture')['project']
            assert recovered_after_delete['document']['floors'][0]['assetId'] is None
            with page.expect_response(lambda response: response.url.endswith('/generate')) as regenerated:
                page.locator('[data-builder-generate]').click()
            assert regenerated.value.ok, regenerated.value.status
            page.wait_for_url(f'**/game/{seed["campaign"]}')
            replacement_scene = page.request.get(api + '/projects/' + project_id).json()['project']['sceneId']
            assert replacement_scene != scene_id
            page.wait_for_function('id=>window.gravewrightMaps?.current?.id===id', arg=replacement_scene)
            replaced = inspect(replacement_scene)
            assert replaced['sceneCount'] == baseline['sceneCount'] + 2
            assert len([row for row in replaced['scene']['objects'] if row['kind'] == 'walls']) == 6
            assert len([tile for tile in replaced['scene']['tiles'] if tile['lod'] == 0]) == 4
            page.screenshot(path=str(output / 'generated-after-texture-removal.png'))
            records.append({'case': 'removed-texture-recovery', 'allProjectVersionsAdvanced': True,
                            'classificationRemoved': True, 'geometryPreserved': True,
                            'reopenedEditedSavedAndGenerated': True, 'newScene': replacement_scene})
            records.extend(independent_doors(context, seed, output, inspect, assets['door']))
        except Exception:
            if not page.is_closed():
                page.screenshot(path=str(output / 'failure-main-page.png'), full_page=True)
            raise
        finally:
            ctx.close(); browser.close()
    real_failures = [request for request in failed_requests if request['error'] != 'net::ERR_ABORTED']
    assert not errors, errors
    assert not real_failures, real_failures
    assert not native_dialogs, native_dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors,
            'failedRequests': failed_requests, 'nativeDialogs': native_dialogs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--inspect', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--prepare-scene', help=argparse.SUPPRESS)
    parser.add_argument('--prepare-legacy-project', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--scene', help=argparse.SUPPRESS)
    parser.add_argument('--fixture', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--port', type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve:
        serve(args.fixture, args.port); return
    if args.inspect or args.prepare_scene or args.prepare_legacy_project:
        inspect_fixture(args.fixture, args.prepare_scene or args.scene, bool(args.prepare_scene),
                        args.prepare_legacy_project); return
    output = (args.output or ROOT / 'data/map-builder-studio' /
              datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError('Use a fresh, empty output directory.')
    output.mkdir(parents=True, exist_ok=True)
    fixture = output / 'fixture'; fixture.mkdir()
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0)); port = connection.getsockname()[1]
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
                    raise RuntimeError(f'Fixture server exited; inspect {output / "server.log"}')
                try:
                    with urlopen(base, timeout=1): break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Fixture server did not become ready.')
            seed = json.loads((fixture / 'seed.json').read_text(encoding='utf-8'))

            def inspect(scene=None, prepare=False, legacy=False):
                arguments = ['--fixture', str(fixture)]
                if legacy:
                    arguments += ['--prepare-legacy-project']
                else:
                    arguments += ['--prepare-scene', scene] if prepare else ['--inspect']
                if scene and not prepare:
                    arguments += ['--scene', scene]
                return json.loads(subprocess.check_output(
                    [*command, *arguments], cwd=ROOT, env=os.environ.copy(), text=True))

            report = check_browser(base, seed, output, args.browser_executable, inspect)
            (output / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
            print(json.dumps({'passed': True, 'cases': len(report['cases']), 'report': str(output / 'report.json')}))
        except Exception:
            (output / 'failure.txt').write_text(traceback.format_exc(), encoding='utf-8')
            raise
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill(); server.wait()
            (output / 'server-exit.json').write_text(json.dumps(
                {'pid': server.pid, 'exitCode': server.returncode}), encoding='utf-8')


if __name__ == '__main__':
    main()
