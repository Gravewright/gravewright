"""Build, organize and safely update a larger Map Builder scene.

Uses only disposable campaigns, generated artwork, databases and portable tools.
The real browser drives authoring and native VTT commands; inspection is confined
to this scenario's database and creates one explicitly synthetic test token.
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

from map_builder import (ROOT, MEASURE, builder_library_settings, builder_sidebar,
                         builder_tool, builder_workspace, change_locale,
                         fixture_environment, serve)
from map_builder_studio import approved_studio_geometry, synthetic_image
from map_builder_reference import upload_asset, wait_ready


def inspect_fixture(fixture, scene_id=None, prepare=False):
    if os.environ.get('PYTHON_DOTENV_DISABLED') != '1' or (
            Path(os.environ.get('GRAVEWRIGHT_DATABASE', '')).resolve()
            != (fixture / 'review.sqlite3').resolve()):
        raise RuntimeError('Refusing inspection outside the disposable fixture.')
    import django
    django.setup()
    from gravewright.actors.models import Actor
    from gravewright.maps import services
    from gravewright.maps.models import Broadcast, MapBuilderProject, Scene
    from gravewright.tokens.models import Token
    result = {'sceneCount': Scene.objects.count(),
              'broadcast': list(Broadcast.objects.values('campaign_id', 'scene_id'))}
    if scene_id:
        seed = json.loads((fixture / 'seed.json').read_text(encoding='utf-8'))
        scene = Scene.objects.get(pk=scene_id, campaign_id=seed['campaign'])
        if prepare:
            actor = Actor.objects.create(campaign=scene.campaign, name='Synthetic manual explorer')
            Token.objects.create(scene=scene, actor=actor, grid_x=6, grid_y=6,
                                 vision_enabled=True, vision_range=16)
        result['scene'] = {
            'id': str(scene.pk), 'block': str(scene.block_id), 'version': scene.version,
            'manifest': services.manifest(scene),
            'objects': list(scene.elements.order_by('pk').values('id', 'kind', 'data', 'version')),
            'tokens': list(scene.tokens.values('id', 'grid_x', 'grid_y', 'version')),
            'tiles': list(scene.tiles.order_by('lod', 'x', 'y').values('lod', 'x', 'y', 'file')),
            'generation': MapBuilderProject.objects.get(scene=scene).generation,
        }
    print(json.dumps(result, default=str, sort_keys=True))


def decoration_image():
    from PIL import Image, ImageDraw
    image = Image.new('RGBA', (128, 64), '#813f28')
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((3, 3, 124, 60), radius=8, fill='#b77539', outline='#f0c987', width=4)
    for x in range(16, 128, 24):
        draw.line((x, 6, x, 58), fill='#4c291b', width=3)
    content = BytesIO(); image.save(content, 'PNG')
    return content.getvalue()


def large_browser(base, seed, output, executable):
    """Measure real input with 1,000 editable objects without a timing budget."""
    from playwright.sync_api import expect, sync_playwright
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        ctx = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        ctx.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = ctx.new_page(); page.on('pageerror', lambda error: errors.append(str(error)))
        builder = f"/game/{seed['campaign']}/map-builder"
        try:
            page.goto(builder)
            expect(page.locator('[data-map-builder]')).to_be_visible()
            project_id = page.evaluate("""async campaign=>{
              const projectId=crypto.randomUUID(),layerId=crypto.randomUUID();
              const document={schemaVersion:3,name:'Synthetic 1,000-object workshop',columns:50,rows:35,
                cellSize:32,background:'#253038',layers:[{id:layerId,name:'Many floors',visible:true,locked:false}],
                floors:Array.from({length:1000},(_,i)=>({id:crypto.randomUUID(),assetId:null,layerId,
                  x:i%40,y:Math.floor(i/40),width:1,height:1,rotation:0})),
                walls:[],doors:[],decorations:[],lights:[],assets:[]};
              const csrf=await(await fetch('/__gravewright/csrf')).json();
              const response=await fetch('/api/containers/'+campaign+'/map-builder/projects/'+projectId,
                {method:'POST',headers:{'Content-Type':'application/json',[csrf.header]:csrf.token},
                 body:JSON.stringify({request_id:crypto.randomUUID(),expected_version:0,folder_id:null,document})});
              if(!response.ok)throw new Error(await response.text());return projectId;
            }""", seed['campaign'])
            page.goto(builder + '?project=' + project_id)
            expect(page.locator('[data-builder-floors] [data-object-id]')).to_have_count(1000)
            page.locator('[data-builder-viewport]').focus()
            start = time.perf_counter(); page.keyboard.press('Control+a')
            expect(page.locator('[data-builder-selected-count]')).to_have_attribute('data-builder-selected-count', '1000')
            selected_ms = (time.perf_counter() - start) * 1000
            points = page.locator('[data-builder-canvas]').evaluate("""svg=>[.5,1].map(v=>{
              const p=new DOMPoint(v,v).matrixTransform(svg.getScreenCTM());return {x:p.x,y:p.y};})""")
            start = time.perf_counter()
            page.mouse.move(points[0]['x'], points[0]['y']); page.mouse.down()
            page.mouse.move(points[1]['x'], points[1]['y'], steps=4); page.mouse.up()
            moved_ms = (time.perf_counter() - start) * 1000
            with page.expect_response(lambda response: response.request.method == 'POST'
                                      and response.url.endswith('/projects/' + project_id)) as saved:
                page.locator('[data-builder-save]').click()
            assert saved.value.ok, saved.value.text()
            floors = saved.value.json()['project']['document']['floors']
            assert len(floors) == 1000 and floors[0]['x'] == floors[0]['y'] == .5
            assert floors[-1]['x'] == 39.5 and floors[-1]['y'] == 24.5
            page.locator('[data-builder-viewport]').focus(); page.keyboard.press('Control+z')
            expect(page.locator('[data-builder-floors] [data-object-id]').first).to_have_attribute('x', '0')
            page.screenshot(path=str(output / 'large-project-1000.png'))
            assert not errors, errors
            return {'passed': True, 'cases': [{'case': 'large-project-real-input', 'objects': 1000,
                    'selectAllElapsedMs': round(selected_ms, 2), 'groupDragElapsedMs': round(moved_ms, 2),
                    'allObjectsMovedExactly': True, 'undoRestoresGeometry': True}], 'pageErrors': errors}
        except Exception:
            page.screenshot(path=str(output / 'failure-large.png'), full_page=True); raise
        finally: ctx.close(); browser.close()


def check_browser(base, seed, output, executable, inspect):
    from playwright.sync_api import expect, sync_playwright
    errors, failed, dialogs, records = [], [], [], []
    builder = f"{base}/game/{seed['campaign']}/map-builder"
    api = f"/api/containers/{seed['campaign']}/map-builder"
    baseline = inspect()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**({'executable_path': str(executable)} if executable else {}))

        def context(width=1440, height=900):
            ctx = browser.new_context(base_url=base, viewport={'width': width, 'height': height})
            ctx.add_cookies([{**seed['sessions']['gm'], 'url': base}])
            def observe(page):
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('requestfailed', lambda request: failed.append({'url': request.url, 'error': request.failure}))
                def dialog(value):
                    dialogs.append({'type': value.type, 'message': value.message}); value.dismiss()
                page.on('dialog', dialog)
            ctx.on('page', observe)
            return ctx

        ctx = context(); page = ctx.new_page()
        try:
            page.goto(builder + '?folder=' + seed['folder'])
            wait_ready(page)
            builder_sidebar(page, 'settings')
            for name, value in [('name', 'São João — Expanded synthetic workshop'), ('columns', '20'),
                                ('rows', '16'), ('cellSize', '64')]:
                field = page.locator(f'[data-builder-form] [name={name}]')
                field.fill(value); field.press('Tab')
            page.locator('[data-builder-fit]').click()

            def field(selector, value):
                control = page.locator(selector)
                control.fill(str(value)); control.dispatch_event('change')

            def brush(tool, **values):
                builder_tool(page, tool)
                if tool != 'light':
                    page.locator('[data-builder-brush-material]').select_option(assets[tool])
                for name, value in values.items(): field(f'[data-builder-brush={name}]', value)

            def point(x, y):
                builder_workspace(page)
                return page.locator('[data-builder-canvas]').evaluate("""(svg,p)=>{
                  const q=new DOMPoint(p.x,p.y).matrixTransform(svg.getScreenCTM());return {x:q.x,y:q.y};
                }""", {'x': x, 'y': y})

            def click(x, y, modifiers=None):
                p = point(x, y)
                for key in modifiers or []: page.keyboard.down(key)
                page.mouse.click(p['x'], p['y'])
                for key in reversed(modifiers or []): page.keyboard.up(key)

            def drag(x1, y1, x2, y2):
                a, b = point(x1, y1), point(x2, y2)
                page.mouse.move(a['x'], a['y']); page.mouse.down()
                page.mouse.move(b['x'], b['y'], steps=8); page.mouse.up()

            def keyboard(key):
                page.locator('[data-builder-viewport]').focus(); page.keyboard.press(key)

            def count(value): expect(page.locator('[data-builder-object-count]')).to_have_text(f'{value} objects')

            def update_scene():
                builder_sidebar(page, 'review')
                page.locator('[data-builder-review-update]').click()

            def save():
                if page.locator('[data-map-builder]').get_attribute('data-save-state') == 'saved':
                    project_id = page.evaluate("new URL(location.href).searchParams.get('project')")
                    page.locator('[data-builder-save]').click()
                    return page.request.get(api + '/projects/' + project_id).json()['project']
                with page.expect_response(lambda response: '/map-builder/projects/' in response.url
                                          and response.request.method == 'POST'
                                          and not response.url.endswith(('/generate', '/update'))) as response:
                    page.locator('[data-builder-save]').click()
                assert response.value.ok, response.value.text()
                return response.value.json()['project']

            assets = {}
            for kind in ('floor', 'wall', 'door', 'decoration'):
                builder_sidebar(page, 'library')
                assets[kind] = upload_asset(page, kind,
                    f'Synthetic {kind} — original authored filename.png',
                    decoration_image() if kind == 'decoration' else synthetic_image(kind))['id']
                page.locator(f'[data-asset-id="{assets[kind]}"]').click()
                builder_library_settings(page)
                page.locator('[data-builder-asset-role]').select_option(kind)
                field('[data-builder-asset-name]', f'Own {kind} alias — São João')
                field('[data-builder-asset-collection]', 'Tavern fixtures' if kind == 'decoration' else 'Room structure')
            page.locator('[data-builder-collection-filter]').select_option('Room structure')
            expect(page.locator(f'[data-asset-id="{assets["decoration"]}"]')).to_have_count(0)
            page.locator('[data-builder-collection-filter]').select_option('Tavern fixtures')
            expect(page.locator(f'[data-asset-id="{assets["decoration"]}"]')).to_be_visible()
            field('[data-builder-search]', 'São João')
            expect(page.locator(f'[data-asset-id="{assets["decoration"]}"]')).to_be_visible()
            page.locator('[data-builder-search]').fill('absent asset'); page.locator('[data-builder-search]').dispatch_event('input')
            expect(page.locator(f'[data-asset-id="{assets["decoration"]}"]')).to_have_count(0)
            page.locator('[data-builder-search]').fill(''); page.locator('[data-builder-search]').dispatch_event('input')
            page.locator('[data-builder-collection-filter]').select_option('')
            metadata = save()['document']['assets']
            for kind, asset_id in assets.items():
                classified = next(row for row in metadata if row['assetId'] == asset_id)
                assert classified['role'] == kind and classified['name'] == f'Own {kind} alias — São João', classified
                assert classified['collection'] == ('Tavern fixtures' if kind == 'decoration' else 'Room structure'), classified
            catalog = page.request.get(api).json()['assets']
            assert all(next(row for row in catalog if row['id'] == asset_id)['name'] ==
                f'Synthetic {kind} — original authored filename.png' for kind, asset_id in assets.items()), catalog
            records.append({'case': 'project-local-asset-alias-collection-search', 'assets': assets})

            brush('floor', floorSize=3, rotation=90)
            page.locator('[data-builder-paint-mode]').select_option('brush')
            click(1.1, 1.1); count(9)
            stamp = save()['document']['floors']
            assert len(stamp) == 9 and all(row['width'] == row['height'] == 1 and row['rotation'] == 90
                                          and row['assetId'] == assets['floor'] for row in stamp), stamp
            assert {(row['x'], row['y']) for row in stamp} == {(x, y) for x in range(1, 4) for y in range(1, 4)}, stamp
            keyboard('Control+z'); count(0)
            brush('floor', floorSize=1, rotation=0)
            page.locator('[data-builder-paint-mode]').select_option('rectangle')
            drag(1, 1, 11, 11)
            floor_count = 100
            count(floor_count)
            room_floor = save()['document']['floors']
            assert len(room_floor) == floor_count and all(row['width'] == row['height'] == 1
                and row['rotation'] == 0 and row['assetId'] == assets['floor'] for row in room_floor), room_floor
            assert {(row['x'], row['y']) for row in room_floor} == {(x, y) for x in range(1, 11) for y in range(1, 11)}
            brush('wall', thickness=.3)
            expect(page.locator('[data-builder-toggle-snap]')).to_have_attribute('aria-pressed', 'true')
            drag(2.12, 2.12, 10.12, 2.3); count(floor_count + 1)
            first_wall = save()['document']['walls'][0]
            assert first_wall['thickness'] == .3 and tuple(first_wall[key] for key in ('x1', 'y1', 'x2', 'y2')) == (2, 2, 10, 2), first_wall
            page.locator('[data-builder-toggle-snap]').click()
            drag(12.12, 12.12, 17.12, 13.37); count(floor_count + 2)
            free_wall = save()['document']['walls'][-1]
            assert tuple(free_wall[key] for key in ('x1', 'y1', 'x2', 'y2')) == (12.12, 12.12, 17.12, 13.37), free_wall
            keyboard('Control+z'); count(floor_count + 1)
            page.locator('[data-builder-toggle-snap]').click()
            for span in [(10, 2, 10, 10), (10, 10, 2, 10), (2, 10, 2, 2)]: drag(*span)
            structure_count = floor_count + 5
            brush('door', thickness=.2); drag(5, 2, 7, 2); count(structure_count)
            records.append({'case': 'configurable-brushes-and-grid-snapping', 'floorSize': 3,
                            'floorRotation': 90, 'floorTiles': floor_count, 'wallThickness': .3,
                            'doorThickness': .2, 'snappedGridEdges': True, 'unsnappedFractionalDiagonal': True})

            builder_sidebar(page, 'layers')
            field('[data-builder-layer-name]', 'Furniture — São João')
            page.locator('[data-builder-layer-add]').click()
            layers = page.locator('[data-builder-project-layer]')
            expect(layers).to_have_count(2)
            furniture = page.locator('[data-builder-project-layer][data-active=true]').get_attribute('data-builder-project-layer')
            page.locator(f'[data-builder-layer-active="{furniture}"]').click()
            brush('decoration', width=2, height=1, rotation=90); click(14, 4); count(structure_count + 1)
            brush('light', lightRadius=3, lightDimRadius=5, lightColor='#e8ac52', lightIntensity=.65)
            object_count = structure_count + 2
            click(16, 8); count(object_count)
            doc = save()['document']
            deco, lamp = doc['decorations'][0], doc['lights'][0]
            assert deco['layerId'] == lamp['layerId'] == furniture, doc
            assert (deco['width'], deco['height'], deco['rotation']) == (2, 1, 90), deco
            assert (lamp['brightRadius'], lamp['dimRadius'], lamp['color'], lamp['intensity']) == (3, 5, '#e8ac52', .65), lamp
            records.append({'case': 'decoration-and-light-authoring', 'decoration': deco, 'light': lamp})

            builder_sidebar(page, 'layers')
            page.locator(f'[data-builder-layer-visible="{furniture}"]').uncheck()
            expect(page.locator('[data-builder-decorations] [data-object-id]')).to_be_hidden()
            expect(page.locator('[data-builder-lights] [data-object-id]')).to_be_hidden()
            page.locator(f'[data-builder-layer-visible="{furniture}"]').check()
            page.locator(f'[data-builder-layer-locked="{furniture}"]').check()
            builder_tool(page, 'select'); keyboard('Control+a')
            expect(page.locator('[data-builder-selected-count]')).to_have_attribute('data-builder-selected-count', str(structure_count))
            keyboard('Delete'); count(2)
            keyboard('Control+z'); count(object_count)
            builder_sidebar(page, 'layers')
            page.locator(f'[data-builder-layer-locked="{furniture}"]').uncheck()
            field(f'[data-builder-layer-title="{furniture}"]', 'Furniture renamed — authored')
            page.locator(f'[data-builder-project-layer="{furniture}"] [data-builder-layer-move="-1"]').click()
            expect(page.locator('[data-builder-project-layer]').last).to_have_attribute('data-builder-project-layer', furniture)
            records.append({'case': 'custom-layer-order-name-visibility-lock', 'layerId': furniture,
                            'lockedObjectsExcludedFromSelectAllAndDelete': True})

            builder_tool(page, 'select'); keyboard('Escape')
            click(deco['x'] + deco['width'] / 2, deco['y'] + deco['height'] / 2)
            click(lamp['x'], lamp['y'], ['Shift'])
            expect(page.locator('[data-builder-selected-count]')).to_have_attribute('data-builder-selected-count', '2')
            keyboard('Control+d'); count(object_count + 2)
            duplicated = save()['document']
            assert len(duplicated['decorations']) == len(duplicated['lights']) == 2
            assert len({row['id'] for kind in ('decorations', 'lights') for row in duplicated[kind]}) == 4
            keyboard('Control+z'); count(object_count)
            keyboard('Control+Shift+z'); count(object_count + 2)
            keyboard('Control+z'); count(object_count)
            keyboard('Escape'); drag(12, 2, 19, 11)
            expect(page.locator('[data-builder-selected-count]')).to_have_attribute('data-builder-selected-count', '2')
            before_rotation = save()['document']
            keyboard('r')
            rotated = save()['document']
            assert rotated['decorations'][0]['rotation'] == (before_rotation['decorations'][0]['rotation'] + 90) % 360
            assert rotated['lights'][0]['x'] != before_rotation['lights'][0]['x']
            keyboard('Control+z')
            builder_sidebar(page, 'layers')
            field('[data-builder-layer-name]', 'Ambient fixtures'); page.locator('[data-builder-layer-add]').click()
            ambient = page.locator('[data-builder-project-layer][data-active=true]').get_attribute('data-builder-project-layer')
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=layerId]').select_option(ambient)
            moved = save()['document']
            assert moved['decorations'][0]['layerId'] == moved['lights'][0]['layerId'] == ambient
            records.append({'case': 'shift-marquee-select-duplicate-rotate-move-layer-history',
                            'multiSelection': 2, 'duplicateNewIds': True, 'undoRedo': True})

            project = save(); project_id = project['id']
            page.reload(); wait_ready(page); count(object_count)
            persisted = page.request.get(api + '/projects/' + project_id).json()['project']
            assert persisted['document'] == project['document']
            count(object_count)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_function('!!window.gravewrightMaps?.current && !!gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            project = page.request.get(api + '/projects/' + project_id).json()['project']
            scene_id = project['sceneId']
            fixture = inspect(scene_id, True); scene = fixture['scene']
            assert fixture['sceneCount'] == baseline['sceneCount'] + 1
            assert fixture['broadcast'] == baseline['broadcast']
            native = page.request.get(f'/api/maps/{scene_id}/state').json()
            assert len(native['images']) == len(native['lights']) == 1, native
            assert native['images'][0]['asset_id'] == assets['decoration']
            assert (native['images'][0]['x'], native['images'][0]['y'], native['images'][0]['rotation']) == (
                (deco['x'] + deco['width'] / 2) * 64,
                (deco['y'] + deco['height'] / 2) * 64, deco['rotation']), native['images'][0]
            assert native['lights'][0]['bright_radius'] == 3 and native['lights'][0]['dim_radius'] == 5
            page.wait_for_function('gravewrightMaps.board?.viewport()?.scale>0')
            expect(page.locator('.game-board__surface canvas')).to_be_visible()
            page.screenshot(path=str(output / 'expanded-native-scene.png'))
            records.append({'case': 'generate-native-decoration-light-and-tiled-map', 'scene': scene_id,
                            'block': scene['block'], 'tileCount': len(scene['tiles']), 'sourceSurvivesReload': True})

            def native_command(area, action, data):
                return page.evaluate("""args=>gravewrightRealtime.mapCommand('objects',{
                  mapId:args.scene,area:args.area,action:args.action,data:args.data})""",
                                     {'scene': scene_id, 'area': area, 'action': action, 'data': data})
            def map_sample(name, x, y):
                from PIL import Image, ImageStat
                p = page.evaluate("""p=>{
                  const surface=document.querySelector('.game-board__surface').getBoundingClientRect();
                  const view=gravewrightMaps.board.viewport();
                  return {x:surface.x+view.x+p.x*64*view.scale,y:surface.y+view.y+p.y*64*view.scale};
                }""", {'x': x, 'y': y})
                image = Image.open(BytesIO(page.screenshot(path=str(output / name)))).convert('RGB')
                px, py = round(p['x']), round(p['y'])
                assert 5 <= px < image.width - 5 and 5 <= py < image.height - 5, p
                return ImageStat.Stat(image.crop((px - 4, py - 4, px + 5, py + 5))).mean

            # The authored warm table must appear on the native canvas, not
            # merely survive as an API record or remain baked into the tiles.
            native_command('lighting', 'update', {'mode': 'none', 'darkness': 0, 'lights_out': False})
            deadline = time.monotonic() + 8
            table_rgb = [0, 0, 0]
            while time.monotonic() < deadline:
                table_rgb = map_sample('generated-decoration-visible.png',
                                       deco['x'] + deco['width'] / 2 + .1,
                                       deco['y'] + deco['height'] / 2 + .15)
                if table_rgb[0] > table_rgb[1] + 15 and table_rgb[1] > table_rgb[2] + 5: break
                page.wait_for_timeout(150)
            assert table_rgb[0] > table_rgb[1] + 15 and table_rgb[1] > table_rgb[2] + 5, table_rgb
            records.append({'case': 'generated-native-decoration-renders', 'pixelRgb': table_rgb})
            native_command('lighting', 'update', {'mode': 'dynamic', 'darkness': 1, 'lights_out': True})
            generated_light = native['lights'][0]
            def light_sample(name):
                return sum(map_sample(name, lamp['x'] + .5, lamp['y'] + .5)) / 3
            native_command('lights', 'update', {'light_id': generated_light['id'], 'enabled': False})
            page.wait_for_timeout(250)
            dark = light_sample('generated-light-disabled.png')
            native_command('lights', 'update', {'light_id': generated_light['id'], 'enabled': True})
            deadline = time.monotonic() + 8
            bright = dark
            while time.monotonic() < deadline:
                bright = light_sample('generated-light-enabled.png')
                if bright > dark + 5: break
                page.wait_for_timeout(150)
            assert bright > dark + 5, {'disabled': dark, 'enabled': bright}
            records.append({'case': 'generated-native-light-renders', 'disabledPixelBrightness': dark,
                            'enabledPixelBrightness': bright})
            native_command('walls', 'create', {'x1': 850, 'y1': 800, 'x2': 950, 'y2': 800})
            native_command('lights', 'create', {'x': 1000, 'y': 700, 'bright_radius': 1,
                                                'dim_radius': 2, 'color': '#77aaff'})
            native_command('images', 'create', {'asset_id': assets['decoration'], 'x': 1100, 'y': 600,
                                               'scale': .5, 'rotation': 15, 'layer': 'map'})
            before = inspect(scene_id)['scene']
            owned = {row['id'] for row in before['generation']['objects']}
            manual = {row['id']: row for row in before['objects'] if row['id'] not in owned}
            assert len(manual) == 3 and len(before['tokens']) == 1, before
            page.goto(builder + '?project=' + project_id); wait_ready(page)
            count(object_count); builder_tool(page, 'wall'); drag(12, 12, 17, 12); count(object_count + 1)
            with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                update_scene()
            assert updated.value.ok, updated.value.text()
            page.wait_for_function('!!window.gravewrightMaps?.current && !!gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            after = inspect(scene_id)['scene']
            assert after['id'] == before['id'] and after['block'] == before['block']
            assert after['tokens'] == before['tokens']
            assert {row['id']: row for row in after['objects'] if row['id'] in manual} == manual
            assert len(after['objects']) == len(before['objects']) + 1
            assert after['manifest']['tileUrlTemplate'] != before['manifest']['tileUrlTemplate']
            assert after['tiles'] != before['tiles']
            expect(page.locator('.game-board__surface canvas')).to_be_visible()
            page.screenshot(path=str(output / 'updated-native-scene-preserves-manual.png'))
            page.goto(builder + '?project=' + project_id); wait_ready(page); count(object_count + 1)
            with page.expect_response(lambda response: response.url.endswith('/update')) as repeated:
                update_scene()
            assert repeated.value.ok, repeated.value.text()
            repeated_scene = inspect(scene_id)['scene']
            assert len(repeated_scene['objects']) == len(after['objects'])
            assert repeated_scene['tokens'] == before['tokens']
            records.append({'case': 'update-same-scene-preserves-manual-content', 'scene': scene_id,
                            'blockUnchanged': True, 'manualObjects': len(manual), 'tokens': 1,
                            'generatedGeometryNotDuplicated': True, 'tileUrlsChanged': True})

            current = page.request.get(api + '/projects/' + project_id).json()['project']
            for project_version, scene_version in [(current['version'] - 1, current['sceneVersion']),
                                                    (current['version'], before['version'])]:
                rejected = page.evaluate("""async args=>{
                  const csrf=await(await fetch('/__gravewright/csrf')).json();
                  const response=await fetch(args.url,{method:'POST',headers:{'Content-Type':'application/json',
                    [csrf.header]:csrf.token},body:JSON.stringify({request_id:crypto.randomUUID(),
                    expected_version:args.projectVersion,expected_scene_version:args.sceneVersion})});
                  return {status:response.status,body:await response.json()};
                }""", {'url': api + '/projects/' + project_id + '/update',
                          'projectVersion': project_version, 'sceneVersion': scene_version})
                assert rejected['status'] == 409, rejected
                assert inspect(scene_id)['scene'] == repeated_scene
            records.append({'case': 'stale-project-and-scene-update-conflicts', 'status': 409,
                            'currentSceneNotOverwritten': True})

            # A native edit made after opening the builder must be surfaced as
            # a conflict. It cannot be overwritten by obtaining a new version.
            page.goto(builder + '?project=' + project_id); wait_ready(page); count(object_count + 1)
            editor_ctx = context(); editor = editor_ctx.new_page()
            try:
                editor.goto(f'/game/{seed["campaign"]}')
                editor.wait_for_function('!!window.gravewrightRealtime && !!gravewrightMaps.current')
                expect(editor.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
                editor.evaluate("id=>gravewrightRealtime.mapCommand('navigate',{mapId:id})", scene_id)
                generated_wall = next(row for row in repeated_scene['objects'] if row['kind'] == 'walls' and row['id'] not in manual)
                editor.evaluate("""args=>gravewrightRealtime.mapCommand('objects',{
                  mapId:args.scene,area:'walls',action:'update',data:{wall_id:args.wall.id,
                    version:args.wall.version,x1:args.wall.data.x1+2}})""",
                                {'scene': scene_id, 'wall': generated_wall})
                conflict_before = inspect(scene_id)['scene']
                with page.expect_response(lambda response: response.url.endswith('/update')) as rejected:
                    update_scene()
                assert rejected.value.status == 409, rejected.value.text()
                expect(page.locator('[data-builder-notice]')).to_be_visible()
                assert inspect(scene_id)['scene'] == conflict_before
                records.append({'case': 'native-generated-object-edit-conflict', 'status': 409,
                                'sceneAndManualContentUntouched': True})
            finally: editor_ctx.close()

            # All new panels, each brush and each object inspector are reviewed
            # with actual saved content and long authored labels in three locales.
            layout_ctx = context(); layout = layout_ctx.new_page()
            try:
                for locale in ('en', 'pt-BR', 'es'):
                    layout.goto(builder + '?project=' + project_id)
                    change_locale(layout, locale, seed['campaign'])
                    layout.goto(builder + '?project=' + project_id)
                    wait_ready(layout)
                    expect(layout.locator('[data-builder-object-count]')).to_have_text(f'{object_count + 1} objects' if locale == 'en' else f'{object_count + 1} objetos')
                    for width, height in ((1586, 992), (1440, 900), (390, 844), (320, 740)):
                        layout.set_viewport_size({'width': width, 'height': height})
                        approved_studio_geometry(layout)
                        for panel in ('library', 'layers', 'selection', 'settings', 'projects'):
                            builder_sidebar(layout, panel)
                            measured = layout.locator('[data-map-builder]').evaluate(MEASURE)
                            assert not measured['tiny'] and not measured['overflow'], (locale, width, panel, measured)
                        builder_sidebar(layout, 'review')
                        measured = layout.locator('[data-map-builder]').evaluate(MEASURE)
                        assert not measured['tiny'] and not measured['overflow'], (locale, width, 'review', measured)
                        for tool in ('floor', 'wall', 'door', 'decoration', 'light'):
                            builder_tool(layout, tool); builder_sidebar(layout, 'library')
                            measured = layout.locator('[data-map-builder]').evaluate(MEASURE)
                            assert not measured['tiny'] and not measured['overflow'], (locale, width, tool, measured)
                        for kind, x, y in [('floor', 6, 6), ('wall', 9, 2), ('door', 6, 2),
                                           ('decoration', deco['x'] + 1, deco['y'] + .5),
                                           ('light', lamp['x'], lamp['y'])]:
                            builder_tool(layout, 'select')
                            layout.locator('[data-builder-viewport]').focus(); layout.keyboard.press('Escape')
                            p = layout.locator('[data-builder-canvas]').evaluate("""(svg,p)=>{
                              const q=new DOMPoint(p.x,p.y).matrixTransform(svg.getScreenCTM());return {x:q.x,y:q.y};
                            }""", {'x': x, 'y': y})
                            layout.mouse.click(p['x'], p['y'])
                            builder_sidebar(layout, 'selection')
                            expect(layout.locator('[data-builder-property=layerId]')).to_be_visible()
                            measured = layout.locator('[data-map-builder]').evaluate(MEASURE)
                            assert not measured['tiny'] and not measured['overflow'], (locale, width, kind, measured)
                        builder_workspace(layout)
                        layout.screenshot(path=str(output / f'expanded-studio-{locale}-{width}.png'))
                        records.append({'case': 'expanded-responsive-layout', 'locale': locale,
                                        'width': width, 'panels': 6, 'brushes': 5, 'inspectors': 5, 'minimumTextPx': 12})
            except Exception:
                layout.screenshot(path=str(output / 'failure-layout.png'), full_page=True)
                raise
            finally: layout_ctx.close()
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            (output / 'failure-browser.json').write_text(json.dumps({'errors': errors, 'failed': failed,
                'dialogs': dialogs, 'cases': records}, indent=2, ensure_ascii=False), encoding='utf-8')
            raise
        finally:
            ctx.close(); browser.close()
    unexpected = [row for row in failed if row['error'] != 'net::ERR_ABORTED']
    assert not errors, errors
    assert not unexpected, unexpected
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'failedRequests': failed, 'nativeDialogs': dialogs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--large-only', action='store_true', help='Measure selection and movement of 1,000 synthetic objects.')
    parser.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--inspect', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--prepare-scene', help=argparse.SUPPRESS)
    parser.add_argument('--scene', help=argparse.SUPPRESS)
    parser.add_argument('--fixture', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--port', type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve: serve(args.fixture, args.port); return
    if args.inspect or args.prepare_scene:
        inspect_fixture(args.fixture, args.prepare_scene or args.scene, bool(args.prepare_scene)); return
    output = (args.output or ROOT / 'data/map-builder-delivery2' /
              datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
    if output.exists() and any(output.iterdir()): raise RuntimeError('Use a fresh empty output directory.')
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
                if server.poll() is not None: raise RuntimeError(f'Fixture exited; inspect {output / "server.log"}')
                try:
                    with urlopen(base, timeout=1): break
                except OSError: time.sleep(.1)
            else: raise RuntimeError('Fixture server did not become ready.')
            seed = json.loads((fixture / 'seed.json').read_text(encoding='utf-8'))
            def inspect(scene=None, prepare=False):
                arguments = ['--fixture', str(fixture)]
                arguments += ['--prepare-scene', scene] if prepare else ['--inspect']
                if scene and not prepare: arguments += ['--scene', scene]
                return json.loads(subprocess.check_output([*command, *arguments], cwd=ROOT,
                                  env=os.environ.copy(), text=True))
            report = large_browser(base, seed, output, args.browser_executable) if args.large_only else check_browser(
                base, seed, output, args.browser_executable, inspect)
            (output / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
            print(json.dumps({'passed': True, 'cases': len(report['cases']), 'report': str(output / 'report.json')}))
        except Exception:
            (output / 'failure.txt').write_text(traceback.format_exc(), encoding='utf-8'); raise
        finally:
            server.terminate()
            try: server.wait(timeout=10)
            except subprocess.TimeoutExpired: server.kill(); server.wait()
            (output / 'server-exit.json').write_text(json.dumps({'pid': server.pid,
                'exitCode': server.returncode}), encoding='utf-8')


if __name__ == '__main__': main()
