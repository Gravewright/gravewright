"""Author native VTT lighting, particles and shaders in a disposable builder.

Uses real presets, renderer pixels, saved projects and generated GM/player scenes.
All database, media, browsers and diagnostics belong to the synthetic fixture.
"""
from __future__ import annotations

from io import BytesIO
import time

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_reference import set_name, wait_ready


def check_browser(base, seed, output, executable):
    from PIL import Image, ImageChops
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    builder = f'/game/{campaign}/map-builder'
    api = f'/api/containers/{campaign}/map-builder'
    errors, dialogs, records = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        player_context = None

        def point(x, y):
            return page.locator('[data-builder-canvas]').evaluate("""(svg, point) => {
              const p = new DOMPoint(...point).matrixTransform(svg.getScreenCTM());
              return [p.x,p.y];
            }""", [x, y])

        def click_point(x, y):
            page.mouse.click(*point(x, y))

        def select(kind, identifier):
            builder_tool(page, 'select')
            page.locator(f'[data-builder-{kind}] [data-object-id="{identifier}"]').click()
            builder_sidebar(page, 'selection')

        def property_value(key, value):
            control = page.locator(f'[data-builder-properties] [data-builder-property="{key}"]')
            expect(control).to_be_visible()
            if control.evaluate('el=>el.tagName') == 'SELECT':
                control.select_option(str(value))
            else:
                control.fill(str(value))
                control.dispatch_event('change')

        def save():
            # A visibility round-trip can return to already acknowledged content;
            # autosave then settles without an unnecessary POST.
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved', timeout=20_000)
            identifier = page.evaluate("new URL(location.href).searchParams.get('project')")
            response = page.request.get(api + '/projects/' + identifier)
            assert response.ok, response.text()
            return response.json()['project']

        def native(area, action, data):
            return page.evaluate("""args=>gravewrightRealtime.mapCommand('objects', {
              mapId:args.scene,area:args.area,action:args.action,data:args.data})""",
                                 {'scene': scene_id, 'area': area, 'action': action, 'data': data})

        def native_state(target=page):
            response = target.request.get(f'/api/maps/{scene_id}/state')
            assert response.ok, response.text()
            return response.json()

        try:
            page.goto(builder)
            wait_ready(page)
            preview_canvas = page.locator('[data-builder-native-preview] canvas, canvas[data-builder-native-preview]')
            expect(preview_canvas).to_have_count(0)
            builder_sidebar(page, 'layers')
            authored_layers = page.locator('[data-builder-project-layer]')
            expect(authored_layers).to_have_count(1)
            native_layer = authored_layers.get_attribute('data-builder-project-layer')
            layer_name = page.locator(f'[data-builder-layer-title="{native_layer}"]')
            layer_name.fill('Authored mixed native effects')
            layer_name.dispatch_event('change')
            expect(page.locator('[data-builder-layer]')).to_have_count(0)
            set_name(page, 'Synthetic native VTT effects')
            builder_sidebar(page, 'library')
            page.locator('[data-builder-role=light]').click()
            page.locator('[data-builder-light-preset=torch]').click()
            click_point(8, 8)
            expect(page.locator('[data-builder-lights] [data-object-id]')).to_have_count(1)
            light_id = page.locator('[data-builder-lights] [data-object-id]').get_attribute('data-object-id')
            select('lights', light_id)
            property_value('angle', 225)
            property_value('rotation', 45)
            property_value('intensity', .7)
            property_value('animation', 'pulse')
            builder_sidebar(page, 'library')
            page.locator('[data-builder-role=effect]').click()
            page.locator('[data-builder-collection-filter]').select_option('particle')
            page.locator('[data-builder-particle-preset=smoke]').click()
            click_point(14, 8)
            expect(page.locator('[data-builder-particles] [data-object-id]')).to_have_count(1)
            particle_id = page.locator('[data-builder-particles] [data-object-id]').get_attribute('data-object-id')
            select('particles', particle_id)
            property_value('density', .45)
            property_value('scale', 2)
            builder_sidebar(page, 'library')
            page.locator('[data-builder-role=effect]').click()
            page.locator('[data-builder-collection-filter]').select_option('shader')
            page.locator('[data-builder-shader-preset=orb-1]').click()
            click_point(23, 12)
            expect(page.locator('[data-builder-shaders] [data-object-id]')).to_have_count(1)
            shader_id = page.locator('[data-builder-shaders] [data-object-id]').get_attribute('data-object-id')
            select('shaders', shader_id)
            property_value('opacity', .75)
            property_value('radius', 4)
            project = save()
            light, = project['document']['lights']
            particle, = project['document']['particles']
            shader, = project['document']['shaders']
            assert (light['animation'], light['angle'], light['rotation']) == ('pulse', 225, 45), light
            assert (particle['kind'], particle['density'], particle['scale']) == ('smoke', .45, 2), particle
            assert (shader['radius'], shader['opacity']) == (4, .75), shader
            assert shader['source'].strip() and shader['name'], shader
            assert project['document']['layers'] == [{'id': native_layer, 'name': 'Authored mixed native effects',
                                                      'visible': True, 'locked': False}], project['document']['layers']
            assert {light['layerId'], particle['layerId'], shader['layerId']} == {native_layer}
            records.append({'case': 'native-presets-place-configure-and-save-with-supported-settings'})

            builder_workspace(page)
            expect(preview_canvas).to_have_count(1)
            page.wait_for_timeout(500)
            viewport = page.locator('[data-builder-viewport]')
            before = Image.open(BytesIO(viewport.screenshot())).convert('RGB')
            page.wait_for_timeout(350)
            after = Image.open(BytesIO(viewport.screenshot())).convert('RGB')
            assert ImageChops.difference(before, after).getbbox(), 'Native builder preview is frozen'
            preview_canvas.evaluate("el=>el.style.visibility='hidden'")
            empty = Image.open(BytesIO(viewport.screenshot())).convert('RGB')
            preview_canvas.evaluate("el=>el.style.visibility=''")
            assert ImageChops.difference(before, empty).getbbox(), 'Native builder canvas has no visible effects'
            page.screenshot(path=str(output / 'builder-native-effects-desktop.png'))
            records.append({'case': 'real-native-renderer-shows-visible-animated-light-particle-and-shader-pixels'})

            page.locator('[data-builder-preview]').click()
            expect(page.locator('[data-builder-grid]')).to_be_hidden()
            expect(preview_canvas).to_have_count(1)
            page.screenshot(path=str(output / 'builder-native-effects-preview.png'))
            page.locator('[data-builder-preview]').click()
            builder_sidebar(page, 'layers')
            visibility = page.locator(f'[data-builder-layer-visible="{native_layer}"]')
            visibility.uncheck()
            expect(preview_canvas).to_have_count(0)
            expect(visibility).not_to_be_checked()
            for kind in ('lights', 'particles', 'shaders'):
                expect(page.locator(f'[data-builder-{kind}] [data-object-id]')).to_be_hidden()
            page.locator('[data-builder-preview]').click()
            expect(preview_canvas).to_have_count(1)
            expect(visibility).to_be_disabled()
            expect(visibility).not_to_be_checked()
            page.locator('[data-builder-preview]').click()
            expect(preview_canvas).to_have_count(0)
            expect(visibility).to_be_enabled()
            expect(visibility).not_to_be_checked()
            visibility.check()
            expect(preview_canvas).to_have_count(1)
            assert save()['document'] == project['document']
            records.append({'case': 'mixed-authored-layer-visibility-releases-native-renderer-and-preview-restores-editor-state'})
            page.reload()
            wait_ready(page)
            expect(page.locator('[data-builder-lights] [data-object-id]')).to_have_count(1)
            expect(page.locator('[data-builder-particles] [data-object-id]')).to_have_count(1)
            expect(page.locator('[data-builder-shaders] [data-object-id]')).to_have_count(1)
            assert save()['document'] == project['document']
            records.append({'case': 'preview-and-reopening-preserve-native-source-document'})

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                page.reload()
                wait_ready(page)
                torch_name, smoke_name, shader_name = {
                    'en': ('Torch', 'Smoke', 'Arcane Sun'),
                    'pt-BR': ('Tocha', 'Fumaça', 'Sol arcano'),
                    'es': ('Antorcha', 'Humo', 'Sol arcano'),
                }[locale]
                for width in (1440, 390):
                    page.set_viewport_size({'width': width, 'height': 900 if width > 500 else 844})
                    builder_sidebar(page, 'library')
                    page.locator('[data-builder-role=light]').click()
                    expect(page.locator('[data-builder-light-preset=torch]')).to_be_visible()
                    expect(page.locator('[data-builder-light-preset=torch] span').last).to_have_text(torch_name)
                    page.locator('[data-builder-role=effect]').click()
                    page.locator('[data-builder-collection-filter]').select_option('particle')
                    expect(page.locator('[data-builder-particle-preset=smoke]')).to_be_visible()
                    expect(page.locator('[data-builder-particle-preset=smoke] span').last).to_have_text(smoke_name)
                    page.locator('[data-builder-collection-filter]').select_option('shader')
                    expect(page.locator('[data-builder-shader-preset=orb-1] span').last).to_have_text(shader_name)
                    metrics = page.locator('[data-map-builder]').evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], (locale, width, metrics)
                    page.screenshot(path=str(output / f'builder-native-effects-{locale}-{width}.png'))
                    records.append({'case': 'localized-native-catalog-desktop-and-mobile', 'locale': locale, 'width': width})
            page.set_viewport_size({'width': 1440, 'height': 900})
            change_locale(page, 'en', campaign)
            page.reload()
            wait_ready(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            project = page.request.get(api + '/projects/' + project['id']).json()['project']
            scene_id = project['sceneId']
            state = native_state()
            native_light, = state['lights']
            native_particle, = state['particles']
            native_shader, = state['shaders']
            cell = project['document']['cellSize']
            assert (native_light['x'], native_light['y']) == (8 * cell, 8 * cell), native_light
            assert (native_light['animation'], native_light['angle'], native_light['rotation']) == ('pulse', 225, 45)
            assert (native_particle['x'], native_particle['y'], native_particle['kind']) == (14 * cell, 8 * cell, 'smoke')
            assert native_shader['radius'] == 4 and native_shader['source'] == shader['source'], native_shader
            records.append({'case': 'generation-creates-real-native-lights-particles-and-shaders-with-correct-units'})

            native('lighting', 'update', {'mode': 'none', 'darkness': 0, 'lights_out': False})
            page.evaluate("""args=>gravewrightRealtime.mapCommand('update',{
              mapId:args.scene,version:args.version,settings:{visibility:'players'}})""",
                          {'scene': scene_id, 'version': project['sceneVersion']})
            page.evaluate("scene=>gravewrightRealtime.mapCommand('activate',{mapId:scene})", scene_id)
            player_context = browser.new_context(base_url=base, viewport={'width': 1200, 'height': 800})
            player_context.add_cookies([{**seed['sessions']['player'], 'url': base}])
            player = player_context.new_page()
            player.on('pageerror', lambda error: errors.append(str(error)))
            player.goto(f'{base}/game/{campaign}')
            player.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            public = native_state(player)
            assert len(public['particles']) == len(public['shaders']) == len(public['lights']) == 1
            player.wait_for_timeout(500)
            board = player.locator('.game-board canvas').first
            rendered = Image.open(BytesIO(board.screenshot())).convert('RGB')
            player.wait_for_timeout(350)
            animated = Image.open(BytesIO(board.screenshot())).convert('RGB')
            assert ImageChops.difference(rendered, animated).getbbox(), 'Generated player effects are frozen'
            player.screenshot(path=str(output / 'native-effects-player.png'))
            records.append({'case': 'generated-native-effects-reach-and-animate-for-player'})

            native('lights', 'update', {'light_id': native_light['id'], 'enabled': False})
            native('particles', 'update', {'emitter_id': native_particle['id'], 'enabled': False})
            manual = native('particles', 'create', {'x': 100, 'y': 100, 'kind': 'ember'})['emitter']
            page.goto(builder + '?project=' + project['id'])
            wait_ready(page)
            set_name(page, 'Synthetic native effects updated safely')
            save()
            builder_sidebar(page, 'review')
            with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                page.locator('[data-builder-review-update]').click()
            assert updated.value.ok, updated.value.text()
            current = page.request.get(f'/api/maps/{scene_id}/state').json()
            assert next(row for row in current['lights'] if row['id'] == native_light['id'])['enabled'] is False
            assert next(row for row in current['particles'] if row['id'] == native_particle['id'])['enabled'] is False
            assert any(row['id'] == manual['id'] for row in current['particles'])
            assert next(row for row in current['shaders'] if row['id'] == native_shader['id'])['source'] == shader['source']
            records.append({'case': 'scene-update-keeps-native-identities-live-toggles-and-manual-effects'})

            page.goto(builder + '?project=' + project['id'])
            wait_ready(page)
            expect(preview_canvas).to_have_count(1)
            page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide'))")
            expect(preview_canvas).to_have_count(0)
            page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))")
            wait_ready(page)
            expect(preview_canvas).to_have_count(1)
            records.append({'case': 'native-preview-disposes-and-remounts-on-page-lifecycle-with-one-canvas'})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            if player_context:
                player_context.close()
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors,
            'nativeDialogs': dialogs, 'assets': 'Native VTT catalogs and isolated synthetic campaign only.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
