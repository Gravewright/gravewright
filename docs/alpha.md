# Alpha Status

> [!WARNING]
> **Gravewright v2.1.0-alpha — SDK Freeze.**
>
> The planned **SDK 1 extension surface is now frozen**. Real campaigns are no longer discouraged, provided you keep regular backups and accept that bugs, migrations, and compatibility fixes may still happen before LTS 1.
>
> Structural changes — database schema, storage layout, realtime events, and public API behavior — may still occur between Alpha releases, and a guaranteed automatic upgrade path is not promised yet. Always back up (`grave backup --include-packages`) and test a restore on a copy before upgrading.
>
> Test it, break it, and report problems or suggestions in [issues](https://github.com/gravewright/gravewright/issues).

## What the SDK Freeze Means

Gravewright v2.1.0-alpha keeps the **SDK 1 extension surface frozen**: SDK 1 receives no new extension primitives; work toward LTS 1 focuses on hardening, security, documentation, compatibility, backup/restore, doctor coverage, migration reliability, examples, and bug fixes.

The frozen SDK 1 surface includes:

- manifest v1, package identity, and package kinds;
- the universal package layout and canonical capabilities;
- settings, assets, and content packs;
- the frontend lifecycle;
- managed `storage.sqlite`;
- the `sdk.bus` package-to-package channel;
- HTML sheets;
- doctor/diagnostics, package integrity, and backup/restore package coverage.

Changes may still occur between Alpha releases in:

- database schema and migration behavior;
- realtime event names and payloads;
- storage layout for maps, assets, and sheets;
- permissions and campaign lifecycle behavior.

## Recommended Use

Gravewright v2.1.0-alpha is suitable for real campaigns if you keep regular backups. It is well suited to:

- campaigns and one-shots with a backup routine;
- ruleset, addon, and HTML-sheet authoring against the frozen SDK 1 surface;
- performance tests with large maps;
- API feedback, bug reports, and reproduction cases.

Still treat with care:

- irreplaceable world data without backups and tested restores;
- public multi-table hosting without an operational backup plan.

## Upgrade Policy During Alpha

During Alpha, maintainers may ship breaking changes without an automatic migration path. Release notes should call out known breaking changes, but old data may still require manual repair or fresh setup.

Before upgrading an instance with data you care about:

1. Stop the application.
2. Create a self-contained backup including packages and managed storage:
   `grave backup -o pre-upgrade.zip --include-assets --include-packages --verify`.
   This captures the database, `storage/`, `data/packages/`, and `data/storage/packages/`.
3. Test the restore on a copy: `grave restore pre-upgrade.zip --dry-run`, then restore into a throwaway data dir.
4. Upgrade only after the copy starts and diagnostics look clean.

## Feedback Wanted

Useful Alpha feedback includes:

- exact reproduction steps;
- browser and server logs with secrets removed;
- screenshots of incorrect UI state;
- campaign size, map dimensions, and player count for performance issues;
- expected behavior and actual behavior;
- notes about confusing docs or missing extension APIs.
