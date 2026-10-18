"""Teleport only the token presentation while preserving the camera and floor.

This standalone WebGL fixture uses the actual token controller and renderer,
synthetic artwork and deliberately delayed responses. No Django, campaign data
or server writes are needed.
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
const [frontend, entry, output, snapshot] = process.argv.slice(1);
require(path.join(frontend, 'node_modules/esbuild')).build({
  entryPoints: [entry], bundle: true, format: 'esm', target: 'es2022',
  nodePaths: [path.join(frontend, 'node_modules')], outfile: output,
  ...(snapshot ? {plugins: [{name: 'saved-token-presentation', setup(build) {
    for (const [filter, filename] of [
      [/game-board[\\/]lib[\\/]pixi-board-renderer\.js$/, 'pixi-board-renderer.js'],
      [/tokens[\\/]ui[\\/]controller\.js$/, 'controller.js'],
      [/tokens[\\/]model[\\/]token-motion\.js$/, 'token-motion.js'],
    ]) build.onLoad({filter}, args => ({
      contents: fs.readFileSync(path.join(snapshot, filename), 'utf8'),
      resolveDir: path.dirname(args.path), loader: 'js',
    }));
  }}]} : {}),
}).catch(error => { console.error(error); process.exitCode = 1; });
"""


def png(color):
    def chunk(kind, value):
        return (struct.pack('!I', len(value)) + kind + value
            + struct.pack('!I', zlib.crc32(kind + value)))
    return (b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', struct.pack('!2I5B', 96, 96, 8, 2, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress((b'\0' + bytes(color) * 96) * 96))
        + chunk(b'IEND', b''))


class ArtworkHandler(SimpleHTTPRequestHandler):
    images = {f'/art/{name}.png': png((81, 111, 174) if name == 'final' else (232, 74, 96))
        for name in ('hero', 'slow', 'stale', 'final', 'dispose')}

    def log_message(self, *_args):
        pass

    def do_GET(self):
        parts = self.path.strip('/').split('/')
        if self.path == '/requests':
            with self.server.request_lock:
                payload = json.dumps(self.server.art_requests).encode()
            self.reply('application/json', payload)
        elif (len(parts) == 3 and parts[0] == 'gate' and parts[1] in self.server.gates
                and parts[2] in ('arm', 'release')):
            gate = self.server.gates[parts[1]]
            (gate.clear if parts[2] == 'arm' else gate.set)()
            self.reply('application/json', b'{}')
        elif self.path in self.images:
            name = Path(self.path).stem
            with self.server.request_lock:
                self.server.art_requests[name] = self.server.art_requests.get(name, 0) + 1
            if name in self.server.gates and not self.server.gates[name].wait(timeout=20):
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
    parser.add_argument('--source-snapshot', type=Path,
        help='Directory with saved controller.js, token-motion.js and pixi-board-renderer.js for before/after checks')
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    work = (args.workdir or ROOT / f'data/runner/token-teleport-presentation-{stamp}').resolve()
    work.mkdir(parents=True, exist_ok=True)
    scratch = work / 'temp'
    scratch.mkdir(exist_ok=True)
    for key in ('TMP', 'TEMP', 'TMPDIR'):
        os.environ[key] = str(scratch)
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / 'data/runner/playwright')
    node = str(args.node or shutil.which('node')
        or ROOT / '.venv/Lib/site-packages/playwright/driver/node.exe')
    subprocess.run([node, '-e', BUILD, str(FRONTEND),
        str(ROOT / 'tests/fixtures/token_teleport_presentation.js'), str(work / 'teleport-test.js'),
        str(args.source_snapshot.resolve()) if args.source_snapshot else ''], cwd=ROOT, check=True)
    (work / 'index.html').write_text(
        '<!doctype html><meta charset="utf-8"><title>Token teleport presentation</title>'
        '<style>body{margin:0;background:#0c1824}</style>'
        '<script type="module" src="teleport-test.js"></script>', encoding='utf-8')
    server = ThreadingHTTPServer(('127.0.0.1', 0),
        functools.partial(ArtworkHandler, directory=str(work)))
    server.gates = {name: threading.Event() for name in ('slow', 'stale', 'dispose')}
    for gate in server.gates.values():
        gate.set()
    server.request_lock = threading.Lock()
    server.art_requests = {}
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
                page = browser.new_page(viewport={'width': 820, 'height': 520}, reduced_motion='no-preference')
                page.on('pageerror', lambda error: errors.append({'message': str(error), 'stack': error.stack}))
                page.on('console', lambda message: errors.append({'message': message.text})
                    if message.type == 'error' else None)
                try:
                    page.goto(f'http://127.0.0.1:{server.server_port}/')
                    page.wait_for_function('typeof window.runTokenTeleportPresentation === "function"')
                    report['result'] = page.evaluate('window.runTokenTeleportPresentation()')
                    assert not errors, errors
                    assert page.locator('canvas').count() == 0, 'disposed board must remove its canvas'
                    assert server.art_requests.get('slow') == 1, 'rapid teleports must share one artwork request'
                    report['success'] = True
                finally:
                    if 'result' not in report:
                        report['result'] = page.evaluate('window.__tokenTeleportPresentation || {}')
                    page.screenshot(path=str(work / 'final.png'))
    except Exception as error:
        report['failure'] = str(error)
        raise
    finally:
        for gate in server.gates.values():
            gate.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        report['art_requests'] = server.art_requests
        (work / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps({'success': report['success'], 'cases': len(report.get('result', {}).get('cases', [])),
            'errors': len(errors), 'report': str(work / 'report.json')}))


if __name__ == '__main__':
    main()
