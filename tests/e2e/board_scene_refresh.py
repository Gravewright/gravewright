"""Same-scene updates preserve the real GPU board, camera and visible artwork.

This standalone browser regression serves synthetic PNGs and the actual local
board sources. Delayed image responses exercise continuity and cancellation
without Django, campaign data or installed modules.
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
const path = require('node:path');
const [frontend, entry, output, boardSource] = process.argv.slice(1);
require(path.join(frontend, 'node_modules/esbuild')).build({
  entryPoints: [entry], bundle: true, format: 'esm', target: 'es2022',
  nodePaths: [path.join(frontend, 'node_modules')], outfile: output,
  ...(boardSource ? {plugins: [{ name: 'saved-board', setup(build) {
    build.onResolve({ filter: /game-board\/ui\/board\.js$/ }, () => ({path: boardSource}));
  }}]} : {}),
}).catch(error => { console.error(error); process.exitCode = 1; });
"""


def png(color):
    def chunk(kind, value):
        return struct.pack('!I', len(value)) + kind + value + struct.pack('!I', zlib.crc32(kind + value))
    row = b'\0' + bytes(color) * 1024
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', 1024, 1024, 8, 2, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress(row * 1024)) + chunk(b'IEND', b''))


class ArtworkHandler(SimpleHTTPRequestHandler):
    colors = {'original': (42, 80, 112), 'revised': (160, 60, 95),
        'superseded': (192, 98, 45), 'latest': (70, 110, 190), 'recovered': (190, 105, 42),
        'stale': (212, 150, 30), 'other': (60, 144, 72)}
    images = {name: png(color) for name, color in colors.items()}

    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path in ('/gate/status', '/gate/failures'):
            with self.server.gate_lock:
                payload = json.dumps(self.server.failures if self.path == '/gate/failures'
                    else self.server.requests).encode()
            self.reply('application/json', payload)
        elif self.path.startswith('/gate/release/'):
            name = self.path.removeprefix('/gate/release/')
            self.server.gates[name].set()
            self.reply('application/json', b'{}')
        elif self.path.startswith('/tiles/'):
            name = self.path.removeprefix('/tiles/').removesuffix('.png')
            if name not in self.images:
                self.send_error(404)
                return
            with self.server.gate_lock:
                self.server.requests[name] += 1
                attempt = self.server.requests[name]
            if name == 'recovered' and attempt == 1:
                self.reply('text/plain', b'Synthetic temporary image failure', status=503)
                with self.server.gate_lock:
                    self.server.failures[name] += 1
                return
            gate = self.server.gates.get(name)
            if gate and not gate.wait(timeout=30):
                self.send_error(504, 'Synthetic delayed response was not released')
                return
            self.reply('image/png', self.images[name])
        else:
            super().do_GET()

    def reply(self, content_type, payload, status=200):
        try:
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # Scene changes intentionally cancel a pending image response.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workdir', type=Path)
    parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--node', type=Path)
    parser.add_argument('--board-source', type=Path, help='Saved board bundle for a before/after regression check')
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    work = (args.workdir or ROOT / f'data/runner/board-scene-refresh-{stamp}').resolve()
    work.mkdir(parents=True, exist_ok=True)
    scratch = work / 'temp'
    scratch.mkdir(exist_ok=True)
    for key in ('TMP', 'TEMP', 'TMPDIR'):
        os.environ[key] = str(scratch)
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / 'data/runner/playwright')
    node = str(args.node or shutil.which('node') or
        ROOT / '.venv/Lib/site-packages/playwright/driver/node.exe')
    subprocess.run([node, '-e', BUILD, str(FRONTEND),
        str(ROOT / 'tests/fixtures/board_scene_refresh.js'), str(work / 'board-test.js'),
        str(args.board_source.resolve()) if args.board_source else ''], cwd=ROOT, check=True)
    (work / 'index.html').write_text(
        '<!doctype html><meta charset="utf-8"><title>Board scene refresh</title>'
        '<style>body{margin:0;background:#0c1824}</style>'
        '<script type="module" src="board-test.js"></script>', encoding='utf-8')
    errors = []
    report = {'success': False, 'errors': errors}
    server = ThreadingHTTPServer(('127.0.0.1', 0),
        functools.partial(ArtworkHandler, directory=str(work)))
    server.gates = {name: threading.Event() for name in
        ('revised', 'superseded', 'latest', 'recovered', 'stale', 'other')}
    server.requests = {name: 0 for name in ArtworkHandler.colors}
    server.failures = {name: 0 for name in ArtworkHandler.colors}
    server.gate_lock = threading.Lock()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            launch = {'headless': True}
            if args.browser_executable:
                launch['executable_path'] = str(args.browser_executable)
            with playwright.chromium.launch(**launch) as browser:
                page = browser.new_page(viewport={'width': 900, 'height': 680})
                page.on('pageerror', lambda error: errors.append({'message': str(error), 'stack': error.stack}))
                try:
                    page.goto(f'http://127.0.0.1:{server.server_port}/')
                    page.wait_for_function('typeof window.runBoardSceneRefresh === "function"')
                    page.evaluate('window.boardSceneRefreshResult = window.runBoardSceneRefresh(); undefined')
                    page.wait_for_function('typeof window.continueBoardSceneRefresh === "function"')
                    page.mouse.move(360, 260)
                    for _ in range(5):
                        page.mouse.wheel(0, -100)
                    page.mouse.move(150, 150)
                    page.mouse.down(button='middle')
                    page.mouse.move(195, 180, steps=3)
                    page.mouse.up(button='middle')
                    page.evaluate('window.continueBoardSceneRefresh()')
                    report['result'] = page.evaluate('window.boardSceneRefreshResult')
                    assert not errors, errors
                    report['success'] = True
                finally:
                    page.screenshot(path=str(work / 'board.png'))
                    page.evaluate('window.disposeBoardSceneRefresh?.()')
                    assert page.locator('canvas').count() == 0, 'disposed board removes its canvas'
    except Exception as error:
        report['success'] = False
        report['failure'] = str(error)
        raise
    finally:
        for gate in server.gates.values():
            gate.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        report['requests'] = server.requests
        report['failures'] = server.failures
        (work / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps({'success': report['success'], 'cases': len(report.get('result', {}).get('cases', [])),
            'errors': len(errors), 'report': str(work / 'report.json')}))


if __name__ == '__main__':
    main()
