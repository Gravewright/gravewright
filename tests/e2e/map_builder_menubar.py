"""Exercise the translated Map Builder action beside the table layer buttons.

Only the shared disposable campaign and its synthetic native scenes are changed.
The action must edit the GM's viewed scene independently of the player broadcast.
"""
from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import map_builder_blueprints as harness
from map_builder import MEASURE, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import wait_ready


EDIT_LABELS = {
    'en': 'Edit map with Map Builder',
    'pt-BR': 'Editar mapa com map builder',
    'es': 'Editar mapa con Map Builder',
}


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    game = f'/game/{campaign}'
    scenes_api = f'/api/containers/{campaign}/scenes'
    records, errors, dialogs = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        review = BuilderReview(page, campaign)
        button = page.locator('.game-menubar__layers [data-scene-builder-open]')

        def scenes(target=page):
            response = target.request.get(scenes_api)
            assert response.ok, response.text()
            return response.json()

        def projects():
            response = page.request.get(review.api)
            assert response.ok, response.text()
            return response.json()['projects']

        def open_game(identifier):
            page.goto(game)
            page.wait_for_function(
                'id=>window.gravewrightMaps?.current?.id===id && !!window.gravewrightRealtime',
                arg=identifier)
            expect(button).to_be_visible()
            expect(button).to_be_enabled()

        def select_scene(identifier):
            page.evaluate('gravewrightMaps.showDirectory()')
            expect(page.locator('#maps-panel')).to_be_visible()
            for folder in (seed['parentFolder'], seed['folder']):
                toggle = page.locator(f'[data-map-folder="{folder}"] > header > .gw-folder__toggle')
                if toggle.get_attribute('aria-expanded') != 'true':
                    toggle.click()
            page.locator(f'.game-directory__scene[data-scene-id="{identifier}"]').click()
            page.wait_for_function('id=>gravewrightMaps.current?.id===id', arg=identifier)
            close = page.locator('[data-map-panel=close]')
            if close.is_visible():
                close.click()

        def opened_project(identifier):
            wait_ready(page)
            current = urlsplit(page.url)
            assert f'{current.scheme}://{current.netloc}' == base, page.url
            assert current.path == review.builder, page.url
            source = review.project(parse_qs(current.query)['project'][0])
            assert source['sceneId'] == identifier, source
            expect(page.locator('[data-builder-generate]')).to_have_text('Update scene')
            assert len(context.pages) == 1, 'The menubar action opened another browser tab.'
            return source

        try:
            # The fixture starts with a private GM selection and a different
            # broadcast. Clicking the action adopts the actual viewed scene.
            open_game(seed['selectedScene'])
            expect(button).to_have_text(EDIT_LABELS['en'])
            initial = scenes()
            assert initial['navigatingMapId'] == seed['selectedScene']
            assert initial['activeMapId'] == seed['broadcastScene']
            assert not projects()
            with page.expect_response(lambda response: response.url.endswith('/adopt')) as adopted:
                button.click()
            assert adopted.value.ok, adopted.value.text()
            source = opened_project(seed['selectedScene'])
            after = scenes()
            assert len(after['maps']) == len(initial['maps'])
            assert after['activeMapId'] == initial['activeMapId']
            assert after['navigatingMapId'] == initial['navigatingMapId']
            assert len(projects()) == 1
            page.screenshot(path=str(output / 'menubar-adopted-viewed-scene.png'))
            records.append({'case': 'native-viewed-scene-is-adopted-independently-of-player-broadcast',
                            'scene': source['sceneId'], 'project': source['id']})

            # Reopening uses the existing source and preserves player state.
            open_game(seed['selectedScene'])
            before_reopen = scenes()
            button.focus()
            page.keyboard.press('Enter')
            assert opened_project(seed['selectedScene'])['id'] == source['id']
            assert scenes() == before_reopen
            assert len(projects()) == 1
            records.append({'case': 'keyboard-reopen-reuses-the-linked-project-without-duplicates'})

            # Switch the viewed map without a reload, then use the same action.
            # Its target must follow the scene rather than the earlier closure.
            open_game(seed['selectedScene'])
            select_scene(seed['broadcastScene'])
            before_switch_edit = scenes()
            button.click()
            second_source = opened_project(seed['broadcastScene'])
            assert second_source['id'] != source['id']
            assert len(projects()) == 2
            after_switch_edit = scenes()
            assert after_switch_edit['activeMapId'] == before_switch_edit['activeMapId']
            assert after_switch_edit['navigatingMapId'] == before_switch_edit['navigatingMapId']
            records.append({'case': 'scene-navigation-updates-the-menubar-action-target'})

            # Translator must supply both the visible and accessible text.
            # Horizontal scrolling inside the layer strip is valid on mobile.
            for locale, label in EDIT_LABELS.items():
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    open_game(seed['broadcastScene'])
                    expect(button).to_have_text(label)
                    expect(button).to_have_accessible_name(label)
                    layer_buttons = page.locator('.game-menubar__layers button:not([data-scene-builder-open])')
                    layer_names = layer_buttons.evaluate_all("""buttons=>buttons.map(button=>
                      button.getAttribute('data-on:click').match(/_layer='([^']+)'/)[1])""")
                    assert {'game', 'gm', 'effects'} <= set(layer_names), layer_names
                    for layer in ('game', 'gm', 'effects'):
                        layer_button = layer_buttons.nth(layer_names.index(layer))
                        layer_button.scroll_into_view_if_needed()
                        layer_button.click()
                        expect(layer_button).to_have_attribute('aria-pressed', 'true')
                        expect(page.locator('#table-workspace')).to_have_attribute('data-table-layer', layer)
                        expect(button).to_be_visible()
                        expect(button).to_be_enabled()
                        button.scroll_into_view_if_needed()
                        metrics = page.locator('.game-menubar__layers').evaluate(MEASURE)
                        assert not metrics['tiny'] and not metrics['overflow'], (locale, width, layer, metrics)
                        assert metrics['scrollWidth'] <= metrics['viewport'] + 1, (locale, width, metrics)
                        records.append({'case': 'translated-action-remains-available-in-each-table-layer',
                                        'locale': locale, 'width': width, 'layer': layer, 'metrics': metrics})
                    page.screenshot(path=str(output / f'menubar-{locale}-{width}.png'))
                    if width == 390:
                        before_mobile_edit = scenes()
                        button.click()
                        wait_ready(page)
                        assert parse_qs(urlsplit(page.url).query)['project'] == [second_source['id']]
                        assert scenes() == before_mobile_edit
                        assert len(projects()) == 2
                        records.append({'case': 'translated-mobile-action-opens-the-current-linked-source',
                                        'locale': locale, 'width': width})

            # Other roles do not receive an edit action even when they have a
            # current scene whose GM source is available to the owner.
            for role in ('player', 'streamer'):
                readonly = browser.new_context(base_url=base, viewport={'width': 1200, 'height': 800})
                readonly.add_cookies([{**seed['sessions'][role], 'url': base}])
                target = readonly.new_page()
                target.on('pageerror', lambda error: errors.append(str(error)))
                target.goto(game)
                target.wait_for_function('id=>window.gravewrightMaps?.current?.id===id', arg=seed['broadcastScene'])
                expect(target.locator('[data-scene-builder-open]')).to_have_count(0)
                readonly.close()
                records.append({'case': 'scene-edit-action-is-absent-for-readonly-roles', 'role': role})

            # Remove only the synthetic fixture scenes through the normal
            # transport to cover live removal and a fresh empty table load.
            page.set_viewport_size({'width': 1440, 'height': 900})
            change_locale(page, 'en', campaign)
            open_game(seed['broadcastScene'])
            for row in scenes()['maps']:
                page.evaluate('args=>gravewrightRealtime.mapCommand("delete",args)', {'mapId': row['id']})
            page.wait_for_function('!!window.gravewrightMaps && !gravewrightMaps.current')
            expect(button).to_be_hidden()
            assert not scenes()['maps']
            page.screenshot(path=str(output / 'menubar-without-scene.png'))
            page.reload()
            page.wait_for_function('!!window.gravewrightMaps && !!window.gravewrightRealtime')
            expect(button).to_have_count(1)
            expect(button).to_be_hidden()
            records.append({'case': 'action-hides-after-scene-removal-and-on-a-fresh-empty-table'})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'data': 'Only the disposable fixture campaign and synthetic native scenes.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
