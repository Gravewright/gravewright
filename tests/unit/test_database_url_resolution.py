from __future__ import annotations

from pathlib import Path

import app.persistence.database as db_module
from app.helpers.env import PROJECT_ROOT
from app.persistence import engine as engine_module


def _set_database_url(value: str) -> str:
    original = db_module.config.database_url
    object.__setattr__(db_module.config, "database_url", value)
    engine_module.reset_engine()
    return original


def _restore_database_url(value: str) -> None:
    object.__setattr__(db_module.config, "database_url", value)
    engine_module.reset_engine()


def test_default_sqlite_url_keeps_database_path_test_hook(tmp_path, monkeypatch):
    original = _set_database_url(f"sqlite:///{db_module.DEFAULT_DATABASE_PATH.as_posix()}")
    try:
        redirected = tmp_path / "isolated.sqlite3"
        monkeypatch.setattr(db_module, "DATABASE_PATH", redirected)

        assert db_module.effective_sqlite_path() == redirected
        assert engine_module._resolve_url() == f"sqlite:///{redirected.as_posix()}"
    finally:
        _restore_database_url(original)


def test_custom_absolute_sqlite_database_url_wins_over_database_path(tmp_path, monkeypatch):
    custom = tmp_path / "custom.sqlite3"
    original = _set_database_url(f"sqlite:///{custom.as_posix()}")
    try:
        monkeypatch.setattr(db_module, "DATABASE_PATH", tmp_path / "ignored.sqlite3")

        assert db_module.effective_sqlite_path() == custom
        assert engine_module._resolve_url() == f"sqlite:///{custom.as_posix()}"
    finally:
        _restore_database_url(original)


def test_relative_sqlite_database_url_is_project_relative(tmp_path, monkeypatch):
    original = _set_database_url("sqlite:///storage/custom.sqlite3")
    try:
        monkeypatch.setattr(db_module, "DATABASE_PATH", tmp_path / "ignored.sqlite3")

        expected = (PROJECT_ROOT / "storage" / "custom.sqlite3").resolve()
        assert db_module.effective_sqlite_path() == expected
        assert engine_module._resolve_url() == f"sqlite:///{expected.as_posix()}"
    finally:
        _restore_database_url(original)
