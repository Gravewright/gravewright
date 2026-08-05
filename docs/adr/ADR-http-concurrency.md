# ADR: HTTP handler concurrency model

- **Status:** Accepted
- **Date:** 2026-08-04
- **Stage:** Maintenance Plan — Etapa 3 (Banco síncrono em handlers assíncronos)

## Context

Gravewright serves HTTP over an async ASGI stack (Litestar/uvicorn) but persists
through SQLAlchemy Core with **synchronous** DBAPI drivers. Many action handlers
were written as `async def` yet performed only synchronous
repository/service calls (no `await`). Such a handler blocks the event loop for
the entire duration of its database transaction. At low load this is invisible;
under concurrency a single slow query serializes every other request sharing the
loop.

A `run_blocking` helper (anyio/`ThreadPoolExecutor` offload) already existed and
was used on the realtime hot paths, but not in the HTTP action handlers.

## Decision

One offload pattern, chosen per handler by its shape:

1. **Purely-synchronous handlers → `def` with `sync_to_thread=True`.** Litestar
   runs sync handlers in a worker thread. The entire handler — and therefore its
   single database transaction — runs off the event loop and stays on one
   thread. This is the default for CRUD-style handlers that do not `await`.

2. **Mixed handlers → `async def` + `await run_blocking(sync_unit)`.** Handlers
   that must `await` something (typically a realtime broadcast) keep the async
   signature and offload only their synchronous database unit through
   `run_blocking`, as a single call so the transaction is not split.

3. **Already-async handlers** whose service methods are themselves async (e.g.
   presence/forgot-password) are left as-is.

### Rules

- A transaction is offloaded as one unit; never split `begin`/`select`/`update`
  across threads.
- Never transport a `Connection`/`Session` between threads.
- Do not mix patterns within a handler.

## Scope of the first migration

Applied to the priority domains (campaigns, invitations, auth). Converted to
`def` + `sync_to_thread=True`:

- `inside/create_campaign`, `inside/update_campaign`, `inside/delete_campaign`,
  `inside/request_delete_campaign`, `inside/decline_campaign_invitation`,
  `inside/list_campaign_invitations`, `inside/show_inside`,
  `game/invite_to_campaign`, `auth/submit_login`, `auth/submit_register`,
  `auth/submit_reset_password`, `auth/logout`.

Converted to `run_blocking` (mixed with a realtime broadcast):

- `game/ban_member`, `inside/accept_campaign_invitation`.

Remaining `async def` action handlers in other domains (scenes, cards, journals,
assets, sdk, etc.) are migrated in later, domain-scoped changes following the
same rules.

## Consequences

- A slow database call no longer serializes independent requests.
- The pattern is enforced by `tests/unit/test_async_handler_offload.py`: it
  proves the offload mechanism keeps the loop responsive, that an exception
  inside an offloaded transaction rolls back, and (source guard) that the
  priority handlers use `sync_to_thread=True` / `run_blocking`.
- Litestar's TestClient drives the app through a blocking anyio portal that
  serializes ASGI calls, so end-to-end event-loop concurrency cannot be shown
  through it; the mechanism the handlers use is tested directly instead.

## Follow-ups

- Etapa 5 reworks `accept_campaign_invitation` for idempotency/concurrency; its
  offload here is compatible and stays.
- Continue migrating the remaining async action domains.
