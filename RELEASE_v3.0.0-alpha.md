# Gravewright v3.0.0-alpha

> **Alpha release. Back up before upgrading.** The SDK 1 extension surface
> remains frozen, while core tabletop features continue to evolve.

Alpha 3 focuses on visual expression, reliable campaign operations, and a
cleaner in-game configuration workflow.

## Highlights

- **Scene shaders** — custom GLSL snippets, world-anchored origins,
  zoom-independent rendering, opacity, and renderer-level compositing modes.
- **Preset library** — 50 localized shader presets covering distinct fire,
  electricity, fog, rune, portal, weather, shadow, and energy effects.
- **Particles** — more particle families and controls for emission, movement,
  lifetime, scale, rotation, colour, opacity, gravity, and spread.
- **Campaign operations** — join codes, ready checks, campaign cloning,
  snapshots, administrative audit history, and global search.
- **Settings experience** — focused configuration launchers, separate modals,
  inline ruleset selection, campaign identity, and compact player management.

## Install or upgrade

Create and verify a complete backup before updating:

```bash
grave backup -o pre-alpha-3.zip --include-assets --include-packages --verify
grave restore pre-alpha-3.zip --dry-run
```

Then update, start Gravewright, and verify the installation:

```bash
grave db upgrade
grave doctor
grave run --open
```

## Compatibility

- Core version: `3.0.0-alpha`.
- Python package version: `3.0.0a0`.
- SDK line: `sdkVersion: "1"` (unchanged).
- Manifest schema: `schemaVersion: 1` (unchanged).

Historical references to Alpha 2.0.0 in the SDK documentation describe the SDK
1 freeze milestone and remain valid; they do not identify the current core
release.

## Known risks

- Alpha migrations may require operator intervention on old installations.
- Custom shaders execute on each connected user's GPU and can cause poor
  performance or rendering failures when authored incorrectly.
- Scripted SDK packages remain trusted browser code and should only be installed
  from trusted authors.

Report issues with reproduction steps, browser/server logs with secrets removed,
GPU/browser information for rendering problems, and screenshots where useful.
