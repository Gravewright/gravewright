# Gravewright Release Notes

This is the single canonical release-history document for Gravewright. It
combines the current-release overview, compatibility information, upgrade
guidance, notable changes, fixes, migrations, and historical Alpha notes.

The project is currently in Beta. SDK 1 RC 1 is the frozen public compatibility
candidate; packages continue to declare `sdkVersion: "1"`.

## Current release at a glance

### Gravewright v1.0.0-beta.4

Beta 4 consolidates the VTT runtime, interface, gameplay automation and
low-end-device performance work while preserving the frozen SDK 1 contract.

Highlights:

- Reworked Gravewright Mode with dockable and detachable windows, compact
  settings, a system tray, lazy directories, and consistent panel dimensions.
- Roll tables, explicit combat start, holding/interruption/resume state,
  authoritative rerolls, and constrained roll-message actions.
- Runtime cleanup, idle suspension, render batching, asset versioning and safer
  transitions between the dashboard and a running table.
- Capability-gated public user presentation colors and updated generated SDK
  reference, declarations, DTOs and capability documentation.
- Expanded automated coverage for multiplayer projection, semantic drag/drop,
  package isolation, resource visibility and low-end performance behavior.

Versions:

- Product: `1.0.0-beta.4`
- Python package target: `1.0.0b4`
- Public extension line: `SDK 1 RC 1` (`sdkVersion: "1"`)

Benchmark methodology and workload boundaries are documented in
[docs/performance.md](docs/performance.md).

## Upgrade guidance

Create and verify a complete backup before upgrading an installation that
contains data you care about:

```bash
grave backup -o pre-upgrade.zip --include-assets --include-packages --verify
grave restore pre-upgrade.zip --dry-run
```

Then apply migrations, refresh package snapshots, run diagnostics, and start:

```bash
grave db upgrade
grave package update all
grave doctor
grave run --open
```

Alpha releases did not guarantee an automatic upgrade path for existing tables.
Scripted SDK packages execute trusted browser JavaScript and should only be
installed from trusted authors. Custom shaders execute on each connected user's
GPU and may cause performance or rendering failures when authored incorrectly.

The `v3.0.2-alpha` shader hotfix had no database migration or public SDK/ABI
change. Its shader lifecycle harness covered continuous animation, static idle,
repeated edits, disposal, deletion, and invalid-source recovery; Windows x64
artifacts were produced from `grave.spec`.

Report issues with exact reproduction steps, sanitized server/browser logs,
relevant campaign and map dimensions, player count, and GPU/browser information
for rendering problems.

## Detailed release history

## v1.0.0-beta.4

### VTT and interface

- Reordered the primary directories to Chat, Scenes, Actors, Journals, Combat,
  Items, Compendiums and Settings.
- Added Qt-inspired dock/undock behavior in Gravewright Mode while retaining
  Classic Mode dimensions and behavior.
- Reorganized General, System and Modules settings into compact, consistent
  two-pane layouts and moved connected users and audio into the system tray.
- Added per-user presentation colors and compact connected-user controls.
- Added lazy resource directories and deterministic scene-directory refreshes.
- Added journal roll tables with weighted, enabled and non-repeating results.

### Runtime and performance

- Reduced repeated requests, listener duplication and unnecessary repaint work.
- Added idle runtime suspension, render batching and versioned asset-cache
  invalidation, and tightened cleanup after rolls and table transitions.
- Hardened map upload, adaptive raster selection, free token movement and grid
  calibration, including fractional grid sizes and offsets.
- Improved low-end browser behavior for tokens, popups, audio and scene changes.

### Gameplay and combat

- Combatants no longer receive initiative merely by joining the tracker; the GM
  starts combat explicitly.
- Added persisted holding, turn interruption and resume state.
- Added defeated-token presentation in the scene and combat order.
- Added authoritative threshold damage, attack classification, condition effects,
  target filtering and roll rerolls.

### SDK 1

- Added stable `rolls.actions` and `rolls.reroll` capabilities through
  `sdk.rolls.actions.register(...)` and `sdk.rolls.reroll(...)`.
- Extended `combat.manage` with `sdk.combat.interruptTurn(...)`,
  `sdk.combat.resumeTurn()` and `sdk.combat.setHolding(...)`.
- Added `users.presentation.read` with `sdk.users.presentation.get(...)` and
  `sdk.users.presentation.list()` for bounded campaign-visible user colors.
- Updated generated JSON, TypeScript declarations, method/DTO references,
  capability descriptions and English, Portuguese and Spanish indexes.
- The compatibility line remains SDK 1 RC 1 and package manifests continue to
  declare `sdkVersion: "1"`; no new SDK version was introduced.

### Reliability

- Isolated package/ruleset fixtures from core CI and expanded multiplayer E2E
  coverage for lazy directories, permissions and semantic drag/drop.
- Fixed scene refresh races, duplicate attack requests, reroll routing and
  stale window/panel state exposed by the interface refactor.

## v1.0.0-beta.3

- Certified CLI ↔ SDK 1 RC 1 parity across scaffold, install, validation,
  activation, diagnostics, and package lifecycle.
- Added Marketplace v2 Core and package distribution channels with
  `core`/`community`/`partner` provenance.
- Updated package authoring and AI workflows around canonical JSON diagnostics.
- Kept runtime and public SDK contracts unchanged by the documentation pass.

## v1.0.0-beta.2

- Completed SDK 1 RC 1 input, semantic runtime, scene, audio, workflow, and
  generated-contract coverage.
- Added the RC 1 semantic snapshot and compatibility classifier.
- Promoted the product version from Beta 1 while preserving `sdkVersion: "1"`.

## v1.0.0-beta.1: 2026-08-15

First Beta release. This section consolidates every feature, behavioural change,
performance improvement, migration, and fix added after `v3.0.2-alpha`.

### Audit hardening

- Bound ID-addressed SDK mutations to the campaign in which the package was authorized.
- Made journal updates non-destructive for omitted fields.
- Centralized targeted handout delivery and enforced its feature flag for SDK calls.
- Added HTTP regression coverage for cross-campaign writes and journal patch semantics.
- Made the latest schema migrations reentrant for legacy and pre-created databases.
- Restored Windows launcher compatibility and bundled-package installation checks.
- Improved CLI discoverability with a zero-argument quick start, workflow examples,
  typo suggestions, clean cancellation, broken-pipe handling and `--no-color`.
- Re-audited the SDK registry, browser runtime, server bridge and generated references.
- Added strong opt-in `grave run --diagnostics`: local redacted rotating JSONL,
  periodic full metric snapshots, explicit retention and no network upload.
- Made diagnostics issue-safe by default with per-run identifier pseudonyms,
  path/network redaction and preservation of older private captures.

### Added

- Completed the SDK 1 gameplay coverage plan with authoritative card reveal,
  discard, scene play and placement operations; item-data writes; expanded
  combat control; journal CRUD and transient handout presentation; PDF
  annotation update/delete; fog operations; scene-image placement; and bounded
  advanced wall editing. Administrative, storage and renderer internals remain
  private by design.

- Added GM-guided predictive tile prefetch for one GM and multiple players. GM
  viewport intent is distributed as bounded, expiring hints; clients consume it
  only when visible work permits and cancel speculative work under pressure.
- Added configurable prefetch policies (`simple`, `exponential`, `sigmoid`,
  `sigmoid_derivative`, and `utility_per_byte`), distance, queue-byte, TTL,
  idle-only, and visible-backlog limits.
- Added versioned virtual-raster metadata, level-of-detail tile/chunk addressing,
  tile index versions, and scene format versions (migration `0044`).
- Added automatic adaptive raster granularity. Import now chooses a safe raster
  policy from source dimensions and workload rather than asking the GM to tune
  implementation-specific map controls; the decision and policy version are
  persisted by migration `0045`.
- Added SDK 1 runtime APIs and capabilities for permissions, actors, actor data,
  items, tokens, scene reads and geometry, effects, UI slots, chat, combat,
  rules actions, cards, and semantic event subscriptions.
- Added strict runtime authorization combining package declarations, campaign
  activation, user authority, resource visibility, bounded payloads, and public
  DTOs that exclude private persistence fields.
- Added SDK package diagnostics for undeclared API use, unused capabilities, and
  forbidden direct access to internal `/game/*` routes.
- Added SDK 1 PDF support: `pdf.get`, `pdf.metadata`, viewer open/navigation,
  search/current-page operations, anchors, and separate read/viewer capability
  gates.
- Added campaign PDF annotations with list/create operations, page/region/text
  validation, visibility checks, independent read/write capabilities, and
  migration `0046`.
- Added SDK asset-package import and generic package content access so bundled
  rulesets do not depend on private application routes.
- Added campaign export/import with selective resources, package state,
  relationship remapping, validation, security exclusions, and a reusable
  canonical campaign-state snapshot representation.
- Added token clipboard operations and keyboard stepping, plus consistent
  folder initial-state and item-folder deletion choices.
- Added renderer resource sharing, spatial visibility diagnostics, logical GPU
  accounting, batched token drawing, shared animated texture sources, and a
  fast-sprite path for dense homogeneous token populations.
- Added headed/headless Playwright performance suites for the 100 Dragons
  renderer, GPU-confirmed scaling and knee discovery, six-client
  Andromeda/5K map prefetch, and the real-campaign composite workload.

### Changed

- Reworked scene streaming around visible-first scheduling, predictive queues,
  cancellation, cache-aware tile manifests, and explicit diagnostics rather
  than treating every frame gap as application render time.
- Reworked map upload and image decoding for very large rasters, staged
  retiling, adaptive pyramids, safe pixel/tile bounds, and platform packaging of
  the required image runtime.
- Optimized Pixi board rendering, token layers, tile layers, lighting, scene
  images, selection, measurements, render scheduling, and camera-driven
  streaming to avoid work when the viewport or scene is unchanged.
- Expanded campaign snapshots to cover the complete persistent campaign state,
  physical files, packages, and newer scene metadata while continuing to
  exclude global accounts, sessions, audit history, and snapshot history.
- Generalized the bundled rulesets to use SDK 1 for core resources and content;
  SDK naming was normalized to SDK 1 and direct private-route dependencies were removed.
- Expanded the Gravewright PDF System to consume the public PDF viewer and
  annotation APIs.
- Updated English and Brazilian Portuguese SDK documentation, capability maps,
  author checklists, reference material, PDF guide, and package power map.
- Updated desktop packaging, environment templates, defaults, and dependency
  lock data for the Beta runtime.

### Savage Worlds

- Added a campaign-scoped initiative deck selector to the combat tracker.
- Added SDK-driven action-card initiative: one public card per combatant,
  Joker-first and Ace-to-Two ranking, suit tie-breaking in Spades/Hearts/
  Diamonds/Clubs order, atomic labels/order updates, and immediate card artwork.
- New cards are dealt when combatants change or a round changes, never when the
  GM advances between combatants or merely interacts with/repaints the tracker.
- The highest card becomes the current combatant after each deal.
- A round containing a Joker resets the selected deck to all 54 cards and
  reshuffles before the following round; a fresh ordered deck is shuffled before
  its first deal.
- Card assignment is cached for first-paint reliability, while authoritative
  combat events recover an initially empty tracker and reject stale asynchronous
  repaints that would restore an older row order.
- Kept the bundled Savage Worlds compatibility package at version `1.1`.

### Fixed

- Fixed combat order races where an older add/remove response could repaint
  after the atomic SDK initiative response and put rows back in stale order.
- Fixed card art missing on the first initiative interaction because a second
  cards-state request raced the render lifecycle.
- Fixed repeated Savage initiative deals caused by treating every tracker action
  as a new round.
- Fixed manual initiative order persistence and ensured the confirmed first row
  owns turn index zero.
- Fixed noisy high-frequency `gm_hint.sample` diagnostics in normal terminal
  output while retaining bounded diagnostic instrumentation.
- Fixed blocking synchronous asset-package route declarations and package asset
  cache invalidation during local development.
- Fixed actor/item/folder refresh consistency, scene/wall update propagation,
  token vision snapshots, and stale-version handling exposed by the SDK move.
- Fixed dynamic-lighting and shader lifecycle edge cases found by the expanded
  browser harnesses.

### Performance validation

- Added reproducible warm-up/measurement protocols, frame/callback/app-render/
  unattributed-gap percentiles, long-task counts, heap/RSS, spatial query, shared
  asset, texture source, and logical GPU metrics.
- Revalidated the optimized shared-asset renderer in headed Chromium with an
  NVIDIA GeForce RTX 4060 explicitly recorded in every result. The synthetic
  dragon workload remained in the approximately 60 Hz presentation band through
  7,500 visible instances and in the approximately 30 Hz band at 10,000. Isolated
  callback p95 was 16.5 ms at 11,000 and 23.2 ms at 11,500, placing the observed
  callback-budget crossing between those points. Sequential near-limit runs
  showed variance, so the project reports ranges rather than a false exact
  ceiling. Counts refer to entities actually visible, not merely requested.
- Added a realistic GPU-confirmed 5K scene protocol with names, two bars per
  token, 150 walls, 12 lights, token vision, and darkness 0.6. Gravewright
  completed 3/3 valid runs at both 500 tokens (median p95 16.9 ms) and 800 tokens
  (median p95 33.2 ms).
- Recorded baseline and guided six-client map runs across every predictive
  policy, including the 5,000×5,000 fixture and adaptive raster policy.

### Database

- Added migrations `0044_virtual_raster_v2`,
  `0045_adaptive_raster_policy`, and `0046_pdf_annotations`.

### Release

- Renumbered the application from the experimental `3.x-alpha` line to
  `1.0.0-beta.1`; Python distribution metadata uses PEP 440 `1.0.0b1`.
- Removed the general real-campaign warning banner from the main README. Backup
  instructions and contextual destructive-operation confirmations remain.

## v3.0.2-alpha: 2026-08-11

Shader lifecycle hotfix. No database migration or public SDK change is included.

### Fixed

- Animated scene shaders now keep requesting frames through the board's existing
  on-demand render scheduler while their speed is non-zero. Static shaders still
  allow the renderer to sleep when the board is idle.
- Editing GLSL source now invalidates and disposes the previous compiled runtime,
  recompiles the latest source, and redraws immediately. The same lifecycle is
  applied to realtime refreshes, deletion, rollback after a failed save, and
  recovery after invalid GLSL, so a page reload is no longer required.

## v3.0.1-alpha: 2026-08-10

Hotfix release on the Alpha 3 line. No schema-breaking changes; one additive
migration (`0043`) and one behavioural default change in table permissions.

### Fixed

- Exploding dice stopped after a single extra die. The evaluator's `!` rolled one
  extra die per maximum in the opening throw and never re-examined what it had
  just added, so a d12 that rolled 12, exploded and rolled 12 again simply
  stopped, and every open-ended total came out low. Explosion now chains while a
  die keeps landing on its maximum, bounded per roll so a die that cannot fail to
  explode still terminates. Dropping (`L`/`H`) is unchanged: it still resolves on
  the opening throw, before any explosion. Measured over 30,000 rolls, `1d4!`
  now averages 3.35 against the open-ended 3.33; the single-extra behaviour
  averaged about 3.12. The SDK formula function `explode(sides, threshold)` is a
  different engine and already chained; the two now agree.
- Enabling a package left its stored manifest hash describing a manifest the row
  no longer held. Enabling re-validates against disk and wrote only the refreshed
  hash, keeping the snapshot taken at install time, so `grave doctor` reported
  `sdk.persistence.manifest_hash_mismatch` for the rest of that install's life.
  The snapshot now travels with the hash: enabling adopts the manifest it just
  validated. Existing inconsistent rows are repaired with
  `grave package update all`.

### Changed

- Players no longer delete chat messages by default. The chat is the table's
  record, and a roll or a line could disappear without the GM seeing it, so
  `chat.delete_own` left the player role's defaults. The permission still exists
  and a table that wants it can grant it back per role; GMs keep
  `chat.delete_any`.
- Board pings are drawn by the renderer instead of DOM overlays, and each player
  has a ping colour of their own (`0043_ping_color_preference`), broadcast with
  the ping so the table can tell who pinged.
- Layer visibility now separates effects, walls, and lighting: hiding lighting no
  longer takes particles and shaders with it, and doors are only pickable where
  they are actually visible.

### Added

- The dice tray accepts an optional name for a roll. The name never enters the
  notation: it travels after `#` as the message label, and shows up in the roll
  toast and in the chat message, live and after a reload.
- The dice tray's history is persisted per table in the browser (`localStorage`),
  holds up to 30 entries instead of 8, keeps the name given to each one, and each
  entry can be removed. History saved by older versions is read as unnamed
  entries.
- GMs and streamer views can browse a scene locally with `?view_scene=`, without
  activating it for the table. The scene manager marks which scene is loaded and
  which is only being browsed.
- The streamer view can compose lighting, walls, particles, and shaders in a local
  sandbox: edits are applied to that view only and never reach the table or the
  database.

## v3.0.0-alpha: 2026-08-09

### Added

- Added a scene shader system with user-authored GLSL, stable world-space origins,
  zoom-independent rendering, opacity control, and distinct compositing modes.
- Added a localized library of 50 shader presets covering substantially different
  visual families instead of minor variations of a circular glow.
- Expanded the particle editor with additional particle types and configurable
  emission, movement, lifetime, scale, colour, opacity, rotation, and spread controls.
- Added dedicated campaign settings launchers and focused configuration modals,
  with campaign identity, inline ruleset selection, and a compact connected-player list.
- Added persistent, catalog-versioned administrative audit history with
  allowlisted metadata, GM-only pagination/filtering, retention, and safe JSON export.
- Added versioned campaign snapshots with checksums, conservative scene/board
  restoration, automatic recovery points, retention, and protected deletion.
- Added transactional, selective campaign cloning for GMs, including a dry-run
  summary, relationship remapping, explicit privacy exclusions, and an
  operational feature flag.
- Added campaign-scoped global search and an accessible Ctrl/Cmd+K command
  palette for actors, items, journals, scenes, and GM-visible compendiums, with
  server-side resource authorization and a bounded portable SQL query.
- Added reusable campaign entry codes with one-time plaintext display,
  expiration, optional use limits, rotation/revocation, rate-limited redemption,
  server-side link continuation, and SQLite/PostgreSQL concurrency guarantees.

### Fixed

- A player could open a sheet and be denied its contents. Reading a campaign
  library file required table-wide authority or ownership of the upload, so a
  PDF-backed character sheet: where the sheet *is* the uploaded file: answered
  403 to the player whose character it was, and to assistant GMs. A library file
  that one of the user's own sheets points at is now readable by that user; the
  reference is verified against the stored sheet, so nothing else in the library
  becomes reachable with it.

### Changed

- Remodelled token bars as two positional slots. A token draws `bar_1` under it
  and `bar_2` above it, green and blue by default, and the active ruleset points
  each slot at whatever it tracks: the core resolves the paths and draws the
  ratio, it never reads the numbers as health. A system may repaint either bar
  with a literal hex; mapping only one slot leaves the other undrawn.
- Rebuilt the combat tracker around a single initiative value per combatant,
  stored as text the core never interprets. The six competing turn-order
  strategies (individual formula, side/group, card deck, spotlight, alternating
  sides, manual) are gone. The active ruleset declares `initiative.input`
  instead: `roll` (the system's formula, with roll buttons), `number` (the GM
  types a number) or `text` (free text, with the GM arranging the order by
  hand). Combatants can be hidden from players, marked defeated, moved through a
  hand-arranged order, and given the turn directly.
- The engine no longer has an initiative formula of its own. A system that
  declares no formula and no rollable action has nothing to roll, and says so,
  rather than falling back to a `1d20` that only made sense for one game.
- The Gravewright PDF System now declares `input: "text"`: the GM types the turn
  position straight into the tracker and orders the list by hand, which is what
  reading a turn order off a PDF actually looks like.
- Empty persistent databases are now initialized automatically through Alembic;
  existing databases with outdated revisions remain fail-closed unless an
  operator explicitly upgrades them or enables automatic migration.
- Entry codes are now the primary way to invite players without collecting an
  email address. Email invitation creation remains available as a marked legacy
  compatibility flow for this release.
- Existing pending email invitations remain acceptable until their normal
  expiry. Operators can disable new legacy invitations with
  `CAMPAIGN_EMAIL_INVITATION_CREATION_ENABLED=false`.

### Removed

- Removed the `hp` token bar key. `rules/token.gw.json` now declares `bar_1` and
  `bar_2`; a mapping that still names its single bar `hp` is read as `bar_1`, and
  migration `0031_token_bar_slots` moves the snapshot unlinked tokens keep in
  `overrides_json`. The realtime token payload gained a `color` per bar.
- Removed the dead `game.sheets.token_config.bar_1_*` strings, which nothing
  rendered and which described the slot as an HP field.
- Removed the combat presentation contract from `rules/combat.gw.json`
  (`ui.combat` skin/density/palette/hero/participant and its ~35 label
  overrides) and the `turnOrder` strategy block. A ruleset now declares only
  `initiative` (label, input, sort, formula, action, tie-breaker, icon, accent)
  and `resources`; panel text comes from the core locales. The pre-v2 nesting is
  still read: including the old `mode`, which maps card/spotlight/alternating/
  manual orders onto `input: "text"`: so installed packages keep working.
- Removed the `combat_events` table, which nothing ever read back, along with
  the encounter's `mode`/`strategy`/`phase`/`settings_json` columns and the
  participant's `initiative_label`/`initiative_data_json`/`sort_key`/
  `group_key`/`metadata_json` columns. `combat_participants` is now
  `combat_combatants` (migration `0029_simplify_combat`), `initiative` is text
  and the numeric ordering key moved to `sort_value` (migration
  `0030_combat_initiative_text`).
- Reduced the combat realtime events to `combat.started`, `combat.updated` and
  `combat.ended`; every one carries the full state. The nine narrower events and
  the unused `combat.next_turn.request` command were removed.
- Replaced the twelve combat HTTP routes with ten: `combatants/add`,
  `combatants/remove`, `combatants/flags`, `initiative/roll` (scoped `all`,
  `npc`, `missing`, or one combatant), `initiative/set`, `order`, `turn`,
  `round`, `start`, `end`. `initiative/set` takes text, not a number.
  `combat.registerPanel` no longer takes `renderHud`, and the combat runtime
  slot/handler names are now `combatantActions`/`combatantMeta`.

### Operations

- `CAMPAIGN_JOIN_CODE_ENABLED=false` provides a non-destructive rollback: it
  hides join-code UI and routes without deleting codes, memberships, legacy
  invitations, or schema. The `campaign_invitations` table is intentionally
  retained for the compatibility window.

## v2.1.0-alpha: 2026-06-24

### Added

- Added the backend foundation for generic card decks, piles, private hands, card events,
  redacted card state, and deck draw/shuffle/reset flows.
- Added card scene-placement backend flows for playing, moving/flipping, and discarding
  cards from scenes.
- Added GM-only card image upload backend support for card fronts and backs.
- Added a card table layer on the board: cards played to a scene are anchored to world
  coordinates and can be moved, resized, rotated, and z-ordered, matching the scene-image
  (asset) interaction model.
- Added drag-and-drop of hand cards onto the table; the hand "flip" control chooses which
  face (front/back) a card lands on, and the hand can draw a card straight to chat.
- Added multi-selection for table cards and scene images: Shift/Ctrl-click to toggle, or a
  right-to-left marquee drag to box-select (left-to-right still selects tokens). Selected
  items move, rotate, delete, and z-order as a group, and Delete/Backspace removes them.
- Added a GM control to remove a deck and all of its cards.
- Added owner permissions so a player can manipulate the cards they played to the table.
- Added complete `grave` operator CLI wiring for local operation and SDK package tooling.
- Added local launchers: `grave` for Linux/macOS and `grave.bat` for Windows.
- Added `grave run` for first-run setup, dependency checks, schema initialization, diagnostics summary, and server launch.
- Added `grave doctor` documentation for environment, package, and database drift checks.
- Added `grave backup`, `grave restore`, and `grave lock` documentation.
- Added `grave package` lifecycle documentation: list, validate, install, enable, disable, remove, update, and doctor.
- Added campaign package activation documentation through `grave campaign package`.
- Added package scaffolding documentation through `grave <kind> new`.
- Added parser smoke-test coverage for the CLI command surface.
- Added browser E2E documentation for the SDK runtime.

### Changed

- Cards and assets a player does not own are no longer interactive for them, and the
  asset (image) library is now GM-only.
- Quick start now uses the `grave` CLI instead of calling `uvicorn` directly.
- Documentation now treats Gravewright SDK packages as the only extension model.
- Documentation now uses ruleset/addon/library/theme/content/assets terminology instead of the old system/module split.
- Operational docs now require backup-before-update discipline during Alpha.
- Security docs now describe trusted JavaScript packages, package path safety, and SDK capability boundaries.

### Breaking Changes

- Existing PRE-ALPHA System API and Module API docs are obsolete.
- Existing Alpha packages may need updates to match the unified SDK manifest, capabilities, activation, and package directory model.
- Existing Alpha tables may require reset or manual repair after SDK/storage/schema changes.

### Known Issues

- Alpha releases do not guarantee an upgrade path for existing tables.
- Scripted SDK packages run trusted JavaScript in the browser; install them only from trusted authors.
- Remote/zip package installation and package signatures are future hardening milestones unless implemented in the running branch.

## PRE-ALPHA SDK Refactor

Breaking changes:

- Removed System API v1.
- Removed Module API v1.
- Removed `/systems/*` routes.
- Removed `/modules/*` routes.
- Removed `data/systems/`.
- Removed `data/modules/`.
- Removed `app/engine/systems/`.
- Removed `app/engine/modules/`.
- Removed `window.Gravewright.modules`.
- Removed `window.GravewrightSheets` and `window.GravewrightCombat` as the public package API (they remain as internal core registries).
- Added the Gravewright SDK.
- Added the unified Gravewright package manifest (`schemas/gravewright-package-v1.schema.json`).
- Added `data/packages/`.
- Added `/sdk/*` routes.
- Added `window.GravewrightSDK`.
- Existing PRE-ALPHA databases must be reset (destructive migration `0007_sdk_packages`).
