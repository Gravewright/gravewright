"""Schema lifecycle: Alembic status, upgrades, and the dev/test bootstrap.

This module keeps the three concerns the maintenance plan (Etapa 2) asked to
separate cleanly apart:

- **status / head detection** — read the applied revision and the expected head;
- **official upgrade path** — ``alembic upgrade head`` (creates a new database or
  upgrades an existing one; the *only* supported way to evolve production data);
- **dev/test bootstrap** — ``metadata.create_all`` plus the partial active-scene
  index, for fast, throwaway local and test databases only.

Production startup validates the database is at head and fails with an
actionable message when it is not, unless auto-migrate is explicitly enabled.
``metadata.create_all`` is never the production upgrade mechanism.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
import uuid
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from app.helpers.env import PROJECT_ROOT


class SchemaOutdatedError(RuntimeError):
    """Raised when the database schema is behind the expected Alembic head."""


_PARTIAL_ACTIVE_SCENE_INDEX = (
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_scenes_active_campaign "
    "ON scenes (campaign_id) WHERE active = 1"
)


def _alembic_config():
    from alembic.config import Config

    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    return cfg


def head_revision() -> str | None:
    """The revision id at the tip of the migration history (expected head)."""
    from alembic.script import ScriptDirectory

    return ScriptDirectory.from_config(_alembic_config()).get_current_head()


def current_revision(engine: Engine) -> str | None:
    """The revision id the database currently reports (``None`` if unmanaged)."""
    from alembic.runtime.migration import MigrationContext

    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def schema_status(engine: Engine) -> dict:
    """Structured migration status for diagnostics and startup checks."""
    current = current_revision(engine)
    head = head_revision()
    return {
        "backend": engine.dialect.name,
        "current": current,
        "head": head,
        "up_to_date": current is not None and current == head,
    }


def upgrade_to_head() -> None:
    """Run ``alembic upgrade head`` against the configured database.

    This is the official path for creating a new database and for upgrading an
    existing one. Safe to run repeatedly (a database already at head is a no-op).
    """
    from alembic import command

    command.upgrade(_alembic_config(), "head")


def create_partial_active_scene_index(engine: Engine) -> None:
    """Create the partial unique index that metadata cannot express portably."""
    if engine.dialect.name in {"sqlite", "postgresql"}:
        with engine.begin() as connection:
            connection.execute(text(_PARTIAL_ACTIVE_SCENE_INDEX))


def bootstrap_schema_from_metadata(engine: Engine) -> None:
    """DEV/TEST ONLY: create the schema directly from metadata.

    Fast bootstrap for throwaway local and test databases. It does NOT alter
    existing tables and is NOT the supported production upgrade mechanism — use
    :func:`upgrade_to_head` for anything with data you care about.
    """
    from app.persistence.tables import metadata

    metadata.create_all(engine, checkfirst=True)
    create_partial_active_scene_index(engine)


def _schema_fingerprint(engine: Engine) -> dict:
    """Return the structural schema identity used by the explicit adopter."""
    inspector = inspect(engine)
    result = {}
    for table in sorted(set(inspector.get_table_names()) - {"alembic_version"}):
        result[table] = {
            "columns": {
                col["name"]: (str(col["type"]), bool(col["nullable"]))
                for col in inspector.get_columns(table)
            },
            "pk": inspector.get_pk_constraint(table).get("constrained_columns", []),
            "uniques": sorted(
                tuple(item["column_names"]) for item in inspector.get_unique_constraints(table)
            ),
            "indexes": sorted(
                (tuple(item["column_names"]), bool(item["unique"]))
                for item in inspector.get_indexes(table)
            ),
            "foreign_keys": sorted(
                (
                    tuple(item["constrained_columns"]),
                    item["referred_table"],
                    tuple(item["referred_columns"]),
                )
                for item in inspector.get_foreign_keys(table)
            ),
            "checks": {
                str(item["name"] or ""): " ".join(str(item["sqltext"]).split())
                for item in inspector.get_check_constraints(table)
            },
        }
    return result


def _fingerprint_digest(fingerprint: dict) -> str:
    encoded = json.dumps(fingerprint, sort_keys=True, separators=(",", ":"), default=list)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def adopt_legacy_database(engine: Engine) -> dict:
    """Safely adopt an unversioned SQLite DB that exactly matches metadata.

    Adoption is intentionally explicit. A safety copy is made first, every
    reflected structural category is compared with a same-dialect reference,
    and Alembic is stamped only after exact equivalence is established.
    """
    if current_revision(engine) is not None:
        raise RuntimeError("Database is already managed by Alembic; use 'grave db upgrade'.")
    if engine.dialect.name != "sqlite":
        raise RuntimeError(
            "Automatic adoption currently requires SQLite so Gravewright can create "
            "a verified local backup. Back up this database with your backend tools first."
        )

    from app.persistence.database import effective_sqlite_path

    database_path = effective_sqlite_path()
    if database_path == ":memory:":
        raise RuntimeError("In-memory databases are disposable and cannot be adopted.")
    source = Path(database_path)
    if not source.is_file():
        raise RuntimeError(f"Database file not found: {source}")

    backup = source.with_name(f"{source.name}.pre-adopt-{int(time.time())}.bak")
    shutil.copy2(source, backup)

    reference_path = source.with_name(f".{source.name}.adopt-reference-{uuid.uuid4().hex}.tmp")
    reference = create_engine(f"sqlite:///{reference_path.as_posix()}")
    try:
        bootstrap_schema_from_metadata(reference)
        actual = _schema_fingerprint(engine)
        expected = _schema_fingerprint(reference)
    finally:
        reference.dispose()
        reference_path.unlink(missing_ok=True)

    digest = _fingerprint_digest(actual)
    if actual != expected:
        from app.observability.audit import emit_audit

        emit_audit(
            "schema.adoption",
            result="refused",
            level="error",
            backend="sqlite",
            fingerprint=digest,
        )
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        changed = sorted(
            table for table in set(actual) & set(expected) if actual[table] != expected[table]
        )
        raise RuntimeError(
            "Schema does not exactly match a known Gravewright revision; no stamp was made. "
            f"Missing tables={missing}, extra tables={extra}, changed tables={changed}. "
            f"Safety backup: {backup}"
        )

    from alembic import command

    revision = head_revision()
    command.stamp(_alembic_config(), revision)
    upgrade_to_head()
    status = schema_status(engine)
    if not status["up_to_date"] or _schema_fingerprint(engine) != expected:
        raise RuntimeError(f"Post-adoption schema audit failed. Restore backup: {backup}")

    from app.observability.audit import emit_audit

    emit_audit(
        "schema.adoption",
        result="success",
        backend="sqlite",
        revision=revision,
        fingerprint=digest,
    )
    return {"revision": revision, "fingerprint": digest, "backup": str(backup)}


def ensure_schema_ready(engine: Engine, *, auto_migrate: bool) -> None:
    """Validate the database is at head; upgrade or fail per ``auto_migrate``.

    Raises :class:`SchemaOutdatedError` with an actionable message when the
    database is behind head and auto-migrate is disabled.
    """
    status = schema_status(engine)
    if status["up_to_date"]:
        return






    table_names = set(inspect(engine).get_table_names())
    is_uninitialized = not (table_names - {"alembic_version"})

    if auto_migrate or is_uninitialized:
        upgrade_to_head()
        return

    from app.observability.audit import emit_audit

    emit_audit(
        "schema.mismatch",
        result="blocked",
        level="error",
        backend=status["backend"],
        current=status["current"],
        head=status["head"],
    )
    current = status["current"] or "none (uninitialized)"
    raise SchemaOutdatedError(
        "Persistent databases must be initialized with Alembic. "
        "Use 'grave db upgrade' or a disposable in-memory database for tests. "
        "Database schema is not up to date: "
        f"current revision {current}, expected head {status['head']}. "
        "Refusing to start to avoid running against an incomplete schema. "
        "Back up first, then run 'alembic upgrade head' (or 'grave db upgrade'). "
        "To upgrade automatically on startup, set AUTO_MIGRATE=true."
    )
