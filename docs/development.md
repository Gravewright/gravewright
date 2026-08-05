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
uv run pytest tests/unit/test_sdk_cli.py -q
uv run pytest tests/unit/test_cli_run.py tests/unit/test_cli_scaffold.py tests/unit/test_sdk_cli.py -q
uv run pytest tests/unit -q
uv run pytest tests/e2e -q
python3 -m compileall app tests scripts main.py
```

## Async Handlers and Blocking Database Work

The backend uses SQLAlchemy Core with **synchronous** DBAPI drivers. Calling a
sync repository/service directly from an `async def` handler blocks the event
loop for the whole transaction and serializes unrelated requests under load.

Follow one pattern per handler (see
[`adr/ADR-http-concurrency.md`](adr/ADR-http-concurrency.md)):

- **Purely-synchronous handler** (no `await`): declare it as a plain `def` with
  `sync_to_thread=True`. Litestar runs it in a worker thread, so the whole
  handler — including its single transaction — stays off the event loop and on
  one thread.

  ```python
  @post("/campaigns", guards=[require_user], sync_to_thread=True)
  def create_campaign(..., campaign_service: CampaignService) -> Redirect | Template:
      result = campaign_service.create_campaign(...)   # sync, offloaded whole
      ...
  ```

- **Mixed handler** (must also `await`, e.g. a realtime broadcast): keep it
  `async def` and wrap the synchronous unit in `await run_blocking(...)`.

  ```python
  result = await run_blocking(service.accept_invitation, invitation_id=..., user_id=...)
  await RealtimeTransport().to_room(...)   # stays on the loop
  ```

**Antipatterns**

- `async def` handler that calls a sync service directly (blocks the loop).
- Splitting one transaction across threads: never run `begin`/`select`/`update`
  of the same unit in separate `run_blocking` calls, and never pass a
  `Connection`/`Session` between threads. Offload the whole unit at once.

## Frontend HTTP client and JSON envelope

Browser code must go through the central client (`static/js/core/http.js`,
`window.GravewrightCore.http`) instead of calling `fetch` directly. It attaches
CSRF from a single source (`core/csrf.js`), parses JSON-or-text safely (never
throws on a non-JSON body), and returns a normalized result:

```js
const result = await GravewrightCore.http.postForm(url, new FormData(form), {
  headers: { "X-Requested-With": "XMLHttpRequest" },
});
if (!result.ok) {
  // result.errorKey is canonical: http.errors.network (status 0), 401
  // auth.errors.session_expired, 403 forbidden, 409 conflict, 429 rate_limited,
  // 5xx server — or the JSON body's error_key when present.
  show(result.errorKey);
  return;
}
```

This is what lets the UI tell a **transport/server failure apart from a form
validation error** — the previous `ui/invitations.js` bug showed any failure
(offline, 500) as "invalid email".

Backend handlers answer JSON callers with the standard envelope via
`app/helpers/http_responses.py`:

```python
from app.helpers.http_responses import wants_json, json_ok, json_error

if wants_json(request):
    return json_ok(message_key="game.invite.success")   # {"ok": true, ...}
    return json_error(error_key="...")                   # {"ok": false, "error_key": ...}
```

Do not re-declare `wants_json` per module. The invitations/membership endpoints
are migrated; other domains follow the same pattern incrementally.

## Dependency Versions

Dependencies are pinned to exact versions for reproducible installs:

- direct dependencies and dependency groups are declared with `==` pins in `pyproject.toml`;
- the full resolution (including transitive dependencies) is frozen in `uv.lock`, which is committed;
- the installers and the Docker image install with `uv sync --frozen`, which uses `uv.lock` exactly and never re-resolves.

To change a dependency version, edit its `==` pin in `pyproject.toml`, then run `uv lock` and commit the updated `uv.lock`. Verify consistency with `uv lock --check`.

## Generated and Runtime Files

Do not commit local runtime data from `storage/`, SQLite databases, WAL/SHM sidecars, `.env`, caches, temporary uploads, local backups, generated performance outputs, or private campaign assets unless a fixture is intentionally part of the test suite.
