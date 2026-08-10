# Gravewright v3.0.1-alpha

> **Hotfix on the Alpha 3 line.** No schema-breaking changes. One additive
> migration (`0043`), one behavioural default change in table permissions, and
> one repair step for installations that already saw the package-integrity bug.
> Back up before upgrading, as with every Alpha release.

Alpha 3.0.1 fixes two defects that were quietly wrong rather than visibly broken
— open-ended dice that stopped exploding, and a package registry row that
described a manifest it no longer stored — and closes the table-record gap that
let players delete chat messages.

## Fixes

### Exploding dice kept stopping after one extra die

The evaluator's `!` rolled one extra die for each maximum in the opening throw
and never looked at the dice it had just added. A d12 that rolled 12, exploded
and rolled 12 again stopped there. Nothing on screen said so — the totals were
simply low, all the time, in every system that relies on open-ended dice.

Explosion now chains while a die keeps landing on its maximum. Dropping (`L`/`H`)
still resolves on the opening throw, before any explosion, so `4d6L1!` means what
it meant. A per-roll ceiling keeps a die that cannot fail to explode from
hanging the request, and dice with no meaningful maximum (`dF`, `d1`) do not
explode at all.

The behaviour is measurable rather than a matter of opinion: over 30,000 rolls
`1d4!` now averages **3.35** against the open-ended expectation of 3.33. The old
single-extra-die behaviour averaged about 3.12.

The SDK formula function `explode(sides, threshold)` is a separate engine and
already chained correctly. The two paths now agree.

### `grave doctor` reported a manifest hash mismatch that could not be cleared

Enabling a package re-validates its manifest against disk. It wrote the refreshed
hash but kept the manifest snapshot taken at install time, so the row's hash
described a manifest the row no longer stored, and
`sdk.persistence.manifest_hash_mismatch` was reported for the rest of that
install's life. Enabling now adopts the manifest it just validated: snapshot and
hash move together.

Repair an affected installation after upgrading:

```bash
grave package update all
grave doctor
```

`update` reinstalls each package from disk and restores its enabled status.

## Changed

- **Players no longer delete chat messages by default.** The chat is the table's
  record; a roll or a line could disappear without the GM seeing it.
  `chat.delete_own` left the player role's defaults. The permission still exists:
  a table that wants it can grant it back to the role in campaign permissions.
  GMs keep `chat.delete_any`.
- **Board pings are rendered by the board renderer** instead of DOM overlays, and
  each player has their own ping colour, broadcast with the ping.
- **Layer visibility separates effects, walls, and lighting.** Hiding lighting no
  longer hides particles and shaders too.

## Added

- **Named rolls.** The dice tray takes an optional name for a roll. It never
  enters the notation — it travels after `#` as the message label — and appears in
  the roll toast and in the chat message, live and after a reload.
- **A persistent tray history.** Up to 30 entries per table, kept in the browser,
  each with the name it was given and removable one by one. Histories saved by
  older versions are read as unnamed entries.
- **Local scene browsing.** GMs and streamer views can open a scene with
  `?view_scene=` without activating it for the table; the scene manager shows
  which scene is loaded and which is only being browsed.
- **A streamer composition sandbox.** Lighting, walls, particles, and shaders
  edited from a streamer view stay in that view and never reach the table or the
  database.

## Documentation

Updated as part of this release:

- `CHANGELOG.md` — the `v3.0.1-alpha` section above, in full.
- `docs/features/dice-tray.md` — new: the tray, open-ended `!`, the `#` label,
  and the local history, including where a name is shown.
- `docs/features/dynamic-lighting.md` — the streamer sandbox and the split
  between effects, walls, and lighting visibility.
- `docs/api/http.md` — the per-user preference routes (`layout`, `vision`,
  `ping`) and the `view_scene` query parameter on `GET /game`.
- `README.md`, `SECURITY.md`, `docs/README.md`, `docs/alpha.md`,
  `docs/pt-br/README.md`, `docs/pt-br/alpha.md` — version references.

## Install or upgrade

Create and verify a complete backup before updating:

```bash
grave backup -o pre-3.0.1.zip --include-assets --include-packages --verify
grave restore pre-3.0.1.zip --dry-run
```

Then update, migrate, repair the package registry, and verify:

```bash
grave db upgrade
grave package update all
grave doctor
grave run --open
```

## Compatibility

- Core version: `3.0.1-alpha`.
- Python package version: `3.0.1a0`.
- SDK line: `sdkVersion: "1"` (unchanged, still frozen).
- Manifest schema: `schemaVersion: 1` (unchanged).
- Migrations: `0043_ping_color_preference`, additive.

## Known risks

- Totals from open-ended dice are now higher than in 3.0.0-alpha. That is the
  fix, not a regression — encounters tuned against the old, truncated totals will
  feel different.
- Tables that relied on players cleaning up their own chat messages need to grant
  `chat.delete_own` back to the player role.
- The tray history lives in the browser: it is per browser and per table, and is
  not included in campaign backups.

Report issues with reproduction steps, server logs with secrets removed, and the
output of `grave doctor --json`.
