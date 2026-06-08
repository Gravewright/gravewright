# Database Backends and Migrations

Gravewright uses SQLAlchemy Core metadata in `app/persistence/tables.py` as the schema source.

## Supported Backends

| Backend | Status | Notes |
| --- | --- | --- |
| SQLite | local development and tests | Default for local runs. Production use is refused unless explicitly overridden. |
| PostgreSQL | supported production backend | Recommended production database. |
| MySQL/MariaDB | experimental portability only | V1 production startup refuses it. Integration smoke tests may exercise it when explicitly configured. |

## Local SQLite

Default:

```env
DATABASE_URL=sqlite:///storage/gravewright.sqlite3
```

Relative SQLite paths are resolved from the project root. For example, `sqlite:///storage/custom.sqlite3` points at `<project>/storage/custom.sqlite3` even if the process starts elsewhere.

## PostgreSQL

Recommended production form:

```env
DATABASE_URL=postgresql+psycopg://gravewright:<password>@localhost:5432/gravewright
```

Use PostgreSQL for production unless you have a deliberate reason to run SQLite and accept its operational limits.

## Runtime Schema Creation

Application startup creates missing schema objects through SQLAlchemy Core metadata. This keeps fresh local and test databases easy to bootstrap.

Historical schema evolution should still go through Alembic migrations. Do not reintroduce raw `sqlite3` schema bootstrap packages.

## Alembic

Alembic is configured in:

```text
alembic.ini
migrations/env.py
migrations/versions/
```

Common commands:

```bash
alembic upgrade head
alembic current
alembic revision --autogenerate -m "describe change"
```

The initial migration creates the current SQLAlchemy Core schema. SQLite and PostgreSQL also get the partial unique index that enforces at most one active scene per campaign. MySQL/MariaDB do not support that partial index in the same form; application logic enforces the invariant during experimental portability checks.

## Production Hardening

When `APP_ENV=production`, startup validates database-related safety:

- `DATABASE_ECHO=false`;
- PostgreSQL is recommended and supported;
- SQLite is refused unless `ALLOW_SQLITE_IN_PRODUCTION=true`;
- MySQL/MariaDB is refused in V1 production.

See `configuration.md` and `deployment.md`.

## Integration Smoke Tests

Backend smoke tests are opt-in:

```bash
GRAVEWRIGHT_TEST_DATABASE_URLS="postgresql+psycopg://user:pass@localhost:5432/gravewright_test" \
  uv run pytest tests/integration/test_database_backends.py -q
```

Multiple URLs may be comma-separated:

```bash
GRAVEWRIGHT_TEST_DATABASE_URLS="postgresql+psycopg://...,mysql+pymysql://..." \
  uv run pytest tests/integration/test_database_backends.py -q
```

The smoke test creates missing schema objects, inserts rows with random IDs, verifies the cross-dialect upsert helper, and deletes only rows it created.

## Async Runtime and Synchronous Repositories

Gravewright currently uses SQLAlchemy Core with synchronous DBAPI drivers. Async WebSocket paths should not call blocking repositories directly from the event loop. Use:

```python
app.helpers.async_blocking.run_blocking(...)
```

Realtime paths already offload recipient lookup, event-log append/replay, presence writes, fog mutations, viewport chunk reads, and board state mutations.

## Diagnostics

Owner diagnostics are available at:

```text
GET /inside/diagnostics
```

Diagnostics include in-process realtime metrics and scrubbed recent diagnostic events. They avoid raw payloads, cookies, password fields, session identifiers, and private content.
