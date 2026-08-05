from __future__ import annotations

import threading
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy.engine import Connection, Result, make_url

from app.config import config
from app.helpers.env import PROJECT_ROOT


# P1: SQLite allows a single writer at a time. Without app-side serialization,
# every worker thread that opens a write transaction races for that lock and
# falls into SQLite's busy-timeout backoff (up to 5s) — turning contention into
# multi-second latency and writer starvation under load. This re-entrant mutex
# makes write transactions queue politely (FIFO) on one in-process lock instead
# of fighting at the SQLite layer. Reentrant so a thread that legitimately nests
# write transactions does not self-deadlock. Networked backends (PostgreSQL)
# have real write concurrency and skip this entirely.
_SQLITE_WRITE_LOCK = threading.RLock()


DEFAULT_DATABASE_PATH = (PROJECT_ROOT / "storage" / "gravewright.sqlite3").resolve()
DATABASE_PATH = DEFAULT_DATABASE_PATH

_initialized = False


def _backend() -> str:
    return make_url(config.database_url).get_backend_name()


def configured_sqlite_path() -> Path | str:
    """SQLite path encoded in ``DATABASE_URL``.

    Relative SQLite paths are resolved from the project root, matching the
    contract documented in ``.env.example``. ``:memory:`` is preserved as a
    DB-API string.
    """
    url = make_url(config.database_url)
    if url.get_backend_name() != "sqlite":
        raise RuntimeError("DATABASE_URL is not a SQLite URL")

    database = url.database or ""
    if database in {"", ":memory:"}:
        return ":memory:"

    path = Path(database).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def effective_sqlite_path() -> Path | str:
    """SQLite file currently used by the application.

    A custom SQLite ``DATABASE_URL`` is honored exactly. When the configured URL
    is the built-in default path, ``DATABASE_PATH`` remains the mutable fallback
    so the existing test suite can redirect the database to a temporary file.
    """
    configured = configured_sqlite_path()
    if configured == ":memory:":
        return configured
    if Path(configured) == DEFAULT_DATABASE_PATH:
        return DATABASE_PATH
    return Path(configured)


def effective_database_url() -> str:
    """SQLAlchemy URL after applying Gravewright's path resolution policy."""
    url = make_url(config.database_url)
    if url.get_backend_name() != "sqlite":
        return config.database_url

    path = effective_sqlite_path()
    if path == ":memory:":
        return "sqlite:///:memory:"
    return f"sqlite:///{Path(path).as_posix()}"


def database_storage_root() -> Path:
    """Filesystem root colocated with the active SQLite DB when applicable."""
    if _backend() == "sqlite":
        path = effective_sqlite_path()
        if path != ":memory:":
            return Path(path).resolve().parent
    return Path(DATABASE_PATH).resolve().parent


def _use_metadata_bootstrap() -> bool:
    """Allow metadata bootstrap only for explicitly disposable test databases."""
    if _backend() != "sqlite":
        return False
    path = effective_sqlite_path()
    if path == ":memory:":
        return True
    if not config.allow_metadata_bootstrap:
        return False
    if config.app_env != "test":
        return False
    return _is_disposable_test_path(Path(path))


def _is_disposable_test_path(path: Path) -> bool:
    """Accept file bootstrap only below an explicitly disposable temp root."""
    resolved = path.resolve()
    configured_root = os.environ.get("GRAVEWRIGHT_TEST_TEMP_ROOT", "").strip()
    roots = [Path(tempfile.gettempdir()).resolve()]
    if configured_root:
        roots.insert(0, Path(configured_root).resolve())
    return any(resolved != root and resolved.is_relative_to(root) for root in roots)


def initialize_database() -> None:
    """Ready the schema for the configured backend.

    - disposable test DBs: bootstrap directly from metadata;
    - persistent DBs: require Alembic head, optionally auto-migrating.
    """
    if _backend() == "sqlite":
        sqlite_path = effective_sqlite_path()
        if sqlite_path != ":memory:":
            Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)

    from app.persistence import schema as schema_module
    from app.persistence.engine import get_engine

    engine = get_engine()
    if _use_metadata_bootstrap():
        schema_module.bootstrap_schema_from_metadata(engine)
    else:
        schema_module.ensure_schema_ready(engine, auto_migrate=config.auto_migrate)


def _ensure_initialized() -> None:
    global _initialized
    if not _initialized:
        initialize_database()
        _initialized = True


@contextmanager
def engine_begin() -> Generator[Connection, None, None]:
    """SQLAlchemy connection wrapped in a transaction (commits on success).

    On SQLite the write transaction is serialized through a process-wide lock so
    concurrent worker threads queue instead of contending on SQLite's single
    writer lock (see ``_SQLITE_WRITE_LOCK``).
    """
    _ensure_initialized()
    from app.persistence.engine import get_engine, is_sqlite

    if is_sqlite():
        with _SQLITE_WRITE_LOCK:
            with get_engine().begin() as connection:
                yield connection
    else:
        with get_engine().begin() as connection:
            yield connection


@contextmanager
def engine_connect() -> Generator[Connection, None, None]:
    """SQLAlchemy connection for reads (no surrounding transaction)."""
    _ensure_initialized()
    from app.persistence.engine import get_engine

    with get_engine().connect() as connection:
        yield connection


def one_or_none(result: Result) -> dict | None:
    """First row of a result as a plain ``dict`` (or ``None``)."""
    row = result.mappings().first()
    return dict(row) if row is not None else None


def all_dicts(result: Result) -> list[dict]:
    """All rows of a result as plain ``dict`` objects."""
    return [dict(row) for row in result.mappings()]
