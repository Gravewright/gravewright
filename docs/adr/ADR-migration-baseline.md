# ADR: Migration baseline and Alembic as schema authority

- **Status:** Accepted
- **Date:** 2026-08-04
- **Stage:** Maintenance Plan: Etapa 1 (Governança e imutabilidade de migrações)

## Context

`migrations/versions/0001_initial_schema.py` previously built the schema with
`from app.persistence.tables import metadata` followed by
`metadata.create_all(bind=bind, checkfirst=True)`. Because the migration derived
its result from the *live* metadata, the schema produced by revision `0001`
changed silently whenever `tables.py` changed. Consequences:

- The historical schema could not be reproduced from the migration history.
- Intermediate migrations `0002`–`0014` are all written defensively
  (`if not _has_table(...)` / `if not _has_column(...)`), so on a fresh database
  `0001`'s `create_all` already produced today's full schema and every later
  migration became a no-op.
- There was no automated guard that a change to `tables.py` was accompanied by a
  migration, so drift between "what startup creates" and "what `alembic upgrade
  head` creates" could go unnoticed.

## Decision on revision 0001: rebaseline (rewrite in place)

**Has `0001` been distributed to persistent installations that must be
preserved byte-for-byte?** No hard guarantee is owed. The project is
`v2.1.0-alpha`, and the historical policy preserved in
[`RELEASE_NOTES.md`](../../RELEASE_NOTES.md) states:

> During Alpha, maintainers may ship breaking changes without an automatic
> migration path … old data may still require manual repair or fresh setup.
> Structural changes: database schema … may still occur between Alpha
> releases, and a guaranteed automatic upgrade path is not promised yet.

Given that policy, **rebaselining `0001` is authorized**. We rewrote
`0001_initial_schema.py` as a *static* rendering of the schema:

- It no longer imports `metadata` and no longer calls `create_all` /
  `drop_all`. The `upgrade()`/`downgrade()` bodies are explicit
  `op.create_table(...)` / `op.drop_table(...)` operations, generated once with
  Alembic autogenerate against the frozen metadata and now hand-owned.
- The revision id `0001_initial_schema` is preserved, so databases that already
  recorded `0001` as applied are unaffected (the revision does not re-run).
- The partial unique index `idx_scenes_active_campaign` (not expressible in
  portable metadata) is created via explicit SQL in the migration, as before.

### Why not squash the whole chain?

Squashing `0002`–`0014` into the baseline would rewrite already-applied
revisions and break existing Alpha databases sitting at an intermediate head.
Instead we keep the numbered chain intact. A squash to a single clean baseline
is deferred to the **first stable (LTS 1) release**, at which point there is a
defined supported-upgrade floor.

### Existing Alpha databases

- A DB at any recorded revision is unaffected by the `0001` rewrite (`0001`
  won't re-run). Remaining revisions apply through their existing guarded logic.
- The legacy-upgrade path is covered by
  `tests/unit/test_schema_legacy_upgrade.py`.

## Consequences

- **Alembic is the authority for schema evolution.** New schema changes ship
  only as new numbered revisions with `upgrade`/`downgrade`. No migration may
  reconstruct the whole schema from `metadata`.
- **Drift is caught in CI.** `tests/unit/test_schema_alembic_parity.py` builds an
  empty database, runs `alembic upgrade head`, and asserts the resulting schema
  (tables, columns, primary keys, foreign keys, unique constraints, indexes, and
  the partial active-scene index) matches what the current metadata declares.
  Changing `tables.py` without a matching migration now fails this test.
- Startup-time `create_all` still exists in `app/persistence/engine.py` as a
  dev/test convenience bridge. Removing it as an upgrade mechanism is the scope
  of **Etapa 2**; this ADR only establishes Alembic as the authority.

## Follow-ups

- Etapa 2: remove `create_all` / `_ensure_incremental_columns` from the
  production startup path; add a schema-diagnostics CLI command.
- LTS 1: squash `0001`–`00NN` into a single clean baseline with a documented
  supported-upgrade floor.
