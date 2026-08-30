# Installing the 5e SRD Compatible Framework

This package is installed as a Gravewright ruleset package.

Expected package path inside a Gravewright checkout:

```text
data/packages/rulesets/dnd5e
```

## Requirements

- Gravewright `2.0.0-alpha.0` or newer within the `2.x` line.
- `uv`, installed by Gravewright's setup scripts or manually.
- Git, if installing from source.

## Install from Git

From the Gravewright project root:

```bash
mkdir -p data/packages/rulesets
git clone https://github.com/Gravewright/gravewright-5e-srd.git data/packages/rulesets/dnd5e
uv run python -m app.cli package validate data/packages/rulesets/dnd5e
uv run python -m app.cli package install dnd5e --enable
uv run python -m app.cli doctor
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force data\packages\rulesets | Out-Null
git clone https://github.com/Gravewright/gravewright-5e-srd.git data\packages\rulesets\dnd5e
uv run python -m app.cli package validate data/packages/rulesets/dnd5e
uv run python -m app.cli package install dnd5e --enable
uv run python -m app.cli doctor
```

## Install from a release ZIP

1. Download the release ZIP.
2. Extract the package folder into:

```text
data/packages/rulesets/dnd5e
```

3. Validate and install:

```bash
uv run python -m app.cli package validate data/packages/rulesets/dnd5e
uv run python -m app.cli package install dnd5e --enable
uv run python -m app.cli doctor
```

## Activating for a campaign

If your Gravewright build includes campaign package activation commands, activate
the ruleset for a campaign after installing it.

The exact command may vary by Gravewright release. Check:

```bash
uv run python -m app.cli campaign --help
uv run python -m app.cli package --help
```

The ruleset is campaign-scoped and exclusive, so a campaign should normally have
only one active ruleset.

## Updating

From the package directory:

```bash
git pull
```

Then from the Gravewright project root:

```bash
uv run python -m app.cli package update dnd5e --json
uv run python -m app.cli doctor
```

## Uninstalling

Disable/remove it through Gravewright's package commands, then remove the folder:

```bash
uv run python -m app.cli package remove dnd5e --force
rm -rf data/packages/rulesets/dnd5e
```

Windows PowerShell:

```powershell
uv run python -m app.cli package remove dnd5e --force
Remove-Item -Recurse -Force data\packages\rulesets\dnd5e
```
