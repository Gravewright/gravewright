# `grave` CLI

`grave` is the developer/operator CLI for Gravewright.

It exists for three audiences:

1. operators who want to run and back up a local table;
2. maintainers diagnosing package/database drift;
3. package authors creating and validating SDK packages.

## Launchers

Linux/macOS:

```bash
./grave doctor
./grave run --open
```

Windows:

```bat
grave.bat doctor
grave.bat run --open
```

Fallback:

```bash
uv run python -m app.cli doctor
```

The launchers call `uv run python -m app.cli`, so they work even before the `grave` console-script entrypoint is installed.

## Exit codes

| Code | Meaning |
|---:|---|
| 0 | OK |
| 1 | doctor or doctor-backed command found an error |
| 2 | invalid CLI usage |
| 3 | refused destructive/unsafe operation without confirmation |
| 4 | required external dependency missing |
| 5 | package incompatibility |

## `grave run`

"I want to play — fix the basics, then start the server."

```bash
grave run
grave run --open
grave run --host 0.0.0.0 --port 8000
grave run --dev
grave run --no-install
grave run --no-migrate
```

It ensures directories exist, checks dependencies, ensures the database schema is present, summarizes `doctor`, and starts `uvicorn main:app`.

## `grave doctor`

Operational health check:

```bash
grave doctor
grave doctor --json
grave doctor --ai
grave doctor --skip-db
grave doctor --packages-dir data/packages
```

Doctor checks:

- Python and `uv`;
- data/package/storage directories;
- SDK schema file;
- legacy `data/systems` / `data/modules`;
- session secret defaults;
- package manifests and referenced files;
- database reachability;
- installed/enabled/active package drift;
- dependencies, conflicts, orphan settings, and orphan content imports.

## `grave backup` / `grave restore`

```bash
grave backup
grave backup -o my.zip --verify
grave backup -o my.zip --include-assets
grave backup -o my.zip --include-assets --include-packages
grave restore my.zip --dry-run
grave restore my.zip --yes
```

Restore refuses to run without `--yes`.

## `grave lock`

```bash
grave lock
grave lock -o grave.lock.json
grave lock --json
```

Writes a reproducible snapshot of the install.

## `grave package`

```bash
grave package list [--json]
grave package validate <path> [--json]
grave package install <id> [--yes] [--enable] [--activate <campaign_id>] [--json]
grave package enable <id>
grave package disable <id> [--force]
grave package remove <id> [--force]
grave package update <id|all> [--json]
grave package doctor <id> [--json]
```

`install` prints requested capabilities and warns when the package runs trusted JavaScript.

## Per-kind sugar

```bash
grave ruleset list
grave ruleset install <id>
grave ruleset new my-rpg --name "My RPG" --sheets --rolls --combat --content

grave addon list
grave addon install <id> --enable --activate <campaign_id>
grave addon new my-addon --name "My Addon" --js --settings

grave theme new my-theme --name "My Theme"
grave content new my-content --name "My Content"
grave assets new my-assets --name "My Assets" --images
grave library new my-library --name "My Library"
```

Per-kind commands enforce the expected package kind.

## `grave campaign package`

```bash
grave campaign package list <campaign_id> [--json]
grave campaign package activate <campaign_id> <package_id>
grave campaign package deactivate <campaign_id> <package_id>
```

Campaigns are addressed by id, not title.

## Package author loop

```bash
grave ruleset new my-rpg --name "My RPG" --sheets --rolls --combat --content
grave package validate data/packages/my-rpg
grave package install my-rpg --yes --enable
grave package doctor my-rpg
```

For AI-assisted creation, see [`creating-packages-with-ai.md`](creating-packages-with-ai.md).
