from __future__ import annotations

from dataclasses import replace

import app.persistence.database as db_module


def _config(monkeypatch, **changes):
    monkeypatch.setattr(db_module, "config", replace(db_module.config, **changes))


def test_memory_sqlite_allows_metadata_without_flag(monkeypatch):
    _config(monkeypatch, database_url="sqlite:///:memory:", allow_metadata_bootstrap=False)
    assert db_module._use_metadata_bootstrap() is True


def test_persistent_sqlite_refuses_metadata_even_in_test(monkeypatch, tmp_path):
    persistent = db_module.PROJECT_ROOT / "storage" / "persistent-test.sqlite3"
    _config(
        monkeypatch,
        database_url=f"sqlite:///{persistent.as_posix()}",
        app_env="test",
        allow_metadata_bootstrap=True,
    )
    monkeypatch.setenv("GRAVEWRIGHT_TEST_TEMP_ROOT", str(tmp_path))
    assert db_module._use_metadata_bootstrap() is False


def test_temporary_sqlite_requires_explicit_opt_in(monkeypatch, tmp_path):
    database = tmp_path / "disposable.sqlite3"
    monkeypatch.setenv("GRAVEWRIGHT_TEST_TEMP_ROOT", str(tmp_path))
    _config(
        monkeypatch,
        database_url=f"sqlite:///{database.as_posix()}",
        app_env="test",
        allow_metadata_bootstrap=False,
    )
    assert db_module._use_metadata_bootstrap() is False
    _config(monkeypatch, allow_metadata_bootstrap=True)
    assert db_module._use_metadata_bootstrap() is True


def test_postgresql_never_allows_metadata_bootstrap(monkeypatch):
    _config(
        monkeypatch,
        database_url="postgresql+psycopg://user:password@localhost/test",
        app_env="test",
        allow_metadata_bootstrap=True,
    )
    assert db_module._use_metadata_bootstrap() is False


def test_development_file_database_uses_alembic(monkeypatch, tmp_path):
    database = tmp_path / "development.sqlite3"
    monkeypatch.setenv("GRAVEWRIGHT_TEST_TEMP_ROOT", str(tmp_path))
    _config(
        monkeypatch,
        database_url=f"sqlite:///{database.as_posix()}",
        app_env="development",
        allow_metadata_bootstrap=True,
    )
    assert db_module._use_metadata_bootstrap() is False
