"""Edit presence filters in the Builder and native region window with isolated data."""
from __future__ import annotations

from copy import deepcopy
import json
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import close_panel, set_name, wait_ready


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    records, errors, dialogs = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        review = BuilderReview(page, campaign)

        def wait_game():
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def select_region(identifier):
            builder_tool(page, 'select'); builder_workspace(page)
            target = page.locator(f'[data-builder-regions] [data-object-id="{identifier}"]')
            box = target.bounding_box()
            page.mouse.click(box['x'] + box['width'] * .2, box['y'] + box['height'] * .2)
            builder_sidebar(page, 'selection')
            expect(page.locator('[data-builder-region-filters]')).to_be_visible()
            page.locator('[data-builder-region-filters]').evaluate('details=>details.open=true')

        def filter_control(key):
            details = page.locator('[data-builder-region-filters]')
            if not details.evaluate('details=>details.open'): details.locator('summary').click()
            return page.locator(f'[data-builder-region-filter="{key}"]')

        try:
            page.goto(f'/game/{campaign}'); wait_game()
            actor_name = 'Synthetic long authored keeper ' + '\u96ea' * 35
            actor = page.evaluate("name=>gravewrightRealtime.resourceCommand('actors','actor.create',{name})", actor_name)
            actor_id = actor['id']
            requests = []

            def catalog(route):
                requests.append(route.request.url)
                if len(requests) == 1:
                    route.fulfill(status=503, json={'error': 'Synthetic catalog failure'})
                else:
                    route.continue_()

            page.route(f'**/api/containers/{campaign}/actors', catalog)
            page.goto(review.builder); wait_ready(page)
            set_name(page, 'Synthetic region filter editor')
            builder_tool(page, 'region'); review.stroke((10, 8), (14, 12))
            builder_sidebar(page, 'selection')
            details = page.locator('[data-builder-region-filters]')
            details.evaluate('details=>details.open=true')
            retry = page.locator('[data-builder-filter-retry]')
            expect(retry).to_be_visible(); retry.click()
            expect(filter_control('actorIds').locator(f'option[value="{actor_id}"]')).to_have_text(actor_name)
            assert len(requests) == 2, requests
            fresh = review.save()
            region_id = fresh['document']['regions'][0]['id']
            assert 'filters' not in fresh['document']['regions'][0]
            expect(filter_control('tokenIds')).to_be_disabled()
            records.append({'case': 'catalog-failure-retry-and-legacy-empty-filters-stay-absent'})

            filter_control('actorIds').select_option([actor_id])
            filter_control('dispositions').select_option(['friendly', 'neutral'])
            filter_control('visibility').select_option('visible')
            authored = review.save()
            expected_filters = {'actorIds': [actor_id], 'tokenIds': [], 'dispositions': ['friendly', 'neutral'], 'visibility': 'visible'}
            assert authored['document']['regions'][0]['filters'] == expected_filters
            page.locator('[data-builder-undo]').click()
            assert review.save()['document']['regions'][0]['filters']['visibility'] == 'any'
            page.locator('[data-builder-redo]').click()
            assert review.save()['document']['regions'][0]['filters'] == expected_filters
            records.append({'case': 'authored-and-or-filters-save-with-one-step-undo-redo'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    page.goto(review.builder + '?project=' + authored['id']); wait_ready(page)
                    select_region(region_id)
                    page.wait_for_function("id=>document.querySelector('[data-builder-region-filter=actorIds]')?.selectedOptions[0]?.value===id", arg=actor_id)
                    filter_control('visibility').scroll_into_view_if_needed()
                    metrics = page.locator('#builder-editor-panels').evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'filters-builder-{locale}-{width}.png'))
                    records.append({'case': 'localized-builder-filters-with-long-authored-names', 'locale': locale, 'width': width, 'metrics': metrics})

            change_locale(page, 'en', campaign); page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(review.builder + '?project=' + authored['id']); wait_ready(page); select_region(region_id)
            filter_control('actorIds').select_option([])
            filter_control('dispositions').select_option([])
            filter_control('visibility').select_option('any')
            cleared = review.save()
            assert 'filters' not in cleared['document']['regions'][0]
            records.append({'case': 'clearing-all-filters-restores-legacy-absence'})

            stale = str(uuid4())
            document = deepcopy(cleared['document'])
            document['regions'][0]['filters'] = {**expected_filters, 'tokenIds': [stale]}
            authored = review.store(cleared['id'], cleared['version'], cleared['folderId'], document)
            page.goto(review.builder + '?project=' + authored['id']); wait_ready(page)
            close_panel(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}'); wait_game()
            scene = review.project(authored['id'])['sceneId']
            page.evaluate("scene=>gravewrightRealtime.mapCommand('activate',{mapId:scene})", scene)
            token_result = page.evaluate("a=>gravewrightRealtime.resourceCommand('tokens','place',{mapId:a.scene,actorId:a.actor,gridX:3,gridY:3})", {'scene': scene, 'actor': actor_id})
            token_id = token_result['createdIds'][0]

            def native_region():
                response = page.request.get(f'/api/maps/{scene}/state'); assert response.ok, response.text()
                region, = response.json()['zones']
                return region

            def open_native():
                page.set_viewport_size({'width': 1440, 'height': 900})
                page.wait_for_function('id=>window.gravewrightMaps?.current?.id===id && !!window.gravewrightMaps?.board?.viewport?.()', arg=scene)
                page.locator('.game-menubar__layer').nth(5).click()
                page.locator('[data-dock-tool=select]:visible').first.click()
                region = native_region()
                point = page.evaluate("""geometry=>{
                  const surface=document.querySelector('.game-table__scene-frame').getBoundingClientRect();
                  const view=gravewrightMaps.board.viewport();
                  return [surface.x+view.x+(geometry.x+geometry.width*.08)*view.scale,
                    surface.y+view.y+(geometry.y+geometry.height*.08)*view.scale];
                }""", region['geometry'])
                page.mouse.dblclick(*point)
                editor = page.locator('[data-region-editor]'); expect(editor).to_be_visible()
                editor.locator('[data-region-filters]').evaluate('details=>details.open=true')
                expect(editor.locator(f'[data-region-filter=actorIds] input[value="{actor_id}"]')).to_be_checked()
                return editor

            editor = open_native()
            stale_checkbox = editor.locator(f'[data-region-filter=tokenIds] input[value="{stale}"]')
            expect(stale_checkbox).to_be_checked()
            expect(editor.locator(f'[data-region-filter=tokenIds] input[value="{token_id}"]')).to_be_visible()
            editor.locator('[data-region-filter-visibility]').select_option('hidden')
            editor.locator('[data-cancel]').click()
            assert native_region()['region']['filters']['visibility'] == 'visible'
            records.append({'case': 'native-editor-shows-real-and-missing-targets-and-cancel-keeps-private-draft'})

            editor = open_native()
            editor.locator('[data-region-filter-visibility]').select_option('hidden')
            editor.locator('[type=submit]').click(); expect(editor).to_have_count(0)
            saved = native_region()
            assert saved['region']['filters'] == {**expected_filters, 'tokenIds': [stale], 'visibility': 'hidden'}
            assert 'occupants' not in saved['region']
            before_runs = len(page.request.get(f'/api/maps/{scene}/automation').json()['runs'])
            records.append({'case': 'native-save-preserves-inert-missing-id-and-never-projects-occupants'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                page.goto(f'/game/{campaign}'); wait_game()
                for width in (1440, 390):
                    editor = open_native()
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    editor.locator('[data-region-filter=tokenIds]').scroll_into_view_if_needed()
                    alignment = editor.locator('.region-editor__choices label').evaluate_all("""labels=>labels.map(label=>{
                      const input=label.querySelector('input').getBoundingClientRect(), text=label.querySelector('span').getBoundingClientRect();
                      return {inline:text.left>=input.right, aligned:Math.abs(text.top-input.top)<=4};
                    })""")
                    assert all(row['inline'] and row['aligned'] for row in alignment), alignment
                    metrics = editor.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    assert editor.locator(f'[data-region-filter=actorIds] input[value="{actor_id}"]').locator('..').inner_text() == actor_name
                    page.screenshot(path=str(output / f'filters-native-{locale}-{width}.png'))
                    editor.locator('[data-cancel]').click()
                    records.append({'case': 'localized-native-filters-stay-reachable-on-mobile', 'locale': locale, 'width': width, 'metrics': metrics})
            assert len(page.request.get(f'/api/maps/{scene}/automation').json()['runs']) == before_runs
        except Exception:
            if not page.is_closed(): page.screenshot(path=str(output / 'failure.png'), full_page=True)
            (output / 'progress.json').write_text(json.dumps({'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs}, indent=2), encoding='utf8')
            raise
        finally:
            context.close(); browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Synthetic actors and a private empty map; no operator data.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
