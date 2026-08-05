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

## Schema Authority

**Alembic is the authority for schema creation and evolution.** A fresh database
must be created with `alembic upgrade head`, and every schema change ships as a
new numbered Alembic revision with `upgrade`/`downgrade`. No migration
reconstructs the whole schema from `metadata` — the baseline revision
(`0001_initial_schema`) is a static, self-contained rendering so its result does
not change when `tables.py` changes. See
[`adr/ADR-migration-baseline.md`](adr/ADR-migration-baseline.md).

Parity between `alembic upgrade head` and the metadata declared in
`app/persistence/tables.py` is enforced by
`tests/unit/test_schema_alembic_parity.py`: changing `tables.py` without a
matching migration fails CI.

For convenience, application startup can still create missing objects from
SQLAlchemy Core metadata to bootstrap local and test databases quickly. This is
a developer convenience, **not** the supported upgrade mechanism — do not rely on
it to evolve a database with data you care about, and do not reintroduce raw
`sqlite3` schema bootstrap packages.

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

The initial migration (`0001_initial_schema`) is a static rendering of the base
schema — it does not import `metadata` — so a fresh `alembic upgrade head`
deterministically reproduces the schema declared in `tables.py`. SQLite and
PostgreSQL also get the partial unique index that enforces at most one active
scene per campaign. MySQL/MariaDB do not support that partial index in the same
form; application logic enforces the invariant during experimental portability
checks.

### Enum check constraints

Priority enum columns are guarded at the database level so out-of-domain values
are rejected even if a service validation is bypassed: `campaign_members.role`
and `campaign_invitations.role` (`PlayerRole`), `campaign_invitations.status`
(`InvitationStatus`), and `campaign_permission_overrides.effect`
(`PermissionEffect`). The allowed sets are derived from the domain enums in
`app/persistence/tables.py` (`enum_check`), so the constraint and the
application validation cannot drift — `tests/unit/test_enum_constraints.py`
enforces this. The migration that adds them audits existing rows first and
refuses to run against out-of-domain data rather than silently coercing it.

### Backup before upgrading

Always back up before running migrations against data you care about
(`grave backup --include-packages`), and test a restore on a copy first. See
[`alpha.md`](alpha.md) for the Alpha upgrade policy.

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

HTTP action handlers follow the same principle: purely-synchronous handlers are
declared `def` with `sync_to_thread=True` (Litestar offloads them whole), and
mixed handlers wrap their sync unit in `await run_blocking(...)`. See
[`development.md`](development.md) and
[`adr/ADR-http-concurrency.md`](adr/ADR-http-concurrency.md).

## Diagnostics

Owner diagnostics are available at:

```text
GET /inside/diagnostics
```

Diagnostics include in-process realtime metrics and scrubbed recent diagnostic events. They avoid raw payloads, cookies, password fields, session identifiers, and private content.

## Adopting a legacy SQLite database

Persistent databases are created and evolved only with Alembic. If an older
SQLite database was created by `metadata.create_all()` and has no
`alembic_version` table, do not stamp it manually. Stop the application and run:

```bash
grave db adopt
```

The command first creates a timestamped `.pre-adopt-*.bak` copy beside the
database. It then compares tables, columns, primary/unique keys, indexes,
foreign keys, and check constraints with the known schema. Only an exact match
is stamped and upgraded to head; drift is reported and leaves the original
database unstamped. Keep the backup until the application and your data have
been verified. PostgreSQL installations must be backed up with the backend's
native tools and currently require operator-managed adoption.

`metadata.create_all()` is limited to SQLite `:memory:` or an explicitly
opted-in file below the test suite's temporary root. File-backed tests set
`ALLOW_METADATA_BOOTSTRAP=true` together with
`GRAVEWRIGHT_TEST_TEMP_ROOT=<pytest temp directory>`. Project, home, storage,
development, production, and PostgreSQL databases are never eligible; initialize
those with `grave db upgrade`.
