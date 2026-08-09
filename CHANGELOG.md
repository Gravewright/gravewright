# Changelog

All notable changes to Gravewright should be documented here.

The project is currently in Alpha. Breaking changes may occur between Alpha releases, especially around database schema, storage layout, the package manifest, package activation, realtime events, and the public SDK.

## Unreleased

No changes documented yet.

## v3.0.0-alpha — 2026-08-09

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
  PDF-backed character sheet — where the sheet *is* the uploaded file — answered
  403 to the player whose character it was, and to assistant GMs. A library file
  that one of the user's own sheets points at is now readable by that user; the
  reference is verified against the stored sheet, so nothing else in the library
  becomes reachable with it.

### Changed

- Remodelled token bars as two positional slots. A token draws `bar_1` under it
  and `bar_2` above it, green and blue by default, and the active ruleset points
  each slot at whatever it tracks — the core resolves the paths and draws the
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
  still read — including the old `mode`, which maps card/spotlight/alternating/
  manual orders onto `input: "text"` — so installed packages keep working.
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

## v2.1.0-alpha — 2026-06-24

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
