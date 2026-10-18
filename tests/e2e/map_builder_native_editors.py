"""Reuse the game's light, particle and shader windows inside Map Builder.

All browser controls, project writes and generated scenes use a disposable
campaign. Editor drafts must never write to the currently selected/live scene.
"""
from __future__ import annotations

import json

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_tool, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import set_name, wait_ready


SOURCE = 'void main() { float a = 0.35 + 0.10 * sin(uTime); finalColor = vec4(uColor * a, a); }'


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    records, errors, dialogs, commands = [], [], [], []
    campaign = seed['campaign']
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.grant_permissions(['clipboard-read', 'clipboard-write'])
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        page.on('request', lambda request: commands.append(request.url)
                if request.method != 'GET' and '/api/maps/' in request.url else None)
        review = BuilderReview(page, campaign)
        identifiers = {}

        def point(x, y):
            return page.locator('[data-builder-canvas]').evaluate("""(svg,p)=>{
              const r=new DOMPoint(...p).matrixTransform(svg.getScreenCTM());return [r.x,r.y];
            }""", [x, y])

        def place(kind, preset, x, y):
            builder_sidebar(page, 'library')
            page.locator('[data-builder-role=light]' if kind == 'lights' else '[data-builder-role=effect]').click()
            if kind != 'lights':
                page.locator('[data-builder-collection-filter]').select_option('particle' if kind == 'particles' else 'shader')
            singular = {'lights': 'light', 'particles': 'particle', 'shaders': 'shader'}[kind]
            page.locator(f'[data-builder-{singular}-preset="{preset}"]').click()
            page.mouse.click(*point(x, y))
            origin = page.locator(f'[data-builder-{kind}] [data-object-id]')
            expect(origin).to_have_count(1)
            identifiers[kind] = origin.get_attribute('data-object-id')

        def origin(kind):
            return page.locator(f'[data-builder-{kind}] [data-object-id="{identifiers[kind]}"]')

        def editor(kind, selection=False):
            builder_tool(page, 'select')
            builder_workspace(page)
            # Clear existing wall-node handles before clicking an origin again.
            page.mouse.click(*point(35, 25))
            if selection:
                origin(kind).click()
                builder_sidebar(page, 'selection')
                page.locator('[data-builder-edit-native]').click()
            else:
                origin(kind).dblclick()
            modal = page.locator(f'[data-builder-native-editor="{kind}"]')
            expect(modal).to_be_visible()
            expected = '.wall-editor' if kind in ('walls', 'doors') else '.light-editor' if kind == 'lights' else '.effect-editor'
            assert modal.evaluate('(el,selector)=>el.matches(selector)||!!el.querySelector(selector)', expected)
            assert modal.evaluate('el=>el.contains(document.activeElement)'), 'Editor must receive focus'
            return modal

        def set_control(modal, label, value):
            control = modal.get_by_label(label, exact=True)
            control.scroll_into_view_if_needed()
            if control.get_attribute('type') == 'checkbox':
                control.set_checked(value)
            elif control.evaluate('el=>el.tagName') == 'SELECT':
                control.select_option(str(value))
            elif control.get_attribute('type') in ('range', 'color'):
                control.evaluate("""(el,value)=>{
                  el.value=String(value);el.dispatchEvent(new Event('input',{bubbles:true}));
                  el.dispatchEvent(new Event('change',{bubbles:true}));
                }""", value)
            else:
                control.fill(str(value))
                control.dispatch_event('input')
                control.dispatch_event('change')

        def apply(modal):
            modal.locator('[data-native-editor-save]').click()
            expect(modal).to_have_count(0)

        def drag_window(modal):
            widget = modal.locator('.light-editor, .effect-editor').first
            header = widget.locator('[data-move-handle]')
            before, handle = widget.bounding_box(), header.bounding_box()
            page.mouse.move(handle['x'] + 100, handle['y'] + 14)
            page.mouse.down()
            page.mouse.move(handle['x'] + 148, handle['y'] + 38, steps=6)
            page.mouse.up()
            after = widget.bounding_box()
            assert abs(after['x'] - before['x'] - 48) < 2 and abs(after['y'] - before['y'] - 24) < 2, (before, after)
            assert abs(after['width'] - before['width']) < 2, (before, after)
            records.append({'case': 'shared-native-window-retains-real-drag-handle', 'before': before, 'after': after})

        def unchanged(project):
            current = review.save()
            assert current['document'] == project['document']
            assert current['version'] == project['version'], (current['version'], project['version'])

        def private_draft(project):
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved')
            key = f'gravewright.map-builder.draft.{campaign}.{project["id"]}'
            assert page.evaluate('key=>sessionStorage.getItem(key)', key) is None, 'Editor changes must stay outside the project draft'

        def assert_one_undo(before, after):
            page.locator('[data-builder-undo]').click()
            assert review.save()['document'] == before['document'], 'An editor save must be exactly one undo step'
            page.locator('[data-builder-redo]').click()
            assert review.save()['document'] == after['document']

        def state(scene):
            response = page.request.get(f'/api/maps/{scene}/state')
            assert response.ok, response.text()
            return response.json()

        def content(snapshot):
            return {key: snapshot.get(key) for key in ('lights', 'particles', 'shaders', 'images', 'walls', 'lighting')}

        def native(scene, area, action, data):
            return page.evaluate("""args=>gravewrightRealtime.mapCommand('objects',{
              mapId:args.scene,area:args.area,action:args.action,data:args.data})""",
                                 {'scene': scene, 'area': area, 'action': action, 'data': data})

        try:
            page.goto(review.builder); wait_ready(page)
            selected_before, broadcast_before = state(seed['selectedScene']), state(seed['broadcastScene'])
            set_name(page, 'Synthetic shared native editing windows')
            place('lights', 'torch', 8, 9)
            place('particles', 'smoke', 16, 9)
            place('shaders', 'orb-1', 25, 12)
            builder_tool(page, 'wall'); review.stroke((4, 17), (13, 17))
            identifiers['walls'] = page.locator('[data-builder-walls] [data-object-id]').get_attribute('data-object-id')
            builder_tool(page, 'door'); review.stroke((19, 17), (21, 17))
            identifiers['doors'] = page.locator('[data-builder-doors] [data-object-id]').get_attribute('data-object-id')
            baseline = review.save()

            builder_sidebar(page, 'library')
            page.locator('[data-builder-role=light]').click()
            page.locator('[data-builder-light-preset=torch]').click()
            page.mouse.dblclick(*point(8, 9))
            modal = page.locator('[data-builder-native-editor=lights]')
            expect(modal).to_be_visible()
            expect(page.locator('[data-builder-lights] [data-object-id]')).to_have_count(1)
            modal.locator('[data-native-editor-cancel]').click()
            unchanged(baseline)
            records.append({'case': 'double-click-native-origin-with-placement-tool-armed-opens-editor-without-placing'})

            for kind, label in (('lights', 'Intensity'), ('particles', 'Quantity'), ('shaders', 'Opacity')):
                modal = editor(kind)
                set_control(modal, label, .2)
                if kind == 'lights':
                    drag_window(modal)
                private_draft(baseline)
                modal.locator('[data-native-editor-cancel]').click()
                expect(modal).to_have_count(0)
                unchanged(baseline)
                modal = editor(kind)
                set_control(modal, label, .3)
                page.keyboard.press('Escape')
                expect(modal).to_have_count(0)
                expect(page.locator('[data-builder-viewport]')).to_be_focused()
                unchanged(baseline)
                records.append({'case': 'shared-native-window-cancel-and-escape-discard-private-draft', 'kind': kind})

            for kind in ('walls', 'doors'):
                modal = editor(kind, selection=True)
                set_control(modal, 'Type', 'window')
                set_control(modal, 'Limit by elevation', True)
                set_control(modal, 'Lower height', 2)
                set_control(modal, 'Upper height', 5)
                private_draft(baseline)
                page.keyboard.press('Escape')
                expect(modal).to_have_count(0)
                unchanged(baseline)
                records.append({'case': 'same-wall-door-window-cancel-preserves-source-and-geometry', 'kind': kind})
                modal = editor(kind, selection=True)
                apply(modal)
                unchanged(baseline)
                records.append({'case': 'unchanged-native-wall-door-save-does-not-rewrite-legacy-defaults', 'kind': kind})

            modal = editor('lights')
            set_control(modal, 'Intensity', .1)
            modal.locator('.light-editor__header button').click()
            expect(modal).to_have_count(0)
            unchanged(baseline)
            records.append({'case': 'native-window-close-button-discards-draft'})

            modal = editor('shaders')
            modal.locator('#effect-shader-source').fill('void main( { invalid_glsl }')
            modal.locator('[data-native-editor-save]').click()
            expect(modal).to_be_visible()
            expect(modal.locator('[role=status]')).not_to_have_text('')
            private_draft(baseline)
            modal.locator('[data-native-editor-cancel]').click()
            unchanged(baseline)
            records.append({'case': 'invalid-shader-is-rejected-before-mutating-project'})

            modal = editor('shaders')
            assert 'void main' in modal.locator('#effect-shader-source').input_value()
            apply(modal)
            unchanged(baseline)
            records.append({'case': 'opening-and-saving-native-preset-keeps-source-and-project-revision'})

            before = baseline
            modal = editor('lights', selection=True)
            for label, value in [('Bright radius', 2.5), ('Unlimited', True), ('Intensity', .65),
                                 ('Cover', 210), ('Direction', 75), ('Animation', 'pulse'), ('Color', '#66bbaa')]:
                set_control(modal, label, value)
            apply(modal)
            light_project = review.save()
            light, = light_project['document']['lights']
            assert (light['brightRadius'], light['dimRadius'], light['intensity'], light['angle'],
                    light['rotation'], light['animation'], light['color']) == (2.5, 0, .65, 210, 75, 'pulse', '#66bbaa'), light
            assert_one_undo(before, light_project)
            records.append({'case': 'same-light-editor-saves-cone-unlimited-animation-and-color-in-one-undo'})

            before = review.save()
            modal = editor('particles', selection=True)
            for label, value in [('Type', 'runes'), ('Size', 4), ('Quantity', .3), ('Color', '#55bb77'),
                                 ('Receive lighting', .6), ('Emit light', .45)]:
                set_control(modal, label, value)
            apply(modal)
            particle_project = review.save()
            particle, = particle_project['document']['particles']
            assert (particle['kind'], particle['scale'], particle['density'], particle['color'],
                    particle['light_response'], particle['light_emission']) == ('runes', 4, .3, '#55bb77', .6, .45), particle
            assert_one_undo(before, particle_project)
            records.append({'case': 'same-particle-editor-saves-type-density-and-light-interaction-in-one-undo'})

            before = review.save()
            modal = editor('shaders', selection=True)
            original_code = modal.locator('#effect-shader-source').input_value()
            modal.locator('[data-native-editor-save]').focus()
            page.keyboard.press('Tab')
            expect(modal.locator('.effect-editor__header button')).to_be_focused()
            page.keyboard.press('Shift+Tab')
            expect(modal.locator('[data-native-editor-save]')).to_be_focused()
            records.append({'case': 'native-editor-traps-tab-focus-between-real-window-controls'})
            library = modal.locator('.effect-editor__library')
            library.locator('summary').click()
            library.get_by_role('searchbox').fill('Glacial Core')
            preset = library.locator('.effect-editor__presets').get_by_role('option')
            expect(preset).to_have_count(1)
            preset.focus()
            page.keyboard.press('Space')
            expect(preset).to_have_attribute('aria-selected', 'true')
            library.get_by_role('button', name='Apply preset', exact=True).press('Enter')
            assert modal.locator('#effect-shader-source').input_value() != original_code
            modal.get_by_role('button', name='AI prompt', exact=True).click()
            prompt = page.locator('.shader-prompt-dialog')
            expect(prompt).to_be_visible()
            page.keyboard.press('Escape')
            expect(prompt).to_have_count(0)
            expect(modal).to_be_visible()
            modal.get_by_role('button', name='AI prompt', exact=True).click()
            prompt.get_by_label('Desired effect', exact=True).fill('Synthetic slow violet mist — local clipboard only.')
            prompt.get_by_role('button', name='Copy instructions and continue', exact=True).click()
            prompt.get_by_label('GLSL returned by the AI', exact=True).fill('```glsl\n' + SOURCE + '\n```')
            prompt.get_by_role('button', name='Insert into editor', exact=True).click()
            expect(prompt).to_have_count(0)
            expect(modal.locator('#effect-shader-source')).to_have_value(SOURCE)
            private_draft(before)
            for label, value in [('Opacity', .65), ('Color', '#b46aff'), ('Blend mode', 'screen'),
                                 ('Intensity', .7), ('Scale', 1.8), ('Speed', 2.2), ('Rotation', 41),
                                 ('Range', 5), ('Receive lighting', .35), ('Emit light', .6)]:
                set_control(modal, label, value)
            page.screenshot(path=str(output / 'native-editor-en-1440-shader.png'))
            apply(modal)
            configured = review.save()
            shader, = configured['document']['shaders']
            assert shader['source'] == SOURCE, shader
            expected = {'opacity': .65, 'color': '#b46aff', 'blend_mode': 'screen', 'intensity': .7,
                        'scale': 1.8, 'speed': 2.2, 'rotation': 41, 'radius': 5,
                        'light_response': .35, 'light_emission': .6}
            assert {key: shader[key] for key in expected} == expected, shader
            assert_one_undo(before, configured)
            records.append({'case': 'same-shader-editor-library-nested-prompt-full-glsl-and-controls-save-in-one-undo'})

            for kind in ('walls', 'doors'):
                before = review.save()
                modal = editor(kind, selection=True)
                set_control(modal, 'Type', 'window' if kind == 'walls' else 'secret')
                set_control(modal, 'Sound', 'attenuate')
                set_control(modal, 'Limit by elevation', True)
                set_control(modal, 'Lower height', -1.5)
                set_control(modal, 'Upper height', 3.5)
                if kind == 'doors':
                    set_control(modal, 'Revealed to players', True)
                apply(modal)
                configured = review.save()
                row, = configured['document'][kind]
                assert row['presentation'] == ('window' if kind == 'walls' else 'secret'), row
                assert row['behavior'] == ({'movement': 'block', 'vision': 'pass', 'light': 'pass', 'sound': 'attenuate'}
                                           if kind == 'walls' else {'movement': 'pass', 'vision': 'block', 'light': 'block', 'sound': 'attenuate'}), row
                assert row['vertical'] == {'bottom': -1.5, 'top': 3.5}, row
                if kind == 'doors':
                    assert row['discovered'] is True, row
                for key in ('id', 'layerId', 'x1', 'y1', 'x2', 'y2'):
                    assert row[key] == before['document'][kind][0][key], (key, row)
                assert_one_undo(before, configured)
                records.append({'case': 'same-wall-door-window-saves-native-channels-elevation-presentation-in-one-undo', 'kind': kind})

            builder_tool(page, 'select'); builder_workspace(page)
            origin('doors').dblclick()
            behavior = page.locator('[data-smart-object-modal]')
            expect(behavior).to_be_visible()
            page.keyboard.press('Escape')
            expect(behavior).to_have_count(0)
            records.append({'case': 'door-double-click-keeps-existing-smart-object-behavior-window'})
            assert content(state(seed['selectedScene'])) == content(selected_before)
            assert content(state(seed['broadcastScene'])) == content(broadcast_before)
            assert not commands, commands
            records.append({'case': 'editing-native-windows-never-mounts-or-writes-to-live-game-scenes'})

            configured = review.save()
            page.goto(review.builder + '?project=' + configured['id']); wait_ready(page)
            assert review.save()['document'] == configured['document']
            modal = editor('shaders')
            expect(modal.locator('#effect-shader-source')).to_have_value(SOURCE)
            modal.locator('[data-native-editor-cancel]').click()
            records.append({'case': 'native-window-source-and-all-configurations-survive-save-and-reopen'})

            for locale, width in [('en', 1440), ('pt-BR', 1440), ('pt-BR', 390), ('es', 390)]:
                page.set_viewport_size({'width': width, 'height': 900 if width > 500 else 844})
                change_locale(page, locale, campaign)
                page.reload(); wait_ready(page)
                for kind in ('lights', 'particles', 'shaders', 'walls', 'doors'):
                    modal = editor(kind, selection=True)
                    intensity, type_label, height, code, light_title = {
                        'en': ('Intensity', 'Type', 'Lower height', 'GLSL code', 'Light source'),
                        'pt-BR': ('Intensidade', 'Tipo', 'Altura inferior', 'Código GLSL', 'Fonte de luz'),
                        'es': ('Intensidad', 'Tipo', 'Altura inferior', 'Código GLSL', 'Fuente de luz'),
                    }[locale]
                    if kind == 'lights':
                        expect(modal).to_have_attribute('aria-label', light_title)
                        expect(modal.get_by_label(intensity, exact=True)).to_have_value('0.65')
                    elif kind == 'particles':
                        expect(modal.get_by_label(type_label, exact=True)).to_have_value('runes')
                    elif kind == 'shaders':
                        expect(modal.get_by_label(code, exact=True)).to_have_value(SOURCE)
                    else:
                        expect(modal.get_by_label(type_label, exact=True)).to_have_value('window' if kind == 'walls' else 'secret')
                        expect(modal.get_by_label(height, exact=True)).to_have_value('-1.5')
                    metrics = modal.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], (locale, width, kind, metrics)
                    assert metrics['scrollWidth'] <= width, metrics
                    save_bounds = modal.locator('[data-native-editor-save]').bounding_box()
                    assert save_bounds and 0 <= save_bounds['y'] < save_bounds['y'] + save_bounds['height'] <= page.viewport_size['height'], save_bounds
                    assert modal.evaluate('el=>el.contains(document.activeElement)')
                    page.screenshot(path=str(output / f'native-editor-{locale}-{width}-{kind}.png'))
                    page.keyboard.press('Escape')
                    expect(modal).to_have_count(0)
                    records.append({'case': 'shared-native-window-localized-responsive-and-keyboard-close',
                                    'locale': locale, 'width': width, 'kind': kind, 'metrics': metrics})
                unchanged(configured)

            page.set_viewport_size({'width': 1440, 'height': 900})
            change_locale(page, 'en', campaign); page.reload(); wait_ready(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            configured = review.project(configured['id'])
            scene = configured['sceneId']
            generated_state = state(scene)
            for kind in ('lights', 'particles', 'shaders'):
                actual, = generated_state[kind]
                source, = configured['document'][kind]
                keys = ({'intensity', 'angle', 'rotation', 'animation', 'color'} if kind == 'lights'
                        else {'kind', 'scale', 'density', 'color', 'light_response', 'light_emission'} if kind == 'particles'
                        else set(expected) | {'source'})
                assert {key: actual[key] for key in keys} == {key: source[key] for key in keys}, (kind, actual, source)
                if kind == 'lights':
                    assert actual['bright_radius'] == source['brightRadius'] and actual['dim_radius'] == source['dimRadius']
            for kind in ('walls', 'doors'):
                source, = configured['document'][kind]
                actual, = (row for row in generated_state['walls'] if row['kind'] == ('wall' if kind == 'walls' else 'door'))
                assert actual['presentation'] == source['presentation']
                assert actual['vertical_bottom'] == source['vertical']['bottom'] and actual['vertical_top'] == source['vertical']['top']
                assert {key: actual[key + '_behavior'] for key in source['behavior']} == source['behavior']
                if kind == 'doors':
                    assert actual['discovered'] is True
            records.append({'case': 'full-native-editor-configurations-generate-as-real-editable-game-objects'})

            game_layers = page.get_by_role('group', name='Layers', exact=True)
            game_layers.get_by_role('button', name='Lighting', exact=True).click()
            page.locator('[data-effect-tool=light]').click()
            expect(page.locator('.light-picker')).to_be_visible()
            page.locator('.light-picker__header button').click()
            page.locator('[data-effect-kind=light]').first.dblclick()
            game_editor = page.get_by_role('dialog', name='Light source', exact=True)
            expect(game_editor).to_be_visible()
            expect(game_editor.get_by_role('slider', name='Intensity', exact=True)).to_have_value('0.65')
            expect(game_editor.locator('[data-native-editor-save]')).to_have_count(0)
            game_editor.get_by_role('button', name='Close', exact=True).click()
            game_layers.get_by_role('button', name='Walls', exact=True).click()
            for index, kind in enumerate(('wall', 'door')):
                page.locator('.wall-workspace g[role=button]').nth(index).focus()
                page.keyboard.press('Enter')
                game_editor = page.get_by_role('dialog', name='Configure wall' if kind == 'wall' else 'Configure door', exact=True)
                expect(game_editor).to_be_visible()
                expect(game_editor.get_by_label('Type', exact=True)).to_have_value('window' if kind == 'wall' else 'secret')
                expect(game_editor.get_by_label('Lower height', exact=True)).to_have_value('-1.5')
                expect(game_editor.locator('[data-native-editor-cancel]')).to_be_hidden()
                game_editor.get_by_role('button', name='Close editor', exact=True).click()
            game_layers.get_by_role('button', name='Effects', exact=True).click()
            for kind in ('particle', 'shader'):
                page.locator(f'[data-effect-tool={kind}]').click()
                expect(page.locator('.effect-picker')).to_be_visible()
                page.locator('.effect-picker__header button').click()
                page.locator(f'[data-effect-kind={kind}]').first.dblclick()
                game_editor = page.get_by_role('dialog', name='Particle emitter' if kind == 'particle' else 'Scene shader', exact=True)
                expect(game_editor).to_be_visible()
                expect(game_editor.locator('[data-native-editor-cancel]')).to_have_count(0)
                if kind == 'shader':
                    expect(game_editor.locator('#effect-shader-source')).to_have_value(SOURCE)
                game_editor.get_by_role('button', name='Close', exact=True).click()
            assert content(state(scene)) == content(generated_state)
            records.append({'case': 'actual-game-native-light-particle-shader-wall-door-windows-retain-normal-host-behavior'})

            native_light = generated_state['lights'][0]
            native(scene, 'lights', 'update', {'light_id': native_light['id'], 'enabled': False})
            live_before = state(scene)
            page.goto(review.builder + '?project=' + configured['id']); wait_ready(page)
            commands.clear()
            modal = editor('shaders')
            set_control(modal, 'Speed', 3.1)
            apply(modal)
            updated = review.save()
            assert content(state(scene)) == content(live_before)
            assert not commands, commands
            builder_sidebar(page, 'review')
            with page.expect_response(lambda response: response.url.endswith('/update')) as result:
                page.locator('[data-builder-review-update]').click()
            assert result.value.ok, result.value.text()
            live_after = state(scene)
            assert live_after['lights'][0]['id'] == native_light['id'] and live_after['lights'][0]['enabled'] is False
            assert live_after['shaders'][0]['id'] == generated_state['shaders'][0]['id']
            assert live_after['shaders'][0]['source'] == SOURCE and live_after['shaders'][0]['speed'] == 3.1
            assert updated['document']['shaders'][0]['speed'] == 3.1
            records.append({'case': 'linked-scene-updates-only-on-request-and-preserves-native-identity-and-live-toggles'})
        except Exception:
            (output / 'partial.json').write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding='utf-8')
            (output / 'failure.html').write_text(page.content(), encoding='utf-8')
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close(); browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Native Gravewright presets and local synthetic GLSL; no external AI calls.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
