"""Exercise explicitly named mixed layers and the collection toolbar.

Uses disposable campaigns, public project APIs and actual browser controls.
New projects have one editable generic layer; an explicitly emptied document
never acquires another layer as a side effect of fixture readiness.
"""
from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import create_layer, set_name, synthetic_texture, wait_ready


KINDS = ('floors', 'walls', 'doors', 'decorations', 'lights', 'particles', 'shaders')


def check_browser(base, seed, output, executable):
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

        def saved():
            return review.save()['document']

        def point(x, y):
            return page.locator('[data-builder-canvas]').evaluate("""(svg,point)=>{
              const p=new DOMPoint(...point).matrixTransform(svg.getScreenCTM());return [p.x,p.y];
            }""", [x, y])

        def click(x, y):
            page.mouse.click(*point(x, y))

        def contents(layer):
            builder_sidebar(page, 'layers')
            details = page.locator(f'[data-builder-layer-contents="{layer}"]')
            if not details.evaluate('el=>el.open'):
                details.locator('summary').click()
            return details

        def import_floor(name, collection, kind):
            builder_workspace(page)
            page.locator('[data-builder-import]').click()
            modal = page.locator('[data-builder-import-modal]')
            modal.locator('[data-builder-import-role]').select_option('floor')
            modal.locator('[data-builder-import-collection]').fill(collection)
            modal.locator('[data-builder-upload]').set_input_files({
                'name': name, 'mimeType': 'image/png', 'buffer': synthetic_texture(kind)})
            with page.expect_response(lambda response: '/library/upload' in response.url) as uploaded:
                modal.locator('[data-builder-import-submit]').click()
            assert uploaded.value.status == 201, uploaded.value.text()
            wait_ready(page)
            return uploaded.value.json()['id']

        def generate(project_id):
            builder_workspace(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            project = review.project(project_id)
            response = page.request.get(f"/api/maps/{project['sceneId']}/state")
            assert response.ok, response.text()
            return project, response.json()

        try:
            page.goto(review.builder); wait_ready(page)
            expect(page.locator('[data-builder-layer]')).to_have_count(0)
            expect(page.locator('[data-builder-create-first-layer]')).to_be_hidden()
            initial_layer = page.locator('[data-builder-active-layer-select]').input_value()
            assert initial_layer
            builder_sidebar(page, 'layers')
            expect(page.locator('[data-builder-project-layer]')).to_have_count(1)
            title = page.locator(f'[data-builder-layer-title="{initial_layer}"]')
            title.fill('My explicitly renamed starting layer'); title.press('Tab')
            initial = saved()
            assert len(initial['layers']) == 1 and initial['layers'][0]['name'] == 'My explicitly renamed starting layer'
            assert not any(initial.get(kind, []) for kind in KINDS)
            records.append({'case': 'new-project-has-one-empty-generic-renamable-layer-and-no-fixed-object-type-layers'})
            page.locator(f'[data-builder-layer-remove="{initial_layer}"]').click()
            builder_workspace(page)
            expect(page.locator('[data-builder-create-first-layer]')).to_be_visible()
            expect(page.locator('[data-builder-active-layer-select]')).to_have_value('')
            expect(page.locator('[data-builder-active-layer-select]')).to_be_disabled()
            set_name(page, 'Synthetic empty project with explicit custom layers')
            empty = review.save()
            assert empty['document']['layers'] == []
            assert not any(empty['document'].get(kind, []) for kind in KINDS)
            page.reload(); wait_ready(page)
            assert saved() == empty['document']
            page.locator('[data-builder-preview]').click()
            expect(page.locator('[data-builder-create-first-layer]')).to_be_hidden()
            page.locator('[data-builder-preview]').click()
            expect(page.locator('[data-builder-create-first-layer]')).to_be_visible()
            page.screenshot(path=str(output / 'custom-layers-empty.png'))
            _, native = generate(empty['id'])
            assert not any(native.get(kind, []) for kind in ('lights', 'particles', 'shaders', 'walls'))
            assert review.project(empty['id'])['document'] == empty['document']
            records.append({'case': 'explicitly-emptied-project-saves-reopens-previews-and-generates-without-recreating-a-layer'})

            page.goto(review.builder + '?project=' + empty['id']); wait_ready(page)
            builder_tool(page, 'floor')
            review.stroke((4, 4), (5, 4))
            expect(page.locator('[data-builder-layer-name]')).to_be_focused()
            assert saved()['layers'] == []
            assert not saved()['floors']
            builder_workspace(page)
            page.locator('[data-builder-create-first-layer]').click()
            expect(page.locator('[data-builder-layer-name]')).to_be_focused()
            expect(page.locator('[data-builder-layer-add]')).to_be_disabled()
            base_layer = create_layer(page, 'Ground and atmosphere - mixed authored layer')
            expect(page.locator('[data-builder-create-first-layer]')).to_be_hidden()
            other_layer = create_layer(page, 'Upper accents - deliberately long authored layer name')
            builder_sidebar(page, 'layers')
            page.locator(f'[data-builder-layer-remove="{other_layer}"]').click()
            assert [row['id'] for row in saved()['layers']] == [base_layer]
            other_layer = create_layer(page, 'Upper accents - deliberately long authored layer name')
            records.append({'case': 'no-implicit-layer-from-drawing-first-layer-CTA-focuses-name-and-Enter-creates-named-layers'})

            stone = import_floor('Synthetic stone collection material.png', 'Stone collection', 'floor')
            accent = import_floor('Synthetic accent collection material.png', 'Accent collection', 'wall')
            collection = page.locator('[data-builder-collection-filter]')
            expect(collection).to_have_count(1)
            assert collection.evaluate('el=>el.closest(".map-builder__dock-toolbar")!==null')
            assert not page.locator('.map-builder__asset-details').evaluate('el=>el.open')
            page.locator('[data-builder-role=floor]').click()
            collection.select_option('Stone collection')
            expect(page.locator('[data-builder-assets] [data-asset-id]')).to_have_count(1)
            expect(page.locator(f'[data-builder-assets] [data-asset-id="{stone}"]')).to_be_visible()
            page.locator('[data-builder-search]').fill('missing material')
            expect(page.locator('[data-builder-assets] [data-asset-id]')).to_have_count(0)
            page.locator('[data-builder-search]').fill('')
            collection.select_option('Accent collection')
            expect(page.locator(f'[data-builder-assets] [data-asset-id="{accent}"]')).to_be_visible()
            collection.select_option('')
            records.append({'case': 'single-collection-filter-beside-search-filters-real-cards-without-opening-library-settings'})

            builder_sidebar(page, 'tools')
            page.locator('[data-builder-active-layer-select]').select_option(base_layer)
            builder_tool(page, 'floor')
            page.locator('[data-builder-brush-material]').select_option(stone)
            page.locator('[data-builder-paint-mode]').select_option('rectangle')
            review.stroke((2, 2), (3, 3))
            builder_tool(page, 'wall'); review.stroke((2, 7), (6, 7))
            builder_tool(page, 'door'); review.stroke((10, 9), (12, 9))
            page.locator('[data-builder-role=light]').click()
            page.locator('[data-builder-light-preset=torch]').click(); click(14, 5)
            page.locator('[data-builder-role=effect]').click()
            page.locator('[data-builder-collection-filter]').select_option('particle')
            page.locator('[data-builder-particle-preset=smoke]').click(); click(16, 6)
            page.locator('[data-builder-collection-filter]').select_option('shader')
            page.locator('[data-builder-shader-preset=orb-1]').click(); click(19, 8)
            authored = saved()
            for kind in ('floors', 'walls', 'doors', 'lights', 'particles', 'shaders'):
                assert len(authored[kind]) == 1 and authored[kind][0]['layerId'] == base_layer, (kind, authored.get(kind))
            expect(page.locator('[data-builder-native-preview] canvas')).to_have_count(1)
            details = contents(base_layer)
            expect(details.locator('[data-builder-layer-object]')).to_have_count(6)
            floor_id, wall_id = authored['floors'][0]['id'], authored['walls'][0]['id']
            wall = authored['walls'][0]
            erase_point = ((wall['x1'] + wall['x2']) / 2, (wall['y1'] + wall['y2']) / 2)
            details.locator(f'[data-builder-layer-object="{floor_id}"]').click()
            expect(details.locator(f'[data-builder-layer-object="{floor_id}"]')).to_have_attribute('aria-pressed', 'true')
            details.locator(f'[data-builder-layer-object="{wall_id}"]').click(modifiers=['Shift'])
            expect(details.locator('[data-builder-layer-object][aria-pressed=true]')).to_have_count(2)
            page.locator(f'[data-builder-layer-locked="{base_layer}"]').check()
            expect(details.locator('[data-builder-layer-object]:enabled')).to_have_count(0)
            expect(page.locator(f'[data-builder-layer-copy="{base_layer}"]')).to_be_disabled()
            page.locator(f'[data-builder-layer-locked="{base_layer}"]').uncheck()
            page.locator(f'[data-builder-layer-visible="{base_layer}"]').uncheck()
            expect(page.locator('[data-builder-native-preview] canvas')).to_have_count(0)
            page.locator(f'[data-builder-layer-visible="{base_layer}"]').check()
            expect(page.locator('[data-builder-native-preview] canvas')).to_have_count(1)
            records.append({'case': 'mixed-layer-lists-and-selects-real-objects-lock-blocks-edit-and-hide-releases-native-renderer'})

            # A real clone includes native objects and remaps authored references.
            project = review.save()
            with_graph = deepcopy(project['document'])
            light_id = with_graph['lights'][0]['id']
            with_graph['doors'][0]['blueprint'] = {'version': 2, 'kind': 'door',
                'states': {state: {'appearance': 'inherit'} for state in ('open', 'closed', 'locked')},
                'graphs': {'enter:open': {'nodes': [
                    {'id': 'event', 'type': 'event', 'event': 'enter:open', 'x': 0, 'y': 0},
                    {'id': 'lamp', 'type': 'light', 'targetId': light_id, 'enabled': True, 'x': 300, 'y': 0}],
                    'edges': [{'from': 'event', 'output': 'next', 'to': 'lamp', 'kind': 'execution'}]}}}
            project = review.store(project['id'], project['version'], project['folderId'], with_graph)
            page.goto(review.builder + '?project=' + project['id']); wait_ready(page)
            builder_sidebar(page, 'layers')
            page.locator(f'[data-builder-layer-copy="{base_layer}"]').click()
            cloned = saved()
            clone_layer = next(row['id'] for row in cloned['layers'] if row['id'] not in (base_layer, other_layer))
            for kind in ('floors', 'walls', 'doors', 'lights', 'particles', 'shaders'):
                old = next(row for row in cloned[kind] if row['layerId'] == base_layer)
                copied = next(row for row in cloned[kind] if row['layerId'] == clone_layer)
                assert copied['id'] != old['id']
                coordinates = ('x1', 'y1', 'x2', 'y2') if kind in ('walls', 'doors') else ('x', 'y')
                assert all(copied[key] == old[key] + 1 for key in coordinates), (kind, old, copied)
            copied_light = next(row for row in cloned['lights'] if row['layerId'] == clone_layer)
            copied_door = next(row for row in cloned['doors'] if row['layerId'] == clone_layer)
            assert copied_door['blueprint']['graphs']['enter:open']['nodes'][1]['targetId'] == copied_light['id']
            page.locator('[data-builder-undo]').click()
            assert saved() == project['document']
            page.locator('[data-builder-redo]').click()
            assert saved() == cloned
            records.append({'case': 'duplicate-layer-copies-mixed-native-objects-offsets-one-cell-remaps-blueprint-and-has-one-history-step'})

            builder_sidebar(page, 'layers')
            before_order = [row['id'] for row in cloned['layers']]
            while page.locator('[data-builder-layer-contents][open]').count():
                page.locator('[data-builder-layer-contents][open] > summary').first.click()
            page.set_viewport_size({'width': 1440, 'height': 1200})
            handle = page.locator(f'[data-builder-layer-drag="{base_layer}"]')
            source_row = page.locator(f'[data-builder-project-layer="{base_layer}"]')
            target = page.locator(f'[data-builder-project-layer="{clone_layer}"]')
            handle.scroll_into_view_if_needed()
            source_box, target_box = handle.bounding_box(), target.bounding_box()
            start = (source_box['x'] + source_box['width'] / 2, source_box['y'] + source_box['height'] / 2)
            end = (target_box['x'] + 120, target_box['y'] + 5)
            page.mouse.move(*start); page.mouse.down()
            page.mouse.move(start[0] + 10, start[1], steps=3)
            page.mouse.move(*end, steps=8); page.mouse.move(end[0] + 1, end[1] + 1)
            expect(source_row).to_have_attribute('data-dragging', 'true')
            expect(target).to_have_attribute('data-drop-target', 'before')
            page.screenshot(path=str(output / 'custom-layers-drag.png'))
            page.mouse.up()
            reordered = saved()
            order = [row['id'] for row in reordered['layers']]
            assert order != before_order and order.index(base_layer) == order.index(clone_layer) + 1, (before_order, order)
            assert reordered['floors'] == cloned['floors'] and reordered['lights'] == cloned['lights']
            page.locator('[data-builder-undo]').click(); assert saved() == cloned
            page.locator('[data-builder-redo]').click(); assert saved() == reordered
            page.set_viewport_size({'width': 1440, 'height': 900})
            records.append({'case': 'native-drag-handle-reorders-stack-without-changing-objects-and-one-undo-restores-order'})

            # Closed lazy details must never retain an erased object's old ID.
            details = contents(base_layer)
            details.locator('summary').click()
            builder_workspace(page)
            builder_sidebar(page, 'tools')
            page.locator('[data-builder-active-layer-select]').select_option(base_layer)
            builder_tool(page, 'erase'); click(*erase_point)
            erased = saved()
            assert all(row['id'] != wall_id for row in erased['walls'])
            details = contents(base_layer)
            expect(details.locator(f'[data-builder-layer-object="{wall_id}"]')).to_have_count(0)
            assert not errors, errors
            page.locator('[data-builder-undo]').click(); assert saved() == reordered
            contents(base_layer)
            click(*erase_point)
            expect(page.locator(f'[data-builder-layer-object="{wall_id}"]')).to_have_count(0)
            assert all(row['id'] != wall_id for row in saved()['walls'])
            page.locator('[data-builder-undo]').click(); assert saved() == reordered
            records.append({'case': 'erase-refreshes-both-closed-lazy-and-open-layer-contents-and-undo-restores-original-object'})

            project = review.save()
            builder_workspace(page); page.locator('[data-builder-preview]').click()
            expect(page.locator('[data-builder-native-preview] canvas')).to_have_count(1)
            page.screenshot(path=str(output / 'custom-layers-preview.png'))
            page.locator('[data-builder-preview]').click()
            page.reload(); wait_ready(page)
            assert saved() == project['document']
            generated, native = generate(project['id'])
            assert generated['document'] == project['document']
            assert len(native['lights']) == len(native['particles']) == len(native['shaders']) == 2
            assert len([row for row in native['walls'] if row['kind'] == 'door']) == 2
            records.append({'case': 'save-reopen-preview-and-generation-preserve-manual-layers-and-native-effects'})

            page.goto(review.builder + '?project=' + project['id']); wait_ready(page)
            for locale, width in (('en', 1440), ('pt-BR', 390), ('pt-BR', 320), ('es', 1024)):
                change_locale(page, locale, campaign)
                page.set_viewport_size({'width': width, 'height': 900 if width >= 1000 else 844})
                page.reload(); wait_ready(page)
                builder_tool(page, 'floor')
                builder_workspace(page)
                page.locator('[data-builder-role=floor]').click()
                collection = page.locator('[data-builder-collection-filter]')
                expect(collection).to_be_visible()
                collection.select_option('Stone collection')
                expect(page.locator(f'[data-builder-assets] [data-asset-id="{stone}"]')).to_be_visible()
                metrics = page.locator('[data-map-builder]').evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, width, metrics)
                assert metrics['scrollWidth'] <= metrics['viewport'] + 1, metrics
                toolbar = collection.locator('..').locator('..').bounding_box()
                bounds = collection.bounding_box()
                assert bounds['x'] >= toolbar['x'] and bounds['x'] + bounds['width'] <= toolbar['x'] + toolbar['width'] + 1
                page.screenshot(path=str(output / f'custom-layers-library-{locale}-{width}.png'))
                builder_sidebar(page, 'layers')
                page.locator('.map-builder__sidebar-content').evaluate('el=>el.scrollTop=0')
                expect(page.locator('[data-builder-layer-contents] > summary').first).to_have_text({
                    'en': 'Layer contents', 'pt-BR': 'Conteúdo da camada', 'es': 'Contenido de la capa'}[locale])
                page.screenshot(path=str(output / f'custom-layers-panel-{locale}-{width}.png'))
                details = contents(base_layer)
                details.locator('summary').scroll_into_view_if_needed()
                metrics = page.locator('[data-map-builder]').evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, width, metrics)
                page.screenshot(path=str(output / f'custom-layers-contents-{locale}-{width}.png'))
                records.append({'case': 'responsive-library-collection-and-mixed-layer-contents', 'locale': locale, 'width': width})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close(); browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Synthetic texture PNGs and native effect presets in a disposable campaign.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
