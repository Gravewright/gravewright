"""Equivalent package/release identities and prerelease update ordering."""

from django.test import SimpleTestCase

from .release_metadata import normalize_version, update_version_is_valid, version_key, version_label
from .updates import _channel


class ReleaseVersionTests(SimpleTestCase):
    def test_python_and_public_alpha_identifiers_are_equivalent(self):
        self.assertEqual(normalize_version('0.1.0a0'), '0.1.0-alpha.0')
        self.assertEqual(normalize_version('v0.1.0-alpha.0'), '0.1.0-alpha.0')
        self.assertTrue(update_version_is_valid('0.1.0a0'))
        self.assertEqual(version_key('0.1.0a0'), version_key('0.1.0-alpha.0'))
        self.assertEqual(version_label('0.1.0a0'), 'Alpha 0.1.0')
        self.assertEqual(version_label('0.1.0-alpha.0'), 'Alpha 0.1.0')
        self.assertEqual(_channel('0.1.0a0'), 'dev')

    def test_prerelease_sequence_compares_numbers_and_precedes_stable(self):
        versions = ['0.1.0a0', '0.1.0-alpha.2', '0.1.0-alpha.10',
                    '0.1.0b0', '0.1.0rc1', '0.1.0']
        self.assertEqual(sorted(reversed(versions), key=version_key), versions)
        self.assertEqual(_channel('0.1.0b0'), 'testing')
        self.assertEqual(_channel('0.1.0rc1'), 'testing')
        self.assertEqual(_channel('0.1.0'), 'stable')
        self.assertEqual(version_label('0.1.0-alpha.2'), 'Alpha 0.1.0 (2)')

    def test_invalid_release_is_not_a_version(self):
        for value in (None, 'Alpha 0.1.0', 'release', '0.1.0/alpha'):
            self.assertFalse(update_version_is_valid(value))
