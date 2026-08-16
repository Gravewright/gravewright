from __future__ import annotations

"""Schema-parity guard (Maintenance Plan - Etapa 1).

Proves that ``alembic upgrade head`` on an empty database produces exactly the
schema declared by ``app.persistence.tables.metadata`` (plus the partial
active-scene index). Because migration ``0001`` is now a *static* rendering that
does NOT import the live metadata, this test is what catches drift: change
``tables.py`` without shipping a matching migration and the two schemas diverge
here.

The comparison reflects both databases, so column types are compared like with
like (reflected-vs-reflected) rather than metadata-object-vs-reflected.
"""

from pathlib import Path

from sqlalchemy import create_engine, inspect, text

import app.persistence.database as db_module
from app.persistence import engine as engine_module
from app.persistence.tables import metadata

# Alembic's bookkeeping table is not part of the application schema.
_IGNORED_TABLES = {"alembic_version"}


def _columns(inspector, table: str) -> dict:
    return {
        col["name"]: (str(col["type"]), bool(col["nullable"]))
        for col in inspector.get_columns(table)
    }


def _pk(inspector, table: str) -> list:
    return inspector.get_pk_constraint(table).get("constrained_columns", [])


def _uniques(inspector, table: str) -> set:
    return {tuple(uc["column_names"]) for uc in inspector.get_unique_constraints(table)}


def _indexes(inspector, table: str) -> dict:
    # Keyed by (columns, unique) so index-name differences don't matter but
    # column coverage and uniqueness must match.
    result = {}
    for idx in inspector.get_indexes(table):
        result[(tuple(idx["column_names"]), bool(idx["unique"]))] = idx["name"]
    return result


def _checks(inspector, table: str) -> dict:
    # Name *and* condition: a migration that recreates a table under a different
    # constraint name still drifts from metadata even if the rule is identical.
    return {
        check["name"]: " ".join(str(check["sqltext"]).split())
        for check in inspector.get_check_constraints(table)
    }


def _foreign_keys(inspector, table: str) -> set:
    return {
        (
            tuple(fk["constrained_columns"]),
            fk["referred_table"],
            tuple(fk["referred_columns"]),
        )
        for fk in inspector.get_foreign_keys(table)
    }


def _schema_fingerprint(engine) -> dict:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names()) - _IGNORED_TABLES
    fingerprint = {}
    for table in tables:
        fingerprint[table] = {
            "columns": _columns(inspector, table),
            "pk": _pk(inspector, table),
            "uniques": _uniques(inspector, table),
            "indexes": _indexes(inspector, table),
            "fks": _foreign_keys(inspector, table),
            "checks": _checks(inspector, table),
        }
    return fingerprint


def _build_metadata_reference(path: Path):
    """The schema authority: metadata + the raw partial active-scene index."""
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_scenes_active_campaign "
                "ON scenes (campaign_id) WHERE active = 1"
            )
        )
    return engine


def _run_alembic_upgrade(db_path: Path, monkeypatch, revision: str = "head") -> None:
    from alembic import command
    from alembic.config import Config

    # env.py resolves the URL through effective_database_url(), which honors
    # the monkeypatched DATABASE_PATH when the configured URL is the default.
    monkeypatch.setattr(db_module, "DATABASE_PATH", db_path)
    monkeypatch.setattr(db_module, "_initialized", False)
    engine_module.reset_engine()

    project_root = Path(__file__).resolve().parents[2]
    cfg = Config(str(project_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(project_root / "migrations"))
    command.upgrade(cfg, revision)
    engine_module.reset_engine()


def _run_alembic_upgrade_head(db_path: Path, monkeypatch) -> None:
    _run_alembic_upgrade(db_path, monkeypatch)


def test_alembic_head_matches_metadata_schema(tmp_path, monkeypatch):
    alembic_db = tmp_path / "alembic.sqlite3"
    _run_alembic_upgrade_head(alembic_db, monkeypatch)
    alembic_engine = create_engine(f"sqlite:///{alembic_db.as_posix()}")

    reference_engine = _build_metadata_reference(tmp_path / "reference.sqlite3")

    try:
        alembic_fp = _schema_fingerprint(alembic_engine)
        reference_fp = _schema_fingerprint(reference_engine)

        # Table set parity first, with a readable diff on failure.
        assert set(alembic_fp) == set(reference_fp), (
            "Tables only via alembic: "
            f"{sorted(set(alembic_fp) - set(reference_fp))}; "
            "tables only via metadata: "
            f"{sorted(set(reference_fp) - set(alembic_fp))}"
        )

        # Per-table structural parity: columns, PK, uniques, indexes, FKs.
        for table in sorted(reference_fp):
            assert alembic_fp[table] == reference_fp[table], (
                f"Schema drift on table '{table}':\n"
                f"  alembic:   {alembic_fp[table]}\n"
                f"  metadata:  {reference_fp[table]}"
            )
    finally:
        alembic_engine.dispose()
        reference_engine.dispose()


def test_alembic_creates_a_missing_sqlite_parent_directory(tmp_path, monkeypatch):
    from app.persistence.schema import current_revision, head_revision

    alembic_db = tmp_path / "missing" / "nested" / "gravewright.sqlite3"
    assert not alembic_db.parent.exists()

    _run_alembic_upgrade_head(alembic_db, monkeypatch)

    assert alembic_db.parent.is_dir()
    assert alembic_db.is_file()
    engine = create_engine(f"sqlite:///{alembic_db.as_posix()}")
    try:
        assert current_revision(engine) == head_revision()
    finally:
        engine.dispose()


def test_upgrade_normalizes_the_legacy_0047_revision_before_migrating(tmp_path, monkeypatch):
    from app.persistence.schema import current_revision, head_revision

    alembic_db = tmp_path / "legacy-0047.sqlite3"
    _run_alembic_upgrade(
        alembic_db,
        monkeypatch,
        revision="0047_remove_quest_board_desc",
    )

    engine = create_engine(f"sqlite:///{alembic_db.as_posix()}")
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE alembic_version "
                    "SET version_num = '0047_remove_quest_board_description'"
                )
            )
        assert current_revision(engine) == "0047_remove_quest_board_description"
    finally:
        engine.dispose()

    _run_alembic_upgrade_head(alembic_db, monkeypatch)

    upgraded = create_engine(f"sqlite:///{alembic_db.as_posix()}")
    try:
        assert current_revision(upgraded) == head_revision()
    finally:
        upgraded.dispose()


def test_revision_normalization_leaves_newer_markers_unchanged(tmp_path, monkeypatch):
    from app.persistence.schema import current_revision

    revisions = ("0048_remove_quest_board_filters", "0049_campaign_player_onboarding")
    for revision in revisions:
        alembic_db = tmp_path / f"{revision}.sqlite3"
        _run_alembic_upgrade(alembic_db, monkeypatch, revision=revision)
        _run_alembic_upgrade(alembic_db, monkeypatch, revision=revision)

        engine = create_engine(f"sqlite:///{alembic_db.as_posix()}")
        try:
            assert current_revision(engine) == revision
        finally:
            engine.dispose()


def test_alembic_head_creates_partial_active_scene_index(tmp_path, monkeypatch):
    alembic_db = tmp_path / "alembic.sqlite3"
    _run_alembic_upgrade_head(alembic_db, monkeypatch)
    engine = create_engine(f"sqlite:///{alembic_db.as_posix()}")
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='index' AND name='idx_scenes_active_campaign'"
                )
            ).first()
        assert row is not None, "partial active-scene index missing after upgrade head"
    finally:
        engine.dispose()


def test_initial_migration_does_not_import_metadata():
    """0001 must be self-contained static DDL, not derived from live metadata."""
    source = (
        Path(__file__).resolve().parents[2] / "migrations" / "versions" / "0001_initial_schema.py"
    ).read_text(encoding="utf-8")
    assert "import metadata" not in source
    assert "metadata.create_all" not in source
    assert "metadata.drop_all" not in source
