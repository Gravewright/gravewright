# Package-to-package Messaging

`sdk.bus.*` is the stable package interoperability contract — the only
client-side messaging surface in SDK 1.

## Stable Interop Bus

Packages declare public interop in `manifest.json` and use the scoped SDK:

```json
{
  "capabilities": ["bus.publish", "bus.subscribe", "bus.request", "bus.provide"],
  "interop": {
    "emits": {
      "my-addon.inventory.changed": {
        "schema": "schemas/events/inventory-changed.schema.json"
      }
    },
    "listens": {
      "other-ruleset.actor.rested": { "schema": "schemas/events/rested.schema.json", "optional": true }
    },
    "provides": {
      "my-addon.getWeight": {
        "params": "schemas/rpc/get-weight.request.json",
        "returns": "schemas/rpc/get-weight.response.json"
      }
    },
    "requires": {
      "other-ruleset.actor.getArmorClass": {
        "params": "schemas/rpc/ac.request.json",
        "returns": "schemas/rpc/ac.response.json",
        "optional": false
      }
    }
  }
}
```

## Events

```js
sdk.bus.subscribe("other-addon.inventory.changed", (payload) => {});
await sdk.bus.publish("my-addon.inventory.changed", { itemId, count });
```

Rules:

- `publish` requires `bus.publish`; `subscribe` requires `bus.subscribe`.
- A package may publish only in its own `{package_id}.*` namespace.
- Published events must be declared in `interop.emits`.
- **Subscribed events must be declared in `interop.listens`** (any namespace,
  including core events). An undeclared subscribe throws
  `sdk.interop.event_undeclared`.
- Reserved namespaces are `gravewright.*`, `core.*`, and `system.*`.
- Payloads are cloned/frozen before delivery.

## RPC

```js
sdk.bus.provide("my-addon.getWeight", async ({ itemId }, ctx) => {
  return computeWeight(itemId, ctx.callerPackageId);
});

const result = await sdk.bus.request("my-addon.getWeight", { itemId }, { timeoutMs: 2000 });
```

`request` resolves to:

```ts
{ ok: true, value: T } | { ok: false, error: { code: string, message: string } }
```

Rules:

- `provide` requires `bus.provide`; `request` requires `bus.request`.
- A package may provide only in its own `{package_id}.*` namespace.
- Provided methods must be declared in `interop.provides`.
- **Requested methods must be declared in `interop.requires`.** An undeclared
  request throws `sdk.interop.method_undeclared`.
- Duplicate providers raise `bus.provider_conflict`.
- Missing providers return `bus.provider_not_found`.
- Timeouts return `bus.provider_timeout`.
- Provider exceptions return `bus.response_invalid`.
- Providers receive caller context, including `callerPackageId`,
  `providerPackageId`, `userId`, and `campaignId` when available.

## Validation And Doctor

The manifest validator enforces namespace and path safety. The loader checks
declared schema files exist on disk. The doctor reports provider conflicts and
missing required providers for active campaign packages.

<<<<<<< HEAD
Under the Alpha 2.0.0 SDK Freeze, enforcement is **strict**: all four directions
are hard-enforced at runtime — `publish`→`emits`, `subscribe`→`listens`,
`provide`→`provides`, and `request`→`requires`. Runtime payload/response schema
validation against the declared schemas is tracked as post-freeze hardening
toward LTS 1.
=======
```json
"dependencies": [
  {
    "id": "dice-so-nice-lite",
    "kind": "addon",
    "minimum": "0.1.0"
  }
]
```

Use a hard dependency when your package cannot function without the other package being installed, enabled, compatible, and active.

### Optional integration

Do not declare a dependency when the integration is optional.

```js
sdk.hooks.on("package:dice-so-nice-lite:settled", (payload) => {
  if (!payload || payload.version !== 1) return;
  // Enhance behavior when the peer exists.
});
```

If the peer package is inactive, the event simply never fires.

## Best practices

- Namespace every cross-package event by the emitting package id.
- Document emitted and consumed events in the package README.
- Keep payloads small and serializable.
- Treat unknown versions as unsupported and ignore them safely.
- Prefer optional integration unless the peer package is required for core behavior.
- Do not use events as a replacement for authoritative server state.

## Formal interop bus — `sdk.bus.*` (experimental)

`sdk.hooks` is `legacy_experimental`. The formal, forward-looking channel for
inter-package communication is the interop bus. It is a clean, separate channel —
**not** a wrapper over `sdk.hooks`, with no automatic bridge between the two.

```ts
sdk.bus.subscribe("other-addon.inventory.changed", (payload) => { /* ... */ });
sdk.bus.publish("my-addon.inventory.changed", { itemId, count });
```

Rules:

- `sdk.bus.publish` requires the `bus.publish` capability; `sdk.bus.subscribe`
  requires `bus.subscribe` (both experimental).
- A package may only publish in its own `{id}.*` namespace; the reserved
  `gravewright.*` / `core.*` / `sdk.*` namespaces are engine-owned. A package may
  subscribe to any event, including core events.
- Payloads are delivered frozen/cloned; a failing listener cannot break the rest.

Manifest declaration:

```json
{
  "interop": {
    "emits": { "my-addon.inventory.changed": { "schema": "schemas/events/inventory-changed.schema.json" } },
    "listens": { "gravewright.actor.updated": { "optional": true } },
    "provides": { "my-addon.getWeight": { "request": "schemas/rpc/get-weight.request.json", "response": "schemas/rpc/get-weight.response.json" } }
  }
}
```

The validator enforces namespacing and safe schema paths; the loader checks the
declared schemas exist on disk; the doctor reports invalid interop declarations
(`sdk.interop.*`).

### Request / provide (RPC)

One provider per method; a request returns a structured `BusResult`:

```ts
sdk.bus.provide("my-addon.getWeight", async ({ itemId }) => computeWeight(itemId));
const result = await sdk.bus.request("my-addon.getWeight", { itemId }, { timeout: 2000 });
// result is { ok: true, value } | { ok: false, error: { code, message } }
```

- `sdk.bus.provide` requires `bus.provide`; `sdk.bus.request` requires
  `bus.request` (both experimental).
- A package may only provide in its own `{id}.*` namespace.
- A duplicate provider for the same method is refused.
- A missing provider, a timeout, or a handler error returns a structured error
  (`sdk.interop.provider_missing` / `provider_timeout` / `response_invalid`).
>>>>>>> origin/main
