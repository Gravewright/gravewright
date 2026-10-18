"""Check authored door pivots and opening artwork using a disposable campaign."""
from __future__ import annotations

from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import builder_sidebar, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import wait_ready, upload_asset, synthetic_texture


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        review = BuilderReview(page, seed['campaign'])
        try:
            page.goto(review.builder)
            wait_ready(page)
            asset = upload_asset(page, 'door', 'Synthetic hinged door.png', synthetic_texture('door'))['id']
            document = page.evaluate("async()=> (await import('/static/gravewright_maps/builder/model.js')).newDocument('Door pivot review')")
            document['assets'] = [{'assetId': asset, 'role': 'door'}]
            identifier = str(uuid4())
            document['doors'] = [{'id': identifier, 'layerId': document['layers'][0]['id'],
                'assetId': asset, 'x1': 5, 'y1': 5, 'x2': 7, 'y2': 5, 'thickness': .2, 'state': 'closed'}]
            project = review.store(str(uuid4()), 0, None, document)
            page.goto(review.builder + '?project=' + project['id'])
            wait_ready(page)
            door = page.locator(f'[data-object-kind=doors][data-object-id="{identifier}"]')
            door.click()
            builder_sidebar(page, 'selection')
            anchor = page.locator('[data-builder-property=rotationAnchor]')
            expect(anchor).to_have_value('')
            anchor.select_option('start')
            expect(page.locator('[data-builder-door-anchor=start]')).to_have_attribute('cx', '5')
            page.locator('[data-builder-rotate]').click()
            stored = review.save()
            actual = stored['document']['doors'][0]
            assert [actual[key] for key in ('x1', 'y1', 'x2', 'y2')] == [5, 5, 5, 7], actual
            page.locator('[data-builder-undo]').click()
            actual = review.save()['document']['doors'][0]
            assert [actual[key] for key in ('x1', 'y1', 'x2', 'y2')] == [5, 5, 7, 5], actual
            page.locator('[data-builder-door-state=open]').click()
            expect(door.locator('g[transform]')).to_have_attribute('transform', 'translate(5 5) rotate(90)')
            expect(door.locator('image')).to_be_visible()
            opened = review.save()['document']['doors'][0]
            assert [opened[key] for key in ('x1', 'y1', 'x2', 'y2')] == [5, 5, 7, 5], opened
            page.locator('[data-builder-door-state=closed]').click()
            expect(door.locator('g[transform]')).to_have_attribute('transform', 'translate(5 5) rotate(0)')
            page.locator('[data-builder-edit-native=doors]').click()
            modal = page.locator('[data-builder-native-editor=doors]')
            expect(modal.locator('[name=rotationAnchor]')).to_have_value('start')
            modal.locator('[name=rotationAnchor]').select_option('end')
            modal.locator('[data-native-editor-save]').click()
            expect(modal).to_have_count(0)
            expect(anchor).to_have_value('end')
            assert review.save()['document']['doors'][0]['rotationAnchor'] == 'end'
            page.reload()
            wait_ready(page)
            door.click()
            builder_sidebar(page, 'selection')
            expect(anchor).to_have_value('end')
            for locale, width in [('en', 1440), ('pt-BR', 390), ('es', 320)]:
                change_locale(page, locale, seed['campaign'])
                page.reload()
                wait_ready(page)
                page.set_viewport_size({'width': width, 'height': 900})
                door.click()
                builder_sidebar(page, 'selection')
                expect(anchor).to_be_visible()
                expect(anchor).to_have_value('end')
                anchor.scroll_into_view_if_needed()
                expect(anchor).to_be_in_viewport()
                page.screenshot(path=str(output / f'door-anchor-{locale}-{width}.png'))
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
            assert not errors, errors
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close()
            browser.close()
    return {'passed': True, 'cases': ['pivot-rotation-undo', 'opening-and-closing-art',
        'shared-editor-save-reload', 'en-pt-BR-es-desktop-mobile'], 'pageErrors': errors}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
