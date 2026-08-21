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

Running `grave` without arguments prints a short quick-start guide and exits
successfully. Use `grave --help` for the complete command list and
`grave <command> --help` for command-specific options. Mistyped top-level
commands suggest the nearest valid command. `grave --no-color <command>`
disables styled terminal output for plain logs.

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | OK |
| `1` | `doctor` or a doctor-backed command found an error |
| `2` | Invalid CLI usage |
| `3` | Destructive or unsafe operation refused without confirmation |
| `4` | Required external dependency missing |
| `5` | Package incompatibility |

## Output contracts

Commands that expose `--json` write exactly one JSON document to stdout. They do
not mix prompts, progress prose, or ANSI styling into that stream. Failures use
`ok: false`, a stable `error_key`, and the command's documented exit class.
`grave doctor --ai` instead renders a bounded repair prompt from the same
findings used by human and JSON output; it never edits files.

For unattended use, combine `--json` with the explicit confirmation flag a
command requires, such as `--yes`; JSON mode never implies consent.

## `grave run`

```bash
grave run
grave run --open
grave run --host 0.0.0.0 --port 8000
grave run --dev
grave run --no-install
grave run --no-migrate
grave run --diagnostics
grave run --diagnostics --diagnostics-file ./diagnostics/table.jsonl
```

`grave run` prepares runtime directories, checks dependencies, ensures the database schema exists, summarizes `doctor`, and starts the server.

`--diagnostics` enables an explicit local diagnostics mode. Redacted structured
events and complete metric snapshots are written every 30 seconds to a rotating
JSONL file (10 MiB each, five backups). The default is
`data/diagnostics/gravewright.jsonl`. Diagnostics are never uploaded; the CLI prints
the destination and retention policy before starting.
The resulting file is suitable for an issue attachment: user, campaign, room,
scene, command and trace identifiers become stable per-run pseudonyms, while
paths, hosts, origins and URLs are redacted. Always review attachments anyway.

## `grave doctor`

```bash
grave doctor
grave doctor --json
grave doctor --ai
grave doctor --strict
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

`--strict` makes warnings fail the command as well as errors. Human, JSON, and
AI output are rendered from the same findings; JSON remains the only stdout
content when `--json` is selected.

## `grave package`

Distribution channels are managed with:

```text
grave channel show [--json]
grave channel set stable
grave channel set testing --target packages
grave channel set dev --target core --yes --json
```

`dev` requires interactive confirmation unless `--yes` is supplied. Selecting a
lower-risk channel never performs an automatic downgrade.

```bash
grave package list [--json]
grave package validate <path> [--json]
grave package install <package> [--yes] [--enable] [--activate <campaign_id>] [--json]
grave package enable <package_id>
grave package disable <package_id> [--force]
grave package remove <package_id> [--force]
grave package update <package_id> [--json]
grave package update <package_id> --remote [--json]
grave package update all --remote [--json]
grave package doctor <package_id> [--json]
```

Important behavior:

- `validate` checks the SDK manifest contract and referenced paths.
- `install` prints requested capabilities and warns when a package runs trusted JavaScript.
- `doctor` surfaces dependency, conflict, compatibility, activation, and package file problems.
- local `update` refreshes installed metadata from disk; `--remote` delegates to
  the canonical Marketplace installer, including checksum, compatibility,
  dependency, rollback, and recovery enforcement.
- `grave package doctor` diagnoses one installed package through canonical
  Package Doctor findings. `grave doctor` diagnoses the whole installation,
  including all discovered packages and orphaned state.

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

## Scaffold, wizard, and templates

All six kinds support `new`, with shared authoring controls:

```bash
grave ruleset new --wizard
grave addon new -i
grave content new my-content --dry-run --json
grave assets new my-assets --output-dir data/packages --yes --json
```

`--wizard`/`-i` is the guided interactive flow. Flag-based scaffolding is the
reproducible automation flow. `--dry-run` returns the intended files without
writing them; `--force` is required to replace an existing target. `--json`
returns the created path and file inventory as one machine-readable document.

Rulesets additionally expose maintained templates:

```bash
grave ruleset new --list-templates
grave ruleset new my-rpg --template blank --name "My RPG" --yes --json
```

A template owns its declared intent. Combining it with intent flags that would
silently change or discard template choices fails with
`scaffold.template_intent_conflict`. Run `grave <kind> new --help` for
kind-specific flags; unsupported flags are rejected rather than ignored.

New ruleset/content scaffolds emit content pack format 2: the manifest declares
`formatVersion`, `documentType`, and bounded `indexFields`, while the pack uses
an `index` array instead of the legacy `entries` representation.

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
