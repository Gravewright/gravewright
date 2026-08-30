# Dice Roller example

A small `addon` that demonstrates:

- a command exported through `get`;
- input validation;
- semantic diagnostics;
- inferred API registration.

Copy the directory into `modules/dice-roller/`, add `"dice-roller": "active"` to `gravewright.modules.json`, and run:

```bash
grave module build modules/dice-roller --check
npm run types:sync
npm run typecheck
grave doctor
```

Consumers with a declared dependency can call:

```ts
const dice = ctx.use("dice-roller");
const result = dice.get("roll")(20, "Player");
```
