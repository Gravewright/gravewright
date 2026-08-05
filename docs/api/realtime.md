# Realtime API

The realtime API is exposed at:

```text
GET /game/ws
```

The transport is WebSocket-based. The backend is authoritative.

## Connection Requirements

A client must have:

- an authenticated browser session;
- campaign membership;
- an allowed origin when origin restrictions are configured;
- messages within `WS_MAX_MESSAGE_BYTES`;
- command rates within configured token buckets.

## Command Flow

1. Client sends a JSON command envelope.
2. The ingress guard validates size, rate, and shape.
3. `CommandDispatcher` routes the command.
4. Command handlers validate permissions and state.
5. Mutations are persisted.
6. Events are broadcast and appended to the room event log when replayable.

## Event Log and Replay

Room events have monotonically increasing sequence numbers. Clients can resume from known sequence state to avoid a full page reload after reconnect. Realtime replay is bounded by event retention and scene epoch checks.

## Scene Streaming

Large maps are streamed through viewport subscriptions. Clients subscribe to a viewport; the server prioritizes chunks by viewport relevance and sends chunk metadata or binary chunk frames. Known chunks are acknowledged so reconnects can avoid resending unchanged chunks.

## Presence

Presence is campaign-scoped. The server sends snapshots on connect and updates when users come online or go offline.

### Data minimization

Membership and presence payloads (`presence.snapshot`, `member.joined`, and the
member roster embedded in the game page) are minimized to the fields the client
actually needs: `user_id`, `name`, `role`, and `is_online`. They **must not**
carry email or other PII. Email is used only where it is functional (inviting a
member by email) or behind an authorized, owner-only admin endpoint. This
contract is enforced by `tests/unit/test_realtime_pii.py`.

### Membership idempotency

Accepting a campaign invitation is idempotent and concurrency-safe: N concurrent
or repeated accepts for the same user create exactly one membership (the
`(campaign_id, user_id)` unique constraint plus `INSERT ... ON CONFLICT DO
NOTHING` are the guard). `member.joined` is published **at most once** — only for
the request that actually created the membership, and only after the transaction
commits. A re-accept by an existing member returns a stable success with no new
row and no event. Enforced by `tests/integration/test_membership_concurrency.py`.

## Common Server Events

```text
presence.snapshot
presence.updated
chat.message.created
chat.message.deleted
member.joined
member.removed
scene.created
scene.updated
scene.layer.created
scene.upload.progress
token.created
token.updated
token.deleted
sheet.updated
combat.updated
```

The exact event set evolves with table features. Event payloads should not be treated as stable public contracts unless documented for extension use.

## Blocking Work

Async handlers that need synchronous repository/service work should use `run_blocking(...)`. This keeps the event loop responsive and emits diagnostics for slow blocking calls.
