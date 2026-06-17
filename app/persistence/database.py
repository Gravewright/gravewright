from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy.engine import Connection, Result, make_url

from app.config import config
from app.helpers.env import PROJECT_ROOT


                                                                                
                                                                         
                                                    
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


def initialize_database() -> None:
    """Create the portable SQLAlchemy Core schema for the configured backend."""
    if _backend() == "sqlite":
        sqlite_path = effective_sqlite_path()
        if sqlite_path != ":memory:":
            Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)

    from app.persistence.engine import create_schema

    create_schema()


def _ensure_initialized() -> None:
    global _initialized
    if not _initialized:
        initialize_database()
        _initialized = True


@contextmanager
def engine_begin() -> Generator[Connection, None, None]:
    """SQLAlchemy connection wrapped in a transaction (commits on success)."""
    _ensure_initialized()
    from app.persistence.engine import get_engine

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
