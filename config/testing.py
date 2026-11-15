"""Django test runner for the file-backed SQLite test database."""

from pathlib import Path

from django.db import connections
from django.test.runner import DiscoverRunner

SIDECARS = ('-wal', '-shm')


def remove_stale_sidecars(database, replacing):
    """Remove WAL files that would otherwise attach to a new database of the same name.

    SQLite replays a ``-wal`` file into whatever database file has that name. Django
    deletes only the database file when it replaces or destroys a test database, so
    an interrupted run can leave its WAL behind. Sidecars are removed when their
    database is missing or about to be replaced; a kept database keeps them.
    """
    database = Path(database)
    if database.exists() and not replacing:
        return []
    removed = []
    for suffix in SIDECARS:
        sidecar = Path(str(database) + suffix)
        if sidecar.is_file():
            sidecar.unlink()
            removed.append(sidecar)
    return removed


def test_database_files():
    for alias in connections:
        settings = connections[alias].settings_dict
        name = settings.get('TEST', {}).get('NAME')
        if settings['ENGINE'].endswith('sqlite3') and name and str(name) != ':memory:':
            yield name


class TestRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        if not self.keepdb:
            for name in test_database_files():
                # Without --noinput Django asks before replacing an existing database.
                remove_stale_sidecars(name, replacing=not self.interactive)
        return super().setup_databases(**kwargs)

    def teardown_databases(self, old_config, **kwargs):
        super().teardown_databases(old_config, **kwargs)
        if not self.keepdb:
            for name in test_database_files():
                try:
                    # Connections still open on worker threads keep the log after
                    # Django deletes the database file.
                    remove_stale_sidecars(name, replacing=False)
                except OSError:
                    pass  # Still open (Windows): the next run removes it before creating.
