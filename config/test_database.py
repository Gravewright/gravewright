import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from django.db import connection
from django.test import SimpleTestCase, TransactionTestCase

from config.engine import configure
from config.testing import remove_stale_sidecars


class StaleSidecarTests(SimpleTestCase):
    def files(self, root, *names):
        for name in names:
            (root / name).write_bytes(b'x')

    def test_sidecars_of_a_missing_or_replaced_database_are_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.files(root, 'test.sqlite3-wal', 'test.sqlite3-shm')
            self.assertEqual(len(remove_stale_sidecars(root / 'test.sqlite3', replacing=False)), 2)
            self.files(root, 'test.sqlite3', 'test.sqlite3-wal', 'test.sqlite3-shm')
            self.assertEqual(len(remove_stale_sidecars(root / 'test.sqlite3', replacing=True)), 2)
            self.assertTrue((root / 'test.sqlite3').exists(), 'Django replaces the database itself')

    def test_a_kept_database_keeps_its_sidecars(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.files(root, 'test.sqlite3', 'test.sqlite3-wal', 'other.sqlite3-wal')
            self.assertEqual(remove_stale_sidecars(root / 'test.sqlite3', replacing=False), [])
            self.assertTrue((root / 'test.sqlite3-wal').exists())
            remove_stale_sidecars(root / 'test.sqlite3', replacing=True)
            self.assertTrue((root / 'other.sqlite3-wal').exists(), 'other databases are untouched')


class JournalModeSettingTests(SimpleTestCase):
    def test_wal_is_the_default_and_delete_remains_available(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('DATABASE_JOURNAL_MODE', None)
            self.assertEqual(configure()['DATABASE_JOURNAL_MODE'], 'wal')
        with patch.dict(os.environ, {'DATABASE_JOURNAL_MODE': ' Delete '}):
            self.assertEqual(configure()['DATABASE_JOURNAL_MODE'], 'delete')

    def test_unknown_journal_modes_are_refused(self):
        for value in ('memory', 'off', 'truncate', 'wal2'):
            with self.subTest(value=value), patch.dict(os.environ, {'DATABASE_JOURNAL_MODE': value}):
                with self.assertRaisesMessage(ValueError, 'DATABASE_JOURNAL_MODE'):
                    configure()


class WriteAheadLogTests(TransactionTestCase):
    """The file-backed test database runs with the configured WAL journal."""

    def test_connections_use_wal(self):
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA journal_mode')
            self.assertEqual(cursor.fetchone()[0], 'wal')

    def test_a_writer_commits_while_a_reader_holds_a_snapshot(self):
        connection.ensure_connection()
        path = connection.settings_dict['NAME']
        with closing(sqlite3.connect(path, timeout=.5, isolation_level=None)) as setup:
            setup.execute('CREATE TABLE IF NOT EXISTS wal_probe (value INTEGER)')
            setup.execute('DELETE FROM wal_probe')
        try:
            with closing(sqlite3.connect(path, timeout=.5, isolation_level=None)) as reader, \
                    closing(sqlite3.connect(path, timeout=.5, isolation_level=None)) as writer:
                reader.execute('BEGIN')
                self.assertEqual(reader.execute('SELECT COUNT(*) FROM wal_probe').fetchone()[0], 0)
                # With a rollback journal this commit waits for the reader and times out.
                writer.execute('BEGIN IMMEDIATE')
                writer.execute('INSERT INTO wal_probe VALUES (1)')
                writer.execute('COMMIT')
                # The reader keeps its snapshot until its transaction ends.
                self.assertEqual(reader.execute('SELECT COUNT(*) FROM wal_probe').fetchone()[0], 0)
                reader.execute('COMMIT')
                self.assertEqual(reader.execute('SELECT COUNT(*) FROM wal_probe').fetchone()[0], 1)
        finally:
            with closing(sqlite3.connect(path, timeout=5, isolation_level=None)) as cleanup:
                cleanup.execute('DROP TABLE IF EXISTS wal_probe')
