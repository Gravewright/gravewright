"""Each extracted installation owns its updater state, regardless of OS profile."""
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.test import SimpleTestCase

from scripts import process_control


class InstallationStorageTests(SimpleTestCase):
    def test_two_installations_ignore_foreign_global_state_on_all_platforms(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            global_state = root / 'profile/Gravewright/updates/active.json'
            global_state.parent.mkdir(parents=True)
            original = json.dumps({'path': str(root / 'obsolete-installation')}).encode()
            global_state.write_bytes(original)
            environment = {
                'LOCALAPPDATA': str(root / 'profile'), 'APPDATA': str(root / 'profile'),
                'HOME': str(root / 'profile'), 'XDG_DATA_HOME': str(root / 'profile'),
                'XDG_STATE_HOME': str(root / 'profile'),
            }
            for platform in ('win32', 'linux', 'darwin'):
                with self.subTest(platform=platform), patch.dict(os.environ, environment, clear=True), \
                        patch.object(process_control.sys, 'platform', platform), \
                        patch.object(Path, 'home', side_effect=AssertionError('Do not use global profile defaults.')), \
                        patch.object(Path, 'cwd', return_value=root / 'unrelated-cwd'):
                    first = process_control.state_home(root / 'first VTT')
                    second = process_control.state_home(root / 'second VTT')
                    self.assertEqual(first, root / 'first VTT/data/updates')
                    self.assertEqual(second, root / 'second VTT/data/updates')
                    self.assertNotEqual(first, second)
                    self.assertEqual(global_state.read_bytes(), original)
                    self.assertFalse(first.exists())
                    self.assertFalse(second.exists())

    def test_default_state_is_relative_to_source_location_without_creating_it(self):
        with patch.object(process_control, '__file__', str(Path('/installation/scripts/process_control.py'))):
            expected = Path(process_control.__file__).resolve().parents[1] / 'data/updates'
            self.assertEqual(process_control.state_home(), expected)
