# `use`

`ctx.use(name)` returns a `ModuleRef` for a dependency declared by exact name.

```ts
dependencies: { "dice-roller": "^1.0.0" },
create(ctx) {
  const dice = ctx.use("dice-roller");
  return { attack: () => dice.get("roll")(20) };
}
```

The reference is a logical, revocable handle—not the dependency instance itself. Every `get()` resolves the currently active instance.

The kernel rejects use when:

- the dependency is not declared;
- it is missing or disabled;
- its version does not satisfy the declared range;
- the requested export is not permitted.

Do not extract and retain values if you require revocation guarantees: JavaScript values already obtained cannot be revoked.

## Complete producer and consumer

The producer publishes `roll`:

```ts
// modules/dice-roller/index.ts
export default defineModule({
  name: "dice-roller", kind: "addon", provider: "community", version: "1.2.0",
  exports: { get: ["roll"] },
  create(_ctx) { return {
    read(_resource: string) { return undefined; }, write(_resource: string, _value: unknown) {}, stat() { return { ready: true }; },
    roll: (sides: number) => Math.floor(Math.random() * sides) + 1,
  }; },
});
```

The consumer declares the exact dependency before requesting it:

```ts
// modules/combat/index.ts
export default defineModule({
  name: "combat", kind: "ruleset", provider: "community", version: "1.0.0",
  dependencies: { "dice-roller": "^1.2.0" },
  exports: { get: ["attack"] },
  create(ctx) {
    const dice = ctx.use("dice-roller");
    return {
      read(_resource: string) { return undefined; }, write(_resource: string, _value: unknown) {}, stat() { return { ready: true }; },
      attack: () => dice.get("roll")(20),
    };
  },
});
```

Removing `dependencies` makes activation fail even if `dice-roller` is installed. Declaring `^2.0.0` also fails while the installed version is `1.2.0`.
