"""Small scene changes update their own layers on a real GPU board.

The synthetic scene has rooms of short walls with doors, thirty animated
torches, ember emitters, two shaders, drawings and cards, with dynamic
darkness. Each step (a drawing, a card, a door, a spatial sound, a light) is
applied several times as the GM and as a player. The report records the
synchronous ``SceneLayers.render`` time, the layers each step mounted, the
longest frame gap after it and long tasks. The visibility worker is served
beside the bundle, so walls past its threshold use it as on a real table. Assertions check that drawings,
cards and sounds mount nothing, that doors and lights keep the scene mounted
and that an opened door lets a torch reach the next room on the GPU.

``--frontend`` bundles the same fixture against another copy of
``gravewright/maps/frontend`` (for example an export of an earlier release)
for before/after measurements; combine it with ``--no-assert``. Headless
browsers usually render WebGL in software, so compare runs made on the same
machine rather than reading the timings as absolute frame budgets.
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
const [frontend, entry, output, alternate, workerOutput] = process.argv.slice(1);
const remap = alternate ? [{ name: 'alternate-frontend', setup(build) {
  build.onResolve({ filter: /gravewright\/maps\/frontend\// }, args => {
    const target = path.resolve(args.resolveDir, args.path);
    const relative = path.relative(frontend, target);
    if (relative.startsWith('..') || path.isAbsolute(relative)) return;
    return { path: path.join(alternate, relative) };
  });
}}] : [];
const esbuild = require(path.join(frontend, 'node_modules/esbuild'));
const common = { bundle: true, format: 'esm', target: 'es2022', nodePaths: [path.join(frontend, 'node_modules')] };
// The board starts its visibility worker beside the bundle: new URL('./visibility-worker.js', import.meta.url).
const worker = path.join(alternate || frontend, 'widgets/game-board/model/visibility-worker.js');
Promise.all([esbuild.build({ ...common, entryPoints: [entry], outfile: output, plugins: remap }),
  esbuild.build({ ...common, entryPoints: [worker], outfile: workerOutput })])
  .catch(error => { console.error(error); process.exitCode = 1; });
"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--workdir', type=Path)
    parser.add_argument('--browser-executable', type=Path)
    parser.add_argument('--node', type=Path)
    parser.add_argument('--frontend', type=Path, help='Another copy of gravewright/maps/frontend to measure')
    parser.add_argument('--repeat', type=int, default=5, help='Repetitions of each step (odd leaves the door open)')
    parser.add_argument('--no-assert', action='store_true', help='Only measure; for earlier sources')
    parser.add_argument('--only', action='append', metavar='STEP',
        help='Measure only this step label, such as "gm: toggle light"; repeatable')
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error('--repeat must be at least 1')
    alternate = args.frontend.resolve() if args.frontend else None
    if alternate and not (alternate / 'widgets/game-board/lib/scene-layers.js').is_file():
        parser.error(f'{alternate} is not a copy of gravewright/maps/frontend')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    work = (args.workdir or ROOT / f'data/runner/scene-layer-updates-{stamp}').resolve()
    work.mkdir(parents=True, exist_ok=True)
    scratch = work / 'temp'
    scratch.mkdir(exist_ok=True)
    for key in ('TMP', 'TEMP', 'TMPDIR'):
        os.environ[key] = str(scratch)
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / 'data/runner/playwright')
    node = str(args.node or shutil.which('node') or
        ROOT / '.venv/Lib/site-packages/playwright/driver/node.exe')
    subprocess.run([node, '-e', BUILD, str(FRONTEND), str(ROOT / 'tests/fixtures/scene_layer_updates.js'),
        str(work / 'scene-test.js'), str(alternate or ''), str(work / 'visibility-worker.js')], cwd=ROOT, check=True)
    (work / 'index.html').write_text(
        '<!doctype html><meta charset="utf-8"><title>Scene layer updates</title>'
        '<style>body{margin:0;background:#0c1824}</style>'
        '<script type="module" src="scene-test.js"></script>', encoding='utf-8')
    errors = []
    report = {'success': False, 'errors': errors, 'frontend': str(alternate or FRONTEND),
        'assertions': not args.no_assert, 'repeat': args.repeat}
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(work)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            launch = {'headless': True}
            if args.browser_executable:
                launch['executable_path'] = str(args.browser_executable)
            with playwright.chromium.launch(**launch) as browser:
                page = browser.new_page(viewport={'width': 1000, 'height': 700})
                page.on('pageerror', lambda error: errors.append({'message': str(error), 'stack': error.stack}))
                try:
                    page.goto(f'http://127.0.0.1:{server.server_port}/')
                    page.wait_for_function('typeof window.runSceneLayerUpdates === "function"')
                    report['result'] = page.evaluate('options => window.runSceneLayerUpdates(options)',
                        {'assertions': not args.no_assert, 'repeat': args.repeat, 'only': args.only})
                    assert not errors, errors
                    report['success'] = True
                finally:
                    page.screenshot(path=str(work / 'scene.png'))
                    page.evaluate('window.disposeSceneLayerUpdates?.()')
                    assert page.locator('canvas').count() == 0, 'disposed board removes its canvas'
    except Exception as error:
        report['success'] = False
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
