# Semantic timelines

A semantic timeline says *what should happen, and how long after the start*. It is
the way to compose a sequence of existing semantic effects — a sound, a title card, a
light, a shader, a particle emitter — into one authored moment.

Core owns the clock. A package states offsets; it never runs a timer, and it cannot
claim that something happened at a time core did not agree to.

## Timeline is not workflow

They look similar and solve opposite problems.

| | Timeline | Durable workflow |
|---|---|---|
| Waits for | a clock | a decision or a deadline |
| Branches | never | on context, including a player's answer |
| Typical use | a cinematic entrance, an alarm sequence, an environment transition | an approval, a negotiation, a multi-step procedure |

If the sequence can change shape depending on what someone chooses, it is a workflow.

## Definition and instance

A **definition** is an id, a schema version, and a list of cues. Each cue carries a
`cueId`, an `offsetMs` from the start, a cue type, and that type's parameters. Core
derives `durationMs` from the last cue; a package does not assert it.

```js
await sdk.timelines.register({
  id: "alarm-cascade",
  schemaVersion: 1,
  cues: [
    { cueId: "siren", offsetMs: 0, type: "AUDIO_PLAY", parameters: {
        asset: { kind: "library-asset", id: alarmAssetId }, channel: "sfx",
        gain: 0.9, audience: { kind: "campaign" }, sceneId } },
    { cueId: "warning", offsetMs: 0, type: "PRESENTATION_SHOW", parameters: {
        mode: "title-card", content: { title: "Alarm", text: "Security is responding." },
        audience: { kind: "campaign" } } },
    { cueId: "flare", offsetMs: 400, type: "LIGHT_CREATE", parameters: {
        x: 700, y: 350, bright_radius: 120, dim_radius: 320, color: "#ff2f3a" } },
    { cueId: "haze", offsetMs: 900, type: "PARTICLE_CREATE", parameters: {
        x: 700, y: 350, kind: "ember", density: 0.6, scale: 4 } },
  ],
});

await sdk.timelines.start({
  definitionId: "alarm-cascade",
  sceneId,
  audience: { kind: "campaign" },
  idempotencyKey: `alarm-cascade:${sceneId}`,
});
```

An **instance** is one run. Read it with `sdk.timelines.get` or
`sdk.timelines.list`, and stop it with `sdk.timelines.cancel`.

## Cue types

`ACTION`, `AUDIO_PLAY`, `PRESENTATION_SHOW`, `LIGHT_CREATE`, `SHADER_PRESET`,
`PARTICLE_CREATE` and `NAVIGATION`. Each delegates to the same authoritative service
the equivalent direct call would use, so a timeline can never do something the
package could not have done itself.

An `ACTION` cue may only reference the running package's own registered actions. A
cue may declare a `cleanupAction`, likewise its own, which core runs for cues that
already fired when the timeline is cancelled.

## Authoritative start time and late join

An instance records the moment it started. A client that connects afterwards is
projected to the correct point: cues already due are treated as executed rather than
replayed from the beginning. This is why offsets, not local timers, are the unit — a
late joiner sees a coherent scene instead of a restarted sequence.

Starting is idempotent through `idempotencyKey`, so a retry or a second client
attempting the same cascade returns the existing instance.

## Authority

The audience follows the same rule as everywhere else: a GM may address the campaign
or named users, and a player may address only themselves. Cue parameters are
validated by the owning domain, so an invalid shader preset or an out-of-range
particle is refused rather than partially applied.

## Lifecycle

Cue execution is receipted, so recovery after a restart does not re-fire a cue that
already ran. Cancelling runs any declared cleanup for the cues that fired. Unloading
the providing package closes its running timelines.

## Common errors

| Code | Cause |
|---|---|
| `VALIDATION_FAILED` | Unknown cue type, duplicate `cueId`, offset beyond bounds, foreign action reference, or invalid cue parameters. |
| `NOT_FOUND` | Unknown definition, or an instance the caller may not see. |
| `PERMISSION_DENIED` | The audience is wider than the caller may address. |

## What this API does not expose

No raw renderer calls, no GLSL, no package-owned timers, and no way to schedule
another package's actions.
