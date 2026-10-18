"""Verify MapBuilder scene icons and editing through the native context menu.

Only disposable campaigns, projects and native scenes from the existing fixture
are used. Normal navigation, broadcasting and non-GM projections remain covered.
"""
from __future__ import annotations

from copy import deepcopy
from io import BytesIO
import time
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import wait_ready


EDIT_LABELS = {'en': 'Edit with MapBuilder', 'pt-BR': 'Editar com MapBuilder', 'es': 'Editar con MapBuilder'}


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    game = f'/game/{campaign}'
    scenes_api = f'/api/containers/{campaign}/scenes'
    records, errors, dialogs = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        review = BuilderReview(page, campaign)
        reference_icon = {}

        def scenes(target=page):
            response = target.request.get(scenes_api)
            assert response.ok, response.text()
            return response.json()

        def scene(identifier, target=page):
            return next(row for row in scenes(target)['maps'] if row['id'] == identifier)

        def open_game():
            page.goto(game)
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')

        def directory():
            page.evaluate('gravewrightMaps.showDirectory()')
            expect(page.locator('#maps-panel')).to_be_visible()
            for identifier in (seed['parentFolder'], seed['folder']):
                toggle = page.locator(f'[data-map-folder="{identifier}"] > header > .gw-folder__toggle')
                if toggle.get_attribute('aria-expanded') != 'true':
                    toggle.click()
            return page.locator('#maps-panel')

        def primary(identifier, target=page):
            return target.locator(f'.game-directory__scene[data-scene-id="{identifier}"]')

        def open_menu(identifier, target=page, keyboard=False):
            source = primary(identifier, target)
            if keyboard:
                source.focus(); target.keyboard.press('Shift+F10')
            else:
                source.click(button='right')
            menu = target.get_by_role('menu')
            expect(menu).to_be_visible()
            expect(menu.get_by_role('menuitem').first).to_be_focused()
            return menu

        def close_menu(identifier, target=page):
            target.keyboard.press('Escape')
            expect(target.get_by_role('menu')).to_have_count(0)
            expect(primary(identifier, target)).to_be_focused()

        def focus_builder_action(target=page):
            action = target.locator('[data-scene-builder-edit]')
            for _ in range(target.get_by_role('menuitem').count()):
                if action.evaluate('el=>el===el.ownerDocument.activeElement'):
                    break
                target.keyboard.press('ArrowDown')
            expect(action).to_be_focused()
            return action

        def compact_icon(identifier, target=page):
            row = primary(identifier, target)
            expect(row).to_have_attribute('data-scene-builder-origin', '')
            expect(row.locator('svg').first).to_have_attribute('aria-label', 'MapBuilder')
            actual = row.evaluate("""row=>({
              color:getComputedStyle(row.querySelector('svg')).color,
              shape:row.querySelector('svg').innerHTML, height:row.getBoundingClientRect().height,
              children:row.children.length, tag:row.tagName})""")
            if primary(seed['broadcastScene'], target).count():
                reference_icon.update(primary(seed['broadcastScene'], target).evaluate("""row=>({
                  color:getComputedStyle(row.querySelector('svg')).color,
                  shape:row.querySelector('svg').innerHTML,height:row.getBoundingClientRect().height})"""))
            common = reference_icon
            assert actual['color'] == 'rgb(210, 121, 107)' and actual['color'] != common['color'], actual
            assert actual['shape'] == common['shape'], 'The MapTrifold icon stays the same shape'
            assert actual['tag'] == 'BUTTON' and actual['children'] == 4, actual
            assert actual['height'] <= common['height'] + 1, (actual, common)
            expect(target.locator('[data-scene-builder-edit]')).to_have_count(0)
            expect(target.locator('[data-scene-row]')).to_have_count(0)
            return actual

        def generate():
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_url(base + game)
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            return review.project(project['id'])['sceneId']

        def native_sample(name, expected):
            from PIL import Image

            if page.locator('[data-map-panel=close]').is_visible():
                page.locator('[data-map-panel=close]').click()
            expect(page.locator('.game-board__surface canvas')).to_be_visible()
            page.wait_for_function('gravewrightMaps.board?.viewport()?.scale>0')
            point = page.evaluate("""()=>{
              const surface=document.querySelector('.game-board__surface').getBoundingClientRect();
              const view=gravewrightMaps.board.viewport();
              return {x:surface.x+view.x+140.8*view.scale,
                      y:surface.y+view.y+147.2*view.scale};
            }""")
            deadline = time.monotonic() + 8
            actual = None
            while time.monotonic() < deadline:
                image = Image.open(BytesIO(page.screenshot())).convert('RGB')
                actual = image.getpixel((round(point['x']), round(point['y'])))
                if max(abs(left - right) for left, right in zip(actual, expected)) < 20:
                    break
                page.wait_for_timeout(150)
            assert max(abs(left - right) for left, right in zip(actual, expected)) < 20, {
                'point': point, 'actual': actual, 'expected': expected}
            page.screenshot(path=str(output / name))
            return actual

        def apply_scene(selector):
            with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                page.locator(selector).click()
            assert updated.value.ok, updated.value.text()
            page.wait_for_url(base + game)
            page.wait_for_function('id=>window.gravewrightMaps?.current?.id===id && !!window.gravewrightRealtime', arg=scene_id)
            result = {'scene': scene(scene_id), 'project': review.project(project['id'])}
            assert result['scene']['id'] == result['project']['sceneId'] == scene_id
            return result

        def edit_background(color):
            builder_sidebar(page, 'settings')
            background = page.locator('[data-builder-form] [name=background]')
            background.fill(color)
            background.dispatch_event('change')
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved')
            saved = review.project(project['id'])
            assert saved['document']['background'] == color, saved
            return saved

        def assert_project_opened(expected, snapshot):
            wait_ready(page)
            expect(page.locator('[data-builder-title]')).to_have_value(expected['name'])
            url = urlsplit(page.url)
            assert f'{url.scheme}://{url.netloc}' == base and url.path == review.builder, page.url
            assert parse_qs(url.query)['project'] == [expected['id']], page.url
            assert len(context.pages) == 1, 'Direct editing opened another browser tab'
            assert review.save()['document'] == expected['document']
            assert scenes() == snapshot, 'Editing a source project changed scene navigation or broadcast'

        try:
            page.goto(review.builder); wait_ready(page)
            original = review.save()
            document = deepcopy(original['document'])
            authored_name = ('Synthetic MapBuilder origin — a deliberately long scene title / ' + 'North gallery ' * 8)[:120].rstrip()
            document.update(name=authored_name, columns=8, rows=6, cellSize=64, background='#284b67')
            project = review.store(str(uuid4()), 0, seed['folder'], document)
            page.goto(review.builder + '?project=' + project['id']); wait_ready(page)
            scene_id = generate()
            projection = scenes()
            assert projection['activeMapId'] == seed['broadcastScene']
            assert projection['navigatingMapId'] == scene_id
            linked = scene(scene_id)
            assert linked['builderProjectId'] == project['id']
            assert 'builderProjectId' not in scene(seed['broadcastScene'])
            assert 'builderProjectId' not in scene(seed['selectedScene'])
            directory()
            compact_icon(scene_id)
            expect(primary(scene_id).locator('strong')).to_have_text(authored_name)
            expect(primary(scene_id).locator('[data-navigating]')).to_be_visible()
            expect(primary(seed['broadcastScene']).locator('[data-broadcast]')).to_be_visible()
            menu = open_menu(seed['selectedScene'])
            expect(menu.locator('[data-scene-builder-edit]')).to_have_count(0)
            close_menu(seed['selectedScene'])
            records.append({'case': 'linked-GM-scene-has-only-a-red-MapTrifold-icon-and-retains-compact-row-geometry'})

            before_edit = scenes()
            menu = open_menu(scene_id)
            labels = page.locator('#map-text').evaluate('el=>JSON.parse(el.textContent)')
            expect(menu.get_by_role('menuitem', name=labels['editScene'], exact=True)).to_be_visible()
            expect(menu.locator('[data-scene-builder-edit]')).to_have_text(EDIT_LABELS['en'])
            close_menu(scene_id)
            open_menu(scene_id, keyboard=True); close_menu(scene_id)
            open_menu(scene_id).locator('[data-scene-builder-edit]').click()
            assert_project_opened(project, before_edit)
            open_game(); directory()
            open_menu(scene_id, keyboard=True); focus_builder_action()
            page.keyboard.press('Enter')
            assert_project_opened(project, before_edit)
            records.append({'case': 'context-menu-mouse-and-keyboard-edit-open-the-source-without-changing-scenes-and-Escape-restores-focus'})

            for interaction in ('click', 'keyboard'):
                open_game(); directory()
                before_detach = scenes()
                with page.expect_popup() as opened:
                    page.locator('[data-map-panel=detach]').click()
                detached = opened.value
                detached.on('pageerror', lambda error: errors.append(str(error)))
                detached.set_viewport_size({'width': 377, 'height': 754})
                compact_icon(scene_id, detached)
                metrics = detached.locator('#maps-panel').evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (interaction, metrics)
                open_menu(scene_id, detached); close_menu(scene_id, detached)
                open_menu(scene_id, detached, keyboard=True); close_menu(scene_id, detached)
                open_menu(scene_id, detached)
                detached.mouse.click(10, 650)
                expect(detached.get_by_role('menu')).to_have_count(0)
                expect(page.get_by_role('menu')).to_have_count(0)
                open_menu(scene_id, detached, keyboard=interaction == 'keyboard')
                edit = detached.locator('[data-scene-builder-edit]')
                expect(edit).to_have_text(EDIT_LABELS['en'])
                expect(page.locator('[data-scene-builder-edit]')).to_have_count(0)
                if interaction == 'keyboard':
                    focus_builder_action(detached)
                detached.screenshot(path=str(output / f'scene-directory-detached-{interaction}-377.png'))
                with detached.expect_event('close'):
                    if interaction == 'click':
                        edit.click()
                    else:
                        detached.keyboard.press('Enter')
                page.wait_for_url('**/map-builder?project=' + project['id'] + '*')
                assert detached.is_closed()
                assert_project_opened(project, before_detach)
                records.append({'case': 'detached-directory-edits-in-the-main-window-and-closes-the-popup',
                                'interaction': interaction, 'width': 377, 'metrics': metrics})

            open_game(); directory()
            primary(seed['selectedScene']).click()
            page.wait_for_function('id=>gravewrightMaps.current?.id===id', arg=seed['selectedScene'])
            assert scenes()['activeMapId'] == seed['broadcastScene']
            directory()
            compact_icon(scene_id)
            open_menu(scene_id)
            labels = page.locator('#map-text').evaluate('el=>JSON.parse(el.textContent)')
            page.get_by_role('menuitem', name=labels['editScene'], exact=True).click()
            expect(page.locator('.game-scene-settings')).to_be_visible()
            page.keyboard.press('Escape')
            expect(page.locator('.game-scene-settings')).to_have_count(0)
            records.append({'case': 'normal-scene-navigation-and-existing-context-settings-remain-usable'})

            version = scene(scene_id)['version']
            page.evaluate("""args=>gravewrightRealtime.mapCommand('update',{
              mapId:args.id,version:args.version,settings:{visibility:'players'}})""", {'id': scene_id, 'version': version})
            directory(); open_menu(scene_id)
            page.get_by_role('menuitem', name='Activate for players', exact=True).click()
            expect(primary(scene_id).locator('[data-broadcast]')).to_be_visible()
            assert scenes()['activeMapId'] == scene_id
            compact_icon(scene_id)
            records.append({'case': 'existing-broadcast-action-and-active-status-coexist-with-MapBuilder-origin'})

            search = page.locator('#maps-panel input[type=search]')
            search.fill('deliberately long scene')
            expect(primary(scene_id)).to_be_visible()
            expect(primary(seed['selectedScene'])).to_have_count(0)
            compact_icon(scene_id)
            search.fill('')
            expect(primary(seed['selectedScene'])).to_be_visible()
            records.append({'case': 'folder-search-retains-the-generated-scene-origin-icon'})

            for locale in EDIT_LABELS:
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    open_game(); panel = directory()
                    primary(scene_id).scroll_into_view_if_needed()
                    layout = compact_icon(scene_id)
                    metrics = panel.evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], (locale, width, metrics)
                    assert metrics['scrollWidth'] <= metrics['viewport'] + 1, (locale, width, metrics)
                    page.screenshot(path=str(output / f'scene-directory-{locale}-{width}.png'))
                    menu = open_menu(scene_id, keyboard=True)
                    expect(menu.locator('[data-scene-builder-edit]')).to_have_text(EDIT_LABELS[locale])
                    labels = page.locator('#map-text').evaluate('el=>JSON.parse(el.textContent)')
                    expect(menu.get_by_role('menuitem', name=labels['editScene'], exact=True)).to_be_visible()
                    focus_builder_action()
                    page.screenshot(path=str(output / f'scene-menu-{locale}-{width}.png'))
                    close_menu(scene_id)
                    records.append({'case': 'localized-single-column-scene-directory', 'locale': locale,
                                    'width': width, 'metrics': metrics, 'layout': layout})

            # Public scene consumers receive no source-project identifier, even
            # when the generated scene is the active scene visible to players.
            for role in ('player', 'streamer'):
                readonly = browser.new_context(base_url=base, viewport={'width': 1200, 'height': 800})
                readonly.add_cookies([{**seed['sessions'][role], 'url': base}])
                target = readonly.new_page()
                target.on('pageerror', lambda error: errors.append(str(error)))
                target.goto(game)
                target.wait_for_function('id=>window.gravewrightMaps?.current?.id===id', arg=scene_id)
                projection = scenes(target)
                assert projection['is_gm'] is False
                assert len(projection['maps']) == 1 and projection['maps'][0]['id'] == scene_id
                assert all('builderProjectId' not in item for item in projection['maps'])
                expect(target.locator('[data-scene-builder-origin],[data-scene-builder-edit]')).to_have_count(0)
                response = target.request.get(review.api + '/projects/' + project['id'])
                assert response.status == 403, (role, response.status, response.text())
                response = target.request.get(review.builder + '?project=' + project['id'])
                assert response.status == 404, (role, response.status)
                readonly.close()
                records.append({'case': 'source-metadata-and-edit-access-stay-GM-only', 'role': role})

            # Reopen the viewed scene through its actual context menu. Applying
            # the source replaces its content without creating another scene.
            page.set_viewport_size({'width': 1440, 'height': 900})
            change_locale(page, 'en', campaign)
            open_game(); directory()
            primary(scene_id).click()
            page.wait_for_function('id=>gravewrightMaps.current?.id===id', arg=scene_id)
            before = scenes()
            identifiers = {row['id'] for row in before['maps']}
            before_version = scene(scene_id)['version']
            original_pixels = native_sample('scene-before-builder-update.png', (40, 75, 103))
            directory()
            open_menu(scene_id).locator('[data-scene-builder-edit]').click()
            wait_ready(page)
            expect(page.locator('[data-builder-generate]')).to_have_text('Update scene')
            expect(page.locator('[data-builder-generate]')).to_be_enabled()
            saved = edit_background('#9b5737')
            applied = apply_scene('[data-builder-generate]')
            assert applied['scene']['version'] == before_version + 1
            after = scenes()
            assert {row['id'] for row in after['maps']} == identifiers
            assert after['activeMapId'] == after['navigatingMapId'] == scene_id
            assert scene(scene_id)['builderProjectId'] == project['id']
            assert review.project(project['id'])['document'] == saved['document']
            updated_pixels = native_sample('scene-after-builder-update.png', (155, 87, 55))
            assert updated_pixels != original_pixels
            directory(); compact_icon(scene_id)
            expect(primary(scene_id).locator('[data-broadcast]')).to_be_visible()
            expect(page.locator('[data-scene-builder-origin]')).to_have_count(1)
            records.append({'case': 'view-context-edit-autosave-and-primary-update-replace-the-same-scene',
                            'scene': scene_id, 'sceneCount': len(identifiers),
                            'beforePixel': original_pixels, 'afterPixel': updated_pixels})

            # The Review panel applies to the same linked scene on a repeat edit.
            open_menu(scene_id).locator('[data-scene-builder-edit]').click()
            wait_ready(page)
            edit_background('#3c8051')
            builder_sidebar(page, 'review')
            expect(page.locator('[data-builder-review-generate]')).to_be_hidden()
            expect(page.locator('[data-builder-review-update]')).to_be_visible()
            repeated = apply_scene('[data-builder-review-update]')
            assert repeated['scene']['version'] == applied['scene']['version'] + 1
            repeated_projection = scenes()
            assert {row['id'] for row in repeated_projection['maps']} == identifiers
            assert repeated_projection['activeMapId'] == repeated_projection['navigatingMapId'] == scene_id
            assert scene(scene_id)['builderProjectId'] == project['id']
            repeated_pixels = native_sample('scene-after-review-update.png', (60, 128, 81))
            directory(); compact_icon(scene_id)
            expect(primary(scene_id).locator('[data-broadcast]')).to_be_visible()
            expect(page.locator('[data-scene-builder-origin]')).to_have_count(1)
            records.append({'case': 'review-update-reuses-the-linked-scene-without-duplicates',
                            'scene': scene_id, 'sceneCount': len(identifiers), 'pixel': repeated_pixels})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close(); browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'data': 'Only generated blank synthetic scenes and disposable fixture projects.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
