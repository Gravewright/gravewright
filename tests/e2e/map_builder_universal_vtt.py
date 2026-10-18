"""Import and export a synthetic Universal VTT map through the public modals.

Uses an isolated campaign and generated bitmap; no publisher maps or operator
files are read. Portable geometry, warnings, retry and role boundaries are checked.
"""
from __future__ import annotations

import base64
from io import BytesIO
import json
from uuid import uuid4

import map_builder_blueprints as harness
from map_builder import MEASURE, builder_sidebar, change_locale
from map_builder_asset_removal import BuilderReview
from map_builder_playtest import persistent_snapshot, post
from map_builder_reference import wait_ready


def artwork_document():
    from PIL import Image
    source = BytesIO()
    with Image.new('RGB', (420, 280), '#244966') as image:
        image.save(source, 'PNG')
    return {'format': .2,
        'resolution': {'map_origin': {'x': 1.25, 'y': 2.5}, 'map_size': {'x': 6, 'y': 4}, 'pixels_per_grid': 70},
        'line_of_sight': [[{'x': 1.25, 'y': 2.5}, {'x': 7.25, 'y': 2.5}]],
        'objects_line_of_sight': [[{'x': 2.25, 'y': 3.5}, {'x': 2.25, 'y': 5.5}, {'x': 3.25, 'y': 5.5}]],
        'portals': [{'position': {'x': 3.75, 'y': 2.5}, 'bounds': [{'x': 3.25, 'y': 2.5}, {'x': 4.25, 'y': 2.5}],
                     'rotation': 0, 'closed': True, 'freestanding': False}],
        'environment': {'baked_lighting': False, 'ambient_light': 'ff102030'},
        'lights': [{'position': {'x': 2.25, 'y': 3.5}, 'range': 2.5, 'intensity': .8, 'color': 'ff2468aa', 'shadows': True}],
        'image': base64.b64encode(source.getvalue()).decode('ascii')}


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    records, errors, dialogs, guests = [], [], [], []
    imported_name = ('Synthetic UVTT — <b>authored map</b> ' + 'North gallery ' * 4).rstrip()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(base_url=base, viewport={'width': 1440, 'height': 900}, accept_downloads=True)
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()

        def observe(target):
            target.on('pageerror', lambda error: errors.append(str(error)))
            target.on('dialog', lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))

        observe(page)
        review = BuilderReview(page, campaign)
        import_endpoint = f'/api/containers/{campaign}/universal-vtt/import'
        scenes_endpoint = f'/api/containers/{campaign}/scenes'

        def game():
            page.goto(f'/game/{campaign}')
            page.wait_for_function('!!window.gravewrightMaps?.current && !!window.gravewrightRealtime')

        def scenes(target=page):
            response = target.request.get(scenes_endpoint)
            assert response.ok, response.text()
            return response.json()

        def directory():
            page.evaluate('gravewrightMaps.showDirectory()')
            expect(page.locator('#maps-panel')).to_be_visible()

        def modal():
            return page.locator('[data-universal-vtt]')

        def builder_import():
            page.goto(review.builder)
            wait_ready(page)
            builder_sidebar(page, 'projects')
            page.locator('[data-builder-uvtt-import]').click()
            expect(modal()).to_be_visible()

        def upload(document, name='Synthetic map.dd2vtt'):
            modal().locator('[data-uvtt-file]').set_input_files({'name': name, 'mimeType': 'application/json',
                'buffer': json.dumps(document).encode('utf-8')})

        def native(identifier):
            response = page.request.get(f'/api/maps/{identifier}/state')
            assert response.ok, response.text()
            return response.json()

        def export_scene(identifier, locale='en'):
            game()
            directory()
            row = page.locator(f'.game-directory__scene[data-scene-id="{identifier}"]')
            row.click(button='right')
            menu = page.get_by_role('menu')
            expect(menu).to_be_visible()
            menu.get_by_role('menuitem', name={'en': 'Export Universal VTT', 'pt-BR': 'Exportar Universal VTT',
                                             'es': 'Exportar Universal VTT'}[locale], exact=True).click()
            expect(modal()).to_be_visible()

        try:
            game()
            original = scenes()
            directory()
            page.locator('[data-map-panel=create]').click()
            page.locator('[data-map-create=uvtt]').click()
            expect(modal()).to_be_visible()
            page.keyboard.press('Escape')
            expect(modal()).to_have_count(0)
            assert scenes() == original
            records.append({'case': 'new-scene-chooser-opens-standard-uvtt-modal-and-escape-preserves-scenes'})

            builder_import()
            assert modal().evaluate('element=>!!element.closest("[role=dialog]")')
            before = persistent_snapshot(output)
            upload({'format': 2, 'image': 'not-a-valid-map'})
            with page.expect_response(lambda response: response.request.method == 'POST'
                                      and response.url.endswith('/universal-vtt/import')) as rejected:
                modal().locator('[data-uvtt-submit]').click()
            assert rejected.value.status == 400, rejected.value.text()
            expect(modal().locator('[data-uvtt-status]')).to_contain_text('Choose a valid Universal VTT 0.2 file.')
            assert persistent_snapshot(output) == before
            records.append({'case': 'invalid-uvtt-file-reports-application-error-without-writing-rows-or-files'})

            document = artwork_document()
            upload(document)
            modal().locator('[data-uvtt-name]').fill(imported_name)
            committed = []

            def lose_ack(route):
                response = route.fetch()
                committed.append(response.json())
                route.abort('failed')

            page.route('**' + import_endpoint, lose_ack, times=1)
            modal().locator('[data-uvtt-submit]').click()
            expect(modal()).to_have_attribute('aria-busy', 'false')
            assert len(committed) == 1, committed
            lost_id = committed[0]['scene']['id']
            retry_before = persistent_snapshot(output)
            with page.expect_response(lambda response: response.request.method == 'POST'
                                      and response.url.endswith('/universal-vtt/import')) as imported:
                modal().locator('[data-uvtt-submit]').click()
            assert imported.value.ok, imported.value.text()
            result = imported.value.json()
            identifier = result['scene']['id']
            assert identifier == lost_id
            assert result['builderEditable'] is False
            expect(modal().locator('[data-uvtt-status]')).to_contain_text('has not been activated for players')
            expect(modal().locator('[data-uvtt-warnings]')).to_contain_text('UVTT portals are imported as doors')
            assert persistent_snapshot(output) == retry_before
            projection = scenes()
            assert len(projection['maps']) == len(original['maps']) + 1
            assert projection['activeMapId'] == original['activeMapId']
            scene = next(row for row in projection['maps'] if row['id'] == identifier)
            assert scene['name'] == imported_name and scene['visibility'] == 'gm'
            assert not scene.get('builderProjectId')
            data = native(identifier)
            assert len(data['walls']) == 5 and len(data['lights']) == 1, data
            portal = next(row for row in data['walls'] if row.get('kind') == 'door')
            assert portal['door_state'] == 'closed' and portal['x1'] == 140 and portal['x2'] == 210
            assert data['lights'][0]['color'] == '#2468aa'
            assert data['lights'][0]['x'] == data['lights'][0]['y'] == 70
            assert data['lights'][0]['dim_radius'] == 2.5
            assert page.request.get(review.api).json()['projects'] == []
            records.append({'case': 'import-retries-one-logical-operation-and-creates-one-gm-only-native-scene-with-cropped-portals-origin-and-argb-light'})
            modal().locator('[data-uvtt-close]').click()

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    builder_import()
                    upload(document, 'Synthetic deliberately long Universal VTT filename for safe interchange.dd2vtt')
                    modal().locator('[data-uvtt-name]').fill(imported_name)
                    metrics = modal().evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'uvtt-import-{locale}-{width}.png'))
                    page.keyboard.press('Escape')
                    expect(modal()).to_have_count(0)
                    assert len(scenes()['maps']) == len(original['maps']) + 1
                    records.append({'case': 'localized-import-modal-handles-long-file-and-scene-names',
                                    'locale': locale, 'width': width, 'metrics': metrics})

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            game()
            catalog = page.request.get(f'/api/maps/{identifier}/automation/network').json()
            owner = next(row for row in catalog['elements'] if row['kind'] == 'door')
            states = {state: {'appearance': 'inherit'} for state in ('closed', 'open', 'locked')}
            blueprint = {'version': 2, 'kind': 'door', 'states': states, 'graphs': {'interact:closed': {
                'nodes': [{'id': 'event', 'type': 'event', 'event': 'interact:closed', 'x': 20, 'y': 30},
                    {'id': 'message', 'type': 'showMessage', 'text': 'PRIVATE_SYNTHETIC_BLUEPRINT_MESSAGE',
                     'audience': {'scope': 'trigger'}, 'x': 400, 'y': 30}],
                'edges': [{'kind': 'execution', 'from': 'event', 'to': 'message', 'output': 'next'}]}}}
            saved = post(page, f'/api/maps/{identifier}/automation/network/{owner["id"]}', {
                'request_id': str(uuid4()), 'expected_version': owner['version'], 'expected_project_version': None,
                'blueprint': blueprint})
            assert saved['status'] == 200, saved
            before_export = persistent_snapshot(output)
            export_scene(identifier)
            pending = []
            export_route = f'**/api/maps/{identifier}/universal-vtt'
            page.route(export_route, lambda route: pending.append(route), times=1)
            with page.expect_request(lambda request: request.url.endswith('/universal-vtt')):
                modal().locator('[data-uvtt-submit]').click()
            expect(modal()).to_have_attribute('aria-busy', 'true')
            assert len(pending) == 1
            page.keyboard.press('Escape')
            expect(modal()).to_have_count(0)
            pending[0].abort('aborted')
            page.unroute(export_route)
            assert persistent_snapshot(output) == before_export
            records.append({'case': 'read-only-export-can-close-while-preparation-is-pending-without-locking-the-game'})
            export_scene(identifier)
            with page.expect_response(lambda response: response.url.endswith('/universal-vtt')) as exported:
                modal().locator('[data-uvtt-submit]').click()
            assert exported.value.ok, exported.value.text()
            expect(modal().locator('[data-uvtt-warnings]')).to_contain_text('UVTT does not include behaviors, variables, timers or scene automation.')
            expect(modal().locator('[data-uvtt-download]')).to_be_visible()
            with page.expect_download() as downloading:
                modal().locator('[data-uvtt-download]').click()
            download = downloading.value
            assert download.suggested_filename.endswith('.uvtt')
            target = output / 'downloaded.uvtt'
            download.save_as(target)
            portable = json.loads(target.read_text(encoding='utf-8'))
            assert portable['format'] == .2 and len(portable['portals']) == len(portable['lights']) == 1
            assert len(portable['line_of_sight']) == 4
            assert 'PRIVATE_SYNTHETIC_BLUEPRINT_MESSAGE' not in json.dumps(portable)
            assert set(portable) == {'format', 'resolution', 'line_of_sight', 'objects_line_of_sight', 'portals', 'environment', 'lights', 'image'}
            assert persistent_snapshot(output) == before_export
            page.screenshot(path=str(output / 'uvtt-export-warnings.png'))
            records.append({'case': 'scene-context-export-downloads-portable-json-with-loss-warnings-and-no-private-graph-or-persisted-changes'})
            modal().locator('[data-uvtt-close]').click()

            for locale in ('en', 'pt-BR', 'es'):
                change_locale(page, locale, campaign)
                for width in (1440, 390):
                    page.set_viewport_size({'width': 1440, 'height': 900})
                    export_scene(identifier, locale)
                    modal().locator('[data-uvtt-submit]').click()
                    expect(modal().locator('[data-uvtt-download]')).to_be_visible()
                    page.set_viewport_size({'width': width, 'height': 900 if width == 1440 else 844})
                    metrics = modal().evaluate(MEASURE)
                    assert not metrics['tiny'] and not metrics['overflow'], metrics
                    page.screenshot(path=str(output / f'uvtt-export-{locale}-{width}.png'))
                    page.keyboard.press('Escape')
                    expect(modal()).to_have_count(0)
                    assert persistent_snapshot(output) == before_export
                    records.append({'case': 'localized-export-shows-download-and-loss-warnings-at-desktop-and-phone-width',
                                    'locale': locale, 'width': width, 'metrics': metrics})

            change_locale(page, 'en', campaign)
            page.set_viewport_size({'width': 1440, 'height': 900})
            builder_import()
            upload(portable, 'Synthetic roundtrip.uvtt')
            modal().locator('[data-uvtt-name]').fill('Synthetic roundtrip scene')
            with page.expect_response(lambda response: response.request.method == 'POST'
                                      and response.url.endswith('/universal-vtt/import')) as imported:
                modal().locator('[data-uvtt-submit]').click()
            assert imported.value.ok, imported.value.text()
            roundtrip_id = imported.value.json()['scene']['id']
            restored = native(roundtrip_id)

            def geometry(values):
                return sorted(tuple(round(row[key], 6) for key in ('x1', 'y1', 'x2', 'y2')) for row in values)

            assert geometry(restored['walls']) == geometry(data['walls'])
            assert restored['lights'][0]['color'] == '#2468aa'
            assert restored['lights'][0]['x'] == restored['lights'][0]['y'] == 70
            assert not any(row.get('blueprint') for row in restored['walls'])
            assert scenes()['activeMapId'] == original['activeMapId']
            modal().locator('[data-uvtt-close]').click()
            records.append({'case': 'downloaded-uvtt-reimports-with-identical-pixel-geometry-and-light-without-restoring-omitted-behaviors'})

            for role in ('player', 'streamer'):
                guest = browser.new_context(base_url=base)
                guests.append(guest)
                guest.add_cookies([{**seed['sessions'][role], 'url': base}])
                target = guest.new_page()
                observe(target)
                target.goto(f'/game/{campaign}')
                target.wait_for_function('!!window.gravewrightRealtime')
                assert identifier not in {row['id'] for row in scenes(target)['maps']}
                denied = target.request.get(f'/api/maps/{identifier}/universal-vtt')
                assert denied.status in (403, 404), (role, denied.status)
                denied = target.request.get(f'/api/maps/{seed["broadcastScene"]}/universal-vtt')
                assert denied.status in (403, 404), (role, denied.status)
                csrf = target.request.get('/__gravewright/csrf').json()
                denied = target.request.post(import_endpoint, headers={csrf['header']: csrf['token']}, multipart={
                    'request_id': str(uuid4()), 'name': 'Unauthorized import',
                    'file': {'name': 'Synthetic denied.uvtt', 'mimeType': 'application/json', 'buffer': json.dumps(document).encode()}})
                assert denied.status in (403, 404), (role, denied.status)
            assert len(scenes()['maps']) == len(original['maps']) + 2
            records.append({'case': 'player-and-streamer-neither-see-private-imports-nor-import-or-export-maps'})
        except Exception:
            if not page.is_closed():
                page.screenshot(path=str(output / 'failure.png'), full_page=True)
            (output / 'progress.json').write_text(json.dumps({'cases': records, 'pageErrors': errors,
                                                            'nativeDialogs': dialogs}, indent=2), encoding='utf-8')
            raise
        finally:
            for guest in guests:
                guest.close()
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'assets': 'Generated solid PNG and explicit synthetic Universal VTT 0.2 geometry.'}


if __name__ == '__main__':
    harness.check_browser = check_browser
    harness.main()
