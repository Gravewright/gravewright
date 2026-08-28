# Beta Status

Current release: **Gravewright v1.0.0-beta.4**.

The SDK 1 public extension contract is frozen. Beta releases focus on compatible
bug fixes, security and permission hardening, migration reliability,
documentation, tests, and performance work.

## Included in Beta 4

- server-authoritative campaigns, scenes, actors, items, journals, cards, and combat;
- SDK 1 packages with capability and user-authority enforcement;
- PDF viewing, navigation, search, metadata, and annotations through SDK 1;
- campaign backup, restore, snapshots, cloning, export, and import;
- virtual-raster maps, adaptive raster granularity, and GM-guided prefetch;
- dynamic lighting, walls, doors, particles, shaders, and streamer composition;
- dense shared-asset token rendering and reproducible performance benchmarks;
- bundled PDF and Savage Worlds compatibility rulesets.
- redesigned Gravewright Mode windows, dockable/detachable directories, system tray,
  compact settings, and lazy-loaded resource directories;
- roll tables, authoritative roll rerolls and constrained roll-card actions;
- explicit combat start plus holding, interruption and turn-resume state;
- user presentation colors exposed through the capability-gated SDK projection;
- runtime suspension and cleanup that reduce idle work and release table resources.

## Compatibility

Package authors should target `sdkVersion: "1"` and declare every capability
they consume. Beta 4 is certified against SDK 1 RC 1; packages continue to use
`sdkVersion: "1"` because RC status is not a manifest version. Database changes are
delivered through Alembic migrations, and documented public SDK 1 APIs are the
compatibility boundary.

## Updating

Use the operator CLI for upgrades:

1. Create a verified backup with `grave backup -o pre-upgrade.zip --include-assets --include-packages --verify`.
2. Run `grave doctor` and resolve reported schema or package problems.
3. Upgrade the application and run the normal migration path.
4. Verify the instance and a representative campaign before normal use.

## Feedback

Reports are most useful when they include exact reproduction steps, the
Gravewright version, browser and server logs with secrets removed, campaign/map
scale, player count, and expected versus actual behaviour.
