"""Exercise project-local collections through the real Map Builder interface.

Only synthetic uploads and an isolated installation-local fixture are used.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import traceback
from urllib.request import urlopen

from map_builder import ROOT, MEASURE, builder_library_settings, change_locale, fixture_environment, serve
from map_builder_families import image_payload
from map_builder_reference import set_name, wait_ready


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    records, errors, requests, dialogs, uploads = [], [], [], [], []
    campaign = seed['campaign']
    builder = f'{base}/game/{campaign}/map-builder'
    api = f'{base}/api/containers/{campaign}/map-builder'
    family = 'Stone variations — São João'
    stone, garden, furniture = 'Dungeon — Stone', 'Garden — Moss', 'Furniture — Oak'
    long_collection = 'Collection — São João stone tiles with a deliberately long authored collection'
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(viewport={'width': 1586, 'height': 992})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('requestfailed', lambda request: requests.append({'url': request.url, 'error': request.failure}))
        page.on('response', lambda response: uploads.append(response) if '/library/upload' in response.url else None)

        def native_dialog(dialog):
            dialogs.append({'type': dialog.type, 'message': dialog.message})
            dialog.dismiss()

        page.on('dialog', native_dialog)
        try:
            page.goto(builder)
            wait_ready(page)
            set_name(page, 'Collections regression — São João')

            def open_import():
                page.locator('[data-builder-import]').click()
                modal = page.locator('[data-builder-import-modal]')
                expect(modal).to_be_visible()
                field = modal.locator('[data-builder-import-collection]')
                expect(field).to_be_visible()
                expect(field).to_have_attribute('maxlength', '80')
                datalist = modal.locator('[data-builder-import-collections]')
                assert field.get_attribute('list') == datalist.get_attribute('id')
                return modal

            def import_file(role, collection, filename, color, asset_family=''):
                modal = open_import()
                modal.locator('[data-builder-import-role]').select_option(role)
                modal.locator('[data-builder-import-family]').fill(asset_family)
                modal.locator('[data-builder-import-collection]').fill(collection)
                modal.locator('[data-builder-upload]').set_input_files(image_payload(filename, color))
                with page.expect_response(lambda response: '/library/upload' in response.url) as uploaded:
                    modal.locator('[data-builder-import-submit]').click()
                assert uploaded.value.status == 201, uploaded.value.text()
                expect(modal).to_have_count(0)
                wait_ready(page)
                return uploaded.value.json()['id']

            def save():
                if page.locator('[data-map-builder]').get_attribute('data-save-state') != 'saved':
                    # Flushing a pending, unchanged snapshot needs no POST.
                    page.locator('[data-builder-save]').click()
                expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved')
                project_id = page.evaluate("new URL(location.href).searchParams.get('project')")
                persisted = page.request.get(api + '/projects/' + project_id)
                assert persisted.ok, persisted.text()
                return persisted.json()['project']

            def individual_ids():
                return page.locator('[data-builder-assets] [data-asset-id]').evaluate_all(
                    'cards => cards.map(card => card.dataset.assetId)')

            def family_cards():
                return page.locator('[data-builder-assets] [data-family-name]')

            def filter_collection(value):
                builder_library_settings(page)
                page.locator('[data-builder-collection-filter]').select_option(value)

            def edit_asset(asset_id):
                page.locator(f'[data-asset-id="{asset_id}"]').dblclick()
                editor = page.locator('[data-builder-asset-modal]')
                expect(editor).to_be_visible()
                expect(editor.locator('[data-builder-import-collection]')).to_be_visible()
                return editor

            initial = save()
            modal = open_import()
            modal.locator('[data-builder-import-collection]').fill('Cancelled collection')
            modal.locator('[data-builder-import-family]').fill('Cancelled family')
            modal.locator('[data-builder-upload]').set_input_files(image_payload('Cancelled.png', '#73705c'))
            modal.locator('[data-builder-import-cancel]').click()
            expect(modal).to_have_count(0)
            assert not uploads
            assert save()['document'] == initial['document']
            records.append({'case': 'collection-import-is-optional-and-cancellable', 'uploads': 0})

            a = import_file('floor', '  ' + stone + '  ', 'Stone A.png', '#62776f', family)
            b = import_file('floor', stone, 'Stone B.png', '#76674f', family)
            c = import_file('floor', garden, 'Stone C.png', '#566e76', family)
            loose = import_file('floor', garden, 'Loose grass.png', '#5a7846')
            table = import_file('decoration', furniture, 'Oak table.png', '#876445')
            project = save()
            project_id = project['id']
            metadata = {entry['assetId']: entry for entry in project['document']['assets']}
            assert [metadata[value]['collection'] for value in (a, b, c, loose, table)] == [stone, stone, garden, garden, furniture]
            original_names = {asset['id']: asset['name'] for asset in page.request.get(api).json()['assets']}
            records.append({'case': 'typed-import-persists-trimmed-project-collections', 'assets': len(metadata)})

            page.locator('[data-builder-role=floor]').click()
            builder_library_settings(page)
            details = page.locator('.map-builder__asset-details')
            expect(details.locator('summary')).to_be_visible()
            expect(page.locator('[data-builder-collection-filter]')).to_be_visible()
            values = page.locator('[data-builder-collection-filter] option').evaluate_all('options => options.map(option => option.value)')
            assert set(values) == {'', stone, garden, furniture} and len(values) == len(set(values)), values
            filter_collection(stone)
            assert set(individual_ids()) == {a, b}, individual_ids()
            expect(family_cards()).to_have_count(1)
            expect(family_cards().locator('.map-builder__family-count')).to_have_text('3')
            filter_collection(garden)
            assert set(individual_ids()) == {c, loose}, individual_ids()
            expect(family_cards()).to_have_count(1)
            filter_collection(furniture)
            assert individual_ids() == []
            expect(family_cards()).to_have_count(0)
            page.locator('[data-builder-role=decoration]').click()
            assert individual_ids() == [table]
            page.locator('[data-builder-role=floor]').click()
            filter_collection(stone)
            family_cards().click()
            expect(page.locator('[data-builder-brush-material]')).to_have_value('family:' + family)
            page.evaluate('() => { window.collectionRandom = Math.random; Math.random = () => .999; }')
            try:
                position = page.locator('[data-builder-canvas]').evaluate("""canvas => {
                  const point = new DOMPoint(2.2, 2.2).matrixTransform(canvas.getScreenCTM());
                  return {x: point.x, y: point.y};
                }""")
                page.mouse.click(position['x'], position['y'])
            finally:
                page.evaluate('() => { Math.random = window.collectionRandom; delete window.collectionRandom; }')
            project = save()
            assert project['document']['floors'][-1]['assetId'] == c, project['document']['floors']
            records.append({'case': 'collection-filters-cards-without-narrowing-family-members', 'familyMembers': 3})

            filter_collection('')
            assert set(individual_ids()) == {a, b, c, loose}
            expect(family_cards()).to_have_count(1)
            page.locator('[data-builder-search]').fill('absent synthetic resource')
            assert individual_ids() == []
            expect(family_cards()).to_have_count(0)
            page.locator('[data-builder-search]').fill('')
            assert len(individual_ids()) == len(set(individual_ids())) == 4
            records.append({'case': 'collection-and-search-filters-do-not-leave-empty-family-or-duplicate-cards'})

            editor = edit_asset(a)
            expect(editor.locator('[data-builder-import-collection]')).to_have_value(stone)
            editor.locator('[data-builder-import-name-input]').fill('Renamed stone — authored alias')
            editor.locator('[data-builder-import-collection]').fill('  Crypt — Revised  ')
            editor.locator('[data-builder-import-submit]').click()
            expect(editor).to_have_count(0)
            metadata = {entry['assetId']: entry for entry in save()['document']['assets']}
            assert metadata[a]['collection'] == 'Crypt — Revised' and metadata[a]['family'] == family
            assert metadata[a]['name'] == 'Renamed stone — authored alias'
            assert {asset['id']: asset['name'] for asset in page.request.get(api).json()['assets']} == original_names
            before_cancel = save()['document']
            editor = edit_asset(b)
            editor.locator('[data-builder-import-collection]').fill('Discard this edit')
            editor.locator('[data-builder-import-cancel]').click()
            expect(editor).to_have_count(0)
            assert save()['document'] == before_cancel
            editor = edit_asset(a)
            expect(editor.locator('[data-builder-import-collection]')).to_have_value('Crypt — Revised')
            editor.locator('[data-builder-import-collection]').fill('')
            editor.locator('[data-builder-import-submit]').click()
            expect(editor).to_have_count(0)
            metadata = {entry['assetId']: entry for entry in save()['document']['assets']}
            assert 'collection' not in metadata[a] and metadata[a]['family'] == family
            values = page.locator('[data-builder-collection-filter] option').evaluate_all('options => options.map(option => option.value)')
            assert 'Crypt — Revised' not in values
            records.append({'case': 'edit-collection-prefills-renames-cancels-and-clears-without-renaming-campaign-images'})

            page.locator(f'[data-asset-id="{b}"]').click()
            builder_library_settings(page)
            expect(page.locator('[data-builder-asset-name]')).to_be_visible()
            expect(page.locator('[data-builder-asset-role]')).to_be_visible()
            legacy_collection = page.locator('[data-builder-asset-collection]')
            expect(legacy_collection).to_be_visible()
            legacy_collection.fill('Legacy — Archive')
            legacy_collection.press('Tab')
            assert next(entry for entry in save()['document']['assets'] if entry['assetId'] == b)['collection'] == 'Legacy — Archive'
            filter_collection('')
            editor = edit_asset(c)
            editor.locator('[data-builder-import-collection]').fill(long_collection)
            editor.locator('[data-builder-import-submit]').click()
            expect(editor).to_have_count(0)
            project = save()
            assert next(entry for entry in project['document']['assets'] if entry['assetId'] == c)['collection'] == long_collection
            records.append({'case': 'library-settings-scrolls-to-operable-classification-fields'})

            other = context.new_page()
            try:
                other.on('pageerror', lambda error: errors.append(str(error)))
                other.on('dialog', native_dialog)
                other.goto(builder)
                wait_ready(other)
                set_name(other, 'Separate collection project')
                with other.expect_response(lambda response: '/map-builder/projects/' in response.url
                                           and response.request.method == 'POST') as saved:
                    other.locator('[data-builder-save]').click()
                assert saved.value.ok, saved.value.text()
                assert saved.value.json()['project']['document']['assets'] == []
                builder_library_settings(other)
                assert other.locator('[data-builder-collection-filter] option').count() == 1
            finally:
                other.close()
            assert page.request.get(api + '/projects/' + project_id).json()['project']['document'] == project['document']
            page.reload()
            wait_ready(page)
            filter_collection('Legacy — Archive')
            assert individual_ids() == [b]
            expect(family_cards()).to_have_count(1)
            assert save()['document'] == project['document']
            records.append({'case': 'collections-persist-after-reload-and-remain-project-local'})

            # Seed a disposable mixed group, then use actual pointer selection and dragging.
            group = page.evaluate("""async endpoint => {
              const csrf = await (await fetch('/__gravewright/csrf')).json();
              const id = crypto.randomUUID(), layerId = crypto.randomUUID();
              const document = {schemaVersion: 3, name: 'Mixed group at a fractional edge',
                columns: 20, rows: 20, cellSize: 32, background: '#253038',
                layers: [{id: layerId, name: 'Base', visible: true, locked: false}],
                floors: [], doors: [], lights: [], assets: [],
                walls: [{id: crypto.randomUUID(), layerId, assetId: null,
                  x1: 10, y1: 5, x2: 12, y2: 5, thickness: .2}],
                decorations: [{id: crypto.randomUUID(), layerId, assetId: null,
                  x: 18.6, y: 5, width: 1, height: 1, rotation: 0}]};
              const response = await fetch(endpoint + '/projects/' + id, {method: 'POST',
                headers: {'Content-Type': 'application/json', [csrf.header]: csrf.token},
                body: JSON.stringify({request_id: crypto.randomUUID(), expected_version: 0,
                  folder_id: null, document})});
              const result = await response.json();
              if (!response.ok) throw new Error(JSON.stringify(result));
              return result.project;
            }""", api)
            page.goto(builder + '?project=' + group['id'])
            wait_ready(page)
            page.locator('[data-builder-quick-tool=select]').click()

            def position(x, y):
                return page.locator('[data-builder-canvas]').evaluate("""(canvas, point) => {
                  const screen = new DOMPoint(point.x, point.y).matrixTransform(canvas.getScreenCTM());
                  return {x: screen.x, y: screen.y};
                }""", {'x': x, 'y': y})

            wall_position, decoration_position = position(11, 5), position(19.1, 5.5)
            page.mouse.click(wall_position['x'], wall_position['y'])
            page.keyboard.down('Shift')
            try:
                page.mouse.click(decoration_position['x'], decoration_position['y'])
            finally:
                page.keyboard.up('Shift')
            expect(page.locator('[data-builder-selection] > *')).to_have_count(2)
            for target_x, expected_wall, expected_decoration in ((12, 10, 18.6), (10, 9, 17.6)):
                start, target = position(11, 5), position(target_x, 5)
                page.mouse.move(start['x'], start['y'])
                page.mouse.down()
                page.mouse.move(target['x'], target['y'], steps=4)
                page.mouse.up()
                moved = save()['document']
                assert moved['walls'][0]['x1'] == expected_wall, moved['walls']
                assert abs(moved['decorations'][0]['x'] - expected_decoration) < 1e-9, moved['decorations']
            records.append({'case': 'pointer-drag-keeps-mixed-wall-group-snapped-at-fractional-edge',
                            'blockedRightDrag': True, 'leftDragCells': 1})

            for locale, collection_label, settings_label in (
                ('en', 'Collection', 'Library settings'),
                ('pt-BR', 'Coleção', 'Configurações da biblioteca'),
                ('es', 'Colección', 'Configuración de la biblioteca'),
            ):
                change_locale(page, locale, campaign)
                for width, height in ((320, 700), (390, 844)):
                    page.set_viewport_size({'width': width, 'height': height})
                    page.goto(builder + '?project=' + project_id)
                    wait_ready(page)
                    expect(page.locator('html')).to_have_attribute('lang', locale)
                    modal = open_import()
                    expect(modal.locator('[data-builder-import-collection]').locator('..')).to_contain_text(collection_label)
                    suggestions = modal.locator('[data-builder-import-collections] option').evaluate_all('options => options.map(option => option.value)')
                    assert long_collection in suggestions
                    modal.locator('[data-builder-import-collection]').fill(long_collection)
                    import_metrics = modal.evaluate(MEASURE)
                    assert not import_metrics['tiny'] and not import_metrics['overflow'], import_metrics
                    page.screenshot(path=str(output / f'collections-import-{locale}-{width}.png'))
                    page.keyboard.press('Escape')
                    filter_collection(long_collection)
                    expect(details.locator('summary')).to_have_text(settings_label)
                    assert individual_ids() == [c]
                    expect(family_cards()).to_have_count(1)
                    page.locator(f'[data-asset-id="{c}"]').click()
                    builder_library_settings(page)
                    expect(page.locator('[data-builder-asset-collection]')).to_have_value(long_collection)
                    page.locator('[data-builder-collection-filter]').scroll_into_view_if_needed()
                    expect(page.locator('[data-builder-collection-filter]')).to_be_in_viewport()
                    page.screenshot(path=str(output / f'collections-filter-{locale}-{width}.png'))
                    page.locator('[data-builder-asset-collection]').scroll_into_view_if_needed()
                    expect(page.locator('[data-builder-asset-collection]')).to_be_in_viewport()
                    layout_metrics = page.locator('[data-map-builder]').evaluate(MEASURE)
                    assert not layout_metrics['tiny'] and not layout_metrics['overflow'], layout_metrics
                    page.screenshot(path=str(output / f'collections-library-{locale}-{width}.png'))
                    editor = edit_asset(c)
                    expect(editor.locator('[data-builder-import-collection]')).to_have_value(long_collection)
                    edit_metrics = editor.evaluate(MEASURE)
                    assert not edit_metrics['tiny'] and not edit_metrics['overflow'], edit_metrics
                    page.screenshot(path=str(output / f'collections-edit-{locale}-{width}.png'))
                    page.keyboard.press('Escape')
                    records.append({'case': 'localized-responsive-collection-controls', 'locale': locale,
                                    'width': width, 'import': import_metrics, 'library': layout_metrics, 'edit': edit_metrics})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    assert not [request for request in requests if request['error'] != 'net::ERR_ABORTED'], requests
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'nativeDialogs': dialogs,
            'failedRequests': requests, 'artwork': 'Synthetic uploaded tiles only.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--fixture', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--port', type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.serve:
        serve(args.fixture, args.port)
        return
    output = (args.output or ROOT / 'data/map-builder-collections' /
              datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError('Use a fresh, empty output directory.')
    output.mkdir(parents=True, exist_ok=True)
    fixture = output / 'fixture'
    fixture.mkdir()
    with socket.socket() as connection:
        connection.bind(('127.0.0.1', 0))
        port = connection.getsockname()[1]
    fixture_environment(fixture, port)
    executable = sys._base_executable if os.name == 'nt' else sys.executable
    command = [executable, '-B', '-X', 'utf8', str(Path(__file__).resolve())]
    base = f'http://127.0.0.1:{port}'
    with (output / 'server.log').open('w', encoding='utf-8') as log:
        server = subprocess.Popen([*command, '--serve', '--fixture', str(fixture), '--port', str(port)],
                                  cwd=ROOT, env=os.environ.copy(), stdout=log, stderr=log)
        try:
            for _ in range(300):
                if server.poll() is not None:
                    raise RuntimeError(f'Fixture exited; inspect {output / "server.log"}')
                try:
                    with urlopen(base, timeout=1):
                        break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Fixture did not become ready.')
            seed = json.loads((fixture / 'seed.json').read_text(encoding='utf-8'))
            report = check_browser(base, seed, output, args.browser_executable)
            (output / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
            print(json.dumps({'passed': True, 'cases': len(report['cases']), 'report': str(output / 'report.json')}))
        except Exception:
            (output / 'failure.txt').write_text(traceback.format_exc(), encoding='utf-8')
            raise
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
            (output / 'server-exit.json').write_text(json.dumps({'pid': server.pid, 'exitCode': server.returncode}), encoding='utf-8')


if __name__ == '__main__':
    main()
