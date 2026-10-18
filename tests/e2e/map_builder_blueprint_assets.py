"""Check state-only door image classification and native blueprint copies."""
from __future__ import annotations

import map_builder_blueprints as harness
from map_builder import builder_library_settings, builder_tool
from map_builder_reference import set_name, upload_asset, wait_ready


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    records, errors, dialogs = [], [], []
    campaign = seed['campaign']
    api = f'/api/containers/{campaign}/map-builder'
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))

        def native_dialog(dialog):
            dialogs.append(dialog.message)
            dialog.dismiss()

        page.on('dialog', native_dialog)
        try:
            page.goto(f'/game/{campaign}/map-builder')
            wait_ready(page)
            set_name(page, 'Synthetic state-only door artwork')
            asset = upload_asset(page, 'door', 'State-only synthetic image.png', harness.artwork('#2974d9'))['id']
            builder_tool(page, 'door')
            page.locator('[data-builder-brush-material]').select_option('')
            field = page.locator('[data-builder-brush=thickness]')
            field.fill('.6')
            field.press('Tab')
            points = page.locator('[data-builder-canvas]').evaluate("""canvas => [[8,6],[10,6]].map(([x,y]) => {
              const point = new DOMPoint(x,y).matrixTransform(canvas.getScreenCTM());
              return {x:point.x,y:point.y};
            })""")
            page.mouse.move(points[0]['x'], points[0]['y'])
            page.mouse.down()
            page.mouse.move(points[1]['x'], points[1]['y'], steps=4)
            page.mouse.up()
            page.locator('[data-builder-doors] [data-object-id]').dblclick()
            modal = page.locator('[data-smart-object-modal]')
            expect(modal).to_be_visible()
            modal.locator('[data-blueprint-state=open]').click()
            modal.locator('[data-blueprint-appearance]').select_option('asset')
            modal.locator('[data-blueprint-asset]').select_option(asset)
            modal.locator('[data-blueprint-add]').click()
            modal.locator('[data-blueprint-node-picker] [data-blueprint-pick-type=sound]').click()
            sound = modal.locator('[data-blueprint-type=sound]')
            sound_id = sound.get_attribute('data-blueprint-node')
            sound.locator('[data-blueprint-param=trackId]').select_option(seed['track'])
            sound.locator('[data-blueprint-param=volume]').fill('.333')
            sound.locator('[data-blueprint-param=volume]').press('Tab')
            modal.locator('[data-blueprint-instance][data-blueprint-event-source] [data-blueprint-output=next]').click()
            modal.locator(f'[data-blueprint-input="{sound_id}"]').click()
            modal.locator('[data-blueprint-save]').click()
            expect(modal).to_have_count(0)
            page.locator('[data-builder-doors] [data-object-id]').dblclick()
            modal = page.locator('[data-smart-object-modal]')
            expect(modal).to_be_visible()
            modal.locator('[data-blueprint-state=open]').click()
            expect(modal.locator('[data-blueprint-param=volume]')).to_have_value('0.333')
            modal.locator('[data-blueprint-close]').click()
            records.append({'case': 'sound-volume-with-three-decimals-saves-and-reopens'})

            def stroke(start, end):
                points = page.locator('[data-builder-canvas]').evaluate("""(canvas, points) => points.map(([x,y]) => {
                  const point = new DOMPoint(x,y).matrixTransform(canvas.getScreenCTM());
                  return {x:point.x,y:point.y};
                })""", [start, end])
                page.mouse.move(points[0]['x'], points[0]['y'])
                page.mouse.down()
                page.mouse.move(points[1]['x'], points[1]['y'], steps=8)
                page.mouse.up()

            # Distinguishing a door click from a drag must keep the builder's
            # brushes usable at the door's endpoints and over its artwork.
            builder_tool(page, 'wall')
            stroke((10, 6), (16, 6))
            expect(page.locator('[data-builder-walls] [data-object-id]')).to_have_count(1)
            expect(page.locator('[data-smart-object-modal]')).to_have_count(0)
            builder_tool(page, 'floor')
            page.locator('[data-builder-brush-material]').select_option('')
            stroke((9.15, 6.1), (12.15, 8.1))
            expect(page.locator('[data-smart-object-modal]')).to_have_count(0)

            def save():
                if page.locator('[data-map-builder]').get_attribute('data-save-state') == 'saved':
                    project = page.evaluate("new URL(location.href).searchParams.get('project')")
                    response = page.request.get(api + '/projects/' + project)
                else:
                    with page.expect_response(lambda response: response.request.method == 'POST'
                                              and '/map-builder/projects/' in response.url
                                              and not response.url.endswith(('/generate', '/update'))) as saved:
                        page.locator('[data-builder-save]').click()
                    response = saved.value
                assert response.ok, response.text()
                return response.json()['project']

            initial = save()
            document = initial['document']
            assert all(item.get('assetId') != asset for kind in ('floors', 'walls', 'doors', 'decorations')
                       for item in document[kind])
            assert document['doors'][0]['blueprint']['states']['open']['assetId'] == asset
            assert document['doors'][0]['assetId'] is None
            assert tuple(document['walls'][0][key] for key in ('x1', 'y1', 'x2', 'y2')) == (10, 6, 16, 6)
            assert any(tile['x'] == 9 and tile['y'] == 6 for tile in document['floors']), document['floors']
            assert any(tile['x'] == 12 and tile['y'] == 8 for tile in document['floors']), document['floors']
            records.append({'case': 'wall-drag-begins-at-door-endpoint-without-opening-blueprint'})
            records.append({'case': 'floor-brush-drag-begins-on-door-without-moving-or-editing-it'})

            # Modal editing must reject a new role before mutating metadata.
            page.locator(f'[data-asset-id="{asset}"]').dblclick()
            editor = page.locator('[data-builder-asset-modal]')
            editor.locator('[data-builder-import-role]').select_option('floor')
            editor.locator('[data-builder-import-submit]').click()
            expect(editor).to_be_visible()
            expect(editor.locator('[role=alert]')).to_contain_text('already used by another brush')
            page.screenshot(path=str(output / 'state-only-asset-modal-guard.png'))
            editor.locator('[data-builder-import-cancel]').click()
            assert save()['document'] == document
            records.append({'case': 'state-only-asset-cannot-change-door-to-floor-in-edit-modal'})

            # The inline library setting reaches the same ownership guard.
            page.locator(f'[data-asset-id="{asset}"]').click()
            builder_library_settings(page)
            page.locator('[data-builder-asset-role]').select_option('floor')
            expect(page.locator('[data-builder-notice]')).to_contain_text('already used by another brush')
            expect(page.locator('[data-builder-asset-role]')).to_have_value('door')
            assert save()['document'] == document
            records.append({'case': 'state-only-asset-cannot-change-door-to-floor-in-library-settings'})

            page.locator('[data-builder-dismiss]').click()
            set_name(page, 'Synthetic state-only artwork remains saveable')
            persisted = save()
            assert persisted['document']['doors'] == document['doors']
            assert persisted['document']['assets'] == document['assets']
            records.append({'case': 'blocked-reclassification-keeps-reference-and-project-still-saves'})

            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            project = page.request.get(api + '/projects/' + initial['id']).json()['project']
            scene = project['sceneId']
            state = page.request.get(f'/api/maps/{scene}/state').json()
            source = next(wall for wall in state['walls'] if wall['kind'] == 'door')
            assert source['thickness'] == .6 * document['cellSize']
            assert 'asset_id' not in source

            # Native keyboard copy uses this built production module and the
            # wall-selection paste command. Check the same path with one door.
            result = page.evaluate("""async args => {
              const {wallPayload} = await import('/static/gravewright_maps/walls/model/walls.js');
              const payload = wallPayload(args.source);
              const expected = structuredClone(payload.blueprint);
              payload.blueprint.states.closed.appearance = 'hidden';
              if (args.source.blueprint.states.closed.appearance === 'hidden') throw new Error('Copy aliases original blueprint');
              payload.blueprint = expected;
              const pasted = await gravewrightRealtime.mapCommand('objects', {mapId:args.scene,
                area:'wall-selection', action:'paste', data:{walls:[{...payload,
                  x1:payload.x1+280,x2:payload.x2+280,y1:payload.y1+70,y2:payload.y2+70,
                  door_state:args.source.door_state,discovered:args.source.discovered}]}});
              return {payload, pasted};
            }""", {'source': source, 'scene': scene})
            assert result['payload']['thickness'] == source['thickness'], result
            assert result['payload']['blueprint'] == source['blueprint'], result
            assert 'asset_id' not in result['payload']
            native = page.request.get(f'/api/maps/{scene}/state').json()
            copy, = [wall for wall in native['walls'] if wall['id'] != source['id'] and wall['kind'] == 'door']
            assert copy['thickness'] == source['thickness']
            assert copy['blueprint'] == source['blueprint']
            assert (copy['x1'], copy['y1']) == (source['x1'] + 280, source['y1'] + 70)
            assert next(wall for wall in native['walls'] if wall['id'] == source['id']) == source
            records.append({'case': 'final-native-copy-module-preserves-blueprint-only-door-thickness',
                            'thickness': copy['thickness'], 'source': source['id'], 'copy': copy['id']})
            page.screenshot(path=str(output / 'state-only-native-copy.png'))
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'One generated PNG, referenced only by an inactive door state.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
