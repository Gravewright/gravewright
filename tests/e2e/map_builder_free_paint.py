"""Verify unsnapped continuous painting against visible and generated pixels.

Every asset, campaign, database and browser output belongs to the disposable
builder fixture. Shape coverage is checked independently of stored box offsets.
"""
from __future__ import annotations

from base64 import b64decode
from copy import deepcopy
from io import BytesIO
import math
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import builder_sidebar, builder_tool, builder_workspace
from map_builder_asset_removal import BuilderReview
from map_builder_reference import set_name, upload_asset, wait_ready


CELL = 64
BACKGROUND = (17, 34, 51)
RED, GREEN, BLUE = (218, 68, 34), (34, 153, 51), (35, 90, 202)
COLORS = (BACKGROUND, RED, GREEN, BLUE)


def artwork(color):
    from PIL import Image

    stream = BytesIO()
    with Image.new('RGB', (32, 32), color) as image:
        image.save(stream, 'PNG')
    return stream.getvalue()


def assert_pixels(image, probes, label):
    samples = []
    for x, y, expected in probes:
        actual = image.getpixel((round(x * CELL), round(y * CELL)))[:3]
        assert max(abs(actual[index] - expected[index]) for index in range(3)) <= 16, {
            'case': label, 'point': [x, y], 'expected': expected, 'actual': actual}
        samples.append({'point': [x, y], 'rgb': actual})
    return samples


def compare_coverage(expected, actual, label):
    """Require both renderers' solid interiors, allowing only a two-pixel edge."""
    from PIL import Image, ImageChops, ImageFilter

    assert expected.size == actual.size
    records = []
    for color in COLORS[1:]:
        masks = []
        for image in (expected, actual):
            channels = image.convert('RGB').split()
            thresholds = [channel.point([255 if abs(value - color[index]) <= 16 else 0 for value in range(256)])
                          for index, channel in enumerate(channels)]
            with ImageChops.darker(thresholds[0], thresholds[1]) as combined:
                masks.append(ImageChops.darker(combined, thresholds[2]))
            for channel in (*channels, *thresholds):
                channel.close()
        try:
            for direction, interior, other in [('expected-to-actual', masks[0], masks[1]),
                                                ('actual-to-expected', masks[1], masks[0])]:
                with interior.filter(ImageFilter.MinFilter(5)) as solid:
                    with ImageChops.subtract(solid, other) as mismatch:
                        count = mismatch.histogram()[255]
                assert count <= 4, {'case': label, 'color': color, 'direction': direction, 'mismatchedInteriorPixels': count}
            records.append({'color': color, 'paintedPixels': masks[0].histogram()[255]})
        finally:
            for mask in masks:
                mask.close()
    assert sum(row['paintedPixels'] for row in records) > 500, (label, records)
    return records


SVG_RASTER = """async args => {
  const original = document.querySelector('[data-builder-canvas]'), svg = original.cloneNode(true);
  svg.setAttribute('width', args.width); svg.setAttribute('height', args.height);
  svg.setAttribute('viewBox', `0 0 ${args.columns} ${args.rows}`);
  svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  svg.setAttribute('preserveAspectRatio', 'none');
  for (const node of svg.querySelectorAll('[data-builder-grid],[data-builder-outline],[data-builder-walls],[data-builder-doors]')) node.remove();
  if (args.ids) for (const node of [...svg.querySelector('[data-builder-floors]').children])
    if (!args.ids.includes(node.dataset.objectId)) node.remove();
  const embedded = new Map();
  for (const node of svg.querySelectorAll('image')) {
    const href = node.getAttribute('href'); if (!href || href.startsWith('data:')) continue;
    if (!embedded.has(href)) {
      const response = await fetch(new URL(href, location.href));
      if (!response.ok) throw Error('Synthetic texture unavailable');
      const blob = await response.blob();
      const data = await new Promise((resolve,reject) => {
        const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(blob);
      });
      embedded.set(href, data);
    }
    node.setAttribute('href', embedded.get(href));
  }
  const blob = new Blob([new XMLSerializer().serializeToString(svg)], {type:'image/svg+xml;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  try {
    const image = new Image();
    await new Promise((resolve,reject) => {image.onload = resolve; image.onerror = reject; image.src = url;});
    const canvas = document.createElement('canvas'); canvas.width = args.width; canvas.height = args.height;
    canvas.getContext('2d').drawImage(image, 0, 0);
    return canvas.toDataURL('image/png');
  } finally { URL.revokeObjectURL(url); }
}"""


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

        def control(selector, value):
            node = page.locator(selector)
            node.scroll_into_view_if_needed()
            if node.evaluate('node=>node.tagName') == 'SELECT':
                node.select_option(str(value))
            else:
                node.fill(str(value)); node.dispatch_event('change')

        def screen(point):
            return page.locator('[data-builder-canvas]').evaluate("""(svg, point)=>{
              const p=new DOMPoint(...point).matrixTransform(svg.getScreenCTM()); return [p.x,p.y];
            }""", point)

        def click(x, y):
            page.mouse.click(*screen([x, y]))

        def stroke(points):
            page.mouse.move(*screen(points[0])); page.mouse.down()
            for point in points[1:]:
                page.mouse.move(*screen(point), steps=4)
            page.mouse.up()

        def snap(enabled):
            button = page.locator('[data-builder-toggle-snap]')
            if button.get_attribute('aria-pressed') != str(enabled).lower():
                button.click()
            expect(button).to_have_attribute('aria-pressed', str(enabled).lower())

        def paint(mode, material, shape='circle', size=None, operation='paint'):
            builder_tool(page, 'floor')
            control('[data-builder-paint-mode]', mode)
            control('[data-builder-paint-operation]', operation)
            control('[data-builder-brush-material]', material)
            if mode == 'brush':
                control('[data-builder-brush-shape]', shape)
                if size is not None:
                    control('[data-builder-brush=floorSize]', size)
            builder_workspace(page)

        def raster(filename=None, ids=None):
            encoded = page.evaluate(SVG_RASTER, {'width': 32 * CELL, 'height': 24 * CELL, 'columns': 32, 'rows': 24, 'ids': ids})
            result = Image.open(BytesIO(b64decode(encoded.split(',', 1)[1]))).convert('RGB')
            if filename:
                result.save(output / filename)
            return result

        def row(document, identifier):
            return next(item for item in document['floors'] if item['id'] == identifier)

        def new_floor(before, after):
            ids = {item['id'] for item in before['floors']}
            result = [item for item in after['floors'] if item['id'] not in ids]
            assert len(result) == 1, {'expected': 'one continuous shape per gesture', 'newFloors': result}
            assert result[0].get('shape', {}).get('contours'), result[0]
            return result[0]

        def hover(x, y, size, shape):
            page.mouse.move(*screen([x, y]))
            cursor = page.locator('[data-builder-brush-cursor]')
            expect(cursor).to_have_count(1)
            box = cursor.evaluate('node=>{const b=node.getBBox();return {x:b.x,y:b.y,width:b.width,height:b.height,d:node.getAttribute("d")};}')
            for key, expected in [('x', x - size / 2), ('y', y - size / 2), ('width', size), ('height', size)]:
                assert abs(box[key] - expected) < .025, (shape, key, box, expected)
            if box['d']:
                assert box['d'].count('M') == 1, 'the free brush guide must not draw a mosaic of grid cells'

        try:
            page.goto(review.builder); wait_ready(page)
            set_name(page, 'Synthetic continuous paint preparation')
            red = upload_asset(page, 'floor', 'Synthetic continuous red.png', artwork(RED))['id']
            green = upload_asset(page, 'floor', 'Synthetic continuous green.png', artwork(GREEN))['id']
            blue = upload_asset(page, 'floor', 'Synthetic continuous blue.png', artwork(BLUE))['id']
            baseline = review.save()
            legacy = deepcopy(baseline['document'])
            legacy.update(name='Synthetic unchanged legacy rectangle', columns=32, rows=24, cellSize=CELL, background='#112233')
            legacy.pop('particles', None); legacy.pop('shaders', None)
            base_layer = legacy['layers'][0]['id']
            legacy['floors'] = [{'id': str(uuid4()), 'layerId': base_layer, 'assetId': red,
                                 'x': 28, 'y': 20, 'width': 1, 'height': 2, 'rotation': 0}]
            saved_legacy = review.store(str(uuid4()), 0, seed['folder'], legacy)
            page.goto(review.builder + '?project=' + saved_legacy['id']); wait_ready(page)
            page.locator('[data-builder-save]').click()
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved')
            assert review.project(saved_legacy['id'])['document'] == saved_legacy['document']
            records.append({'case': 'legacy-schema-three-rectangle-opens-and-saves-without-new-shape-fields'})

            document = deepcopy(saved_legacy['document'])
            document['name'] = 'Synthetic free continuous painting'
            upper_layer = str(uuid4())
            document['layers'].append({'id': upper_layer, 'name': 'Untouched upper floor', 'visible': True, 'locked': False})
            upper = {'id': str(uuid4()), 'layerId': upper_layer, 'assetId': blue,
                     'x': 14.2, 'y': 14.1, 'width': .9, 'height': .8, 'rotation': 0}
            document['floors'] = [upper]
            project = review.store(str(uuid4()), 0, seed['folder'], document)
            page.goto(review.builder + '?project=' + project['id']); wait_ready(page)
            control('[data-builder-active-layer-select]', base_layer)
            snap(False)

            paint('brush', red, size=2.5)
            hover(5.35, 5.45, 2.5, 'circle')
            page.screenshot(path=str(output / 'free-round-hover.png'))
            curve = [(5.35, 5.45), (5.9, 5.95), (6.65, 6.75), (7.7, 7.5), (8.8, 8.0), (10.15, 7.8)]
            stroke(curve)
            current = review.save()['document']; rounded = new_floor(document, current)
            round_probes = [(4.25, 5.45, RED), (4.0, 5.45, BACKGROUND), (4.2, 4.3, BACKGROUND),
                            (11.25, 7.8, RED), (11.55, 7.8, BACKGROUND), (11.25, 8.9, BACKGROUND)]
            with raster('free-round-stroke.png') as image:
                samples = assert_pixels(image, round_probes + [(x, y, RED) for x, y in curve], 'continuous round stroke')
            records.append({'case': 'fractional-round-brush-sweeps-a-smooth-curve-with-real-round-endcaps', 'samples': samples})

            paint('brush', green, shape='square', size=2.35)
            hover(14.25, 4.35, 2.35, 'square')
            stroke([(14.25, 4.35), (16.1, 5.3), (18.6, 6.1)])
            previous, current = current, review.save()['document']
            squared = new_floor(previous, current)
            square_probes = [(13.2, 3.3, GREEN), (12.9, 3.3, BACKGROUND), (19.65, 6.9, GREEN), (19.95, 6.9, BACKGROUND)]
            with raster('free-square-stroke.png') as image:
                assert_pixels(image, round_probes + square_probes, 'fractional swept square')
            records.append({'case': 'fractional-square-stamp-retains-its-corners-and-continuous-swept-edge'})

            paint('circle', red)
            stroke([(25.2, 5.4), (26.65, 6.6)])
            previous, current = current, review.save()['document']; circle = new_floor(previous, current)
            radius = math.hypot(1.45, 1.2)
            circle_probes = [(25.2, 5.4, RED), (25.2 + radius - .15, 5.4, RED),
                             (25.2 + radius + .15, 5.4, BACKGROUND), (25.2 + radius * .88, 5.4 + radius * .88, BACKGROUND)]
            paint('rectangle', red); stroke([(3.2, 13.35), (7.65, 16.1)])
            previous, current = current, review.save()['document']; rectangle = new_floor(previous, current)
            rectangle_probes = [(3.3, 13.45, RED), (3.05, 13.45, BACKGROUND), (7.5, 15.9, RED), (7.8, 15.9, BACKGROUND)]
            paint('polygon', green)
            for x, y in [(12.2, 13.1), (18.7, 13.45), (16.8, 17.6), (11.85, 16.3)]:
                click(x, y)
            page.locator('[data-builder-polygon-finish]').click()
            previous, current = current, review.save()['document']; polygon = new_floor(previous, current)
            with raster('free-fractional-forms.png') as image:
                assert_pixels(image, circle_probes + rectangle_probes + [(12.3, 13.3, GREEN), (12.1, 13.0, BACKGROUND),
                    (17.6, 14.5, GREEN), (18.9, 14.5, BACKGROUND)], 'true fractional forms')
            records.append({'case': 'circle-outline-fractional-rectangle-and-clicked-polygon-preserve-real-coverage'})

            paint('circle', green, operation='erase'); stroke([(15.3, 14.6), (16.95, 14.6)])
            current = review.save()['document']
            assert row(current, upper['id']) == upper
            assert row(current, polygon['id']).get('shape', {}).get('cuts'), 'free erase must persist a hole, not an empty bounding rectangle'
            hole_probes = [(15.3, 14.6, BACKGROUND), (15.8, 14.6, BACKGROUND), (14.5, 14.4, BLUE), (17.6, 14.5, GREEN)]
            with raster('free-area-erase.png') as image:
                assert_pixels(image, hole_probes, 'active-layer free erase')
            page.locator('[data-builder-undo]').click(); restored = review.save()['document']
            assert row(restored, polygon['id']) == polygon
            page.locator('[data-builder-redo]').click(); current = review.save()['document']
            records.append({'case': 'free-area-erasure-cuts-a-real-hole-preserves-other-layer-and-one-undo-redo'})

            before_fill = deepcopy(row(current, polygon['id']))
            paint('fill', red); click(17.6, 14.5)
            current = review.save()['document']
            assert row(current, polygon['id']) == {**before_fill, 'assetId': red, 'rotation': 0}
            with raster('free-fill-shape.png') as image:
                assert_pixels(image, [(x, y, RED if color == GREEN else color) for x, y, color in hole_probes], 'fill exact free shape')
            records.append({'case': 'unsnapped-fill-recolors-the-clicked-shape-with-hole-and-identity-preserved'})

            builder_tool(page, 'select'); click(16.7, 16.6); builder_sidebar(page, 'selection')
            before_move = deepcopy(row(current, polygon['id']))
            with raster(ids=[polygon['id']]) as before_image:
                control('[data-builder-properties] [data-builder-property=x]', before_move['x'] + 2.35)
                control('[data-builder-properties] [data-builder-property=y]', before_move['y'] + .4)
                current = review.save()['document']; moved = row(current, polygon['id'])
                assert moved['shape'] == before_move['shape']
                with before_image.transform(before_image.size, Image.Transform.AFFINE, (1, 0, -2.35 * CELL, 0, 1, -.4 * CELL),
                                            resample=Image.Resampling.NEAREST, fillcolor=BACKGROUND) as expected:
                    with raster(ids=[polygon['id']]) as actual:
                        compare_coverage(expected, actual, 'moving clipped free geometry')
            with raster(ids=[polygon['id']]) as before_image:
                center = ((moved['x'] + moved['width'] / 2) * CELL, (moved['y'] + moved['height'] / 2) * CELL)
                page.locator('[data-builder-rotate]').click(); current = review.save()['document']
                with before_image.rotate(-90, center=center, resample=Image.Resampling.NEAREST, fillcolor=BACKGROUND) as expected:
                    with raster('free-rotated-mask.png', ids=[polygon['id']]) as actual:
                        compare_coverage(expected, actual, 'rotating contours and cuts')
            rotated = deepcopy(row(current, polygon['id']))
            with raster(ids=[polygon['id']]) as before_image:
                page.locator('[data-builder-duplicate]').click(); previous, current = current, review.save()['document']
                copied = new_floor(previous, current)
                assert copied['shape'] == rotated['shape'] and copied['id'] != rotated['id']
                dx, dy = (copied['x'] - rotated['x']) * CELL, (copied['y'] - rotated['y']) * CELL
                with before_image.transform(before_image.size, Image.Transform.AFFINE, (1, 0, -dx, 0, 1, -dy),
                                            resample=Image.Resampling.NEAREST, fillcolor=BACKGROUND) as expected:
                    with raster(ids=[copied['id']]) as actual:
                        compare_coverage(expected, actual, 'duplicating clipped free geometry')
            records.append({'case': 'move-quarter-turn-and-duplicate-transform-actual-contours-and-holes'})

            builder_workspace(page); snap(True); paint('brush', blue, shape='square', size=1)
            previous = current; click(25.7, 20.6); current = review.save()['document']
            old_ids = {item['id'] for item in previous['floors']}
            grid = [item for item in current['floors'] if item['id'] not in old_ids]
            assert len(grid) == 1 and 'shape' not in grid[0]
            assert (grid[0]['x'], grid[0]['y'], grid[0]['width'], grid[0]['height']) == (25, 20, 1, 1)
            with raster('free-and-grid-paint.png') as image:
                assert_pixels(image, [(25.2, 20.2, BLUE), (24.8, 20.2, BACKGROUND), (26.2, 20.2, BACKGROUND)], 'snap on grid painting')
            records.append({'case': 'reenabling-snap-restores-original-one-cell-floor-format-and-pixel-coverage'})

            before_reload = raster('free-before-reload.png')
            try:
                page.reload(); wait_ready(page)
                assert review.save()['document'] == current
                with raster('free-after-reload.png') as image:
                    compare_coverage(before_reload, image, 'reloaded free geometry')
                page.locator('[data-builder-preview]').click()
                page.screenshot(path=str(output / 'free-preview.png'))
                with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                    page.locator('[data-builder-generate]').click()
                assert generated.value.ok, generated.value.text()
                page.wait_for_url(f'{base}/game/{campaign}')
                final = review.project(project['id']); assert final['document'] == current
                response = page.request.get(f'/api/maps/{final["sceneId"]}/manifest'); assert response.ok
                manifest = response.json(); level = next(item for item in manifest['levels'] if item['lod'] == 0)
                with Image.new('RGB', (manifest['width'], manifest['height'])) as generated_image:
                    for y in range(level['rows']):
                        for x in range(level['columns']):
                            url = manifest['tileUrlTemplate'].replace('{lod}', '0').replace('{x}', str(x)).replace('{y}', str(y))
                            tile = page.request.get(url); assert tile.ok, (url, tile.status)
                            with Image.open(BytesIO(tile.body())) as image:
                                generated_image.paste(image, (x * manifest['tileSize'], y * manifest['tileSize']))
                    generated_image.save(output / 'free-generated-raster.png')
                    coverage = compare_coverage(before_reload, generated_image, 'SVG editor versus generated native tile raster')
                    assert_pixels(generated_image, round_probes + square_probes + circle_probes + rectangle_probes,
                                  'generated smooth outlines')
                records.append({'case': 'save-reload-and-generated-raster-preserve-free-shape-coverage', 'coverage': coverage})
            finally:
                before_reload.close()
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close(); browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Only generated solid-color PNGs and isolated synthetic campaign data.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
