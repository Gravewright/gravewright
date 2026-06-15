# Development

## Local Workflow

```bash
uv sync --group dev
cp .env.example .env
chmod +x grave
./grave doctor
./grave run --open
```

Fallback:

```bash
uv run python -m app.cli doctor
uv run python -m app.cli run --open
```

## Code Organization

Add code in the layer that owns the behavior:

- CLI and operator tooling: `app/cli`
- HTTP forms and templates: `app/actions`
- product rules: `app/business`
- table runtime: `app/engine`
- SDK package services: `app/engine/sdk`
- realtime dispatch and transport: `app/realtime`
- database access: `app/persistence/repositories`
- shared domain constants and validation: `app/domain`
- browser behavior: `static/js`
- styles: `static/css`
- templates: `templates`

## Service Dependencies

Services are provided through `app/actions/service_dependencies.py` and Litestar dependency injection. Services should be stateless or manage only immutable collaborators.

## Database Changes

Update `app/persistence/tables.py` and add Alembic migrations under `migrations/versions/`. Keep migrations portable for SQLite and PostgreSQL unless a feature intentionally requires PostgreSQL-only behavior.

## Public API Changes

When changing SDK package, browser runtime, manifest, content-pack, schema, CLI, or realtime public contracts:

1. update docs in the same change;
2. update schemas when applicable;
3. add compatibility or migration notes;
4. add tests that cover both valid and invalid inputs;
5. update `CHANGELOG.md`.

## Useful Test Commands

```bash
uv run pytest tests/unit/test_cli_parser_smoke.py -q
uv run pytest tests/unit/test_cli_backup.py tests/unit/test_cli_doctor.py tests/unit/test_sdk_cli.py -q
uv run pytest tests/unit -q
uv run pytest tests/e2e -q
python3 -m compileall app tests scripts main.py
```

## Generated and Runtime Files

Do not commit local runtime data from `storage/`, SQLite databases, WAL/SHM sidecars, `.env`, caches, temporary uploads, local backups, generated performance outputs, or private campaign assets unless a fixture is intentionally part of the test suite.
