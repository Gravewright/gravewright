"""Keep the Map Builder library and brush choices aligned with imported types.

Uploads, campaign, project, media and server are synthetic and disposable. The
scenario never classifies or rewrites an operator's images.
"""
from __future__ import annotations

import json

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar
from map_builder_asset_removal import BuilderReview
from map_builder_reference import upload_asset, wait_ready


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    records, errors, failed, dialogs = [], [], [], []
    campaign = seed['campaign']
    roles = ('floor', 'wall', 'door', 'decoration')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        review = BuilderReview(page, campaign)

        def diagnostics(target):
            target.on('pageerror', lambda error: errors.append(str(error)))
            target.on('requestfailed', lambda request: failed.append({'url': request.url, 'error': request.failure}))
            target.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))

        def idle(target=page):
            expect(target.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved', timeout=20_000)

        def project():
            identifier = page.evaluate("new URL(location.href).searchParams.get('project')")
            assert identifier
            return review.project(identifier)

        def gallery(role, expected, target=page):
            target.locator(f'[data-builder-role="{role}"]').click()
            expect(target.locator(f'[data-builder-role="{role}"]')).to_have_attribute('aria-pressed', 'true')
            cards = target.locator('[data-builder-assets] [data-asset-id]')
            expect(cards).to_have_count(len(expected))
            actual = cards.evaluate_all('cards=>cards.map(card=>card.dataset.assetId)')
            assert set(actual) == set(expected) and len(actual) == len(set(actual)), {'role': role, 'actual': actual, 'expected': sorted(expected)}

        diagnostics(page)
        try:
            # This predates the Builder project and therefore has no project
            # classification. Keep it reachable through Material, not type tabs.
            csrf = page.request.get('/__gravewright/csrf').json()
            uploaded = page.request.post(f'/api/containers/{campaign}/library/upload',
                headers={csrf['header']: csrf['token']}, multipart={'file': {
                    'name': 'Synthetic preexisting unclassified campaign image.png',
                    'mimeType': 'image/png', 'buffer': harness.artwork('#77805c')}})
            assert uploaded.status == 201, uploaded.text()
            legacy = uploaded.json()['id']
            page.goto(review.builder)
            wait_ready(page)
            expect(page.locator('[data-builder-role=floor]')).to_have_attribute('aria-pressed', 'true')
            for role in roles:
                gallery(role, set())
            records.append({'case': 'unclassified-campaign-image-does-not-appear-in-any-classified-type-tab'})

            page.locator('[data-builder-quick-name]').fill('Synthetic strict asset type filtering')
            page.locator('[data-builder-quick-name]').press('Tab')
            idle()
            assets = {}
            colors = {'floor': '#a27540', 'wall': '#717b85', 'door': '#6d462e', 'decoration': '#417b5d'}
            for role in roles:
                asset = upload_asset(page, role, f'Synthetic imported {role}.png', harness.artwork(colors[role]))
                assets[role] = asset['id']
                gallery(role, {asset['id']})
                idle()
                metadata = {row['assetId']: row for row in project()['document']['assets']}
                assert metadata[asset['id']]['role'] == role
                records.append({'case': 'imported-type-immediately-selects-and-filters-its-own-tab-and-saves-automatically', 'role': role})

            expected = {role: {identifier} for role, identifier in assets.items()}
            for role in roles:
                gallery(role, expected[role])
            original_campaign = {row['id']: row['name'] for row in page.request.get(review.api).json()['assets']}
            assert set(original_campaign) == {legacy, *assets.values()}
            before_reload = project()
            records.append({'case': 'switching-type-tabs-shows-exact-disjoint-classified-assets'})

            # The initial Floor category must be a real filter even before the
            # user clicks it. A new tab has no retained JavaScript editor state.
            identifier = before_reload['id']
            for target, kind in ((page, 'reload'), (context.new_page(), 'new-tab')):
                if kind == 'reload':
                    target.reload()
                else:
                    diagnostics(target)
                    target.goto(review.builder + '?project=' + identifier)
                wait_ready(target)
                expect(target.locator('[data-builder-role=floor]')).to_have_attribute('aria-pressed', 'true')
                cards = target.locator('[data-builder-assets] [data-asset-id]')
                expect(cards).to_have_count(len(expected['floor']))
                assert set(cards.evaluate_all('cards=>cards.map(card=>card.dataset.assetId)')) == expected['floor']
                for role in roles:
                    gallery(role, expected[role], target)
                if target != page:
                    target.close()
                records.append({'case': 'saved-type-metadata-and-initial-floor-filter-survive-independent-load', 'load': kind})

            page.locator('[data-builder-quick-tool=paint]').click()
            expect(page.locator('[data-builder-role=floor]')).to_have_attribute('aria-pressed', 'true')
            gallery('floor', expected['floor'])
            builder_sidebar(page, 'tools')
            material_ids = set(page.locator('[data-builder-brush-material] option').evaluate_all('options=>options.map(option=>option.value)'))
            assert assets['floor'] in material_ids and legacy in material_ids
            assert not ({assets['wall'], assets['door'], assets['decoration']} & material_ids)
            expect(page.locator('[data-builder-brush-material] optgroup[label="Unclassified images"] option')).to_have_attribute('value', legacy)
            builder_sidebar(page, 'library')
            records.append({'case': 'quick-paint-restores-floor-gallery-and-material-selector-excludes-other-imported-types'})

            # Classification edits move the same image instead of uploading,
            # deleting or renaming the campaign resource.
            for asset_id, old_role, new_role in ((assets['decoration'], 'decoration', 'door'),):
                gallery(old_role, expected[old_role])
                page.locator(f'[data-builder-assets] [data-asset-id="{asset_id}"]').dblclick()
                modal = page.locator('[data-builder-asset-modal]')
                expect(modal).to_be_visible()
                modal.locator('[data-builder-import-role]').select_option(new_role)
                modal.locator('[data-builder-import-submit]').click()
                expect(modal).to_have_count(0)
                expected[old_role].remove(asset_id)
                expected[new_role].add(asset_id)
                idle()
                for role in roles:
                    gallery(role, expected[role])
                metadata = {row['assetId']: row for row in project()['document']['assets']}
                assert metadata[asset_id]['role'] == new_role
                assert {row['id']: row['name'] for row in page.request.get(review.api).json()['assets']} == original_campaign
                records.append({'case': 'editing-asset-type-moves-existing-image-and-preserves-campaign-assets', 'sourceRole': old_role})

            gallery('door', expected['door'])
            builder_sidebar(page, 'tools')
            expect(page.locator('[data-builder-brush-material] optgroup[label="Unclassified images"] option')).to_have_attribute('value', legacy)
            page.locator('[data-builder-brush-material]').select_option(legacy)
            idle()
            expected['door'].add(legacy)
            builder_sidebar(page, 'library')
            for role in roles:
                gallery(role, expected[role])
            metadata = {row['assetId']: row for row in project()['document']['assets']}
            assert metadata[legacy]['role'] == 'door'
            assert {row['id']: row['name'] for row in page.request.get(review.api).json()['assets']} == original_campaign
            builder_sidebar(page, 'tools')
            assert page.locator('[data-builder-brush-material] optgroup[label="Unclassified images"] option').count() == 0
            builder_sidebar(page, 'library')
            records.append({'case': 'material-selector-classifies-untyped-campaign-image-for-active-tool-without-reuploading'})

            page.reload()
            wait_ready(page)
            for role in roles:
                gallery(role, expected[role])
            assert project()['document']['floors'] == [] and project()['document']['doors'] == []
            gallery('door', expected['door'])
            metrics = page.locator('[data-map-builder]').evaluate(MEASURE)
            assert not metrics['tiny'] and not metrics['overflow'], metrics
            page.screenshot(path=str(output / 'typed-door-library.png'))
            records.append({'case': 'edited-types-survive-reload-without-creating-map-elements', 'metrics': metrics})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            (output / 'diagnostics.json').write_text(json.dumps({'errors': errors, 'failedRequests': failed, 'nativeDialogs': dialogs}, indent=2), encoding='utf-8')
            raise
        finally:
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    assert not [request for request in failed if request['error'] != 'net::ERR_ABORTED'], failed
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'failedRequests': failed, 'assets': 'Synthetic solid-color PNGs in an isolated campaign.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
