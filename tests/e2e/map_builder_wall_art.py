"""Exercise wall-local artwork, edge snapping and door cuts in a real browser.

Uses only a synthetic transparent strip and an isolated disposable campaign.
Color samples distinguish cropped, rotated wall art from a square floor pattern.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
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
from uuid import uuid4

from map_builder import ROOT, builder_sidebar, builder_tool, fixture_environment, serve
from map_builder_reference import close_panel, set_name, upload_asset, wait_ready


RED = (220, 30, 30)
BLUE = (30, 60, 220)
GREEN = (30, 220, 60)
BACKGROUND = (37, 48, 56)


def synthetic_wall():
    from PIL import Image, ImageDraw

    image = Image.new('RGBA', (240, 80))
    draw = ImageDraw.Draw(image)
    # The visible bounds are 216 by 24, giving a nine-thickness repeat.
    draw.rectangle((12, 28, 119, 51), fill=(*RED, 255))
    draw.rectangle((120, 28, 227, 51), fill=(*BLUE, 255))
    draw.rectangle((12, 28, 227, 35), fill=(*GREEN, 255))
    draw.point((2, 2), fill=(255, 255, 255, 1))
    content = BytesIO()
    image.save(content, 'PNG')
    image.close()
    return content.getvalue()


def wall_point(wall, distance, normal=0):
    dx, dy = wall['x2'] - wall['x1'], wall['y2'] - wall['y1']
    size = math.hypot(dx, dy)
    ux, uy = dx / size, dy / size
    return (wall['x1'] + distance * ux - normal * uy,
            wall['y1'] + distance * uy + normal * ux)


def assert_color(actual, expected, label, tolerance=38):
    assert max(abs(a - b) for a, b in zip(actual[:3], expected)) <= tolerance, {
        'sample': label, 'actual': actual, 'expected': expected,
    }


def check_browser(base, seed, output, executable):
    from PIL import Image
    from playwright.sync_api import expect, sync_playwright

    campaign = seed['campaign']
    builder = f'{base}/game/{campaign}/map-builder'
    api = f'{base}/api/containers/{campaign}/map-builder'
    records, errors, dialogs, failed_requests = [], [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path': str(executable)} if executable else {}))
        context = browser.new_context(viewport={'width': 1586, 'height': 992}, device_scale_factor=1)
        context.add_cookies([{**seed['sessions']['gm'], 'url': base}])
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('requestfailed', lambda request: failed_requests.append({'url': request.url, 'error': request.failure}))

        def native_dialog(dialog):
            dialogs.append({'type': dialog.type, 'message': dialog.message})
            dialog.dismiss()

        page.on('dialog', native_dialog)
        try:
            page.goto(builder)
            wait_ready(page)
            set_name(page, 'Synthetic wall alignment')
            asset_id = upload_asset(page, 'wall', 'Synthetic padded asymmetric wall.png', synthetic_wall())['id']
            builder_tool(page, 'wall')
            page.locator('[data-builder-brush-material]').select_option(asset_id)
            thickness = page.locator('[data-builder-brush=thickness]')
            thickness.fill('.6')
            thickness.press('Tab')
            snap = page.locator('[data-builder-toggle-snap]')
            expect(snap).to_have_attribute('aria-pressed', 'true')

            def position(x, y):
                return page.locator('[data-builder-canvas]').evaluate("""(canvas, point) => {
                  const result = new DOMPoint(point.x, point.y).matrixTransform(canvas.getScreenCTM());
                  return {x: result.x, y: result.y};
                }""", {'x': x, 'y': y})

            def ready_art(selector='[data-builder-walls]'):
                page.wait_for_function("""selector => {
                  const walls = [...document.querySelectorAll(selector + ' [data-object-kind=walls]')];
                  return walls.length > 0 && walls.every(wall => wall.dataset.wallArt === 'ready');
                }""", arg=selector)
                # Resolve referenced image resources before taking pixel samples.
                page.evaluate("""async () => await Promise.all(
                  [...document.querySelectorAll('[data-builder-defs] image')].map(element =>
                    new Promise((resolve, reject) => {
                      const image = new Image(); image.onload = resolve; image.onerror = reject;
                      image.src = element.getAttribute('href');
                    })))""")

            def stroke(start, end, preview=None):
                first, last = position(*start), position(*end)
                page.mouse.move(first['x'], first['y'])
                page.mouse.down()
                page.mouse.move(last['x'], last['y'], steps=8)
                if preview:
                    ready_art('[data-builder-ghost]')
                    strip = page.locator('[data-builder-ghost] [data-builder-wall-strip]')
                    expect(strip).to_have_count(1)
                    transform = strip.get_attribute('transform')
                    assert transform == preview, transform
                    page.screenshot(path=str(output / 'wall-drag-preview.png'))
                page.mouse.up()

            def save():
                if page.locator('[data-map-builder]').get_attribute('data-save-state') == 'saved':
                    project_id = page.evaluate("new URL(location.href).searchParams.get('project')")
                    response = page.request.get(api + '/projects/' + project_id)
                else:
                    with page.expect_response(lambda response: '/map-builder/projects/' in response.url
                                              and response.request.method == 'POST'
                                              and not response.url.endswith(('/generate', '/update'))) as saved:
                        page.locator('[data-builder-save]').click()
                    response = saved.value
                assert response.ok, response.text()
                return response.json()['project']

            # A mostly horizontal/vertical gesture follows grid edges; it does
            # not leave diagonal segments crossing the interiors of cells.
            stroke((3.2, 4.3), (19.3, 5.2), preview='translate(3 4) rotate(0)')
            stroke((24.4, 3.2), (25.1, 19.1))
            project = save()
            horizontal, vertical = project['document']['walls']
            assert tuple(horizontal[key] for key in ('x1', 'y1', 'x2', 'y2')) == (3, 4, 19, 4), horizontal
            assert tuple(vertical[key] for key in ('x1', 'y1', 'x2', 'y2')) == (24, 3, 24, 19), vertical
            assert all(wall['thickness'] == .6 for wall in (horizontal, vertical))
            records.append({'case': 'grid-edges-and-dominant-axis-preview', 'walls': [horizontal, vertical]})

            # Moving a snapped wall keeps its center on an entire grid edge,
            # even when the pointer moves only a fraction of one cell.
            builder_tool(page, 'select')
            stroke((5, 4), (5.6, 4.3))
            moved = save()['document']['walls'][0]
            assert tuple(moved[key] for key in ('x1', 'y1', 'x2', 'y2')) == (4, 4, 20, 4), moved
            page.locator('[data-builder-undo]').click()
            project = save()
            assert project['document']['walls'][0] == horizontal
            records.append({'case': 'wall-move-keeps-grid-boundary-and-undo-restores-source'})
            close_panel(page)
            page.locator('[data-builder-quick-tool=select]').click()
            first = position(5, 4)
            page.mouse.click(first['x'], first['y'])
            page.locator('[data-builder-wall-extend=end]').click()
            target = position(21, 8)
            page.mouse.move(target['x'], target['y'], steps=5)
            marker = page.locator('[data-builder-wall-node-preview]')
            expect(marker).to_have_count(1)
            expect(marker).to_have_attribute('vector-effect', 'non-scaling-stroke')
            bounds = marker.bounding_box()
            # The 5 px radius and 2 px non-scaling stroke occupy a 12 px box.
            assert 11 <= bounds['width'] <= 13 and 11 <= bounds['height'] <= 13, bounds
            page.screenshot(path=str(output / 'wall-extension-armed.png'))
            page.keyboard.press('Escape')
            expect(marker).to_have_count(0)
            unchanged = save()
            assert unchanged['document'] == project['document'] and unchanged['version'] == project['version']
            records.append({'case': 'armed-extension-preview-marker-keeps-pixel-stroke-and-Escape-preserves-source'})
            builder_tool(page, 'wall')

            snap.click()
            expect(snap).to_have_attribute('aria-pressed', 'false')
            stroke((3.2, 10.3), (16.4, 19.1))
            project = save()
            diagonal = project['document']['walls'][2]
            assert diagonal['x1'] != diagonal['x2'] and diagonal['y1'] != diagonal['y2'], diagonal
            for key, value in zip(('x1', 'y1', 'x2', 'y2'), (3.2, 10.3, 16.4, 19.1)):
                assert abs(diagonal[key] - value) < .03, diagonal
            records.append({'case': 'free-wall-preserves-noninteger-diagonal', 'wall': diagonal})

            # Add an actual open door via the controls. Its hole must cut the
            # parent wall while keeping that wall's material phase on both sides.
            snap.click()
            builder_tool(page, 'door')
            stroke((9, 4), (11, 4))
            builder_sidebar(page, 'selection')
            page.locator('[data-builder-door-state=open]').click()
            close_panel(page)
            project = save()
            assert project['document']['doors'][0]['state'] == 'open', project
            assert tuple(project['document']['doors'][0][key] for key in ('x1', 'y1', 'x2', 'y2')) == (9, 4, 11, 4)

            def browser_samples(filename, source):
                ready_art()
                content = page.screenshot(path=str(output / filename))
                with Image.open(BytesIO(content)) as screenshot:
                    samples = []
                    for wall in source['walls']:
                        repeat_sample = 11.7 if wall['id'] == horizontal['id'] else 6.3
                        for distance, normal, expected in (
                            (.9, .12, RED), (3.6, .12, BLUE), (repeat_sample, .12, RED),
                            (.9, -.18, GREEN), (.9, .24, RED), (.9, .42, BACKGROUND),
                        ):
                            x, y = wall_point(wall, distance, normal)
                            screen = position(x, y)
                            pixel = screenshot.getpixel((round(screen['x']), round(screen['y'])))
                            label = {'wall': wall['id'], 'distance': distance, 'normal': normal}
                            assert_color(pixel, expected, label)
                            samples.append({**label, 'rgb': pixel[:3]})
                    for x in (9.5, 10.5):
                        screen = position(x, 4)
                        assert_color(screenshot.getpixel((round(screen['x']), round(screen['y']))),
                                     BACKGROUND, f'open door at {x}')
                    screen = position(11.4, 4.12)
                    assert_color(screenshot.getpixel((round(screen['x']), round(screen['y']))),
                                 BLUE, 'wall phase after door')
                    return samples

            page.locator('[data-builder-preview]').click()
            expect(page.locator('[data-builder-grid]')).to_be_hidden()
            samples = browser_samples('wall-preview.png', project['document'])
            records.append({'case': 'wall-local-art-and-alpha-trim-in-preview', 'samples': samples,
                            'openDoorCutsArt': True, 'repeatPeriodInCells': 5.4})
            page.locator('[data-builder-preview]').click()

            # Saved source from before this fix can contain arbitrary coordinates.
            # Loading or saving it must not apply the new gesture-only snapping.
            legacy = {**deepcopy(horizontal), 'id': str(uuid4()),
                      'x1': 28.2, 'y1': 22.7, 'x2': 34.8, 'y2': 25.1}
            document = deepcopy(project['document'])
            document['walls'].append(legacy)
            result = page.evaluate("""async args => {
              const csrf = await (await fetch('/__gravewright/csrf')).json();
              const response = await fetch(args.url, {method: 'POST',
                headers: {'Content-Type': 'application/json', [csrf.header]: csrf.token},
                body: JSON.stringify(args.payload)});
              return {status: response.status, body: await response.json()};
            }""", {'url': api + '/projects/' + project['id'], 'payload': {
                'request_id': str(uuid4()), 'expected_version': project['version'],
                'folder_id': project['folderId'], 'document': document,
            }})
            assert result['status'] == 200, result
            project = result['body']['project']
            page.reload()
            wait_ready(page)
            expect(page.locator('[data-builder-walls] [data-object-id]')).to_have_count(4)
            assert save()['document']['walls'][-1] == legacy, save()
            set_name(page, 'Synthetic wall alignment preserved')
            project = save()
            document = deepcopy(project['document'])
            assert document['walls'][-1] == legacy, document
            page.locator('[data-builder-preview]').click()
            browser_samples('wall-reloaded-preview.png', project['document'])
            page.locator('[data-builder-preview]').click()
            assert save()['document'] == document
            records.append({'case': 'reload-keeps-artwork-and-legacy-wall-coordinates', 'legacy': legacy})

            # Restoring a cached page remounts the editor without duplicating
            # patterns or leaving input handlers from the previous mount.
            pattern_count = page.locator('[data-wall-texture]').count()
            for _ in range(2):
                page.evaluate("dispatchEvent(new PageTransitionEvent('pageshow', {persisted: true}))")
                wait_ready(page)
                ready_art()
                expect(page.locator('[data-wall-texture]')).to_have_count(pattern_count)
                assert save()['document'] == document
            page.locator('[data-builder-preview]').click()
            browser_samples('wall-restored-preview.png', document)
            page.locator('[data-builder-preview]').click()
            records.append({'case': 'cached-page-restoration-keeps-art-and-single-patterns'})

            with page.expect_response(lambda response: response.url.endswith('/generate')) as generated:
                page.locator('[data-builder-generate]').click()
            assert generated.value.ok, generated.value.status
            page.wait_for_url(f'{base}/game/{campaign}')
            generated_project = page.request.get(api + '/projects/' + project['id']).json()['project']
            assert generated_project['document'] == document
            scene_id = generated_project['sceneId']
            manifest_response = page.request.get(f'{base}/api/maps/{scene_id}/manifest')
            assert manifest_response.ok, manifest_response.text()
            manifest = manifest_response.json()
            raster = Image.new('RGB', (manifest['width'], manifest['height']))
            level = next(level for level in manifest['levels'] if level['lod'] == 0)
            try:
                for row in range(level['rows']):
                    for column in range(level['columns']):
                        url = manifest['tileUrlTemplate'].replace('{lod}', '0').replace('{x}', str(column)).replace('{y}', str(row))
                        tile_response = page.request.get(base + url)
                        assert tile_response.ok, (url, tile_response.status)
                        with Image.open(BytesIO(tile_response.body())) as tile:
                            raster.paste(tile, (column * manifest['tileSize'], row * manifest['tileSize']))
                raster.save(output / 'wall-generated-raster.png')
                for wall in document['walls']:
                    repeat_sample = 11.7 if wall['id'] == horizontal['id'] else 6.3
                    for distance, normal, expected in (
                        (.9, .12, RED), (3.6, .12, BLUE), (repeat_sample, .12, RED),
                        (.9, -.18, GREEN), (.9, .24, RED), (.9, .42, BACKGROUND),
                    ):
                        x, y = wall_point(wall, distance, normal)
                        pixel = raster.getpixel((round(x * document['cellSize']), round(y * document['cellSize'])))
                        assert_color(pixel, expected, {'wall': wall['id'], 'distance': distance, 'normal': normal})
                for x in (9.5, 10.5):
                    assert_color(raster.getpixel((round(x * document['cellSize']), 4 * document['cellSize'])),
                                 BACKGROUND, f'generated open door at {x}')
                assert_color(raster.getpixel((round(11.4 * document['cellSize']), round(4.12 * document['cellSize']))),
                             BLUE, 'generated wall phase after door')
            finally:
                raster.close()
            page.screenshot(path=str(output / 'wall-generated-scene.png'))
            records.append({'case': 'generated-raster-matches-wall-local-art-and-door-cuts',
                            'scene': scene_id, 'documentUnchanged': True})
        except Exception:
            page.screenshot(path=str(output / 'failure.png'), full_page=True)
            raise
        finally:
            context.close()
            browser.close()
    assert not errors, errors
    assert not dialogs, dialogs
    assert not [request for request in failed_requests if request['error'] != 'net::ERR_ABORTED'], failed_requests
    return {'passed': True, 'cases': records, 'pageErrors': errors,
            'nativeDialogs': dialogs, 'failedRequests': failed_requests,
            'artwork': 'Synthetic padded asymmetric RGBA strip only.'}


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
    output = (args.output or ROOT / 'data/map-builder-wall-art' /
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
