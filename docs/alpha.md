# Alpha Status

> [!WARNING]
> **ALPHA — DO NOT RUN LONG CAMPAIGNS.**
>
> Gravewright is in Alpha. Structural changes, especially database schema and public API contract changes, may happen between versions. **There is no guaranteed upgrade path**: an update can make an existing table unrecoverable.
>
> **Use it for one-shots, testing, and experimentation.** Test it, break it, and report problems or suggestions in [issues](https://github.com/gravewright/gravewright/issues).
>
> In a one-shot, you may lose one session. In a campaign, you may lose months.

## What Alpha Means

Alpha means the project is public enough to test and discuss, but not stable enough to trust with long-running campaign data.

Expect changes in:

- database schema;
- migration behavior;
- system and module manifests;
- public browser APIs;
- realtime event names and payloads;
- storage layout for maps, assets, sheets, and packages;
- permissions and campaign lifecycle behavior.

## Recommended Use

Use Gravewright Alpha for:

- one-shots;
- local experiments;
- ruleset and module prototyping;
- performance tests with large maps;
- API feedback;
- bug reports and reproduction cases.

Do not rely on Alpha releases for:

- long campaigns;
- irreplaceable world data;
- public multi-table hosting;
- production instances without backups and restore tests.

## Upgrade Policy Before 1.0

Before 1.0, maintainers may ship breaking changes without an automatic migration path. Release notes should call out known breaking changes, but old data may still require manual repair or fresh setup.

Before upgrading an instance with data you care about:

1. Stop the application.
2. Back up the database.
3. Back up `storage/`.
4. Back up `GRAVEWRIGHT_DATA_DIR` or `data/`.
5. Test restore on a copy.
6. Upgrade only after the copy starts and diagnostics look clean.

## Feedback Wanted

Useful Alpha feedback includes:

- exact reproduction steps;
- browser and server logs with secrets removed;
- screenshots of incorrect UI state;
- campaign size, map dimensions, and player count for performance issues;
- expected behavior and actual behavior;
- notes about confusing docs or missing extension APIs.
