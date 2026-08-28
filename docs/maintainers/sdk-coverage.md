# Core and SDK 1 Coverage Audit

Audit date: 2026-08-27. This document compares the user-facing domain services
implemented by the Gravewright core with the public, capability-gated browser
SDK. It does not treat every internal service as a candidate public API:
administration, persistence, transport, rendering, and package installation
remain core-owned by design.

Implementation status: priorities 0–2 were completed on 2026-08-14. Optional
asset mutation, chat deletion, bulk light/effect operations, and Priority 3 GM
automation remain deliberately deferred.

## Current coverage

The SDK registry, generated capability tables, browser runtime, server command
bridge, and their contract tests agree on the currently exposed surface.

| Domain | Current public coverage | Assessment |
|---|---|---|
| Actors | Read/list, CRUD, validated actor-data patching | Good |
| Items | Read/list, core-field CRUD and validated item-data patching | Good |
| Tokens | Read/list, CRUD and movement | Good; HP and conditions exist indirectly through rule actions |
| Scenes | Read/list/active, geometry, effects, fog and image placements | Good for gameplay tools |
| Combat | State, explicit lifecycle, turns/rounds, holding, interruption/resume, flags and initiative | Good |
| Chat and dice | Send/read messages, authoritative dice, roll intents, constrained roll actions and rerolls | Good |
| Rules | Validate and execute a bounded semantic action graph | Good |
| Cards | State, shuffle, reset, draw, reveal, discard and scene placement | Good |
| PDFs | Read, viewer navigation and complete annotation CRUD | Good |
| Assets | Permission-filtered listing | Partial |
| Content | Package content packs and campaign import flow | Good for declarative content |
| UI and sheets | Slots, modals, toast, HTML sheets, controllers and helpers | Good |
| Package runtime | Settings, scoped SQLite, events, inter-package bus and localization | Good |
| Journals and handouts | Runtime journal CRUD and transient presentation | Good |
| Fog and scene images | Bounded fog operations and authorized placements | Good |
| User presentation | Campaign-visible bounded user colors through read-only projection | Good |

## Implemented additions

### Beta 4 compatible additions

- `rolls.actions` registers bounded actions on roll messages without exposing a
  general chat hook.
- `rolls.reroll` replays a persisted roll through its authoritative ruleset
  policy rather than trusting a replacement formula from the browser.
- `combat.manage` includes holding, turn interruption and authoritative resume.
- `users.presentation.read` exposes only the public presentation projection of
  users visible in the active campaign.

### Priority 0: complete cards

The SDK exposes reveal, discard, play-to-scene, placement update and placement
discard through `cards.manage`, with server-side permission checks:

```js
sdk.cards.reveal(cardIds)
sdk.cards.discard(cardIds)
sdk.cards.play(cardId, { sceneId, x, y, rotation, scale, faceUp })
sdk.cards.updatePlacement(placementId, patch)
sdk.cards.discardPlacement(placementId)
```

Deck-definition creation, deck instantiation, and deletion should be exposed
only if runtime-authored card games are an explicit goal. Otherwise deck
definitions should remain declarative package content and GM configuration.

### Priority 1: closed gameplay asymmetries

- `sdk.items.patchData(itemId, patch)` is symmetric with actor data writes.
- Combat exposes initiative rolling, round advancement and safe flags.
- Journals provide read/list and validated CRUD; handout presentation remains
  transient and respects the application feature flag.
- PDF annotations provide update/delete in addition to list/create, with the
  core authoritative for regions, pages, ownership and document visibility.
- Token HP and conditions are supported semantic rule actions. Add
  direct convenience methods only if packages need them outside action graphs.

### Priority 2: scene-tool expansion delivered

- Fog state, enable/disable, reset and bounded paint operations.
- Scene-image placement, update and removal for already authorized assets.
- Advanced wall operations: split, node movement and bounded bulk edits.
- Optional bounded bulk operations for lights and effects.
- Asset upload/create/move/delete if package-driven asset workflows are desired.
- Chat message deletion only for the sender or an authorized GM; bulk clear
  should remain an administrative operation.

### Priority 3: optional GM automation

Scene creation, metadata update, activation, grouping, map upload and retiling
are useful for campaign-management addons, but have larger storage and denial of
service implications. If exposed, they need a distinct GM-only capability,
strict payload/size limits, progress reporting, and audit events.

## Intentionally private

The following core surfaces should not be mirrored into SDK 1:

- authentication, sessions, campaign membership, bans and invitations;
- ownership and permission override;
- backup, restore, snapshots, imports and administrative audit history;
- package install, enable, removal and campaign activation;
- raw database, filesystem, network, HTTP route and WebSocket access;
- renderer internals, tile/chunk scheduling, predictive prefetch and caches;
- direct repository access and unrestricted bulk mutation.

Packages should express gameplay intent through validated commands. The server
must continue to enforce campaign membership, role, resource visibility,
ownership, capability gates, payload limits, and optimistic version checks.

## Verification status

The delivered Priority 0–2 surface is covered by registry/bridge contract tests,
HTTP authorization tests, cross-campaign mutation tests and the core domain
suite. Optional GM automation remains deferred until a separate threat and
resource-limit review.

Every addition must update the canonical capability registry, generated tables,
browser runtime, server bridge, DTOs, English/PT-BR reference docs, fixtures,
permission tests, and end-to-end package tests in the same change.
