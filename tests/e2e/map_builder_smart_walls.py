"""Review joined wall artwork and editable nodes in an isolated campaign.

Asymmetric synthetic artwork exposes texture flips, phase resets and corner
gaps. Pointer, touch and keyboard gestures edit actual persisted wall geometry.
"""
from __future__ import annotations

from base64 import b64decode
from copy import deepcopy
from io import BytesIO
import math
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import upload_asset, wait_ready
from map_builder_wall_art import assert_color, synthetic_wall


CELL = 64
BACKGROUND = (17, 34, 51)

WALL_RASTER = """async args=>{
 const svg=document.querySelector('[data-builder-canvas]').cloneNode(true);
 svg.setAttribute('width',args.width);svg.setAttribute('height',args.height);
 svg.setAttribute('viewBox',`0 0 ${args.columns} ${args.rows}`);
 svg.setAttribute('xmlns','http://www.w3.org/2000/svg');svg.setAttribute('preserveAspectRatio','none');
 for(const el of svg.querySelectorAll('[data-builder-grid],[data-builder-outline]'))el.remove();
 const cache=new Map();
 for(const image of svg.querySelectorAll('image')){
  const url=image.getAttribute('href');if(!url||url.startsWith('data:'))continue;
  if(!cache.has(url)){
   const response=await fetch(new URL(url,location.href));if(!response.ok)throw Error('Missing synthetic wall texture');
   const blob=await response.blob();cache.set(url,await new Promise((resolve,reject)=>{
    const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsDataURL(blob);
   }));
  }image.setAttribute('href',cache.get(url));
 }
 const url=URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(svg)],{type:'image/svg+xml;charset=utf-8'}));
 try{
  const image=new Image();await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=reject;image.src=url;});
  const canvas=document.createElement('canvas');canvas.width=args.width;canvas.height=args.height;
  canvas.getContext('2d').drawImage(image,0,0);return canvas.toDataURL('image/png');
 }finally{URL.revokeObjectURL(url);}
}"""

WALL_MESH_POLYGONS = """paths=>{
 const inverse=document.querySelector('[data-builder-canvas]').getScreenCTM().inverse();
 return paths.flatMap(path=>{
  const transform=inverse.multiply(path.getScreenCTM());
  return [...path.getAttribute('d').matchAll(/M([^Z]+)Z/g)].map(ring=>{
   const numbers=[...ring[1].matchAll(/[-+]?(?:\\d*\\.?\\d+)(?:e[-+]?\\d+)?/gi)].map(match=>Number(match[0]));
   const points=[];for(let i=0;i<numbers.length;i+=2){
    const p=new DOMPoint(numbers[i],numbers[i+1]).matrixTransform(transform);points.push([p.x*64,p.y*64]);
   }return points;
  });
 });
}"""


def same_box(before, after, bounds, label):
    from PIL import ImageChops
    pixels = tuple(round(value * CELL) for value in bounds)
    with before.crop(pixels) as a, after.crop(pixels) as b, ImageChops.difference(a, b) as difference:
        maximum = max(high for low, high in difference.getextrema())
        assert maximum <= 4, {'case': label, 'bounds': bounds, 'maxRgbDelta': maximum}


def wall_pixel(image, x, y, label):
    color = image.getpixel((round(x * CELL), round(y * CELL)))[:3]
    assert max(abs(a - b) for a, b in zip(color, BACKGROUND)) >= 60, (label, x, y, color)


def inside_polygon(point, ring):
    inside = False
    x, y = point
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]:
            inside = not inside
    return inside


def polygon_edge_distance(point, ring):
    result = float('inf')
    for a, b in zip(ring, ring[1:] + ring[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        square = dx * dx + dy * dy
        t = max(0, min(1, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / square)) if square else 0
        result = min(result, math.hypot(point[0] - a[0] - t * dx, point[1] - a[1] - t * dy))
    return result


def coverage_parity(before, after, polygons):
    from PIL import Image, ImageChops, ImageFilter
    assert before.size == after.size
    masks = []
    with Image.new('RGB', before.size, BACKGROUND) as background:
        for image in (before, after):
            with ImageChops.difference(image, background) as difference, difference.convert('L') as contrast:
                masks.append(contrast.point(lambda value: 255 if value > 20 else 0))
    try:
        counts, residuals = [], []
        assert polygons and all(len(ring) >= 3 for ring in polygons)
        for direction, (source, target) in enumerate((masks, list(reversed(masks)))):
            with source.filter(ImageFilter.MinFilter(5)) as interior, ImageChops.subtract(interior, target) as missing:
                count = missing.histogram()[255]
                assert count <= 4, {'missingWallInteriorPixels': count}
                bounds = missing.getbbox()
                if bounds:
                    for y in range(bounds[1], bounds[3]):
                        for x in range(bounds[0], bounds[2]):
                            if not missing.getpixel((x, y)):
                                continue
                            center = (x + .5, y + .5)
                            inside = any(inside_polygon(center, ring) for ring in polygons)
                            distance = min(polygon_edge_distance(center, ring) for ring in polygons)
                            evidence = {'direction': direction, 'pixel': [x, y], 'insideMesh': inside,
                                        'edgeDistancePx': distance, 'svg': before.getpixel((x, y)),
                                        'pillow': after.getpixel((x, y))}
                            assert distance <= .5, evidence
                            if direction == 0:
                                # SVG antialiasing can close a subpixel gap between
                                # independent layers. Missing actual mesh coverage
                                # is never accepted by the small count allowance.
                                assert not inside, evidence
                            residuals.append(evidence)
                counts.append(count)
        return {'missingMaskPixels': counts, 'geometricEdgeResiduals': residuals}
    finally:
        for mask in masks:
            mask.close()


def check_browser(base, seed, output, executable):
    from PIL import Image
    from playwright.sync_api import expect, sync_playwright

    records, errors, dialogs = [], [], []
    campaign = seed['campaign']
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900}, has_touch=True)
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        review = BuilderReview(page, campaign)

        def saved():
            return review.save()

        def position(x, y):
            return page.locator('[data-builder-canvas]').evaluate("""(svg,point)=>{
              const p=new DOMPoint(...point).matrixTransform(svg.getScreenCTM());return [p.x,p.y];
            }""", [x, y])

        def click(x, y):
            builder_workspace(page)
            page.mouse.click(*position(x, y))

        def ready_art():
            page.wait_for_function("""()=>{
              const walls=[...document.querySelectorAll('[data-builder-walls] [data-object-kind=walls]')];
              return walls.length>0&&walls.every(el=>el.dataset.wallArt==='ready'||el.dataset.wallArt==='builtin');
            }""")

        def raster(filename):
            preview = page.locator('[data-builder-preview]')
            was_preview = preview.get_attribute('aria-pressed') == 'true'
            if not was_preview:
                builder_workspace(page); preview.click()
            ready_art()
            encoded = page.evaluate(WALL_RASTER, {'width': 20 * CELL, 'height': 18 * CELL, 'columns': 20, 'rows': 18})
            image = Image.open(BytesIO(b64decode(encoded.split(',', 1)[1]))).convert('RGB')
            image.save(output / filename)
            if not was_preview:
                preview.click()
            return image

        def wall(a, b, asset=True, thickness=.8, identifier=None):
            return {'id': identifier or str(uuid4()), 'layerId': ground, 'assetId': asset_id if asset else None,
                    'x1': a[0], 'y1': a[1], 'x2': b[0], 'y2': b[1], 'thickness': thickness}

        def open_document(name, walls, doors=None, extra_layers=None):
            document = deepcopy(template)
            document.update(name=name, walls=deepcopy(walls), doors=deepcopy(doors or []))
            document['layers'] += deepcopy(extra_layers or [])
            project = review.store(str(uuid4()), 0, seed['folder'], document)
            page.goto(review.builder + '?project=' + project['id']); wait_ready(page)
            return project

        def select(identifier):
            builder_workspace(page)
            page.locator('[data-builder-quick-tool=select]').click()
            document = saved()['document']
            item = next(row for row in document['walls'] if row['id'] == identifier)
            # Avoid the midpoint's interactive plus when reselecting this wall.
            click(item['x1'] + (item['x2'] - item['x1']) * .25,
                  item['y1'] + (item['y2'] - item['y1']) * .25)
            expect(page.locator('[data-builder-wall-handle]')).to_have_count(2)

        def drag(element, endpoint, cancel=False):
            box = element.bounding_box()
            assert box and box['width'] >= 14 and box['height'] >= 14, box
            page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
            page.mouse.down(); page.mouse.move(*position(*endpoint), steps=8)
            if cancel:
                page.keyboard.press('Escape')
            page.mouse.up()

        def undo():
            page.locator('[data-builder-undo]').click()

        def redo():
            page.locator('[data-builder-redo]').click()

        def node_rows(document, point):
            found = []
            for item in document['walls']:
                if item['layerId'] != ground:
                    continue
                for suffix in ('1', '2'):
                    if abs(item['x' + suffix] - point[0]) < .001 and abs(item['y' + suffix] - point[1]) < .001:
                        found.append((item['id'], suffix))
            return found

        def assert_node(before, after, start, end):
            changed = node_rows(before, start)
            assert changed
            expected = deepcopy(before)
            for identifier, suffix in changed:
                item = next(row for row in expected['walls'] if row['id'] == identifier)
                item['x' + suffix], item['y' + suffix] = end
            assert after == expected

        try:
            page.goto(review.builder); wait_ready(page)
            name = page.locator('[data-builder-quick-name]')
            name.fill('Synthetic smart wall preparation'); name.press('Enter')
            asset_id = upload_asset(page, 'wall', 'Synthetic padded asymmetric joined wall.png', synthetic_wall())['id']
            template = deepcopy(saved()['document'])
            template.update(columns=20, rows=18, cellSize=CELL, background='#112233')
            ground = template['layers'][0]['id']
            single = open_document('Reference continuous wall phase', [wall((2, 3), (14, 3))])
            reference = raster('single-wall-reference.png')
            chain = [wall((2, 3), (8, 3)), wall((14, 3), (8, 3))]
            connected = open_document('Collinear wall phase across segment and direction', chain)
            with raster('collinear-wall-preview.png') as image:
                same_box(reference, image, (2.1, 2.8, 13.9, 3.2), 'collinear phase matches one wall')
                for x in (7.8, 8, 8.2):
                    wall_pixel(image, x, 3, 'no gap at collinear seam')
            reversed_chain = [{**row, 'x1': row['x2'], 'y1': row['y2'], 'x2': row['x1'], 'y2': row['y1']} for row in chain]
            reversed_project = open_document('Reversing authored endpoints preserves artwork', reversed_chain)
            with raster('reversed-wall-preview.png') as image:
                same_box(reference, image, (2.1, 2.8, 13.9, 3.2), 'direction reversal preserves canonical art')
            assert saved()['document'] == reversed_project['document']
            reference.close()
            records.append({'case': 'asymmetric-collinear-art-keeps-phase-and-direction-and-joins-without-rewriting-source'})

            a, b, c, left_l, right_l, door_wall = [str(uuid4()) for _ in range(6)]
            walls = [wall((2, 3), (8, 3), identifier=a), wall((8, 3), (14, 3), identifier=b),
                     wall((8, 3), (8, 9), identifier=c), wall((2, 11), (8, 11), identifier=left_l),
                     wall((8, 11), (8, 15), identifier=right_l), wall((2, 15), (14, 15), identifier=door_wall)]
            door = {'id': str(uuid4()), 'layerId': ground, 'assetId': None, 'x1': 6, 'y1': 15,
                    'x2': 7, 'y2': 15, 'thickness': .8, 'state': 'open'}
            art_project = open_document('L and T joined walls with an open doorway', walls, [door])
            with raster('wall-joins-preview.png') as image:
                for x, y in ((8.15, 10.85), (7.85, 11.15), (8, 3), (7.8, 3.1), (8.2, 3.1)):
                    wall_pixel(image, x, y, 'L/T join coverage')
                for x in (6.25, 6.5, 6.75):
                    assert_color(image.getpixel((round(x * CELL), 15 * CELL)), BACKGROUND, 'door opening', tolerance=4)
            records.append({'case': 'L-and-T-corners-fill-the-junction-and-open-door-keeps-a-real-gap'})

            # Node topology ignores material/thickness, but always respects layers.
            walls[2] = wall((8, 3), (8, 9), asset=False, thickness=.3, identifier=c)
            other_id = str(uuid4())
            other = {**wall((8, 3), (12, 6)), 'layerId': other_id}
            project = open_document('Editable shared nodes and independent doors', walls + [other], [door],
                                    [{'id': other_id, 'name': 'Locked independent wall layer', 'visible': True, 'locked': True}])
            original = deepcopy(project['document'])
            select(a)
            handle = page.locator('[data-builder-wall-handle][data-wall-endpoint=end]')
            drag(handle, (9.3, 4.2))
            moved = saved()
            assert_node(original, moved['document'], (8, 3), (9, 4))
            undo(); assert saved()['document'] == original
            redo(); moved = saved()
            select(a); drag(page.locator('[data-builder-wall-handle][data-wall-endpoint=end]'), (10, 5), cancel=True)
            cancelled = saved()
            assert cancelled['version'] == moved['version'] and cancelled['document'] == moved['document']
            undo(); assert saved()['document'] == original
            redo(); moved = saved()
            records.append({'case': 'dragging-shared-T-node-moves-three-connected-walls-across-materials-one-undo-and-Escape-keeps-version'})

            builder_sidebar(page, 'tools')
            page.locator('[data-builder-toggle-snap]').click()
            select(a); drag(page.locator('[data-builder-wall-handle][data-wall-endpoint=end]'), (9.35, 4.65))
            fractional = saved()
            actual = next(row for row in fractional['document']['walls'] if row['id'] == a)
            free_point = (actual['x2'], actual['y2'])
            assert abs(free_point[0] - 9.35) < .03 and abs(free_point[1] - 4.65) < .03, free_point
            assert_node(moved['document'], fractional['document'], (9, 4), free_point)
            select(a)
            endpoint = page.locator('[data-builder-wall-handle][data-wall-endpoint=end]')
            expect(endpoint).to_have_attribute('role', 'button')
            endpoint.focus(); endpoint.press('ArrowRight')
            expect(page.locator('[data-builder-wall-handle][data-wall-endpoint=end]')).to_be_focused()
            keyboard = saved()
            assert_node(fractional['document'], keyboard['document'], free_point, (round(free_point[0] + .1, 3), free_point[1]))
            undo(); assert saved()['document'] == fractional['document']
            builder_sidebar(page, 'layers')
            page.locator(f'[data-builder-layer-locked="{ground}"]').check()
            locked = saved()
            expect(page.locator('[data-builder-wall-handle]')).to_have_count(0)
            click(5, 3.5)
            assert saved()['document'] == locked['document']
            builder_sidebar(page, 'layers')
            page.locator(f'[data-builder-layer-locked="{ground}"]').uncheck()
            assert saved()['document'] == fractional['document']
            records.append({'case': 'fractional-and-keyboard-node-edits-respect-snap-layer-locks-other-layer-and-independent-door-geometry'})

            select(c)
            before_split = saved()['document']
            split = page.locator('[data-builder-wall-split]')
            split.focus(); split.press('Enter')
            expect(page.locator('[data-builder-viewport]')).to_be_focused()
            split_doc = saved()['document']
            old = next(row for row in before_split['walls'] if row['id'] == c)
            midpoint = ((old['x1'] + old['x2']) / 2, (old['y1'] + old['y2']) / 2)
            assert len(split_doc['walls']) == len(before_split['walls']) + 1 and len(node_rows(split_doc, midpoint)) == 2
            undo(); assert saved()['document'] == before_split
            select(c); drag(page.locator('[data-builder-wall-split]'), (12, 7))
            corner = saved()['document']
            assert len(corner['walls']) == len(before_split['walls']) + 1 and len(node_rows(corner, (12, 7))) == 2
            undo(); assert saved()['document'] == before_split
            redo(); assert saved()['document'] == corner
            records.append({'case': 'midpoint-Enter-adds-node-and-midpoint-drag-makes-a-corner-in-one-undo-step'})

            select(a)
            before_extend = saved()['document']
            page.locator('[data-builder-wall-extend=start]').click()
            click(1, 5)
            extended = saved()['document']
            added = [row for row in extended['walls'] if row['id'] not in {item['id'] for item in before_extend['walls']}]
            assert len(added) == 1
            assert {(added[0]['x1'], added[0]['y1']), (added[0]['x2'], added[0]['y2'])} == {(2, 3), (1, 5)}
            assert all(next(row for row in extended['walls'] if row['id'] == old['id']) == old for old in before_extend['walls'])
            undo(); assert saved()['document'] == before_extend
            redo(); extended = saved()['document']
            select(a); drag(page.locator('[data-builder-wall-extend=end]'), (14, 2))
            assert len(saved()['document']['walls']) == len(extended['walls']) + 1
            undo(); assert saved()['document'] == extended
            select(a)
            stable = saved()
            page.locator('[data-builder-wall-extend=start]').click(); page.keyboard.press('Escape')
            assert saved()['document'] == stable['document'] and saved()['version'] == stable['version']
            select(a)
            plus = page.locator('[data-builder-wall-extend=start]')
            plus.focus(); plus.press('Enter')
            expect(page.locator('[data-builder-viewport]')).to_be_focused()
            page.keyboard.press('Escape')
            assert saved()['document'] == stable['document'] and saved()['version'] == stable['version']
            page.screenshot(path=str(output / 'wall-nodes-desktop.png'))
            records.append({'case': 'endpoint-plus-click-and-drag-extend-with-new-segments-one-undo-and-Escape-cancels-armed-extension'})

            select(a)
            before_t = saved()['document']
            page.locator('[data-builder-wall-extend=end]').click()
            click(10.02, 15.04)
            connected_t = saved()['document']
            new_walls = [row for row in connected_t['walls'] if row['id'] not in {item['id'] for item in before_t['walls']}]
            assert len(new_walls) == 2, new_walls
            branch = next(row for row in new_walls if (row['x1'], row['y1']) == free_point or (row['x2'], row['y2']) == free_point)
            target_node = (branch['x2'], branch['y2']) if (branch['x1'], branch['y1']) == free_point else (branch['x1'], branch['y1'])
            assert abs(target_node[0] - 10.02) < .04 and target_node[1] == 15, target_node
            assert len(node_rows(connected_t, target_node)) == 3
            assert connected_t['doors'] == before_t['doors']
            undo(); assert saved()['document'] == before_t
            records.append({'case': 'extending-onto-an-existing-wall-snaps-to-edge-creates-shared-T-node-and-is-one-undo'})

            # Pixel-sized targets remain usable after zooming on a narrow screen.
            change_locale(page, 'pt-BR', campaign)
            page.set_viewport_size({'width': 390, 'height': 844}); page.reload(); wait_ready(page)
            builder_sidebar(page, 'tools')
            if page.locator('[data-builder-toggle-snap]').get_attribute('aria-pressed') == 'true':
                page.locator('[data-builder-toggle-snap]').click()
            builder_workspace(page)
            page.locator('[data-builder-zoom=in]').click()
            select(a)
            handle = page.locator('[data-builder-wall-handle][data-wall-endpoint=end]')
            expect(handle).to_have_attribute('aria-label', 'Mover nó de paredes conectadas')
            bounds = handle.bounding_box()
            assert 18 <= bounds['width'] <= 26 and 18 <= bounds['height'] <= 26, bounds
            mobile_before = saved()['document']
            item = next(row for row in mobile_before['walls'] if row['id'] == a)
            old_point = (item['x2'], item['y2'])
            target = (old_point[0] + .7, old_point[1] + .6)
            end = position(*target)
            cdp = context.new_cdp_session(page)
            start = {'x': bounds['x'] + bounds['width'] / 2, 'y': bounds['y'] + bounds['height'] / 2}
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [start]})
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': end[0], 'y': end[1]}]})
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
            cdp.detach()
            mobile = saved()['document']
            moved_item = next(row for row in mobile['walls'] if row['id'] == a)
            touched = (moved_item['x2'], moved_item['y2'])
            assert abs(touched[0] - target[0]) < .04 and abs(touched[1] - target[1]) < .04, touched
            assert_node(mobile_before, mobile, old_point, touched)
            undo(); assert saved()['document'] == mobile_before
            select(a)
            metrics = page.locator('[data-map-builder]').evaluate(MEASURE)
            assert not metrics['tiny'] and not metrics['overflow'], metrics
            page.screenshot(path=str(output / 'wall-nodes-pt-BR-390-zoom.png'))
            records.append({'case': 'zoomed-mobile-endpoint-handles-keep-screen-size-and-real-touch-drag-has-one-undo'})

            page.set_viewport_size({'width': 1440, 'height': 900}); page.reload(); wait_ready(page)
            final_source = saved()
            assert final_source['document'] == mobile_before
            assert final_source['document']['doors'] == original['doors']
            assert next(row for row in final_source['document']['walls'] if row['id'] == other['id']) == other
            with raster('edited-walls-preview.png') as expected:
                polygons = page.locator('[data-builder-wall-mesh]').evaluate_all(WALL_MESH_POLYGONS)
                with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                    page.locator('[data-builder-generate]').click()
                assert generated.value.ok, generated.value.text()
                page.wait_for_url(f'{base}/game/{campaign}')
                stored = review.project(project['id'])
                assert stored['document'] == final_source['document']
                manifest = page.request.get(f"/api/maps/{stored['sceneId']}/manifest").json()
                level = next(row for row in manifest['levels'] if row['lod'] == 0)
                with Image.new('RGB', (manifest['width'], manifest['height'])) as image:
                    for y in range(level['rows']):
                        for x in range(level['columns']):
                            url = manifest['tileUrlTemplate'].replace('{lod}', '0').replace('{x}', str(x)).replace('{y}', str(y))
                            tile = page.request.get(url); assert tile.ok
                            with Image.open(BytesIO(tile.body())) as source:
                                image.paste(source, (x * manifest['tileSize'], y * manifest['tileSize']))
                    image.save(output / 'edited-walls-generated.png')
                    comparison = coverage_parity(expected, image, polygons)
                    for x in (6.25, 6.5, 6.75):
                        assert_color(image.getpixel((round(x * CELL), 15 * CELL)), BACKGROUND, 'generated door opening', tolerance=4)
                    for x, y in ((8.15, 10.85), (7.85, 11.15)):
                        wall_pixel(image, x, y, 'generated L corner')
                state = page.request.get(f"/api/maps/{stored['sceneId']}/state").json()
                assert any(row['kind'] == 'door' and row['door_state'] == 'open' for row in state['walls'])
            records.append({'case': 'saved-edited-nodes-reopen-and-generate-with-matching-wall-coverage-open-door-and-source-preserved',
                            'coverage': comparison})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close(); browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Synthetic padded asymmetric RGB wall strip; isolated campaign only.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
