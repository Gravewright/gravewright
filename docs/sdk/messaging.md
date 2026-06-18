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

Under the Alpha 2.0.0 SDK Freeze, enforcement is **strict**: all four directions
are hard-enforced at runtime — `publish`→`emits`, `subscribe`→`listens`,
`provide`→`provides`, and `request`→`requires`. Runtime payload/response schema
validation against the declared schemas is tracked as post-freeze hardening
toward LTS 1.
