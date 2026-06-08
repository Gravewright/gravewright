from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect

import app.persistence.database as db_module
from app.persistence import engine as engine_module
from app.persistence.tables import metadata


def test_metadata_schema_builds_all_declared_tables(tmp_path, monkeypatch):
    path = tmp_path / "metadata.sqlite3"
    monkeypatch.setattr(db_module, "DATABASE_PATH", path)
    monkeypatch.setattr(db_module, "_initialized", False)
    engine_module.reset_engine()
    try:
        db_module.initialize_database()
        inspector = inspect(engine_module.get_engine())
        assert set(inspector.get_table_names()) == set(metadata.tables)
    finally:
        engine_module.reset_engine()


def test_legacy_sqlite_schema_package_removed():
    import app.persistence as persistence

    assert not (persistence.__path__[0] and Path(persistence.__path__[0], "schema").exists())
