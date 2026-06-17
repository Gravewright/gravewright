# `grave` CLI for SDK authors

`grave` is the local operator and SDK tooling CLI for Gravewright.

It serves three audiences:

1. operators running, backing up, restoring, and diagnosing local tables;
2. maintainers diagnosing package/database drift;
3. package authors creating, validating, installing, and activating SDK packages.

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
uv run python -m app.cli run --open
```

The launchers call `uv run python -m app.cli`, so they work even before the `grave` console-script entry point is installed.

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | OK |
| `1` | `doctor` or a doctor-backed command found an error |
| `2` | Invalid CLI usage |
| `3` | Destructive or unsafe operation refused without confirmation |
| `4` | Required external dependency missing |
| `5` | Package incompatibility |

## `grave run`

```bash
grave run
grave run --open
grave run --host 0.0.0.0 --port 8000
grave run --dev
grave run --no-install
grave run --no-migrate
```

`grave run` prepares runtime directories, checks dependencies, ensures the database schema exists, summarizes `doctor`, and starts the server.

## `grave doctor`

```bash
grave doctor
grave doctor --json
grave doctor --ai
grave doctor --skip-db
grave doctor --packages-dir data/packages
```

Doctor checks include:

- Python and `uv` availability;
- data/package/storage directories;
- SDK schema file;
- session secret defaults;
- package manifests;
- referenced package files;
- database reachability;
- installed, enabled, and active package drift;
- dependencies and conflicts;
- orphan settings;
- orphan content imports.

## `grave package`

```bash
grave package list [--json]
grave package validate <path> [--json]
grave package install <package> [--yes] [--enable] [--activate <campaign_id>] [--json]
grave package enable <package_id>
grave package disable <package_id> [--force]
grave package remove <package_id> [--force]
grave package update <package_id> [--json]
grave package doctor <package_id> [--json]
```

Important behavior:

- `validate` checks the SDK manifest contract and referenced paths.
- `install` prints requested capabilities and warns when a package runs trusted JavaScript.
- `doctor` surfaces dependency, conflict, compatibility, activation, and package file problems.

## Per-kind commands

```bash
grave ruleset list
grave ruleset install <package>
grave ruleset new my-rpg --name "My RPG" --sheets --rolls --combat --content

grave addon list
grave addon install <package> --enable --activate <campaign_id>
grave addon new my-addon --name "My Addon" --js --settings

grave theme new my-theme --name "My Theme"
grave content new my-content --name "My Content"
grave assets new my-assets --name "My Assets" --images
grave library new my-library --name "My Library"
```

Per-kind commands enforce the expected package kind.

## Campaign package activation

```bash
grave campaign package list <campaign_id> [--json]
grave campaign package activate <campaign_id> <package_id>
grave campaign package deactivate <campaign_id> <package_id>
```

Campaigns are addressed by id, not title.

## Backup and restore before SDK changes

```bash
grave backup -o gravewright-backup.zip --include-assets --include-packages --verify
grave restore gravewright-backup.zip --dry-run
grave restore gravewright-backup.zip --yes
```

Restore is destructive and requires explicit confirmation.

## Lockfile

```bash
grave lock
grave lock -o grave.lock.json
grave lock --json
```

Use lockfiles to record a reproducible snapshot of installed package state.

## Package author loop

```bash
grave ruleset new my-rpg --name "My RPG" --sheets --rolls --combat --content
grave package validate data/packages/rulesets/my-rpg
grave package install my-rpg --yes --enable
grave package doctor my-rpg
```

For addons:

```bash
grave addon new my-addon --name "My Addon" --js --settings
grave package validate data/packages/addons/my-addon
grave package install my-addon --yes --enable
grave campaign package activate <campaign_id> my-addon
grave package doctor my-addon
```
