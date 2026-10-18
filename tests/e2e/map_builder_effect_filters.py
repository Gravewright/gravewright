"""Filter native effects without changing saved map content or collections.

Uses synthetic imports, a disposable campaign and the real placement controls.
The only delayed request is an owned save used to inspect the busy state.
"""
from __future__ import annotations

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import set_name, wait_ready


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    records, errors, dialogs = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        review = BuilderReview(page, seed['campaign'])
        selector = page.locator('[data-builder-collection-filter]')
        root = page.locator('[data-map-builder]')
        search = page.locator('[data-builder-search]')

        def role(value):
            builder_sidebar(page, 'library')
            page.locator(f'[data-builder-role={value}]').click()

        def effect(tool):
            role('effect')
            selector.select_option(tool)
            expect(root).to_have_attribute('data-tool', tool)
            own, other = ('particle', 'shader') if tool == 'particle' else ('shader', 'particle')
            assert page.locator(f'[data-builder-{own}-preset]').count() > 0
            expect(page.locator(f'[data-builder-{other}-preset]')).to_have_count(0)

        def place(x, y):
            builder_workspace(page)
            position = page.locator('[data-builder-canvas]').evaluate("""(svg,point)=>{
              const p=new DOMPoint(...point).matrixTransform(svg.getScreenCTM());return [p.x,p.y];
            }""", [x, y])
            page.mouse.click(*position)

        def import_floor(collection, color):
            page.locator('[data-builder-import]').click()
            modal = page.locator('[data-builder-import-modal]')
            modal.locator('[data-builder-import-role]').select_option('floor')
            modal.locator('[data-builder-import-collection]').fill(collection)
            modal.locator('[data-builder-upload]').set_input_files({
                'name': f'Synthetic {collection} collection floor.png', 'mimeType': 'image/png',
                'buffer': harness.artwork(color),
            })
            with page.expect_response(lambda response: '/library/upload' in response.url) as uploaded:
                modal.locator('[data-builder-import-submit]').click()
            assert uploaded.value.status == 201, uploaded.value.text()
            expect(modal).to_have_count(0)
            return uploaded.value.json()['id']

        def asset_ids():
            return page.locator('[data-builder-assets] [data-asset-id]').evaluate_all(
                'cards=>cards.map(card=>card.dataset.assetId)')

        def unchanged(project):
            current = review.save()
            assert current['document'] == project['document']
            assert current['version'] == project['version']
            return current

        def screen(locale, width, tool):
            effect(tool)
            expected = {'en': ('Effect type', 'Particles'), 'pt-BR': ('Tipo de efeito', 'Partículas'),
                        'es': ('Tipo de efecto', 'Partículas')}[locale]
            expect(selector).to_have_attribute('aria-label', expected[0])
            assert selector.locator('option').evaluate_all('options=>options.map(option=>[option.value,option.text])') == [
                ['particle', expected[1]], ['shader', 'Shaders']]
            selector.scroll_into_view_if_needed()
            expect(selector).to_be_in_viewport()
            metrics = root.evaluate(MEASURE)
            assert not metrics['tiny'] and not metrics['overflow'], (locale, width, metrics)
            assert metrics['scrollWidth'] <= width, metrics
            page.screenshot(path=str(output / f'effect-filter-{locale}-{width}-{tool}.png'))
            records.append({'case': 'localized-effect-filter-and-single-catalog-fit', 'locale': locale,
                            'width': width, 'tool': tool, 'metrics': metrics})

        try:
            page.goto(review.builder); wait_ready(page)
            set_name(page, 'Synthetic native effect filters and collection name collisions')
            particle_floor = import_floor('particle', '#67824f')
            shader_floor = import_floor('shader', '#775394')
            baseline = review.save()
            role('floor'); selector.select_option('particle')
            assert asset_ids() == [particle_floor]
            effect('shader')
            role('floor'); expect(selector).to_have_value('particle')
            assert asset_ids() == [particle_floor]
            selector.select_option('shader')
            assert asset_ids() == [shader_floor]
            role('effect'); expect(selector).to_have_value('shader')
            role('wall'); expect(selector).to_have_value('shader')
            role('floor'); expect(selector).to_have_value('shader')
            assert asset_ids() == [shader_floor]
            unchanged(baseline)
            records.append({'case': 'effect-subtype-is-independent-from-authored-particle-and-shader-collection-names'})

            effect('particle')
            search.fill('Smoke')
            expect(page.locator('[data-builder-particle-preset=smoke]')).to_be_visible()
            expect(page.locator('[data-builder-shader-preset]')).to_have_count(0)
            selector.select_option('shader')
            expect(root).to_have_attribute('data-tool', 'shader')
            expect(page.locator('[data-builder-particle-preset]')).to_have_count(0)
            search.fill('Arcane Sun')
            expect(page.locator('[data-builder-shader-preset=orb-1]')).to_be_visible()
            search.fill('missing synthetic native preset')
            expect(page.locator('[data-builder-assets-empty]')).to_be_visible()
            expect(page.locator('[data-builder-particle-preset], [data-builder-shader-preset]')).to_have_count(0)
            search.fill('')
            unchanged(baseline)
            records.append({'case': 'search-filters-only-the-selected-native-effect-catalog-without-source-or-version-changes'})

            role('light'); page.locator('[data-builder-light-preset=torch]').click()
            effect('particle'); page.locator('[data-builder-particle-preset=rain]').click()
            effect('shader'); page.locator('[data-builder-shader-preset=orb-1]').click()
            effect('particle')
            expect(page.locator('[data-builder-particle-preset=rain]')).to_have_attribute('aria-pressed', 'true')
            builder_tool(page, 'shader')
            expect(selector).to_have_value('shader')
            expect(page.locator('[data-builder-native-preset]')).to_have_value('orb-1')
            builder_tool(page, 'particle')
            expect(selector).to_have_value('particle')
            expect(page.locator('[data-builder-native-preset]')).to_have_value('rain')
            role('light')
            expect(page.locator('[data-builder-light-preset=torch]')).to_have_attribute('aria-pressed', 'true')
            unchanged(baseline)
            records.append({'case': 'tool-drawer-and-effect-filter-sync-with-independent-light-particle-and-shader-preset-choices'})

            effect('particle'); place(8, 8)
            expect(page.locator('[data-builder-particles] [data-object-id]')).to_have_count(1)
            effect('shader'); effect('particle')
            page.locator('[data-builder-undo]').click()
            assert review.save()['document'] == baseline['document']
            page.locator('[data-builder-redo]').click()
            particle_project = review.save()
            assert len(particle_project['document'].get('particles', [])) == 1
            assert particle_project['document']['particles'][0]['kind'] == 'rain'
            assert not particle_project['document'].get('shaders')
            effect('shader'); place(18, 10)
            effect('particle'); effect('shader')
            page.locator('[data-builder-undo]').click()
            assert review.save()['document'] == particle_project['document']
            page.locator('[data-builder-redo]').click()
            project = review.save()
            assert len(project['document']['particles']) == len(project['document']['shaders']) == 1
            assert not any(project['document'].get(kind) for kind in ('floors', 'walls', 'doors', 'decorations', 'lights'))
            records.append({'case': 'each-filter-places-only-its-remembered-preset-and-filter-changes-create-no-undo-steps'})

            effect('shader')
            page.locator('[data-builder-preview]').click()
            expect(selector).to_be_disabled()
            expect(page.locator('[data-builder-shader-preset=orb-1]')).to_be_disabled()
            page.locator('[data-builder-preview]').click()
            expect(selector).to_be_enabled()
            unchanged(project)
            pending = []
            page.route('**/map-builder/projects/*', lambda route: pending.append(route), times=1)
            set_name(page, 'Synthetic effect filters while saving')
            page.locator('[data-builder-save]').click()
            expect(selector).to_be_disabled()
            assert len(pending) == 1
            with page.expect_response(lambda response: response.request.method == 'POST' and '/map-builder/projects/' in response.url):
                pending[0].continue_()
            expect(selector).to_be_enabled()
            project = review.save()
            records.append({'case': 'effect-selector-and-presets-are-disabled-in-preview-and-while-save-is-pending'})

            page.reload(); wait_ready(page)
            assert review.save()['document'] == project['document']
            effect('particle'); expect(page.locator('[data-builder-particles] [data-object-id]')).to_have_count(1)
            effect('shader'); expect(page.locator('[data-builder-shaders] [data-object-id]')).to_have_count(1)
            unchanged(project)
            records.append({'case': 'save-and-reopen-preserve-exact-native-source-without-inserting-extra-effects'})

            for locale, width in (('pt-BR', 1440), ('pt-BR', 390), ('es', 390), ('en', 1440)):
                page.set_viewport_size({'width': width, 'height': 900 if width > 500 else 844})
                change_locale(page, locale, seed['campaign'])
                page.reload(); wait_ready(page)
                screen(locale, width, 'particle')
                screen(locale, width, 'shader')
                unchanged(project)
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close(); browser.close()
    assert not errors and not dialogs, {'pageErrors': errors, 'nativeDialogs': dialogs}
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Two synthetic solid PNGs in collections named particle and shader.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
