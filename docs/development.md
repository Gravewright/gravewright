# Development

## Local Workflow

```bash
uv sync
cp .env.example .env
uv run uvicorn main:app --reload
```

Run focused tests while editing:

```bash
uv run pytest tests/unit/test_map_upload_service.py
```

Run broad checks before sharing a change:

```bash
uv run pytest tests/unit
python3 -m compileall app tests scripts main.py
```

## Code Organization

Add code in the layer that owns the behavior:

- HTTP forms and templates: `app/actions`
- product rules: `app/business`
- table runtime: `app/engine`
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

When changing system, module, browser, manifest, content-pack, schema, or realtime public contracts:

1. update docs in the same change;
2. update schemas when applicable;
3. add compatibility or migration notes;
4. add tests that cover both valid and invalid inputs.

## Generated and Runtime Files

Do not commit local runtime data from `storage/`, caches, temporary uploads, or generated performance outputs unless a fixture is intentionally part of the test suite.
