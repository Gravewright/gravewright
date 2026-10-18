"""Check explicit campaign asset removal from the Map Builder asset editor.

All campaign state and media are synthetic and use the shared isolated builder
fixture. Browser diagnostics stay in a fresh installation-local output folder.
"""
from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, change_locale
from map_builder_reference import set_name, upload_asset, wait_ready


class BuilderReview:
    """Drive public controls and APIs without accessing an operator campaign."""

    def __init__(self, page, campaign):
        self.page = page
        self.builder = f'/game/{campaign}/map-builder'
        self.api = f'/api/containers/{campaign}/map-builder'
        self.campaign = campaign

    def save(self):
        if self.page.locator('[data-map-builder]').get_attribute('data-save-state') == 'saved':
            project_id = self.page.evaluate("new URL(location.href).searchParams.get('project')")
            response = self.page.request.get(self.api + '/projects/' + project_id)
        else:
            with self.page.expect_response(lambda response: response.request.method == 'POST'
                                           and '/map-builder/projects/' in response.url
                                           and not response.url.endswith(('/generate', '/update'))) as saved:
                self.page.locator('[data-builder-save]').click()
            response = saved.value
        assert response.ok, response.text()
        return response.json()['project']

    def stroke(self, start, end):
        from map_builder import builder_workspace
        builder_workspace(self.page)
        points = self.page.locator('[data-builder-canvas]').evaluate("""(canvas, points) => points.map(point => {
          const p = new DOMPoint(...point).matrixTransform(canvas.getScreenCTM());
          return [p.x, p.y];
        })""", [start, end])
        self.page.mouse.move(*points[0])
        self.page.mouse.down()
        self.page.mouse.move(*points[1], steps=5)
        self.page.mouse.up()

    def project(self, project_id):
        response = self.page.request.get(self.api + '/projects/' + project_id)
        assert response.ok, response.text()
        return response.json()['project']

    def copy_project(self, project):
        document = deepcopy(project['document'])
        document['name'] = 'Other saved project sharing the removed image'
        return self.store(str(uuid4()), 0, project['folderId'], document)

    def store(self, project_id, version, folder_id, document):
        result = self.page.evaluate("""async args => {
          const csrf = await (await fetch('/__gravewright/csrf')).json();
          const response = await fetch(args.url, {method:'POST',
            headers:{'Content-Type':'application/json', [csrf.header]:csrf.token},
            body:JSON.stringify(args.body)});
          return {status:response.status, body:await response.json()};
        }""", {'url': self.api + '/projects/' + project_id, 'body': {
            'request_id': str(uuid4()), 'expected_version': version,
            'folder_id': folder_id, 'document': document}})
        assert result['status'] == 200, result
        return result['body']['project']

    def draft(self, project_id):
        return self.page.evaluate("""key => {
          const draft = JSON.parse(sessionStorage.getItem(key));
          if (!draft) throw Error('Expected the unsaved project draft');
          return draft.document;
        }""", f'gravewright.map-builder.draft.{self.campaign}.{project_id}')


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    records, errors, failed, dialogs, deletions = [], [], [], [], []
    campaign = seed['campaign']
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('requestfailed', lambda request: failed.append({'url': request.url, 'error': request.failure}))
        page.on('request', lambda request: deletions.append(request.post_data_json)
                if request.method == 'POST' and request.url.endswith('/library/assets/delete') else None)

        def native_dialog(dialog):
            dialogs.append(dialog.message)
            dialog.dismiss()

        page.on('dialog', native_dialog)
        review = BuilderReview(page, campaign)
        try:
            page.goto(review.builder)
            wait_ready(page)
            set_name(page, 'Synthetic asset deletion baseline')
            removed = upload_asset(page, 'door',
                                   'Synthetic door material with a deliberately long descriptive author supplied name.png',
                                   harness.artwork('#a4522d'))['id']
            retained = upload_asset(page, 'decoration', 'Synthetic retained decoration.png',
                                    harness.artwork('#3f7696'))['id']
            # The destructive control belongs only to existing assets.
            page.locator('[data-builder-import]').click()
            importing = page.locator('[data-builder-import-modal]')
            expect(importing.locator('[data-builder-asset-remove]:visible')).to_have_count(0)
            importing.locator('[data-builder-import-cancel]').click()
            builder_tool(page, 'door')
            page.locator('[data-builder-brush-material]').select_option(removed)
            review.stroke((8, 6), (10, 6))
            original = review.save()
            other = review.copy_project(original)

            def open_editor(keyboard=False, asset_id=removed, role='door'):
                builder_sidebar(page, 'library')
                page.locator(f'[data-builder-role={role}]').click()
                card = page.locator(f'[data-builder-assets] [data-asset-id="{asset_id}"]')
                card.scroll_into_view_if_needed()
                if keyboard:
                    card.focus()
                    page.keyboard.press('Shift+F10')
                else:
                    card.dblclick()
                editor = page.locator('[data-builder-asset-modal]')
                expect(editor).to_be_visible()
                expect(editor.locator('[data-builder-asset-remove]')).to_be_visible()
                return editor

            def confirmation(editor):
                editor.locator('[data-builder-asset-remove]').click()
                confirm = page.locator('[data-builder-asset-remove-confirm]')
                expect(confirm).to_be_visible()
                expect(confirm).to_have_attribute('role', 'dialog')
                expect(page.locator('dialog')).to_have_count(0)
                return confirm

            # Long existing names must fit alongside the new action. Cancellation
            # retains the asset form's pending alias as well as campaign data.
            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width, height in ((1440, 900), (390, 844)):
                    page.set_viewport_size({'width': width, 'height': height})
                    page.goto(review.builder + '?project=' + original['id'])
                    wait_ready(page)
                    expect(page.locator('html')).to_have_attribute('lang', locale)
                    editor = open_editor(keyboard=True)
                    alias = 'Pending authored alias preserved when campaign deletion is canceled'
                    editor.locator('[data-builder-import-name-input]').fill(alias)
                    edit_metrics = editor.evaluate(MEASURE)
                    assert not edit_metrics['tiny'] and not edit_metrics['overflow'], edit_metrics
                    page.screenshot(path=str(output / f'asset-editor-{locale}-{width}.png'))
                    confirm = confirmation(editor)
                    assert confirm.inner_text().strip()
                    confirm_metrics = confirm.evaluate(MEASURE)
                    assert not confirm_metrics['tiny'] and not confirm_metrics['overflow'], confirm_metrics
                    page.screenshot(path=str(output / f'asset-remove-confirm-{locale}-{width}.png'))
                    for _ in range(10):
                        page.keyboard.press('Tab')
                        assert confirm.evaluate('element => element.contains(document.activeElement)')
                    confirm.locator('[data-builder-asset-remove-cancel]').click()
                    expect(confirm).to_have_count(0)
                    expect(editor.locator('[data-builder-import-name-input]')).to_have_value(alias)
                    expect(editor.locator('[data-builder-asset-remove]')).to_be_focused()
                    editor.locator('[data-builder-import-cancel]').click()
                    assert review.project(original['id'])['document'] == original['document']
                    assert removed in {asset['id'] for asset in page.request.get(review.api).json()['assets']}
                    assert not deletions, deletions
                    records.append({'case': 'localized-asset-editor-and-nested-confirmation-cancel-preserve-form-and-data',
                                    'locale': locale, 'width': width, 'editMetrics': edit_metrics,
                                    'confirmMetrics': confirm_metrics})

            # Make one scene contain a real door using the material. Its native
            # barrier must survive deleting only the artwork from the campaign.
            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(review.builder + '?project=' + original['id'])
            wait_ready(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            generated_project = review.project(original['id'])
            scene_id = generated_project['sceneId']
            native_before = page.request.get(f'/api/maps/{scene_id}/state').json()
            native_door, = [wall for wall in native_before['walls'] if wall['kind'] == 'door']
            assert native_door['asset_id'] == removed, native_door
            page.goto(review.builder + '?project=' + original['id'])
            wait_ready(page)
            set_name(page, 'Unsaved name preserved across asset deletion')
            builder_tool(page, 'wall')
            page.locator('[data-builder-brush-material]').select_option('')
            review.stroke((15, 10), (18, 10))
            unsaved = review.draft(original['id'])
            assert len(unsaved['walls']) == 1 and unsaved['name'] != original['document']['name'], unsaved

            editor = open_editor()
            confirm = confirmation(editor)
            delete_url = f'**/api/containers/{campaign}/library/assets/delete'

            def fail_delete(route):
                route.fulfill(status=503, content_type='application/json',
                              body='{"error":"Synthetic asset removal failure"}')

            page.route(delete_url, fail_delete)
            with page.expect_response(lambda response: response.url.endswith('/library/assets/delete')) as rejected:
                confirm.locator('[data-builder-asset-remove-submit]').click()
            assert rejected.value.status == 503
            expect(confirm.locator('[role=alert]')).to_contain_text('Synthetic asset removal failure')
            expect(confirm.locator('[data-builder-asset-remove-submit]')).to_be_enabled()
            expect(editor).to_be_visible()
            assert review.draft(original['id']) == unsaved
            assert review.project(original['id'])['document'] == generated_project['document']
            assert review.project(other['id'])['document'] == other['document']
            assert removed in {asset['id'] for asset in page.request.get(review.api).json()['assets']}
            page.screenshot(path=str(output / 'asset-remove-recoverable-failure.png'))
            page.unroute(delete_url, fail_delete)
            records.append({'case': 'failed-delete-keeps-asset-all-projects-unsaved-draft-and-retryable-confirmation'})

            with page.expect_response(lambda response: response.url.endswith('/library/assets/delete')) as accepted:
                confirm.locator('[data-builder-asset-remove-submit]').click()
            assert accepted.value.ok, accepted.value.text()
            expect(confirm).to_have_count(0)
            expect(editor).to_have_count(0)
            wait_ready(page)
            expect(page.locator(f'[data-builder-assets] [data-asset-id="{removed}"]')).to_have_count(0)
            assets = {asset['id'] for asset in page.request.get(review.api).json()['assets']}
            assert removed not in assets and retained in assets, assets
            assert page.request.get(f'/game/map-assets/{removed}').status == 404
            cleaned = review.draft(original['id'])
            assert cleaned['name'] == unsaved['name'] and cleaned['walls'] == unsaved['walls'], cleaned
            assert cleaned['doors'][0]['assetId'] is None, cleaned
            assert removed not in str(cleaned), cleaned
            remote = review.project(original['id'])
            assert remote['version'] > generated_project['version'], remote
            assert remote['document']['doors'][0]['assetId'] is None, remote
            other_cleaned = review.project(other['id'])
            assert other_cleaned['version'] > other['version'], other_cleaned
            assert other_cleaned['document']['doors'][0]['assetId'] is None, other_cleaned
            assert removed not in str(other_cleaned['document']), other_cleaned
            native_after = page.request.get(f'/api/maps/{scene_id}/state').json()
            same_door, = [wall for wall in native_after['walls'] if wall['id'] == native_door['id']]
            assert same_door['kind'] == 'door' and same_door['door_state'] == 'closed', same_door
            assert not same_door.get('asset_id'), same_door
            assert all(same_door[key] == native_door[key] for key in ('x1', 'y1', 'x2', 'y2')), same_door
            records.append({'case': 'confirmed-campaign-delete-refreshes-gallery-and-other-project-and-preserves-native-door-barrier'})

            # Sanitized history must never reintroduce references to a deleted
            # campaign resource, even while the user's unsaved work is retained.
            page.locator('[data-builder-undo]').click()
            assert removed not in str(review.draft(original['id']))
            page.locator('[data-builder-redo]').click()
            assert review.draft(original['id']) == cleaned
            saved = review.save()
            assert saved['document'] == cleaned, saved
            page.reload()
            wait_ready(page)
            assert review.project(original['id'])['document'] == cleaned
            assert not page.locator('[data-builder-notice]:visible').count()
            assert len(deletions) == 2 and all(payload == {'asset_id': removed} for payload in deletions), deletions
            page.screenshot(path=str(output / 'asset-removed-current-draft-saved.png'))
            records.append({'case': 'unsaved-name-and-geometry-survive-delete-undo-redo-save-and-reload-with-current-revision'})

            # A committed delete with a lost response must reconcile through
            # the catalog rather than presenting a stale, unusable asset.
            lost_asset = upload_asset(page, 'door', 'Synthetic lost acknowledgement door.png',
                                      harness.artwork('#7b4931'))['id']
            before_lost_ack = review.save()
            set_name(page, 'Unsaved work retained after lost deletion acknowledgement')
            editor = open_editor(asset_id=lost_asset)
            confirm = confirmation(editor)

            def lose_acknowledgement(route):
                response = route.fetch()
                assert response.ok, response.text()
                route.fulfill(status=503, content_type='application/json',
                              body='{"error":"Synthetic lost deletion acknowledgement"}')

            page.route(delete_url, lose_acknowledgement)
            with page.expect_response(lambda response: response.url.endswith('/library/assets/delete')) as lost_ack:
                confirm.locator('[data-builder-asset-remove-submit]').click()
            assert lost_ack.value.status == 503
            expect(confirm).to_have_count(0)
            expect(editor).to_have_count(0)
            page.unroute(delete_url, lose_acknowledgement)
            reconciled = review.draft(original['id'])
            assert lost_asset not in str(reconciled), reconciled
            assert reconciled['name'] == 'Unsaved work retained after lost deletion acknowledgement', reconciled
            assert review.project(original['id'])['version'] > before_lost_ack['version']
            assert lost_asset not in {asset['id'] for asset in page.request.get(review.api).json()['assets']}
            assert review.save()['document'] == reconciled
            page.reload()
            wait_ready(page)
            records.append({'case': 'lost-delete-acknowledgement-reconciles-confirmed-catalog-absence-and-preserves-unsaved-work'})

            # A reload can interrupt the acknowledgement after the server
            # commits. Persisted intent must repair the recovered draft and
            # revision before another save, retaining unrelated local edits.
            reload_asset = upload_asset(page, 'door', 'Synthetic reload during committed deletion.png',
                                        harness.artwork('#8f603c'))['id']
            review.save()
            set_name(page, 'Unsaved work retained after reloading a committed deletion')
            editor = open_editor(asset_id=reload_asset)
            confirm = confirmation(editor)

            def reload_after_commit(route):
                response = route.fetch()
                assert response.ok, response.text()
                page.evaluate('setTimeout(() => location.reload(), 0)')
                route.abort('aborted')

            page.route(delete_url, reload_after_commit)
            with page.expect_navigation(wait_until='domcontentloaded'):
                confirm.locator('[data-builder-asset-remove-submit]').click(no_wait_after=True)
            page.unroute(delete_url, reload_after_commit)
            wait_ready(page)
            recovered = review.draft(original['id'])
            assert recovered['name'] == 'Unsaved work retained after reloading a committed deletion', recovered
            assert reload_asset not in str(recovered), recovered
            assert reload_asset not in {asset['id'] for asset in page.request.get(review.api).json()['assets']}
            assert review.save()['document'] == recovered
            page.reload()
            wait_ready(page)
            records.append({'case': 'reload-after-committed-delete-recovers-persisted-intent-and-unrelated-unsaved-edits'})

            # Another browser may have deleted an alternate image while this
            # editor still has it cached. Deleting a lever's base image must
            # never promote that missing alternate into the base image.
            lever_base = upload_asset(page, 'decoration', 'Synthetic stale alternate lever base.png',
                                      harness.artwork('#6b492d'))['id']
            lever_alternate = upload_asset(page, 'decoration', 'Synthetic stale alternate lever on.png',
                                           harness.artwork('#31728e'))['id']
            lever_source = review.save()
            lever_document = deepcopy(lever_source['document'])
            lever_document['decorations'].append({
                'id': str(uuid4()), 'layerId': lever_document['layers'][0]['id'], 'assetId': lever_base,
                'x': 12, 'y': 12, 'width': 2, 'height': 2, 'rotation': 0, 'lever': {'state': 'off'},
                'blueprint': {'version': 2, 'kind': 'lever', 'graphs': {}, 'states': {
                    'off': {'appearance': 'inherit'}, 'on': {'appearance': 'asset', 'assetId': lever_alternate}}},
            })
            review.store(lever_source['id'], lever_source['version'], lever_source['folderId'], lever_document)
            page.goto(review.builder + '?project=' + original['id'])
            wait_ready(page)
            deleted_alternate = page.evaluate("""async args => {
              const csrf = await (await fetch('/__gravewright/csrf')).json();
              const response = await fetch(args.url, {method:'POST',
                headers:{'Content-Type':'application/json', [csrf.header]:csrf.token},
                body:JSON.stringify({asset_id:args.id})});
              return {status:response.status, body:await response.json()};
            }""", {'url': f'/api/containers/{campaign}/library/assets/delete', 'id': lever_alternate})
            assert deleted_alternate['status'] == 200, deleted_alternate
            set_name(page, 'Unsaved lever edit survives stale alternate cleanup')
            editor = open_editor(asset_id=lever_base, role='decoration')
            confirm = confirmation(editor)
            with page.expect_response(lambda response: response.url.endswith('/library/assets/delete')) as lever_deleted:
                confirm.locator('[data-builder-asset-remove-submit]').click()
            assert lever_deleted.value.ok, lever_deleted.value.text()
            expect(confirm).to_have_count(0)
            expect(editor).to_have_count(0)
            without_art = review.draft(original['id'])
            decoration = without_art['decorations'][-1]
            assert decoration['assetId'] is None and 'lever' not in decoration and 'blueprint' not in decoration, decoration
            assert lever_base not in str(without_art) and lever_alternate not in str(without_art), without_art
            assert without_art['name'] == 'Unsaved lever edit survives stale alternate cleanup', without_art
            assert review.save()['document'] == without_art
            page.reload()
            wait_ready(page)
            records.append({'case': 'stale-missing-alternate-is-not-promoted-when-removing-lever-base-image'})

            # Deletion may clean another browser's latest saved project. The
            # editor must preserve that concurrent edit and retain its conflict
            # guard instead of adopting the remote version to force a save.
            concurrent_asset = upload_asset(page, 'door', 'Synthetic concurrent project door.png',
                                            harness.artwork('#985b3f'))['id']
            before_concurrent = review.save()
            set_name(page, 'Local unsaved name before concurrent campaign deletion')
            remote_document = deepcopy(before_concurrent['document'])
            remote_document['name'] = 'Concurrent saved edit must survive'
            remote = review.store(before_concurrent['id'], before_concurrent['version'],
                                  before_concurrent['folderId'], remote_document)
            editor = open_editor(asset_id=concurrent_asset)
            confirm = confirmation(editor)
            with page.expect_response(lambda response: response.url.endswith('/library/assets/delete')) as concurrent_delete:
                confirm.locator('[data-builder-asset-remove-submit]').click()
            assert concurrent_delete.value.ok, concurrent_delete.value.text()
            expect(confirm).to_have_count(0)
            expect(editor).to_have_count(0)
            expect(page.locator('[data-builder-notice]')).to_contain_text('this project has changed elsewhere')
            local = review.draft(original['id'])
            assert local['name'] == 'Local unsaved name before concurrent campaign deletion', local
            assert concurrent_asset not in str(local), local
            remote_cleaned = review.project(original['id'])
            assert remote_cleaned['version'] > remote['version']
            assert remote_cleaned['document']['name'] == remote_document['name'], remote_cleaned
            assert concurrent_asset not in str(remote_cleaned['document']), remote_cleaned
            attempted_writes = []

            def observe_write(response):
                if response.request.method == 'POST' and response.url.endswith('/projects/' + original['id']):
                    attempted_writes.append(response)

            page.on('response', observe_write)
            page.locator('[data-builder-save]').click()
            wait_ready(page)
            page.remove_listener('response', observe_write)
            if attempted_writes:
                assert all(response.status == 409 for response in attempted_writes), [response.status for response in attempted_writes]
            else:
                expect(page.locator('[data-builder-notice]')).to_contain_text('this project has changed elsewhere')
            assert review.project(original['id']) == remote_cleaned
            assert review.draft(original['id']) == local
            page.screenshot(path=str(output / 'asset-removed-concurrent-project-protected.png'))
            records.append({'case': 'asset-removal-preserves-concurrent-saved-project-and-keeps-local-revision-conflict'})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    assert not [request for request in failed if request['error'] != 'net::ERR_ABORTED'], failed
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'failedRequests': failed, 'assets': 'Synthetic solid-color PNGs; no operator data.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
