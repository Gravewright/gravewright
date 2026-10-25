# Upgrading and recovery

[Documentation](../README.md) · [Português](../pt-BR/upgrading.md)

This guide covers the **Gravewright 0.3.3 — Alpha** release. Its source
artifact is `Gravewright-0.3.3-django.zip`, with the matching
`Gravewright-0.3.3-django.zip.sha256`. See the [release notes](../releases/0.3.3.md)
for features and [deployment](deployment.md) for public-server configuration.

## Before upgrading

1. Record the running version and configured paths. Stop all table and campaign
   manager writes, then stop the Runner and every ASGI/maintenance process using
   the installation. A browser closed by itself does not stop the server.
2. Back up `.env`, the configured database and private media together. Include
   external module/content directories, local `extensions/`, trust keys and
   Runner/update recovery state. By default, `.env` and `extensions/` are at the
   installation root; the database, media and runtime/recovery state are under
   `data/`. Protect this backup: it contains accounts, GM secrets, private sheets
   and retained deleted attachments.
3. Retain the matching application source and lock files with the backup. Test
   recovery in a separate directory with separate database/media settings before
   using an important campaign as the first upgrade check.
4. Use the complete release archive and its matching SHA-256 value. Never reuse
   the checksum of a different ZIP or replace only an installer entrypoint.

Do not redirect defaults to a shared OS profile to repair an installation. A
non-writable installation must report the failing path. Explicit operator
storage overrides remain supported, and must be backed up as well.

## Upgrade paths

After completing the stopped-instance backup, restart the **current** Runner
for a compatible managed installation, then use
**Administration → Updates → Install update**. Keep **Keep a .old copy for rollback**
enabled when recovery is wanted. Leave that Runner open while the supervisor
downloads, verifies, prepares dependencies, snapshots data, migrates, replaces
files and restarts. Reconnecting browsers reload after the target version is
confirmed. Do not run a second server against that database during this process.

For a manual upgrade, stop the installation, preserve the configuration and
data listed above, replace application files with the complete release, then run
the platform installer and use its regenerated Runner:

| Platform | Prepare the upgrade | Start |
| --- | --- | --- |
| Windows | `Install Windows.bat` | `Gravewright Runner.bat` |
| Linux | `bash "./Install Linux.sh"` | `bash "./Gravewright Runner.sh"` |
| macOS | `bash "./Install macOS.command"` | `bash "./Gravewright Runner.command"` |

The installers preserve project `.env` and prepare locked Python/frontend
dependencies. They apply migrations before startup. Rerun installation after
moving the source because launchers and environments refer to its location.
Do not copy a generated Runner from another machine or installation.

Source deployments started directly with Daphne require an operator-managed
upgrade. Configure local tool storage below, prepare the frontend as described
in [frontend](frontend.md), and run from the installation root with the intended
configuration:

```bash
uv sync --locked --no-dev
uv run --locked --no-dev python manage.py migrate --plan
uv run --locked --no-dev python manage.py migrate --noinput
uv run --locked --no-dev python manage.py collectstatic --noinput
uv run --locked --no-dev python manage.py check
```

Retain `--extra vips` on dependency synchronization if that installation uses
the optional libvips tiler. After these commands, restart the service using its
existing deployment profile. `check --deploy` and public HTTPS/WSS verification
also apply to public deployments.

### Numbering and same-version packages

The release identifier is **0.3.3**, following **0.3.2**. The updater compares
version numbers, so a compatible installation on 0.3.2 can discover 0.3.3 through
its configured release repository. The project remains in Alpha and the host SDK contract is unchanged;
optional APIs still need capability checks. Historical release notes retain
their original identifiers.

An installation reporting the earlier incorrectly numbered **3.0.1** considers
0.3.3 a lower version and will not receive it through automatic discovery.
Back up its matching source, database and media, then use the manual installation
procedure with the complete 0.3.3 archive and matching checksum. This corrects
the release numbering; do not try to downgrade the database by swapping older
code over it. If recovery is needed, restore matching source, database and media
together.

A host already reporting **0.3.3** will not receive a reissued 0.3.3 through
version discovery. Use the manual upgrade procedure with the replacement ZIP
and its own checksum. Do not downgrade a database by swapping older source over
it; recovery requires matching source, database and media.

## Database migrations in 0.3.3

Compared with 0.3.2, this release adds three migrations:

| Migration | Stored capability |
| --- | --- |
| [maps/0014_sceneassignment.py](../../gravewright/maps/migrations/0014_sceneassignment.py) | Individual player scene assignments |
| [maps/0015_builderobjectpreset.py](../../gravewright/maps/migrations/0015_builderobjectpreset.py) | Campaign-owned reusable Builder object presets |
| [tokens/0002_token_appearance.py](../../gravewright/tokens/migrations/0002_token_appearance.py) | Token name, turn-indicator and bar presentation settings |

Older installations also need earlier pending migrations. The preceding 0.3.2
release added these seven migrations relative to 0.3.1:

| Migration | Stored capability |
| --- | --- |
| [table/0003_progress_clock.py](../../gravewright/table/migrations/0003_progress_clock.py) | Progress clocks and retry receipts |
| [table/0004_progress_clue.py](../../gravewright/table/migrations/0004_progress_clue.py) | Staged clues and their separate retry receipts |
| [table/0005_mind_maps.py](../../gravewright/table/migrations/0005_mind_maps.py) | Mind-map graphs, visibility, selected editors and separate retry receipts |
| [table/0006_clock_description.py](../../gravewright/table/migrations/0006_clock_description.py) | Authored clock descriptions, empty on existing clocks |
| [campaigns/0005_preparation.py](../../gravewright/campaigns/migrations/0005_preparation.py) | Personal GM dashboards, session plans, timeline events and preparation receipts |
| [journals/0004_revision.py](../../gravewright/journals/migrations/0004_revision.py) | Journal revisions, trash and retained attachment metadata |
| [pdf_system/0001_initial.py](../../gravewright/pdf_system/migrations/0001_initial.py) | Reusable PDF mapping templates, their bundles and revisions |

Run the normal migration command rather than applying only these files: Django
orders their dependencies and also includes missing earlier migrations. The
new tables do not fabricate history for changes made before the feature existed.
Keep the pre-upgrade backup; do not assume older application code can open the
migrated database safely.

## Campaign archives and instance backups

| Recovery material | What it preserves |
| --- | --- |
| Complete campaign export or clone | Selected campaign content, clocks/clues, mind maps, preparation, timeline, portable dashboard metadata and journal history/trash; typed references are remapped |
| Campaign snapshot | Campaign recovery data, including the new preparation/history content; dashboard restoration applies to current GM memberships |
| Coordinated full instance backup | Database, private files, accounts, permissions, host/module state and pending automation, together with configuration and matching application source |

The `preparation` selection controls session plans, timeline events and dashboard
metadata. The `journals` selection controls journal history/trash. Portable
imports do not recreate source users or campaign memberships; individual access
grants are sanitized. A full snapshot can preserve permissions, while it cannot
turn an absent user into a current member. Portable import assigns suitable
dashboard metadata to the importing GM; merge preserves an existing dashboard.

Trashed documents can retain physical attachments. Complete campaign exports,
clones and snapshots include these files; an export that excludes files is
rejected when they are needed to preserve the trash. Do not manually delete
retained files from media storage. Restoration validates file availability,
resource ownership, revisions and quest prerequisites before committing.

Archives from older versions remain importable. If they lack preparation
metadata, restoring them preserves existing preparation/history instead of
deleting data that the archive never contained. Campaign packages still omit
pending Blueprint continuations and command receipts; a full database backup
includes them. See [campaign management](campaign-management.md) for detailed
selection rules.

## Verification and recovery

After startup, check that Administration reports **0.3.3**. Sign in as a GM and
a player using a synthetic or copied campaign. Verify the campaign manager and
table, a mapped PDF, map upload/Universal VTT import, a clock, and a clue whose
content remains hidden until completion. Check private journal visibility,
session save/reopen, history/trash restoration and a representative backup round
trip. Verify a [mind map](mindmaps.md) with a selected player editor: unreadable
links stay unavailable, ordinary graph edits preserve those links, and a copied
graph targets copied campaign resources. Use the [testing guide](testing.md) for
isolated automated scenarios. Also check individual scene assignments, the saved
blank-map grid, cursor preferences, token bar audiences and a reusable Builder
object. Rehearse a Smart Object shader action before applying it to a live scene.

If managed installation fails, retain updater transactions, backups and logs;
the supervisor attempts recovery and handles interrupted transactions on the
next launch. Preserve `.env`, `data/`, tool environments and immutable launcher
copies together. Avoid deleting recovery directories to suppress a failure.

A retained `.old` folder contains the previous source and matching data under
`.gravewright-rollback`. Its name comes from the installation directory, with a
unique suffix for collisions. Runner defaults place it under
`data/updates/retained/`; normal `main.py` places it under
`data/updates/<installation-hash>/retained/`. With every server stopped, invoke
[rollback_update.py](../../scripts/rollback_update.py) using the installation's
Python and the actual retained path, as shown in [deployment](deployment.md).
This returns data to the backup time and discards subsequent changes.

When inspecting a restored full database, use
`GRAVEWRIGHT_AUTOMATION_WORKER_ENABLED=false` before startup if overdue Blueprint
waits must remain paused during inspection. Re-enable only when the recovery
copy is intended to execute its automation. A campaign-only archive does not
restore that pending queue.

## Local tool storage

Native installers, generated Runners and `main.py` configure tool caches and
temporary storage inside `data/runner/` automatically. Manual uv/npm commands
need the same environment before they run. From the writable installation root,
use a fresh shell and keep these variables scoped to that shell.

On Linux/macOS Bash:

```bash
export GRAVEWRIGHT_RUNNER_ROOT="$PWD/data/runner"
mkdir -p "$GRAVEWRIGHT_RUNNER_ROOT/tmp"
export UV_CACHE_DIR="$GRAVEWRIGHT_RUNNER_ROOT/cache"
export UV_PYTHON_INSTALL_DIR="$GRAVEWRIGHT_RUNNER_ROOT/python"
export UV_PYTHON_BIN_DIR="$GRAVEWRIGHT_RUNNER_ROOT/python-bin"
export UV_PYTHON_INSTALL_BIN=0 UV_PYTHON_INSTALL_REGISTRY=0 UV_PYTHON_NO_REGISTRY=1
export npm_config_cache="$GRAVEWRIGHT_RUNNER_ROOT/npm-cache"
export CARGO_HOME="$GRAVEWRIGHT_RUNNER_ROOT/cargo"
export RUSTUP_HOME="$GRAVEWRIGHT_RUNNER_ROOT/rustup"
export XDG_CACHE_HOME="$GRAVEWRIGHT_RUNNER_ROOT/xdg-cache"
export XDG_DATA_HOME="$GRAVEWRIGHT_RUNNER_ROOT/xdg-data"
export XDG_CONFIG_HOME="$GRAVEWRIGHT_RUNNER_ROOT/xdg-config"
export TEMP="$GRAVEWRIGHT_RUNNER_ROOT/tmp" TMP="$GRAVEWRIGHT_RUNNER_ROOT/tmp" TMPDIR="$GRAVEWRIGHT_RUNNER_ROOT/tmp"
```

On Windows PowerShell:

```powershell
$env:GRAVEWRIGHT_RUNNER_ROOT = Join-Path (Get-Location).Path 'data/runner'
$gravewrightTools = $env:GRAVEWRIGHT_RUNNER_ROOT
New-Item -ItemType Directory -Force -Path (Join-Path $gravewrightTools 'tmp') | Out-Null
$gravewrightPaths = @{
    UV_CACHE_DIR = 'cache'; UV_PYTHON_INSTALL_DIR = 'python'; UV_PYTHON_BIN_DIR = 'python-bin'
    npm_config_cache = 'npm-cache'; CARGO_HOME = 'cargo'; RUSTUP_HOME = 'rustup'
    XDG_CACHE_HOME = 'xdg-cache'; XDG_DATA_HOME = 'xdg-data'; XDG_CONFIG_HOME = 'xdg-config'
    TEMP = 'tmp'; TMP = 'tmp'; TMPDIR = 'tmp'; LOCALAPPDATA = 'profile/local'; APPDATA = 'profile/roaming'
}
foreach ($entry in $gravewrightPaths.GetEnumerator()) {
    $gravewrightPath = Join-Path $gravewrightTools $entry.Value
    New-Item -ItemType Directory -Force -Path $gravewrightPath | Out-Null
    [Environment]::SetEnvironmentVariable($entry.Key, $gravewrightPath, 'Process')
}
$env:UV_PYTHON_INSTALL_BIN = '0'
$env:UV_PYTHON_INSTALL_REGISTRY = '0'
$env:UV_PYTHON_NO_REGISTRY = '1'
```

These commands do not change HOME or permanent OS configuration. An operator's
explicit tool-root override can replace `data/runner/`; use an absolute path or
resolve it against this installation, never another installation's active state.
For two independent installations, prepare each inside its own shell and root.
