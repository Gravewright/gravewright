"""Exercise explicit Map Builder imports, asset families and four paint modes.

Only synthetic images and disposable installation-local campaigns are used.
The browser drives import, selection, pointer input, history and generation.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import traceback
from urllib.request import urlopen

from map_builder import ROOT, MEASURE, builder_tool, change_locale, fixture_environment, serve
from map_builder_reference import reference_geometry, set_name, wait_ready


def image_payload(name, color):
    from PIL import Image, ImageDraw

    image = Image.new('RGB', (64, 64), color)
    ImageDraw.Draw(image).rectangle((3, 3, 60, 60), outline='#10191c', width=3)
    content = BytesIO()
    image.save(content, 'PNG')
    return {'name': name, 'mimeType': 'image/png', 'buffer': content.getvalue()}


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    records, errors, requests, dialogs, uploads = [], [], [], [], []
    campaign = seed['campaign']
    builder = f'{base}/game/{campaign}/map-builder'
    api = f'{base}/api/containers/{campaign}/map-builder'
    family = 'Dungeon tiles — São João'
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
            reference_geometry(page)

            def open_import():
                page.locator('[data-builder-import]').click()
                modal = page.locator('[data-builder-import-modal]')
                expect(modal).to_be_visible()
                expect(modal).to_have_attribute('role', 'dialog')
                expect(modal).to_have_attribute('aria-modal', 'true')
                assert modal.evaluate("element => element.localName") != 'dialog'
                return modal

            def import_files(role, name, files):
                modal = open_import()
                modal.locator('[data-builder-import-role]').select_option(role)
                modal.locator('[data-builder-import-family]').fill(name)
                modal.locator('[data-builder-upload]').set_input_files(files)
                start = len(uploads)
                modal.locator('[data-builder-import-submit]').click()
                expect(modal).to_have_count(0)
                wait_ready(page)
                responses = uploads[start:]
                assert len(responses) == len(files), (len(responses), len(files))
                assert all(response.status == 201 for response in responses), [response.text() for response in responses]
                return [response.json()['id'] for response in responses]

            def save():
                if page.locator('[data-map-builder]').get_attribute('data-save-state') != 'saved':
                    with page.expect_response(lambda response: '/map-builder/projects/' in response.url
                                              and response.request.method == 'POST'
                                              and not response.url.endswith(('/generate', '/update'))) as saved:
                        page.locator('[data-builder-save]').click()
                    assert saved.value.ok, saved.value.text()
                    return saved.value.json()['project']
                project_id = page.evaluate("new URL(location.href).searchParams.get('project')")
                persisted = page.request.get(api + '/projects/' + project_id)
                assert persisted.ok, persisted.text()
                return persisted.json()['project']

            def point(x, y):
                return page.locator('[data-builder-canvas]').evaluate("""(canvas, point) => {
                  const screen = new DOMPoint(point.x, point.y).matrixTransform(canvas.getScreenCTM());
                  return {x: screen.x, y: screen.y};
                }""", {'x': x, 'y': y})

            def stroke(points, check_preview=False):
                is_floor = page.locator('[data-builder-tool=floor]').get_attribute('aria-pressed') == 'true'
                start, *rest = [point(x, y) for x, y in points]
                page.mouse.move(start['x'], start['y'])
                page.mouse.down()
                for target in rest:
                    page.mouse.move(target['x'], target['y'], steps=1)
                if check_preview:
                    preview = page.locator('[data-builder-floors]' if is_floor else '[data-builder-ghost]').evaluate("""ghost => {
                      const references=[...ghost.querySelectorAll('[fill],[stroke]')].flatMap(element =>
                        ['fill','stroke'].map(attribute => element.getAttribute(attribute)).filter(Boolean))
                        .filter(value => value.startsWith('url(#'));
                      return {count: references.length, missing: references.filter(value => {
                        const id=value.slice(5,-1), pattern=document.getElementById(id);
                        return pattern?.localName!=='pattern'
                          || !pattern.querySelector('image')?.getAttribute('href')?.startsWith('/game/map-assets/');
                      })};
                    }""")
                    assert preview['count'] > 0 and not preview['missing'], preview
                page.mouse.up()

            def click(x, y):
                position = point(x, y)
                page.mouse.click(position['x'], position['y'])

            def floors():
                return page.locator('[data-builder-floors] [data-object-id]')

            # Choosing files waits for explicit submission and remains cancellable.
            modal = open_import()
            expect(modal.locator('[data-builder-import-role] option')).to_have_count(4)
            assert modal.locator('[data-builder-import-role] option').evaluate_all(
                'options => options.map(option => option.value)') == ['floor', 'wall', 'door', 'decoration']
            modal.locator('[data-builder-import-submit]').click()
            expect(modal).to_be_visible()
            assert not uploads, 'An empty import must not upload an image.'
            modal.locator('[data-builder-upload]').set_input_files(image_payload('cancelled.png', '#624b5a'))
            assert not uploads, 'Choosing files must wait for Import.'
            modal.locator('[data-builder-import-cancel]').click()
            expect(modal).to_have_count(0)
            expect(page.locator('[data-builder-import]')).to_be_focused()
            modal = open_import()
            assert modal.locator('[data-builder-upload]').input_value() == '', 'A cancelled selection must not carry into the next import.'
            tab_order = modal.locator('button,input,select,textarea,a[href],[tabindex]').evaluate_all("""elements => elements
              .filter(element => !element.disabled && element.tabIndex >= 0 && element.getClientRects().length)
              .map(element => element.outerHTML)""")
            assert tab_order, 'Import needs keyboard-operable controls.'
            modal.evaluate("""element => {
              const fields=[...element.querySelectorAll('button,input,select,textarea,a[href],[tabindex]')]
                .filter(field => !field.disabled && field.tabIndex >= 0 && field.getClientRects().length);
              fields.at(-1).focus();
            }""")
            page.keyboard.press('Tab')
            assert modal.evaluate("""element => {
              const first=[...element.querySelectorAll('button,input,select,textarea,a[href],[tabindex]')]
                .find(field => !field.disabled && field.tabIndex >= 0 && field.getClientRects().length);
              return document.activeElement===first;
            }"""), 'Tab must stay inside the import modal.'
            page.keyboard.press('Escape')
            expect(page.locator('[data-builder-import-modal]')).to_have_count(0)
            assert not uploads
            records.append({'case': 'explicit-import-type-cancel-and-keyboard', 'writesBeforeSubmit': 0})

            # Type selection is independent of the currently active Wall tool.
            first = import_files('floor', family, [image_payload('Dungeon A.png', '#7c6a54'),
                                                    image_payload('Dungeon B.png', '#526d71')])
            expect(page.locator('[data-builder-tool=floor]')).to_have_attribute('aria-pressed', 'true')
            family_card = page.locator('[data-family-name]').filter(has_text=family)
            expect(family_card).to_have_count(1)
            expect(family_card).to_be_visible()
            second = import_files('floor', family, [image_payload('Dungeon C.png', '#69764d')])
            asset_ids = first + second
            family_card.click()
            material = page.locator('[data-builder-brush-material]')
            expect(material).to_have_value('family:' + family)
            project = save()
            classified = project['document']['assets']
            assert {entry['assetId'] for entry in classified if entry.get('family') == family} == set(asset_ids), classified
            assert all(entry['role'] == 'floor' for entry in classified), classified
            records.append({'case': 'typed-family-multi-import-and-add-member', 'assets': asset_ids, 'family': family})

            # Existing images can join and leave a family without another upload.
            loose_id = import_files('floor', '', [image_payload('Loose floor.png', '#607453')])[0]
            upload_count = len(uploads)
            page.locator(f'[data-asset-id="{loose_id}"]').dblclick()
            editor = page.locator('[data-builder-asset-modal]')
            expect(editor).to_be_visible()
            expect(editor.locator('[data-builder-import-files]')).to_be_hidden()
            editor.locator('[data-builder-import-family]').fill(family)
            editor.locator('[data-builder-import-submit]').click()
            expect(editor).to_have_count(0)
            entry = next(value for value in save()['document']['assets'] if value['assetId'] == loose_id)
            assert entry['family'] == family, entry
            page.locator(f'[data-asset-id="{loose_id}"]').dblclick()
            editor = page.locator('[data-builder-asset-modal]')
            editor.locator('[data-builder-import-family]').fill('')
            editor.locator('[data-builder-import-submit]').click()
            expect(editor).to_have_count(0)
            entry = next(value for value in save()['document']['assets'] if value['assetId'] == loose_id)
            assert 'family' not in entry and len(uploads) == upload_count, entry
            records.append({'case': 'existing-asset-joins-and-leaves-family', 'additionalUploads': 0})

            # A failed second file retains the first import and retries only the missing file.
            before_retry = page.request.get(api).json()['assets']
            retry_family = 'Retry dungeon family'
            retry_modal = open_import()
            retry_modal.locator('[data-builder-import-role]').select_option('floor')
            retry_modal.locator('[data-builder-import-family]').fill(retry_family)
            retry_modal.locator('[data-builder-upload]').set_input_files([
                image_payload('Retry tile A.png', '#487257'), image_payload('Retry tile B.png', '#795b47')])
            attempts = []

            def temporary_failure(route):
                attempts.append(route.request.url)
                if len(attempts) == 2:
                    route.fulfill(status=503, content_type='application/json',
                                  body=json.dumps({'error': 'Synthetic temporary upload failure.'}))
                else:
                    route.continue_()

            upload_route = '**/library/upload'
            page.route(upload_route, temporary_failure)
            before_retry_responses = len(uploads)
            try:
                retry_modal.locator('[data-builder-import-submit]').click()
                expect(retry_modal.locator('[role=alert]')).to_be_visible()
                assert len(page.request.get(api).json()['assets']) == len(before_retry) + 1
                retry_modal.locator('[data-builder-import-submit]').click()
                expect(retry_modal).to_have_count(0)
            finally:
                page.unroute(upload_route, temporary_failure)
            assert len(attempts) == 3, attempts
            assert [response.status for response in uploads[before_retry_responses:]] == [201, 503, 201]
            after_retry = page.request.get(api).json()['assets']
            retry_ids = {asset['id'] for asset in after_retry} - {asset['id'] for asset in before_retry}
            assert len(retry_ids) == 2, retry_ids
            retry_entries = [entry for entry in save()['document']['assets'] if entry.get('family') == retry_family]
            assert {entry['assetId'] for entry in retry_entries} == retry_ids, retry_entries
            records.append({'case': 'partial-upload-retry-keeps-completed-file', 'requests': 3, 'newAssets': 2})

            modal = open_import()
            modal.locator('[data-builder-import-role]').select_option('wall')
            modal.locator('[data-builder-import-family]').fill(family)
            modal.locator('[data-builder-upload]').set_input_files(image_payload('wrong-family-type.png', '#60616c'))
            before_invalid = len(uploads)
            modal.locator('[data-builder-import-submit]').click()
            expect(modal.locator('[role=alert]')).to_be_visible()
            assert len(uploads) == before_invalid, 'A family containing floors must reject wall uploads before writing.'
            modal.locator('[data-builder-import-cancel]').click()
            records.append({'case': 'family-type-conflict-rejected-before-upload', 'uploads': 0})

            builder_tool(page, 'floor')
            material.select_option('family:' + family)
            page.locator('[data-builder-paint-mode]').select_option('brush')
            # A controlled uniform source makes all three variants observable without chance-based assertions.
            page.evaluate("""() => { window.familyOriginalRandom = Math.random; let index=0;
              Math.random = () => [0.05, 0.45, 0.95][index++ % 3]; }""")
            try:
                stroke([(1.2, 2.2), (12.2, 2.2), (1.2, 2.2)], check_preview=True)
            finally:
                page.evaluate('() => { Math.random = window.familyOriginalRandom; delete window.familyOriginalRandom; }')
            expect(floors()).to_have_count(12)
            painted = save()['document']['floors']
            assert {(tile['x'], tile['y']) for tile in painted} == {(x, 2) for x in range(1, 13)}, painted
            assert {tile['assetId'] for tile in painted} == set(asset_ids), painted
            assert all(tile['width'] == tile['height'] == 1 for tile in painted), painted
            page.locator('[data-builder-undo]').click()
            expect(floors()).to_have_count(0)
            page.locator('[data-builder-redo]').click()
            expect(floors()).to_have_count(12)
            assert save()['document']['floors'] == painted, 'Redo must keep the originally selected concrete variants and IDs.'
            records.append({'case': 'continuous-brush-interpolation-revisit-and-history', 'cells': 12, 'allVariants': True})

            stroke([(5.2, 2.2)])
            expect(floors()).to_have_count(12)
            repainted = save()['document']['floors']
            assert len({(tile['x'], tile['y']) for tile in repainted}) == 12, repainted
            page.locator('[data-builder-undo]').click()
            assert save()['document']['floors'] == painted, 'Undo repaint must restore the replaced tile and its original ID.'
            records.append({'case': 'repainting-replaces-a-cell-and-undo-restores-it', 'cells': 12})

            page.locator('[data-builder-paint-mode]').select_option('rectangle')
            stroke([(4, 9), (8, 12)])
            rectangle = save()['document']['floors']
            added = [tile for tile in rectangle if tile['id'] not in {value['id'] for value in painted}]
            assert {(tile['x'], tile['y']) for tile in added} == {(x, y) for x in range(4, 8) for y in range(9, 12)}, added
            assert all(tile['assetId'] in asset_ids and tile['width'] == tile['height'] == 1 for tile in added), added
            records.append({'case': 'rectangle-family-cell-fill', 'cells': len(added)})

            page.locator('[data-builder-paint-mode]').select_option('circle')
            stroke([(14, 12), (17, 12)])
            circle = save()['document']['floors']
            added = [tile for tile in circle if tile['id'] not in {value['id'] for value in rectangle}]
            assert 4 < len(added) < 36, added
            assert all(tile['assetId'] in asset_ids and tile['width'] == tile['height'] == 1 for tile in added), added
            assert all((tile['x'] + .5 - 14) ** 2 + (tile['y'] + .5 - 12) ** 2 <= 9 for tile in added), added
            assert len({(tile['x'], tile['y']) for tile in added}) == len(added), added
            records.append({'case': 'circle-family-cell-fill', 'cells': len(added)})

            page.locator('[data-builder-paint-mode]').select_option('polygon')
            for position in [(22, 9), (27, 9), (27, 14), (22, 14)]:
                click(*position)
            page.locator('[data-builder-viewport]').focus()
            page.keyboard.press('Enter')
            polygon = save()['document']['floors']
            added = [tile for tile in polygon if tile['id'] not in {value['id'] for value in circle}]
            assert {(tile['x'], tile['y']) for tile in added} == {(x, y) for x in range(22, 27) for y in range(9, 14)}, added
            for position in [(30, 20), (34, 20), (34, 25)]:
                click(*position)
            page.keyboard.press('Escape')
            expect(page.locator('[data-builder-ghost] > *')).to_have_count(0)
            assert save()['document']['floors'] == polygon, 'Escape must cancel an unfinished polygon.'
            records.append({'case': 'polygon-family-fill-enter-and-escape', 'cells': len(added), 'cancelPreservesDocument': True})

            for position in [(28, 9), (31, 9), (31, 12)]:
                click(*position)
            last = point(28, 12)
            page.mouse.dblclick(last['x'], last['y'])
            double_polygon = save()['document']['floors']
            added = [tile for tile in double_polygon if tile['id'] not in {value['id'] for value in polygon}]
            assert {(tile['x'], tile['y']) for tile in added} == {(x, y) for x in range(28, 31) for y in range(9, 12)}, added
            expect(page.locator('[data-builder-ghost] > *')).to_have_count(0)
            records.append({'case': 'polygon-family-fill-double-click', 'cells': len(added)})

            for position in [(31, 20), (34, 20), (34, 23)]:
                click(*position)
            renamed = 'Dungeon revision — São João'
            set_name(page, renamed)
            expect(page.locator('[data-builder-ghost] > *')).to_have_count(0)
            page.locator('[data-builder-viewport]').focus()
            page.keyboard.press('Enter')
            interrupted = save()['document']
            assert interrupted['name'] == renamed and interrupted['floors'] == double_polygon, interrupted
            records.append({'case': 'editing-settings-cancels-polygon-without-losing-new-name', 'name': renamed})

            before_type_edit = save()['document']
            page.locator('[data-builder-role=floor]').click()
            page.locator(f'[data-asset-id="{asset_ids[0]}"]').dblclick()
            editor = page.locator('[data-builder-asset-modal]')
            editor.locator('[data-builder-import-family]').fill('')
            editor.locator('[data-builder-import-role]').select_option('wall')
            editor.locator('[data-builder-import-submit]').click()
            expect(editor.locator('[role=alert]')).to_be_visible()
            editor.locator('[data-builder-import-cancel]').click()
            assert save()['document'] == before_type_edit, 'Editing a used material must preserve its painted type.'
            records.append({'case': 'used-material-type-change-rejected', 'sourcePreserved': True})

            wall_family = 'Crypt walls'
            wall_assets = import_files('wall', wall_family, [image_payload('Crypt wall A.png', '#73766f'),
                                                           image_payload('Crypt wall B.png', '#5d665b')])
            expect(page.locator('[data-builder-tool=wall]')).to_have_attribute('aria-pressed', 'true')
            page.locator('[data-builder-brush-material]').select_option('family:' + wall_family)
            page.evaluate('() => { window.familyOriginalRandom = Math.random; Math.random = () => .05; }')
            try:
                stroke([(2, 18), (8, 18)], check_preview=True)
            finally:
                page.evaluate('() => { Math.random = window.familyOriginalRandom; delete window.familyOriginalRandom; }')
            page.evaluate('() => { window.familyOriginalRandom = Math.random; Math.random = () => .95; }')
            try:
                stroke([(8, 18), (14, 18)])
            finally:
                page.evaluate('() => { Math.random = window.familyOriginalRandom; delete window.familyOriginalRandom; }')
            walls = save()['document']['walls']
            assert len(walls) == 2 and {wall['assetId'] for wall in walls} == set(wall_assets), walls

            door_assets = import_files('door', '', [image_payload('Crypt door.png', '#96673e')])
            expect(page.locator('[data-builder-tool=door]')).to_have_attribute('aria-pressed', 'true')
            stroke([(4, 18), (5, 18)])
            object_assets = import_files('decoration', '', [image_payload('Wooden crate.png', '#8d5c38')])
            expect(page.locator('[data-builder-tool=decoration]')).to_have_attribute('aria-pressed', 'true')
            click(25, 20)
            typed = save()['document']
            assert len(typed['doors']) == len(typed['decorations']) == 1, typed
            assert typed['doors'][0]['assetId'] == door_assets[0], typed['doors']
            assert typed['decorations'][0]['assetId'] == object_assets[0], typed['decorations']
            assert not typed['lights']
            records.append({'case': 'wall-family-and-typed-door-object-placement',
                            'walls': wall_assets, 'door': door_assets[0], 'object': object_assets[0]})

            page.screenshot(path=str(output / 'families-painted-desktop.png'))
            project = save()
            project_id = project['id']
            page.reload()
            wait_ready(page)
            persisted = page.request.get(api + '/projects/' + project_id).json()['project']
            assert persisted['document'] == project['document'], 'Concrete tile assignments must survive reload.'
            builder_tool(page, 'floor')
            page.locator('[data-builder-role=floor]').click()
            page.locator('[data-family-name]').filter(has_text=family).click()
            expect(page.locator('[data-builder-brush-material]')).to_have_value('family:' + family)
            reference_geometry(page)
            records.append({'case': 'family-and-concrete-paint-persist-reload', 'project': project_id})

            # New import controls use the application modal on smaller viewports too.
            for width, height in ((390, 844), (320, 700)):
                page.set_viewport_size({'width': width, 'height': height})
                modal = open_import()
                modal.locator('[data-builder-import-family]').fill('A long authored family name — São João ' * 2)
                metrics = modal.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], metrics
                assert metrics['scrollWidth'] <= metrics['viewport'] + 1, metrics
                page.screenshot(path=str(output / f'families-import-{width}.png'))
                page.keyboard.press('Escape')
                records.append({'case': 'responsive-import-modal', 'width': width, 'metrics': metrics})
            page.set_viewport_size({'width': 1586, 'height': 992})

            for locale, words in (
                ('pt-BR', {'title': 'Importar assets', 'type': 'Tipo de asset', 'family': 'Família de assets',
                           'types': ['Chão', 'Parede', 'Porta', 'Objeto'],
                           'paintLabel': 'Ferramenta de pintura',
                           'shapes': ['Pincel livre', 'Retângulo', 'Círculo', 'Polígono', 'Preenchimento']}),
                ('es', {'title': 'Importar recursos', 'type': 'Tipo de recurso', 'family': 'Familia de recursos',
                        'types': ['Suelo', 'Pared', 'Puerta', 'Objeto'],
                        'paintLabel': 'Herramienta de pintura',
                        'shapes': ['Pincel libre', 'Rectángulo', 'Círculo', 'Polígono', 'Relleno']}),
            ):
                change_locale(page, locale, campaign)
                page.goto(builder + '?project=' + project_id)
                wait_ready(page)
                expect(page.locator('html')).to_have_attribute('lang', locale)
                builder_tool(page, 'floor')
                page.locator('[data-builder-role=floor]').click()
                page.locator('[data-family-name]').filter(has_text=family).click()
                shape = page.locator('[data-builder-paint-mode]')
                assert shape.locator('option').all_text_contents() == words['shapes']
                expect(shape.locator('..')).to_contain_text(words['paintLabel'])
                expect(page.locator('[data-builder-title]')).to_have_text(renamed)
                page.screenshot(path=str(output / f'families-painted-{locale}.png'))
                page.set_viewport_size({'width': 390, 'height': 844})
                modal = open_import()
                expect(modal.locator('strong')).to_have_text(words['title'])
                expect(modal.locator('[data-builder-import-role]').locator('..')).to_contain_text(words['type'])
                expect(modal.locator('[data-builder-import-family]').locator('..')).to_contain_text(words['family'])
                assert modal.locator('[data-builder-import-role] option').all_text_contents() == words['types']
                modal.locator('[data-builder-import-family]').fill(family)
                metrics = modal.evaluate(MEASURE)
                assert not metrics['tiny'] and not metrics['overflow'], metrics
                page.screenshot(path=str(output / f'families-import-{locale}-390.png'))
                page.keyboard.press('Escape')
                page.set_viewport_size({'width': 1586, 'height': 992})
                records.append({'case': 'localized-family-import-and-paint-controls', 'locale': locale, 'metrics': metrics})

            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.text()
            page.wait_for_url(f'{base}/game/{campaign}')
            generated_project = page.request.get(api + '/projects/' + project_id).json()['project']
            assert generated_project['sceneId']
            assert generated_project['document'] == project['document'], 'Generation must not reshuffle saved materials.'
            records.append({'case': 'generate-preserves-concrete-family-tiles', 'scene': generated_project['sceneId']})
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
    output = (args.output or ROOT / 'data/map-builder-families' /
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
