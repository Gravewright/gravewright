"""Verify Tiles behavior and compatibility with earlier painted maps.

Campaigns, textures, projects, native effects and generated scenes are disposable.
Legacy style metadata remains authored content and does not change the semantics
of a newly drawn brush after explicitly choosing Tiles.
"""
from __future__ import annotations

from base64 import b64decode
from copy import deepcopy
from io import BytesIO
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_free_paint import SVG_RASTER, artwork
from map_builder_reference import set_name, upload_asset, wait_ready


CELL = 64
BLUE, RED, GREEN = (32, 64, 128), (224, 64, 32), (48, 192, 96)
REMOVED_UI = ','.join('[data-builder-' + name + ']' for name in (
    'paint-dock', 'paint-dock-toggle', 'paint-tool', 'paint-swatch',
    'paint-color', 'paint-opacity', 'paint-source', 'paint-size', 'paint-size-slider', 'paint-opacity-slider'))


def blend(bottom, top, alpha):
    return tuple(round(a * (1 - alpha) + b * alpha) for a, b in zip(bottom, top))


def assert_pixels(image, probes, label):
    for x, y, expected in probes:
        actual = image.getpixel((round(x * CELL), round(y * CELL)))[:3]
        assert max(abs(a - b) for a, b in zip(actual, expected)) <= 4, {
            'case': label, 'point': [x, y], 'expected': expected, 'actual': actual}


def compare_rasters(expected, actual, document):
    """Keep interiors strict and bound the known coincident-cut AA edge band."""
    from PIL import ImageChops, ImageFilter

    assert expected.size == actual.size
    cuts = []
    for floor in document['floors']:
        for ring in floor.get('shape', {}).get('cuts', []):
            points = [((floor['x'] + u * floor['width']) * CELL, (floor['y'] + v * floor['height']) * CELL) for u, v in ring]
            cuts.extend(zip(points, points[1:] + points[:1]))

    def cut_distance(x, y):
        distances = []
        for a, b in cuts:
            dx, dy = b[0] - a[0], b[1] - a[1]
            square = dx * dx + dy * dy
            t = max(0, min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / square)) if square else 0
            distances.append(((x - a[0] - t * dx) ** 2 + (y - a[1] - t * dy) ** 2) ** .5)
        return min(distances, default=float('inf'))

    residuals = {}
    for before, after in [(expected, actual), (actual, expected)]:
        source, target = before.split(), after.split()
        try:
            for index, (channel, other) in enumerate(zip(source, target)):
                with channel.filter(ImageFilter.MinFilter(5)) as low:
                    with channel.filter(ImageFilter.MaxFilter(5)) as high:
                        with ImageChops.subtract(low, other) as below:
                            with ImageChops.subtract(other, high) as above:
                                with ImageChops.lighter(below, above) as delta:
                                    mismatch = delta.point(lambda value: 255 if value > 4 else 0)
                bad = []
                with mismatch:
                    box = mismatch.getbbox()
                    for y in range(box[1], box[3]) if box else []:
                        for x in range(box[0], box[2]):
                            if not mismatch.getpixel((x, y)):
                                continue
                            distance = cut_distance(x + .5, y + .5)
                            difference = max(abs(a - b) for a, b in zip(expected.getpixel((x, y)), actual.getpixel((x, y))))
                            if distance <= 2 and difference <= 64:
                                residuals[x, y] = {'distancePx': distance, 'maxRgbDelta': difference}
                            else:
                                bad.append({'point': [x, y], 'distancePx': distance, 'maxRgbDelta': difference})
                assert len(bad) <= 8, {'channel': index, 'mismatchedInteriorPixels': len(bad), 'samples': bad[:8]}
        finally:
            for channel in (*source, *target):
                channel.close()
    return {'cutBoundaryResidualPixels': len(residuals),
            'maxCutBoundaryDistancePx': max((row['distancePx'] for row in residuals.values()), default=0),
            'maxCutBoundaryRgbDelta': max((row['maxRgbDelta'] for row in residuals.values()), default=0)}


def check_browser(base, seed, output, executable):
    from PIL import Image
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

        def tiles_ui(mode='tiles'):
            expect(page.locator(REMOVED_UI)).to_have_count(0)
            expect(page.locator('[data-builder-editing-mode]')).to_have_value(mode)
            assert not page.locator('link[href*="paint-design.css"]').count()
            expect(page.locator('.map-builder__tool-rail,.map-builder__toolbars')).to_have_count(0)
            expect(page.locator('[data-builder-tool=floor]')).to_have_count(1)
            assert page.locator('[data-builder-tool=floor]').evaluate('el=>!!el.closest("[data-builder-sidebar-panel=tools]")')
            expect(page.locator('.map-builder__header [data-builder-quick-name]')).to_be_visible()
            for action in ('undo', 'redo', 'save'):
                expect(page.locator(f'.map-builder__header [data-builder-{action}]')).to_have_count(1)
            assert page.locator('[data-builder-assets-panel]').evaluate('el=>el.parentElement.matches("[data-map-builder]")')

        def control(selector, value):
            builder_sidebar(page, 'tools')
            field = page.locator(selector); field.scroll_into_view_if_needed()
            if field.evaluate('el=>el.tagName') == 'SELECT':
                field.select_option(str(value))
            else:
                field.fill(str(value)); field.dispatch_event('change')

        def snap(value):
            builder_sidebar(page, 'tools')
            field = page.locator('[data-builder-toggle-snap]')
            expect(field).to_be_enabled()
            if field.get_attribute('aria-pressed') != str(value).lower():
                field.click()
            expect(field).to_have_attribute('aria-pressed', str(value).lower())

        def floor(mode='brush', material=None, operation='paint', size=1, shape='square'):
            builder_tool(page, 'floor')
            control('[data-builder-paint-mode]', mode)
            control('[data-builder-paint-operation]', operation)
            if material:
                control('[data-builder-brush-material]', material)
            if mode == 'brush':
                control('[data-builder-brush-shape]', shape)
                control('[data-builder-brush=floorSize]', size)
            builder_workspace(page)

        def point(x, y):
            return page.locator('[data-builder-canvas]').evaluate("""(svg,point)=>{
              const p=new DOMPoint(...point).matrixTransform(svg.getScreenCTM());return [p.x,p.y];
            }""", [x, y])

        def click(x, y):
            builder_workspace(page)
            page.mouse.click(*point(x, y))

        def stroke(start, end):
            builder_workspace(page)
            page.mouse.move(*point(*start)); page.mouse.down()
            page.mouse.move(*point(*end), steps=8); page.mouse.up()

        def saved():
            return review.save()['document']

        def raster(filename=None):
            encoded = page.evaluate(SVG_RASTER, {'width': 1024, 'height': 768, 'columns': 16, 'rows': 12, 'ids': None})
            image = Image.open(BytesIO(b64decode(encoded.split(',', 1)[1]))).convert('RGB')
            if filename:
                image.save(output / filename)
            return image

        def generated_raster(project, expected, probes, label):
            with page.expect_response(lambda response: response.url.endswith('/generate')) as response:
                page.locator('[data-builder-generate]').click()
            assert response.value.ok, response.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            stored = review.project(project['id'])
            manifest = page.request.get(f'/api/maps/{stored["sceneId"]}/manifest').json()
            level = next(item for item in manifest['levels'] if item['lod'] == 0)
            with Image.new('RGB', (manifest['width'], manifest['height'])) as image:
                for y in range(level['rows']):
                    for x in range(level['columns']):
                        url = manifest['tileUrlTemplate'].replace('{lod}', '0').replace('{x}', str(x)).replace('{y}', str(y))
                        tile = page.request.get(url); assert tile.ok
                        with Image.open(BytesIO(tile.body())) as source:
                            image.paste(source, (x * manifest['tileSize'], y * manifest['tileSize']))
                image.save(output / (label + '-generated.png'))
                comparison = compare_rasters(expected, image, stored['document'])
                assert_pixels(image, probes, label)
            return stored, comparison

        try:
            page.goto(review.builder); wait_ready(page); tiles_ui()
            set_name(page, 'Synthetic Tiles-only preparation')
            blue = upload_asset(page, 'floor', 'Synthetic blue tile.png', artwork(BLUE))['id']
            red = upload_asset(page, 'floor', 'Synthetic red tile.png', artwork(RED))['id']
            green = upload_asset(page, 'floor', 'Synthetic green tile.png', artwork(GREEN))['id']
            source = review.save()
            plain = deepcopy(source['document'])
            plain.update(name='Synthetic unchanged original Tiles document', columns=16, rows=12, cellSize=CELL, background='#112233')
            plain.pop('editingMode', None)
            base_layer = plain['layers'][0]['id']
            backing = {'id': str(uuid4()), 'layerId': base_layer, 'assetId': blue,
                       'x': 0, 'y': 0, 'width': 16, 'height': 12, 'rotation': 0}
            plain['floors'] = [backing]
            for value in (None, 'tiles'):
                document = deepcopy(plain)
                if value:
                    document['editingMode'] = value
                original = review.store(str(uuid4()), 0, seed['folder'], document)
                page.goto(review.builder + '?project=' + original['id']); wait_ready(page); tiles_ui()
                page.locator('[data-builder-save]').click()
                expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved')
                assert saved() == original['document']
            records.append({'case': 'new-and-original-Tiles-documents-have-one-editor-and-save-without-added-mode-or-style-fields'})

            legacy = deepcopy(plain)
            legacy.update(name='Synthetic legacy painted map preserved in the Tiles editor', editingMode='paint')
            authored_layer = str(uuid4())
            legacy['layers'].append({'id': authored_layer, 'name': 'Legacy color and texture content — long authored layer name', 'visible': True, 'locked': False})
            legacy['floors'].extend([
                {'id': str(uuid4()), 'layerId': authored_layer, 'assetId': None, 'x': 2, 'y': 2, 'width': 4, 'height': 3, 'rotation': 0, 'paint': {'color': '#e04020', 'opacity': .5}},
                {'id': str(uuid4()), 'layerId': authored_layer, 'assetId': None, 'x': 4, 'y': 3, 'width': 4, 'height': 3, 'rotation': 0, 'paint': {'color': '#e04020', 'opacity': .5}},
                {'id': str(uuid4()), 'layerId': authored_layer, 'assetId': green, 'x': 9, 'y': 2, 'width': 3, 'height': 3, 'rotation': 0, 'paint': {'color': None, 'opacity': .25}},
                {'id': str(uuid4()), 'layerId': authored_layer, 'assetId': None, 'x': 9, 'y': 7, 'width': 3, 'height': 3, 'rotation': 0,
                 'paint': {'color': '#30c060', 'opacity': .4}, 'shape': {'contours': [[[0, 0], [1, 0], [0, 1]]], 'cuts': []}},
            ])
            legacy['lights'] = [{'id': str(uuid4()), 'layerId': base_layer, 'x': 14, 'y': 5,
                                 'brightRadius': 1, 'dimRadius': 2, 'color': '#ffc977', 'intensity': .3, 'enabled': True}]
            legacy['particles'] = [{'id': str(uuid4()), 'layerId': base_layer, 'x': 14, 'y': 10, 'kind': 'smoke',
                                    'scale': 1, 'density': .2, 'color': '#9aa3ad', 'enabled': True,
                                    'rotation': 0, 'light_response': 0, 'light_emission': 0}]
            project = review.store(str(uuid4()), 0, seed['folder'], legacy)
            legacy = project['document']
            page.goto(review.builder + '?project=' + project['id']); wait_ready(page); tiles_ui('paint')
            page.locator('[data-builder-save]').click()
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved')
            assert saved() == legacy
            probes = [(2.5, 2.5, blend(BLUE, RED, .5)), (4.5, 3.5, blend(blend(BLUE, RED, .5), RED, .5)),
                      (9.5, 2.5, blend(BLUE, GREEN, .25)), (9.5, 7.5, blend(BLUE, GREEN, .4)), (11.5, 9.5, BLUE)]
            with raster('legacy-original-editor.png') as expected:
                assert_pixels(expected, probes, 'legacy source styles')
                stored, comparison = generated_raster(project, expected, probes, 'legacy-original')
            assert stored['document'] == legacy
            records.append({'case': 'legacy-paint-mode-preserves-color-alpha-free-geometry-and-original-native-generation', 'comparison': comparison})

            page.goto(review.builder + '?project=' + project['id']); wait_ready(page)
            page.locator('[data-builder-editing-mode]').select_option('tiles'); tiles_ui()
            control('[data-builder-active-layer-select]', authored_layer)
            snap(True); floor(material=green); click(4.7, 3.7)
            current = saved()
            tiles = [row for row in current['floors'] if row['assetId'] == green and row['x'] == 4 and row['y'] == 3 and row['width'] == row['height'] == 1]
            assert len(tiles) == 1 and 'paint' not in tiles[0] and 'shape' not in tiles[0], tiles
            assert current['editingMode'] == 'tiles', 'Only the explicit mode switch changes the authored editing mode'
            with raster('legacy-with-new-opaque-Tile.png') as image:
                assert_pixels(image, [(4.5, 3.5, GREEN), (2.5, 2.5, blend(BLUE, RED, .5))], 'new Tiles brush over old alpha')
            records.append({'case': 'legacy-mode-metadata-never-enables-free-branch-or-alpha-for-a-new-snapped-Tiles-stroke'})

            floor('rectangle', green); stroke((12, 8), (14, 10)); current = saved()
            floor('fill', red); click(12.5, 8.5); current = saved()
            with raster() as image:
                assert_pixels(image, [(12.5, 8.5, RED), (13.5, 9.5, RED)], 'Tiles bucket fill')
            floor('rectangle', red, operation='erase'); stroke((13, 9), (14, 10)); current = saved()
            with raster() as image:
                assert_pixels(image, [(12.5, 8.5, RED), (13.5, 9.5, BLUE)], 'Tiles area erasure')
            page.locator('[data-builder-undo]').click()
            with raster() as image:
                assert_pixels(image, [(13.5, 9.5, RED)], 'one eraser undo')
            page.locator('[data-builder-redo]').click(); current = saved()
            records.append({'case': 'Tiles-rectangle-bucket-fill-and-active-layer-area-eraser-have-real-pixels-and-history'})

            snap(False); floor(material=green, size=2.5, shape='circle')
            stroke((3.35, 9.25), (6.25, 9.25)); after = saved()
            added = [row for row in after['floors'] if row['id'] not in {item['id'] for item in current['floors']}]
            assert len(added) == 1 and added[0].get('shape', {}).get('contours') and 'paint' not in added[0], added
            continuous = added[0]; current = after
            assert abs(continuous['x'] - 2.1) < .025, continuous
            with raster() as image:
                assert_pixels(image, [(2.25, 9.25, GREEN), (2, 9.25, BLUE), (2.2, 8.1, BLUE)], 'continuous Tiles brush')
            floor('circle', green, operation='erase'); stroke((4.75, 9.25), (5.5, 9.25)); current = saved()
            assert next(row for row in current['floors'] if row['id'] == continuous['id'])['shape']['cuts']
            with raster() as image:
                assert_pixels(image, [(4.75, 9.25, BLUE), (3.25, 9.25, GREEN)], 'free Tiles circular eraser')
            floor(material=green, size=2.5, shape='circle')
            builder_tool(page, 'erase'); click(6.25, 9.25)
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-tool', 'erase')
            assert not any(row['id'] == continuous['id'] for row in saved()['floors'])
            page.locator('[data-builder-undo]').click(); current = saved()
            assert any(row['id'] == continuous['id'] for row in current['floors'])
            records.append({'case': 'snap-off-remains-truly-continuous-and-E-keeps-the-Tiles-object-eraser-semantics'})

            builder_sidebar(page, 'layers')
            page.locator(f'[data-builder-layer-locked="{authored_layer}"]').check()
            guarded = saved(); floor(material=red, size=1); click(8.5, 10.5)
            assert saved() == guarded
            if page.locator('[data-builder-dismiss]').is_visible():
                page.locator('[data-builder-dismiss]').click()
            builder_sidebar(page, 'layers'); page.locator(f'[data-builder-layer-locked="{authored_layer}"]').uncheck()
            current = saved(); before_solo = deepcopy(current)
            page.locator(f'[data-builder-layer-solo="{authored_layer}"]').click()
            expect(page.locator('[data-builder-native-preview] canvas')).to_have_count(0)
            assert saved() == before_solo
            page.locator(f'[data-builder-layer-solo="{authored_layer}"]').click()
            expect(page.locator('[data-builder-native-preview] canvas')).to_have_count(1)
            assert saved() == before_solo
            assert current['lights'] == legacy['lights'] and current['particles'] == legacy['particles']
            assert next(row for row in current['floors'] if row['id'] == backing['id']) == backing
            if page.locator('[data-builder-dismiss]').is_visible():
                page.locator('[data-builder-dismiss]').click()
            records.append({'case': 'Tiles-layer-lock-and-solo-preserve-native-effects-and-other-layer-artwork'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 1024, 390, 320):
                    page.set_viewport_size({'width': width, 'height': 900 if width >= 1000 else 844})
                    page.reload(); wait_ready(page); tiles_ui(); floor(material=green)
                    metrics = page.locator('[data-map-builder]').evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], (locale, width, metrics)
                    assert metrics['scrollWidth'] <= metrics['viewport'] + 1, (locale, width, metrics)
                    bounds = page.evaluate("""()=>{
                      const box=s=>{const r=document.querySelector(s).getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,height:r.height};};
                      return {header:box('.map-builder__header'),canvas:box('[data-builder-viewport]'),library:box('[data-builder-assets-panel]')};
                    }""")
                    assert abs(bounds['canvas']['left']) <= 1, (locale, width, bounds)
                    assert abs(bounds['canvas']['right'] - width) <= 1, (locale, width, bounds)
                    assert abs(bounds['canvas']['top'] - bounds['header']['bottom']) <= 1, (locale, width, bounds)
                    assert abs(bounds['canvas']['bottom'] - bounds['library']['top']) <= 1, (locale, width, bounds)
                    assert bounds['canvas']['height'] >= 180, (locale, width, bounds)
                    expect(page.locator('[data-builder-quick-name]')).to_have_value(current['name'])
                    page.screenshot(path=str(output / f'tiles-only-{locale}-{width}.png'))
                    records.append({'case': 'Tiles-editor-layout-preserves-original-controls-with-compact-mode-selector', 'locale': locale, 'width': width, 'metrics': metrics})

            page.set_viewport_size({'width': 1440, 'height': 900})
            page.reload(); wait_ready(page); tiles_ui()
            assert saved() == current
            with raster('tiles-final-editor.png') as expected:
                page.locator('[data-builder-preview]').click()
                page.screenshot(path=str(output / 'tiles-only-preview.png'))
                final_probes = [(2.5, 2.5, blend(BLUE, RED, .5)), (4.5, 3.5, GREEN),
                                (9.5, 2.5, blend(BLUE, GREEN, .25)), (4.75, 9.25, BLUE), (3.25, 9.25, GREEN), (13.5, 9.5, BLUE)]
                final, comparison = generated_raster(project, expected, final_probes, 'tiles-final')
            assert final['document'] == current
            records.append({'case': 'legacy-content-and-new-Tiles-edits-save-reload-preview-and-generate-together-with-pixel-parity', 'comparison': comparison})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close(); browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'artwork': 'Only generated solid-color textures and isolated synthetic native effects.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
