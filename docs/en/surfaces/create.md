# `create`

`create(context)` constructs one runtime instance when the module becomes active.

```ts
create(ctx) {
  const cache = new Map<string, unknown>();
  return {
    clear() { cache.clear(); },
    size() { return cache.size; },
  };
}
```

Private state belongs in the closure. The returned object may be large, but only declared exports and composition values are visible outside the module.

Guidelines:

- Delay connections, timers, and listeners until activation or an explicit command.
- Throwing from `create()` fails activation and triggers composition rollback.
- A later reactivation creates a new instance; volatile state is not preserved.
- Do not retain the raw context as an escape hatch for undeclared dependencies.

## Instance isolation example

```ts
create(ctx) {
  let connected = false;
  const pending = new Map<string, Promise<unknown>>();

  return {
    async connect() {
      if (connected) return;
      connected = true;
      ctx.diagnostic.record({ event: "storage.connected", actor: "Backend", action: "Connect storage", status: "success" });
    },
    pendingCount() { return pending.size; },
  };
}
```

`connected` and `pending` are private. Consumers can only call names listed in `exports`. After disable and reactivation, both values return to their initial state because a fresh instance is created.
