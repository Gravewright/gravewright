from __future__ import annotations

"""Legacy-upgrade guard (Maintenance Plan - Etapa 1).

Simulates a database that predates later additive migrations (missing
``scenes.board_version`` and the whole ``card_events`` table), stamps it at the
baseline revision, runs ``alembic upgrade head``, and asserts the guarded
migrations reconcile the schema back to parity with the current metadata. A
small write smoke confirms the upgraded database is usable.
"""

from pathlib import Path

from sqlalchemy import create_engine, inspect, text

import app.persistence.database as db_module
from app.persistence import engine as engine_module
from app.persistence.tables import metadata

from tests.unit.test_schema_alembic_parity import _schema_fingerprint


def _alembic_config():
    from alembic.config import Config

    project_root = Path(__file__).resolve().parents[2]
    cfg = Config(str(project_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(project_root / "migrations"))
    return cfg


def _build_legacy_database(path: Path) -> None:
    """Full current schema, then rolled back to a pre-0002/pre-0009 shape."""
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE scenes DROP COLUMN board_version"))
        conn.execute(text("DROP TABLE card_events"))
    engine.dispose()


def test_legacy_database_upgrades_to_head(tmp_path, monkeypatch):
    from alembic import command

    legacy_db = tmp_path / "legacy.sqlite3"
    _build_legacy_database(legacy_db)

    # Sanity: the legacy shape really is missing the later objects.
    legacy_engine = create_engine(f"sqlite:///{legacy_db.as_posix()}")
    inspector = inspect(legacy_engine)
    assert "board_version" not in {c["name"] for c in inspector.get_columns("scenes")}
    assert "card_events" not in inspector.get_table_names()
    legacy_engine.dispose()

    monkeypatch.setattr(db_module, "DATABASE_PATH", legacy_db)
    monkeypatch.setattr(db_module, "_initialized", False)
    engine_module.reset_engine()

    cfg = _alembic_config()
    command.stamp(cfg, "0001_initial_schema")
    command.upgrade(cfg, "head")
    engine_module.reset_engine()

    upgraded = create_engine(f"sqlite:///{legacy_db.as_posix()}")
    reference = create_engine(f"sqlite:///{(tmp_path / 'reference.sqlite3').as_posix()}")
    metadata.create_all(reference)
    try:
        inspector = inspect(upgraded)
        # The guarded migrations reconciled the missing objects.
        assert "board_version" in {c["name"] for c in inspector.get_columns("scenes")}
        assert "card_events" in inspector.get_table_names()

        # Full structural parity with current metadata after the upgrade.
        up_fp = _schema_fingerprint(upgraded)
        ref_fp = _schema_fingerprint(reference)
        for table in sorted(ref_fp):
            assert up_fp[table] == ref_fp[table], f"legacy upgrade left drift on '{table}'"

        # Write smoke: the upgraded database accepts inserts and reads them back.
        with upgraded.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (id, name, email, password_hash, system_role, created_at, updated_at) "
                    "VALUES ('u1', 'Legacy', 'legacy@test.com', 'x', 'user', 0, 0)"
                )
            )
        with upgraded.connect() as conn:
            row = conn.execute(text("SELECT name FROM users WHERE id='u1'")).first()
        assert row is not None and row[0] == "Legacy"
    finally:
        upgraded.dispose()
        reference.dispose()
