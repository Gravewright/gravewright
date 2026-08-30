# 5e SRD Compatible Framework for Gravewright

Unofficial 5e/SRD-compatible ruleset package for Gravewright.

This package provides schemas, sheets, rules, mappings, automation, and small
sample/model content packs for running 5e-compatible games in Gravewright. It is
designed as a technical ruleset framework, not as a replacement for any official
rulebook or digital compendium.

## Status

Package status: **Alpha / SDK 1 compatible**

Tested with:

```text
Gravewright 3.0.0-alpha
SDK 1
```

## What this package includes

* Actor schemas for characters and monsters.
* Item schemas for weapons, armor, equipment, consumables, spells, feats,
  features, races, backgrounds, classes, and effects.
* Declarative actor and item sheets.
* Runtime sheet helpers through `sheets.runtime`.
* Declarative combat configuration through `combat.config`.
* Dice, roll intent, chat-card, token, and combat mappings.
* Small sample/model content packs for development and drag/drop testing.

## What this package does not include

This package does **not** include:

* official rulebooks;
* official PDFs;
* official artwork;
* official trade dress;
* a full proprietary compendium;
* closed/proprietary monsters, settings, subclasses, spells, or other material
  outside material the project is permitted to use;
* any claim of official affiliation, endorsement, or approval by Wizards of the
  Coast.

Users are responsible for owning and using any rulebooks or content required for
their own table.

## Legal and attribution notice

This is an unofficial compatibility package. See [`NOTICE.md`](NOTICE.md) and
[`CONTENT_POLICY.md`](CONTENT_POLICY.md) before adding content.

Where SRD material is included or adapted, it is attributed under Creative
Commons Attribution 4.0 International (CC BY 4.0). See [`NOTICE.md`](NOTICE.md).

## Installation

The recommended way to install this ruleset is through the Gravewright web
interface.

### Install through Gravewright

1. Download the latest release `.zip` from this repository.
2. Open Gravewright in your browser.
3. Go to **Sistemas de Regras** / **Rulesets**.
4. Click **Enviar e instalar**.
5. Select the downloaded `.zip` file.
6. Review the package details.
7. Click **Instalar**.

After installation, the ruleset will appear in the available rulesets list.

When creating or configuring a campaign, select the **5e SRD Compatible
Framework** ruleset for that campaign.

### Install manually from a Gravewright checkout

Manual installation is intended for developers, maintainers, and advanced users.

From the Gravewright project root:

```bash
mkdir -p data/packages/rulesets
git clone https://github.com/Gravewright/gravewright-5e-srd.git data/packages/rulesets/dnd5e
uv run python -m app.cli package validate data/packages/rulesets/dnd5e
uv run python -m app.cli package install dnd5e --enable
uv run python -m app.cli doctor
```

On Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force data\packages\rulesets | Out-Null
git clone https://github.com/Gravewright/gravewright-5e-srd.git data\packages\rulesets\dnd5e
uv run python -m app.cli package validate data/packages/rulesets/dnd5e
uv run python -m app.cli package install dnd5e --enable
uv run python -m app.cli doctor
```

### Updating a manual install

From the package directory:

```bash
git pull
```

Then from the Gravewright project root:

```bash
uv run python -m app.cli package update dnd5e --json
uv run python -m app.cli doctor
```

## Repository layout

```text
manifest.json
assets/
content/
layouts/
locales/
mappings/
rules/
schemas/
```

## Compatibility

See [`COMPATIBILITY.md`](COMPATIBILITY.md).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Security

See [`SECURITY.md`](SECURITY.md).
