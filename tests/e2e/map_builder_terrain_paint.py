"""Review continuous terrain painting with synthetic patterns and real pixels.

Campaigns, source documents, media, native scenes and diagnostics are disposable.
"""
from __future__ import annotations

from base64 import b64decode
from copy import deepcopy
from io import BytesIO
import math
import time
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_free_paint import SVG_RASTER
from map_builder_reference import set_name, upload_asset, wait_ready


CELL = 64
BACKGROUND = (17, 34, 51)


def patterned_texture(first, second):
    """An asymmetric authored repeat makes accidental texture stretching visible."""
    from PIL import Image, ImageDraw

    target = BytesIO()
    with Image.new('RGB', (CELL, CELL), first) as image:
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 15, 63), fill=second)
        draw.rectangle((16, 0, 63, 7), fill=second)
        image.save(target, 'PNG')
    return target.getvalue()


def maximum_delta(a, b):
    return max(abs(first - second) for first, second in zip(a[:3], b[:3]))


def brush_alpha(item, x, y):
    """Independent continuous radial kernel, evaluated at a raster pixel center."""
    brush = item['brush']
    u, v = (x - item['x']) / item['width'], (y - item['y']) / item['height']
    radius_x, radius_y = brush['radius']
    hardness, coverage = brush['hardness'], 0
    for center_u, center_v, strength in brush['points']:
        distance = math.hypot((u - center_u) / radius_x, (v - center_v) / radius_y)
        if distance >= 1:
            continue
        falloff = 1 if distance <= hardness or hardness == 1 else (1 - distance) / (1 - hardness)
        alpha = strength * falloff
        coverage += alpha * (1 - coverage)
    return coverage


def expected_pixel(document, assets, pixel_x, pixel_y):
    """Composite authored material and erase operators by project layer order."""
    x, y = (pixel_x + .5) / CELL, (pixel_y + .5) / CELL
    final = list(BACKGROUND)
    for layer in document['layers']:
        premultiplied, coverage = [0., 0., 0.], 0.
        for item in document['floors']:
            if item['layerId'] != layer['id']:
                continue
            if 'brush' in item:
                alpha = brush_alpha(item, x, y)
            elif item['x'] <= x < item['x'] + item['width'] and item['y'] <= y < item['y'] + item['height']:
                alpha = item.get('paint', {}).get('opacity', 1)
            else:
                alpha = 0
            if item.get('brush', {}).get('operation') == 'erase':
                premultiplied = [value * (1 - alpha) for value in premultiplied]
                coverage *= 1 - alpha
            elif alpha:
                first, second = assets[item['assetId']]
                color = second if pixel_x % CELL < 16 or pixel_y % CELL < 8 else first
                premultiplied = [value * (1 - alpha) + color[index] * alpha
                                 for index, value in enumerate(premultiplied)]
                coverage += alpha * (1 - coverage)
        final = [value * (1 - coverage) + premultiplied[index] for index, value in enumerate(final)]
    return tuple(round(value) for value in final)


def check_probes(image, document, assets, points, label):
    result = []
    for x, y in points:
        pixel_x, pixel_y = round(x * CELL), round(y * CELL)
        expected = expected_pixel(document, assets, pixel_x, pixel_y)
        actual = image.getpixel((pixel_x, pixel_y))[:3]
        assert maximum_delta(expected, actual) <= 5, {
            'case': label, 'point': [x, y], 'expected': expected, 'actual': actual}
        result.append({'point': [x, y], 'expected': expected, 'actual': actual})
    return result


def generated_image(page, project):
    from PIL import Image

    manifest_response = page.request.get(f"/api/maps/{project['sceneId']}/manifest")
    assert manifest_response.ok, manifest_response.text()
    manifest = manifest_response.json()
    level = next(row for row in manifest['levels'] if row['lod'] == 0)
    image = Image.new('RGB', (manifest['width'], manifest['height']))
    for y in range(level['rows']):
        for x in range(level['columns']):
            url = manifest['tileUrlTemplate'].replace('{lod}', '0').replace('{x}', str(x)).replace('{y}', str(y))
            tile = page.request.get(url)
            assert tile.ok, tile.text()
            with Image.open(BytesIO(tile.body())) as source:
                image.paste(source, (x * manifest['tileSize'], y * manifest['tileSize']))
    return image


def check_browser(base, seed, output, executable):
    from PIL import Image, ImageChops
    from playwright.sync_api import expect, sync_playwright

    records, errors, dialogs = [], [], []
    campaign = seed['campaign']
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        review = BuilderReview(page, campaign)
        root = page.locator('[data-map-builder]')
        modes = page.locator('[data-builder-editing-mode]')

        def point(x, y):
            return page.locator('[data-builder-canvas]').evaluate("""(svg,point)=>{
              const p=new DOMPoint(...point).matrixTransform(svg.getScreenCTM());return [p.x,p.y];
            }""", [x, y])

        def stroke(points, hold=0, cancel=False):
            builder_workspace(page)
            page.mouse.move(*point(*points[0])); page.mouse.down()
            for position in points[1:]:
                page.mouse.move(*point(*position), steps=4)
            if hold:
                page.wait_for_timeout(hold)
            if cancel:
                page.keyboard.press('Escape')
            page.mouse.up()

        def control(selector, value):
            field = page.locator(selector)
            field.scroll_into_view_if_needed()
            if field.evaluate('el=>el.tagName') == 'SELECT':
                field.select_option(str(value))
            else:
                field.fill(str(value)); field.dispatch_event('change')

        def terrain(material, size=3, hardness=50, intensity=35, operation='paint'):
            expect(modes).to_have_value('paint')
            page.locator('[data-builder-quick-tool=paint]').click()
            builder_sidebar(page, 'tools')
            control('[data-builder-brush-material]', material)
            control('[data-builder-paint-operation]', operation)
            control('[data-builder-terrain-hardness]', hardness)
            control('[data-builder-terrain-intensity]', intensity)
            field = page.locator('[data-builder-quick-brush-size]')
            field.fill(str(size)); field.press('Enter')
            expect(page.locator('[data-builder-brush=floorSize]')).to_have_value(str(size))
            builder_workspace(page)

        def new_brush(before, after, operation='paint'):
            prior = {item['id'] for item in before['floors']}
            added = [item for item in after['floors'] if item['id'] not in prior]
            assert len(added) == 1, added
            assert added[0]['brush']['operation'] == operation, added
            assert added[0]['brush']['points']
            return added[0]

        def unchanged(project):
            result = review.save()
            assert result['document'] == project['document']
            assert result['version'] == project['version']
            return result

        def resize_brush(delta_x, expected, cancel=False, filename=None):
            builder_workspace(page)
            size = page.locator('[data-builder-quick-brush-size]')
            original = size.input_value()
            start = point(7.25, 7.25)
            page.mouse.move(*start)
            page.keyboard.down('Shift'); page.mouse.down()
            page.mouse.move(start[0] + delta_x, start[1], steps=5)
            expect(page.locator('[data-builder-resize-preview]')).to_have_count(1)
            expect(page.locator('[data-builder-brush-cursor]')).to_have_count(1)
            expect(size).to_have_value(f'{expected:g}')
            if filename:
                page.screenshot(path=str(output / filename))
            if cancel:
                page.keyboard.press('Escape')
            page.mouse.up(); page.keyboard.up('Shift')
            expect(page.locator('[data-builder-resize-preview]')).to_have_count(0)
            expect(size).to_have_value(original if cancel else f'{expected:g}')
            unchanged(project)

        def raster(filename=None):
            encoded = page.evaluate(SVG_RASTER, {'width': 20 * CELL, 'height': 16 * CELL,
                                                'columns': 20, 'rows': 16, 'ids': None})
            image = Image.open(BytesIO(b64decode(encoded.split(',', 1)[1]))).convert('RGB')
            if filename:
                image.save(output / filename)
            return image

        def compare(expected, actual, label):
            assert expected.size == actual.size
            # Wall artwork and native doors have their own rendering tests.
            # This full terrain crop includes every soft/hard/mixed/erased edge.
            with expected.crop((0, 0, 20 * CELL, 13 * CELL)) as a, actual.crop((0, 0, 20 * CELL, 13 * CELL)) as b:
                with ImageChops.difference(a, b) as difference:
                    maximum = max(high for low, high in difference.getextrema())
                    difference.save(output / f'{label}-difference.png')
            assert maximum <= 8, {'case': label, 'maxTerrainRgbDelta': maximum}
            return {'maxTerrainRgbDelta': maximum}

        def native(area, action, data):
            return page.evaluate("""args=>gravewrightRealtime.mapCommand('objects',{
              mapId:args.scene,area:args.area,action:args.action,data:args.data})""",
                                 {'scene': scene_id, 'area': area, 'action': action, 'data': data})

        try:
            page.goto(review.builder); wait_ready(page)
            set_name(page, 'Synthetic continuous terrain preparation')
            colors = [((76, 134, 67), (35, 88, 109)), ((221, 73, 39), (139, 39, 75)),
                      ((48, 79, 207), (100, 163, 224))]
            identifiers = [upload_asset(page, 'floor', f'Synthetic terrain pattern {index}.png',
                                        patterned_texture(*palette))['id']
                           for index, palette in enumerate(colors)]
            green, red, blue = identifiers
            assets = dict(zip(identifiers, colors))
            builder_sidebar(page, 'library')
            page.locator('[data-builder-role=light]').click()
            page.locator('[data-builder-light-preset=torch]').click(); stroke([(12, 12)])
            template = deepcopy(review.save()['document'])
            active, protected = str(uuid4()), str(uuid4())
            base_floor = {'id': str(uuid4()), 'layerId': active, 'assetId': green,
                          'x': 0, 'y': 0, 'width': 20, 'height': 16, 'rotation': 0}
            other_floor = {'id': str(uuid4()), 'layerId': protected, 'assetId': blue,
                           'x': 14, 'y': 9, 'width': 4, 'height': 4, 'rotation': 0}
            wall = {'id': str(uuid4()), 'layerId': active, 'assetId': None,
                    'x1': 2, 'y1': 14, 'x2': 18, 'y2': 14, 'thickness': .4}
            door = {'id': str(uuid4()), 'layerId': active, 'assetId': None,
                    'x1': 9, 'y1': 14, 'x2': 11, 'y2': 14, 'thickness': .4, 'state': 'closed'}
            template.update(name='Synthetic terrain pattern blending and native gates', columns=20, rows=16,
                            cellSize=CELL, background='#112233', layers=[
                                {'id': active, 'name': 'Terrain and architecture', 'visible': True, 'locked': False},
                                {'id': protected, 'name': 'Unchanged locked upper floor', 'visible': True, 'locked': True}],
                            floors=[base_floor, other_floor], walls=[wall], doors=[door])
            for light in template['lights']:
                light['layerId'] = active
            project = review.store(str(uuid4()), 0, seed['folder'], template)
            page.goto(review.builder + '?project=' + project['id']); wait_ready(page)
            expect(modes).to_have_value('tiles')
            unchanged(project)
            camera = page.locator('[data-builder-canvas]').get_attribute('viewBox')
            grid_visible = page.locator('[data-builder-grid]').is_visible()
            modes.select_option('paint')
            mode_project = review.save()
            assert mode_project['document'] == {**project['document'], 'editingMode': 'paint'}
            assert page.locator('[data-builder-canvas]').get_attribute('viewBox') == camera
            assert page.locator('[data-builder-grid]').is_visible() == grid_visible
            page.locator('[data-builder-undo]').click()
            assert review.save()['document'] == project['document']
            page.locator('[data-builder-redo]').click(); project = review.save()
            expect(modes).to_have_value('paint')
            records.append({'case': 'mode-switch-is-one-undo-preserving-source-geometry-native-objects-layers-and-camera'})

            terrain(red)
            resize_brush(40, 4, filename='terrain-Shift-resize-preview.png')
            resize_brush(-20, 3.5)
            resize_brush(80, 5.5, cancel=True)
            records.append({'case': 'Shift-drag-Paint-resizes-right-left-with-live-circular-preview-no-source-change-and-Escape-restores-size'})

            terrain(red, 3, 0, 60)
            before = project['document']
            stroke([(3.25, 4.25), (4.75, 4.25), (6.75, 5.5)])
            project = review.save()
            soft = new_brush(before, project['document'])
            first = soft['brush']['points'][0]
            assert abs(soft['x'] + first[0] * soft['width'] - 3.25) <= .002
            assert abs(soft['y'] + first[1] * soft['height'] - 4.25) <= .002
            assert len(soft['brush']['points']) > 3
            assert next(item for item in project['document']['floors'] if item['id'] == base_floor['id']) == base_floor
            with raster('terrain-soft-freehand-editor.png') as image:
                probes = check_probes(image, project['document'], assets,
                                      [(3.75, 4.75), (5.75, 5.25), (6.75, 5.75), (6.75, 6.7)], 'soft freehand')
            records.append({'case': 'freehand-stroke-is-fractional-continuous-soft-and-textured-without-grid-cells', 'probes': probes})

            terrain(red, 4, 0, 25)
            before = project['document']; stroke([(4.25, 9.25)])
            short_project = review.save(); short = new_brush(before, short_project['document'])
            stroke([(9.25, 9.25)], hold=550)
            held_project = review.save(); held = new_brush(short_project['document'], held_project['document'])
            short_alpha = brush_alpha(short, 4.25, 9.25)
            held_alpha = brush_alpha(held, 9.25, 9.25)
            assert held_alpha > short_alpha + .3, {'short': short_alpha, 'held': held_alpha}
            page.locator('[data-builder-undo]').click()
            assert review.save()['document'] == short_project['document']
            page.locator('[data-builder-redo]').click(); project = review.save()
            with raster('terrain-stationary-build-up-editor.png') as image:
                probes = check_probes(image, project['document'], assets, [(4.25, 9.25), (9.25, 9.25), (10.75, 9.25)], 'stationary accumulation')
            records.append({'case': 'holding-still-builds-intensity-within-one-stroke-and-one-undo',
                            'shortAlpha': short_alpha, 'heldAlpha': held_alpha, 'probes': probes})

            terrain(red, 3, 0, 100)
            before = project['document']; stroke([(3.25, 12.25)])
            soft_project = review.save(); edge_soft = new_brush(before, soft_project['document'])
            terrain(red, 3, 100, 100)
            stroke([(8.25, 12.25)])
            project = review.save(); edge_hard = new_brush(soft_project['document'], project['document'])
            soft_alpha = brush_alpha(edge_soft, 4.45, 12.25)
            hard_alpha = brush_alpha(edge_hard, 9.45, 12.25)
            assert hard_alpha > soft_alpha + .7
            with raster('terrain-hardness-editor.png') as image:
                probes = check_probes(image, project['document'], assets,
                                      [(4.45, 12.25), (9.45, 12.25), (3.25, 12.25), (8.25, 12.25)], 'hardness edge falloff')
            records.append({'case': 'hardness-controls-the-radial-edge-while-asymmetric-texture-retains-world-phase', 'probes': probes})

            terrain(blue, 3, 50, 50)
            before = project['document']; stroke([(9.25, 9.25)])
            mixed = review.save(); new_brush(before, mixed['document'])
            with raster('terrain-two-material-mix-editor.png') as image:
                probes = check_probes(image, mixed['document'], assets, [(9.25, 9.25), (9.75, 9.75), (10.5, 9.25)], 'different materials mix')
            terrain(blue, 3, 0, 100, 'erase')
            stroke([(9.25, 9.25), (15.25, 10.25)])
            erased = review.save(); new_brush(mixed['document'], erased['document'], 'erase')
            assert next(item for item in erased['document']['floors'] if item['id'] == other_floor['id']) == other_floor
            with raster('terrain-soft-erase-editor.png') as image:
                probes += check_probes(image, erased['document'], assets,
                                       [(9.25, 9.25), (10.25, 9.75), (11.5, 10.75), (15.25, 10.25), (17.75, 12.75)], 'layer-local soft erase')
            terrain(blue, 1.5, 100, 100)
            stroke([(10.25, 10.25)])
            project = review.save()
            with raster('terrain-after-erase-new-paint-editor.png') as image:
                probes += check_probes(image, project['document'], assets, [(10.25, 10.25)], 'later stroke survives earlier erase')
            records.append({'case': 'different-patterns-mix-and-soft-eraser-affects-only-earlier-floors-on-active-layer', 'probes': probes})

            terrain(red, 3, 50, 35)
            stroke([(2.25, 7.25), (3.25, 7.25)], hold=150, cancel=True)
            page.wait_for_timeout(100)
            unchanged(project)
            builder_sidebar(page, 'layers')
            lock = page.locator(f'[data-builder-layer-locked="{active}"]')
            lock.check(); locked = review.save()
            builder_workspace(page); stroke([(2.25, 7.25)])
            unchanged(locked)
            builder_sidebar(page, 'layers'); lock.uncheck(); project = review.save()
            builder_workspace(page)
            page.locator('[data-builder-dismiss]').click() if page.locator('[data-builder-notice]').is_visible() else None
            records.append({'case': 'Escape-discards-held-stroke-and-locked-layer-rejects-paint-without-source-or-revision-change'})

            terrain_rows = deepcopy([row for row in project['document']['floors'] if row.get('brush')])
            modes.select_option('tiles')
            builder_tool(page, 'floor')
            snap = page.locator('[data-builder-toggle-snap]')
            expect(snap).to_be_enabled()
            if snap.get_attribute('aria-pressed') != 'true':
                snap.click()
            control('[data-builder-brush-material]', green)
            control('[data-builder-paint-operation]', 'paint')
            control('[data-builder-paint-mode]', 'brush')
            control('[data-builder-brush-shape]', 'square')
            page.locator('[data-builder-quick-tool=paint]').click()
            size = page.locator('[data-builder-quick-brush-size]'); size.fill('1'); size.press('Enter')
            tiles_project = review.save()
            project = tiles_project
            resize_brush(60, 3, filename='tiles-Shift-resize-preview.png')
            resize_brush(-80, 1)
            resize_brush(80, 3, cancel=True)
            stroke([(1.25, 1.25)])
            unchanged(tiles_project)
            stroke([(18.25, 1.25)], cancel=True)
            unchanged(tiles_project)
            assert [row for row in tiles_project['document']['floors'] if row.get('brush')] == terrain_rows
            builder_sidebar(page, 'tools'); snap.click()
            builder_workspace(page)
            size.fill('1.5'); size.press('Enter')
            resize_brush(20, 2)
            resize_brush(-10, 1.75)
            resize_brush(20, 2.25, cancel=True)
            modes.select_option('paint'); project = review.save()
            records.append({'case': 'Tiles-restores-grid-no-op-and-Shift-resize-grid-or-free-footprints-without-rewriting-source'})

            page.reload(); wait_ready(page)
            assert review.save()['document'] == project['document']
            final_points = [(3.75, 4.75), (6.75, 6.7), (4.25, 9.25), (9.25, 9.25), (10.25, 10.25),
                            (4.45, 12.25), (9.45, 12.25), (15.25, 10.25), (17.75, 12.75), (1.75, 1.75)]
            with raster('terrain-final-editor.png') as expected:
                check_probes(expected, project['document'], assets, final_points, 'saved terrain')
                page.locator('[data-builder-preview]').click()
                expect(modes).to_be_disabled()
                builder_sidebar(page, 'tools')
                expect(page.locator('[data-builder-terrain-hardness]')).to_be_disabled()
                expect(page.locator('[data-builder-terrain-intensity]')).to_be_disabled()
                builder_workspace(page)
                page.screenshot(path=str(output / 'terrain-preview.png'))
                page.locator('[data-builder-preview]').click()
                expect(modes).to_be_enabled()
                pending = []
                page.route('**/map-builder/projects/*/generate', lambda route: pending.append(route), times=1)
                page.locator('[data-builder-generate]').click()
                expect(modes).to_be_disabled()
                expect(page.locator('[data-builder-terrain-hardness]')).to_be_disabled()
                expect(page.locator('[data-builder-terrain-intensity]')).to_be_disabled()
                deadline = time.monotonic() + 5
                while not pending and time.monotonic() < deadline:
                    page.wait_for_timeout(10)
                assert len(pending) == 1
                with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                    pending[0].continue_()
                assert generated.value.ok, generated.value.text()
                page.wait_for_url(f'{base}/game/{campaign}')
                final = review.project(project['id'])
                assert final['document'] == project['document']
                with generated_image(page, final) as image:
                    image.save(output / 'terrain-generated.png')
                    comparison = compare(expected, image, 'terrain-generated')
                    probes = check_probes(image, final['document'], assets, final_points, 'generated terrain')
            scene_id = final['sceneId']
            state = page.request.get(f'/api/maps/{scene_id}/state').json()
            native_door, = [item for item in state['walls'] if item['kind'] == 'door']
            assert native_door['door_state'] == 'closed'
            assert len(state['walls']) == 3 and len(state['lights']) == 1
            records.append({'case': 'save-reopen-preview-generate-preserve-parametric-source-textured-pixels-and-native-wall-door-light',
                            'comparison': comparison, 'probes': probes})

            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            native('walls', 'door', {'wall_id': native_door['id'], 'door_state': 'open'})
            manual = native('walls', 'create', {'x1': 20, 'y1': 20, 'x2': 60, 'y2': 60})['wall']
            page.goto(review.builder + '?project=' + project['id']); wait_ready(page)
            terrain(blue, 2, 100, 100); stroke([(16.25, 4.25)])
            updated_source = review.save()
            with raster('terrain-update-editor.png') as expected:
                builder_sidebar(page, 'review')
                with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                    page.locator('[data-builder-review-update]').click()
                assert updated.value.ok, updated.value.text()
                final = review.project(project['id'])
                assert final['sceneId'] == scene_id and final['document'] == updated_source['document']
                with generated_image(page, final) as image:
                    image.save(output / 'terrain-update-generated.png')
                    comparison = compare(expected, image, 'terrain-updated')
                    check_probes(image, final['document'], assets, [(16.25, 4.25), *final_points], 'updated terrain')
            state = page.request.get(f'/api/maps/{scene_id}/state').json()
            assert next(item for item in state['walls'] if item['id'] == native_door['id'])['door_state'] == 'open'
            assert next(item for item in state['walls'] if item['id'] == manual['id']) == manual
            records.append({'case': 'scene-update-replaces-terrain-raster-while-preserving-live-door-state-and-manual-native-wall', 'comparison': comparison})

            page.goto(review.builder + '?project=' + project['id']); wait_ready(page)
            project = final
            for locale, width in (('en', 1440), ('pt-BR', 1440), ('pt-BR', 390), ('es', 390)):
                page.set_viewport_size({'width': width, 'height': 900 if width > 500 else 844})
                change_locale(page, locale, campaign)
                page.reload(); wait_ready(page)
                expected_label = {'en': 'Painting', 'pt-BR': 'Pintura', 'es': 'Pintura'}[locale]
                expect(modes.locator('option[value=paint]')).to_have_text(expected_label)
                expect(modes).to_have_value('paint')
                page.locator('[data-builder-quick-tool=paint]').click()
                builder_sidebar(page, 'tools')
                expect(page.locator('[data-builder-terrain-hardness]')).to_be_visible()
                expect(page.locator('[data-builder-terrain-intensity]')).to_be_visible()
                page.locator('[data-builder-terrain-intensity]').scroll_into_view_if_needed()
                expect(page.locator('[data-builder-terrain-hardness]')).to_be_in_viewport()
                expect(page.locator('[data-builder-terrain-intensity]')).to_be_in_viewport()
                metrics = root.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, width, metrics)
                page.screenshot(path=str(output / f'terrain-tools-{locale}-{width}.png'))
                builder_workspace(page)
                page.screenshot(path=str(output / f'terrain-workspace-{locale}-{width}.png'))
                if locale == 'pt-BR' and width == 1440:
                    expected_size = float(page.locator('[data-builder-quick-brush-size]').input_value()) + 1
                    resize_brush(40, expected_size, cancel=True, filename='terrain-Shift-resize-preview-pt-BR-1440.png')
                unchanged(final)
                records.append({'case': 'localized-terrain-mode-and-live-controls-fit-desktop-and-mobile', 'locale': locale, 'width': width, 'metrics': metrics})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close(); browser.close()
    assert not errors and not dialogs, {'pageErrors': errors, 'nativeDialogs': dialogs}
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Three generated asymmetric floor patterns in an isolated campaign.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
