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
