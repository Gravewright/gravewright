# Lifecycle and state

A module moves through explicit host and kernel stages:

```text
discovered → validated → loaded → instantiated → composed → active
                                      │                       │
                                      └──── rollback ◄────────┘
                                                              │
                                               dispose ◄── disabled
```

- Discovery finds module directories with `manifest.json`.
- Loading validates static metadata and dependency order.
- Instantiation calls `create()` only for active modules.
- `ctx.onDispose()` registers cleanup as soon as an external resource exists.
- Composition registers middleware, routes, and slots.
- Server start happens after successful composition.
- Disable executes disposers in reverse order.

`gravewright.modules.json` stores `active` or `disabled`; missing entries default to disabled. Installation changes physical presence only and does not activate a module.

`kernel.plan()` validates dependencies, capabilities, singleton rules, routes, and visual slots before any factory executes. If `create()` fails, registered resources are disposed in reverse order. `kernel.shutdown()` stops the server, then releases composition and resources in reverse topological order. Reactivation creates a fresh instance.

```ts
create(ctx) {
  const timer = setInterval(runJob, 1_000);
  ctx.onDispose(() => clearInterval(timer));
  return { read, write, stat };
}
```

## Rollback example

Suppose activation registers two values and the second registrar fails:

```text
1. middleware /game registered       ✓
2. route /game registration fails    ✗
3. middleware disposer runs          ↩
4. module remains disabled
```

Disposers should therefore be idempotent and tolerate partial external cleanup:

```ts
return async () => {
  if (!subscription) return;
  const current = subscription;
  subscription = undefined;
  await current.close();
};
```
