"""Review the Map Builder reference chrome using an isolated, synthetic campaign.

The scene is drawn through real browser controls from synthetic uploaded images.
No reference tavern artwork, demo project, operator data or preset is installed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from io import BytesIO
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import traceback
from urllib.request import urlopen

from map_builder import ROOT, MEASURE, change_locale, fixture_environment, serve


def synthetic_texture(kind):
    from PIL import Image, ImageDraw

    palette = {'floor': ('#586246', '#48523a'), 'wall': ('#777a73', '#444b48'),
               'door': ('#775635', '#423725')}
    background, detail = palette[kind]
    image = Image.new('RGB', (128, 128), background)
    draw = ImageDraw.Draw(image)
    for offset in range(0, 128, 16):
        if kind == 'floor':
            for x in range(offset % 32, 128, 32):
                draw.rectangle((x, offset, x + 12, offset + 3), fill=detail)
        elif kind == 'wall':
            draw.line((0, offset, 128, offset), fill=detail, width=3)
            for x in range((offset // 16 % 2) * 16, 128, 32):
                draw.line((x, offset, x, offset + 16), fill=detail, width=2)
        else:
            draw.line((offset, 0, offset, 128), fill=detail, width=3)
    output = BytesIO()
    image.save(output, 'PNG')
    return output.getvalue()


REFERENCE_GEOMETRY = """()=>{
 const box=selector=>{const r=document.querySelector(selector).getBoundingClientRect();
  return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};};
 const font=selector=>{const s=getComputedStyle(document.querySelector(selector));
  return {family:s.fontFamily,size:s.fontSize,weight:s.fontWeight};};
 return {header:box('.map-builder__header'),canvas:box('[data-builder-viewport]'),
  removedBars:document.querySelectorAll('.map-builder__toolbars,.map-builder__tool-rail').length,
  dock:box('.map-builder__asset-dock'),status:box('.map-builder__status'),
  fonts:{interface:font('.map-builder'),brand:font('.map-builder__brand'),
   back:font('.map-builder__back'),quickName:font('[data-builder-quick-name]')},
  activeToolStyle:(()=>{const s=getComputedStyle(document.querySelector('[data-builder-tool=wall]'));
   return {border:s.borderTopColor,background:s.backgroundImage,color:s.color};})(),
  labels:{header:document.querySelector('.map-builder__header').innerText,
   name:document.querySelector('[data-builder-quick-name]').value},
  width:innerWidth,height:innerHeight};
}"""


def reference_geometry(page):
    result = page.evaluate(REFERENCE_GEOMETRY)
    # Drawing options live in Tools. The canvas reclaims both removed bars;
    # the desktop header and library keep their existing heights.
    assert result['removedBars'] == 0, result
    expected = {
        'header': {'top': 0, 'height': 60},
        'canvas': {'left': 0, 'top': 60, 'right': 1586, 'bottom': 792},
        'dock': {'left': 0, 'top': 792, 'right': 1586, 'height': 200, 'bottom': 992},
    }
    for area, dimensions in expected.items():
        for key, value in dimensions.items():
            assert abs(result[area][key] - value) <= 1, (area, key, value, result)
    canvas, status = result['canvas'], result['status']
    assert canvas['left'] <= status['left'] < status['right'] <= canvas['right'], result
    assert canvas['top'] <= status['top'] < status['bottom'] <= canvas['bottom'], result
    return result


def close_panel(page):
    close = page.locator('[data-builder-close-panel]')
    if close.is_visible():
        close.click()


def set_name(page, name):
    close_panel(page)
    page.locator('.map-builder__layers-toggle').click()
    page.locator('[data-builder-sidebar-tab=settings][role=tab]').click()
    details = page.locator('[data-builder-settings]')
    if not details.evaluate('el=>el.open'):
        details.locator('summary').click()
    field = page.locator('[data-builder-form] [name=name]')
    field.fill(name)
    field.press('Tab')
    close_panel(page)


def wait_ready(page):
    page.wait_for_function("document.querySelector('[data-map-builder]')?.getAttribute('aria-busy')==='false'")
    page.evaluate('document.fonts.ready')


def create_layer(page, name='Synthetic test layer'):
    """Explicitly create a named layer through the editor's real controls."""
    from playwright.sync_api import expect
    from map_builder import builder_sidebar

    builder_sidebar(page, 'layers')
    field = page.locator('[data-builder-layer-name]')
    field.fill(name)
    field.press('Enter')
    active = page.locator('[data-builder-active-layer-select]')
    expect(active).not_to_have_value('')
    identifier = active.input_value()
    expect(page.locator(f'[data-builder-layer-title="{identifier}"]')).to_have_value(name)
    close_panel(page)
    return identifier


def upload_asset(page, kind, name, content):
    """Import through the same explicit type form used by a GM."""
    from playwright.sync_api import expect

    page.locator('[data-builder-import]').click()
    modal = page.locator('[data-builder-import-modal]')
    expect(modal).to_be_visible()
    modal.locator('[data-builder-import-role]').select_option(kind)
    modal.locator('[data-builder-upload]').set_input_files({
        'name': name, 'mimeType': 'image/png', 'buffer': content,
    })
    with page.expect_response(lambda response: '/library/upload' in response.url) as uploaded:
        modal.locator('[data-builder-import-submit]').click()
    assert uploaded.value.status == 201, uploaded.value.text()
    expect(modal).to_have_count(0)
    wait_ready(page)
    return uploaded.value.json()


def chrome_only(page):
    from playwright.sync_api import expect

    for selector in (
        '.map-builder__library', '.map-builder__utility-tools',
        '[data-builder-snap-step]', '[data-builder-toggle-grid]',
        '[data-builder-tool-help]',
        '[data-builder-classify]', '.map-builder__sidebar-tabs',
        '[data-builder-notice]', '[role=dialog]', 'dialog',
    ):
        expect(page.locator(selector + ':visible')).to_have_count(0)
    expect(page.locator('[data-builder-assets] [data-asset-id=""]')).to_have_count(0)
    expect(page.locator('.map-builder__asset-details')).to_be_visible()
    assert not page.locator('.map-builder__asset-details').evaluate('element => element.open')


def layout_metrics(page):
    from playwright.sync_api import expect

    metrics = page.locator('[data-map-builder]').evaluate(MEASURE)
    assert not metrics['tiny'] and not metrics['overflow'], metrics
    assert metrics['scrollWidth'] <= metrics['viewport'] + 1, metrics
    canvas = page.locator('[data-builder-viewport]').bounding_box()
    assert canvas['height'] >= 180 and canvas['width'] >= 180, canvas
    expect(page.locator('.map-builder__toolbars,.map-builder__tool-rail')).to_have_count(0)
    controls = page.locator('.map-builder__header').evaluate("""header=>{
      const bounds=header.getBoundingClientRect();
      return [...header.querySelectorAll('input,select,button,a')]
        .filter(el=>el.checkVisibility({checkVisibilityCSS:true}))
        .map(el=>({element:el.outerHTML,left:el.getBoundingClientRect().left,right:el.getBoundingClientRect().right,top:el.getBoundingClientRect().top,bottom:el.getBoundingClientRect().bottom}))
        .filter(el=>el.left<bounds.left-1||el.right>bounds.right+1||el.top<bounds.top-1||el.bottom>bounds.bottom+1);
    }""")
    assert not controls, ('Header controls exceed its bounds', controls)
    if metrics['viewport'] <= 600:
        save = page.locator('[data-builder-save]')
        label = page.locator('[data-builder-save-state]')
        expect(save).to_be_visible()
        expect(label).to_be_visible()
        assert label.inner_text().strip(), 'The mobile Save button must have visible text.'
        button_box, label_box = save.bounding_box(), label.bounding_box()
        assert label_box['width'] >= 12 and label_box['height'] >= 12, label_box
        assert label_box['x'] >= button_box['x'] and label_box['x'] + label_box['width'] <= button_box['x'] + button_box['width'] + 1, (button_box, label_box)
        metrics['mobileSaveLabel'] = label.inner_text()
    return metrics


def check_browser(base, seed, output, executable):
    from playwright.sync_api import expect, sync_playwright

    errors, requests, dialogs, records = [], [], [], []
    builder = f"{base}/game/{seed['campaign']}/map-builder"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(viewport={'width': 1586, 'height': 992})
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('requestfailed', lambda request: requests.append({'url': request.url, 'error': request.failure}))

        def native_dialog(dialog):
            dialogs.append({'type': dialog.type, 'message': dialog.message})
            dialog.dismiss()

        page.on('dialog', native_dialog)
        try:
            page.goto(builder)
            wait_ready(page)
            change_locale(page, 'pt-BR', seed['campaign'])
            page.goto(builder)
            wait_ready(page)
            expect(page.locator('html')).to_have_attribute('lang', 'pt-BR')
            expect(page.locator('[data-builder-tool=wall]')).to_have_attribute('aria-pressed', 'true')
            expect(page.locator('[data-builder-role=floor]')).to_have_attribute('aria-pressed', 'true')
            expect(page.locator('[data-builder-assets-empty]')).to_be_visible()
            chrome_only(page)
            records.append({'case': 'empty-reference-desktop', 'geometry': reference_geometry(page),
                            'metrics': layout_metrics(page)})
            page.screenshot(path=str(output / 'reference-empty-1586.png'))
            for width, height in ((390, 844), (320, 700)):
                page.set_viewport_size({'width': width, 'height': height})
                records.append({'case': 'empty-responsive', 'width': width, **layout_metrics(page)})
                chrome_only(page)
                page.screenshot(path=str(output / f'reference-empty-{width}.png'))
            page.set_viewport_size({'width': 1586, 'height': 992})
            set_name(page, 'Taverna do Vale')

            def tool(name):
                from map_builder import builder_tool
                builder_tool(page, name)

            def point(x, y):
                close_panel(page)
                return page.locator('[data-builder-canvas]').evaluate("""(svg,p)=>{
                  const q=new DOMPoint(p.x,p.y).matrixTransform(svg.getScreenCTM());return {x:q.x,y:q.y};
                }""", {'x': x, 'y': y})

            def drag(x1, y1, x2, y2):
                start, end = point(x1, y1), point(x2, y2)
                page.mouse.move(start['x'], start['y'])
                page.mouse.down()
                page.mouse.move(end['x'], end['y'], steps=8)
                page.mouse.up()

            assets = {}
            asset_names = {'floor': 'Grama', 'wall': 'Pedra', 'door': 'Porta de madeira'}
            for kind in ('floor', 'wall', 'door'):
                tool(kind)
                assets[kind] = upload_asset(page, kind, asset_names[kind], synthetic_texture(kind))['id']
            # Import focuses its explicit type. Reopen the saved project to review
            # the reference's default Floor library, independently of import state.
            with page.expect_response(lambda response: '/map-builder/projects/' in response.url
                                      and response.request.method == 'POST') as imported_project:
                page.locator('[data-builder-save]').click()
            assert imported_project.value.ok, imported_project.value.text()
            page.reload()
            wait_ready(page)
            expect(page.locator('[data-builder-role=floor]')).to_have_attribute('aria-pressed', 'true')
            expect(page.locator('[data-builder-assets] [data-asset-id]')).to_have_count(1)
            expect(page.locator('[data-builder-assets] [data-asset-id]')).to_have_attribute('data-asset-id', assets['floor'])

            for kind in ('floor', 'wall'):
                page.locator(f'[data-builder-role={kind}]').click()
                card = page.locator(f'[data-asset-id="{assets[kind]}"]')
                card.click()
                from map_builder import builder_sidebar
                builder_sidebar(page, 'tools')
                expect(page.locator(f'[data-builder-tool={kind}]')).to_have_attribute('aria-pressed', 'true')
                material = page.locator('[data-builder-brush-material]')
                thumbnail = page.locator('[data-builder-brush-thumbnail]')
                expect(material).to_have_value(assets[kind])
                expect(thumbnail).to_be_visible()
                expect(thumbnail).to_have_attribute('src', card.locator('img').get_attribute('src'))
                material.select_option('')
                expect(thumbnail).to_be_hidden()
                material.select_option(assets[kind])
                expect(thumbnail).to_be_visible()
                expect(material).to_have_value(assets[kind])
            records.append({'case': 'real-assets-and-materials', 'assets': assets, 'syntheticAssetNames': asset_names,
                            'cardAndDropdownStayInSync': True, 'builtinMaterialRoundtrip': True})

            tool('floor')
            page.locator('[data-builder-paint-mode]').select_option('rectangle')
            page.locator('[data-builder-brush-material]').select_option(assets['floor'])
            drag(8, 8, 28, 22)
            tool('wall')
            page.locator('[data-builder-brush-material]').select_option(assets['wall'])
            thickness = page.locator('[data-builder-brush=thickness]')
            thickness.fill('0.2')
            thickness.press('Tab')
            for span in ((8, 8, 28, 8), (28, 8, 28, 22), (28, 22, 8, 22), (8, 22, 8, 8)):
                drag(*span)
            expect(page.locator('[data-builder-floors] [data-object-id]')).to_have_count(280)
            expect(page.locator('[data-builder-walls] [data-object-id]')).to_have_count(4)
            expect(page.locator('.map-builder__library')).to_be_hidden()

            # Changing the library during selection must not move the wall or camera.
            original_wall = page.locator('[data-builder-walls]').inner_html()
            before = page.locator('[data-builder-viewport]').bounding_box()
            page.locator('[data-builder-role=light]').click()
            expect(page.locator('[data-builder-import]')).to_be_visible()
            tool('select')
            target = point(18, 8)
            page.mouse.click(target['x'], target['y'])
            assert page.locator('[data-builder-walls]').inner_html() == original_wall
            assert page.locator('[data-builder-viewport]').bounding_box() == before
            expect(page.locator('.map-builder__library')).to_be_hidden()

            with page.expect_response(lambda response: '/map-builder/projects/' in response.url
                                      and response.request.method == 'POST') as saved:
                page.locator('[data-builder-save]').click()
            assert saved.value.ok, saved.value.text()
            project = saved.value.json()['project']
            expected_walls = [(8, 8, 28, 8), (28, 8, 28, 22), (28, 22, 8, 22), (8, 22, 8, 8)]
            assert [tuple(row[key] for key in ('x1', 'y1', 'x2', 'y2'))
                    for row in project['document']['walls']] == expected_walls, project
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved')
            markup = {kind: page.locator(f'[data-builder-{kind}]').inner_html() for kind in ('floors', 'walls')}
            page.locator('[data-builder-preview]').click()
            expect(page.locator('[data-builder-preview]')).to_have_attribute('aria-pressed', 'true')
            expect(page.locator('[data-builder-grid]')).to_be_hidden()
            drag(18, 8, 18, 10)
            for kind, html in markup.items():
                assert page.locator(f'[data-builder-{kind}]').inner_html() == html
            page.locator('[data-builder-preview]').click()
            expect(page.locator('[data-builder-grid]')).to_be_visible()
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved')
            records.append({'case': 'pointer-save-preview', 'project': project['id'], 'floors': 280, 'walls': 4,
                            'clickDoesNotMoveWall': True, 'previewPreservesSource': True})

            # Reload the saved project to review the default Floor library and actual persistence.
            page.reload()
            wait_ready(page)
            tool('wall')
            page.locator('[data-builder-brush-material]').select_option(assets['wall'])
            expect(page.locator('[data-builder-tool=wall]')).to_have_attribute('aria-pressed', 'true')
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved')
            active_border = page.locator('[data-builder-tool=wall]').evaluate('el=>getComputedStyle(el).borderTopColor')
            inactive_border = page.locator('[data-builder-tool=floor]').evaluate('el=>getComputedStyle(el).borderTopColor')
            assert active_border != inactive_border, ('Active tool needs its reference accent border', active_border)
            expect(page.locator('[data-builder-role=floor]')).to_have_attribute('aria-pressed', 'true')
            expect(page.locator('[data-builder-assets] [data-asset-id]')).to_have_count(1)
            expect(page.locator('[data-builder-assets] [data-asset-id]')).to_have_attribute('data-asset-id', assets['floor'])
            expect(page.locator('[data-builder-title]')).to_have_text('Taverna do Vale')
            expect(page.locator('[data-builder-dimensions]')).to_have_text('40 × 30 células')
            chrome_only(page)
            records.append({'case': 'populated-reference-desktop', 'geometry': reference_geometry(page),
                            'metrics': layout_metrics(page)})
            page.screenshot(path=str(output / 'reference-populated-fit-1586.png'))
            durable = page.request.get(f"{base}/api/containers/{seed['campaign']}/map-builder/projects/{project['id']}")
            assert durable.ok and durable.json()['project']['document'] == project['document']

            # Use actual wheel events to reach 100%; the label remains camera-owned.
            source_before_zoom = {kind: page.locator(f'[data-builder-{kind}]').inner_html()
                                  for kind in ('floors', 'walls')}
            viewport = page.locator('[data-builder-viewport]')
            viewport.hover()
            for _ in range(8):
                scale = page.locator('[data-builder-canvas]').evaluate('svg=>svg.getScreenCTM().a')
                delta = -math.log(project['document']['cellSize'] / scale) / .002
                if abs(delta) < .001:
                    break
                delta = max(-200, min(200, delta))
                expected_scale = scale * math.exp(-delta * .002)
                page.mouse.wheel(0, delta)
                page.wait_for_function("expected=>Math.abs(document.querySelector('[data-builder-canvas]').getScreenCTM().a-expected)<.001",
                                       arg=expected_scale)
            expect(page.locator('[data-builder-zoom-level]')).to_have_text('100%')
            for kind, html in source_before_zoom.items():
                assert page.locator(f'[data-builder-{kind}]').inner_html() == html
            expect(page.locator('[data-map-builder]')).to_have_attribute('data-save-state', 'saved')
            after_zoom = page.request.get(f"{base}/api/containers/{seed['campaign']}/map-builder/projects/{project['id']}")
            assert after_zoom.ok and after_zoom.json()['project']['document'] == project['document']
            chrome_only(page)
            records.append({'case': 'reference-actual-100-percent', 'geometry': reference_geometry(page),
                            'metrics': layout_metrics(page), 'sourceAndCoordinatesUnchanged': True})
            page.screenshot(path=str(output / 'reference-populated-1586.png'))

            long_asset_name = 'Textura sintética de pedra — nome autoral muito longo para validar os controles e a biblioteca.png'
            uploaded = upload_asset(page, 'wall', long_asset_name, synthetic_texture('wall'))
            expect(page.locator(f'[data-asset-id="{uploaded["id"]}"]')).to_have_attribute('title', long_asset_name)
            set_name(page, ('São João — ' + 'Nome autoral muito longo para testar o cabeçalho ' * 2)[:120])
            for width, height in ((1586, 992), (390, 844), (320, 700)):
                page.set_viewport_size({'width': width, 'height': height})
                chrome_only(page)
                records.append({'case': 'populated-long-content', 'width': width, **layout_metrics(page)})
                page.screenshot(path=str(output / f'reference-long-{width}.png'))

            for locale, words in (
                ('en', ('Back to game', 'Preview', 'Generate scene', 'Wall', 'Floor', '40 × 30 cells')),
                ('es', ('Volver al juego', 'Vista previa', 'Generar escena', 'Pared', 'Suelo', '40 × 30 celdas')),
            ):
                localized_context = browser.new_context(viewport={'width': 1586, 'height': 992})
                localized_context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
                localized = localized_context.new_page()
                localized.on('pageerror', lambda error: errors.append(str(error)))
                localized.on('requestfailed', lambda request: requests.append({'url': request.url, 'error': request.failure}))
                localized.on('dialog', native_dialog)
                try:
                    localized.goto(builder)
                    wait_ready(localized)
                    change_locale(localized, locale, seed['campaign'])
                    localized.goto(builder)
                    wait_ready(localized)
                    expect(localized.locator('html')).to_have_attribute('lang', locale)
                    for selector, text in zip(('.map-builder__back', '[data-builder-preview]',
                                               '[data-builder-generate]', '[data-builder-tool=wall]',
                                               '[data-builder-tool=floor]', '[data-builder-dimensions]'), words):
                        expect(localized.locator(selector)).to_have_text(text)
                    chrome_only(localized)
                    records.append({'case': 'localized-reference-render', 'locale': locale,
                                    'geometry': reference_geometry(localized), 'metrics': layout_metrics(localized)})
                    localized.screenshot(path=str(output / f'reference-{locale}-1586.png'))
                finally:
                    localized_context.close()
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    assert not [request for request in requests if request['error'] != 'net::ERR_ABORTED'], requests
    return {'passed': True, 'cases': records, 'pageErrors': errors, 'failedRequests': requests,
            'nativeDialogs': dialogs, 'artwork': 'Synthetic uploaded textures; no tavern artwork or preset.'}


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
    output = (args.output or ROOT / 'data/map-builder-reference' /
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
