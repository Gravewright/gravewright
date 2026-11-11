# Realtime: design direction

[Documentation](../README.md) · [Português](../pt-BR/realtime-direction.md) · [Architecture](architecture.md)

## Status and purpose

This document records the approved direction for the table's realtime transport:
how WebSocket commands, post-commit invalidations and recipient projections should
evolve to reduce latency and database contention. The project owner approved it on
2026-11-09, including the transport authorization change in stage 6.

All stages were delivered on 2026-11-09; [Architecture](architecture.md) describes
the resulting behavior and [Testing](testing.md) lists the regression tests. Two
conditional items were not built because their conditions were not met: validating
movement outside the transaction (stage 3) and a shared projection cache (stage 5).
The measurements below describe the transport before these stages.

## Current behavior and measured costs

These measurements were taken on 2026-11-09 with a synthetic campaign on an isolated
test database. They are single samples of handler processing, not end-to-end
latency, percentiles or capacity limits.

- A committed change in items, combat, cards, audio or compendiums schedules nine
  internal events (ten for a scene compendium import): five resource refreshes plus
  layers, actors, tokens and journals. Layer and token handlers also refresh audio.
- For a GM subscribed to the five resource modules and to the actor and journal
  directories, a token move costs 32 SQL statements and 6 frames per client, and an
  audio change costs 108 statements and 24 frames.
- Every token move resends the complete map layers. With 102 unchanged images, a move
  delivered 12,705 bytes instead of 2,115.
- Each socket processes commands, deliveries, cursor, drag and viewport samples and
  pongs in a single sequence. Its incoming queue is unbounded, and rate limiting is
  evaluated when a message is processed rather than when it arrives.
- SQLite `transaction_mode='IMMEDIATE'` serializes every write transaction, and a
  compendium read also opens `BEGIN IMMEDIATE`. A one-second write transaction
  delayed an unrelated write by about 1.03 s in both the DELETE and WAL journal modes.
- A lock timeout (`OperationalError`) in a command handler closes the socket. The
  browser resends pending chat messages and rolls on every ping, which adds duplicate
  work while the server is slow.
- Every received frame rereads the session and membership (two queries). Every
  presence pong writes the lease and runs a global cleanup of expired leases.
- Channels layers silently drop a group message when a channel's queue is full
  (default capacity 100), so a slow consumer can miss an invalidation.

## Invariants

Every stage preserves these rules:

- The server filters every delivery per recipient. No envelope, delta or cache may
  give a recipient data that its complete projection would not contain.
- A request UUID identifies one logical command. Retries (`busy`, deadline and
  reconnection) reuse it; a new operation gets a new UUID.
- Notifications are scheduled after commit, and clients can always resynchronize.
- Write commands keep their authorization, receipts and revisions inside the owning
  services.
- The SDK event surface (`createEvents` in
  `gravewright/modules/static/gravewright_modules/domain-api.js`) keeps delivering the
  same payloads. Any SDK-visible change goes through
  `gravewright/modules/contracts/frontend.json` and `scripts/generate_frontend_api.py`.
- The core contains no RPG-system names. Packages extend refresh dependencies only
  through generic contracts.
- Automatic retries are silent. Any new interface text uses the official translation
  mechanism (`en`, `pt-BR`, `es`).

## Stages

Stages run in order. Stage 5 depends on stage 4, and stage 7 uses the presence task
introduced in stage 2.

| Stage | Change | Status |
| --- | --- | --- |
| 0 | Baseline measurements and instrumentation | Delivered |
| 1 | Recoverable database contention | Delivered |
| 2 | Separate lanes per connection | Delivered |
| 3 | Short write transactions | Delivered; the conditional movement pre-validation was not needed |
| 4 | One envelope per commit | Delivered |
| 5 | Changed-only delivery | Delivered; the conditional shared projection cache was not built |
| 6 | Cached transport authorization | Delivered (start condition met: authorization was 25–50% of the queries on cursor, drag and pong paths) |
| 7 | Presence without per-pong writes | Delivered |

### Stage 0: baseline and instrumentation

- A versioned budget test counts SQL statements, frames and bytes per scenario and
  starts from the values above. An optional benchmark output records medians and
  95th percentiles, following the pattern of `GRAVEWRIGHT_EVENT_BENCHMARK_OUTPUT`.
- Slow-handler warnings report queue wait, handler time, SQL count and time, frames
  and bytes, and lock errors produce a `database busy` warning. A new
  `GRAVEWRIGHT_REALTIME_SLOW_MS` setting controls the threshold (default 500, `0`
  disables it). Logs never include payloads or user content. The Runner hosts Daphne
  in its own process, so these warnings reach `data/logs/runner.log`.

Acceptance: the budgets reproduce the measured values, and baseline browser
measurements are saved before any behavior changes.

### Stage 1: recoverable database contention

- The browser resends pending chat messages and rolls only after reconnecting. A
  `roll_in_progress` reply schedules one retry with backoff (1, 2, 4 and 8 seconds).
- SQLite lock errors become a recoverable `busy` error that carries the same request
  ID, and the browser retries silently with that ID. Other database errors keep
  failing visibly.
- When completing a roll hits a lock, the server releases the reservation so that the
  retry claims it again. The unconfirmed result never leaves the server.
- Each command has a 45-second deadline, above the 30-second SQLite timeout. When it
  expires, the browser treats the socket as failed and reconnects, which resends
  pending commands with their original IDs.
- A lock error in a delivery handler does not close the socket. The affected
  projection is sent again during the next heartbeat upkeep.

Acceptance: pings cause no duplicate sends, a `busy` retry is applied once (one
receipt), and errors other than locks behave as before.

### Stage 2: separate lanes per connection

- Ephemeral samples (cursor, viewport and viewport stop, and drag per stream) use
  latest-value slots processed on a separate per-socket thread. Drag end and cancel
  messages are never dropped.
- Lease renewal after a pong runs outside the command lane.
- Commands keep their order in a bounded queue (256 messages). Rate limiting uses the
  arrival time, and streamer and table checks apply to every lane.

Acceptance: pongs, cursors and drags progress while a command is blocked, commands
stay ordered, and queue overflow or an excessive burst closes the socket with 4429.

### Stage 3: short write transactions

- Reads, starting with compendium reads, run without `BEGIN IMMEDIATE` and keep their
  live grant checks.
- Compendium imports validate their files before the write transaction begins.
- Token commands look for an existing receipt before taking the write lock and build
  the acknowledgement projection after commit. Region automation stays inside the
  transaction because it is part of the operation.
- Conditional: validating movement outside the transaction, with a revision check
  inside it, is done only if measurements show that validation dominates the
  transaction and wall changes carry a checkable revision.

Acceptance: reads open no `BEGIN IMMEDIATE`, a read completes while a writer holds the
lock, concurrent retries of one request produce a single receipt, and command results
keep their current contract.

### Stage 4: one envelope per commit

- `dispatch.changed` schedules a single `room.changes` event that lists the
  projections to refresh. Extension signals are unchanged.
- A declarative dependency map in the core first reproduces the current refresh sets
  without duplicates. It is then narrowed using a test that compares every user's
  projections before and after each representative command.
- Consumers authorize once per envelope, check again before deferred resources, keep
  the current delivery order and emit `api.changed` once per domain.
- Chat history is reloaded only when an envelope requests it, and the history query
  loads message recipients without one query per message.

Acceptance: every projection that changes for any test user appears in the envelope,
each projection is delivered once, and the budgets fall below the stage 0 values.

### Stage 5: changed-only delivery

- Each socket remembers what it last received. Unchanged projections send nothing.
  Tokens and layers send `upserts`/`removes` deltas computed from the recipient's
  complete projection. First subscriptions and resynchronization send complete state.
- The browser merges deltas and dispatches the same events with complete payloads, so
  the board and the SDK see no change.
- A per-campaign revision, incremented inside the committing transaction, lets a
  consumer detect a missed envelope and resynchronize. This stage adds a migration.
- Conditional: a projection cache keyed by scene, revision and user is added only if
  measurements with five or more players show that projection dominates.

Acceptance: applying the deltas always reproduces the complete projection for that
user, hidden tokens never appear in player frames, and a token move in a scene with
102 unchanged images sends no layer data.

### Stage 6: cached transport authorization

This is an approved change to security behavior. Currently, as
[Architecture](architecture.md) describes, the socket rereads the live session, auth
backend, session hash and membership for every received frame, delivery and
heartbeat.

Approved on 2026-11-09:

- A socket may reuse its last successful authorization for up to **2 seconds**, and
  never beyond the session expiry date.
- The following events invalidate a cached authorization before the next frame is
  processed: logout, session deletion, a password change (for other sessions),
  membership removal, a role change, user deactivation, streamer link revocation or
  expiry, and campaign deletion. Changes in the same process synchronously increment a
  local authorization epoch; other processes receive an invalidation event through
  the channel layer.
- Code paths that bypass model signals (`QuerySet.update()` or `.delete()`) must
  increment the epoch and send the invalidation explicitly.
- Write commands are still authorized by their services.
- Start condition: measurements from stages 0–5 show that authorization is a relevant
  cost on the cursor, drag or pong paths. Otherwise the current behavior remains.

Acceptance: each invalidation closes the socket on the next frame, even within the
2-second window, and the existing revocation tests pass unchanged.

### Stage 7: presence without per-pong writes

- `renew` recreates a lease that another socket's cleanup removed.
- A lease is renewed only during the second half of its lifetime. Expired-lease
  cleanup moves to the heartbeat upkeep and runs at most once per half TTL in each
  process, after an existence check.

Acceptance: presence survives a command that runs longer than the TTL, and each
renewal window causes at most one write.

## Outside this direction

- Replacing SQLite or enabling WAL. This is evaluated only after these stages, with
  portability, backup and concurrency tests; the measurement above shows that WAL
  alone does not remove writer serialization.
- Broadcasting unfiltered state and hiding it in the browser.
- Keeping sessions or presence only in process memory, which would break deployments
  with several workers on Redis.
- Removing receipts or revisions to save queries.

## Validation

Each stage keeps the existing Django, Node and browser suites passing and adds
regression tests for its guarantees; [Testing](testing.md) documents them as they are
added. SQL, frame and byte counts are deterministic and may become test ceilings.
Timings are observations compared on the same machine and fixture, never pass/fail
thresholds.
