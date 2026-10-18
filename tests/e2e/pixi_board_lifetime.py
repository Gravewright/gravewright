"""Disposing one real GPU board must preserve every other mounted board.

This focused browser check bundles the actual local renderer sources. It needs
neither Django nor campaign data and uses only synthetic artwork and labels.
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
import subprocess
import threading

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / 'gravewright/maps/frontend'
BUILD = r"""
const path = require('node:path');
const [frontend, entry, output] = process.argv.slice(1);
require(path.join(frontend, 'node_modules/esbuild')).buildSync({
  entryPoints: [entry], bundle: true, format: 'esm', target: 'es2022',
  nodePaths: [path.join(frontend, 'node_modules')], outfile: output,
});
"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workdir', type=Path)
    parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--node', type=Path)
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    work = (args.workdir or ROOT / f'data/runner/pixi-board-lifetime-{stamp}').resolve()
    work.mkdir(parents=True, exist_ok=True)
    scratch = work / 'temp'
    scratch.mkdir(exist_ok=True)
    for key in ('TMP', 'TEMP', 'TMPDIR'):
        os.environ[key] = str(scratch)
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / 'data/runner/playwright')
    node = str(args.node or shutil.which('node') or
        ROOT / '.venv/Lib/site-packages/playwright/driver/node.exe')
    subprocess.run([node, '-e', BUILD, str(FRONTEND),
        str(ROOT / 'tests/fixtures/pixi_board_lifetime.js'), str(work / 'board-test.js')],
        cwd=ROOT, check=True)
    (work / 'index.html').write_text(
        '<!doctype html><meta charset="utf-8"><title>Board lifetime</title>'
        '<style>body{margin:0;background:#0c1824}</style>'
        '<script type="module" src="board-test.js"></script>', encoding='utf-8')
    errors = []
    report = {'success': False, 'errors': errors}
    server = ThreadingHTTPServer(('127.0.0.1', 0),
        functools.partial(QuietHandler, directory=str(work)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            launch = {'headless': True}
            if args.browser_executable:
                launch['executable_path'] = str(args.browser_executable)
            with playwright.chromium.launch(**launch) as browser:
                page = browser.new_page(viewport={'width': 1100, 'height': 760})
                page.on('pageerror', lambda error: errors.append({'message': str(error), 'stack': error.stack}))
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                page.wait_for_function('typeof window.runBoardLifetime === "function"')
                report['result'] = page.evaluate('window.runBoardLifetime()')
                page.wait_for_timeout(100)
                assert not errors, errors
                assert page.locator('canvas').count() == 0, 'every disposed board removes its own canvas'
                report['success'] = True
    except Exception as error:
        report['failure'] = str(error)
        raise
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        (work / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps({'success': report['success'], 'cases': len(report.get('result', {}).get('cases', [])),
            'errors': len(errors), 'report': str(work / 'report.json')}))


if __name__ == '__main__':
    main()
