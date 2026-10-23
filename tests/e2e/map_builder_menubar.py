"""Exercise scene editing and translated directory actions in the lower dock.

Only the shared disposable campaign and its synthetic native scenes are changed.
The action must edit the GM's viewed scene independently of the player broadcast.
"""
from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

import map_builder_blueprints as harness
from map_builder import MEASURE, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_reference import wait_ready


EDIT_LABELS = {
    'en': 'Edit Scene',
    'pt-BR': 'Editar Cena',
    'es': 'Editar escena',
}
DOCK_LABELS = {
    'en': ('Mind maps', 'Clues', 'Progress clocks'),
    'pt-BR': ('Mapas mentais', 'Pistas', 'Relógios de progresso'),
    'es': ('Mapas mentales', 'Pistas', 'Relojes de progreso'),
}
DIRECTORIES = (
    ('mindmaps', '[data-mindmap-directory]', 'Synthetic dock mind map', 'SYNTHETIC_PRIVATE_DOCK_MINDMAP'),
    ('clues', '[data-clue-panel]', 'Synthetic dock clue', 'SYNTHETIC_PRIVATE_DOCK_CLUE'),
    ('clocks', '[data-clock-panel]', 'Synthetic dock clock', 'SYNTHETIC_PRIVATE_DOCK_CLOCK'),
)
# An absolute tooltip intentionally extends beyond its icon button. Its viewport
# bounds and the icon's hitbox are measured separately below.
DOCK_MEASURE = MEASURE.replace(
    "el.matches('button')&&css.overflowX==='visible'",
    "el.matches('button')&&!el.querySelector(':scope > .game-dock__tip')&&css.overflowX==='visible'",
)


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    game = f'/game/{campaign}'
    scenes_api = f'/api/containers/{campaign}/scenes'
    records, errors, dialogs, failed, extra_contexts = [], [], [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            **({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
        page.on('requestfailed', lambda request: failed.append({'url': request.url, 'error': request.failure}))
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
            response = page.goto(game)
            assert response.ok, (response.status, page.url)
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

        def inspect_dock(target, locale):
            for (kind, _, _, _), label in zip(DIRECTORIES, DOCK_LABELS[locale]):
                toggle = target.locator(f'.game-dock .game-dock__item[data-{kind}-open]')
                expect(toggle).to_have_count(1); expect(toggle).to_be_visible()
                expect(target.locator(f'.game-menubar [data-{kind}-open]')).to_have_count(0)
                expect(toggle).to_have_accessible_name(label)
                expect(toggle).to_have_attribute('aria-expanded', 'false')
                assert toggle.locator('svg').count() >= 1
                tip = toggle.locator('.game-dock__tip')
                assert tip.text_content().strip()
                toggle.scroll_into_view_if_needed(); toggle.hover(); expect(tip).to_be_visible()
                assert tip.evaluate('node=>parseFloat(getComputedStyle(node).fontSize)') >= 12
                assert tip.evaluate('''node=>{
                  const r=node.getBoundingClientRect();
                  return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight;
                }'''), (locale, kind, tip.bounding_box())
                assert toggle.evaluate('''node=>{
                  const b=node.getBoundingClientRect(),s=node.querySelector('svg').getBoundingClientRect();
                  return b.width>=24&&b.height>=24&&s.left>=b.left&&s.right<=b.right&&s.top>=b.top&&s.bottom<=b.bottom;
                }'''), (locale, kind, toggle.bounding_box())
                metrics = target.locator('.game-dock').evaluate(DOCK_MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], (locale, kind, metrics)
            target.mouse.move(0, 0)
            metrics = target.locator('.game-menubar').evaluate(MEASURE)
            assert not metrics['tiny'] and not metrics['overflow'], (locale, metrics)

        def open_directories(target, *, readonly=False, keyboard=False):
            for kind, panel_selector, public_name, private_name in DIRECTORIES:
                toggle = target.locator(f'.game-dock [data-{kind}-open]')
                if keyboard: toggle.focus(); target.keyboard.press('Enter')
                else: toggle.click()
                panel = target.locator(panel_selector); expect(panel).to_be_visible()
                expect(toggle).to_have_attribute('aria-expanded', 'true')
                expect(panel).to_contain_text(public_name)
                if readonly:
                    expect(panel).not_to_contain_text(private_name)
                    expect(panel.locator('[data-clock-action], [data-clue-action]')).to_have_count(0)
                    if kind == 'mindmaps':
                        expect(panel.get_by_role('button', name='New mind map', exact=True)).to_have_count(0)
                else: expect(panel).to_contain_text(private_name)
                if keyboard: target.keyboard.press('Escape')
                else:
                    close = panel.locator(':scope > header > button').last
                    expect(close).to_have_text('×')
                    assert close.get_attribute('aria-label')
                    close.click()
                expect(panel).to_have_count(0)
                expect(toggle).to_have_attribute('aria-expanded', 'false')

        try:
            # The fixture starts with a private GM selection and a different
            # broadcast. Clicking the action adopts the actual viewed scene.
            open_game(seed['selectedScene'])
            expect(button).to_have_text(EDIT_LABELS['en'])
            page.evaluate('''async campaign=>{
              const api=gravewright.forTable(campaign);
              await api.clocks.create({name:'Synthetic dock clock',visibility:'players',pinned:false,playersCanEdit:false});
              await api.clocks.create({name:'SYNTHETIC_PRIVATE_DOCK_CLOCK',visibility:'gm',pinned:false});
              await api.clues.create({name:'Synthetic dock clue',segments:1,value:1,visibility:'players',pinned:false});
              await api.clues.create({name:'SYNTHETIC_PRIVATE_DOCK_CLUE',segments:1,value:1,visibility:'gm',pinned:false});
              await api.mindmaps.create({name:'Synthetic dock mind map',visibility:'players'});
              await api.mindmaps.create({name:'SYNTHETIC_PRIVATE_DOCK_MINDMAP',visibility:'gm'});
            }''', campaign)
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
                for width in (1440, 320):
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    open_game(seed['broadcastScene'])
                    expect(button).to_have_text(label)
                    expect(button).to_have_accessible_name(label)
                    inspect_dock(page, locale)
                    if (locale, width) in (('en', 1440), ('pt-BR', 320)):
                        before_directories = scenes()
                        open_directories(page, keyboard=width == 320)
                        assert scenes() == before_directories
                        if width == 320:
                            page.locator('.game-dock [data-panel=journals]').click()
                            journal_panel = page.locator('#journals-panel')
                            expect(journal_panel).to_be_visible()
                            bounds = journal_panel.bounding_box()
                            dock_bounds = page.locator('.game-dock').bounding_box()
                            assert bounds['y'] >= 0 and bounds['x'] >= 0
                            assert bounds['x'] + bounds['width'] <= width + 1
                            assert bounds['y'] + bounds['height'] <= dock_bounds['y'] - 7, (bounds, dock_bounds)
                            page.screenshot(path=str(output / 'dock-native-directory-pt-BR-320.png'))
                            page.locator('.game-dock [data-panel=journals]').click()
                            expect(journal_panel).to_be_hidden()
                        records.append({'case': 'lower-dock-directories-open-and-close-with-active-state-without-changing-scenes',
                                        'locale': locale, 'width': width})
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
                    if width == 320:
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
                extra_contexts.append(readonly)
                readonly.add_cookies([{**seed['sessions'][role], 'url': base}])
                target = readonly.new_page()
                target.on('pageerror', lambda error: errors.append(str(error)))
                target.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
                for width in (1440, 320):
                    target.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    target.goto(game)
                    target.wait_for_function('id=>window.gravewrightMaps?.current?.id===id', arg=seed['broadcastScene'])
                    expect(target.locator('[data-scene-builder-open]')).to_have_count(0)
                    inspect_dock(target, 'en')
                    open_directories(target, readonly=True, keyboard=width == 320)
                    target.screenshot(path=str(output / f'dock-{role}-{width}.png'))
                    records.append({'case': 'readonly-role-keeps-public-dock-directories-without-private-records-or-configuration',
                                    'role': role, 'width': width})
                readonly.close()

            # These manager tools keep their sidebar entries and HTTP transport.
            change_locale(page, 'en', campaign)
            manager_context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900})
            extra_contexts.append(manager_context)
            manager_context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
            manager = manager_context.new_page(); manager_sockets = []
            manager.on('websocket', lambda stream: manager_sockets.append(stream.url))
            manager.on('pageerror', lambda error: errors.append(str(error)))
            before_manager = scenes()
            manager.goto(f'/campaigns/{campaign}/manage?section=clocks')
            expect(manager.locator('[data-manager-ready=true]')).to_be_attached(timeout=30000)
            expect(manager.locator('.game-dock')).to_have_count(0)
            for kind, _, public_name, _ in DIRECTORIES:
                manager.locator(f'[data-manager-section={kind}]').click()
                view = manager.locator(f'[data-manager-view={kind}]')
                expect(view).to_be_visible(); expect(view).to_contain_text(public_name)
            assert not manager_sockets and scenes() == before_manager
            manager_context.close()
            records.append({'case': 'campaign-manager-retains-its-three-sidebar-tools-without-a-table-socket-or-navigation-change'})

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
            (output / 'browser-diagnostics.json').write_text(json.dumps({'completedCases': records,
                'pageErrors': errors, 'nativeDialogs': dialogs, 'failedRequests': failed}, indent=2), encoding='utf-8')
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            for extra in extra_contexts: extra.close()
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    assert not [request for request in failed if request['error'] != 'net::ERR_ABORTED'], failed
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'failedRequests': failed,
            'data': 'Only the disposable fixture campaign and synthetic native scenes.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
