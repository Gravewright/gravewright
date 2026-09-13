"""Localized presentation must never serve as a frontend control identifier."""
import re
from django.conf import settings
from django.test import SimpleTestCase


class TranslationHookTests(SimpleTestCase):
    def test_frontend_selectors_do_not_match_translatable_attribute_values(self):
        pattern = re.compile(r'\[\s*(?:aria-label|title|placeholder|alt)\s*[*^$|~]?=')
        failures = []
        for path in (settings.BASE_DIR / 'gravewright').rglob('*'):
            if path.suffix not in {'.js', '.ts', '.html', '.css'} or {'vendor', 'node_modules'} & set(path.parts) or not path.is_file():
                continue
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if pattern.search(line):
                    failures.append(f'{path.relative_to(settings.BASE_DIR)}:{number}')
        self.assertEqual(failures, [], 'Use stable data-* hooks instead of translated labels.')

    def test_control_dispatch_does_not_compare_accessibility_labels(self):
        pattern = re.compile(
            r'''getAttribute\(\s*['"](?:aria-label|title|placeholder|alt)['"]\s*\)\s*(?:===?|!==?)'''
            r'''|\.includes\(\s*\w+\.getAttribute\(\s*['"](?:aria-label|title|placeholder|alt)['"]'''
        )
        failures = []
        for path in (settings.BASE_DIR / 'gravewright').rglob('*.js'):
            if path.is_file() and not {'vendor', 'node_modules'} & set(path.parts) and pattern.search(path.read_text()):
                failures.append(str(path.relative_to(settings.BASE_DIR)))
        self.assertEqual(failures, [], 'Dispatch actions using stable IDs, never visible labels.')
