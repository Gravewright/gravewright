# Server contract

`server` is the only structurally required kind. Exactly one active module must implement it.

Required exports:

- `start()` — open the host listener after composition finishes.
- `stop()` — close resources cleanly.
- `route(mount, handler)` — register a final handler and return a disposer.
- `middleware(mount, handler)` — register chain middleware and return a disposer.
- `slot(name, value)` — register an extension value and return a disposer.

The kernel validates that every required export is declared under `get` and is a function. It does not require Express or know how requests are transported.

`start()` is awaited exactly once after middleware, routes, and slots are composed. The active server cannot be disabled while the kernel is running.

## Minimal registrar behavior

```ts
route(mount: string, handler: RouteHandler) {
  let active = true;
  adapter.register(mount, async (request, response, next) => {
    if (!active) return next();
    await handler(request, response);
  });
  return () => { active = false; };
}
```

The returned disposer is mandatory. The kernel uses it for failed activation rollback and module disable. A registrar that returns nothing violates the contract even if registration initially succeeds.

```ts
async start() { listener = await adapter.listen({ host: "127.0.0.1", port: 3000 }); }
async stop() { await listener?.close(); listener = undefined; }
```
