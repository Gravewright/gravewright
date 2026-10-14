"""Retained rollback copies stay in local updater storage and restore safely."""

from contextlib import closing
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
from unittest import TestCase
from unittest.mock import patch

from scripts.project_files import copy_files, source_files, storage_path
from scripts.rollback_update import rollback
from scripts.update_supervisor import Supervisor, read, retained_backup_parent, write


class PortableBackupsTests(TestCase):
    def setUp(self):
        temporary_root = Path(__file__).resolve().parents[1] / 'data'
        temporary_root.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='backup-', dir=temporary_root)
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name).resolve()
        self.origin = self.work / 'Application'
        self.data = self.origin / 'data'
        self.state = self.data / 'updates'
        self.media = self.data / 'media'
        self.media.mkdir(parents=True)
        self.database = self.data / 'database.sqlite3'
        (self.origin / 'pyproject.toml').write_text('[project]\nversion = "0.2.3"\n', encoding='utf-8')
        (self.origin / 'app.py').write_text('previous code\n', encoding='utf-8')
        (self.origin / '.env').write_text('LOCAL_SETTING=preserve\n', encoding='utf-8')
        (self.media / 'fixture.txt').write_text('previous media', encoding='utf-8')
        self.set_database('previous data', create=True)
        self.enterContext(patch.dict(os.environ, {
            'GRAVEWRIGHT_RUNNER_DATA': str(self.data),
            'GRAVEWRIGHT_MODULES_ROOT': 'data/media/modules',
            'DJANGO_SETTINGS_MODULE': 'config.settings',
        }, clear=True))
        self.supervisor = Supervisor(self.origin, self.state, self.database, self.media, '127.0.0.1', 3000)

    def set_database(self, value, *, create=False):
        with closing(sqlite3.connect(self.database)) as connection, connection:
            if create:
                connection.execute('create table fixture(value text)')
                connection.execute('insert into fixture values (?)', (value,))
            else:
                connection.execute('update fixture set value = ?', (value,))

    def assert_previous_installation(self):
        self.assertEqual((self.origin / 'app.py').read_text(encoding='utf-8'), 'previous code\n')
        self.assertFalse((self.origin / 'new.py').exists())
        self.assertEqual((self.origin / '.env').read_text(encoding='utf-8'), 'LOCAL_SETTING=preserve\n')
        self.assertEqual((self.media / 'fixture.txt').read_text(encoding='utf-8'), 'previous media')
        with closing(sqlite3.connect(self.database)) as connection:
            self.assertEqual(connection.execute('select value from fixture').fetchone()[0], 'previous data')

    def complete_backup(self, old):
        backup = self.state / 'backups' / 'fixture'
        self.supervisor.backup(backup)
        files = source_files(self.origin, self.supervisor.protected)
        copy_files(self.origin, old, files)
        metadata = old / '.gravewright-rollback'
        shutil.copytree(storage_path(backup), storage_path(metadata))
        write(metadata / 'project.json', {
            'previous': str(self.origin), 'previous_python': sys.executable,
            'backup': 'fixture', 'restore': True,
            'project_files': files, 'incoming_files': files,
        })
        write(metadata / 'installation.json', {
            'origin': str(self.origin), 'state': str(self.state),
            'database': str(self.database), 'media': str(self.media),
            'extra_paths': {name: str(path) for name, path in self.supervisor.extra_paths.items()},
            'protected': [str(path) for path in self.supervisor.protected],
        })
        return metadata

    def change_installation(self):
        (self.origin / 'app.py').write_text('new code', encoding='utf-8')
        (self.origin / 'new.py').write_text('added later', encoding='utf-8')
        (self.media / 'fixture.txt').write_text('new media', encoding='utf-8')
        self.set_database('new data')

    def test_new_retained_copies_are_local_and_collisions_preserve_previous_backups(self):
        first = self.supervisor.create_retained_copy('a' * 32)
        (first / 'keep.txt').write_text('first', encoding='utf-8')
        second = self.supervisor.create_retained_copy('b' * 32)
        (second / 'keep.txt').write_text('second', encoding='utf-8')
        third = self.supervisor.create_retained_copy('b' * 32)
        self.assertEqual(first, self.state / 'retained/Application.old')
        self.assertEqual(second, self.state / ('retained/Application.' + 'b' * 32 + '.old'))
        self.assertNotIn(third, (first, second))
        self.assertTrue(third.is_relative_to(self.origin))
        self.assertEqual((first / 'keep.txt').read_text(), 'first')
        self.assertEqual((second / 'keep.txt').read_text(), 'second')
        self.assertEqual(list(self.origin.parent.glob('*.old')), [])
        self.assertEqual(source_files(self.origin, self.supervisor.protected), ['app.py', 'pyproject.toml'])

    def test_invalid_identifier_is_rejected_before_creating_any_backup(self):
        with self.assertRaisesRegex(ValueError, 'identifier'):
            self.supervisor.create_retained_copy('../outside')
        self.assertFalse((self.state / 'retained').exists())

    def test_path_guard_accepts_local_copy_and_requires_explicit_legacy_support(self):
        local = self.state / 'retained/Application.old'
        legacy = self.origin.with_name('Application.old')
        self.assertEqual(retained_backup_parent(self.origin, self.state, local), local.parent)
        with self.assertRaisesRegex(ValueError, 'retained backup path'):
            retained_backup_parent(self.origin, self.state, legacy)
        self.assertEqual(retained_backup_parent(self.origin, self.state, legacy, allow_legacy=True), legacy.parent)
        for invalid in (self.origin, self.origin.parent, self.origin / 'impostor.old',
                        self.state / 'retained', self.state / 'retained/not-a-backup',
                        self.work / 'elsewhere/Application.old'):
            with self.subTest(path=invalid), self.assertRaisesRegex(ValueError, 'retained backup path'):
                retained_backup_parent(self.origin, self.state, invalid, allow_legacy=True)

    def test_retained_directory_cannot_be_redirected_outside_updater_storage(self):
        outside = self.work / 'outside'
        outside.mkdir()
        try:
            (self.state / 'retained').symlink_to(outside, target_is_directory=True)
        except OSError as error:
            self.skipTest(f'Symlink creation unavailable: {error}')
        with self.assertRaisesRegex(ValueError, 'retained backup path'):
            self.supervisor.create_retained_copy('a' * 32)
        self.assertEqual(list(outside.iterdir()), [])

    def test_recovery_rejects_an_invalid_old_path_before_restoring_code_or_storage(self):
        write(self.state / 'transaction.json', {
            'previous': str(self.origin), 'backup': 'fixture', 'restore': True,
            'old_copy': str(self.work / 'elsewhere/Application.old'),
        })
        with patch.object(self.supervisor, 'restore') as restore, \
                patch('scripts.update_supervisor.replace_files') as replace:
            with self.assertRaisesRegex(ValueError, 'retained backup path'):
                self.supervisor.recover()
            restore.assert_not_called()
            replace.assert_not_called()
        self.assert_previous_installation()
        self.assertTrue((self.state / 'transaction.json').exists())

    def test_recovery_removes_only_the_incomplete_local_or_recorded_legacy_copy(self):
        for old in (self.state / 'retained/Application.old', self.origin.with_name('Application.old')):
            with self.subTest(path=old):
                old.mkdir(parents=True)
                (old / 'partial.txt').write_text('incomplete', encoding='utf-8')
                write(self.state / 'transaction.json', {
                    'previous': str(self.origin), 'previous_python': sys.executable,
                    'backup': 'fixture', 'restore': False, 'old_copy': str(old),
                })
                self.supervisor.recover()
                self.assertFalse(old.exists())
                self.assert_previous_installation()

    def test_explicit_rollback_restores_local_code_and_data_without_recursive_copy(self):
        old = self.supervisor.create_retained_copy('a' * 32)
        metadata = self.complete_backup(old)
        self.change_installation()
        self.assertEqual(rollback(old), self.origin)
        self.assert_previous_installation()
        self.assertTrue((metadata / 'database.sqlite3').exists())
        self.assertEqual(read(self.state / 'active.json')['path'], str(self.origin))

    def test_explicit_rollback_still_reads_a_legacy_sibling_backup(self):
        old = self.origin.with_name('Application.old')
        old.mkdir()
        self.complete_backup(old)
        self.change_installation()
        self.assertEqual(rollback(old), self.origin)
        self.assert_previous_installation()
        self.assertTrue(old.exists())

    def test_apply_retains_matching_backup_inside_native_project_data(self):
        candidate = self.work / 'candidate'
        candidate.mkdir()
        (candidate / 'pyproject.toml').write_text('[project]\nversion = "0.2.4"\n', encoding='utf-8')
        (candidate / 'app.py').write_text('new code', encoding='utf-8')
        (candidate / 'new.py').write_text('added later', encoding='utf-8')
        with patch('scripts.update_supervisor.download'), \
                patch('scripts.update_supervisor.extract', return_value=candidate), \
                patch('scripts.update_supervisor.shutil.which', return_value='uv'), \
                patch.object(self.supervisor, 'command'), \
                patch.object(self.supervisor, 'stop'), patch.object(self.supervisor, 'start'), \
                patch.object(self.supervisor, 'ready'):
            self.supervisor.apply({'version': '0.2.4', 'artifact': {'size': 0}})
        progress = read(self.state / 'progress.json')
        self.assertEqual(progress['stage'], 'complete')
        old = Path(progress['backup'])
        self.assertEqual(old.parent, self.state / 'retained')
        self.assertTrue(old.is_relative_to(self.origin))
        self.assertEqual((old / 'app.py').read_text(), 'previous code\n')
        self.assertEqual(list(self.origin.parent.glob('*.old')), [])
        rollback(old)
        self.assert_previous_installation()
