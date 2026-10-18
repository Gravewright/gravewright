"""Review stable library controls and checkbox behavior in the real Map Builder.

Uses the shared disposable campaign, server and synthetic media fixture. Long
authored collection names, native catalogs and localizations share one layout.
"""
from __future__ import annotations

import json

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import close_panel, synthetic_texture, upload_asset, wait_ready


HEADER = """() => {
  const box = selector => {
    const el = document.querySelector(selector), r = el.getBoundingClientRect();
    return {x:r.x,y:r.y,width:r.width,height:r.height,visible:el.checkVisibility()};
  };
  return {title:box('.map-builder__dock-title'),search:box('[data-builder-search]'),
    filter:box('[data-builder-collection-filter]'),roles:box('.map-builder__role-picker'),
    toggle:box('[data-builder-library-toggle]'),toolbar:box('.map-builder__dock-toolbar')};
}"""


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
        root = page.locator('[data-map-builder]')

        def roles():
            return ('floor', 'wall', 'door', 'decoration', 'light', 'effect')

        def verify_header(locale, width, populated):
            page.set_viewport_size({'width': width, 'height': 900 if width > 500 else 844})
            change_locale(page, locale, campaign)
            page.reload(); wait_ready(page)
            close_panel(page)
            baseline, measured = None, []
            for role in roles():
                page.locator(f'[data-builder-role={role}]').click()
                if role == 'effect':
                    page.locator('[data-builder-collection-filter]').select_option('particle')
                current = page.evaluate(HEADER)
                measured.append({'role': role, 'geometry': current})
                baseline = baseline or current
                for name in ('title', 'search', 'filter', 'roles', 'toggle'):
                    for dimension in ('x', 'y', 'width', 'height'):
                        assert abs(current[name][dimension] - baseline[name][dimension]) <= 1, (
                            locale, width, populated, role, name, dimension, baseline, current)
                if role == 'effect':
                    page.locator('[data-builder-collection-filter]').select_option('shader')
                    shader = page.evaluate(HEADER)
                    for name in ('title', 'search', 'filter', 'roles', 'toggle'):
                        assert shader[name] == current[name], (name, current, shader)
                    expect(page.locator('[data-builder-particle-preset]')).to_have_count(0)
                select_style = page.locator('[data-builder-collection-filter]').evaluate(
                    'el=>parseFloat(getComputedStyle(el).paddingInlineEnd)')
                assert select_style >= 24, 'A native select needs room for its disclosure arrow'
                metrics = root.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, width, role, metrics)
                assert metrics['scrollWidth'] <= width + 1, metrics
                if locale == 'pt-BR' and populated:
                    page.screenshot(path=str(output / f'library-{role}-{width}.png'))
            # Matching and empty results must not move any of the filters.
            page.locator('[data-builder-role=floor]').click()
            if populated:
                collection = page.locator('[data-builder-collection-filter]')
                name = collection.locator('option').last.get_attribute('value')
                collection.select_option(name)
                filtered = page.evaluate(HEADER)
                for role in ('light', 'effect', 'floor'):
                    page.locator(f'[data-builder-role={role}]').click()
                expect(collection).to_have_value(name)
                assert page.evaluate(HEADER) == filtered
            search = page.locator('[data-builder-search]')
            search.fill('Synthetic'); matching = page.evaluate(HEADER)
            search.fill('no-result-generated-synthetic-needle')
            expect(page.locator('[data-builder-assets-empty]')).to_be_visible()
            assert page.evaluate(HEADER) == matching
            search.fill('')
            toggle = page.locator('[data-builder-library-toggle]')
            toggle.click(); expect(toggle).to_have_attribute('aria-expanded', 'false')
            expect(page.locator('#builder-library-content')).to_be_hidden()
            collapsed = page.evaluate(HEADER)
            for role in ('light', 'effect', 'floor'):
                page.locator(f'[data-builder-role={role}]').click()
                current = page.evaluate(HEADER)
                assert current == collapsed, (role, collapsed, current)
            toggle.click(); expect(toggle).to_have_attribute('aria-expanded', 'true')
            records.append({'case': 'library-header-remains-stable-across-material-native-filter-search-and-collapse',
                            'locale': locale, 'width': width, 'populated': populated, 'geometry': measured})

        def geometry(control):
            control.scroll_into_view_if_needed()
            result = control.evaluate("""el => {
              const r=el.getBoundingClientRect(), l=el.closest('label'), p=l.getBoundingClientRect();
              return {x:r.x,y:r.y,width:r.width,height:r.height,checked:el.checked,
                labelWidth:p.width,labelHeight:p.height,verticalCenter:Math.abs(r.y+r.height/2-p.y-p.height/2),
                type:el.type,appearance:getComputedStyle(el).appearance};
            }""")
            assert 14 <= result['width'] <= 24 and 14 <= result['height'] <= 24, result
            assert result['verticalCenter'] <= 2, result
            return result

        def toggle(selector, initial=True):
            control = page.locator(selector)
            expect(control).to_be_visible()
            assert control.is_checked() == initial
            before = geometry(control)
            control.locator('..').click()
            expect(control).to_be_checked(checked=not initial)
            after_pointer = geometry(control)
            control.focus(); page.keyboard.press('Space')
            expect(control).to_be_checked(checked=initial)
            after_keyboard = geometry(control)
            for dimension in ('x', 'y', 'width', 'height', 'labelWidth', 'labelHeight'):
                assert before[dimension] == after_pointer[dimension] == after_keyboard[dimension], (
                    selector, dimension, before, after_pointer, after_keyboard)
            return before

        def select(kind, identifier):
            builder_tool(page, 'select'); builder_workspace(page)
            box = page.locator(f'[data-builder-{kind}] [data-object-id="{identifier}"]').bounding_box()
            fraction = .5 if kind == 'lights' else .25
            page.mouse.click(box['x'] + box['width'] * fraction, box['y'] + box['height'] * fraction)
            builder_sidebar(page, 'selection')

        try:
            page.goto(review.builder); wait_ready(page)
            # Persist the empty document so locale reloads revisit the same map.
            initial = review.save()
            for locale in ('en', 'pt-BR', 'es'):
                for width in (1440, 390):
                    verify_header(locale, width, False)

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(review.builder + '?project=' + initial['id']); wait_ready(page)
            material = upload_asset(page, 'floor', 'Synthetic textured floor.png', synthetic_texture('floor'))['id']
            # The real asset form supplies an authored long collection label.
            card = page.locator(f'[data-builder-assets] [data-asset-id="{material}"]')
            card.dblclick()
            modal = page.locator('[data-builder-asset-modal]')
            modal.locator('[data-builder-import-collection]').fill(
                'Synthetic collection with a long authored description and Unicode — chão')
            modal.locator('[data-builder-import-submit]').click()
            expect(modal).to_have_count(0)
            decoration = upload_asset(page, 'decoration', 'Synthetic torch artwork.png', harness.artwork('#ab742b'))['id']
            builder_tool(page, 'decoration')
            page.locator('[data-builder-brush-material]').select_option(decoration)
            review.stroke((5, 5), (7, 7)); builder_sidebar(page, 'selection')
            page.locator('[data-builder-property=behavior]').select_option('torch')
            builder_tool(page, 'light'); review.stroke((20, 5), (20, 5))
            builder_tool(page, 'region'); review.stroke((24, 15), (28, 19))
            project = review.save()
            torch = project['document']['decorations'][0]['id']
            light = next(item['id'] for item in project['document']['lights']
                         if item['id'] != project['document']['decorations'][0]['torch']['lightId'])
            region = project['document']['regions'][0]['id']
            layer = project['document']['layers'][0]['id']
            for locale in ('en', 'pt-BR', 'es'):
                for width in (1440, 390):
                    verify_header(locale, width, True)
                    metrics = {}
                    builder_sidebar(page, 'settings')
                    details = page.locator('[data-builder-settings]')
                    if not details.evaluate('el=>el.open'):
                        details.locator('summary').click()
                    for name in ('grid', 'snap'):
                        metrics[name] = toggle(f'[data-builder-form] [name={name}]')
                    builder_sidebar(page, 'layers')
                    metrics['visible'] = toggle(f'[data-builder-layer-visible="{layer}"]')
                    metrics['locked'] = toggle(f'[data-builder-layer-locked="{layer}"]', False)
                    select('lights', light)
                    metrics['nativeEnabled'] = toggle('[data-builder-property=enabled]')
                    if locale == 'pt-BR':
                        page.screenshot(path=str(output / f'checkbox-native-{locale}-{width}.png'))
                    select('decorations', torch)
                    metrics['torchLit'] = toggle('[data-builder-property=torchLit]')
                    select('regions', region)
                    metrics['regionEnabled'] = toggle('[data-builder-property=regionEnabled]')
                    # A full checkbox round trip can cancel a pending autosave
                    # because the document matches its persisted snapshot again.
                    # Settle autosave before reading; a no-op needs no POST.
                    expect(root).to_have_attribute('data-save-state', 'saved')
                    current = review.project(project['id'])['document']
                    assert current == project['document'], 'Every reversible checkbox round trip preserves the authored map'
                    page.screenshot(path=str(output / f'checkboxes-{locale}-{width}.png'))
                    records.append({'case': 'localized-checkboxes-have-compact-aligned-stable-pointer-and-keyboard-controls',
                                    'locale': locale, 'width': width, 'metrics': metrics})
        except Exception:
            (output / 'last-header.json').write_text(json.dumps(page.evaluate(HEADER), indent=2), encoding='utf-8')
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close(); browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Generated textured PNG and solid-color synthetic torch artwork.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
