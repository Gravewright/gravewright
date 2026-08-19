# Directed interactions

Directed interactions are server-owned multiplayer decisions. Requesters declare explicit campaign recipients, plain-text prompt data, a bounded response schema, deadline, visibility, and optional workflow provenance. They never contain arbitrary HTML or execute an action automatically.

```js
const interaction = await sdk.interactions.request({
  kind: "reaction",
  recipients: [playerId],
  title: "Reaction",
  text: "Use Shield?",
  responseSchema: { type: "boolean" },
  deadline: Math.floor(Date.now() / 1000) + 30
});
```

Supported response types are boolean, single choice, bounded multi-choice, bounded number, and bounded string. The server derives the responder from the authenticated session. Responses can be immutable or replaceable; idempotency keys make retries safe. Open interactions survive reload and are recovered with `list({status: "open", recipient: "me"})`. Deadlines are server-owned, and package deactivation cancels its open requests.

