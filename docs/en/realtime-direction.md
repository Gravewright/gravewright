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
| 8 | Background load found in a replayed session | Delivered |
| 9 | SQLite write-ahead log | Delivered (owner decision, 2026-11-15) |
| 10 | Deliveries on their own lane | Delivered (owner decision, 2026-11-15) |
| 11 | Work repeated for every sample and scene change | Delivered (2026-11-15); scene answers follow the stage 6 rule |

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

### Stage 8: background load found in a replayed session

On 2026-11-15 a GM and three players replayed a real 0.3.5 session with real browsers,
on a copy of that campaign and the Runner profile, at the command rates of its
receipts. No lock errors occurred. Each `room.changes` delivery cost about 60 SQL
statements and 0.4 s per recipient, and GM scene activations made every client
resubscribe at once, which produced multi-second queues. Most database work did not
come from play:

- every installed-module call rewrote its mount lease (about 106 writes per minute
  with four clients, more than all game writes together);
- the mind map workspace reloaded over HTTP after every socket frame, including other
  users' cursors (250–310 reads per minute);
- the SDK HTTP client read a new CSRF token before every write;
- the GM board renews its viewport every second, and each GM camera sample
  (`room.gm_sample`) waited on every recipient's command lane (700–800 s per hour).

Changes:

- Module calls extend a mount lease only during the second half of its 30 minutes.
- The mind map workspace ignores frames that carry no table state: liveness,
  pointer, drag and camera samples and prefetch hints.
- The SDK HTTP client reuses one CSRF token per client and reads it again once when
  the server refuses it (`invalid_csrf_token`); the refusal precedes the view, so the
  repeated request cannot repeat its effect.
- GM camera samples use the peer sample lane, with one latest-value slot per GM.
- While a socket's work waits, the channel reader keeps at most one queued
  `room.presence` and one `room.lobby`, and folds a `room.changes` envelope into the
  queued one right before it when their revisions are consecutive. The folded
  envelope refreshes the union in delivery order and carries `first_revision`, so a
  lost envelope still triggers a full refresh. Envelopes with teleports are not folded.
- A presence renewal counts its half TTL from when it began, so a renewal that waited
  for SQLite no longer pushes the next one past the lease expiry.

Merging the scene subscriptions each client sends after an activation was not done:
each `resources.sync` ran in about 22 ms and waited about 0.4 s (p95 2.4 s) behind
other work, so fewer frames would not remove that work.

Acceptance: a GM sample reaches a recipient whose command is blocked and only each
GM's newest sample waits; repeated presence reads run once; consecutive envelopes are
delivered once with the union of their projections, while gaps still refresh
everything; a fresh lease is read without a write.

### Stage 9: SQLite write-ahead log

- `DATABASE_JOURNAL_MODE` selects the journal on every connection; `wal` is the
  default and `delete` keeps the rollback journal for a database on a network folder.
  With WAL a writer commits while readers keep their snapshot, so deliveries, samples
  and presence reads no longer wait for each commit. Writers still take turns.
- The database's `-wal` and `-shm` files belong to it. The updater already protects
  them, backs up through SQLite's backup API (which includes the log) and removes them
  before restoring a database file. The test runner removes sidecars left by an
  interrupted run before creating the test database, because SQLite replays a `-wal`
  file into any database of that name.
- Synchronous mode stays at SQLite's default, so a commit is durable when it returns.

Acceptance: connections report `wal`; a writer commits while a reader holds an open
read transaction (the same commit waits under `delete`); managed update, failure
restoration and rollback keep the database consistent.

Measured in the stage 8 replay with scene changes (one 20-minute session per journal,
both with the delivery lane of stage 10): WAL lowered the 99th percentile of SQL time
per statement from 12.2 to 8.2 ms and the 95th percentile of sheet-save round trips
from 1.6 s to 0.4 s. Most remaining time is Python work, not SQL.

### Stage 10: deliveries on their own lane

- Server events (`room.changes` and the other channel events) wait in a delivery queue
  handled by a third per-socket task with its own synchronous thread. Commands and
  subscriptions keep their order on the command lane and no longer wait behind
  deliveries; the delivery lane starts after connect, so earlier events wait in order.
- Commands and deliveries both refresh projections. Each projection is read and sent
  under its own lock (tokens, layers, actors, journals, the scene list with chat
  history, each table resource, the lobby), and a subscription changes its state under
  the same lock. Sends of one projection therefore follow the order of their reads,
  and a refresh of the previous subscription never arrives after, or as the base of a
  delta for, the new one. Different projections proceed in parallel.
- A command's acknowledgement may now arrive after the projection its commit
  refreshed, as it already could for another user's command.
- Coalescing and folding (stage 8) apply to the delivery queue.

Acceptance: a command is acknowledged while a delivery is blocked; a subscription
change waits for an in-flight refresh of the same projection and its state is the last
one sent; repeated presence reads run once and consecutive envelopes fold while
deliveries wait.

Measured in the same replay without scene changes, with WAL and this lane against
stage 8 alone: commands over one second fell from 8 to 2 per hour and the slowest
command from 1.8 s to 1.1 s, and deliveries stopped queueing (95th percentile 1 ms).
Each `room.changes` delivery took longer, about 760 ms on average instead of 540 ms:
the extra thread per socket competes for the interpreter lock, and the time inside the
thread outside SQL and CPU grew from about 180 to 290 ms. The sessions with scene
changes separate the two effects: the lane alone raised the average delivery from 520
to 611 ms, and WAL brought it back to 560 ms. With scene changes, the resubscription bursts still
queued 2–3 s on the command lane: they are the client's own subscription frames.
Reducing the Python work per projection is the next step; if it does not remove this
cost, the lane should be revisited.

### Stage 11: work repeated for every sample and scene change

A profile of the stage 10 replay with scene changes, by synchronous CPU per operation,
showed that projections were not the main cost: relaying cursors used 65% of it (each
sample resolved the member and scene in the database, once for the sender and once
for every recipient), GM camera samples and viewports another 21%, and `room.changes`
8%. Every scene change also resent each client's item and compendium directories,
which do not depend on the scene (about 340 KB per client), and every scene list
refresh resent the whole chat history (about 84 KB), usually unchanged.

- Samples reuse the answer to "may this member see this scene" (relayed cursors, the
  sender's pointer identity, GM camera samples and the tile drain) for at most the
  stage 6 window, while the access epoch is unchanged and until the socket receives
  its next server event other than samples, presence and lobby reads. Changes are
  announced after commit, so an answer read before an announcement is never stored
  after it; a refused read drops every answer. A socket's own viewport always reads
  the database. Rows changed directly in the database without an event reach samples
  when the answer expires, as cached authorization does.
- The table subscribes items and compendiums without a scene, so a scene change
  resubscribes only combat, cards, audio, clocks and clues.
- A token or layer subscription change no longer recomputes audio and combat, whose
  inputs it does not change; extensions still receive the same `api.changed` hints.
- Chat history travels like other projections: an unchanged history is not sent
  again, a live message (`chat.message`, `chat.ack`) makes the next one whole, and
  `chat.sync` always receives it. Deltas were not added: in the replay, histories that
  changed between refreshes totalled 0.18 MB, while scope changes need the whole list.
- Live messages are sent under the chat history's lock. Since stage 10 a history read
  on one lane could reach the browser after a message sent from the other lane, and
  the browser then replaced its list without that message.
- Whole projections keep only their canonical text, so the previous one is not
  serialized again for each comparison.
- A frame sent between Daphne's closing handshake and the disconnect event is
  dropped instead of failing its lane.

Acceptance: a cursor relay reads each scene once, a scene announcement stops it at
once and an access change in the process reads again; subscription changes do not
recompute audio or combat; an unchanged history is not sent, and neither a live
message nor an acknowledgement reaches the browser before an older history.

Measured in the same replay with scene changes, with WAL and the delivery lane,
against stage 10 (one 20-minute session each): synchronous server CPU fell from 326 to
114 s and process CPU from 553 to 304 s (median 0.41 to 0.17 cores); the cursor relay
went from 212 to 26 s and GM camera samples from 36 to 12 s. Browsers received
15.6 MB instead of 26.7 MB: compendium directories 1.7 MB instead of 10.3 MB and chat
history 3.1 MB instead of 5.9 MB. Commands over one second fell from 197 to 95 per hour
and their 95th-percentile wait from 1.9 to 1.1 s; a token move reached the other players
in 0.49 s at the 95th percentile instead of 1.36 s, a GM activation was acknowledged in
1.4 s instead of 3.9 s, and pointers reached peers in 6 ms instead of 32 ms at the
median. Sheet saves were slower at the 95th percentile (0.9 s instead of 0.4 s; earlier
runs ranged from 0.4 to 1.6 s).

Each `room.changes` delivery still takes about 540 ms on average: an envelope reaches
every socket at once, and each delivery uses about 74 ms of CPU, so the recipients'
threads take turns for the interpreter lock (263 ms outside SQL for 74 ms of CPU). The
cost per projection multiplied by the number of recipients is now the remaining lever;
the delivery lane stays, because commands no longer wait behind it.

## Outside this direction

- Replacing SQLite. WAL lets readers proceed during a commit but does not remove
  writer serialization (see the measurement above and stage 9).
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
