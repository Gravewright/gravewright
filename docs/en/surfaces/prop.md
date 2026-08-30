# `prop`

`exports.prop` exposes a property through both `get()` and `set()`.

```ts
exports: { prop: ["status"] }
```

Use it only when shared property semantics are genuinely part of the contract. It is suitable for small observable configuration values, not internal stores or complex aggregates.

Because writes use the deprecated generic `set()` path, explicit commands are preferred for new APIs. A command can preserve invariants and provide a stable migration path when representation changes.

## Property example

```ts
exports: { prop: ["debug"] },
create(_ctx) {
  return { debug: false };
}
```

```ts
const logger = ctx.use("logger");
const enabled = logger.get("debug");
logger.set("debug", true);
```

This is acceptable for a simple boolean with no invariants. If enabling debug requires authorization, persistence, cleanup, or diagnostics, publish `enableDebug()` and `disableDebug()` commands instead.
