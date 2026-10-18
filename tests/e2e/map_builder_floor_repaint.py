"""Verify floor repainting through actual brushes and generated raster pixels.

Campaigns, assets, databases, browser state and output files are disposable.
No-op checks compare persisted versions, complete source documents and history;
coverage probes independently check union-minus-cuts geometry.
"""
from __future__ import annotations

from base64 import b64decode
from copy import deepcopy
from io import BytesIO
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import builder_sidebar, builder_workspace
from map_builder_asset_removal import BuilderReview
from map_builder_free_paint import SVG_RASTER, artwork
from map_builder_reference import upload_asset, wait_ready
from map_builder_tiles_only import assert_pixels, compare_rasters


CELL = 64
RED, BLUE, GREEN, BACKGROUND = (224, 64, 32), (32, 64, 128), (48, 192, 96), (17, 34, 51)


def in_ring(point, ring):
    x, y = point
    inside = False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
            inside = not inside
    return inside


def covering(document, layer_id, x, y):
    result = []
    for row in document['floors']:
        if row['layerId'] != layer_id or not (row['x'] <= x < row['x'] + row['width'] and row['y'] <= y < row['y'] + row['height']):
            continue
        point = [(x - row['x']) / row['width'], (y - row['y']) / row['height']]
        shape = row.get('shape')
        if not shape or any(in_ring(point, ring) for ring in shape['contours']) and not any(in_ring(point, ring) for ring in shape['cuts']):
            result.append(row)
    return result


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

        def point(x, y):
            return page.locator('[data-builder-canvas]').evaluate("""(svg,point)=>{
              const p=new DOMPoint(...point).matrixTransform(svg.getScreenCTM());return [p.x,p.y];
            }""", [x, y])

        def click(x, y):
            builder_workspace(page)
            page.mouse.click(*point(x, y))

        def saved():
            return review.save()

        def tools():
            builder_sidebar(page, 'tools')

        def paint(material, size=1, snap=True, shape='square'):
            tools()
            if page.locator('[data-builder-toggle-snap]').get_attribute('aria-pressed') != str(snap).lower():
                page.locator('[data-builder-toggle-snap]').click()
            page.locator('[data-builder-tool=floor]').click()
            page.locator('[data-builder-brush-material]').select_option(material)
            page.locator('[data-builder-brush-shape]').select_option(shape)
            page.locator('[data-builder-brush=rotation]').fill('0')
            page.locator('[data-builder-brush=rotation]').dispatch_event('change')
            page.locator('[data-builder-quick-tool=paint]').click()
            field = page.locator('[data-builder-quick-brush-size]')
            field.fill(str(size)); field.press('Enter')

        def no_op(project, action, label):
            before = deepcopy(project)
            action()
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved')
            result = saved()
            assert result['document'] == before['document'], (label, 'source changed')
            assert result['version'] == before['version'], (label, before['version'], result['version'])
            assert [row['id'] for row in result['document']['floors']] == [row['id'] for row in before['document']['floors']]
            return result

        def fixture(name, floors, metadata=None):
            document = deepcopy(template)
            layer_id, upper_id = str(uuid4()), str(uuid4())
            document.update(name=name, layers=[
                {'id': layer_id, 'name': 'Active floor layer', 'visible': True, 'locked': False},
                {'id': upper_id, 'name': 'Unchanged other layer', 'visible': True, 'locked': False}])
            document['floors'] = [{**deepcopy(row), 'id': row.get('id', str(uuid4())), 'layerId': layer_id} for row in floors]
            other = {'id': str(uuid4()), 'layerId': upper_id, 'assetId': green,
                     'x': 14, 'y': 9, 'width': 3, 'height': 3, 'rotation': 0}
            document['floors'].append(other)
            if metadata:
                metadata(document)
            project = review.store(str(uuid4()), 0, seed['folder'], document)
            page.goto(review.builder + '?project=' + project['id']); wait_ready(page)
            return project, layer_id, other

        def raster(filename):
            encoded = page.evaluate(SVG_RASTER, {'width': 20 * CELL, 'height': 14 * CELL,
                                                'columns': 20, 'rows': 14, 'ids': None})
            image = Image.open(BytesIO(b64decode(encoded.split(',', 1)[1]))).convert('RGB')
            image.save(output / filename)
            return image

        def sample(x, y, material):
            page.locator('[data-builder-quick-tool=paint]').click()
            page.locator('[data-builder-viewport]').focus()
            page.keyboard.press('i'); click(x, y)
            tools()
            expect(page.locator('[data-builder-brush-material]')).to_have_value(material)
            builder_workspace(page)

        def other_unchanged(project, other):
            assert next(row for row in project['document']['floors'] if row['id'] == other['id']) == other

        try:
            page.goto(review.builder); wait_ready(page)
            name = page.locator('[data-builder-quick-name]')
            name.fill('Synthetic floor repaint preparation'); name.press('Enter')
            red = upload_asset(page, 'floor', 'Synthetic red floor.png', artwork(RED))['id']
            blue = upload_asset(page, 'floor', 'Synthetic blue floor.png', artwork(BLUE))['id']
            green = upload_asset(page, 'floor', 'Synthetic green other-layer floor.png', artwork(GREEN))['id']
            template = deepcopy(saved()['document'])
            template.update(columns=20, rows=14, cellSize=CELL, background='#112233')

            project, layer, other = fixture('Identical cell repaint and mixed free geometry', [
                {'assetId': red, 'x': 1, 'y': 1, 'width': 1, 'height': 1, 'rotation': 0,
                 'paint': {'color': None, 'opacity': 1}},
                {'assetId': blue, 'x': 2, 'y': 1, 'width': 1, 'height': 1, 'rotation': 0}])
            paint(red)
            project = no_op(project, lambda: click(1.5, 1.5), 'identical unit tile and normalized opaque style')
            click(5.5, 1.5); changed = saved()
            no_op(changed, lambda: click(5.5, 1.5), 'same new cell after one meaningful edit')
            page.locator('[data-builder-undo]').click()
            assert saved()['document'] == project['document']
            page.locator('[data-builder-redo]').click(); changed = saved()
            paint(red, 2.5, False, 'circle'); click(8.25, 8.25)
            mixed = saved()
            assert any(row.get('shape') for row in mixed['document']['floors'])
            paint(red)
            mixed = no_op(mixed, lambda: click(1.5, 1.5), 'same cell in a document containing free geometry')
            other_unchanged(mixed, other)
            records.append({'case': 'same-cell-repaint-preserves-IDs-order-source-version-and-does-not-consume-Undo-even-with-free-geometry'})

            paint(red, 2.5, False, 'circle')
            mixed = no_op(mixed, lambda: click(8.25, 8.25), 'same free round stamp')
            review.stroke((8.25, 8.25), (10.75, 8.25)); union = saved()
            assert union['document'] != mixed['document']
            for x, y in ((7.25, 8.25), (8.25, 8.25), (9.5, 8.25), (11.5, 8.25)):
                rows = covering(union['document'], layer, x, y)
                assert len(rows) == 1 and rows[0]['assetId'] == red, (x, y, rows)
            no_op(union, lambda: review.stroke((8.25, 8.25), (10.75, 8.25)), 'footprint covered by union of same free floors')
            page.locator('[data-builder-undo]').click(); assert saved()['document'] == mixed['document']
            page.locator('[data-builder-redo]').click(); union = saved()
            with raster('same-free-union-editor.png') as image:
                assert_pixels(image, [(7.25, 8.25, RED), (9.5, 8.25, RED), (11.5, 8.25, RED), (14.5, 10.5, GREEN)], 'same free union')
            other_unchanged(union, other)
            records.append({'case': 'free-circle-and-swept-strokes-have-one-coverage-and-repainting-their-union-is-a-true-no-op'})

            family = 'Synthetic varied floor family'

            def family_metadata(document):
                for row in document['assets']:
                    if row['assetId'] in (red, blue):
                        row['family'] = family

            grid = [{'assetId': red if (x + y) % 2 else blue, 'x': x, 'y': y, 'width': 1, 'height': 1, 'rotation': 0}
                    for y in range(4, 7) for x in range(1, 4)]
            family_project, layer, other = fixture('Family preservation and partial grid replacement', grid, family_metadata)
            paint('family:' + family, 3)
            page.evaluate('()=>{window.repaintRandom=Math.random;Math.random=()=>.999;}')
            try:
                no_op(family_project, lambda: click(1.25, 4.25), 'eligible family variations must not reroll')
            finally:
                page.evaluate('()=>{Math.random=window.repaintRandom;delete window.repaintRandom;}')
            paint(red, 3); click(1.25, 4.25)
            replaced = saved()
            same = [row for row in family_project['document']['floors'] if row['layerId'] == layer and row['assetId'] == red]
            for old in same:
                assert next(row for row in replaced['document']['floors'] if row['id'] == old['id']) == old
            assert [row['id'] for row in replaced['document']['floors'] if row['id'] in {item['id'] for item in same}] == [row['id'] for row in same]
            assert len([row for row in replaced['document']['floors'] if row['layerId'] == layer]) == 9
            for y in range(4, 7):
                for x in range(1, 4):
                    rows = covering(replaced['document'], layer, x + .5, y + .5)
                    assert len(rows) == 1 and rows[0]['assetId'] == red, rows
            other_unchanged(replaced, other)
            sample(2.5, 5.5, red)
            with raster('partial-grid-replacement-editor.png') as image:
                assert_pixels(image, [(1.5, 4.5, RED), (2.5, 5.5, RED), (3.5, 6.5, RED), (14.5, 10.5, GREEN)], 'partial grid replacement')
            records.append({'case': 'family-repaint-keeps-original-variations-and-partial-grid-brush-only-replaces-different-cells-without-overdraw'})

            geometry = {'contours': [[[0, 0], [1, 0], [1, 1], [0, 1]]],
                        'cuts': [[[.1, .125], [.2, .125], [.2, .25], [.1, .25]]]}
            project, layer, other = fixture('Different material replaces free area while preserving authored holes', [
                {'assetId': red, 'x': 2, 'y': 2, 'width': 10, 'height': 8, 'rotation': 0, 'shape': geometry},
                {'assetId': blue, 'x': 1, 'y': 1, 'width': 1, 'height': 1, 'rotation': 0}])
            paint(blue, 4, False, 'circle'); click(8, 6)
            replaced = saved()
            for x, y, material in ((8, 6, blue), (8, 4.2, blue), (6.3, 4.3, red), (11.5, 9.5, red)):
                rows = covering(replaced['document'], layer, x, y)
                assert len(rows) == 1 and rows[0]['assetId'] == material, (x, y, rows)
            assert not covering(replaced['document'], layer, 3.5, 3.5)
            other_unchanged(replaced, other)
            sample(8, 6, blue); sample(6.3, 4.3, red)
            probes = [(8, 6, BLUE), (8, 4.2, BLUE), (6.3, 4.3, RED), (3.5, 3.5, BACKGROUND),
                      (11.5, 9.5, RED), (14.5, 10.5, GREEN)]
            with raster('different-free-replacement-editor.png') as image:
                assert_pixels(image, probes, 'free replacement and preserved hole')
            paint(blue, 4, False, 'circle')
            replaced = no_op(replaced, lambda: click(8, 6), 'identical circle after different-material replacement')
            paint(blue)
            no_op(replaced, lambda: click(8.25, 6.25), 'unit footprint fully inside existing same free circle')
            click(6.25, 4.25); mixed_replacement = saved()
            for x, y, material in ((6.2, 4.2, blue), (6.8, 4.8, blue), (8, 6, blue), (5.8, 4.2, red), (11.5, 9.5, red)):
                rows = covering(mixed_replacement['document'], layer, x, y)
                assert len(rows) == 1 and rows[0]['assetId'] == material, (x, y, rows)
            assert not covering(mixed_replacement['document'], layer, 3.5, 3.5)
            other_unchanged(mixed_replacement, other)
            sample(6.2, 4.2, blue)
            probes = [(x, y, BLUE if (x, y) == (6.3, 4.3) else color) for x, y, color in probes]
            probes += [(6.2, 4.2, BLUE), (6.8, 4.8, BLUE), (5.8, 4.2, RED)]
            page.reload(); wait_ready(page)
            assert saved()['document'] == mixed_replacement['document']
            records.append({'case': 'different-free-and-grid-over-free-replacements-remove-overdraw-preserve-outside-holes-other-layer-and-sample-correct-material'})

            with raster('repaint-final-editor.png') as expected:
                assert_pixels(expected, probes, 'saved replacement')
                page.locator('[data-builder-preview]').click()
                page.screenshot(path=str(output / 'repaint-preview.png'))
                with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                    page.locator('[data-builder-generate]').click()
                assert generated.value.ok, generated.value.text()
                page.wait_for_url(f'{base}/game/{campaign}')
                final = review.project(project['id'])
                assert final['document'] == mixed_replacement['document']
                manifest = page.request.get(f"/api/maps/{final['sceneId']}/manifest").json()
                level = next(row for row in manifest['levels'] if row['lod'] == 0)
                with Image.new('RGB', (manifest['width'], manifest['height'])) as image:
                    for y in range(level['rows']):
                        for x in range(level['columns']):
                            url = manifest['tileUrlTemplate'].replace('{lod}', '0').replace('{x}', str(x)).replace('{y}', str(y))
                            tile = page.request.get(url); assert tile.ok
                            with Image.open(BytesIO(tile.body())) as source:
                                image.paste(source, (x * manifest['tileSize'], y * manifest['tileSize']))
                    image.save(output / 'repaint-final-generated.png')
                    comparison = compare_rasters(expected, image, final['document'])
                    assert_pixels(image, probes, 'generated replacement')
            records.append({'case': 'save-reopen-preview-generate-preserve-replacement-source-and-real-raster-pixel-parity', 'comparison': comparison})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close(); browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Synthetic opaque solid-color floor PNGs in a disposable campaign.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
