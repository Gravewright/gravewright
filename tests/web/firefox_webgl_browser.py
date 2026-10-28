"""Exercise real Pixi texture uploads and context recovery in Playwright Firefox.

Serve the built host assets with synthetic graphics; no campaign or database is
needed. Install Playwright's Firefox before running this standalone test.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit
import unittest

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
STATIC_ROOTS = tuple((ROOT / 'gravewright').glob('*/static'))
HTML = b'''<!doctype html><html><head><style>
body { margin: 0; } #board { width: 128px; height: 128px; }
</style></head><body><div id="board"></div><script type="module">
import { createPixiApplication } from '/static/gravewright_maps/runtime/widgets/game-board/lib/pixi-application.js';
import { PixiBoardRenderer } from '/static/gravewright_maps/runtime/widgets/game-board/lib/pixi-board-renderer.js';
import { Graphics, Sprite, Texture, Text } from '/static/gravewright_maps/vendor/pixi.js';
const host = document.querySelector('#board');
window.application = await createPixiApplication({ width: 128, height: 128,
    background: '#182030', antialias: true, autoStart: false });
host.append(application.canvas);
window.board = new PixiBoardRenderer(application, 'Synthetic board');
const white = new Sprite(Texture.WHITE);
white.position.set(12, 12); white.width = 48; white.height = 48;
const empty = new Sprite(Texture.EMPTY);
empty.position.set(64, 12); empty.width = 48; empty.height = 48;
const marker = new Graphics().rect(12, 72, 48, 36).fill('#cc8040');
const text = new Text({text: 'VTT', style: {fontSize: 16, fill: '#ffffff'}});
text.position.set(70, 84);
application.stage.addChild(white, empty, marker, text);
let renders = 0;
const render = application.render.bind(application);
application.render = () => { render(); window.renderCount = ++renders; };
board.invalidate();
window.ready = true;
</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/':
            content, kind = HTML, 'text/html'
        elif path.startswith('/static/'):
            content = None
            for root in STATIC_ROOTS:
                candidate = (root / path.removeprefix('/static/')).resolve()
                if candidate.is_relative_to(root.resolve()) and candidate.is_file():
                    content = candidate.read_bytes()
                    break
            if content is None:
                self.send_error(404)
                return
            kind = 'text/javascript'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)


class FirefoxWebGLTests(unittest.TestCase):
    def test_uploads_are_initialized_and_restored_board_repaints_without_input(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.firefox.launch()
                page = browser.new_page(viewport={'width': 256, 'height': 256})
                warnings, errors = [], []
                page.on('console', lambda message: warnings.append(message.text)
                        if message.type in ('warning', 'error') else None)
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                page.wait_for_function('window.ready && window.renderCount > 0')
                canvas = page.locator('#board canvas')
                before = Image.open(BytesIO(canvas.screenshot())).convert('RGB')
                self.assertEqual(before.getpixel((24, 24)), (255, 255, 255))
                self.assertEqual(before.getpixel((80, 24)), (24, 32, 48))
                self.assertEqual(warnings, [])
                self.assertEqual(errors, [])
                page.evaluate('''() => {
                    const canvas = document.querySelector('#board canvas');
                    window.gl = canvas.getContext('webgl2');
                    window.loss = gl.getExtension('WEBGL_lose_context');
                    window.previousRenderCount = renderCount;
                    window.restored = false;
                    canvas.addEventListener('webglcontextrestored', () => window.restored = true, {once: true});
                    loss.loseContext();
                }''')
                page.wait_for_function('gl.isContextLost()')
                # This loss is deliberately induced; real startup emitted none.
                page.evaluate('loss.restoreContext()')
                page.wait_for_function('window.restored && renderCount > previousRenderCount')
                after = Image.open(BytesIO(canvas.screenshot())).convert('RGB')
                if ImageChops.difference(before, after).getbbox():
                    output = ROOT / 'data/diagnostics/firefox-webgl-recovery'
                    output.mkdir(parents=True, exist_ok=True)
                    before.save(output / 'before.png')
                    after.save(output / 'after.png')
                self.assertIsNone(ImageChops.difference(before, after).getbbox())
                self.assertEqual(errors, [])
                self.assertEqual([message for message in warnings
                                  if 'WebGL context was lost.' not in message], [])
                page.evaluate('board.destroy()')
                self.assertEqual(canvas.count(), 0)
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
