# `set` (deprecated)

`ref.set(name, value)` writes to a name declared in `exports.set` or `exports.prop`.

```ts
ctx.use("theme").set("mode", "dark");
```

This surface remains for compatibility but is deprecated because generic cross-module mutation exposes shared mutable state and bypasses domain-specific validation.

Prefer:

```ts
ctx.use("theme").get("setMode")("dark");
```

The owning module can then validate the value, emit diagnostics, persist it, or reject the transition. New modules should normally leave `exports.set` empty.

## Legacy versus command API

Avoid a generic writable field:

```ts
exports: { set: ["volume"] },
create(_ctx) { return { volume: 50 }; }
```

Prefer an explicit command:

```ts
exports: { get: ["setVolume", "volume"] },
create(ctx) {
  let current = 50;
  return {
    volume: () => current,
    setVolume(next: number) {
      if (!Number.isInteger(next) || next < 0 || next > 100) throw new RangeError("volume must be 0..100");
      current = next;
      ctx.diagnostic.record({ event: "audio.volume", actor: "User", action: "Change volume", status: "success", details: { volume: next } });
    },
  };
}
```

The command owns validation and auditing; callers cannot place the module in an invalid state.
