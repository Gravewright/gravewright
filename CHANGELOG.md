# Changelog

All notable changes to Gravewright should be documented here.

The project is currently in Alpha. Breaking changes may occur between Alpha releases, especially around database schema, storage layout, the package manifest, package activation, realtime events, and the public SDK.

## Unreleased

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
