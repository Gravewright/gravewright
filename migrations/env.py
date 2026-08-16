from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import inspect
from sqlalchemy import pool
from sqlalchemy import text

from app.persistence.database import effective_database_url, ensure_sqlite_database_parent
from app.persistence.tables import metadata

config = context.config

if config.config_file_name is not None:
    # Alembic may run in-process (CLI/tests/startup). Do not disable application
    # loggers as a side effect, otherwise diagnostics become order-dependent.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = metadata

LEGACY_0047_REVISION = "0047_remove_quest_board_description"
CURRENT_0047_REVISION = "0047_remove_quest_board_desc"


def _database_url() -> str:
    return effective_database_url()


def _normalize_legacy_revision(connection) -> None:
    """Map the oversized 0047 marker written by older builds to its new ID."""
    if inspect(connection).has_table("alembic_version"):
        connection.execute(
            text(
                "UPDATE alembic_version SET version_num = :current "
                "WHERE version_num = :legacy"
            ),
            {"current": CURRENT_0047_REVISION, "legacy": LEGACY_0047_REVISION},
        )
    # Inspection starts an implicit transaction on both supported backends.
    # Finish it before Alembic opens the migration transaction below.
    connection.commit()


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    ensure_sqlite_database_parent()
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        _normalize_legacy_revision(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
