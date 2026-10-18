"""Keep single and grouped floor art visible through region/effect updates.

This standalone WebGL fixture uses real local SceneLayers sources and synthetic
PNG material/mask responses. Holding replacement responses exposes even a single
blank frame without loading Django, a database or campaign media.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import threading
import zlib

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / 'gravewright/maps/frontend'
BUILD = r"""
const path = require('node:path'), fs = require('node:fs');
const [frontend, entry, output, savedSource, savedKey] = process.argv.slice(1);
require(path.join(frontend, 'node_modules/esbuild')).build({
  entryPoints: [entry], bundle: true, format: 'esm', target: 'es2022',
  nodePaths: [path.join(frontend, 'node_modules')], outfile: output,
  ...(savedSource || savedKey ? {plugins: [{name: 'saved-scene-layers', setup(build) {
    for (const [filter, source] of [[/game-board[\\/]lib[\\/]scene-layers\.js$/, savedSource],
        [/game-board[\\/]model[\\/]scene-render-key\.js$/, savedKey]]) {
      if (source) build.onLoad({filter}, args => ({
        contents: fs.readFileSync(source, 'utf8'), resolveDir: path.dirname(args.path), loader: 'js',
      }));
    }
  }}]} : {}),
}).catch(error => { console.error(error); process.exitCode = 1; });
"""


def png(width, height, color):
    def chunk(kind, value):
        return (struct.pack('!I', len(value)) + kind + value
            + struct.pack('!I', zlib.crc32(kind + value)))
    row = b'\0' + bytes(color) * width
    return (b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, 2, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress(row * height)) + chunk(b'IEND', b''))


class ArtworkHandler(SimpleHTTPRequestHandler):
    images = {
        '/game/map-assets/material': png(64, 64, (56, 112, 80)),
        '/game/map-assets/replacement-material': png(64, 64, (180, 95, 60)),
        '/game/map-assets/single-mask': png(200, 160, (255, 255, 255)),
        '/game/map-assets/group-mask': png(240, 200, (255, 255, 255)),
        '/game/map-assets/private-mask': png(80, 80, (255, 255, 255)),
        '/art/eraser': png(50, 50, (255, 255, 255)),
        '/art/decoration': png(80, 80, (81, 111, 174)),
    }

    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path in ('/gate/arm', '/gate/release'):
            (self.server.gate.clear if self.path == '/gate/arm' else self.server.gate.set)()
            self.reply('application/json', b'{}')
        elif self.path in self.images:
            with self.server.request_lock:
                self.server.art_requests[self.path] = self.server.art_requests.get(self.path, 0) + 1
            if not self.server.gate.wait(timeout=20):
                self.send_error(504, 'Synthetic delayed response was not released')
                return
            self.reply('image/png', self.images[self.path])
        elif self.path == '/favicon.ico':
            self.reply('image/x-icon', b'')
        else:
            super().do_GET()

    def reply(self, content_type, payload):
        try:
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workdir', type=Path)
    parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--node', type=Path)
    parser.add_argument('--scene-source', type=Path, help='Saved SceneLayers source for a before/after check')
    parser.add_argument('--render-key-source', type=Path, help='Saved SceneRenderKey source for a before/after check')
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    work = (args.workdir or ROOT / f'data/runner/scene-layer-continuity-{stamp}').resolve()
    work.mkdir(parents=True, exist_ok=True)
    scratch = work / 'temp'
    scratch.mkdir(exist_ok=True)
    for key in ('TMP', 'TEMP', 'TMPDIR'):
        os.environ[key] = str(scratch)
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / 'data/runner/playwright')
    node = str(args.node or shutil.which('node')
        or ROOT / '.venv/Lib/site-packages/playwright/driver/node.exe')
    subprocess.run([node, '-e', BUILD, str(FRONTEND),
        str(ROOT / 'tests/fixtures/scene_layer_continuity.js'), str(work / 'scene-test.js'),
        str(args.scene_source.resolve()) if args.scene_source else '',
        str(args.render_key_source.resolve()) if args.render_key_source else ''], cwd=ROOT, check=True)
    (work / 'index.html').write_text(
        '<!doctype html><meta charset="utf-8"><title>Scene layer continuity</title>'
        '<style>body{margin:0;background:#0c1824}</style>'
        '<script type="module" src="scene-test.js"></script>', encoding='utf-8')
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(ArtworkHandler, directory=str(work)))
    server.gate = threading.Event()
    server.gate.set()
    server.art_requests = {}
    server.request_lock = threading.Lock()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    errors = []
    report = {'success': False, 'errors': errors}
    try:
        with sync_playwright() as playwright:
            launch = {'headless': True}
            if args.browser_executable:
                launch['executable_path'] = str(args.browser_executable)
            with playwright.chromium.launch(**launch) as browser:
                page = browser.new_page(viewport={'width': 760, 'height': 560})
                page.on('pageerror', lambda error: errors.append({'message': str(error), 'stack': error.stack}))
                try:
                    page.goto(f'http://127.0.0.1:{server.server_port}/')
                    page.wait_for_function('typeof window.runSceneLayerContinuity === "function"')
                    report['result'] = page.evaluate('window.runSceneLayerContinuity()')
                    assert not errors, errors
                    report['success'] = True
                finally:
                    server.gate.set()
                    report['observed'] = page.evaluate('window.__sceneLayerContinuity')
                    page.screenshot(path=str(work / 'scene.png'))
                    page.evaluate('window.disposeSceneLayerContinuity?.()')
                    assert page.locator('canvas').count() == 0, 'disposed scene removes its canvas'
    except Exception as error:
        report['failure'] = str(error)
        raise
    finally:
        server.gate.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        report['requests'] = server.art_requests
        (work / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps({'success': report['success'],
            'cases': len(report.get('result', {}).get('cases', [])),
            'errors': len(errors), 'report': str(work / 'report.json')}))


if __name__ == '__main__':
    main()
