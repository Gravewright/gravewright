"""SQLAlchemy engine + schema bootstrap, configured by ``DATABASE_URL``.

Repositories use :func:`get_engine` and the Core expression language
against the tables in :mod:`app.persistence.tables`, so the same code runs on
SQLite, PostgreSQL and MySQL.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Engine
from sqlalchemy import Table
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.config import config
from app.persistence.tables import metadata

_engine: Engine | None = None
_engine_url: str | None = None


def _resolve_url() -> str:
    """The SQLAlchemy URL after project-relative SQLite path resolution."""
                                                                 
    from app.persistence import database

    return database.effective_database_url()


def get_engine() -> Engine:
    global _engine, _engine_url
    url = _resolve_url()
    if _engine is None or _engine_url != url:
        if _engine is not None:
            _engine.dispose()
        _engine = create_engine(url, **_engine_kwargs(url))
        _engine_url = url
        _configure_sqlite_pragmas(_engine)
    return _engine


def _engine_kwargs(url: str) -> dict:
    """Engine options. Networked backends get the full pool tuning; SQLite (WAL)
    gets a wider pool than SQLAlchemy's default 5+10 so the many ``run_blocking``
    worker threads doing concurrent reads don't queue on connection checkout."""
    kwargs: dict = {"future": True, "echo": config.database_echo}
    if make_url(url).get_backend_name() != "sqlite":
        kwargs.update(
            pool_size=config.database_pool_size,
            max_overflow=config.database_max_overflow,
            pool_timeout=config.database_pool_timeout,
            pool_recycle=config.database_pool_recycle_seconds,
            pool_pre_ping=config.database_pool_pre_ping,
        )
    else:
        kwargs.update(
            pool_size=config.sqlite_pool_size,
            max_overflow=config.sqlite_max_overflow,
            pool_timeout=config.database_pool_timeout,
        )
    return kwargs


def reset_engine() -> None:
    """Drop the cached engine. Tests call this when they repoint the database."""
    global _engine, _engine_url
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _engine_url = None


def is_sqlite() -> bool:
    return get_engine().dialect.name == "sqlite"


def _configure_sqlite_pragmas(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_connection, _record):                
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


def upsert_statement(
    *,
    dialect_name: str,
    table: Table,
    values: dict[str, Any],
    index_elements: list[str],
    set_: dict[str, Any],
):
    """Build a portable INSERT ... ON CONFLICT/DUPLICATE KEY UPDATE statement.

    PostgreSQL and SQLite share the ``ON CONFLICT (...) DO UPDATE`` form keyed on
    ``index_elements``; MySQL uses ``ON DUPLICATE KEY UPDATE`` (keyed implicitly
    by the row's unique/primary keys).
    """
    if dialect_name in {"mysql", "mariadb"}:
        statement = mysql_insert(table).values(**values)
        return statement.on_duplicate_key_update(**set_)

    insert_fn = postgresql_insert if dialect_name == "postgresql" else sqlite_insert
    statement = insert_fn(table).values(**values)
    return statement.on_conflict_do_update(index_elements=index_elements, set_=set_)


def create_schema() -> None:
    """Create every table (and the partial index) on the configured backend."""
    engine = get_engine()
    metadata.create_all(engine, checkfirst=True)
    _ensure_incremental_columns(engine)

                                                                               
                                                                               
                                                                   
    dialect = engine.dialect.name
    if dialect in ("sqlite", "postgresql"):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_scenes_active_campaign "
                    "ON scenes (campaign_id) WHERE active = 1"
                )
            )


def _ensure_incremental_columns(engine: Engine) -> None:
    """Small compatibility bridge for DBs created before Alembic migrations.

    ``metadata.create_all()`` creates missing tables but does not alter existing
    ones. Until production deployments run Alembic explicitly, keep additive
    schema changes safe for self-hosted SQLite/PostgreSQL/MySQL databases.
    """
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "scenes" in table_names:
        scene_columns = {column["name"] for column in inspector.get_columns("scenes")}
        if "board_version" not in scene_columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE scenes ADD COLUMN board_version INTEGER NOT NULL DEFAULT 1")
                )
