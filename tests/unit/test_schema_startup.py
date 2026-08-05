from __future__ import annotations

"""Startup schema policy (Maintenance Plan - Etapa 2).

Covers the split between the dev/test metadata bootstrap and the production
Alembic-validated path, and guards that the startup engine no longer creates or
alters the schema ad hoc.
"""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

import app.persistence.database as db_module
from app.persistence import engine as engine_module
from app.persistence import schema as schema_module
from app.persistence.schema import (
    SchemaOutdatedError,
    bootstrap_schema_from_metadata,
    ensure_schema_ready,
    head_revision,
    schema_status,
)
from app.persistence.tables import metadata


def _sqlite_engine(path: Path):
    return create_engine(f"sqlite:///{path.as_posix()}")


def test_bootstrap_from_metadata_creates_full_schema(tmp_path):
    engine = _sqlite_engine(tmp_path / "boot.sqlite3")
    try:
        bootstrap_schema_from_metadata(engine)
        inspector = inspect(engine)
        assert set(inspector.get_table_names()) >= set(metadata.tables)
        # Partial active-scene index is created by the bootstrap too.
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='index' "
                    "AND name='idx_scenes_active_campaign'"
                )
            ).first()
        assert row is not None
    finally:
        engine.dispose()


def test_ensure_schema_ready_raises_when_uninitialized(tmp_path):
    engine = _sqlite_engine(tmp_path / "empty.sqlite3")
    try:
        with pytest.raises(SchemaOutdatedError) as excinfo:
            ensure_schema_ready(engine, auto_migrate=False)
        message = str(excinfo.value)
        # Actionable: names the expected head and the remediation command.
        assert head_revision() in message
        assert "alembic upgrade head" in message
    finally:
        engine.dispose()


def test_ensure_schema_ready_auto_migrates_new_database(tmp_path, monkeypatch):
    db_path = tmp_path / "auto.sqlite3"
    # env.py resolves the URL via effective_database_url() -> DATABASE_PATH.
    monkeypatch.setattr(db_module, "DATABASE_PATH", db_path)
    monkeypatch.setattr(db_module, "_initialized", False)
    engine_module.reset_engine()

    engine = _sqlite_engine(db_path)
    try:
        ensure_schema_ready(engine, auto_migrate=True)
        status = schema_status(engine)
        assert status["up_to_date"] is True
        assert status["current"] == head_revision()
        # Created through the official migration path (alembic_version present).
        assert "alembic_version" in inspect(engine).get_table_names()
    finally:
        engine.dispose()
        engine_module.reset_engine()


def test_ensure_schema_ready_noop_when_at_head(tmp_path, monkeypatch):
    db_path = tmp_path / "head.sqlite3"
    monkeypatch.setattr(db_module, "DATABASE_PATH", db_path)
    monkeypatch.setattr(db_module, "_initialized", False)
    engine_module.reset_engine()

    from app.persistence.schema import upgrade_to_head

    upgrade_to_head()
    engine = _sqlite_engine(db_path)
    try:
        # Already at head: must not raise and must not change anything.
        ensure_schema_ready(engine, auto_migrate=False)
        assert schema_status(engine)["up_to_date"] is True
    finally:
        engine.dispose()
        engine_module.reset_engine()


def test_initialize_database_production_requires_head(tmp_path, monkeypatch):
    """Production dispatch validates head instead of running create_all."""
    db_path = tmp_path / "prod.sqlite3"
    monkeypatch.setattr(db_module, "DATABASE_PATH", db_path)
    monkeypatch.setattr(db_module, "_initialized", False)
    monkeypatch.setattr(db_module, "_use_metadata_bootstrap", lambda: False)
    # Real test config has auto_migrate=False (frozen), so the production
    # dispatch must refuse to start against an empty database.
    assert db_module.config.auto_migrate is False
    engine_module.reset_engine()
    try:
        with pytest.raises(SchemaOutdatedError):
            db_module.initialize_database()
    finally:
        engine_module.reset_engine()


def test_startup_engine_has_no_ad_hoc_schema_creation():
    """engine.py must not create_all / ALTER / build production indexes."""
    source = Path(engine_module.__file__).read_text(encoding="utf-8")
    assert "create_all" not in source
    assert "ALTER TABLE" not in source
    assert "_ensure_incremental_columns" not in source
    assert "CREATE UNIQUE INDEX" not in source
    assert "CREATE INDEX" not in source


def test_schema_module_owns_partial_index_only_for_bootstrap():
    """The partial index lives in the migration + the dev/test bootstrap, not
    as a production side effect of engine startup."""
    source = Path(schema_module.__file__).read_text(encoding="utf-8")
    assert "idx_scenes_active_campaign" in source
