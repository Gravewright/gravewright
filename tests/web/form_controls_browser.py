"""Exercise shared form appearance and native behavior without campaign data."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import unittest
from urllib.parse import unquote, urlsplit

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'test-results' / 'form-controls'
STATIC = {
    name: ROOT / f'gravewright/{name}/static/gravewright_{name}'
    for name in ['web', 'table', 'pdf_system']
}
HTML = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/static/gravewright_web/css/tokens.css">
<link rel="stylesheet" href="/static/gravewright_web/css/index.css">
<style>
main { max-width: 900px; margin: var(--space-0) auto; padding: var(--space-5); }
h1 { font-size: var(--text-2xl); }
.native-fields { display: grid; gap: var(--space-3); }
.native-fields label { display: grid; min-width: 0; gap: var(--space-1); }
</style></head><body><main>
<h1>Shared form controls</h1>
<form class="gw-form">
<div class="gw-form__grid">
<label class="gw-field"><span class="gw-field__label">Campaign name</span>
<input name="title" required maxlength="80" placeholder="Name your campaign"></label>
<label class="gw-field"><span class="gw-field__label">System</span>
<select name="system"><option>Gravewright PDF System</option><option>Another system</option></select></label>
<label class="gw-field"><span class="gw-field__label">Description</span>
<textarea name="description" rows="4">An unfinished story with a long description that wraps across narrow screens.</textarea></label>
<label class="gw-field"><span class="gw-field__label">Image</span>
<input type="file" name="image" accept="image/png,image/jpeg" aria-describedby="image-help">
<small id="image-help">PNG or JPEG</small></label>
<label class="gw-field"><span class="gw-field__label">Visible choices</span>
<select name="choices" multiple size="3"><option value="one">One</option><option value="two">Two</option><option value="three">Three</option></select></label>
<label class="gw-field"><span class="gw-field__label">Email</span>
<input type="email" name="email" required aria-describedby="email-help">
<small id="email-help">Use a valid email address.</small></label>
<label class="gw-field"><span class="gw-field__label">Read only</span>
<input name="readonly" value="A generated access code" readonly></label>
<label class="gw-field"><span class="gw-field__label">Disabled</span>
<input name="disabled" value="Unavailable" disabled></label>
<label class="gw-field gw-field--inline"><span>Show grid</span><input type="checkbox" name="grid" checked></label>
<label class="gw-field gw-field--inline"><span>Public scene</span><input type="radio" name="visibility" checked></label>
<label class="gw-field"><span>Opacity</span><input type="range" name="opacity" min="0" max="100" value="40"></label>
<label class="gw-field gw-field--inline"><span>Grid color</span><input type="color" name="color" value="#c09a5a"></label>
<label class="gw-switch"><input class="gw-switch__input" type="checkbox" name="notifications"><span class="gw-switch__control"></span><span class="gw-switch__text"><span class="gw-switch__title">Notifications</span><span class="gw-switch__help">Keep the native keyboard behavior.</span></span></label>
</div>
<div class="gw-form__footer"><span class="gw-form__note">Synthetic data only</span><button class="gw-button gw-button--primary">Save</button></div>
</form>
<h1>Fields mounted without component classes</h1>
<section class="native-fields" id="dynamic"></section>
<script>
const root = document.querySelector('#dynamic');
for (const type of ['text', 'search', 'url', 'email', 'password', 'number', 'date', 'datetime-local', 'time', 'file']) {
  const label = document.createElement('label');
  label.textContent = type;
  const input = document.createElement('input');
  input.type = type; input.name = 'native-' + type;
  label.append(input); root.append(label);
}
document.querySelector('form').addEventListener('submit', event => event.preventDefault());
</script></main></body></html>'''

GEOMETRY_HTML = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<link rel="stylesheet" href="/static/gravewright_web/css/tokens.css">
<link rel="stylesheet" href="/static/gravewright_web/css/index.css">
<link rel="stylesheet" href="/static/gravewright_pdf_system/pdf-sheet.css">
<link rel="stylesheet" href="/static/gravewright_table/window-polish.css">
</head><body><div id="table-workspace"></div><main class="gw-window">
<div class="pdf-sheet__stage" style="position:relative;width:260px;height:80px">
<input class="pdf-sheet__field" id="authored-small" style="width:320px;height:16px;top:0;font-size:9px" value="Authored text">
<input class="pdf-sheet__field" id="authored-large" style="width:180px;height:20px;top:30px" value="Authored text">
</div>
<div class="pdf-sheet__stage" data-viewer-missing="true"><div class="pdf-sheet__fields">
<input class="pdf-sheet__field" id="fallback" value="Fallback form field">
</div></div>
</main></body></html>'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if path == '/':
            raw, kind = HTML.encode(), 'text/html; charset=utf-8'
        elif path == '/geometry':
            raw, kind = GEOMETRY_HTML.encode(), 'text/html; charset=utf-8'
        elif path.startswith('/static/gravewright_'):
            package, _, relative = path.removeprefix('/static/gravewright_').partition('/')
            root = STATIC.get(package)
            target = (root / relative).resolve() if root else None
            if target is None or not target.is_relative_to(root) or not target.is_file():
                self.send_error(404)
                return
            raw, kind = target.read_bytes(), 'text/css; charset=utf-8'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class FormControlsBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'
        OUTPUT.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def test_native_controls_keep_the_theme_and_keyboard_behavior(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={'width': 1100, 'height': 900})
            page.goto(self.base)
            expect(page.locator('[name="native-file"]')).to_be_visible()
            surfaces = page.locator('input:not([type="checkbox"], [type="radio"], [type="range"], [type="color"]), select, textarea').evaluate_all('''controls => controls.map(control => {
                const style = getComputedStyle(control);
                return {name: control.name, background: style.backgroundColor, size: parseFloat(style.fontSize)};
            })''')
            for surface in surfaces:
                self.assertEqual(surface['background'], 'rgb(21, 26, 32)', surface)
                self.assertGreaterEqual(surface['size'], 12, surface)
            for name in ['image', 'native-file']:
                color = page.locator(f'[name="{name}"]').evaluate("el => getComputedStyle(el, '::file-selector-button').backgroundColor")
                self.assertNotIn(color, ['rgb(239, 239, 239)', 'rgb(255, 255, 255)'])
            self.assertNotEqual(page.locator('[name="system"]').evaluate('el => getComputedStyle(el).backgroundImage'), 'none')
            self.assertEqual(page.locator('[name="choices"]').evaluate('el => getComputedStyle(el).backgroundImage'), 'none')
            for name in ['grid', 'visibility']:
                box = page.locator(f'[name="{name}"]').bounding_box()
                self.assertLessEqual(box['width'], 22)
                self.assertLessEqual(box['height'], 22)
            grid = page.locator('[name="grid"]')
            grid.focus()
            page.keyboard.press('Space')
            expect(grid).not_to_be_checked()
            slider = page.locator('[name="opacity"]')
            slider.focus()
            page.keyboard.press('ArrowRight')
            expect(slider).to_have_value('41')
            expect(page.locator('[name="readonly"]')).to_have_value('A generated access code')
            self.assertFalse(page.locator('[name="readonly"]').is_editable())
            expect(page.locator('[name="disabled"]')).to_be_disabled()
            image = page.locator('[name="image"]')
            image.focus()
            self.assertTrue(image.evaluate("el => el.matches(':focus-visible')"))
            with page.expect_file_chooser() as chooser:
                page.keyboard.press('Enter')
            chooser.value.set_files({'name': 'a-long-synthetic-cover-name.png', 'mimeType': 'image/png', 'buffer': b'synthetic'})
            self.assertEqual(image.evaluate('el => el.files[0].name'), 'a-long-synthetic-cover-name.png')
            page.locator('[name="title"]').fill('Synthetic campaign')
            email = page.locator('[name="email"]')
            email.fill('invalid')
            email.blur()
            expect(email).to_have_css('border-top-color', 'rgb(210, 121, 107)')
            email.fill('owner@example.test')
            email.blur()
            expect(email).not_to_have_css('border-top-color', 'rgb(210, 121, 107)')
            email.evaluate("el => el.setAttribute('aria-invalid', 'true')")
            expect(email).to_have_css('border-top-color', 'rgb(210, 121, 107)')
            for width in [1100, 390, 320]:
                page.set_viewport_size({'width': width, 'height': 900})
                self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), width)
                self.assertEqual(page.locator('[name="title"]').bounding_box()['height'], 42)
                page.screenshot(path=str(OUTPUT / f'controls-{width}.png'), full_page=True)
            browser.close()

    def test_pdf_fields_preserve_authored_sizes_inside_table_windows(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            page.goto(self.base + '/geometry')
            small = page.locator('#authored-small')
            self.assertEqual(small.bounding_box()['height'], 16)
            self.assertEqual(small.bounding_box()['width'], 320)
            expect(small).to_have_css('font-size', '9px')
            self.assertEqual(page.locator('#authored-large').bounding_box()['height'], 20)
            self.assertGreaterEqual(page.locator('#fallback').bounding_box()['height'], 26)
            small.fill('Updated authored text')
            expect(small).to_have_value('Updated authored text')
            browser.close()


if __name__ == '__main__':
    unittest.main()
