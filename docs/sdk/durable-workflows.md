# Durable workflows

A durable workflow coordinates a multi-step authoritative process that may need to
wait — for a player's decision, or for a deadline — and must still be correct after a
browser reload, a package reload, or a server restart.

It is deliberately not a script. A workflow is *data*: every executable step is
chosen from a closed set, and all suspension state lives in core. A package
describes the process once and never holds the pending state itself.

## Definition and instance

A **definition** is the shape of the process: an id, a schema version, an ordered
list of steps, and the bounds it accepts (`maxDuration`, `maxSteps`). Register it
with `sdk.workflows.register`.

An **instance** is one run of that definition, started with `sdk.workflows.start`.
Starting is idempotent through `idempotencyKey`: the same key returns the same
instance rather than starting a second one. An instance freezes the definition it
started with, so re-registering a changed definition never rewrites a run already in
progress.

Read instances with `sdk.workflows.get` and `sdk.workflows.list`; stop one early with
`sdk.workflows.cancel`.

## Steps

| Step | Meaning |
|---|---|
| `ACTION` | Execute one of your own registered actions. |
| `INTERACTION` | Ask a user to decide, and suspend until they answer. |
| `WAIT_UNTIL` | Suspend until an absolute time or for a number of seconds. |
| `BRANCH` | Compare a context key to a value and jump to one of two steps. |
| `SET` | Write a literal into workflow context. |
| `COMPLETE` | Finish successfully. |
| `FAIL` | Finish unsuccessfully with a reason. |

`BRANCH` may only jump forward, so a definition cannot loop.

## Deciding on a player's answer

An `INTERACTION` step may declare an optional `resultKey`. When the interaction
completes, core writes the recipient's resolved response *value* — never the
interaction object — into `context[resultKey]`, and the ordinary `BRANCH` step reads
it like any other key.

```js
await sdk.workflows.register({
  id: "breach-response",
  schemaVersion: 1,
  maxDuration: 3600,
  steps: [
    { type: "ACTION", action: "my-package:alarm.raise@1", input: { actorId } },
    {
      type: "INTERACTION",
      resultKey: "response",
      request: {
        recipients: [operativeUserId],
        title: "Security response",
        text: "Suppress the alarm?",
        responseSchema: { type: "single-choice", choices: [
          { id: "SUPPRESS", label: "Suppress" },
          { id: "IGNORE", label: "Let it run" },
        ] },
        deadline: Math.floor(Date.now() / 1000) + 900,
      },
    },
    { type: "BRANCH", key: "response", equals: "SUPPRESS", then: 3, else: 4 },
    { type: "ACTION", action: "my-package:alarm.suppress@1", input: { actorId } },
    { type: "COMPLETE", reason: "resolved" },
  ],
});

await sdk.workflows.start({
  definitionId: "breach-response",
  sceneId,
  idempotencyKey: `breach:${sceneId}`,
});
```

Because a scalar branch cannot represent disagreement, `resultKey` is only valid on a
request with exactly one recipient. The key must be a workflow-local identifier and
may not claim the runtime slots `input`, `lastResult` or `interaction`.

## Authority

A workflow acts as the user who started it, never as the recipient of a question.
Knowing who was asked confers nothing: the answer is only accepted from the
authenticated recipient, and every `ACTION` step is authorized against the starting
user's current authority at the moment it runs. A workflow is visible to its owner
and to the GM.

## Lifecycle and recovery

Suspension is persisted, so a waiting workflow is not a promise held in a browser.
A player who reloads still sees the pending decision; a server that restarts resumes
from the step it stopped at. Each step records a receipt, so a replayed completion
advances the run once and no action executes twice.

Cancellation, expiry and provider failure never fabricate an answer: `resultKey`
simply stays unset, and a definition that must handle refusal branches on the absent
key. If the providing package is unloaded, its running instances are closed rather
than left orphaned.

## Common errors

| Code | Cause |
|---|---|
| `VALIDATION_FAILED` | A step outside the closed set, a backward branch, an invalid `resultKey`, or a bound exceeded. |
| `NOT_FOUND` | Unknown definition, or an instance the caller may not see. |
| `PERMISSION_DENIED` | The package or the user lacks authority for the operation. |
| `STALE_VERSION` | `expectedVersion` no longer matches on cancel. |

## What this API does not expose

No callbacks, no arbitrary code, no package-owned timers, and no way to observe or
mutate another package's workflows.
