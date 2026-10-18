"""Exercise refined floor painting and layers using an isolated synthetic map.

Uses real controls, saved projects and generated native objects. The shared
fixture owns its database, media, runtime caches and browser diagnostics.
"""
from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import set_name, synthetic_texture, upload_asset, wait_ready


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

        def point(x, y):
            return page.locator('[data-builder-canvas]').evaluate("""(canvas, point) => {
              const p = new DOMPoint(...point).matrixTransform(canvas.getScreenCTM()); return [p.x,p.y];
            }""", [x, y])

        def click(x, y, modifiers=None):
            page.mouse.move(*point(x, y))
            for key in modifiers or []:
                page.keyboard.down(key)
            page.mouse.click(*point(x, y))
            for key in reversed(modifiers or []):
                page.keyboard.up(key)

        def control(selector, value):
            element = page.locator(selector)
            if element.evaluate('el=>el.tagName') == 'SELECT':
                element.select_option(str(value))
            else:
                element.fill(str(value)); element.dispatch_event('change')

        def floor_tool(mode='brush', operation='paint', material=None):
            builder_tool(page, 'floor')
            control('[data-builder-paint-mode]', mode)
            control('[data-builder-paint-operation]', operation)
            if material is not None:
                control('[data-builder-brush-material]', material)

        def use_layer(identifier):
            control('[data-builder-active-layer-select]', identifier)

        def saved_document():
            return review.save()['document']

        def undo():
            page.locator('[data-builder-undo]').click()

        def material_at(document, x, y, layer_id):
            rows = [row for row in document['floors'] if row['layerId'] == layer_id
                    and row['x'] <= x + .5 < row['x'] + row['width']
                    and row['y'] <= y + .5 < row['y'] + row['height']]
            return (rows[-1]['assetId'], rows[-1]['rotation']) if rows else None

        def floor_order(document):
            return [row['id'] for layer in document['layers'] for row in document['floors']
                    if row['layerId'] == layer['id']]

        try:
            page.goto(review.builder); wait_ready(page)
            set_name(page, 'Synthetic painting and layer refinements')
            stone = upload_asset(page, 'floor', 'Synthetic stone.png', synthetic_texture('floor'))['id']
            accent = upload_asset(page, 'floor', 'Synthetic accent.png', synthetic_texture('wall'))['id']
            lever_asset = upload_asset(page, 'decoration', 'Synthetic lever.png', synthetic_texture('door'))['id']
            source = review.save()
            document = deepcopy(source['document'])
            base_id, upper_id, effects_id = [str(uuid4()) for _ in range(3)]
            floor_id, island_id, upper_floor_id, light_id, particle_id, shader_id, door_id, lever_id = [str(uuid4()) for _ in range(8)]
            document['layers'] = [
                {'id': identifier, 'name': name, 'visible': True, 'locked': False}
                for identifier, name in [(base_id, 'Stone floor'), (upper_id, 'Accents and controls'), (effects_id, 'Native atmosphere')]]
            document['floors'] = [
                {'id': upper_floor_id, 'layerId': upper_id, 'assetId': accent, 'x': 5, 'y': 4, 'width': 2, 'height': 2, 'rotation': 0},
                {'id': floor_id, 'layerId': base_id, 'assetId': stone, 'x': 2, 'y': 2, 'width': 8, 'height': 6, 'rotation': 90},
                {'id': island_id, 'layerId': base_id, 'assetId': stone, 'x': 14, 'y': 2, 'width': 2, 'height': 2, 'rotation': 90},
            ]
            document['lights'] = [{'id': light_id, 'layerId': effects_id, 'x': 24, 'y': 5, 'brightRadius': 3,
                                   'dimRadius': 5, 'color': '#ffc977', 'intensity': .8, 'enabled': True,
                                   'animation': 'pulse', 'rotation': 35, 'angle': 225}]
            document['particles'] = [{'id': particle_id, 'layerId': effects_id, 'kind': 'smoke', 'x': 28, 'y': 6,
                                      'scale': 2, 'density': .25, 'color': '#aabbee', 'enabled': True,
                                      'rotation': 15, 'light_response': .3, 'light_emission': .2}]
            document['shaders'] = [{'id': shader_id, 'layerId': effects_id, 'name': 'Synthetic aura', 'x': 30, 'y': 10,
                                    'source': 'gravewright-preset://orb-1/v1', 'radius': 3, 'scale': 1,
                                    'intensity': .8, 'opacity': .65, 'speed': 1, 'color': '#8fb6ff', 'rotation': 20,
                                    'blend_mode': 'add', 'enabled': True, 'light_response': 0, 'light_emission': .3}]
            document['doors'] = [{'id': door_id, 'layerId': upper_id, 'assetId': None,
                                  'x1': 22, 'y1': 12, 'x2': 24, 'y2': 12, 'thickness': .2, 'state': 'closed',
                                  'blueprint': {'version': 2, 'kind': 'door', 'states': {
                                      state: {'appearance': 'inherit'} for state in ('open', 'closed', 'locked')},
                                      'graphs': {'enter:open': {'nodes': [
                                          {'id': 'event', 'type': 'event', 'event': 'enter:open', 'x': 0, 'y': 0},
                                          {'id': 'light', 'type': 'light', 'targetId': light_id, 'enabled': True, 'x': 300, 'y': 0},
                                          {'id': 'lever', 'type': 'reference', 'targetId': lever_id, 'x': 300, 'y': 200},
                                      ], 'edges': [{'from': 'event', 'output': 'next', 'to': 'light', 'kind': 'execution'}]}}}}]
            document['decorations'] = [{'id': lever_id, 'layerId': upper_id, 'assetId': lever_asset,
                                        'x': 25, 'y': 12, 'width': 1, 'height': 1, 'rotation': 0, 'lever': {'state': 'off'}}]
            next(row for row in document['assets'] if row['assetId'] == stone)['family'] = 'Synthetic stone family'
            project = review.store(str(uuid4()), 0, seed['folder'], document)
            original = deepcopy(project['document'])
            page.goto(review.builder + '?project=' + project['id']); wait_ready(page)
            use_layer(base_id)

            floor_tool(material=accent)
            control('[data-builder-brush-shape]', 'circle')
            control('[data-builder-brush=floorSize]', 4)
            page.locator('[data-builder-brush-adjust="1"]').click()
            expect(page.locator('[data-builder-brush=floorSize]')).to_have_value('5')
            page.locator('[data-builder-brush-adjust="-1"]').click()
            expect(page.locator('[data-builder-brush=floorSize]')).to_have_value('4')
            page.locator('[data-builder-brush-adjust="1"]').click()
            page.locator('[data-builder-viewport]').focus()
            page.keyboard.press(']'); expect(page.locator('[data-builder-brush=floorSize]')).to_have_value('6')
            page.keyboard.press('['); expect(page.locator('[data-builder-brush=floorSize]')).to_have_value('5')
            page.mouse.move(*point(20.5, 22.5))
            cursor = page.locator('[data-builder-brush-cursor]')
            expect(cursor).to_have_count(1)
            assert cursor.get_attribute('d').count('M') == 21, cursor.get_attribute('d')
            click(20.5, 22.5)
            painted = saved_document()
            assert material_at(painted, 20, 22, base_id) == (accent, 0)
            assert material_at(painted, 18, 20, base_id) is None
            assert sum(row['width'] * row['height'] for row in painted['floors']) == 77
            undo(); assert saved_document() == original
            records.append({'case': 'round-brush-cursor-size-buttons-and-bracket-shortcuts-paint-round-footprint'})

            floor_tool('rectangle', 'erase')
            review.stroke((3, 3), (7, 6))
            erased = saved_document()
            assert material_at(erased, 3, 3, base_id) is None
            assert next(row for row in erased['floors'] if row['id'] == upper_floor_id) == original['floors'][0]
            assert sum(row['width'] * row['height'] for row in erased['floors'] if row['layerId'] == base_id) == 40
            undo(); assert saved_document() == original
            records.append({'case': 'area-erasure-fragments-large-floor-preserves-other-layer-and-one-undo-restores'})

            floor_tool('fill', 'paint', accent)
            # The final material cell borders empty cells on its right/bottom.
            # Grid snapping must not round this raw bucket seed into that region.
            click(9.75, 7.75)
            filled = saved_document()
            assert material_at(filled, 2, 2, base_id) == (accent, 0)
            assert material_at(filled, 9, 7, base_id) == (accent, 0)
            assert material_at(filled, 14, 2, base_id) == (stone, 90)
            assert material_at(filled, 10, 7, base_id) is None
            undo(); assert saved_document() == original
            records.append({'case': 'bucket-fill-replaces-only-contiguous-material-not-disconnected-island-or-empty-area'})

            for trigger in ('button', 'shortcut', 'alt'):
                floor_tool('rectangle', 'erase', accent)
                control('[data-builder-brush=rotation]', 0)
                if trigger == 'button':
                    page.locator('[data-builder-sample-material]').click()
                elif trigger == 'shortcut':
                    page.locator('[data-builder-viewport]').focus(); page.keyboard.press('i')
                click(3.5, 3.5, ['Alt'] if trigger == 'alt' else None)
                expect(page.locator('[data-builder-brush-material]')).to_have_value(stone)
                expect(page.locator('[data-builder-brush=rotation]')).to_have_value('90')
                expect(page.locator('[data-builder-paint-operation]')).to_have_value('paint')
                expect(page.locator('[data-builder-paint-mode]')).to_have_value('brush')
                expect(page.locator('[data-builder-sample-material]')).to_have_attribute('aria-pressed', 'false')
            assert saved_document() == original
            records.append({'case': 'sample-button-I-and-alt-click-select-concrete-family-image-and-saved-rotation'})

            floor_tool('polygon', 'paint', accent)
            for x, y in [(15, 16), (19, 16), (19, 19)]:
                click(x, y)
            expect(page.locator('[data-builder-polygon-cancel]')).to_be_enabled()
            page.locator('[data-builder-polygon-cancel]').press('Enter')
            assert saved_document() == original
            for x, y in [(15, 16), (19, 16), (19, 19)]:
                click(x, y)
            page.locator('[data-builder-polygon-finish]').click()
            polygon = saved_document()
            assert material_at(polygon, 18, 16, base_id) == (accent, 90)
            assert material_at(polygon, 15, 18, base_id) is None
            undo(); assert saved_document() == original
            records.append({'case': 'polygon-visible-cancel-and-finish-controls-cancel-or-commit-one-edit'})

            builder_sidebar(page, 'layers')
            assert page.locator('[data-builder-project-layer]').evaluate_all('rows=>rows.map(row=>row.dataset.builderProjectLayer)') == [effects_id, upper_id, base_id]
            use_layer(effects_id)
            expect(page.locator(f'[data-builder-project-layer="{effects_id}"]')).to_have_attribute('data-active', 'true')
            expect(page.locator('[data-builder-active-layer-select]')).to_have_value(effects_id)
            page.locator(f'[data-builder-layer-select="{base_id}"]').click()
            expect(page.locator(f'[data-builder-layer-transfer="{upper_id}"]')).to_be_enabled()
            page.locator(f'[data-builder-layer-transfer="{upper_id}"]').click()
            moved = saved_document()
            assert all(row['layerId'] == upper_id for row in moved['floors'])
            assert moved['lights'] == original['lights'] and moved['doors'] == original['doors']
            undo(); assert saved_document() == original
            records.append({'case': 'highest-first-layer-list-toolbar-active-layer-select-contents-and-move-here'})

            builder_sidebar(page, 'layers')
            native_canvas = page.locator('[data-builder-native-preview] canvas')
            expect(native_canvas).to_have_count(1)
            page.locator(f'[data-builder-layer-solo="{base_id}"]').click()
            expect(page.locator(f'[data-builder-floors] [data-object-id="{upper_floor_id}"]')).to_be_hidden()
            expect(page.locator(f'[data-builder-lights] [data-object-id="{light_id}"]')).to_be_hidden()
            expect(native_canvas).to_have_count(0)
            assert saved_document() == original
            page.locator('[data-builder-preview]').click()
            expect(native_canvas).to_have_count(1)
            expect(page.locator('[data-builder-active-layer-select]')).to_be_disabled()
            expect(page.locator(f'[data-builder-layer-select="{base_id}"]')).to_be_disabled()
            assert saved_document() == original
            page.locator('[data-builder-preview]').click()
            builder_sidebar(page, 'layers')
            page.locator('[data-builder-layer-name]').fill('Synthetic isolated addition')
            page.locator('[data-builder-layer-add]').click()
            new_layer = page.locator('[data-builder-active-layer-select]').input_value()
            assert new_layer not in (base_id, upper_id, effects_id)
            expect(page.locator(f'[data-builder-layer-solo="{new_layer}"]')).to_have_attribute('aria-pressed', 'true')
            expect(native_canvas).to_have_count(0)
            floor_tool('brush', 'paint', accent)
            click(18.5, 22.5)
            added = saved_document()
            assert any(row['layerId'] == new_layer for row in added['floors'])
            undo()
            assert not any(row['layerId'] == new_layer for row in saved_document()['floors'])
            undo(); assert saved_document() == original
            expect(native_canvas).to_have_count(1)
            records.append({'case': 'solo-hides-other-renderers-without-visibility-edits-preview-is-readonly-and-added-layer-retargets-solo'})

            use_layer(upper_id)
            for attribute, value in [('locked', True), ('visible', False)]:
                builder_sidebar(page, 'layers')
                field = page.locator(f'[data-builder-layer-{attribute}="{upper_id}"]')
                field.set_checked(value)
                expect(page.locator(f'[data-builder-layer-select="{upper_id}"]')).to_be_disabled()
                expect(page.locator(f'[data-builder-layer-merge="{upper_id}"]')).to_be_disabled()
                guarded = saved_document()
                floor_tool(material=accent)
                page.mouse.move(*point(18.5, 22.5))
                expect(page.locator('[data-builder-brush-cursor]')).to_have_count(0)
                click(18.5, 22.5)
                assert saved_document() == guarded
                undo(); assert saved_document() == original
            records.append({'case': 'locked-and-hidden-layer-guards-disable-content-actions-cursor-and-floor-painting'})

            builder_sidebar(page, 'layers')
            page.locator(f'[data-builder-layer-merge="{effects_id}"]').click()
            first_merge = saved_document()
            for kind in ('lights', 'particles', 'shaders'):
                assert first_merge[kind] == [{**row, 'layerId': upper_id} for row in original[kind]]
            page.locator(f'[data-builder-layer-merge="{upper_id}"]').click()
            merged = saved_document()
            assert len(merged['layers']) == 1 and floor_order(merged) == floor_order(original)
            for kind in ('floors', 'doors', 'decorations', 'lights', 'particles', 'shaders'):
                assert {row['id'] for row in merged[kind]} == {row['id'] for row in original[kind]}
                for row in merged[kind]:
                    before = next(item for item in original[kind] if item['id'] == row['id'])
                    assert row == {**before, 'layerId': base_id}, (kind, row, before)
            undo(); assert saved_document() == first_merge
            undo(); assert saved_document() == original
            records.append({'case': 'merge-down-preserves-paint-order-native-identities-and-blueprint-targets-each-merge-is-one-undo'})

            layouts = []
            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign); page.reload(); wait_ready(page)
                for width in (1440, 390):
                    page.set_viewport_size({'width': width, 'height': 900 if width > 500 else 844})
                    floor_tool('brush', 'paint', stone)
                    control('[data-builder-brush-shape]', 'circle')
                    builder_sidebar(page, 'layers')
                    page.locator('.map-builder__sidebar-content').evaluate('panel=>panel.scrollTop=0')
                    metrics = page.locator('[data-map-builder]').evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], (locale, width, metrics)
                    assert metrics['scrollWidth'] <= metrics['viewport'] + 1, (locale, width, metrics)
                    toolbar_status = page.locator('[data-builder-active-layer-status]').evaluate("""status=>{
                      const text=status.getBoundingClientRect(),bar=status.closest('.map-builder__toolbars').getBoundingClientRect();
                      return {top:text.top,bottom:text.bottom,barTop:bar.top,barBottom:bar.bottom,
                        contentWidth:status.scrollWidth,visibleWidth:status.clientWidth};
                    }""")
                    assert toolbar_status['top'] >= toolbar_status['barTop'] and toolbar_status['bottom'] <= toolbar_status['barBottom'], (locale, width, toolbar_status)
                    assert toolbar_status['contentWidth'] <= toolbar_status['visibleWidth'] + 1, (locale, width, toolbar_status)
                    page.screenshot(path=str(output / f'builder-refinements-{locale}-{width}.png'))
                    layouts.append({'locale': locale, 'width': width, **metrics, 'toolbarStatus': toolbar_status})
                    page.locator('[data-builder-project-layer]').first.scroll_into_view_if_needed()
                    expect(page.locator('[data-builder-layer-merge]').first).to_be_visible()
                    actions_metrics = page.locator('[data-map-builder]').evaluate(MEASURE)
                    assert not actions_metrics['tiny'] and not actions_metrics['overflow'], (locale, width, actions_metrics)
                    page.screenshot(path=str(output / f'builder-layer-actions-{locale}-{width}.png'))
                    builder_workspace(page)
                    page.screenshot(path=str(output / f'builder-painting-{locale}-{width}.png'))
            records.append({'case': 'EN-PT-ES-painting-and-layer-layouts-at-desktop-and-mobile', 'layouts': layouts})

            page.set_viewport_size({'width': 1440, 'height': 900})
            change_locale(page, 'en', campaign); page.reload(); wait_ready(page)
            assert saved_document() == original
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            current = review.project(project['id'])
            scene = page.request.get(f"/api/maps/{current['sceneId']}/state").json()
            native_light, = scene['lights']; native_particle, = scene['particles']; native_shader, = scene['shaders']
            cell = original['cellSize']
            assert (native_light['x'], native_light['y'], native_light['animation'], native_light['angle']) == (24 * cell, 5 * cell, 'pulse', 225)
            assert (native_particle['kind'], native_particle['density'], native_particle['x']) == ('smoke', .25, 28 * cell)
            assert native_shader['source'] == original['shaders'][0]['source'] and native_shader['radius'] == 3
            native_door = next(row for row in scene['walls'] if row['kind'] == 'door')
            native_lever = next(row for row in scene['images'] if 'lever' in row)
            nodes = native_door['blueprint']['graphs']['enter:open']['nodes']
            assert next(row for row in nodes if row['type'] == 'light')['targetId'] == native_light['id']
            assert next(row for row in nodes if row['type'] == 'reference')['targetId'] == native_lever['id']
            assert current['document'] == original
            records.append({'case': 'save-reopen-generate-preserves-native-settings-and-resolves-original-blueprint-UUID-targets'})

            page.evaluate("""args=>gravewrightRealtime.mapCommand('objects', {
              mapId:args.scene,area:'lights',action:'update',data:{light_id:args.light,enabled:false}})""",
                          {'scene': current['sceneId'], 'light': native_light['id']})
            page.goto(review.builder + '?project=' + project['id']); wait_ready(page)
            builder_sidebar(page, 'layers')
            page.locator(f'[data-builder-layer-merge="{effects_id}"]').click()
            page.locator(f'[data-builder-layer-merge="{upper_id}"]').click()
            merged_source = saved_document()
            assert len(merged_source['layers']) == 1
            builder_sidebar(page, 'review')
            with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                page.locator('[data-builder-review-update]').click()
            assert updated.value.ok, updated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            final = page.request.get(f"/api/maps/{current['sceneId']}/state").json()
            for kind in ('lights', 'particles', 'shaders', 'images', 'walls'):
                assert {row['id'] for row in final[kind]} == {row['id'] for row in scene[kind]}, kind
            assert final['lights'][0]['enabled'] is False
            for kind, keys in [('particles', ('kind', 'density', 'scale', 'x', 'y')),
                               ('shaders', ('source', 'radius', 'opacity', 'x', 'y'))]:
                assert {key: final[kind][0][key] for key in keys} == {key: scene[kind][0][key] for key in keys}
            updated_door = next(row for row in final['walls'] if row['id'] == native_door['id'])
            assert updated_door['blueprint'] == native_door['blueprint']
            updated_lever = next(row for row in final['images'] if row['id'] == native_lever['id'])
            assert updated_lever['lever'] == native_lever['lever']
            assert review.project(project['id'])['document'] == merged_source
            records.append({'case': 'merging-and-updating-generated-scene-keeps-native-IDs-blueprint-targets-and-live-light-state'})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close(); browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Generated texture PNGs and native host effect presets; isolated synthetic campaign only.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
