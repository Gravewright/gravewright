# Gravewright v2.1.0-alpha

> **Alpha release.** The SDK 1 extension surface remains frozen. Gravewright is
> usable for real campaigns if you keep regular backups, but database schema,
> storage layout, realtime events, and public API behavior may still change
> between Alpha releases, and an automatic upgrade path is not guaranteed yet.

This release builds a complete **card system** on top of the frozen SDK 1 surface:
generic decks, private hands, and a fully interactive card/asset table layer.

## Highlights

- **Card decks & hands** — generic decks, draw piles, discard, private per-player
  hands, redacted card state, and shuffle/reset/draw flows.
- **Card table layer** — cards played to a scene are anchored to world
  coordinates and pan/zoom with the board; move, resize, rotate, flip, and
  z-order them, matching the scene-image (asset) interaction model.
- **Hand workflow** — drag a card from your hand onto the table; the hand "flip"
  control chooses which face (front/back) it lands on; draw a card straight to
  chat.
- **Multi-selection (cards & images)** — Shift/Ctrl-click to toggle, or a
  **right-to-left marquee drag** to box-select (left-to-right still selects
  tokens). Move, rotate, delete, and z-order the whole selection together;
  Delete/Backspace removes it.
- **GM controls** — upload card fronts/backs, remove a deck and all of its cards.
  Players can manipulate the cards they own; the image (asset) library is GM-only.

## Install / Upgrade

Fresh install or local run:

```bash
grave run
```

Upgrading an instance with data you care about — **back up first**:

```bash
grave backup -o pre-upgrade.zip --include-assets --include-packages --verify
grave restore pre-upgrade.zip --dry-run   # test the restore on a copy
```

Then upgrade and confirm a clean start with `grave doctor`.

## Breaking changes

- None to the SDK 1 contract — the SDK 1 extension surface stays frozen.
- Pre-Alpha System API / Module API remain removed and unsupported.

## Schema / storage changes

- New card-system tables (decks, deck instances, piles, pile entries, card
  instances, scene card placements) and supporting migrations.
- As with any Alpha release, an automatic upgrade path for existing data is not
  guaranteed — back up and test a restore before upgrading.

## SDK / package manifest changes

- None. `sdkVersion` stays `1`; package compatibility is unchanged.

## Known data-loss risks

- Alpha releases do not guarantee an upgrade path for existing tables.
- Always keep a verified backup before upgrading a campaign you care about.

## Known issues

- Scripted SDK packages run trusted JavaScript in the browser; install them only
  from trusted authors.
- Remote/zip package installation and package signatures are future hardening
  milestones.

## Feedback wanted

- Exact reproduction steps, server/browser logs (secrets removed), and
  screenshots of incorrect UI state.
- Campaign size, map dimensions, and player count for performance reports.
- Confusing docs or missing extension APIs.

Report problems and suggestions in
[issues](https://github.com/gravewright/gravewright/issues).
