"""Asset updates invalidate transitive imports without duplicating modules."""

from tempfile import TemporaryDirectory
from pathlib import Path
from django.test import SimpleTestCase, override_settings
from .assets import module_import_map, static, versions


class AssetVersionTests(SimpleTestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'workspace.js').write_text("import './sheet.js';", encoding='utf-8')
        (self.root / 'sheet.js').write_text('export const template = "old";', encoding='utf-8')
        self.settings_override = override_settings(
            STATICFILES_DIRS=[self.root],
            STATICFILES_FINDERS=['django.contrib.staticfiles.finders.FileSystemFinder'],
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        versions.cache_clear()
        self.addCleanup(versions.cache_clear)

    def test_changed_dependency_gets_a_new_url_and_matches_direct_script(self):
        old = module_import_map()['imports']['/static/sheet.js']
        (self.root / 'sheet.js').write_text('export const template = "new";', encoding='utf-8')
        versions.cache_clear()
        imports = module_import_map()['imports']
        self.assertNotEqual(old, imports['/static/sheet.js'])
        self.assertEqual(imports['/static/sheet.js'], static('sheet.js'))
        self.assertEqual(imports['/static/workspace.js'], static('workspace.js'))

    def test_unversioned_noncode_assets_keep_their_url(self):
        self.assertEqual(static('image.png'), '/static/image.png')

    def test_import_map_has_request_specific_csp_authorization(self):
        import re
        from django.http import HttpResponse
        from django.template import engines
        from django.test import RequestFactory
        from gravewright.accounts.middleware import AuthSecurityMiddleware
        template = engines['jinja2'].get_template('gravewright_web/base.html')
        middleware = AuthSecurityMiddleware(lambda request: HttpResponse(template.render({'request': request})))
        first = middleware(RequestFactory().get('/asset-review'))
        second = middleware(RequestFactory().get('/asset-review'))
        pattern = r'<script type="importmap" nonce="([^"]+)"'
        first_nonce = re.search(pattern, first.content.decode()).group(1)
        second_nonce = re.search(pattern, second.content.decode()).group(1)
        self.assertNotEqual(first_nonce, second_nonce)
        self.assertIn("'nonce-" + first_nonce + "'", first['Content-Security-Policy'])
        self.assertNotIn("'unsafe-inline'", first['Content-Security-Policy'].split('style-src')[0])
