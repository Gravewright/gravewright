"""Exercise automatic project and Smart Object persistence with real revisions.

Campaign, artwork, database, media and server are disposable. Delayed or lost
responses exercise the actual browser queue and server receipts without touching
the operator's Runner, configuration or campaigns.
"""
from __future__ import annotations

from copy import deepcopy
import json
import re
import time
from urllib.parse import urlsplit
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_playtest import post
from map_builder_reference import close_panel, upload_asset, wait_ready


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    records, errors, dialogs, writes = [], [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()

        def project_write(request):
            return request.method == 'POST' and bool(re.search(r'/map-builder/projects/[0-9a-f-]+$', urlsplit(request.url).path))

        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        page.on('request', lambda request: writes.append(deepcopy(request.post_data_json)) if project_write(request) else None)
        review = BuilderReview(page, campaign)
        routes = []

        def name(value, blur=True):
            field = page.locator('[data-builder-quick-name]')
            field.fill(value)
            if blur:
                field.press('Tab')

        def project_id():
            return page.evaluate("new URL(location.href).searchParams.get('project')")

        def persisted(predicate, identifier=None, timeout=20):
            deadline, last = time.monotonic() + timeout, None
            while time.monotonic() < deadline:
                current_id = identifier or project_id()
                if current_id:
                    response = page.request.get(review.api + '/projects/' + current_id)
                    if response.ok:
                        last = response.json()['project']
                        if predicate(last):
                            return last
                page.wait_for_timeout(100)
            raise AssertionError({'message': 'Automatic save did not reach the expected project state.', 'lastProject': last})

        def idle():
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved', timeout=20_000)

        def open_editor(identifier):
            builder_tool(page, 'select')
            builder_workspace(page)
            page.locator(f'[data-builder-decorations] [data-object-id="{identifier}"]').dblclick()
            modal = page.locator('[data-smart-object-modal]')
            expect(modal).to_be_visible()
            expect(modal.locator('[data-blueprint-save]:visible')).to_have_count(0)
            expect(modal.locator('[data-blueprint-cancel]')).to_be_visible()
            return modal

        def add_node(modal, kind):
            before = set(modal.locator('[data-blueprint-node]').evaluate_all('nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            modal.locator('[data-blueprint-add]').click()
            modal.locator(f'[data-blueprint-pick-type="{kind}"]').click()
            after = set(modal.locator('[data-blueprint-node]').evaluate_all('nodes=>nodes.map(node=>node.dataset.blueprintNode)'))
            identifier, = after - before
            return identifier

        def card(modal, identifier):
            return modal.locator(f'[data-blueprint-node="{identifier}"]')

        def connect(modal, source, target):
            modal.locator('[data-blueprint-fit]').click()
            source.click()
            card(modal, target).locator('[data-blueprint-input]').click()

        try:
            page.goto(review.builder)
            wait_ready(page)
            name('Synthetic map saved automatically', blur=False)
            initial = persisted(lambda value: value['document']['name'] == 'Synthetic map saved automatically')
            idle()
            identifier = initial['id']
            assert writes and all(value['request_id'] for value in writes)
            page.reload()
            wait_ready(page)
            expect(page.locator('[data-builder-quick-name]')).to_have_value(initial['name'])
            assert review.project(identifier)['document'] == initial['document']
            records.append({'case': 'name-edit-creates-project-without-clicking-save-and-survives-reload'})

            boot_attempts = []

            def fail_initial_library(route):
                boot_attempts.append(route.request.url)
                if len(boot_attempts) == 1:
                    route.fulfill(status=503, json={'error': 'Synthetic transient library failure'})
                else:
                    route.continue_()

            boot_pattern = '**' + review.api
            page.route(boot_pattern, fail_initial_library)
            routes.append((boot_pattern, fail_initial_library))
            writes_before_boot = len(writes)
            page.reload()
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'blocked')
            retry_boot = page.locator('[data-builder-notice]').get_by_role('button', name='Retry', exact=True)
            expect(retry_boot).to_be_visible()
            expect(page.locator('[data-builder-quick-name]')).to_be_disabled()
            expect(page.locator('[data-builder-save]')).to_be_disabled()
            assert len(writes) == writes_before_boot
            assert review.project(identifier)['document'] == initial['document']
            retry_boot.click()
            wait_ready(page)
            expect(page.locator('[data-builder-quick-name]')).to_be_enabled()
            expect(page.locator('[data-builder-quick-name]')).to_have_value(initial['name'])
            idle()
            assert len(boot_attempts) == 2 and len(writes) == writes_before_boot
            page.unroute(boot_pattern, fail_initial_library)
            routes.remove((boot_pattern, fail_initial_library))
            records.append({'case': 'transient-library-boot-failure-blocks-editing-and-retry-restores-project-without-writing-empty-data'})

            floor_asset = upload_asset(page, 'floor', 'Synthetic autosaved floor.png', harness.artwork('#a97638'))['id']
            lever_asset = upload_asset(page, 'decoration', 'Synthetic autosaved lever.png', harness.artwork('#386ba2'))['id']
            builder_tool(page, 'floor')
            page.locator('[data-builder-brush-material]').select_option(floor_asset)
            review.stroke((5, 5), (5, 5))
            painted = persisted(lambda value: len(value['document']['floors']) == 1)
            idle()
            page.locator('[data-builder-undo]').click()
            persisted(lambda value: not value['document']['floors'])
            idle()
            page.locator('[data-builder-redo]').click()
            persisted(lambda value: value['document']['floors'] == painted['document']['floors'])
            idle()
            records.append({'case': 'painting-undo-and-redo-save-automatically-and-retain-authored-history'})

            # The first response is held after the server commits. Authoring
            # continues while it is in flight, then the later snapshot follows.
            held = {}

            def delay_response(route):
                if held:
                    route.continue_()
                    return
                held.update(route=route, response=route.fetch(), payload=deepcopy(route.request.post_data_json))

            pattern = '**/map-builder/projects/*'
            page.route(pattern, delay_response)
            routes.append((pattern, delay_response))
            name('Synthetic response held while painting')
            deadline = time.monotonic() + 15
            while not held and time.monotonic() < deadline:
                page.wait_for_timeout(50)
            assert held, 'Expected one in-flight automatic write'
            expect(page.locator('[data-builder-tool=floor]')).to_be_enabled()
            points = page.locator('[data-builder-canvas]').evaluate('''(canvas,values)=>values.map(value=>{
              const point=new DOMPoint(...value).matrixTransform(canvas.getScreenCTM());return [point.x,point.y];
            })''', [[7.25, 5.25], [7.3, 5.3]])
            page.mouse.move(*points[0])
            page.mouse.down()
            held['route'].fulfill(response=held['response'])
            page.mouse.move(*points[1], steps=5)
            page.mouse.up()
            review.stroke((9.25, 5.25), (9.25, 5.25))
            name('Synthetic latest edits survive an older acknowledgement')
            page.unroute(pattern, delay_response)
            routes.remove((pattern, delay_response))
            latest = persisted(lambda value: value['document']['name'] == 'Synthetic latest edits survive an older acknowledgement'
                               and len(value['document']['floors']) == 3)
            idle()
            assert latest['version'] > painted['version']
            assert held['payload']['document']['name'] == 'Synthetic response held while painting'
            page.locator('[data-builder-undo]').click()
            persisted(lambda value: value['document']['name'] == 'Synthetic response held while painting'
                      and len(value['document']['floors']) == 3)
            page.locator('[data-builder-redo]').click()
            persisted(lambda value: value['document']['name'] == latest['document']['name'])
            idle()
            records.append({'case': 'in-flight-save-keeps-painting-enabled-and-old-response-cannot-overwrite-new-edits-or-undo-history'})

            # The server receives the first write; the browser loses its reply.
            # A retry must reuse its exact payload and logical-operation UUID.
            attempts, committed_versions = [], []

            def lose_response(route):
                attempts.append(deepcopy(route.request.post_data_json))
                if len(attempts) == 1:
                    committed_versions.append(route.fetch().json()['project']['version'])
                    route.abort('failed')
                else:
                    route.continue_()

            page.route(pattern, lose_response)
            routes.append((pattern, lose_response))
            name('Synthetic recovered response receipt')
            deadline = time.monotonic() + 15
            while len(attempts) < 1 and time.monotonic() < deadline:
                page.wait_for_timeout(50)
            assert attempts
            recovered = persisted(lambda value: value['document']['name'] == 'Synthetic recovered response receipt')
            idle()
            assert len(attempts) >= 2 and attempts[0] == attempts[1], attempts
            assert recovered['version'] == committed_versions[0], {'committed': committed_versions, 'recovered': recovered['version'], 'attempts': attempts}
            page.unroute(pattern, lose_response)
            routes.remove((pattern, lose_response))
            records.append({'case': 'lost-committed-response-retries-identical-uuid-and-payload-without-a-second-write'})

            # Reload while B has committed without an acknowledgement and Undo
            # has restored A. Recovery first replays B's receipt, then saves A
            # against the acknowledged revision instead of guessing its version.
            reload_attempts, reload_held = [], {}

            def hold_before_reload(route):
                reload_attempts.append(deepcopy(route.request.post_data_json))
                if len(reload_attempts) == 1:
                    reload_held.update(route=route, response=route.fetch())
                else:
                    route.continue_()

            page.route(pattern, hold_before_reload)
            routes.append((pattern, hold_before_reload))
            name('Synthetic uncertain B restored through receipt replay')
            deadline = time.monotonic() + 15
            while not reload_held and time.monotonic() < deadline:
                page.wait_for_timeout(50)
            assert reload_held
            committed_b = reload_held['response'].json()['project']
            page.locator('[data-builder-undo]').click()
            expect(page.locator('[data-builder-quick-name]')).to_have_value(recovered['name'])
            draft = page.evaluate('key=>JSON.parse(sessionStorage.getItem(key))',
                                 f'gravewright.map-builder.draft.{campaign}.{identifier}')
            assert draft['document'] == recovered['document']
            assert draft['saveAttempt']['payload']['document'] == committed_b['document']
            assert draft['pending'] and page.locator('[data-map-builder]').get_attribute('data-save-state') != 'saved'
            page.reload()
            reload_held['route'].abort('aborted')
            wait_ready(page)
            replayed = persisted(lambda value: value['document'] == recovered['document'])
            idle()
            assert len(reload_attempts) == 3, reload_attempts
            assert reload_attempts[0] == reload_attempts[1], reload_attempts
            assert reload_attempts[2]['document'] == recovered['document']
            assert reload_attempts[2]['expected_version'] == committed_b['version']
            assert replayed['version'] == committed_b['version'] + 1
            expect(page.locator('[data-builder-quick-name]')).to_have_value(recovered['name'])
            page.unroute(pattern, hold_before_reload)
            routes.remove((pattern, hold_before_reload))
            recovered = replayed
            records.append({'case': 'reload-replays-uncertain-committed-receipt-before-saving-undone-draft-with-acknowledged-revision'})

            # A concurrent writer wins a real revision race. The browser keeps
            # its local draft, then explicitly saves it under another identity.
            block = {}

            def delay_request(route):
                if block:
                    route.continue_()
                else:
                    block.update(route=route, payload=deepcopy(route.request.post_data_json))

            page.route(pattern, delay_request)
            routes.append((pattern, delay_request))
            name('Synthetic local draft awaiting conflict')
            deadline = time.monotonic() + 15
            while not block and time.monotonic() < deadline:
                page.wait_for_timeout(50)
            remote = deepcopy(recovered['document'])
            remote['name'] = 'Synthetic remote revision must be preserved'
            remote_project = review.store(identifier, recovered['version'], recovered['folderId'], remote)
            block['route'].continue_()
            expect(page.locator('[data-builder-notice]').get_by_role('button', name='Save a copy', exact=True)).to_be_visible()
            assert review.project(identifier)['document'] == remote_project['document']
            expect(page.locator('[data-builder-quick-name]')).to_have_value('Synthetic local draft awaiting conflict')
            page.unroute(pattern, delay_request)
            routes.remove((pattern, delay_request))
            page.locator('[data-builder-notice]').get_by_role('button', name='Save a copy', exact=True).click()
            copied = persisted(lambda value: value['id'] != identifier and value['document']['name'] == 'Synthetic local draft awaiting conflict')
            idle()
            assert review.project(identifier)['document'] == remote_project['document']
            identifier = copied['id']
            records.append({'case': 'revision-conflict-keeps-remote-data-and-local-draft-and-explicit-copy-creates-independent-project'})

            block = {}
            page.route(pattern, delay_request)
            routes.append((pattern, delay_request))
            name('Synthetic local draft to discard explicitly')
            deadline = time.monotonic() + 15
            while not block and time.monotonic() < deadline:
                page.wait_for_timeout(50)
            assert block
            remote = deepcopy(copied['document'])
            remote['name'] = 'Synthetic explicitly reloaded remote revision'
            reloaded = review.store(identifier, copied['version'], copied['folderId'], remote)
            block['route'].continue_()
            reload_button = page.locator('[data-builder-notice]').get_by_role('button', name='Reload saved project', exact=True)
            expect(reload_button).to_be_visible()
            page.unroute(pattern, delay_request)
            routes.remove((pattern, delay_request))
            reload_button.click()
            expect(page.locator('[data-builder-quick-name]')).to_have_value(reloaded['name'])
            idle()
            assert review.project(identifier)['document'] == reloaded['document']
            records.append({'case': 'explicit-conflict-reload-adopts-current-remote-revision-without-writing-the-stale-draft'})

            builder_tool(page, 'decoration')
            page.locator('[data-builder-brush-material]').select_option(lever_asset)
            review.stroke((17, 12), (19, 14))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=behavior]').select_option('lever')
            close_panel(page)
            prepared = persisted(lambda value: any(row.get('lever') for row in value['document']['decorations']))
            idle()
            owner_id = prepared['document']['decorations'][0]['id']
            modal = open_editor(owner_id)
            modal.locator('[data-blueprint-event="interact"]').click()
            counter = add_node(modal, 'counter')
            connect(modal, modal.locator('[data-blueprint-event-port="interact"]'), counter)
            target = card(modal, counter).locator('[data-blueprint-param=target]')
            target.fill('5')
            target.dispatch_event('change')

            def saved_counter(project, expected):
                owner = next(row for row in project['document']['decorations'] if row['id'] == owner_id)
                return any(node.get('target') == expected for graph in owner.get('blueprint', {}).get('graphs', {}).values()
                           for node in graph['nodes'] if node['id'] == counter)

            graph_saved = persisted(lambda value: saved_counter(value, 5))
            expect(modal.locator('[data-blueprint-autosave]')).to_have_attribute('data-state', 'saved')
            target.fill('0')
            target.dispatch_event('change')
            modal.locator('[data-blueprint-close]').click()
            expect(modal).to_be_visible()
            assert not target.evaluate('element=>element.checkValidity()')
            assert saved_counter(review.project(identifier), 5)
            target.fill('6')
            target.dispatch_event('change')
            modal.locator('[data-blueprint-close]').click()
            expect(modal).to_have_count(0)
            persisted(lambda value: saved_counter(value, 6))
            idle()
            modal = open_editor(owner_id)
            expect(card(modal, counter).locator('[data-blueprint-param=target]')).to_have_value('6')
            modal.locator('[data-blueprint-close]').click()
            records.append({'case': 'smart-object-graph-persists-without-save-close-flushes-valid-edits-and-invalid-field-blocks-close-without-committing'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width, height in ((1440, 900), (390, 844)):
                    page.set_viewport_size({'width': width, 'height': height})
                    page.goto(review.builder + '?project=' + identifier)
                    wait_ready(page)
                    modal = open_editor(owner_id)
                    expect(modal.locator('[data-blueprint-autosave]')).to_be_visible()
                    metrics = modal.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'autosave-editor-{locale}-{width}.png'))
                    modal.locator('[data-blueprint-close]').click()
                    records.append({'case': 'localized-project-and-graph-autosave-status-and-close-controls-fit-desktop-mobile',
                                    'locale': locale, 'width': width, 'metrics': metrics})

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(review.builder + '?project=' + identifier)
            wait_ready(page)

            # Normal navigation waits for a final project write. Reload reads
            # server state, with no manual save click anywhere in this scenario.
            name('Synthetic navigation flush', blur=False)
            page.locator('.map-builder__back').click()
            page.wait_for_url(f'{base}/game/{campaign}')
            final = review.project(identifier)
            assert final['document']['name'] == 'Synthetic navigation flush', final
            page.goto(review.builder + '?project=' + identifier)
            wait_ready(page)
            expect(page.locator('[data-builder-quick-name]')).to_have_value(final['name'])
            records.append({'case': 'back-to-game-navigation-flushes-focused-name-and-pending-write-before-leaving'})

            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            scene = review.project(identifier)['sceneId']

            def native_state():
                response = page.request.get(f'/api/maps/{scene}/state')
                assert response.ok, response.text()
                return response.json()

            def automation():
                response = page.request.get(f'/api/maps/{scene}/automation')
                assert response.ok, response.text()
                return response.json()

            native_owner, = [value for value in native_state()['images'] if value.get('lever')]
            native_url = f'/api/maps/{scene}/automation/network/{native_owner["id"]}'
            before_log = automation()
            page.locator('.game-menubar__layer').nth(5).click()
            page.locator('[data-dock-tool=automation]').click()
            controls = page.locator('.automation-log')
            controls.locator('[data-automation-view=doors]').click()
            controls.locator(f'[data-scene-controls-element="{native_owner["id"]}"]').click()
            controls.locator('[data-scene-controls-edit]').click()
            modal = page.locator('[data-smart-object-modal]')
            expect(modal).to_be_visible()
            target = card(modal, counter).locator('[data-blueprint-param=target]')
            with page.expect_response(lambda response: response.request.method == 'POST'
                                      and response.url.endswith(native_url)) as live_saved:
                target.fill('9')
                target.dispatch_event('change')
            assert live_saved.value.ok, live_saved.value.text()
            expect(modal.locator('[data-blueprint-autosave]')).to_have_attribute('data-state', 'saved')
            native_owner = next(value for value in native_state()['images'] if value['id'] == native_owner['id'])
            assert saved_counter(review.project(identifier), 9)
            assert native_owner['lever']['state'] == 'off'
            assert automation()['runs'] == before_log['runs']
            assert automation()['variables'] == before_log['variables']
            records.append({'case': 'live-smart-object-autosave-updates-native-and-source-revisions-without-executing-gameplay'})

            native_block, native_attempts = {}, []

            def delay_native(route):
                native_attempts.append(deepcopy(route.request.post_data_json))
                if native_block:
                    route.continue_()
                else:
                    native_block.update(route=route, payload=deepcopy(route.request.post_data_json))

            native_pattern = '**' + native_url
            page.route(native_pattern, delay_native)
            routes.append((native_pattern, delay_native))
            target.fill('10')
            target.dispatch_event('change')
            deadline = time.monotonic() + 15
            while not native_block and time.monotonic() < deadline:
                page.wait_for_timeout(50)
            assert native_block
            remote_blueprint = deepcopy(native_owner['blueprint'])
            for graph in remote_blueprint['graphs'].values():
                for value in graph['nodes']:
                    if value['id'] == counter:
                        value['target'] = 12
            remote_result = post(page, native_url, {'request_id': str(uuid4()),
                'expected_version': native_owner['version'],
                'expected_project_version': review.project(identifier)['version'], 'blueprint': remote_blueprint})
            assert remote_result['status'] == 200, remote_result
            native_block['route'].continue_()
            expect(modal.locator('[data-blueprint-autosave]')).to_have_attribute('data-state', 'conflict')
            expect(modal.locator('[data-blueprint-discard]')).to_be_visible()
            expect(modal.locator('[data-blueprint-retry]')).to_be_hidden()
            assert saved_counter(review.project(identifier), 12)
            modal.locator('[data-blueprint-close]').click()
            expect(modal).to_be_visible()
            target.fill('11')
            target.dispatch_event('change')
            page.wait_for_timeout(1200)
            assert len(native_attempts) == 2, native_attempts
            assert native_attempts[0]['expected_version'] == native_block['payload']['expected_version']
            assert saved_counter(review.project(identifier), 12)
            modal.locator('[data-blueprint-discard]').click()
            expect(modal).to_have_count(0)
            assert automation()['runs'] == before_log['runs']
            assert automation()['variables'] == before_log['variables']
            page.unroute(native_pattern, delay_native)
            routes.remove((native_pattern, delay_native))
            records.append({'case': 'live-autosave-conflict-pauses-further-edits-and-close-without-rebase-and-explicit-discard-preserves-remote-config'})
        except Exception:
            (output / 'writes.json').write_text(json.dumps(writes, indent=2), encoding='utf-8')
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            for pattern, callback in routes:
                page.unroute(pattern, callback)
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'projectWrites': len(writes), 'assets': 'Synthetic solid-color PNGs; no operator campaign data.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
