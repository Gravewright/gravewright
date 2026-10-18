"""Exercise real header selection, painting, brush sizing and object erasure.

The shared fixture isolates campaigns, media, runtime caches and result files.
The scenario uses actual pointers and saved documents rather than setting UI
controller state or manufacturing selection events.
"""
from __future__ import annotations

from copy import deepcopy

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import layout_metrics, synthetic_texture, upload_asset, wait_ready


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
        size = page.locator('[data-builder-quick-brush-size]')
        quick_name = page.locator('[data-builder-quick-name]')

        def quick(tool):
            page.locator(f'[data-builder-quick-tool={tool}]').click()
            expect(page.locator('[data-builder-close-panel]')).to_be_hidden()
            expect(page.locator('[data-builder-viewport]')).to_be_focused()
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-tool', 'floor' if tool == 'paint' else tool)

        def tools():
            builder_sidebar(page, 'tools')

        def saved():
            return review.save()['document']

        def change_size(value):
            size.fill(str(value)); size.press('Enter')
            expect(page.locator('[data-builder-viewport]')).to_be_focused()
            expect(size).to_have_value(str(value))

        def point(x, y):
            return page.locator('[data-builder-canvas]').evaluate("""(svg,point)=>{
              const p=new DOMPoint(...point).matrixTransform(svg.getScreenCTM());return [p.x,p.y];
            }""", [x, y])

        def click(x, y, modifiers=()):
            builder_workspace(page)
            for key in modifiers:
                page.keyboard.down(key)
            page.mouse.click(*point(x, y))
            for key in reversed(modifiers):
                page.keyboard.up(key)

        def area(document):
            return sum(row['width'] * row['height'] for row in document['floors'])

        def undo():
            page.locator('[data-builder-undo]').click()

        def redo():
            page.locator('[data-builder-redo]').click()

        def selected(count):
            expect(page.locator('[data-builder-selection] > *')).to_have_count(count)

        def source_after_name(document, value):
            expected = deepcopy(document); expected['name'] = value
            assert saved() == expected

        try:
            page.goto(review.builder); wait_ready(page)
            for tool in ('select', 'paint', 'erase'):
                button = page.locator(f'[data-builder-quick-tool={tool}]')
                expect(button).to_have_count(1)
                assert button.evaluate('el=>el.closest(".map-builder__header")!==null')
            expect(size).to_have_count(1)
            quick_name.fill('Synthetic header drawing tools'); quick_name.press('Enter')
            stone = upload_asset(page, 'floor', 'Synthetic header floor.png', synthetic_texture('floor'))['id']
            tools()
            page.locator('[data-builder-tool=floor]').click()
            page.locator('[data-builder-brush-material]').select_option(stone)
            page.locator('[data-builder-paint-mode]').select_option('rectangle')
            page.locator('[data-builder-paint-operation]').select_option('erase')
            quick('paint')
            expect(page.locator('[data-builder-quick-tool=paint]')).to_have_attribute('aria-pressed', 'true')
            tools()
            expect(page.locator('[data-builder-paint-mode]')).to_have_value('brush')
            expect(page.locator('[data-builder-paint-operation]')).to_have_value('paint')
            expect(page.locator('[data-builder-brush-material]')).to_have_value(stone)
            quick('paint'); change_size(1)
            click(3.25, 3.25); one = saved()
            assert len(one['floors']) == 1 and area(one) == 1 and one['floors'][0]['assetId'] == stone
            click(6.25, 3.25); baseline = saved()
            assert len(baseline['floors']) == 2 and area(baseline) == 2
            records.append({'case': 'header-Paint-closes-panel-forces-freehand-paint-preserves-material-and-size-one-paints-real-cell'})

            quick('select')
            expect(size).to_be_disabled()
            click(3.5, 3.5); selected(1)
            click(6.5, 3.5, ('Shift',)); selected(2)
            click(6.5, 3.5, ('Shift',)); selected(1)
            review.stroke((2.7, 2.7), (7.2, 4.2)); selected(2)
            quick('select'); selected(2)
            review.stroke((3.5, 3.5), (4.5, 4.5))
            moved = saved()
            for old in baseline['floors']:
                current = next(row for row in moved['floors'] if row['id'] == old['id'])
                assert current['x'] == old['x'] + 1 and current['y'] == old['y'] + 1
            undo(); assert saved() == baseline
            records.append({'case': 'header-Select-keeps-selection-and-supports-real-Shift-toggle-marquee-and-group-move-with-one-undo'})

            quick('paint'); change_size(3)
            click(10.25, 4.25); large = saved()
            new_tiles = [row for row in large['floors'] if row['id'] not in {item['id'] for item in baseline['floors']}]
            assert len(new_tiles) == 9 and area(large) - area(baseline) == 9
            assert all(row['assetId'] == stone for row in new_tiles)
            assert max(row['x'] + row['width'] for row in new_tiles) - min(row['x'] for row in new_tiles) == 3
            assert max(row['y'] + row['height'] for row in new_tiles) - min(row['y'] for row in new_tiles) == 3
            undo(); assert saved() == baseline
            redo(); assert saved() == large
            tools()
            field = page.locator('[data-builder-brush=floorSize]')
            expect(field).to_have_value('3')
            field.fill('4'); field.dispatch_event('change')
            expect(size).to_have_value('4')
            quick('paint')
            page.keyboard.press('['); expect(size).to_have_value('3')
            page.keyboard.press(']'); expect(size).to_have_value('4')
            tools(); expect(field).to_have_value('4')
            records.append({'case': 'header-size-three-paints-nine-cells-and-Tools-size-and-bracket-shortcuts-mirror-the-same-brush'})

            if page.locator('[data-builder-toggle-snap]').get_attribute('aria-pressed') == 'true':
                page.locator('[data-builder-toggle-snap]').click()
            page.locator('[data-builder-brush-shape]').select_option('circle')
            quick('paint'); change_size(2.5)
            assert float(size.get_attribute('min')) == .05
            assert float(size.get_attribute('step')) == .05
            review.stroke((15.25, 14.4), (18.6, 15.2))
            free = saved()
            added = [row for row in free['floors'] if row['id'] not in {item['id'] for item in large['floors']}]
            assert len(added) == 1 and added[0]['shape']['contours']
            assert abs(added[0]['x'] - 14) <= .003 and abs(added[0]['y'] - 13.15) <= .003, added[0]
            assert abs(added[0]['width'] - 5.85) <= .003 and abs(added[0]['height'] - 3.3) <= .003, added[0]
            tools(); expect(field).to_have_value('2.5')
            page.locator('[data-builder-toggle-snap]').click()
            expect(size).to_have_value('3')
            expect(field).to_have_value('3')
            quick('paint')
            records.append({'case': 'snap-off-header-fractional-size-produces-continuous-round-geometry-and-snap-on-normalizes-both-controls'})

            quick('erase')
            expect(size).to_be_disabled()
            expect(page.locator('[data-builder-quick-tool=erase]')).to_have_attribute('aria-pressed', 'true')
            target = baseline['floors'][0]
            click(target['x'] + .5, target['y'] + .5)
            erased = saved()
            assert all(row['id'] != target['id'] for row in erased['floors'])
            assert len(erased['floors']) == len(free['floors']) - 1
            undo(); assert saved() == free
            records.append({'case': 'header-Erase-removes-hit-object-and-one-undo-restores-it-without-area-erasure'})

            quick('paint')
            quick_name.fill('Header quick tools preserve name and history'); quick_name.press('Enter')
            source_after_name(free, 'Header quick tools preserve name and history')
            undo(); assert saved() == free
            redo(); renamed = saved()
            assert renamed['name'] == 'Header quick tools preserve name and history'
            pending = []

            def hold_save(route):
                if route.request.method == 'POST' and not route.request.url.endswith(('/generate', '/update')):
                    pending.append(route)
                else:
                    route.continue_()

            quick_name.fill('Busy header controls resume after Save'); quick_name.press('Enter')
            page.route('**/map-builder/projects/*', hold_save)
            with page.expect_request(lambda request: request.method == 'POST' and '/map-builder/projects/' in request.url):
                page.locator('[data-builder-save]').click()
            expect(page.locator('[data-map-builder]')).to_have_attribute('aria-busy', 'true')
            for selector in ('[data-builder-quick-tool]', '[data-builder-quick-brush-size]', '[data-builder-quick-name]'):
                for control in page.locator(selector).all():
                    expect(control).to_be_disabled()
            assert len(pending) == 1, len(pending)
            pending.pop().continue_()
            wait_ready(page)
            page.unroute('**/map-builder/projects/*', hold_save)
            expect(size).to_be_enabled()
            page.locator('[data-builder-preview]').click()
            for control in page.locator('[data-builder-quick-tool],[data-builder-quick-brush-size],[data-builder-quick-name],[data-builder-undo],[data-builder-redo]').all():
                expect(control).to_be_disabled()
            page.locator('[data-builder-preview]').click()
            expect(size).to_be_enabled()
            expect(quick_name).to_be_enabled()
            project = review.save()
            records.append({'case': 'header-name-history-and-real-Save-busy-Preview-readonly-remain-consistent-with-quick-tools'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 1024, 390, 320):
                    page.set_viewport_size({'width': width, 'height': 900 if width >= 1000 else 844})
                    page.reload(); wait_ready(page)
                    quick('paint')
                    layout_metrics(page)
                    bounds = page.locator('.map-builder__header').bounding_box()
                    for control in page.locator('[data-builder-quick-tool],[data-builder-quick-brush-size]').all():
                        box = control.bounding_box()
                        assert box['width'] >= 24 and box['height'] >= 28, box
                        assert bounds['x'] <= box['x'] and box['x'] + box['width'] <= bounds['x'] + bounds['width'] + 1, box
                        assert bounds['y'] <= box['y'] and box['y'] + box['height'] <= bounds['y'] + bounds['height'] + 1, box
                    metrics = page.locator('[data-map-builder]').evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], (locale, width, metrics)
                    expect(page.locator('[data-builder-quick-tool=paint]')).to_have_attribute('aria-label', {'en': 'Paint', 'pt-BR': 'Pintar', 'es': 'Pintar'}[locale])
                    page.screenshot(path=str(output / f'header-tools-{locale}-{width}.png'))
                    quick('select'); expect(size).to_be_disabled()
                    quick('erase'); expect(size).to_be_disabled()
                    assert saved() == project['document']
                    records.append({'case': 'responsive-localized-functional-header-tools', 'locale': locale, 'width': width})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close(); browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Synthetic floor texture in a disposable campaign.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
