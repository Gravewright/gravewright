"""Review the Map Builder's editor panels using isolated synthetic map data.

Real controls exercise panel navigation, painting, selection and native catalogs.
No operator campaign, storage, installed package or running server is reused.
"""
from __future__ import annotations

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import create_layer, set_name, synthetic_texture, upload_asset, wait_ready


TABS = ('tools', 'layers', 'selection', 'settings', 'projects', 'review')


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
        root = page.locator('[data-map-builder]')
        drawer = page.locator('[data-builder-region=library]')
        tabs = drawer.locator('[data-builder-sidebar-tab][role=tab]')
        size = page.locator('[data-builder-quick-brush-size]')

        def tab(name):
            return drawer.locator(f'[data-builder-sidebar-tab={name}][role=tab]')

        def point(x, y):
            return page.locator('[data-builder-canvas]').evaluate("""(svg,p)=>{
              const result=new DOMPoint(...p).matrixTransform(svg.getScreenCTM());
              return [result.x,result.y];
            }""", [x, y])

        def click(x, y):
            builder_workspace(page)
            page.mouse.click(*point(x, y))

        def field(selector, value):
            control = page.locator(selector)
            control.scroll_into_view_if_needed()
            if control.evaluate('el=>el.tagName') == 'SELECT':
                control.select_option(str(value))
            else:
                control.fill(str(value)); control.dispatch_event('change')

        def unchanged(project):
            # Navigation and brush settings can briefly schedule autosave before
            # it recognizes an unchanged document. A no-op has no POST response.
            expect(root).to_have_attribute('data-save-state', 'saved')
            current = review.project(project['id'])
            assert current['document'] == project['document']
            assert current['version'] == project['version']

        def active_tab(name):
            target = tab(name)
            expect(target).to_have_attribute('aria-selected', 'true')
            expect(target).to_have_attribute('tabindex', '0')
            expect(drawer.locator('[data-builder-sidebar-tab][role=tab][aria-selected=true]')).to_have_count(1)
            panel = drawer.locator(f'[data-builder-sidebar-panel={name}]')
            expect(panel).to_be_visible()
            expect(panel).to_have_attribute('role', 'tabpanel')
            expect(panel).to_have_attribute('aria-labelledby', target.get_attribute('id'))
            expect(target).to_have_attribute('aria-controls', panel.get_attribute('id'))
            expect(drawer.locator('[data-builder-sidebar-panel]:visible')).to_have_count(1)

        def resize_preview(mode):
            builder_workspace(page)
            page.locator('[data-builder-editing-mode]').select_option(mode)
            page.locator('[data-builder-quick-tool=paint]').click()
            size.fill('2'); size.press('Enter')
            project = review.save()
            start = point(20.5, 14.5)
            page.mouse.move(*start); page.keyboard.down('Shift'); page.mouse.down()
            page.mouse.move(start[0] + 40, start[1], steps=4)
            expect(size).to_have_value('3')
            expect(page.locator('[data-builder-resize-preview]')).to_have_count(1)
            page.mouse.up(); page.keyboard.up('Shift')
            expect(page.locator('[data-builder-resize-preview]')).to_have_count(0)
            builder_sidebar(page, 'tools')
            expect(page.locator('[data-builder-brush=floorSize]')).to_have_value('3')
            unchanged(project)

        def layout(locale, width, capture):
            page.set_viewport_size({'width': width, 'height': 900 if width > 500 else 844})
            change_locale(page, locale, seed['campaign'])
            page.reload(); wait_ready(page)
            builder_tool(page, 'floor')
            field('[data-builder-brush-material]', material)
            measurements = {}
            for name in TABS:
                if name == 'selection':
                    builder_workspace(page)
                    page.locator('[data-builder-quick-tool=select]').click(); click(3.5, 3.5)
                builder_sidebar(page, name); active_tab(name)
                page.locator('.map-builder__sidebar-content').evaluate('el=>{el.scrollTop=0;}')
                visible_tabs = tabs.evaluate_all("""buttons=>buttons.map(button=>{
                  const r=button.getBoundingClientRect(),p=button.parentElement.getBoundingClientRect();
                  const range=document.createRange();range.selectNodeContents(button.querySelector('span'));
                  return {name:button.dataset.builderSidebarTab,visible:button.checkVisibility(),
                    labelLines:range.getClientRects().length,
                    fits:r.left>=p.left-1&&r.right<=p.right+1&&r.top>=p.top-1&&r.bottom<=p.bottom+1};
                })""")
                assert all(item['visible'] and item['fits'] and item['labelLines'] == 1 for item in visible_tabs), visible_tabs
                metrics = root.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, width, name, metrics)
                assert metrics['scrollWidth'] <= width, metrics
                measurements[name] = metrics
                if name in capture:
                    page.screenshot(path=str(output / f'editor-panels-{locale}-{width}-{name}.png'))
            unchanged(baseline)
            records.append({'case': 'all-six-localized-panels-fit-with-long-authored-content',
                            'locale': locale, 'width': width, 'metrics': measurements})

        try:
            page.goto(review.builder); wait_ready(page)
            builder_sidebar(page, 'projects')
            expect(page.locator('[data-builder-projects-empty]')).to_be_visible()
            builder_sidebar(page, 'selection')
            expect(page.locator('[data-builder-properties] input')).to_have_count(0)
            page.locator('[data-builder-select-on-map]').click()
            expect(drawer).to_be_hidden(); expect(root).to_have_attribute('data-tool', 'select')
            builder_sidebar(page, 'layers')
            expect(page.locator('[data-builder-project-layer]')).to_have_count(1)
            page.locator('[data-builder-layer-remove]').click()
            expect(page.locator('[data-builder-layers-empty]')).to_be_visible()
            expect(page.locator('[data-builder-create-first-layer]')).to_be_visible()
            first_layer = create_layer(page, 'Synthetic ground layer with a deliberately long authored name')
            expect(page.locator('[data-builder-project-layer]')).to_have_count(1)
            records.append({'case': 'empty-project-selection-and-layer-states-retain-working-create-actions'})

            set_name(page, 'Synthetic ancient underground workshop — a deliberately long map name for editor panel review')
            material = upload_asset(page, 'floor', 'Synthetic mossy floor with a deliberately long image name.png', synthetic_texture('floor'))['id']
            for number in range(3):
                create_layer(page, f'Synthetic layer {number + 2} — long named decorative effects and architectural details')
            builder_sidebar(page, 'layers')
            page.locator(f'[data-builder-layer-active="{first_layer}"]').click()
            builder_tool(page, 'floor')
            field('[data-builder-brush-material]', material)
            field('[data-builder-brush=floorSize]', 1)
            click(3.5, 3.5)
            baseline = review.save()
            assert len(baseline['document']['floors']) == 1
            assert baseline['document']['floors'][0]['assetId'] == material
            builder_sidebar(page, 'layers')
            tabs.first.focus()
            for name in TABS:
                if name != 'tools':
                    page.keyboard.press('ArrowRight')
                else:
                    page.keyboard.press('Home')
                active_tab(name)
                expect(tab(name)).to_be_focused()
            page.keyboard.press('Home'); active_tab('tools')
            page.keyboard.press('ArrowDown'); active_tab('settings')
            page.keyboard.press('ArrowUp'); active_tab('tools')
            page.keyboard.press('ArrowLeft'); active_tab('review')
            page.keyboard.press('End'); active_tab('review')
            tab('review').click()
            active_tab('review'); expect(drawer).to_be_visible()
            expect(page.locator('[data-builder-panel-context]')).to_have_text(baseline['document']['name'])
            unchanged(baseline)
            records.append({'case': 'six-tabs-have-linked-panels-single-tab-stop-and-keyboard-navigation-without-source-changes'})

            builder_sidebar(page, 'layers')
            scrolling = page.locator('.map-builder__sidebar-content')
            bottom = scrolling.evaluate('el=>{el.scrollTop=el.scrollHeight;return el.scrollTop;}')
            assert bottom > 0
            builder_sidebar(page, 'review')
            assert scrolling.evaluate('el=>el.scrollTop') == 0
            builder_sidebar(page, 'layers')
            assert abs(scrolling.evaluate('el=>el.scrollTop') - bottom) < 2
            unchanged(baseline)
            records.append({'case': 'each-panel-restores-its-own-scroll-position-under-fixed-heading-and-tabs'})

            builder_workspace(page)
            trigger = page.locator('.map-builder__layers-toggle')
            trigger.focus(); trigger.press('Enter')
            expect(drawer).to_be_visible()
            assert trigger.evaluate('el=>el.inert')
            page.locator('[data-builder-close-panel]').click()
            expect(drawer).to_be_hidden(); expect(trigger).to_be_focused()
            assert not trigger.evaluate('el=>el.inert')
            trigger.press('Enter'); builder_sidebar(page, 'settings')
            expect(trigger).to_have_attribute('aria-expanded', 'true')
            assert trigger.evaluate('el=>el.inert')
            tab('settings').focus(); page.keyboard.press('Escape')
            expect(drawer).to_be_hidden(); expect(trigger).to_be_focused()
            assert not trigger.evaluate('el=>el.inert')
            expect(trigger).to_have_attribute('aria-expanded', 'false')
            expect(page.locator('.map-builder__asset-dock')).to_be_visible()
            unchanged(baseline)
            records.append({'case': 'closing-panels-restores-trigger-focus-and-keeps-bottom-library-accessible'})

            page.locator('[data-builder-quick-tool=select]').click(); click(3.5, 3.5)
            builder_sidebar(page, 'selection')
            expect(page.locator('[data-builder-property=x]')).to_have_value('3')
            field('[data-builder-property=x]', 4)
            changed = review.save()
            assert changed['document']['floors'][0]['x'] == 4
            assert changed['document']['floors'][0]['id'] == baseline['document']['floors'][0]['id']
            page.locator('[data-builder-undo]').click()
            baseline = review.save()
            assert baseline['document']['floors'][0]['x'] == 3
            builder_workspace(page)
            trigger.focus(); trigger.press('Enter'); builder_sidebar(page, 'selection')
            tab('selection').focus()
            page.keyboard.press('Escape')
            expect(drawer).to_be_hidden(); expect(trigger).to_be_focused()
            expect(page.locator('[data-builder-selection] > *')).to_have_count(1)
            unchanged(baseline)
            records.append({'case': 'selection-panel-edits-real-object-properties-with-preserved-identity-and-undo'})

            resize_preview('tiles')
            records.append({'case': 'Tiles-brush-controls-stay-synchronized-with-Shift-drag-preview-without-map-edits'})
            resize_preview('paint')
            builder_sidebar(page, 'tools')
            expect(page.locator('[data-builder-terrain-controls]')).to_be_visible()
            expect(page.locator('[data-builder-tile-tools]')).to_be_hidden()
            field('[data-builder-terrain-hardness]', 25)
            field('[data-builder-terrain-intensity]', 60)
            field('[data-builder-brush-material]', material)
            click(15.25, 13.75)
            baseline = review.save()
            assert len(baseline['document']['floors']) == 2
            brush = baseline['document']['floors'][-1]['brush']
            assert brush['hardness'] == .25 and brush['operation'] == 'paint'
            assert all(point[2] == .6 for point in brush['points'])
            records.append({'case': 'Painting-panel-exposes-active-brush-controls-and-commits-real-soft-stroke'})

            builder_sidebar(page, 'library')
            page.locator('[data-builder-role=effect]').click()
            page.locator('[data-builder-collection-filter]').select_option('shader')
            expect(root).to_have_attribute('data-tool', 'shader')
            expect(page.locator('[data-builder-particle-preset]')).to_have_count(0)
            assert page.locator('[data-builder-shader-preset]').count() > 0
            builder_sidebar(page, 'tools')
            expect(page.locator('[data-builder-native-brush]')).to_be_visible()
            builder_sidebar(page, 'review'); builder_sidebar(page, 'library')
            expect(page.locator('[data-builder-collection-filter]')).to_have_value('shader')
            unchanged(baseline)
            records.append({'case': 'panel-navigation-retains-native-effect-catalog-and-active-preset-without-source-changes'})

            builder_tool(page, 'floor')
            page.locator('[data-builder-preview]').click()
            builder_sidebar(page, 'tools')
            expect(page.locator('[data-builder-brush=floorSize]')).to_be_disabled()
            expect(page.locator('[data-builder-terrain-hardness]')).to_be_disabled()
            expect(page.locator('[data-builder-terrain-intensity]')).to_be_disabled()
            builder_sidebar(page, 'selection')
            for control in page.locator('[data-builder-properties] input, [data-builder-properties] select').all():
                expect(control).to_be_disabled()
            page.locator('[data-builder-preview]').click()
            unchanged(baseline)
            records.append({'case': 'Preview-retains-navigation-and-pauses-panel-editing-controls'})

            for locale, width, capture in (
                ('pt-BR', 1440, ('tools', 'layers', 'selection', 'projects', 'review')),
                ('en', 1440, ('tools',)),
                ('pt-BR', 390, ('tools', 'layers', 'selection')),
                ('es', 390, ('tools',)),
                ('pt-BR', 320, ('tools', 'layers')),
                ('es', 320, ('review',)),
            ):
                layout(locale, width, capture)
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close(); browser.close()
    assert not errors and not dialogs, {'pageErrors': errors, 'nativeDialogs': dialogs}
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'One synthetic floor PNG; long authored map, image and layer names.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
