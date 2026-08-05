from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

import app.persistence.database as db_module
from app.persistence import engine as engine_module
from app.persistence.schema import adopt_legacy_database, bootstrap_schema_from_metadata


def _legacy_database(path):
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    bootstrap_schema_from_metadata(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users "
                "(id, name, email, password_hash, system_role, created_at, updated_at) "
                "VALUES ('legacy-user', 'Legacy', 'legacy@example.test', 'x', 'user', 0, 0)"
            )
        )
    engine.dispose()


def test_adopt_exact_legacy_schema_preserves_data(tmp_path, monkeypatch):
    path = tmp_path / "legacy.sqlite3"
    _legacy_database(path)
    monkeypatch.setattr(db_module, "DATABASE_PATH", path)
    monkeypatch.setattr(db_module, "_initialized", False)
    engine_module.reset_engine()
    engine = engine_module.get_engine()
    try:
        result = adopt_legacy_database(engine)
        assert result["revision"]
        assert result["fingerprint"]
        assert result["backup"]
        assert "alembic_version" in inspect(engine).get_table_names()
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT name FROM users WHERE id='legacy-user'")
                ).scalar_one()
                == "Legacy"
            )
    finally:
        engine_module.reset_engine()


def test_adopt_refuses_divergent_schema_without_stamping(tmp_path, monkeypatch):
    path = tmp_path / "drift.sqlite3"
    _legacy_database(path)
    raw = create_engine(f"sqlite:///{path.as_posix()}")
    with raw.begin() as connection:
        connection.execute(text("CREATE TABLE unexpected_table (id TEXT PRIMARY KEY)"))
    raw.dispose()
    monkeypatch.setattr(db_module, "DATABASE_PATH", path)
    monkeypatch.setattr(db_module, "_initialized", False)
    engine_module.reset_engine()
    engine = engine_module.get_engine()
    try:
        import pytest

        with pytest.raises(RuntimeError, match="no stamp was made"):
            adopt_legacy_database(engine)
        assert "alembic_version" not in inspect(engine).get_table_names()
    finally:
        engine_module.reset_engine()
