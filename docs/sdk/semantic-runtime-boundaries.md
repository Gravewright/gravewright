# Semantic runtime boundaries

The SDK exposes intent, not machinery. Each runtime domain below accepts a typed
description of what should happen and leaves core to decide whether it may, when it
happens, and who observes it. Knowing where those lines fall is usually enough to
predict what an API will and will not give you.

## Drag and drop is a protocol, not a DOM event

`sdk.ui.dragDrop` describes what was carried and where it landed as content
references and a world position. It is not `DragEvent`, `DataTransfer`, a selector,
or any other DOM handle. Core re-resolves the reference and the target immediately
before running the registered action bound to that target, so a gesture can never
assert an outcome the acting user could not have performed directly.

## Audio is a core domain, not an element

Core owns playback state, audience, lifecycle and the reconnect projection.
`sdk.audio` never hands back an `HTMLAudioElement`, a WebAudio node, a media URL, or
authority over a listener's personal volume.

## Navigation changes a viewpoint, nothing else

`sdk.navigation.scene` moves which scene a user is looking at. It does not move,
create or mutate a token, and it is not a presentation.

## Input separates meaning from binding

A package declares what a command means; the user owns which key invokes it. Core
keeps the raw keyboard and pointer listeners, protected shortcuts, text-input
suppression, long-press thresholds, pointer cancellation, and multi-pointer conflict
resolution.

## Neighbouring domains that are deliberately distinct

| This | is not | because |
|---|---|---|
| Presentation | Navigation | one shows content, the other changes scene context |
| Directed Interaction | Presentation | one requests a decision and waits for an answer |
| Durable Workflow | Semantic Timeline | one waits for decisions, the other runs to a clock |
| Token Transfer | Scene Navigation | one moves a token, the other moves a view |
| Scene Zone | World Object | one is a region, the other is an addressable thing |
| Sound | Playback | one is reusable content, the other is a running instance |

Scene world objects remain semantic resources with data and interactions. They are
not renderer objects, and no API returns a drawing handle for one.
