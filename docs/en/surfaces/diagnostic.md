# Diagnostics

`ctx.diagnostic.record()` emits an opt-in semantic audit event.

```ts
ctx.diagnostic.record({
  event: "dice.roll",
  actor: "Player",
  action: "Roll d20",
  status: "success",
  details: { sides: 20, result: 10 },
});
```

`status` reports technical execution success or failure—not success inside the RPG rules. The host records events only when started with `grave run --diagnostic`.

Diagnostics are opt-in, best-effort observability. Without a configured
reporter, `record()` is an intentional no-op and never changes module behavior.
Do not use diagnostics as a control channel or error-handling mechanism: fatal
failures must still be expressed through an explicit throw or return value.

Use public actor labels and semantic actions. Never emit tokens, session identifiers, private filesystem paths, full request bodies, secrets, or personal data. Unsafe detail fields are filtered, but authors must still minimize data at the source.

## Success and failure

```ts
try {
  const result = roll(20);
  ctx.diagnostic.record({ event: "dice.roll", actor: "Player", action: "Roll d20", status: "success", details: { result } });
  return result;
} catch {
  ctx.diagnostic.record({ event: "dice.roll", actor: "Player", action: "Roll d20", status: "failure", reason: "Dice service unavailable" });
  throw new Error("roll failed");
}
```

Good detail: `{ sides: 20, result: 10 }`. Bad detail: `{ token, sessionId, requestBody, absolutePath }`.
