# Lobby and ready check

The campaign lobby combines the existing realtime presence with a persistent,
idempotent preparation state. Each member can select a character they own, report
whether the page assets finished loading, and mark themselves ready. The GM sees
the same server-authorized summary as every member.

`LOBBY_READY_CHECK_ENABLED=true` enables the UI and endpoints. Setting it to
`false` and restarting hides the interface and makes its endpoints return 404;
stored readiness remains available if the feature is enabled again.

## Guarantees

- Only campaign members can read or update a lobby.
- A non-GM can select only an active actor explicitly owned by that user; the GM
  may select any active actor in the campaign.
- Repeating an identical update is safe and leaves one state row per member.
- Realtime broadcasts contain only the campaign ID; clients fetch the canonical
  snapshot after receiving the event.
- Active in-process WebSocket connections take precedence over persisted presence.
  Persisted connections older than 12 seconds are marked offline, and an open
  lobby refreshes every 10 seconds so abrupt disconnects converge automatically.

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /game/lobby?campaign_id=...` | Returns members, online/ready/assets state, selected character, selectable actors, and totals. |
| `POST /game/lobby/state` | Idempotently replaces the authenticated member's preparation state. |
