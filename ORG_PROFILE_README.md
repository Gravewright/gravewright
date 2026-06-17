<div align="center">
  <img src="https://raw.githubusercontent.com/Gravewright/gravewright/main/icon.svg" width="96" alt="Gravewright logo" />

# Gravewright

**An open-source virtual tabletop for tabletop RPGs, built for performance, extensibility, and control.**

Self-hostable. Server-authoritative. SDK-driven. Package-ready.

[Core Platform](https://github.com/Gravewright/gravewright) ·
[Releases](https://github.com/Gravewright/gravewright/releases) ·
[Documentation](https://github.com/Gravewright/gravewright/tree/main/docs) ·
[Issues](https://github.com/Gravewright/gravewright/issues)

</div>

---

## What is Gravewright?

**Gravewright** is an open-source virtual tabletop platform for tabletop RPGs.

It is designed for groups, game masters, ruleset creators, package authors, and developers who want a VTT that is fast, extensible, self-hostable, and transparent by design.

Gravewright focuses on:

* **Performance** for large maps and realtime collaboration.
* **Extensibility** through the Gravewright SDK and declarative packages.
* **Control** over hosting, data, rules, permissions, and gameplay experience.
* **Open development** with clear architecture, public documentation, and permissive API materials.

> [!WARNING]
> **Gravewright v1.0.0-alpha.1 is an Alpha release.**
>
> Use it for testing, experiments, one-shots, and short Alpha arcs.
>
> It is **not recommended for long-running campaigns yet**. Database schemas, storage layout, SDK package contracts, realtime events, and public APIs may change between Alpha releases.
>
> There is no guaranteed upgrade path between Alpha releases. Back up before updating.

## Install Guide and Demo

New to Gravewright? Start with the install guide and demo video:

[![Gravewright install guide and demo](https://img.youtube.com/vi/19F2UvY4j9w/hqdefault.jpg)](https://youtu.be/19F2UvY4j9w)

[Watch the Gravewright install guide and demo](https://youtu.be/19F2UvY4j9w)

## Main Repository

* **Core platform:** [Gravewright/gravewright](https://github.com/Gravewright/gravewright)
* **Latest releases:** [GitHub Releases](https://github.com/Gravewright/gravewright/releases)
* **Documentation:** [docs/](https://github.com/Gravewright/gravewright/tree/main/docs)
* **SDK documentation:** [docs/sdk/](https://github.com/Gravewright/gravewright/tree/main/docs/sdk)
* **Brazilian Portuguese docs:** [docs/pt-br/](https://github.com/Gravewright/gravewright/tree/main/docs/pt-br)
* **Issues and feedback:** [GitHub Issues](https://github.com/Gravewright/gravewright/issues)

## Try Gravewright

Gravewright is currently distributed as **v1.0.0-alpha.1** for local testing and experimentation.

There is no stable desktop installer yet. The recommended way to try Gravewright is to download a GitHub release or clone the repository and run it locally.

Requirements:

* Python 3.11 or newer
* [`uv`](https://docs.astral.sh/uv/getting-started/installation/)

Quick local setup:

```bash
git clone https://github.com/Gravewright/gravewright.git
cd gravewright
cp .env.example .env
uv sync
chmod +x grave
./grave doctor
./grave run --open
```

Then open:

```txt
http://127.0.0.1:8000
```

On Windows PowerShell:

```powershell
git clone https://github.com/Gravewright/gravewright.git
cd gravewright
Copy-Item .env.example .env
uv sync
.\grave.bat doctor
.\grave.bat run --open
```

Fallback command:

```bash
uv run python -m app.cli doctor
uv run python -m app.cli run --open
```

For release-based installation, download the latest archive from:

* [Gravewright releases](https://github.com/Gravewright/gravewright/releases)

## Grave CLI

Gravewright includes a local operator CLI called `grave`.

Common commands:

```bash
grave doctor
grave run --open
grave backup -o backup.zip --include-assets --verify
grave restore backup.zip --dry-run
grave package list
grave package validate data/packages/rulesets/my-rpg
grave package install my-rpg --yes --enable
grave campaign package activate <campaign_id> my-addon
grave ruleset new my-rpg --name "My RPG" --sheets --rolls --combat --content
grave addon new my-addon --name "My Addon" --js --settings
grave lock -o grave.lock.json
```

Start here:

* [CLI documentation](https://github.com/Gravewright/gravewright/blob/main/docs/sdk/cli.md)

## For Players and Game Masters

Gravewright aims to provide a virtual tabletop that can be hosted and controlled by your own group, without depending on a closed platform.

The project is still early, but the long-term goal is to support:

* campaigns;
* maps and scenes;
* fog, tokens, measurements, pings, and markers;
* actors and items;
* sheets;
* journals and quests;
* chat and dice rolls;
* combat;
* permissions;
* realtime collaboration;
* read-only streamer views;
* diagnostics;
* installable SDK packages.

Use **v1.0.0-alpha.1** for one-shots, experiments, testing, and feedback.

## For Ruleset Creators

Rulesets are Gravewright SDK packages that define the base game system for a campaign.

A ruleset package can provide:

* actor types;
* item types;
* schemas;
* declarative sheets;
* derived rules;
* dice and roll behavior;
* combat configuration;
* token mappings;
* labels and locales;
* reusable game structure;
* starter content packs.

Start here:

* [Gravewright SDK](https://github.com/Gravewright/gravewright/blob/main/docs/sdk/README.md)
* [Package manifest reference](https://github.com/Gravewright/gravewright/blob/main/docs/sdk/manifest.md)
* [Package kinds](https://github.com/Gravewright/gravewright/blob/main/docs/sdk/kinds.md)
* [Capabilities](https://github.com/Gravewright/gravewright/blob/main/docs/sdk/capabilities.md)
* [Creating packages with the CLI](https://github.com/Gravewright/gravewright/blob/main/docs/sdk/cli.md)

Create a ruleset scaffold:

```bash
grave ruleset new my-rpg --name "My RPG" --sheets --rolls --combat --content
```

## For Addon and Package Developers

Gravewright extensions are SDK packages.

Supported package kinds:

* `ruleset` — base game system for a campaign;
* `addon` — optional campaign extension;
* `library` — passive dependency shared by packages;
* `theme` — visual/UI package;
* `content` — importable content package;
* `assets` — reusable media package.

Addon packages can add optional behavior, UI, plugins, settings, scene tools, overlays, content, themes, and browser runtime behavior through documented SDK capabilities.

Start here:

* [SDK runtime](https://github.com/Gravewright/gravewright/blob/main/docs/sdk/runtime.md)
* [SDK security](https://github.com/Gravewright/gravewright/blob/main/docs/sdk/security.md)
* [SDK messaging](https://github.com/Gravewright/gravewright/blob/main/docs/sdk/messaging.md)
* [Public API documentation](https://github.com/Gravewright/gravewright/tree/main/docs/api)

Create an addon scaffold:

```bash
grave addon new my-addon --name "My Addon" --js --settings
```

Validate a package:

```bash
grave package validate data/packages/my-addon
grave package doctor my-addon
```

## For Contributors

Gravewright is early and actively evolving.

Good contribution areas include:

* documentation;
* test coverage;
* UI/UX polish;
* accessibility;
* performance testing;
* SDK package examples;
* ruleset examples;
* addon examples;
* browser runtime feedback;
* backup/restore feedback;
* bug reports from one-shot testing.

Before contributing, read:

* [Contributing guide](https://github.com/Gravewright/gravewright/blob/main/CONTRIBUTING.md)
* [Architecture](https://github.com/Gravewright/gravewright/blob/main/docs/architecture.md)
* [Testing](https://github.com/Gravewright/gravewright/blob/main/docs/testing.md)
* [Security](https://github.com/Gravewright/gravewright/blob/main/docs/security.md)
* [SDK documentation](https://github.com/Gravewright/gravewright/tree/main/docs/sdk)

Useful local checks:

```bash
grave doctor
uv run pytest tests/unit -q
uv run python -m compileall -q app tests scripts main.py
uv run pytest tests/e2e -q
```

## Project Status

Gravewright is currently **v1.0.0-alpha.1**.

Core gameplay, realtime transport, maps, actors, items, journals, permissions, SDK packages, package tooling, diagnostics, and public APIs are available for Alpha testing and are still evolving.

Breaking changes may happen between Alpha releases.

Do not trust Alpha releases with irreplaceable campaign data.

## Language

The primary project documentation is written in English.

Brazilian Portuguese documentation is also available under:

* [docs/pt-br/](https://github.com/Gravewright/gravewright/tree/main/docs/pt-br)

---

<div align="center">
  <strong>Build the table. Control the rules. Own the experience.</strong>
</div>
