"""Review authored element names and the complete Map Builder library toolbar.

The shared fixture owns every session, campaign, uploaded image and server.
Real controls rename independent placements, choose named references, create
regions/Empty Objects and update the same native scene without replacing IDs.
"""
from __future__ import annotations

from copy import deepcopy
import json
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, builder_workspace, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_combination_matrix import behavior
from map_builder_playtest import chain, node
from map_builder_reference import close_panel, upload_asset, wait_ready


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    cases, errors, dialogs, failed = [], [], [], []
    campaign, project_id = seed['campaign'], None
    kinds = ('floors', 'walls', 'doors', 'decorations', 'regions', 'lights', 'particles', 'shaders')
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
        toolbar = page.locator('.map-builder__dock-toolbar')

        def saved():
            expect(page.locator('[data-map-builder]')).to_have_attribute(
                'data-save-state', 'saved', timeout=20_000)
            return review.project(page.evaluate("new URL(location.href).searchParams.get('project')"))

        def select(identifier):
            builder_sidebar(page, 'layers')
            contents = page.locator('[data-builder-layer-contents]').first
            if not contents.evaluate('element=>element.open'):
                contents.locator('summary').click()
            page.locator(f'[data-builder-layer-object="{identifier}"]').click()
            builder_sidebar(page, 'selection')
            expect(page.locator('[data-builder-selection-name]')).to_be_visible()
            expect(page.locator('[data-builder-selection-name]')).to_have_count(1)

        def rename(identifier, name):
            select(identifier)
            field = page.locator('[data-builder-selection-name]')
            field.fill(name)
            field.press('Tab')
            return saved()

        def native_state(scene):
            response = page.request.get(f'/api/maps/{scene}/state')
            assert response.ok, response.text()
            return response.json()

        def native_named(state, name):
            rows = [row for key in ('walls', 'images', 'zones', 'lights', 'particles', 'shaders')
                    for row in state.get(key, [])]
            return next(row for row in rows
                        if row.get('name') == name or row.get('region', {}).get('name') == name)

        def game():
            page.wait_for_url(f'{base}/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')
            expect(page.locator('.game-menubar__presence')).to_have_attribute('data-presence', 'seated')

        def toolbar_metrics():
            return toolbar.evaluate('''element=>{
              const r=element.getBoundingClientRect();
              return {top:r.top,height:r.height,buttons:[...element.querySelectorAll('button')]
                .filter(button=>button.checkVisibility()).map(button=>{
                  const b=button.getBoundingClientRect();return {
                    text:button.innerText,top:b.top,height:b.height};})};}''')

        def keyboard_tools():
            tools = toolbar.locator('[data-builder-dock-tools]')
            tools.locator('button').first.focus()
            seen = []
            for _ in range(tools.locator('button').count()):
                focused = page.locator(':focus')
                expect(focused).to_be_in_viewport()
                key = focused.evaluate('''button=>button.dataset.builderDockTool || button.dataset.builderTool || button.dataset.builderRole
                  || (button.hasAttribute('data-builder-empty-object')?'empty':'unknown')''')
                seen.append(key)
                page.keyboard.press('Tab')
            assert set(seen) >= {'select', 'erase', 'pan', 'floor', 'wall', 'door',
                                 'decoration', 'empty', 'light', 'effect', 'region'}, seen

        try:
            page.goto(review.builder)
            wait_ready(page)
            page.locator('[data-builder-quick-name]').fill('Synthetic independent element names')
            page.locator('[data-builder-quick-name]').press('Tab')
            keyboard_tools()
            blue = upload_asset(page, 'decoration', 'Synthetic shared blue artwork.png',
                                harness.artwork('#2467b9'))['id']
            project = saved()
            project_id = project['id']

            # Both formerly buried tools are usable from the library itself.
            toolbar.locator('[data-builder-dock-tool=empty]').click()
            review.stroke((6, 6), (8, 8))
            project = saved()
            empty, = project['document']['decorations']
            # Older valid Empty Objects have no authored name. Display the
            # localized fallback without silently writing it into their source.
            legacy_document = deepcopy(project['document'])
            legacy_document['decorations'][0].pop('name', None)
            project = review.store(project['id'], project['version'], project['folderId'], legacy_document)
            assert 'name' not in project['document']['decorations'][0]
            page.goto(review.builder + '?project=' + project_id)
            wait_ready(page)
            select(empty['id'])
            legacy_name = page.locator('[data-builder-selection-name]')
            expect(legacy_name).to_have_value('Empty Object')
            assert legacy_name.evaluate('input=>input.checkValidity()')
            legacy_name.press('Escape')
            expect(legacy_name).to_have_value('Empty Object')
            assert legacy_name.evaluate('input=>input.checkValidity()')
            assert 'name' not in saved()['document']['decorations'][0]
            cases.append({'case': 'legacy-unnamed-empty-reopens-with-valid-display-fallback-without-rewriting-source'})
            rename(empty['id'], 'Gatilho invisível da entrada')
            close_panel(page)
            toolbar.locator('[data-builder-dock-tool=region]').click()
            review.stroke((10, 8), (14, 12))
            project = saved()
            region, = project['document']['regions']
            rename(region['id'], 'Área da ponte principal')
            cases.append({'case': 'library-toolbar-places-empty-object-and-presence-region'})

            document = deepcopy(saved()['document'])
            layer = document['layers'][0]['id']
            ids = {kind: str(uuid4()) for kind in kinds}
            ids['regions'] = region['id']
            document['floors'] = [{'id': ids['floors'], 'layerId': layer, 'assetId': None,
                'x': 2, 'y': 15, 'width': 2, 'height': 2, 'rotation': 0}]
            document['walls'] = [{'id': ids['walls'], 'layerId': layer, 'assetId': None,
                'x1': 18, 'y1': 15, 'x2': 21, 'y2': 15, 'thickness': .3}]
            document['doors'] = [{'id': ids['doors'], 'layerId': layer, 'assetId': None,
                'x1': 22, 'y1': 15, 'x2': 24, 'y2': 15, 'thickness': .3,
                'state': 'closed', 'blueprint': behavior('door', {})}]
            document['decorations'].append({'id': ids['decorations'], 'layerId': layer,
                'assetId': blue, 'x': 17, 'y': 7, 'width': 2, 'height': 2, 'rotation': 0})
            factories = page.evaluate('''async()=>{
              const {nativeFactory}=await import('/static/gravewright_maps/builder/native-controls.js');
              return {lights:nativeFactory('light','none',26,6),
                particles:nativeFactory('particle','smoke',30,6),
                shaders:nativeFactory('shader','orb-1',34,6)};}''')
            for kind, values in factories.items():
                document[kind] = [{**values, 'id': ids[kind], 'layerId': layer}]
            source = document['decorations'][0]
            source['blueprint'] = behavior('lever', {'presence:enter': chain('presence:enter',
                [node('appearance', 'sprite', appearance='inherit')],
                [node('target', 'reference', targetId=ids['decorations'])],
                [('target', 'door', 'appearance', 'target')])})
            project = saved()
            project = review.store(project['id'], project['version'], project['folderId'], document)
            page.goto(review.builder + '?project=' + project_id)
            wait_ready(page)

            names = dict(zip(kinds, ('Piso da entrada', 'Muro da ponte', 'Porta da cripta',
                'Alavanca da ponte', 'Área da ponte principal', 'Luz da entrada',
                'Fumaça da lareira', 'Brilho do portal')))
            before_ids = {kind: {row['id'] for row in project['document'][kind]} for kind in kinds}
            for kind in kinds:
                project = rename(ids[kind], names[kind])
                row = next(row for row in project['document'][kind] if row['id'] == ids[kind])
                assert row['name'] == names[kind], (kind, row)
                assert {row['id'] for row in project['document'][kind]} == before_ids[kind]
                builder_sidebar(page, 'layers')
                expect(page.locator(f'[data-builder-layer-object="{ids[kind]}"]')).to_contain_text(names[kind])
                cases.append({'case': 'single-selection-name-autosaves-with-stable-id', 'kind': kind})
            assert next(row for row in project['document']['decorations']
                        if row['id'] == empty['id'])['blueprint']['graphs']['presence:enter']['nodes'][2]['targetId'] == ids['decorations']

            builder_sidebar(page, 'layers')
            page.locator(f'[data-builder-layer-object="{ids["decorations"]}"]').click()
            page.locator(f'[data-builder-layer-object="{ids["doors"]}"]').click(modifiers=['Shift'])
            builder_sidebar(page, 'selection')
            expect(page.locator('[data-builder-selected-count="2"]')).to_be_visible()
            expect(page.locator('[data-builder-selection-name]')).to_have_count(0)
            cases.append({'case': 'mixed-multiselection-keeps-independent-element-names'})

            # Clear an optional instance label without renaming its shared asset.
            project = rename(ids['decorations'], '')
            ordinary = next(row for row in project['document']['decorations'] if row['id'] == ids['decorations'])
            assert not ordinary.get('name'), ordinary
            builder_sidebar(page, 'layers')
            expect(page.locator(f'[data-builder-layer-object="{ids["decorations"]}"]')).to_contain_text('Synthetic shared blue artwork.png')
            page.locator('[data-builder-undo]').click()
            project = saved()
            assert next(row for row in project['document']['decorations'] if row['id'] == ids['decorations'])['name'] == names['decorations']
            select(ids['decorations'])
            page.locator('[data-builder-duplicate]').click()
            duplicate_project = saved()
            duplicate, = [row for row in duplicate_project['document']['decorations'] if row['id'] not in before_ids['decorations']]
            assert duplicate['name'] == names['decorations'] and duplicate['assetId'] == blue
            page.locator('[data-builder-undo]').click()
            assert len(saved()['document']['decorations']) == 2
            page.locator('[data-builder-redo]').click()
            assert next(row for row in saved()['document']['decorations'] if row['id'] == duplicate['id'])['name'] == names['decorations']
            page.locator('[data-builder-undo]').click()
            project = saved()
            library = page.request.get(review.api).json()['assets']
            assert next(row for row in library if row['id'] == blue)['name'] == 'Synthetic shared blue artwork.png'
            cases.append({'case': 'optional-name-fallback-undo-redo-and-independent-duplicate-preserve-artwork'})

            page.reload()
            wait_ready(page)
            for kind in kinds:
                select(ids[kind])
                expect(page.locator('[data-builder-selection-name]')).to_have_value(names[kind])
            select(ids['regions'])
            expect(page.locator(f'[data-builder-region-door] option[value="{ids["doors"]}"]')).to_have_text(names['doors'])
            select(empty['id'])
            page.locator('[data-builder-edit-behavior]').click()
            modal = page.locator('[data-smart-object-modal]')
            expect(modal.locator('[data-blueprint-instance-name]')).to_have_text('Gatilho invisível da entrada')
            modal.locator('[data-blueprint-event="presence:enter"]').click()
            reference = modal.locator('[data-blueprint-node=target] [data-blueprint-param=targetId]')
            expect(reference).to_have_value(ids['decorations'])
            for kind in ('decorations', 'doors'):
                expect(reference.locator(f'option[value="{ids[kind]}"]')).to_contain_text(names[kind])
            before = set(modal.locator('[data-blueprint-node]').evaluate_all(
                'rows=>rows.map(row=>row.dataset.blueprintNode)'))
            modal.locator('[data-blueprint-add]').click()
            modal.locator('[data-blueprint-pick-type=lightReference]').click()
            light_reference, = set(modal.locator('[data-blueprint-node]').evaluate_all(
                'rows=>rows.map(row=>row.dataset.blueprintNode)')) - before
            expect(modal.locator(f'[data-blueprint-node="{light_reference}"] '
                f'[data-blueprint-param=targetId] option[value="{ids["lights"]}"]')).to_contain_text(names['lights'])
            modal.locator('[data-blueprint-close]').click()
            builder_sidebar(page, 'tools')
            page.locator('[data-builder-network]').click()
            network = page.locator('[data-scene-network]')
            expect(network.locator(f'[data-network-element="{ids["decorations"]}"]')).to_contain_text(names['decorations'])
            page.screenshot(path=str(output / 'named-scene-network.png'))
            network.locator('[data-network-close]').click()
            cases.append({'case': 'reopened-properties-reference-options-pressure-door-and-network-use-authored-names'})

            # Category changes keep fixed chrome even when import is inapplicable.
            close_panel(page)
            baseline = toolbar_metrics()
            for role in ('floor', 'wall', 'door', 'decoration', 'light', 'effect'):
                toolbar.locator(f'[data-builder-role={role}]').click()
                measurements = toolbar_metrics()
                assert abs(measurements['top'] - baseline['top']) <= 1, measurements
                assert abs(measurements['height'] - baseline['height']) <= 1, measurements
            page.locator('[data-builder-collection-filter]').select_option('shader')
            expect(page.locator('[data-builder-shader-preset]')).not_to_have_count(0)
            page.locator('[data-builder-collection-filter]').select_option('particle')
            expect(page.locator('[data-builder-particle-preset]')).not_to_have_count(0)
            cases.append({'case': 'library-category-changes-keep-header-position-and-effects-filter'})

            long_name = 'Alavanca — entrada principal e ponte sobre o rio subterrâneo com pedras antigas'
            project = rename(ids['decorations'], long_name)
            names['decorations'] = long_name
            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width, height in ((1440, 900), (390, 844), (320, 740)):
                    page.set_viewport_size({'width': width, 'height': height})
                    page.goto(review.builder + '?project=' + project_id)
                    wait_ready(page)
                    expect(page.locator('html')).to_have_attribute('lang', locale)
                    close_panel(page)
                    for selector in ('[data-builder-dock-tool=region]', '[data-builder-dock-tool=empty]'):
                        button = toolbar.locator(selector)
                        button.scroll_into_view_if_needed()
                        expect(button).to_be_in_viewport()
                    if locale == 'en':
                        keyboard_tools()
                    metrics = page.locator('[data-map-builder]').evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    assert metrics['scrollWidth'] <= metrics['viewport'] + 1, metrics
                    page.screenshot(path=str(output / f'toolbar-{locale}-{width}.png'))
                    select(ids['decorations'])
                    expect(page.locator('[data-builder-selection-name]')).to_have_value(long_name)
                    metrics = page.locator('#builder-editor-panels').evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'names-{locale}-{width}.png'))
                    cases.append({'case': 'localized-toolbar-and-long-authored-name-fit', 'locale': locale, 'width': width})

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            page.goto(review.builder + '?project=' + project_id)
            wait_ready(page)
            close_panel(page)
            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            game()
            project = review.project(project_id)
            scene = project['sceneId']
            state = native_state(scene)
            native_ids = {kind: native_named(state, names[kind])['id']
                          for kind in kinds if kind != 'floors'}
            native_owner = native_named(state, 'Gatilho invisível da entrada')
            graph = native_owner['blueprint']['graphs']['presence:enter']
            assert next(row for row in graph['nodes'] if row['id'] == 'target')['targetId'] == native_ids['decorations']
            cases.append({'case': 'generation-preserves-names-and-remaps-reference-to-named-native-image'})

            page.goto(review.builder + '?project=' + project_id)
            wait_ready(page)
            updated_name = 'Alavanca da ponte restaurada'
            project = rename(ids['decorations'], updated_name)
            close_panel(page)
            with page.expect_response(lambda response: response.url.endswith('/update')) as updated:
                page.locator('[data-builder-generate]').click()
            assert updated.value.ok, updated.value.text()
            game()
            assert review.project(project_id)['sceneId'] == scene
            updated_state = native_state(scene)
            assert native_named(updated_state, updated_name)['id'] == native_ids['decorations']
            for kind in native_ids:
                if kind != 'decorations':
                    assert native_named(updated_state, names[kind])['id'] == native_ids[kind]
            native_owner = native_named(updated_state, 'Gatilho invisível da entrada')
            assert next(row for row in native_owner['blueprint']['graphs']['presence:enter']['nodes']
                        if row['id'] == 'target')['targetId'] == native_ids['decorations']
            cases.append({'case': 'linked-scene-update-renames-without-replacing-native-ids-or-reference-wires'})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            (output / 'observations.json').write_text(json.dumps({
                'cases': cases, 'project': review.project(project_id) if project_id else None,
                'pageErrors': errors, 'nativeDialogs': dialogs, 'failedRequests': failed,
            }, indent=2, ensure_ascii=False), encoding='utf-8')
            raise
        finally:
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    assert not [row for row in failed if row['error'] != 'net::ERR_ABORTED'], failed
    return {'passed': True, 'cases': cases, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'failedRequests': failed, 'assets': 'Synthetic blue image and native host presets.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
