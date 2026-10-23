"""Translation inventory must include the native Translator adapter calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import audit_translations


class TranslationAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.catalogs = self.root / 'catalogs'
        self.catalogs.mkdir()
        self.write_catalogs({'Existing label': 'Existing label'})

    def write_catalogs(self, source, translated=None):
        for locale, messages in [('en', source), ('pt-BR', translated or source)]:
            (self.catalogs / f'{locale}.json').write_text(
                json.dumps(messages, ensure_ascii=False), encoding='utf-8')

    def javascript(self, relative, content):
        target = self.root / 'gravewright' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')

    def audit(self):
        with patch.object(audit_translations, 'ROOT', self.root):
            return audit_translations.audit(self.catalogs)

    def test_native_and_adapter_calls_are_reported_with_their_source_paths(self):
        self.javascript('maps/panel.js', '''
            t('Full vision');
            translator.t('Visibility');
            api.i18n.t ('Open mind map');
            gwText('Clock controls');
            modalText('Clue controls');
            text('Roll formula');
            label('Reference field');
            t(' Existing label ');
        ''')
        errors, missing = self.audit()
        self.assertEqual(errors, [])
        self.assertEqual(set(missing), {
            'Full vision', 'Visibility', 'Open mind map', 'Clock controls',
            'Clue controls', 'Roll formula', 'Reference field',
        })
        self.assertTrue(all(paths == ['gravewright/maps/panel.js'] for paths in missing.values()))

    def test_content_dynamic_values_dependencies_and_test_fixtures_are_not_inventory(self):
        self.javascript('maps/panel.js', '''
            const authoredName = 'The Lantern Gate';
            t(authoredName);
            api.i18n.t('module.custom_label');
            t('Existing label');
        ''')
        for path in ('maps/vendor/library.js', 'maps/node_modules/library/index.js', 'maps/panel.test.js'):
            self.javascript(path, "t('Dependency or test text');")
        self.assertEqual(self.audit(), ([], {}))

    def test_javascript_escapes_resolve_to_the_actual_catalog_key(self):
        self.javascript('pdf/fields.js', r'''t('Preparing PDF page {0} of {1}\u2026');''')
        errors, missing = self.audit()
        self.assertEqual(errors, [])
        self.assertEqual(missing, {
            'Preparing PDF page {0} of {1}…': ['gravewright/pdf/fields.js'],
        })

    def test_catalog_validation_still_rejects_lost_parameters_and_missing_keys(self):
        self.write_catalogs({'Hello {name}: {0}': 'Hello {name}: {0}'},
                            {'Hello {name}: {0}': 'Olá {name}: {1}', 'Extra label': 'Outro rótulo'})
        errors, missing = self.audit()
        self.assertIn('pt-BR: different source keys', errors)
        self.assertIn('pt-BR: altered placeholders: Hello {name}: {0}', errors)
        self.assertEqual(missing, {})
