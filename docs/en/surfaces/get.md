# `get`

`ref.get(name)` reads a value listed in `exports.get`.

```ts
const roll = ctx.use("dice-roller").get("roll");
const result = roll(20);
```

Functions are ordinary values: `get()` authorizes and returns the function, then the caller invokes it. The function still operates on the dependency's original runtime instance.

`get()` fails if the module is disabled, the instance is unavailable, or the name was not declared. TypeScript limits names through `ModuleRegistry`; the kernel repeats authorization at runtime.

Use command-shaped functions for mutations so validation, audit, and invariants stay inside the owning module.

## Values and commands

```ts
// Producer
exports: { get: ["systemName", "roll"] },
create(_ctx) {
  return {
    systemName: "D20 Basic",
    roll(sides: number) {
      if (!Number.isInteger(sides) || sides < 2) throw new RangeError("invalid die");
      return Math.floor(Math.random() * sides) + 1;
    },
  };
}
```

```ts
// Consumer
const dice = ctx.use("dice-roller");
const name = dice.get("systemName"); // string
const roll = dice.get("roll");       // (sides: number) => number
const result = roll(20);              // number
```

`dice.get("secretSeed")` is rejected at compile time and runtime when `secretSeed` is not exported, even if it exists privately in the producer.
