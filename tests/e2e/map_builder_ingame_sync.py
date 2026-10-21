"""Keep linked MapBuilder projects aligned with edits made on the native table.

Uses the normal editor, HTTP project API and native WebSocket object commands
against synthetic artwork and a disposable campaign. No operator data is read.
"""
from __future__ import annotations

from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import close_panel, upload_asset, wait_ready


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    cases, errors, dialogs, syncs, writes = [], [], [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        review = BuilderReview(page, campaign)
        game_page = None

        def observe(target):
            target.on('pageerror', lambda error: errors.append(str(error)))
            target.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
            target.on('response', lambda response: syncs.append(response.status)
                      if response.request.method == 'POST' and response.url.endswith('/sync') else None)

        observe(page)

        def record_write(request):
            if request.method == 'POST' and '/map-builder/projects/' in request.url:
                if request.url.rsplit('/', 1)[-1] not in ('sync', 'generate', 'update'):
                    writes.append(request.post_data_json)

        page.on('request', record_write)
        autosave_route = '**/gravewright_maps/builder/autosave.js*'
        deferred_modules = []

        def defer_autosave(route):
            # Keep the real persistence queue, receipts and merger. Only extend
            # its editing debounce in this browser so pending drafts cannot
            # race the assertions or be mistaken for acknowledged saves.
            response = route.fetch()
            source = response.text()
            assert 'delay = 700' in source
            deferred_modules.append(route.request.url)
            route.fulfill(response=response, body=source.replace('delay = 700', 'delay = 60_000', 1))

        def game(target=page):
            target.wait_for_url(f'{base}/game/{campaign}')
            target.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(target.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def command(area, action, data, target=page):
            return target.evaluate('''a=>gravewrightRealtime.mapCommand('objects',{
              mapId:a.scene,area:a.area,action:a.action,data:a.data})''',
                {'scene': scene, 'area': area, 'action': action, 'data': data})

        def state():
            response = page.request.get(f'/api/maps/{scene}/state')
            assert response.ok, response.text()
            return response.json()

        def reopen():
            page.goto(review.builder + '?project=' + project['id'])
            wait_ready(page)
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved', timeout=20_000)
            return review.project(project['id'])

        def update():
            close_panel(page)
            with page.expect_response(lambda response: response.request.method == 'POST'
                                      and response.url.endswith('/update')) as response:
                page.locator('[data-builder-generate]').click()
            assert response.value.ok, response.value.text()
            game()
            updated = review.project(project['id'])
            assert updated['sceneId'] == scene
            return updated

        try:
            page.goto(review.builder)
            wait_ready(page)
            door_asset = upload_asset(page, 'door', 'Synthetic synchronizing door.png', harness.artwork('#a87331'))['id']
            image_asset = upload_asset(page, 'decoration', 'Synthetic movable decoration.png', harness.artwork('#396ca5'))['id']
            document = page.evaluate("async()=> (await import('/static/gravewright_maps/builder/model.js')).newDocument('Synthetic in-game synchronization')")
            layer = document['layers'][0]['id']
            door_source, image_source, light_source = [str(uuid4()) for _ in range(3)]
            document['assets'] = [{'assetId': door_asset, 'role': 'door'}, {'assetId': image_asset, 'role': 'decoration'}]
            document['doors'] = [{'id': door_source, 'layerId': layer, 'assetId': door_asset,
                'x1': 5, 'y1': 5, 'x2': 7, 'y2': 5, 'thickness': .2, 'state': 'closed', 'name': 'Authored door'}]
            document['decorations'] = [{'id': image_source, 'layerId': layer, 'assetId': image_asset,
                'x': 12, 'y': 7, 'width': 2, 'height': 1, 'rotation': 0, 'name': 'Authored decoration'}]
            document['lights'] = [{'id': light_source, 'layerId': layer, 'x': 10, 'y': 12,
                'brightRadius': 2, 'dimRadius': 4, 'color': '#ffd8a8', 'intensity': .8,
                'enabled': True, 'rotation': 0, 'angle': 360, 'animation': 'none'}]
            project = review.store(str(uuid4()), 0, seed['folder'], document)
            reopen()
            close_panel(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            game()
            project = review.project(project['id'])
            scene = project['sceneId']
            native = state()
            door, image, light = native['walls'][0], native['images'][0], native['lights'][0]
            cell = document['cellSize']
            command('walls', 'door', {'wall_id': door['id'], 'door_state': 'open'})
            command('walls', 'update', {'wall_id': door['id'], 'x1': 6 * cell, 'x2': 8 * cell,
                'y1': 6 * cell, 'y2': 6 * cell, 'rotationAnchor': 'end', 'thickness': .4 * cell,
                'name': 'Door changed during the game'})
            command('images', 'update', {'placement_id': image['id'], 'x': 15 * cell,
                'y': 9 * cell, 'scale': image['scale'] * 1.5, 'rotation': 90, 'name': 'Moved during the game'})
            command('lights', 'update', {'light_id': light['id'], 'x': 11 * cell, 'y': 13 * cell,
                'dim_radius': 8, 'color': '#66aacc', 'enabled': False})
            manual = command('walls', 'create', {'x1': 23 * cell, 'y1': 15 * cell,
                'x2': 25 * cell, 'y2': 15 * cell, 'name': 'External manual wall'})['wall']

            project = reopen()
            synced = project['document']
            authored = synced['doors'][0]
            assert [authored[key] for key in ('x1', 'x2', 'y1', 'y2', 'thickness')] == [6, 8, 6, 6, .4], authored
            assert authored['rotationAnchor'] == 'end' and authored['name'] == 'Door changed during the game'
            assert authored['state'] == 'closed', authored
            assert synced['decorations'][0]['rotation'] == 90
            assert synced['decorations'][0]['name'] == 'Moved during the game'
            assert synced['lights'][0]['dimRadius'] == 8 and synced['lights'][0]['enabled'] is True
            assert not synced['walls'], 'The external native wall must remain outside generated ownership.'
            builder_tool(page, 'select')
            builder_workspace(page)
            page.locator(f'[data-object-kind=doors][data-object-id="{door_source}"]').click()
            builder_sidebar(page, 'selection')
            expect(page.locator('[data-builder-property=rotationAnchor]')).to_have_value('end')
            page.screenshot(path=str(output / 'imported-native-door-properties.png'))
            cases.append({'case': 'reopening-imports-native-door-image-and-light-edits-and-keeps-authored-play-defaults'})

            project = update()
            current = state()
            assert next(row for row in current['walls'] if row['id'] == door['id'])['door_state'] == 'open'
            assert next(row for row in current['walls'] if row['id'] == manual['id']) == manual
            assert next(row for row in current['images'] if row['id'] == image['id'])['rotation'] == 90
            assert next(row for row in current['lights'] if row['id'] == light['id'])['enabled'] is False
            cases.append({'case': 'updating-keeps-the-same-scene-native-identities-live-state-and-manual-content'})

            # An already open builder must also refresh before Update. Native
            # commands execute in a background game tab, so no focus event can
            # import the change before the explicit Update path is exercised.
            game_page = context.new_page()
            observe(game_page)
            game_page.goto(f'/game/{campaign}')
            game(game_page)
            page.bring_to_front()
            project = reopen()
            page.locator('[data-builder-quick-name]').fill('Independent authored project rename')
            page.locator('[data-builder-quick-name]').press('Tab')
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved', timeout=20_000)
            command('walls', 'update', {'wall_id': door['id'], 'rotationAnchor': 'start',
                'name': 'Second native edit while builder is open'}, game_page)
            project = update()
            assert project['document']['name'] == 'Independent authored project rename'
            assert project['document']['doors'][0]['rotationAnchor'] == 'start'
            assert project['document']['doors'][0]['name'] == 'Second native edit while builder is open'
            assert next(row for row in state()['walls'] if row['id'] == door['id'])['rotationAnchor'] == 'start'
            cases.append({'case': 'update-reconciles-a-background-game-edit-and-retains-an-independent-builder-edit'})

            page.route(autosave_route, defer_autosave)
            project = reopen()
            previous_name = project['document']['name']
            before_writes = len(writes)
            page.locator('[data-builder-quick-name]').fill('Unsaved draft retained through focus sync')
            page.locator('[data-builder-quick-name]').press('Tab')
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'unsaved')
            assert review.draft(project['id'])['name'] == 'Unsaved draft retained through focus sync'
            assert review.project(project['id'])['document']['name'] == previous_name
            command('walls', 'update', {'wall_id': door['id'], 'rotationAnchor': 'end',
                'name': 'Game edit imported on focus'}, game_page)
            with page.expect_response(lambda response: response.request.method == 'POST'
                                      and response.url.endswith('/sync')) as focused:
                page.evaluate("dispatchEvent(new Event('focus'))")
            assert focused.value.ok, focused.value.text()
            expect(page.locator('[data-map-builder]')).to_have_attribute('aria-busy', 'false')
            draft = review.draft(project['id'])
            assert draft['name'] == 'Unsaved draft retained through focus sync'
            assert draft['doors'][0]['rotationAnchor'] == 'end'
            assert draft['doors'][0]['name'] == 'Game edit imported on focus'
            assert review.project(project['id'])['document']['name'] == previous_name
            assert len(writes) == before_writes, 'The draft must remain unposted during the focus merge.'
            page.locator('[data-builder-undo]').click()
            expect(page.locator('[data-builder-quick-name]')).to_have_value(previous_name)
            builder_tool(page, 'select')
            builder_workspace(page)
            page.locator(f'[data-object-kind=doors][data-object-id="{door_source}"]').click()
            builder_sidebar(page, 'selection')
            expect(page.locator('[data-builder-property=rotationAnchor]')).to_have_value('end')
            expect(page.locator('[data-builder-property=name]')).to_have_value('Game edit imported on focus')
            page.locator('[data-builder-redo]').click()
            expect(page.locator('[data-builder-quick-name]')).to_have_value('Unsaved draft retained through focus sync')
            draft = review.draft(project['id'])
            assert draft['doors'][0]['rotationAnchor'] == 'end'
            assert draft['doors'][0]['name'] == 'Game edit imported on focus'
            page.screenshot(path=str(output / 'focus-sync-retains-draft-and-rebased-history.png'))
            project = review.save()
            assert project['document']['name'] == 'Unsaved draft retained through focus sync'
            assert project['document']['doors'][0]['rotationAnchor'] == 'end'
            page.unroute(autosave_route, defer_autosave)
            project = update()
            cases.append({'case': 'focus-sync-merges-an-unsaved-disjoint-draft-and-undo-redo-keep-imported-game-fields'})

            command('images', 'delete', {'placement_id': image['id']})
            project = reopen()
            assert project['document']['decorations'] == []
            expect(page.locator(f'[data-object-kind=decorations][data-object-id="{image_source}"]')).to_have_count(0)
            project = update()
            current = state()
            assert all(row['id'] != image['id'] for row in current['images'])
            assert next(row for row in current['walls'] if row['id'] == manual['id']) == manual
            cases.append({'case': 'native-deletion-removes-the-generated-source-and-never-recreates-it'})

            change_locale(page, 'pt-BR', campaign)
            page.set_viewport_size({'width': 390, 'height': 844})
            project = reopen()
            expect(page.locator('html')).to_have_attribute('lang', 'pt-BR')
            assert project['document']['doors'][0]['rotationAnchor'] == 'end'
            assert not page.locator('[data-builder-notice]').is_visible()
            metrics = page.locator('[data-map-builder]').evaluate(MEASURE)
            assert not metrics['tiny'] and not metrics['overflow'], metrics
            page.screenshot(path=str(output / 'synchronized-project-pt-BR-mobile.png'))
            cases.append({'case': 'synchronized-project-reopens-in-portuguese-on-a-small-viewport', 'metrics': metrics})

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.route(autosave_route, defer_autosave)
            project = reopen()
            builder_tool(page, 'select')
            builder_workspace(page)
            page.locator(f'[data-object-kind=doors][data-object-id="{door_source}"]').click()
            builder_sidebar(page, 'selection')
            before_writes = len(writes)
            page.locator('[data-builder-property=rotationAnchor]').select_option('center')
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'unsaved')
            assert review.draft(project['id'])['doors'][0]['rotationAnchor'] == 'center'
            command('walls', 'update', {'wall_id': door['id'], 'rotationAnchor': 'start'}, game_page)
            with page.expect_response(lambda response: response.request.method == 'POST'
                                      and response.url.endswith('/sync')) as conflicted:
                page.evaluate("dispatchEvent(new Event('focus'))")
            assert conflicted.value.ok, conflicted.value.text()
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'conflict')
            expect(page.locator('[data-builder-property=rotationAnchor]')).to_have_value('center')
            assert review.draft(project['id'])['doors'][0]['rotationAnchor'] == 'center'
            assert review.project(project['id'])['document']['doors'][0]['rotationAnchor'] == 'start'
            assert len(writes) == before_writes
            notice = page.locator('[data-builder-notice]')
            expect(notice).to_contain_text('Your edits are kept in this tab.')
            expect(notice.get_by_role('button', name='Reload saved project', exact=True)).to_be_visible()
            expect(notice.get_by_role('button', name='Save a copy', exact=True)).to_be_visible()
            page.screenshot(path=str(output / 'same-field-draft-conflict-retains-local-anchor.png'))
            page.unroute(autosave_route, defer_autosave)
            cases.append({'case': 'same-field-focus-conflict-retains-the-local-draft-and-offers-reload-or-copy'})
            assert len(deferred_modules) == 2, deferred_modules
            assert syncs and all(status == 200 for status in syncs), syncs
            assert not errors, errors
            assert not dialogs, dialogs
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close()
            browser.close()
    return {'passed': True, 'cases': cases, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'syncStatuses': syncs, 'assets': 'Generated solid-color PNG artwork.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
