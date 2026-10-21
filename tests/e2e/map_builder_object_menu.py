"""Exercise object context actions and configurable ready-made behaviors.

The real builder, native modals, Blueprint validation, generated scene and audio
run in a disposable campaign with synthetic artwork and a silent WAV. No operator
database, media, configuration or running server is reused.
"""
from __future__ import annotations

from copy import deepcopy
from io import BytesIO
import json
import time

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import set_name, upload_asset, wait_ready


PRESETS = {
    'switch', 'chest', 'secret-passage', 'book', 'altar', 'trap', 'bell',
    'pressure-plate', 'dice-request', 'quest-start', 'quest-complete',
    'entrance-sign', 'timed-switch', 'door-button',
}


def check_browser(base, seed, output, executable):
    from PIL import Image
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    records, errors, dialogs = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_init_script(harness.AUDIO_PROBE)
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        review = BuilderReview(page, campaign)
        root = page.locator('[data-map-builder]')
        viewport = page.locator('[data-builder-viewport]')
        menu = page.locator('[data-builder-object-menu]')
        catalog = page.locator('[data-interactive-object-catalog]')

        def object_node(identifier, kind='decorations'):
            return page.locator(f'[data-builder-{kind}] [data-object-id="{identifier}"]').first

        def open_menu(identifier, keyboard=False, kind='decorations'):
            builder_workspace(page)
            if keyboard:
                builder_tool(page, 'select')
                builder_workspace(page)
                object_node(identifier, kind).click()
                viewport.focus()
                page.keyboard.press('Shift+F10')
            else:
                object_node(identifier, kind).click(button='right')
            expect(menu).to_be_visible()
            expect(menu).to_have_attribute('role', 'menu')
            return menu

        def action(identifier, name, keyboard=False, kind='decorations'):
            open_menu(identifier, keyboard=keyboard, kind=kind)
            menu.locator(f'[data-builder-object-action="{name}"]').click()

        def property_modal(identifier, name, keyboard=False, kind='decorations'):
            action(identifier, name, keyboard=keyboard, kind=kind)
            modal = page.locator(f'[data-builder-property-modal="{name}"]')
            expect(modal).to_be_visible()
            assert modal.evaluate('element=>!!element.closest("[role=dialog]")')
            expect(page.locator('dialog')).to_have_count(0)
            return modal

        def preset(identifier, name):
            action(identifier, 'templates')
            entries = set(menu.locator('[data-builder-object-action^="preset:"]').evaluate_all(
                'buttons=>buttons.map(button=>button.dataset.builderObjectAction.slice(7))'))
            assert PRESETS <= entries, entries
            menu.locator(f'[data-builder-object-action="preset:{name}"]').click()
            expect(catalog).to_be_visible()
            expect(catalog.locator(f'[data-interactive-preset="{name}"]')).to_have_attribute('aria-pressed', 'true')
            return catalog

        def close_modal(modal):
            page.keyboard.press('Escape')
            expect(modal).to_have_count(0)
            expect(viewport).to_be_focused()

        def unchanged(project):
            current = review.save()
            assert current['document'] == project['document'], (current['document'], project['document'])
            return current

        def nodes(element):
            return [node for graph in element.get('blueprint', {}).get('graphs', {}).values()
                    for node in graph['nodes']]

        def decoration(project, identifier):
            return next(row for row in project['document']['decorations'] if row['id'] == identifier)

        def apply_catalog():
            catalog.locator('.blueprint-templates__primary').click()
            expect(catalog).to_have_count(0)

        try:
            page.goto(review.builder)
            wait_ready(page)
            set_name(page, 'Synthetic context actions with long object and media labels — 雪')
            off_asset = upload_asset(page, 'decoration',
                'Synthetic chest closed — a deliberately long authored object image label.png',
                harness.artwork('#b94a28'))['id']
            on_asset = upload_asset(page, 'decoration',
                'Synthetic chest open — a deliberately long alternate image label.png',
                harness.artwork('#2677dd'))['id']
            builder_tool(page, 'decoration')
            page.locator('[data-builder-brush-material]').select_option(off_asset)
            review.stroke((8, 8), (10, 10))
            review.stroke((16, 8), (18, 10))
            initial = review.save()
            first, second = [row['id'] for row in initial['document']['decorations']]

            # A secondary press may select an object but must not start drawing
            # with the currently active tool, move it, or create an undo entry.
            builder_tool(page, 'wall')
            builder_workspace(page)
            point = object_node(first).bounding_box()
            page.mouse.move(point['x'] + point['width'] / 2, point['y'] + point['height'] / 2)
            page.mouse.down(button='right')
            page.mouse.move(point['x'] + point['width'] / 2 + 35,
                            point['y'] + point['height'] / 2 + 20, steps=4)
            page.mouse.up(button='right')
            if menu.is_visible():
                page.keyboard.press('Escape')
            unchanged(initial)
            open_menu(first)
            expect(menu.locator('[data-builder-object-action=properties]')).to_be_focused()
            page.keyboard.press('End')
            expect(menu.locator('[role=menuitem]').last).to_be_focused()
            page.keyboard.press('Home')
            expect(menu.locator('[role=menuitem]').first).to_be_focused()
            page.keyboard.press('Escape')
            expect(menu).to_have_count(0)
            expect(viewport).to_be_focused()
            unchanged(initial)
            records.append({'case': 'right-button-gesture-and-context-keyboard-navigation-preserve-map-geometry'})

            properties = property_modal(first, 'properties', keyboard=True)
            name = properties.locator('[data-builder-property=name]')
            name.fill('Synthetic ornate chest with a deliberately long authored object name — 雪')
            name.dispatch_event('change')
            close_modal(properties)
            renamed = review.save()
            assert decoration(renamed, first)['name'].startswith('Synthetic ornate chest')
            page.locator('[data-builder-undo]').click()
            unchanged(initial)
            records.append({'case': 'keyboard-context-properties-edit-persists-and-one-undo-restores-original'})

            appearance = property_modal(first, 'appearance')
            appearance.locator('[data-builder-property=assetId]').select_option(on_asset)
            close_modal(appearance)
            changed = review.save()
            assert decoration(changed, first)['assetId'] == on_asset
            page.locator('[data-builder-undo]').click()
            unchanged(initial)
            records.append({'case': 'appearance-has-independent-native-modal-and-edits-real-object-with-undo'})

            behavior = property_modal(first, 'behavior')
            values = set(behavior.locator('[data-builder-property=behavior] option').evaluate_all(
                'options=>options.map(option=>option.value.replace(/^preset:/,""))'))
            assert PRESETS <= values and {'none', 'torch', 'lever'} <= values, values
            close_modal(behavior)
            unchanged(initial)
            records.append({'case': 'behavior-modal-exposes-expanded-ready-made-behaviors-and-existing-components'})

            behavior = property_modal(first, 'behavior')
            behavior.locator('[data-builder-property=behavior]').select_option('preset:bell')
            expect(behavior).to_have_count(0)
            expect(catalog).to_be_visible()
            expect(catalog.locator('[data-interactive-preset=bell]')).to_have_attribute('aria-pressed', 'true')
            close_modal(catalog)
            unchanged(initial)
            records.append({'case': 'choosing-ready-made-behavior-opens-its-configurable-catalog-form'})

            preset(first, 'chest')
            expect(catalog.locator('[data-interactive-preset-include-sound]')).not_to_be_checked()
            expect(catalog.locator('[data-interactive-preset-sound]')).to_be_disabled()
            expect(catalog.locator('[data-interactive-preset-include-image]')).not_to_be_checked()
            expect(catalog.locator('[data-interactive-preset-image]')).to_be_disabled()
            catalog.locator('[data-interactive-preset-include-sound]').check()
            catalog.locator('[data-interactive-preset-sound]').select_option(seed['track'])
            catalog.locator('[data-interactive-preset-include-image]').check()
            catalog.locator('[data-interactive-preset-image]').select_option(on_asset)
            close_modal(catalog)
            unchanged(initial)
            records.append({'case': 'ready-made-preset-media-options-are-opt-in-and-cancel-preserves-object'})

            preset(first, 'chest')
            message = 'Synthetic chest opened with optional audio and image.'
            catalog.locator('[data-interactive-preset-message]').fill(message)
            catalog.locator('[data-interactive-preset-include-sound]').check()
            catalog.locator('[data-interactive-preset-sound]').select_option(seed['track'])
            catalog.locator('[data-interactive-preset-volume]').fill('0.6')
            catalog.locator('[data-interactive-preset-include-image]').check()
            catalog.locator('[data-interactive-preset-image]').select_option(on_asset)
            apply_catalog()
            authored = review.save()
            chest = decoration(authored, first)
            assert chest['lever']['state'] == 'off' and chest['assetId'] == off_asset, chest
            sound, = [row for row in nodes(chest) if row['type'] == 'sound']
            assert sound['trackId'] == seed['track'] and sound['volume'] == .6, sound
            assert chest['blueprint']['states']['on'] == {'appearance': 'asset', 'assetId': on_asset}, chest
            assert chest['blueprint']['states']['off'] == {'appearance': 'inherit'}, chest
            assert any(row.get('text') == message for row in nodes(chest)), chest
            page.locator('[data-builder-undo]').click()
            unchanged(initial)
            page.locator('[data-builder-redo]').click()
            unchanged(authored)
            records.append({'case': 'ready-made-chest-saves-validated-graph-sound-state-image-and-single-undo-redo'})

            preset(first, 'bell')
            catalog.locator('.blueprint-templates__primary').click()
            expect(catalog.locator('.blueprint-templates__primary')).to_have_text('Replace and apply')
            close_modal(catalog)
            unchanged(authored)
            records.append({'case': 'canceling-preset-replacement-retains-existing-authored-graph-and-media'})

            preset(second, 'chest')
            catalog.locator('[data-interactive-preset-include-sound]').check()
            catalog.locator('[data-interactive-preset-sound]').select_option(seed['track'])
            catalog.locator('[data-interactive-preset-include-image]').check()
            catalog.locator('[data-interactive-preset-image]').select_option(on_asset)
            catalog.locator('[data-interactive-preset-include-sound]').uncheck()
            catalog.locator('[data-interactive-preset-include-image]').uncheck()
            apply_catalog()
            authored = review.save()
            plain = decoration(authored, second)
            assert not any(row['type'] == 'sound' for row in nodes(plain)), plain
            assert plain['blueprint']['states']['on'] == {'appearance': 'inherit'}, plain
            records.append({'case': 'unchecked-media-options-omit-sound-and-image-even-after-choosing-values'})

            # The editor uses the exact graph saved by the catalog. Its local
            # simulation must validate without activating the playable scene.
            behavior = property_modal(first, 'behavior')
            behavior.locator('[data-builder-edit-behavior]').click()
            editor = page.locator('[data-smart-object-modal]')
            expect(editor).to_be_visible()
            editor.locator('[data-blueprint-event=interact]').click()
            editor.locator('[data-blueprint-fit]').click()
            editor.locator('[data-blueprint-simulate]').click()
            expect(editor.locator('[data-blueprint-trace]')).to_contain_text('Synthetic door click')
            expect(editor.locator('[data-blueprint-trace]')).to_contain_text(message)
            editor.locator('[data-blueprint-cancel]').click()
            if behavior.count():
                close_modal(behavior)
            unchanged(authored)
            records.append({'case': 'configured-preset-reopens-in-real-node-editor-and-simulates-connected-actions'})

            properties = property_modal(first, 'properties')
            properties.locator('[data-builder-property=name]').fill(
                'Synthetic ornate chest with a deliberately long authored object name — 雪')
            close_modal(properties)
            authored = review.save()
            assert decoration(authored, first)['name'].startswith('Synthetic ornate chest')
            baseline = deepcopy(authored['document'])
            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width, height in ((1440, 900), (390, 844), (320, 700)):
                    page.set_viewport_size({'width': width, 'height': height})
                    page.goto(review.builder + '?project=' + authored['id'])
                    wait_ready(page)
                    expect(page.locator('html')).to_have_attribute('lang', locale)
                    measurements = {}
                    for name in ('properties', 'appearance', 'behavior'):
                        modal = property_modal(first, name, keyboard=name == 'properties')
                        expect(modal.locator('footer button')).to_have_text(
                            {'en': 'Done', 'pt-BR': 'Concluído', 'es': 'Listo'}[locale])
                        metrics = modal.evaluate(MEASURE)
                        assert not metrics['tiny'] and not metrics['overflow'], (locale, width, name, metrics)
                        for _ in range(8):
                            page.keyboard.press('Tab')
                            assert modal.evaluate('element=>element.closest("[role=dialog]").contains(document.activeElement)')
                        page.screenshot(path=str(output / f'object-{name}-{locale}-{width}.png'))
                        measurements[name] = metrics
                        close_modal(modal)
                    preset(first, 'chest')
                    catalog.locator('[data-interactive-preset-include-sound]').check()
                    catalog.locator('[data-interactive-preset-sound]').select_option(seed['track'])
                    catalog.locator('[data-interactive-preset-include-image]').check()
                    catalog.locator('[data-interactive-preset-image]').select_option(on_asset)
                    list_layout = catalog.evaluate('''element=>{
                      const sidebar=element.querySelector('.interactive-presets__sidebar').getBoundingClientRect();
                      const list=element.querySelector('.blueprint-templates__list').getBoundingClientRect();
                      const content=element.querySelector('.blueprint-templates__panes > .blueprint-templates__content').getBoundingClientRect();
                      return {height:list.height,sidebarBottom:sidebar.bottom,contentTop:content.top};
                    }''')
                    assert list_layout['height'] >= 96, (locale, width, list_layout)
                    if width <= 600:
                        assert list_layout['sidebarBottom'] <= list_layout['contentTop'] + 1, list_layout
                        catalog.locator('.blueprint-templates__panes').evaluate('element=>{element.scrollTop=0;}')
                    metrics = catalog.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], (locale, width, metrics)
                    page.screenshot(path=str(output / f'object-presets-{locale}-{width}.png'))
                    measurements['templates'] = metrics
                    measurements['templates']['list'] = list_layout
                    close_modal(catalog)
                    assert review.save()['document'] == baseline
                    records.append({'case': 'localized-context-modals-and-preset-media-fit-and-trap-focus',
                                    'locale': locale, 'width': width, 'metrics': measurements})

            # Check the mobile's visible alternative to a secondary pointer.
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-object-options]').click()
            expect(menu).to_be_visible()
            page.keyboard.press('Escape')
            records.append({'case': 'visible-selection-button-opens-same-object-menu-on-phone'})

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(review.builder + '?project=' + authored['id'])
            wait_ready(page)
            builder_tool(page, 'door')
            review.stroke((22, 12), (25, 12))
            builder_tool(page, 'region')
            review.stroke((20, 16), (24, 20))
            authored = review.save()
            region = authored['document']['regions'][0]
            door = authored['document']['doors'][0]
            filters = property_modal(region['id'], 'region', kind='regions')
            filters.locator('[data-builder-region-pick-door]').click()
            expect(filters).to_be_hidden()
            page.keyboard.press('Escape')
            expect(filters).to_be_visible()
            expect(filters.locator('[data-builder-region-pick-door]')).to_be_focused()
            expect(filters.locator('[data-builder-region-door]')).to_have_value('')
            filters.locator('[data-builder-region-pick-door]').click()
            expect(filters).to_be_hidden()
            object_node(door['id'], 'doors').click()
            expect(filters).to_be_visible()
            expect(filters.locator('[data-builder-region-door]')).to_have_value(door['id'])
            close_modal(filters)
            unchanged(authored)
            records.append({'case': 'region-context-modal-suspends-for-map-picking-and-resumes-after-cancel-or-selection'})
            builder_workspace(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')
            page.locator('.individual-audio__toggle').first.click()
            expect(page.locator('.individual-audio__toggle').first).to_have_attribute('aria-pressed', 'true')
            project = review.project(authored['id'])
            scene = project['sceneId']

            def state():
                response = page.request.get(f'/api/maps/{scene}/state')
                assert response.ok, response.text()
                return response.json()

            native, = [row for row in state()['images'] if row.get('blueprint', {}).get('states', {}).get('on', {}).get('assetId') == on_asset]
            assert native['asset_id'] == off_asset and native['lever']['state'] == 'off', native

            def rendered_color(expected):
                page.wait_for_function('!!gravewrightMaps.board?.viewport()')
                point = page.evaluate('''image=>{
                  const r=document.querySelector('.game-board__surface').getBoundingClientRect(),v=gravewrightMaps.board.viewport();
                  return {x:r.x+v.x+image.x*v.scale+8,y:r.y+v.y+image.y*v.scale};
                }''', native)
                deadline = time.monotonic() + 10
                while True:
                    with Image.open(BytesIO(page.screenshot())) as bitmap:
                        rgb = bitmap.convert('RGB').getpixel((round(point['x']), round(point['y'])))
                    if expected == 'blue' and rgb[2] > rgb[0] + 60 or expected == 'orange' and rgb[0] > rgb[2] + 60:
                        return {'expected': expected, 'rgb': rgb}
                    assert time.monotonic() < deadline, {'expected': expected, 'rgb': rgb, 'point': point}
                    page.wait_for_timeout(100)

            control = page.locator(f'[data-smart-image-id="{native["id"]}"][data-smart-image-action=interact]')
            expect(control).to_be_visible()
            control.focus()
            control.press('Enter')
            deadline = time.monotonic() + 12
            while True:
                current = next(row for row in state()['images'] if row['id'] == native['id'])
                if current['lever']['state'] == 'on' and current['asset_id'] == on_asset:
                    break
                assert time.monotonic() < deadline, current
                page.wait_for_timeout(100)
            page.wait_for_function('window.__blueprintAudio.playing.length>0')
            assert not page.evaluate('window.__blueprintAudio.rejected'), page.evaluate('window.__blueprintAudio')
            prompt = page.locator('[data-automation-presentation]')
            if prompt.count():
                page.locator('[data-presentation-close]').click()
            pixels = [rendered_color('blue')]
            control.focus()
            control.press('Enter')
            deadline = time.monotonic() + 12
            while True:
                current = next(row for row in state()['images'] if row['id'] == native['id'])
                if current['lever']['state'] == 'off' and current['asset_id'] == off_asset:
                    break
                assert time.monotonic() < deadline, current
                page.wait_for_timeout(100)
            pixels.append(rendered_color('orange'))
            page.screenshot(path=str(output / 'object-preset-native-scene.png'))
            records.append({'case': 'generated-native-chest-interaction-plays-real-sound-and-restores-image-on-close',
                            'nativeId': native['id'], 'pixels': pixels,
                            'audio': page.evaluate('window.__blueprintAudio')})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            (output / 'audio-diagnostics.json').write_text(json.dumps(page.evaluate('window.__blueprintAudio'),
                indent=2), encoding='utf-8')
            (output / 'progress.json').write_text(json.dumps({'cases': records, 'pageErrors': errors,
                'nativeDialogs': dialogs}, indent=2, ensure_ascii=False), encoding='utf-8')
            raise
        finally:
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Two generated solid-color PNGs and a generated silent one-second WAV.'}


if __name__ == '__main__':
    harness.__file__ = __file__
    harness.check_browser = check_browser
    harness.main()
