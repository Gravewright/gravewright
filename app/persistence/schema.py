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

from sqlalchemy import text
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


def ensure_schema_ready(engine: Engine, *, auto_migrate: bool) -> None:
    """Validate the database is at head; upgrade or fail per ``auto_migrate``.

    Raises :class:`SchemaOutdatedError` with an actionable message when the
    database is behind head and auto-migrate is disabled.
    """
    status = schema_status(engine)
    if status["up_to_date"]:
        return

    if auto_migrate:
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
        "Database schema is not up to date: "
        f"current revision {current}, expected head {status['head']}. "
        "Refusing to start to avoid running against an incomplete schema. "
        "Back up first, then run 'alembic upgrade head' (or 'grave db upgrade'). "
        "To upgrade automatically on startup, set AUTO_MIGRATE=true."
    )
