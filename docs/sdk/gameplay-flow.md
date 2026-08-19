# Gameplay flow

A gameplay flow answers *who acts, and when*. It orders participants through named
phases and records what each of them committed to, without assuming anything about
the game being played.

It is not a combat tracker. A flow has no dice, no d20, no initiative score and no
hit points; it never reads a ruleset. A systemless campaign can run an entire
session on it, and a ruleset that wants initiative can build that on top.

## Definition and instance

A **definition** names the phases and the turn model. Register it with
`sdk.gameplay.flows.register`.

```js
await sdk.gameplay.flows.register({
  id: "infiltration",
  schemaVersion: 1,
  turnModel: "SIMULTANEOUS",
  phases: [
    { id: "BRIEFING", label: "Briefing", submissionPolicy: "all" },
    { id: "PLANNING", label: "Planning", submissionPolicy: "all" },
    { id: "RESOLUTION", label: "Resolution", submissionPolicy: "all" },
  ],
});
```

An **instance** is one run, started by a GM with `sdk.gameplay.flows.start` and an
explicit participant list. Read it with `sdk.gameplay.flows.get` or
`sdk.gameplay.flows.list`.

## Turn models

- **`SIMULTANEOUS`** — every participant commits, and the phase reveals once the
  last one has. This is the secret-commitment model.
- **`SEQUENTIAL`** — one participant is active at a time, in participant order.
- **`PHASED`** — participants act within a phase without a per-turn active seat.

## Secret commitment and reveal

Under `SIMULTANEOUS`, `sdk.gameplay.flows.submit` records a participant's choice and
the flow keeps it private. Until every participant has submitted, each of them sees
only their own entry in `submissions`, and `revealed` is `false`. When the last
submission lands, the flow reveals and every participant sees the whole set at once.

The GM sees submissions throughout, which is what makes them able to narrate.

A submission is a commitment: submitting twice in the same phase is refused, and
`expectedVersion` makes concurrent submissions safe. Advancing to the next phase with
`sdk.gameplay.flows.advance` clears the submissions and starts the next round of
commitment.

## Authority

Only a GM starts a flow or advances its phase. Only a listed participant may submit,
and only for themselves. A user who is not a participant cannot read the flow at all.

## Lifecycle

Flow state is persisted, not held in a client. A participant who reloads sees the
current phase and their own standing commitment; a participant who joins late sees
the phase as it is now. A phase may carry `deadlineSeconds`, in which case core
advances the flow when the deadline passes rather than waiting forever.

Phases cycle: advancing past the last phase returns to the first and increments the
round and cycle counters. A flow expresses completion by reaching a phase that means
completion in your design — commonly a final phase named `COMPLETE`.

## Common errors

| Code | Cause |
|---|---|
| `VALIDATION_FAILED` | Malformed definition, unknown participant, or a value that is not JSON-safe. |
| `NOT_FOUND` | The flow does not exist, or the caller is not a participant or GM. |
| `ALREADY_SUBMITTED` | This participant already committed in this phase. |
| `NOT_ACTIVE_PARTICIPANT` | Sequential model, and it is not this participant's turn. |
| `STALE_VERSION` | `expectedVersion` no longer matches. |

## What this API does not expose

No initiative, no automatic turn timers a package controls, no way to submit for
another user, and no access to another participant's commitment before reveal.
