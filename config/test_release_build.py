"""Source archives ship executable installers, never personal launchers or data."""

from pathlib import Path
import stat
import tempfile
from unittest import TestCase
from unittest.mock import patch
import zipfile

from scripts import build_release


class InstallerArchiveTests(TestCase):
    def test_archive_keeps_posix_installers_executable_and_excludes_private_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            notes = 'docs/releases/0.2.1.md'
            names = build_release.required_files(notes) | {
                'scripts/posix/runner.sh', 'Gravewright Runner.bat',
                'Gravewright Runner.sh', 'Gravewright Runner.command',
                'Gravewright Runner.desktop', '.Gravewright-staging.command',
                '.env', 'data/private.txt',
            }
            for name in names:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('private' if name.startswith(('Gravewright Runner', '.env', 'data/')) else 'public\n', encoding='utf-8')
            (root / 'pyproject.toml').write_text('[project]\nname = "gravewright-vtt"\nversion = "0.2.1"\n', encoding='utf-8')
            (root / 'uv.lock').write_text('[[package]]\nname = "gravewright-vtt"\nversion = "0.2.1"\n', encoding='utf-8')
            (root / 'gravewright/maps/frontend/package.json').write_text('{"version":"0.2.1"}', encoding='utf-8')
            (root / 'gravewright/maps/frontend/package-lock.json').write_text('{"version":"0.2.1","packages":{"":{"version":"0.2.1"}}}', encoding='utf-8')
            with patch.object(build_release, 'git_files', return_value=names):
                result = build_release.build(root)
            with zipfile.ZipFile(result['archive']) as archive:
                archived = set(archive.namelist())
                self.assertTrue(build_release.required_files(notes) <= archived)
                self.assertFalse(any(name.startswith(('Gravewright Runner', '.Gravewright-', '.env', 'data/'))
                                     for name in archived if name != '.env.example'))
                for name in ('Install Linux.sh', 'Install macOS.command', 'scripts/posix/install.sh', 'scripts/posix/runner.sh'):
                    mode = archive.getinfo(name).external_attr >> 16
                    self.assertEqual(stat.S_IMODE(mode), 0o755, name)
                self.assertEqual(stat.S_IMODE(archive.getinfo('Install Windows.bat').external_attr >> 16), 0o644)
            for name in ('Install Linux.sh', 'Install macOS.command'):
                with self.subTest(missing=name):
                    (root / name).unlink()
                    with patch.object(build_release, 'git_files', return_value=names):
                        with self.assertRaisesRegex(ValueError, 'Required public files are not selected'):
                            build_release.build(root, check=True)
                    (root / name).write_text('public\n', encoding='utf-8')
