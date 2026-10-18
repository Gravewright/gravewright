"""Verify the canvas-focused Map Builder and its real editing controls.

All state, browser storage, media and server processes belong to a disposable
synthetic campaign. Existing document models and generation remain unchanged.
"""
from __future__ import annotations

from copy import deepcopy

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import layout_metrics, reference_geometry, synthetic_texture, upload_asset, wait_ready


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

        def name():
            return page.locator('[data-builder-quick-name]')

        def same_content(actual, expected):
            before, after = deepcopy(expected), deepcopy(actual)
            before.pop('name'); after.pop('name')
            assert before == after

        def check_name(value):
            expect(name()).to_have_value(value)
            builder_sidebar(page, 'settings')
            expect(page.locator('[data-builder-form] [name=name]')).to_have_value(value)
            builder_workspace(page)
            document = saved()
            assert document['name'] == value, document['name']
            return document

        def header_history(action):
            page.locator(f'.map-builder__header [data-builder-{action}]').click()

        def point(x, y):
            return page.locator('[data-builder-canvas]').evaluate("""(svg,point)=>{
              const p=new DOMPoint(...point).matrixTransform(svg.getScreenCTM());return [p.x,p.y];
            }""", [x, y])

        def click(x, y):
            builder_workspace(page)
            page.mouse.click(*point(x, y))

        def tool_controls():
            builder_sidebar(page, 'tools')
            expect(page.locator('[data-builder-sidebar-panel=tools]')).to_be_visible()

        def layout():
            builder_workspace(page)
            expect(page.locator('.map-builder__tool-rail')).to_have_count(0)
            expect(page.locator('.map-builder__toolbars')).to_have_count(0)
            boxes = page.evaluate("""()=>{
              const box=s=>{const r=document.querySelector(s).getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom,right:r.right};};
              return {header:box('.map-builder__header'),canvas:box('[data-builder-viewport]'),dock:box('[data-builder-assets-panel]')};
            }""")
            assert abs(boxes['canvas']['x']) <= 1, boxes
            assert abs(boxes['canvas']['y'] - boxes['header']['bottom']) <= 1, boxes
            assert abs(boxes['canvas']['right'] - page.viewport_size['width']) <= 1, boxes
            assert abs(boxes['canvas']['bottom'] - boxes['dock']['y']) <= 1, boxes
            assert boxes['canvas']['height'] >= 180, boxes
            controls = page.locator('.map-builder__header').evaluate("""header=>{
              const r=header.getBoundingClientRect();return [...header.querySelectorAll('input,button,a')]
                .filter(el=>el.checkVisibility({checkVisibilityCSS:true})).map(el=>{const b=el.getBoundingClientRect();return {html:el.outerHTML,left:b.left,right:b.right,top:b.top,bottom:b.bottom};})
                .filter(b=>b.left<r.left-1||b.right>r.right+1||b.top<r.top-1||b.bottom>r.bottom+1);
            }""")
            assert not controls, controls
            metrics = page.locator('[data-map-builder]').evaluate(MEASURE)
            assert not metrics['tiny'] and not metrics['overflow'], metrics
            assert metrics['scrollWidth'] <= metrics['viewport'] + 1, metrics

        try:
            page.goto(review.builder); wait_ready(page)
            page.set_viewport_size({'width': 1586, 'height': 992})
            reference_geometry(page); layout_metrics(page)
            page.set_viewport_size({'width': 1440, 'height': 900})
            layout()
            expect(name()).to_have_attribute('maxlength', '120')
            order = page.locator('.map-builder__header').evaluate("""header=>{
              const all=[...header.querySelectorAll('button')];return ['undo','redo','save'].map(key=>all.indexOf(header.querySelector('[data-builder-'+key+']')));
            }""")
            assert -1 not in order and order == sorted(order), order
            name().fill('Synthetic clean layout baseline'); name().press('Enter')
            initial = check_name('Synthetic clean layout baseline')
            stone = upload_asset(page, 'floor', 'Synthetic clean-layout floor.png', synthetic_texture('floor'))['id']
            page.locator('[data-builder-role=floor]').click()
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-tool', 'floor')
            page.locator(f'[data-builder-assets] [data-asset-id="{stone}"]').click()
            tool_controls()
            for selector in ('[data-builder-brush-material]', '[data-builder-paint-mode]', '[data-builder-brush-shape]', '[data-builder-brush=floorSize]', '[data-builder-active-layer-select]', '[data-builder-toggle-snap]'):
                expect(page.locator(selector)).to_be_visible()
                assert page.locator(selector).evaluate('el=>el.closest("[data-builder-sidebar-panel=tools]")!==null')
            page.locator('[data-builder-paint-mode]').select_option('rectangle')
            review.stroke((2, 2), (4, 4))
            baseline = saved()
            assert len(baseline['floors']) == 4
            records.append({'case': 'removed-rail-and-toolbar-release-canvas-and-real-floor-options-live-in-Tools'})

            name().fill('Confirmed by Enter'); name().press('Enter')
            renamed = check_name('Confirmed by Enter'); same_content(renamed, baseline)
            header_history('undo'); restored = check_name(baseline['name']); same_content(restored, baseline)
            header_history('redo'); check_name('Confirmed by Enter')
            name().fill('Confirmed by blur')
            page.locator('.map-builder__identity h1').click()
            check_name('Confirmed by blur')
            header_history('undo'); check_name('Confirmed by Enter')
            header_history('redo'); check_name('Confirmed by blur')
            records.append({'case': 'header-name-Enter-and-blur-sync-Settings-and-saved-project-with-one-history-step-each'})

            name().fill('Confirmed by Ctrl+S')
            with page.expect_response(lambda response: response.request.method == 'POST' and '/map-builder/projects/' in response.url
                                      and not response.url.endswith(('/generate', '/update'))) as persisted:
                name().press('Control+s')
            assert persisted.value.ok, persisted.value.text()
            assert persisted.value.json()['project']['document']['name'] == 'Confirmed by Ctrl+S'
            committed = check_name('Confirmed by Ctrl+S'); same_content(committed, baseline)
            header_history('undo'); check_name('Confirmed by blur')
            header_history('redo'); check_name('Confirmed by Ctrl+S')
            page.reload(); wait_ready(page); check_name('Confirmed by Ctrl+S')
            records.append({'case': 'Ctrl+S-commits-focused-header-name-once-and-reload-keeps-it'})

            builder_tool(page, 'floor')
            page.locator('[data-builder-paint-mode]').select_option('brush')
            click(8.5, 8.5)
            count = page.locator('[data-builder-floors] [data-object-id]').count()
            assert count == 5, count
            name().fill('Unconfirmed name cancelled with Escape'); name().press('Escape')
            expect(name()).to_have_value('Confirmed by Ctrl+S')
            assert page.locator('[data-builder-floors] [data-object-id]').count() == count
            header_history('undo')
            assert saved()['name'] == 'Confirmed by Ctrl+S' and len(saved()['floors']) == 4
            header_history('redo'); dirty_content = saved()
            assert len(dirty_content['floors']) == 5
            records.append({'case': 'Escape-cancels-only-header-name-draft-without-losing-drawing-or-adding-history'})

            # Library categories now select the matching drawing tool themselves.
            for role, tool in (('wall', 'wall'), ('door', 'door'), ('decoration', 'decoration'), ('light', 'light'), ('floor', 'floor')):
                page.locator(f'[data-builder-role={role}]').click()
                expect(page.locator('[data-map-builder]')).to_have_attribute('data-tool', tool)
            page.locator('[data-builder-role=light]').click()
            page.locator('[data-builder-light-preset=torch]').click(); click(15, 8)
            expect(page.locator('[data-builder-native-preview] canvas')).to_have_count(1)
            native_source = saved()
            assert len(native_source['lights']) == 1 and native_source['lights'][0]['animation'] == 'torch'
            page.locator('[data-builder-role=effect]').click()
            page.locator('[data-builder-collection-filter]').select_option('particle')
            page.locator('[data-builder-particle-preset=smoke]').click()
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-tool', 'particle')
            builder_tool(page, 'pan'); builder_tool(page, 'erase'); builder_tool(page, 'select')
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-tool', 'select')
            builder_workspace(page)
            records.append({'case': 'library-types-arm-correct-tools-and-native-light-and-panel-utility-tools-still-work'})

            page.locator('[data-builder-preview]').click()
            expect(name()).to_be_disabled()
            expect(page.locator('[data-builder-undo]')).to_be_disabled()
            expect(page.locator('[data-builder-redo]')).to_be_disabled()
            tool_controls()
            expect(page.locator('[data-builder-tool=floor]')).to_be_disabled()
            expect(page.locator('[data-builder-paint-mode]')).to_be_disabled()
            builder_workspace(page)
            page.screenshot(path=str(output / 'clean-layout-preview.png'))
            page.locator('[data-builder-preview]').click()
            expect(name()).to_be_enabled()
            assert saved() == native_source
            records.append({'case': 'Preview-disables-header-editing-history-and-Tools-without-changing-content'})

            long_name = 'Synthetic long authored map name - ' + '0123456789' * 10
            long_name = long_name[:120]
            name().fill(long_name); name().press('Enter')
            project = review.save()
            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 1024, 390, 320):
                    page.set_viewport_size({'width': width, 'height': 900 if width >= 1000 else 844})
                    page.reload(); wait_ready(page)
                    layout()
                    expect(name()).to_have_value(long_name)
                    expect(name()).to_have_attribute('aria-label', {'en': 'Map name', 'pt-BR': 'Nome do mapa', 'es': 'Nombre del mapa'}[locale])
                    page.screenshot(path=str(output / f'clean-layout-{locale}-{width}.png'))
                    tool_controls()
                    expect(page.locator('[data-builder-sidebar-tab=tools][role=tab]')).to_have_text({'en': 'Tools', 'pt-BR': 'Ferramentas', 'es': 'Herramientas'}[locale])
                    metrics = page.locator('[data-map-builder]').evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], (locale, width, metrics)
                    page.screenshot(path=str(output / f'clean-layout-tools-{locale}-{width}.png'))
                    builder_workspace(page)
                    assert saved() == project['document']
                    records.append({'case': 'responsive-localized-header-and-Tools-retain-long-authored-name', 'locale': locale, 'width': width})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close(); browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Synthetic floor texture and native Torch preset in a disposable campaign.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
